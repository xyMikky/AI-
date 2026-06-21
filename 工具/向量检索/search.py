"""
Phase 2 · 向量检索接口
======================

读取 Phase 1 构建的 vectors.npz + metadata.parquet,对查询做 embedding
并返回 top-K 最相关的档案切片。

用法:
    # CLI 直接搜
    python 工具/向量检索/search.py "欧美电商促销结构版式"

    # 指定 top_k 和域过滤
    python 工具/向量检索/search.py "促销Banner" --top 10 --domain E_平面与海报

    # 排除某个类型
    python 工具/向量检索/search.py "详情页" --exclude-type INDEX

    # Python 内调用
    from search import search
    results = search("促销Banner", top_k=5)
"""

from __future__ import annotations

import argparse
import sys
from functools import lru_cache
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

from embedder import SiliconFlowEmbedder  # noqa: E402
from query_rewriter import rewrite as rewrite_query  # noqa: E402
from reranker import SiliconFlowReranker  # noqa: E402

VECTORS_PATH = SCRIPT_DIR / "vector_index" / "vectors.npz"
METADATA_PATH = SCRIPT_DIR / "vector_index" / "metadata.parquet"

# Qwen3 instruction-aware:query 侧加 task 描述能提升检索质量
DEFAULT_QUERY_INSTRUCTION = (
    "Given a design task or question in Chinese, "
    "retrieve the most relevant archived design references, principles, "
    "brand guidelines, and prompt cases that help answer it."
)


# ----------------------------------------------------------------------------
# 索引加载(带缓存,供多次查询复用)
# ----------------------------------------------------------------------------
@lru_cache(maxsize=1)
def _load_index():
    if not VECTORS_PATH.exists():
        raise FileNotFoundError(
            f"索引未构建,请先跑: python 工具/向量检索/build_index.py\n"
            f"缺失: {VECTORS_PATH}"
        )
    npz = np.load(VECTORS_PATH, allow_pickle=True)
    vectors = npz["vectors"].astype(np.float32)
    ids = npz["ids"].tolist()
    # 归一化以便用点积做余弦
    norms = np.linalg.norm(vectors, axis=1, keepdims=True) + 1e-12
    vectors_normed = vectors / norms
    meta = pd.read_parquet(METADATA_PATH)
    # 建立 id -> row_idx 的映射
    id_to_idx = {cid: i for i, cid in enumerate(ids)}
    return vectors_normed, meta, ids, id_to_idx


@lru_cache(maxsize=1)
def _get_embedder() -> SiliconFlowEmbedder:
    return SiliconFlowEmbedder()


@lru_cache(maxsize=1)
def _get_reranker() -> SiliconFlowReranker:
    return SiliconFlowReranker()


# ----------------------------------------------------------------------------
# 搜索核心
# ----------------------------------------------------------------------------
def search(
    query: str,
    top_k: int = 5,
    domain_filter: str | list[str] | None = None,
    type_filter: str | list[str] | None = None,
    exclude_type: str | list[str] | None = None,
    use_instruction: bool = True,
    min_score: float = 0.0,
    rewrite: bool = False,
    return_rewrite_info: bool = False,
    rerank: bool = False,
    rerank_pool: int = 20,
    rerank_doc_chars: int = 1500,
) -> list[dict] | tuple[list[dict], dict]:
    """
    语义检索。两阶段(粗排 + 精排):

      Stage 1 (embedding 粗排):
         query → vector → 余弦相似度 → top-`rerank_pool` 候选

      Stage 2 (reranker 精排,可选,仅 rerank=True 时启用):
         (query, doc) 成对送 Qwen3-Reranker / BGE-Reranker → top-K 结果
         结果项同时保留 vector_score 和 rerank_score

    Args:
        query: 查询文本
        top_k: 最终返回数量
        domain_filter: 只保留指定域
        type_filter: 只保留指定切片类型
        exclude_type: 排除指定切片类型(例如 'INDEX')
        use_instruction: 是否用 Qwen3 instruction 格式包装查询
        min_score: 向量分数下限
        rewrite: 先用 query_rewriter 扩展查询(追加领域术语)
        return_rewrite_info: 若为 True,返回 (results, rewrite_info)
        rerank: 启用 rerank 精排(成本 +¥0.001~0.003/次,精度大幅提升)
        rerank_pool: 粗排送入精排的候选数(默认 20,越大精度越高但成本越大)
        rerank_doc_chars: 送入 rerank 的每条 doc 截断字符数(控成本)

    Returns:
        默认:    [{score, chunk_id, domain, type, source_path, preview, text, ...}, ...]
          rerank=True 时每条额外含 vector_score / rerank_score 字段
        rewrite_info 开启:  (results, rewrite_info)
    """
    vectors, meta, ids, _ = _load_index()

    # 可选:先改写 query(口语化 → 结构化)
    rewrite_info = None
    search_query = query
    if rewrite:
        rewrite_info = rewrite_query(query)
        search_query = rewrite_info["expanded"]

    # 构造查询文本
    if use_instruction:
        q_text = f"Instruct: {DEFAULT_QUERY_INSTRUCTION}\nQuery: {search_query}"
    else:
        q_text = search_query

    # embed 查询
    embedder = _get_embedder()
    q_vec = embedder.embed_batch([q_text])[0]
    q_vec = q_vec / (np.linalg.norm(q_vec) + 1e-12)

    # 余弦相似度(归一化后的点积)
    scores = vectors @ q_vec

    # 过滤
    mask = np.ones(len(scores), dtype=bool)
    if domain_filter:
        wanted = {domain_filter} if isinstance(domain_filter, str) else set(domain_filter)
        mask &= meta["source_domain"].isin(wanted).to_numpy()
    if type_filter:
        wanted = {type_filter} if isinstance(type_filter, str) else set(type_filter)
        mask &= meta["source_type"].isin(wanted).to_numpy()
    if exclude_type:
        excluded = {exclude_type} if isinstance(exclude_type, str) else set(exclude_type)
        mask &= ~meta["source_type"].isin(excluded).to_numpy()
    if min_score > 0:
        mask &= scores >= min_score

    # 只在 mask=True 中排序 —— 若开启 rerank,取更大的候选池
    candidate_idx = np.where(mask)[0]
    if len(candidate_idx) == 0:
        if return_rewrite_info:
            return [], (rewrite_info or {})
        return []

    initial_k = max(rerank_pool, top_k) if rerank else top_k
    candidate_scores = scores[candidate_idx]
    order = np.argsort(-candidate_scores)[:initial_k]
    top_idx = candidate_idx[order]

    candidates = []
    for idx in top_idx:
        row = meta.iloc[idx]
        candidates.append({
            "score": float(scores[idx]),              # 粗排阶段:该字段 = 向量分
            "vector_score": float(scores[idx]),
            "chunk_id": row["chunk_id"],
            "source_domain": row["source_domain"],
            "source_type": row["source_type"],
            "source_path": row["source_path"],
            "preview": row["preview"],
            "text": row["text"],
            "chars": int(row["chars"]),
            "est_tokens": int(row["est_tokens"]),
        })

    # Stage 2: rerank 精排
    if rerank and candidates:
        try:
            reranker = _get_reranker()
            docs = [c["text"][:rerank_doc_chars] for c in candidates]
            ranked = reranker.rerank(search_query, docs, top_n=top_k)
            results = []
            for idx, r_score in ranked:
                c = dict(candidates[idx])
                c["rerank_score"] = float(r_score)
                c["score"] = float(r_score)           # 精排后:score 字段 = rerank 分
                results.append(c)
        except Exception as e:
            # rerank 失败时降级为向量粗排结果,保留前 top_k
            sys.stderr.write(f"[warn] rerank 调用失败,降级为向量粗排: {e}\n")
            results = candidates[:top_k]
    else:
        results = candidates[:top_k]

    if return_rewrite_info:
        return results, (rewrite_info or {})
    return results


# ----------------------------------------------------------------------------
# CLI
# ----------------------------------------------------------------------------
def _print_result_human(results: list[dict], show_text: bool = False):
    if not results:
        print("  无匹配结果")
        return
    for i, r in enumerate(results, 1):
        if "rerank_score" in r:
            header = (
                f"\n[{i}] rerank={r['rerank_score']:.4f}  "
                f"vec={r['vector_score']:.4f}  "
                f"{r['source_domain']}/{r['source_type']}"
            )
        else:
            header = f"\n[{i}] score={r['score']:.4f}  {r['source_domain']}/{r['source_type']}"
        print(header)
        print(f"    路径: {r['source_path']}")
        print(f"    ID  : {r['chunk_id']}  ({r['chars']} 字 / {r['est_tokens']} tokens)")
        if show_text:
            print("    ---")
            print("    " + r["text"][:600].replace("\n", "\n    "))
            if len(r["text"]) > 600:
                print(f"    ... (余 {len(r['text']) - 600} 字)")
        else:
            print(f"    预览: {r['preview'][:140]}...")


def _print_result_json(
    query: str,
    results: list[dict],
    include_full_text: bool = False,
    rewrite_info: dict | None = None,
):
    """AI 消费友好的结构化输出。"""
    import json
    out = {
        "query": query,
        "n_results": len(results),
    }
    if rewrite_info:
        out["rewrite"] = {
            "expanded_query": rewrite_info.get("expanded"),
            "extracted": rewrite_info.get("extracted"),
            "keywords_added": rewrite_info.get("keywords_added"),
        }
    def _serialize(i: int, r: dict) -> dict:
        base = {
            "rank": i + 1,
            "score": round(r["score"], 4),
            "chunk_id": r["chunk_id"],
            "domain": r["source_domain"],
            "type": r["source_type"],
            "source_path": r["source_path"],
            "chars": r["chars"],
            "est_tokens": r["est_tokens"],
            "preview": r["preview"][:200],
        }
        if "rerank_score" in r:
            base["rerank_score"] = round(r["rerank_score"], 4)
            base["vector_score"] = round(r["vector_score"], 4)
        if include_full_text:
            base["text"] = r["text"]
        return base

    out["results"] = [_serialize(i, r) for i, r in enumerate(results)]
    print(json.dumps(out, ensure_ascii=False, indent=2))


def main():
    ap = argparse.ArgumentParser(
        description="向量检索 · 从参考库/P域/品牌规范中召回最相关的档案切片"
    )
    ap.add_argument("query", help="检索查询")
    ap.add_argument("--top", type=int, default=5, help="返回 top K(默认 5)")
    ap.add_argument("--domain", default=None, help="只搜指定域(如 E_平面与海报 / 品牌规范)")
    ap.add_argument("--type", dest="stype", default=None, help="只搜指定切片类型(RECORD/PRINCIPLE/BRAND/P_CASE/P_CATALOG)")
    ap.add_argument("--exclude-type", default="INDEX", help="排除类型(默认排除 INDEX)")
    ap.add_argument("--no-instruction", action="store_true", help="不加 Qwen3 instruction 前缀")
    ap.add_argument("--min-score", type=float, default=0.0, help="分数下限,低于此值的结果丢弃")
    ap.add_argument("--text", action="store_true", help="[人类模式]显示前 600 字正文")
    ap.add_argument("--json", dest="as_json", action="store_true", help="[AI模式]以 JSON 格式输出")
    ap.add_argument("--full", action="store_true", help="[AI模式]JSON 中包含完整切片正文(配合 --json)")
    ap.add_argument("--rewrite", action="store_true", help="先用 query_rewriter 扩展口语化查询为结构化串")
    ap.add_argument("--rerank", action="store_true", help="启用 cross-encoder 精排(成本 +¥0.001~0.003/次,精度大幅提升)")
    ap.add_argument("--rerank-pool", type=int, default=20, help="rerank 粗排候选池大小(默认 20)")
    args = ap.parse_args()

    ret = search(
        args.query,
        top_k=args.top,
        domain_filter=args.domain,
        type_filter=args.stype,
        exclude_type=args.exclude_type if args.exclude_type != "NONE" else None,
        use_instruction=not args.no_instruction,
        min_score=args.min_score,
        rewrite=args.rewrite,
        return_rewrite_info=args.rewrite,
        rerank=args.rerank,
        rerank_pool=args.rerank_pool,
    )
    if args.rewrite:
        results, rewrite_info = ret
    else:
        results, rewrite_info = ret, None

    if args.as_json:
        _print_result_json(args.query, results, include_full_text=args.full, rewrite_info=rewrite_info)
        return

    print(f"查询: {args.query}")
    if rewrite_info:
        print(f"改写后: {rewrite_info.get('expanded')}")
        extracted = {k: v for k, v in rewrite_info.get("extracted", {}).items() if v}
        if extracted:
            print(f"抽取元数据: {extracted}")
    if args.domain:
        print(f"域过滤: {args.domain}")
    if args.stype:
        print(f"类型过滤: {args.stype}")
    if args.exclude_type:
        print(f"排除类型: {args.exclude_type}")
    if args.rerank:
        print(f"Rerank: 启用(pool={args.rerank_pool})")
    print("-" * 82)
    _print_result_human(results, show_text=args.text)


if __name__ == "__main__":
    main()
