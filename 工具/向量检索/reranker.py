"""
SiliconFlow Reranker 客户端
=========================

对 Qwen3-Reranker-8B(或 BAAI/bge-reranker-v2-m3)的 HTTP 调用做薄封装。

与 Embedder 的差别:
- Embedder 是"双塔":query 和 doc 各自编码后算相似度,适合快速粗排
- Reranker 是"交叉编码器":query 和 doc 成对输入模型,捕获 token 级精细匹配
  → 精度显著高于 embedding 相似度,但每次只能打分一组
  → 理想用法:embedding 召回 top-20 粗排,rerank 精排到 top-5

定价(SiliconFlow 2026-04):
- Qwen/Qwen3-Reranker-8B    约 ¥0.35 / 百万 tokens(请求 + 文档)
- Pro/BAAI/bge-reranker-v2-m3 约 ¥0.15 / 百万 tokens(更便宜,多语言也够用)

典型一次检索:query 300 tokens + 20 条 doc × 500 tokens ≈ 1 万 tokens ≈ ¥0.0035
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

import requests
from dotenv import load_dotenv

try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

_ENV_PATH = Path(__file__).resolve().parent.parent.parent / "config" / ".env"
load_dotenv(_ENV_PATH)


class RerankError(RuntimeError):
    pass


class SiliconFlowReranker:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[int] = None,
        max_rpm: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY", "").strip()
        if not self.api_key:
            raise RerankError("SILICONFLOW_API_KEY 未配置(检查 config/.env)")
        self.base_url = (base_url or os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")).rstrip("/")
        self.model = model or os.getenv("RERANK_MODEL", "Pro/BAAI/bge-reranker-v2-m3")
        self.timeout = int(timeout or os.getenv("RERANK_TIMEOUT", "60"))
        self.max_rpm = int(max_rpm or os.getenv("RERANK_MAX_RPM", "1200"))
        self._min_interval = 60.0 / max(1, self.max_rpm)
        self._last_call_ts = 0.0

    def rerank(
        self,
        query: str,
        documents: list[str],
        top_n: Optional[int] = None,
        max_retries: int = 4,
    ) -> list[tuple[int, float]]:
        """
        对 (query, documents[i]) 做精排,返回 [(index, score), ...],按 score 降序。

        index 是原输入 documents 列表中的索引。
        """
        if not documents:
            return []
        if not query or not query.strip():
            raise RerankError("query 为空")

        now = time.time()
        sleep_for = self._last_call_ts + self._min_interval - now
        if sleep_for > 0:
            time.sleep(sleep_for)

        payload = {
            "model": self.model,
            "query": query,
            "documents": documents,
            "return_documents": False,
        }
        if top_n is not None:
            payload["top_n"] = int(top_n)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/rerank"

        last_err = None
        for attempt in range(max_retries):
            try:
                self._last_call_ts = time.time()
                resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout)
                if resp.status_code == 429:
                    wait = (2 ** attempt) * 2
                    time.sleep(wait)
                    last_err = f"429 Too Many Requests, retry in {wait}s"
                    continue
                if resp.status_code >= 500:
                    wait = (2 ** attempt) * 2
                    time.sleep(wait)
                    last_err = f"{resp.status_code} server error, retry in {wait}s"
                    continue
                if resp.status_code != 200:
                    raise RerankError(f"HTTP {resp.status_code}: {resp.text[:300]}")

                data = resp.json()
                results = data.get("results", [])
                if not results:
                    raise RerankError(f"Rerank 返回空:{str(data)[:300]}")

                parsed: list[tuple[int, float]] = []
                for item in results:
                    idx = item.get("index")
                    score = item.get("relevance_score", item.get("score", 0.0))
                    if idx is None:
                        continue
                    parsed.append((int(idx), float(score)))
                parsed.sort(key=lambda x: -x[1])
                return parsed

            except requests.Timeout:
                wait = (2 ** attempt) * 2
                time.sleep(wait)
                last_err = f"timeout after {self.timeout}s"
            except requests.RequestException as e:
                wait = (2 ** attempt) * 2
                time.sleep(wait)
                last_err = f"{type(e).__name__}: {e}"

        raise RerankError(f"连续 {max_retries} 次失败: {last_err}")

    def ping(self) -> bool:
        r = self.rerank("塑身衣", ["塑身衣广告图", "Bauhaus 几何版式", "热带水果摄影"], top_n=3, max_retries=2)
        return len(r) == 3


if __name__ == "__main__":
    r = SiliconFlowReranker()
    print(f"Model  : {r.model}")
    print(f"BaseURL: {r.base_url}")
    print(f"MaxRPM : {r.max_rpm} (min interval: {r._min_interval:.3f}s)")

    query = "欧美电商塑身衣促销Banner版式"
    docs = [
        "P2 促销Banner 海报 · 含 NEBILITY 对角分栏版式与红色 CTA",
        "宠物食品包装色彩趋势 — 马卡龙色系与插画元素",
        "Bauhaus 几何版式原则:面/线/点三元素的动态平衡",
        "功能服装详情页 HERO 模块 — 健身房场景全身模特",
        "欧美详情页排版高级感规范 — 字体大小 / 字距 / 留白",
        "东方花鸟摄影 — 黄金时段自然光与柔焦人像",
    ]
    print(f"\n[ping] 对 {len(docs)} 条文档打分,query='{query}'")
    t0 = time.time()
    results = r.rerank(query, docs, top_n=len(docs))
    print(f"  耗时: {time.time() - t0:.2f}s  (返回 {len(results)} 条)")
    print(f"{'rank':<6}{'index':<8}{'score':<12}doc")
    for rank, (idx, score) in enumerate(results, 1):
        print(f"{rank:<6}{idx:<8}{score:<12.4f}{docs[idx][:60]}")
