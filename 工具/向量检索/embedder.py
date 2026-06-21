"""
SiliconFlow Embedding 客户端
============================

对 Qwen3-Embedding-8B 的 HTTP 调用做薄封装,处理:
- 批量 embed
- 限流(按 RPM)
- 指数退避重试
- 超时处理

不含业务逻辑。供 build_index.py / search.py 共用。
"""

from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from typing import Optional

import numpy as np
import requests
from dotenv import load_dotenv

# 强制 UTF-8 输出
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 加载 .env
_ENV_PATH = Path(__file__).resolve().parent.parent.parent / "config" / ".env"
load_dotenv(_ENV_PATH)


class EmbedError(RuntimeError):
    pass


class SiliconFlowEmbedder:
    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        model: Optional[str] = None,
        dim: Optional[int] = None,
        timeout: Optional[int] = None,
        max_rpm: Optional[int] = None,
    ):
        self.api_key = api_key or os.getenv("SILICONFLOW_API_KEY", "").strip()
        if not self.api_key:
            raise EmbedError("SILICONFLOW_API_KEY 未配置(检查 config/.env)")
        self.base_url = (base_url or os.getenv("SILICONFLOW_BASE_URL", "https://api.siliconflow.cn/v1")).rstrip("/")
        self.model = model or os.getenv("EMBEDDING_MODEL", "Qwen/Qwen3-Embedding-8B")
        self.dim = int(dim or os.getenv("EMBEDDING_DIM", "4096"))
        self.timeout = int(timeout or os.getenv("EMBEDDING_TIMEOUT", "60"))
        self.max_rpm = int(max_rpm or os.getenv("EMBEDDING_MAX_RPM", "1600"))
        self._min_interval = 60.0 / max(1, self.max_rpm)
        self._last_call_ts = 0.0

    # --------------------------------------------------------------
    # 单批调用
    # --------------------------------------------------------------
    def embed_batch(
        self,
        texts: list[str],
        max_retries: int = 4,
        return_numpy: bool = True,
    ) -> np.ndarray | list[list[float]]:
        """对一批文本做 embedding,返回 (n, dim) 矩阵。"""
        if not texts:
            raise EmbedError("texts 为空")

        # 限速
        now = time.time()
        sleep_for = self._last_call_ts + self._min_interval - now
        if sleep_for > 0:
            time.sleep(sleep_for)

        payload = {
            "model": self.model,
            "input": texts,
            "encoding_format": "float",
        }
        # 维度参数:Qwen3 支持 Matryoshka,4096 不传,否则传 dimensions
        if self.dim and self.dim != 4096:
            payload["dimensions"] = self.dim

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        url = f"{self.base_url}/embeddings"

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
                    raise EmbedError(f"HTTP {resp.status_code}: {resp.text[:300]}")

                data = resp.json()
                items = data.get("data", [])
                if len(items) != len(texts):
                    raise EmbedError(f"返回条数 {len(items)} 与输入 {len(texts)} 不匹配")
                # items 按 index 排序(防乱序)
                items.sort(key=lambda x: x.get("index", 0))
                vectors = [it["embedding"] for it in items]
                if return_numpy:
                    return np.array(vectors, dtype=np.float32)
                return vectors
            except requests.Timeout:
                wait = (2 ** attempt) * 2
                time.sleep(wait)
                last_err = f"timeout after {self.timeout}s"
            except requests.RequestException as e:
                wait = (2 ** attempt) * 2
                time.sleep(wait)
                last_err = f"{type(e).__name__}: {e}"

        raise EmbedError(f"连续 {max_retries} 次失败: {last_err}")

    # --------------------------------------------------------------
    # 测试
    # --------------------------------------------------------------
    def ping(self) -> bool:
        """简单探活:embed 一条短文本。"""
        vec = self.embed_batch(["你好"], max_retries=2)
        return vec.shape == (1, self.dim)


if __name__ == "__main__":
    # 简易自检
    e = SiliconFlowEmbedder()
    print(f"Model: {e.model}")
    print(f"Base URL: {e.base_url}")
    print(f"Target dim: {e.dim}")
    print(f"Max RPM: {e.max_rpm} (min interval: {e._min_interval:.3f}s)")
    print("\n[ping] embedding '你好' ...")
    t0 = time.time()
    vec = e.embed_batch(["你好"])
    print(f"  shape: {vec.shape}  dtype: {vec.dtype}  耗时: {time.time() - t0:.2f}s")
    print(f"  前 8 维: {vec[0, :8]}")
    print("\n[batch] embedding 3 条 ...")
    t0 = time.time()
    vec = e.embed_batch(["塑身衣广告", "Bauhaus 几何版式", "Minimalist portrait photography"])
    print(f"  shape: {vec.shape}  耗时: {time.time() - t0:.2f}s")
