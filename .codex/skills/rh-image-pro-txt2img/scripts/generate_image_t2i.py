#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH GPT-image 2 官方文生图 API 调用脚本

使用 RunningHub API (endpoint: rhart-image-g-2-official/text-to-image) 实现纯文本生图。
与图生图 (rhart-image-n-pro/edit) 不同，本脚本不需要输入参考图片。

用法：
    python generate_image_t2i.py \
        --prompt "描述文字" \
        [--aspect-ratio "9:16"] \
        [--resolution "2k"] \
        [--quality "medium"] \
        [--output-dir "/AI设计师助手/生成结果输出"] \
        [--label "任务名称"]

输出：JSON 格式，包含 saved_paths / result_urls / error
"""

import json
import os
import sys
import time
import argparse
import requests
from pathlib import Path
from datetime import datetime
from typing import Optional

# ── 路径推断 ─────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent
SKILL_DIR    = SCRIPT_DIR.parent
CODEX_DIR   = SKILL_DIR.parent.parent
PROJECT_ROOT = CODEX_DIR.parent
CONFIG_DIR   = PROJECT_ROOT / "config"
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "生成结果输出"

ENDPOINT   = "rhart-image-g-2-official/text-to-image"
DEFAULT_BASE_URL = "https://www.runninghub.cn/openapi/v2"


# ── 配置读取 ──────────────────────────────────────────────────────────────────

def _load_env() -> dict:
    env_path = CONFIG_DIR / ".env"
    result = {}
    if not env_path.exists():
        return result
    with open(env_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, _, v = line.partition("=")
                k = k.strip(); v = v.strip().strip('"').strip("'")
                if k and v:
                    result[k] = v
    return result


_ENV = None


def _get(key: str, default: str = "") -> str:
    global _ENV
    if _ENV is None:
        _ENV = _load_env()
    return os.environ.get(key, "").strip() or _ENV.get(key, "").strip() or default


def get_api_key() -> str:
    return _get("RH_API_KEY")


def get_base_url() -> str:
    return _get("RH_API_BASE_URL", DEFAULT_BASE_URL)


def get_default_max_poll_seconds() -> int:
    raw = _get("RH_API_MAX_POLLING_TIME", "")
    if raw:
        try:
            return max(30, int(raw.strip()))
        except ValueError:
            pass
    return 600


def get_poll_interval_seconds() -> float:
    raw = _get("RH_API_POLLING_INTERVAL", "")
    if raw:
        try:
            return max(1.0, min(60.0, float(raw.strip().replace(",", "."))))
        except ValueError:
            pass
    return 5.0


# ── API 任务提交与轮询 ────────────────────────────────────────────────────────

def submit_task(payload: dict, api_key: str, base_url: str, timeout: int = 60) -> str:
    url     = f"{base_url.rstrip('/')}/{ENDPOINT}"
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    for attempt in range(3):
        if attempt:
            time.sleep(min(2 ** attempt + 1, 15))
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            data = resp.json() if resp.text else {}
            if resp.status_code != 200:
                raise RuntimeError(f"提交 HTTP {resp.status_code}: {data.get('errorMessage', '')}")
            err = data.get("errorCode") or data.get("errorMessage")
            if err:
                raise RuntimeError(f"提交失败: {err}")
            task_id = data.get("taskId") or data.get("task_id")
            if not task_id:
                raise RuntimeError("响应中无 taskId")
            return str(task_id)
        except requests.RequestException as e:
            if attempt == 2:
                raise RuntimeError(f"网络错误: {e}")
    raise RuntimeError("提交失败: 已重试 3 次")


def poll_task(task_id: str, api_key: str, base_url: str,
              interval: float = 5.0, max_time: int = 600) -> list:
    url      = f"{base_url.rstrip('/')}/query"
    headers  = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    payload  = {"taskId": task_id}
    start    = time.time()
    failures = 0

    while True:
        if time.time() - start > max_time:
            raise RuntimeError(f"轮询超时 ({max_time}s) [taskId={task_id}]")
        time.sleep(interval)
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=30)
        except requests.RequestException:
            failures += 1
            if failures >= 5:
                raise RuntimeError("连续网络错误，轮询中止")
            continue

        if resp.status_code != 200:
            failures += 1
            if failures >= 5:
                raise RuntimeError(f"服务器连续错误 HTTP {resp.status_code}")
            time.sleep(min(failures * 2, 10))
            continue

        try:
            data = resp.json()
        except Exception:
            failures += 1
            continue

        failures = 0
        err = data.get("errorCode") or data.get("errorMessage")
        if err:
            raise RuntimeError(f"任务失败: {err}")

        status = (data.get("status") or "").upper()
        if status == "SUCCESS":
            urls = [r.get("url") or r.get("outputUrl") for r in (data.get("results") or [])]
            urls = [u for u in urls if u]
            if not urls:
                raise RuntimeError(f"结果中无图片 URL [taskId={task_id}]")
            return urls
        if status == "FAILED":
            raise RuntimeError(f"任务执行失败 [taskId={task_id}]")
        if status == "CANCEL":
            raise RuntimeError(f"任务已取消 [taskId={task_id}]")
        print(f"  [轮询] 状态={status} 已等待 {int(time.time()-start)}s ...", file=sys.stderr)


def download_image(url: str, save_path: Path, timeout: int = 60):
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(resp.content)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def run(prompt: str, aspect_ratio: str, resolution: str, quality: str,
        output_dir: Path, label: str, max_poll_seconds: Optional[int] = None) -> dict:

    api_key  = get_api_key()
    base_url = get_base_url()

    if not api_key or api_key == "your_runninghub_api_key_here":
        return {
            "success": False,
            "error": (
                "未配置 RH_API_KEY！\n"
                f"请编辑: {CONFIG_DIR / '.env'}\n"
                "将 RH_API_KEY=your_runninghub_api_key_here 替换为真实 API Key"
            )
        }

    # 1. 构建 payload（无图片上传，直接提交）
    payload = {
        "prompt":      prompt,
        "aspectRatio": aspect_ratio,
        "resolution":  resolution,
        "quality":     quality,
    }

    # 2. 提交任务
    print(f"[1/3] 提交文生图任务...", file=sys.stderr)
    print(f"  prompt: {prompt[:80]}{'...' if len(prompt)>80 else ''}", file=sys.stderr)
    print(f"  aspectRatio={aspect_ratio}  resolution={resolution}  quality={quality}", file=sys.stderr)
    task_id = submit_task(payload, api_key, base_url)
    print(f"  taskId={task_id}", file=sys.stderr)

    # 3. 轮询结果
    mps = max_poll_seconds if max_poll_seconds is not None else get_default_max_poll_seconds()
    print(f"[2/3] 等待生图完成（最长 {mps}s）...", file=sys.stderr)
    result_urls = poll_task(
        task_id, api_key, base_url,
        interval=get_poll_interval_seconds(),
        max_time=mps,
    )
    print(f"  生图完成，获得 {len(result_urls)} 张图片", file=sys.stderr)

    # 4. 下载保存
    print(f"[3/3] 下载保存图片...", file=sys.stderr)
    date_str  = datetime.now().strftime("%Y%m%d")
    out_dir   = output_dir / date_str
    timestamp = datetime.now().strftime("%H%M%S")
    safe_label = "".join(c for c in (label or prompt[:30]) if c not in r'\/:*?"<>|').strip()
    safe_label = safe_label.replace(" ", "_") or "generated"

    saved_paths = []
    for i, url in enumerate(result_urls):
        ext      = "jpg" if url.lower().endswith(".jpg") else "png"
        filename = f"{safe_label}_{timestamp}_{i+1}.{ext}"
        save_path = out_dir / filename
        download_image(url, save_path)
        saved_paths.append(str(save_path))
        print(f"  已保存: {save_path}", file=sys.stderr)

    return {
        "success":     True,
        "task_id":     task_id,
        "result_urls": result_urls,
        "saved_paths": saved_paths,
        "save_dir":    str(out_dir),
        "prompt":      prompt,
        "aspect_ratio": aspect_ratio,
        "resolution":   resolution,
        "quality":      quality,
    }


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="RH GPT-image 2 官方文生图 CLI")
    parser.add_argument("--prompt",       required=True,
                        help="图像描述提示词（默认中文，技术锚点保留原样）")
    parser.add_argument("--aspect-ratio", default="9:16",
                        choices=["1:1","16:9","9:16","4:3","3:4","3:2","2:3","5:4","4:5","21:9"],
                        help="输出图片比例（默认 9:16）")
    parser.add_argument("--resolution",   default="2k",
                        choices=["1k","2k","4k"],
                        help="输出分辨率（默认 2k）")
    parser.add_argument("--quality",      default="medium",
                        choices=["low","medium","high"],
                        help="生成质量（默认 medium）")
    parser.add_argument("--output-dir",   default=str(DEFAULT_OUTPUT_DIR),
                        help="图片保存根目录")
    parser.add_argument("--label",        default="",
                        help="输出文件名标签（留空则使用 prompt 前 30 字）")
    parser.add_argument("--max-poll-seconds", type=int, default=None,
                        help="轮询最长时间（秒）；省略时读取 config/.env 的 RH_API_MAX_POLLING_TIME，未配置则 600")
    args = parser.parse_args()

    max_poll = (
        args.max_poll_seconds
        if args.max_poll_seconds is not None
        else get_default_max_poll_seconds()
    )

    result = run(
        prompt      = args.prompt,
        aspect_ratio= args.aspect_ratio,
        resolution  = args.resolution,
        quality     = args.quality,
        output_dir  = Path(args.output_dir),
        label       = args.label,
        max_poll_seconds=max_poll,
    )

    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
