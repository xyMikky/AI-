"""
Phase 1 · 全量构建向量索引
============================

读取 chunking.py 切出的记录,调 SiliconFlow Qwen3-Embedding-8B 批量向量化,
保存到:
    vector_index/vectors.npz          — (N, 4096) float32
    vector_index/metadata.parquet     — chunk_id / path / domain / type / preview / chars / tokens
    vector_index/checkpoint.pkl       — 断点续传状态(中断恢复用)

用法:
    # 全量构建
    python 工具/向量检索/build_index.py

    # 小批测试(只跑前 20 条)
    python 工具/向量检索/build_index.py --limit 20

    # 断点续传(自动检测 checkpoint)
    python 工具/向量检索/build_index.py --resume

    # 重新构建(忽略 checkpoint)
    python 工具/向量检索/build_index.py --force
"""

from __future__ import annotations

import argparse
import pickle
import sys
import time
from dataclasses import asdict
from pathlib import Path

import numpy as np
import pandas as pd
from tqdm import tqdm

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from chunking import Chunk  # noqa: E402
from embedder import SiliconFlowEmbedder  # noqa: E402
from scan_archives import (  # noqa: E402
    scan_reference_library,
    scan_p_domain_cases,
    scan_brand_library,
    scan_capability_modules,
    scan_scene_knowledge,
)

PROJECT_ROOT = SCRIPT_DIR.parent.parent
OUTPUT_DIR = SCRIPT_DIR / "vector_index"
VECTORS_PATH = OUTPUT_DIR / "vectors.npz"
METADATA_PATH = OUTPUT_DIR / "metadata.parquet"
CHECKPOINT_PATH = OUTPUT_DIR / "checkpoint.pkl"
INFO_PATH = OUTPUT_DIR / "index_info.json"


# ----------------------------------------------------------------------------
# 收集所有 chunks
# ----------------------------------------------------------------------------
def collect_all_chunks() -> list[Chunk]:
    """静默扫描(scan 函数自带少量 print,接受)。"""
    ref_chunks, _ = scan_reference_library()
    p_chunks, _ = scan_p_domain_cases()
    brand_chunks, _ = scan_brand_library()
    module_chunks, _ = scan_capability_modules()
    scene_chunks, _ = scan_scene_knowledge()
    return ref_chunks + p_chunks + brand_chunks + module_chunks + scene_chunks


# ----------------------------------------------------------------------------
# 断点续传
# ----------------------------------------------------------------------------
def load_checkpoint() -> dict | None:
    if not CHECKPOINT_PATH.exists():
        return None
    try:
        with open(CHECKPOINT_PATH, "rb") as f:
            return pickle.load(f)
    except Exception as e:
        print(f"  ! checkpoint 读取失败,忽略: {e}", file=sys.stderr)
        return None


def save_checkpoint(state: dict):
    with open(CHECKPOINT_PATH, "wb") as f:
        pickle.dump(state, f)


def clear_checkpoint():
    if CHECKPOINT_PATH.exists():
        CHECKPOINT_PATH.unlink()


# ----------------------------------------------------------------------------
# 主构建流程
# ----------------------------------------------------------------------------
def build(limit: int | None = None, resume: bool = False, force: bool = False):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # --- 1. 收集 chunks ---
    print("=" * 82)
    print("Phase 1 · 全量构建向量索引")
    print("=" * 82)
    print("\n[1/4] 扫描并切片...")
    chunks = collect_all_chunks()
    if limit:
        chunks = chunks[:limit]
        print(f"  [LIMIT] 只处理前 {limit} 块")
    print(f"  共 {len(chunks)} 块待 embedding")

    # --- 2. 检查 checkpoint ---
    processed_ids: set[str] = set()
    processed_vectors: dict[str, np.ndarray] = {}
    if force:
        clear_checkpoint()
        if VECTORS_PATH.exists():
            VECTORS_PATH.unlink()
        if METADATA_PATH.exists():
            METADATA_PATH.unlink()
        print("  [FORCE] 已清除旧索引与 checkpoint")
    elif resume:
        cp = load_checkpoint()
        if cp:
            processed_ids = set(cp["ids"])
            processed_vectors = cp["vectors"]
            print(f"  [RESUME] 从 checkpoint 恢复 {len(processed_ids)} 条已完成")

    todo = [c for c in chunks if c.chunk_id not in processed_ids]
    if not todo:
        print("  全部已完成,无需重跑")
    else:
        print(f"  待处理 {len(todo)} 块(跳过已完成 {len(processed_ids)} 块)")

    # --- 3. 批量 embedding ---
    if todo:
        print("\n[2/4] 初始化 SiliconFlow 客户端...")
        embedder = SiliconFlowEmbedder()
        print(f"  模型: {embedder.model}  维度: {embedder.dim}")

        import os as _os
        batch_size = int(_os.getenv("EMBEDDING_BATCH_SIZE", "10"))

        n_batches = (len(todo) + batch_size - 1) // batch_size
        print(f"\n[3/4] 批量 embedding(batch={batch_size}, 共 {n_batches} 批)...")

        t_start = time.time()
        pbar = tqdm(total=len(todo), desc="embed", unit="chunk")
        checkpoint_every = max(5, n_batches // 20)  # 每 5% 存一次
        batches_since_ckpt = 0
        try:
            for i in range(0, len(todo), batch_size):
                batch = todo[i : i + batch_size]
                texts = [c.text for c in batch]
                vectors = embedder.embed_batch(texts)
                for ch, vec in zip(batch, vectors):
                    processed_vectors[ch.chunk_id] = vec
                    processed_ids.add(ch.chunk_id)
                pbar.update(len(batch))
                batches_since_ckpt += 1
                if batches_since_ckpt >= checkpoint_every:
                    save_checkpoint({"ids": list(processed_ids), "vectors": processed_vectors})
                    batches_since_ckpt = 0
        except KeyboardInterrupt:
            pbar.close()
            print("\n  ! 被中断,保存 checkpoint...")
            save_checkpoint({"ids": list(processed_ids), "vectors": processed_vectors})
            print(f"  已保存 {len(processed_ids)} 条到 {CHECKPOINT_PATH.name}")
            print(f"  下次用 --resume 恢复")
            return
        except Exception as e:
            pbar.close()
            print(f"\n  ! 发生错误: {e}")
            print("  保存 checkpoint...")
            save_checkpoint({"ids": list(processed_ids), "vectors": processed_vectors})
            raise
        pbar.close()
        elapsed = time.time() - t_start
        print(f"  完成 {len(todo)} 块,耗时 {elapsed:.1f}s,均速 {len(todo)/max(elapsed,0.01):.1f} chunk/s")

    # --- 4. 保存最终索引 ---
    print("\n[4/4] 保存索引文件...")
    # 按原始 chunks 顺序重排
    ordered_ids = [c.chunk_id for c in chunks]
    vectors_matrix = np.stack([processed_vectors[cid] for cid in ordered_ids], axis=0)

    # 元数据表
    meta_rows = []
    for c in chunks:
        meta_rows.append({
            "chunk_id": c.chunk_id,
            "source_path": c.source_path,
            "source_domain": c.source_domain,
            "source_type": c.source_type,
            "chunk_index": c.chunk_index,
            "chars": c.chars,
            "est_tokens": c.est_tokens,
            "preview": c.text.replace("\n", " ")[:200],
            "text": c.text,  # 完整文本也存,供检索结果显示片段
        })
    meta_df = pd.DataFrame(meta_rows)

    # 保存
    np.savez_compressed(VECTORS_PATH, vectors=vectors_matrix, ids=np.array(ordered_ids))
    meta_df.to_parquet(METADATA_PATH, index=False, compression="snappy")

    info = {
        "total_chunks": len(chunks),
        "vector_dim": int(vectors_matrix.shape[1]),
        "vectors_path": str(VECTORS_PATH.relative_to(PROJECT_ROOT)),
        "metadata_path": str(METADATA_PATH.relative_to(PROJECT_ROOT)),
        "model": "Qwen/Qwen3-Embedding-8B",
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    import json
    INFO_PATH.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    # 清除 checkpoint(全部完成)
    clear_checkpoint()

    print(f"  vectors.npz       : {vectors_matrix.shape}  ({VECTORS_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"  metadata.parquet  : {len(meta_df)} 行  ({METADATA_PATH.stat().st_size / 1024:.1f} KB)")
    print(f"  index_info.json   : {INFO_PATH.name}")

    print("\n" + "=" * 82)
    print("✅ 构建完成")
    print("=" * 82)
    print(f"  索引位置: {OUTPUT_DIR.relative_to(PROJECT_ROOT)}")
    print(f"  下一步  : python 工具/向量检索/search.py \"你的问题\"")


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=None, help="只处理前 N 块(测试用)")
    ap.add_argument("--resume", action="store_true", help="从 checkpoint 续跑")
    ap.add_argument("--force", action="store_true", help="强制重建,忽略 checkpoint 和旧索引")
    args = ap.parse_args()
    build(limit=args.limit, resume=args.resume, force=args.force)


if __name__ == "__main__":
    main()
