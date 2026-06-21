"""
向量索引增量更新
================

按 (source_path, text_hash) 作为复用键:
    - 新切片正文与旧库中某切片完全一致 -> 直接复用旧向量(免费)
    - 正文变化或全新切片 -> 只对这部分调用 embedding API

典型场景:
    - M10 / M17 学习后追加了新记录
    - P 域入库了新成功案例
    - 某子文件被手工编辑

用法:
    # 常规增量更新(推荐)
    python 工具/向量检索/update_index.py

    # 试运行(只统计变更,不真正调用 API)
    python 工具/向量检索/update_index.py --dry-run

    # 强制全量重建(等价于 build_index.py --force)
    python 工具/向量检索/update_index.py --full

期望行为:
    - 新追加 10 条记录 -> 只 embed 这 10 条(~5-15s,~¥0.005)
    - 编辑了 3 条记录   -> 只 embed 这 3 条
    - 删除了 2 条记录   -> 不 embed, 只从索引中剔除
    - 无变更           -> 打印"无变更",立即退出
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

import numpy as np
import pandas as pd

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
INFO_PATH = OUTPUT_DIR / "index_info.json"


def _text_hash(text: str) -> str:
    return hashlib.md5(text.encode("utf-8")).hexdigest()[:16]


def _load_existing() -> tuple[dict[tuple[str, str], np.ndarray], dict[str, np.ndarray], int]:
    """
    从已有索引加载两种复用映射:
        reuse_by_hash     : (source_path, text_hash) -> vector   [主键,正文完全相同即复用]
        reuse_by_chunk_id : chunk_id                 -> vector   [辅键,id 未变即复用]
    返回:
        (reuse_by_hash, reuse_by_chunk_id, old_row_count)
    若索引不存在 -> 三者均为空。
    """
    if not (VECTORS_PATH.exists() and METADATA_PATH.exists()):
        return {}, {}, 0

    vecs_npz = np.load(VECTORS_PATH, allow_pickle=True)
    old_vectors = vecs_npz["vectors"]
    old_ids = vecs_npz["ids"]
    old_meta = pd.read_parquet(METADATA_PATH)

    if len(old_ids) != len(old_meta):
        print(f"  ! 警告: vectors({len(old_ids)}) 与 metadata({len(old_meta)}) 行数不一致,忽略旧索引", file=sys.stderr)
        return {}, {}, 0

    by_hash: dict[tuple[str, str], np.ndarray] = {}
    by_id: dict[str, np.ndarray] = {}
    for i, cid in enumerate(old_ids):
        cid = str(cid)
        row = old_meta.iloc[i]
        vec = old_vectors[i]
        by_id[cid] = vec
        h = _text_hash(str(row["text"]))
        by_hash[(str(row["source_path"]), h)] = vec

    return by_hash, by_id, len(old_ids)


def collect_all_chunks() -> list[Chunk]:
    ref_chunks, _ = scan_reference_library()
    p_chunks, _ = scan_p_domain_cases()
    brand_chunks, _ = scan_brand_library()
    module_chunks, _ = scan_capability_modules()
    scene_chunks, _ = scan_scene_knowledge()
    return ref_chunks + p_chunks + brand_chunks + module_chunks + scene_chunks


def update(dry_run: bool = False):
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    print("=" * 82)
    print("向量索引 · 增量更新")
    print("=" * 82)

    # Step 1: 加载旧索引的复用映射
    print("\n[1/4] 加载旧索引...")
    reuse_by_hash, reuse_by_id, old_count = _load_existing()
    if old_count == 0:
        print("  未找到旧索引 -> 建议直接用 build_index.py --force 全量构建")
        print("  或继续:本次将把所有切片视为新切片")
    else:
        print(f"  旧索引: {old_count} 条切片")

    # Step 2: 扫描当前所有切片
    print("\n[2/4] 扫描并切片当前档案...")
    chunks = collect_all_chunks()
    print(f"  当前: {len(chunks)} 条切片")

    # Step 3: 按 hash 做复用匹配
    print("\n[3/4] 计算复用 / 变更 / 新增 / 删除...")
    reused_vectors: dict[str, np.ndarray] = {}
    to_embed: list[Chunk] = []
    reused_via_hash = 0
    reused_via_id = 0

    for c in chunks:
        h = _text_hash(c.text)
        key_hash = (c.source_path, h)

        if key_hash in reuse_by_hash:
            reused_vectors[c.chunk_id] = reuse_by_hash[key_hash]
            reused_via_hash += 1
        elif c.chunk_id in reuse_by_id:
            # chunk_id 相同但正文已变 -> 不复用,必须重 embed
            to_embed.append(c)
        else:
            to_embed.append(c)

    # 额外统计:有多少是因 id 复用(正文未变但 id 相同),多少是 hash 复用(正文未变但 id 变化)
    for c in chunks:
        if c.chunk_id in reused_vectors and c.chunk_id in reuse_by_id:
            # 判断是 hash 命中还是 id 命中——已经在上面归到 hash 里了
            pass

    deleted = old_count - reused_via_hash  # 原索引有但当前扫描没有的数量(粗算)
    print(f"  复用(正文未变): {reused_via_hash} 条")
    print(f"  需要重新 embed : {len(to_embed)} 条")
    print(f"  旧索引中已失效 : ~{max(deleted, 0)} 条")

    if len(to_embed) == 0:
        print("\n  ✅ 所有切片均可复用,无需调用 API")
        if old_count == len(chunks) and reused_via_hash == len(chunks):
            print("  索引文件已是最新,无需重写")
            return
        print("  继续重写索引以消除失效切片")

    # 成本估算
    est_tokens = sum(c.est_tokens for c in to_embed)
    est_cost = est_tokens / 1_000_000 * 0.50  # ¥0.5/M tokens
    est_time = len(to_embed) * 0.8            # 粗估 0.8s/chunk
    print(f"\n  预计调用 API 成本: ¥{est_cost:.4f}({est_tokens:,} tokens)")
    print(f"  预计耗时         : {est_time:.0f}s")

    if dry_run:
        print("\n[DRY-RUN] 仅统计,不真正调用 API,退出。")
        return

    # Step 4: 对 to_embed 调 API
    if to_embed:
        print("\n[4/4] 批量 embedding...")
        embedder = SiliconFlowEmbedder()

        import os as _os
        batch_size = int(_os.getenv("EMBEDDING_BATCH_SIZE", "10"))

        try:
            from tqdm import tqdm
            pbar = tqdm(total=len(to_embed), desc="embed", unit="chunk")
        except Exception:
            pbar = None

        t0 = time.time()
        for i in range(0, len(to_embed), batch_size):
            batch = to_embed[i : i + batch_size]
            texts = [c.text for c in batch]
            vectors = embedder.embed_batch(texts)
            for ch, vec in zip(batch, vectors):
                reused_vectors[ch.chunk_id] = vec
            if pbar:
                pbar.update(len(batch))
        if pbar:
            pbar.close()
        elapsed = time.time() - t0
        print(f"  完成 {len(to_embed)} 条,耗时 {elapsed:.1f}s")
    else:
        print("\n[4/4] 跳过 embedding(全部复用)")

    # Step 5: 保存
    print("\n[5/5] 重写索引文件...")
    ordered_ids = [c.chunk_id for c in chunks]
    vectors_matrix = np.stack([reused_vectors[cid] for cid in ordered_ids], axis=0)

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
            "text": c.text,
        })
    meta_df = pd.DataFrame(meta_rows)

    np.savez_compressed(VECTORS_PATH, vectors=vectors_matrix, ids=np.array(ordered_ids))
    meta_df.to_parquet(METADATA_PATH, index=False, compression="snappy")

    info = {
        "total_chunks": len(chunks),
        "vector_dim": int(vectors_matrix.shape[1]),
        "vectors_path": str(VECTORS_PATH.relative_to(PROJECT_ROOT)),
        "metadata_path": str(METADATA_PATH.relative_to(PROJECT_ROOT)),
        "model": "Qwen/Qwen3-Embedding-8B",
        "built_at": time.strftime("%Y-%m-%d %H:%M:%S"),
        "last_update_mode": "incremental",
        "last_update_stats": {
            "reused": reused_via_hash,
            "re_embedded": len(to_embed),
        },
    }
    INFO_PATH.write_text(json.dumps(info, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"  vectors.npz       : {vectors_matrix.shape}  ({VECTORS_PATH.stat().st_size / 1024 / 1024:.2f} MB)")
    print(f"  metadata.parquet  : {len(meta_df)} 行")
    print(f"  index_info.json   : 模式=incremental, 复用={reused_via_hash}, 重嵌={len(to_embed)}")

    print("\n" + "=" * 82)
    print("✅ 增量更新完成")
    print("=" * 82)


def main():
    ap = argparse.ArgumentParser(description="向量索引增量更新(按 text hash 复用)")
    ap.add_argument("--dry-run", action="store_true", help="只统计变更,不真正调用 API")
    ap.add_argument("--full", action="store_true", help="等价于 build_index.py --force(强制全量重建)")
    args = ap.parse_args()

    if args.full:
        # 直接调 build_index
        from build_index import build  # type: ignore
        build(force=True)
        return

    update(dry_run=args.dry_run)


if __name__ == "__main__":
    main()
