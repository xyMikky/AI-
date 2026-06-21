#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
RH 全能图片PRO-图生图 API 调用脚本

支持三个模型（通过 --model 参数选择，默认 pro）：

  pro    (默认) rhart-image-n-pro/edit
         全能图片PRO（Nano Banana Pro / Gemini 3 Pro Image），细节还原精准，
         适合产品精修与最终出图。支持最多 10 张参考图、resolution 1k/2k/4k。

  flash         rhart-image-n-g31-flash/image-to-image
         Banana2 Flash 版，价格更低，特征提取能力强，大幅改动时仍能保留原图
         核心结构；细节略逊于 pro，适合前期批量创意阶段，或 pro 繁忙时的备用
         选择。支持最多 10 张参考图、resolution 1k/2k/4k。

  gpt-image-2   [实验性] rhart-image-g-2/image-to-image（走 rhtv.runninghub.cn 子域）
         ChatGPT 系图生图模型。API 功能尚不完善、稳定性待验证。
         ⚠ 默认不使用；AI 调用时仅在用户明确点名要求（gpt-image-2 / GPT /
         ChatGPT 模型）时切换，不得基于场景推断主动替换 pro。
         限制：
           * imageUrls 最多 2 张，每张 ≤10MB；
           * 不支持 resolution 参数（传入会被忽略）；
           * aspectRatio 官方枚举仅 2:3 / 1:1 / 3:2，本脚本不再将该字段写入
             payload；请在 prompt 文本中用自然语言说明想要的比例（例如
             "aspect ratio 21:9" / "比例 9:16 竖版"）。

用法：
    python generate_image.py \
        --images "path1.jpg" "path2.jpg" \
        --prompt "描述文字" \
        [--model pro|flash|gpt-image-2] \
        [--aspect-ratio "3:4"] \
        [--resolution "2k"] \
        [--output-dir "/AI师助手/生成结果输出"] \
        [--label "任务名称"]

输出：JSON 格式，包含 saved_paths / result_urls / error
"""

import json
import os
import sys
import time
import argparse
import requests
from io import BytesIO
from pathlib import Path
from datetime import datetime

# ── 路径推断 ─────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).resolve().parent          # .cursor/skills/.../scripts/
SKILL_DIR    = SCRIPT_DIR.parent                        # .cursor/skills/.../
CURSOR_DIR   = SKILL_DIR.parent.parent                  # .cursor/
PROJECT_ROOT = CURSOR_DIR.parent                        # 项目根目录
CONFIG_DIR   = PROJECT_ROOT / "config"                  # 项目级配置目录
DEFAULT_OUTPUT_DIR = PROJECT_ROOT / "生成结果输出"

# 可用模型配置：每个模型的端点、独立 base_url（可选）、图片上限、是否支持 resolution
DEFAULT_BASE_URL = "https://www.runninghub.cn/openapi/v2"

MODEL_CONFIGS = {
    "pro": {
        "endpoint":              "rhart-image-n-pro/edit",
        "base_url":              None,   # None → 使用默认 DEFAULT_BASE_URL
        "max_images":            10,
        "supports_resolution":   True,
        "supports_aspect_ratio": True,   # 是否在 payload 中发送 aspectRatio 字段
        "experimental":          False,
        "display_name":          "全能图片PRO（Nano Banana Pro / Gemini 3 Pro Image）",
    },
    "flash": {
        "endpoint":              "rhart-image-n-g31-flash/image-to-image",
        "base_url":              None,
        "max_images":            10,
        "supports_resolution":   True,
        "supports_aspect_ratio": True,
        "experimental":          False,
        "display_name":          "Banana2 Flash（Gemini Flash）",
    },
    "gpt-image-2": {
        "endpoint":              "rhart-image-g-2/image-to-image",
        "base_url":              "https://rhtv.runninghub.cn/openapi/v2",
        "max_images":            2,
        "supports_resolution":   False,
        # aspectRatio 官方枚举过窄（仅 2:3/1:1/3:2），不在 payload 中发送，
        # 改由 prompt 文本自然语言传达比例（模型对文字描述的比例更宽容）
        "supports_aspect_ratio": False,
        "experimental":          True,   # 实验性模型：仅用户明确点名时使用
        "display_name":          "GPT-image 2（ChatGPT 系，⚠ 实验性）",
    },
}
DEFAULT_MODEL = "pro"


def get_model_config(model: str) -> dict:
    """根据模型 key 返回配置；未知模型回退到默认 pro。"""
    return MODEL_CONFIGS.get(model, MODEL_CONFIGS[DEFAULT_MODEL])


def resolve_base_url(model: str, global_base_url: str) -> str:
    """返回该模型实际使用的 base_url：模型配置优先，否则用全局 base_url。"""
    cfg = get_model_config(model)
    return (cfg.get("base_url") or "").strip() or global_base_url

# ── RunningHub 错误码字典 ─────────────────────────────────────────────────────
# 来源：https://www.runninghub.cn/runninghub-api-doc-cn/doc-8287338
RH_ERROR_MESSAGES: dict[int, str] = {
    1011: "系统繁忙（模型负载较高），请稍后重试",
    1001: "API Key 无效或已过期",
    1002: "账户余额不足",
    1003: "请求参数错误",
    1004: "图片格式不支持",
    1005: "图片尺寸超限",
    1006: "并发任务数达到上限",
    1010: "内容违规，请修改提示词",
}

# 遇到这些错误码时自动等待重试（非致命，属于临时性服务状态）
RH_RETRYABLE_CODES: set[int] = {1011, 1006}
# 1011 = 系统繁忙；1006 = 并发上限，等一会也会释放


def _rh_error_display(code, message: str = "") -> str:
    """将 RunningHub errorCode 转为可读的中文描述。"""
    try:
        code_int = int(code)
    except (TypeError, ValueError):
        return str(code) if code else (message or "未知错误")
    known = RH_ERROR_MESSAGES.get(code_int, "")
    if known:
        return f"错误码 {code_int}：{known}"
    if message:
        return f"错误码 {code_int}：{message}"
    return f"错误码 {code_int}（含义未收录，可查阅 RunningHub 官方错误码文档）"


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
    """读取 config/.env 中 RH_API_MAX_POLLING_TIME；无效或未设置时默认 600。"""
    raw = _get("RH_API_MAX_POLLING_TIME", "")
    if raw:
        try:
            return max(30, int(raw.strip()))
        except ValueError:
            pass
    return 600


def get_poll_interval_seconds() -> float:
    """读取 RH_API_POLLING_INTERVAL；无效或未设置时默认 5.0 秒。"""
    raw = _get("RH_API_POLLING_INTERVAL", "")
    if raw:
        try:
            return max(1.0, min(60.0, float(raw.strip().replace(",", "."))))
        except ValueError:
            pass
    return 5.0


# ── 图片上传 ──────────────────────────────────────────────────────────────────

def upload_image(file_path: Path, api_key: str, base_url: str, timeout: int = 60) -> str:
    """上传本地图片到 RH OSS，返回下载 URL。"""
    suffix    = file_path.suffix.lower()
    mime_map  = {".jpg": "image/jpeg", ".jpeg": "image/jpeg",
                 ".png": "image/png",  ".webp": "image/webp"}
    mime_type = mime_map.get(suffix, "image/jpeg")
    url       = f"{base_url.rstrip('/')}/media/upload/binary"
    headers   = {"Authorization": f"Bearer {api_key}"}

    for attempt in range(3):
        if attempt:
            time.sleep(min(2 ** attempt, 30))
        try:
            files = {"file": (file_path.name, file_path.read_bytes(), mime_type)}
            resp  = requests.post(url, headers=headers, files=files, timeout=timeout)
            data  = resp.json() if resp.text else {}
            if resp.status_code != 200:
                if resp.status_code >= 500 or resp.status_code == 429:
                    continue
                raise RuntimeError(f"上传 HTTP {resp.status_code}: {data.get('message', '')}")
            if data.get("code") != 0:
                raise RuntimeError(data.get("message", "上传失败"))
            dl_url = (data.get("data") or {}).get("download_url")
            if not dl_url:
                raise RuntimeError("响应中无 download_url")
            return dl_url
        except requests.RequestException as e:
            if attempt == 2:
                raise RuntimeError(f"网络错误: {e}")
    raise RuntimeError("上传失败：已重试 3 次")


# ── API 任务提交与轮询 ────────────────────────────────────────────────────────

def submit_task(payload: dict, api_key: str, base_url: str,
                timeout: int = 60, model: str = DEFAULT_MODEL) -> str:
    endpoint   = get_model_config(model)["endpoint"]
    url        = f"{base_url.rstrip('/')}/{endpoint}"
    headers    = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
    max_tries  = 3   # 可重试错误码（1011/1006）最多重试 3 次
    base_wait  = 30  # 可重试错误首次等待秒数，之后每次 +15s

    for attempt in range(max_tries):
        if attempt:
            # 网络/HTTP 错误用指数退避；可重试 API 错误用固定步进等待
            pass
        try:
            resp = requests.post(url, headers=headers, json=payload, timeout=timeout)
            data = resp.json() if resp.text else {}

            if resp.status_code != 200:
                if resp.status_code in (429, 503) or resp.status_code >= 500:
                    wait = min(2 ** attempt + 1, 30)
                    print(f"  [提交] HTTP {resp.status_code}，{wait}s 后重试 (attempt {attempt+1}/{max_tries})...",
                          file=sys.stderr)
                    time.sleep(wait)
                    continue
                raise RuntimeError(f"提交 HTTP {resp.status_code}: {data.get('errorMessage', '')}")

            err_code = data.get("errorCode")
            err_msg  = data.get("errorMessage") or ""

            if err_code:
                try:
                    code_int = int(err_code)
                except (TypeError, ValueError):
                    code_int = -1

                if code_int in RH_RETRYABLE_CODES:
                    wait = base_wait + attempt * 15
                    display = _rh_error_display(code_int, err_msg)
                    print(f"  [提交] {display}，等待 {wait}s 后重试 (attempt {attempt+1}/{max_tries})...",
                          file=sys.stderr)
                    time.sleep(wait)
                    continue

                raise RuntimeError(f"提交失败：{_rh_error_display(err_code, err_msg)}")

            if err_msg and not err_code:
                raise RuntimeError(f"提交失败：{err_msg}")

            task_id = data.get("taskId") or data.get("task_id")
            if not task_id:
                raise RuntimeError("响应中无 taskId")
            return str(task_id)

        except requests.RequestException as e:
            if attempt == max_tries - 1:
                raise RuntimeError(f"网络错误: {e}")
            wait = min(2 ** attempt + 1, 15)
            print(f"  [提交] 网络异常 ({e})，{wait}s 后重试...", file=sys.stderr)
            time.sleep(wait)

    raise RuntimeError(f"提交失败：已重试 {max_tries} 次仍遭遇系统繁忙，可能为供应商侧问题，建议稍后手动重试")


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
        err_code = data.get("errorCode")
        err_msg  = data.get("errorMessage") or ""

        if err_code:
            try:
                code_int = int(err_code)
            except (TypeError, ValueError):
                code_int = -1

            if code_int in RH_RETRYABLE_CODES:
                # 可重试错误：打印提示，继续轮询（等待后会自动重新查询）
                display = _rh_error_display(code_int, err_msg)
                elapsed = int(time.time() - start)
                print(f"  [轮询] {display}，继续等待... (已等待 {elapsed}s)", file=sys.stderr)
                time.sleep(30)  # 系统繁忙时额外等待 30s 再轮询
                continue

            raise RuntimeError(f"任务失败：{_rh_error_display(err_code, err_msg)}")

        if err_msg and not err_code:
            raise RuntimeError(f"任务失败：{err_msg}")

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
        # CREATE / QUEUED / RUNNING → 继续轮询
        print(f"  [轮询] 状态={status} 已等待 {int(time.time()-start)}s ...", file=sys.stderr)


def download_image(url: str, save_path: Path, timeout: int = 60):
    resp = requests.get(url, timeout=timeout)
    resp.raise_for_status()
    save_path.parent.mkdir(parents=True, exist_ok=True)
    save_path.write_bytes(resp.content)


# ── 主流程 ────────────────────────────────────────────────────────────────────

def run(images: list, prompt: str, aspect_ratio: str, resolution: str,
        output_dir: Path, label: str, max_poll_seconds: int = 600,
        model: str = DEFAULT_MODEL) -> dict:

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

    if model not in MODEL_CONFIGS:
        return {"success": False, "error": f"未知模型: {model}，可选: {list(MODEL_CONFIGS.keys())}"}

    cfg            = get_model_config(model)
    model_base_url = resolve_base_url(model, base_url)
    max_images     = cfg["max_images"]

    if cfg.get("experimental"):
        print(
            f"  [实验性模型] 当前使用 {model}（{cfg['display_name']}）。"
            f"该模型 API 功能不完善、稳定性待验证，如非显式指定，建议改用默认的 --model pro。",
            file=sys.stderr,
        )

    if not images:
        return {"success": False, "error": "至少需要提供一张参考图片"}

    if len(images) > max_images:
        return {
            "success": False,
            "error": f"模型 {model} 最多支持 {max_images} 张参考图片，当前传入 {len(images)} 张",
        }

    # 1. 验证图片路径
    img_paths = []
    for p in images:
        path = Path(p)
        if not path.is_absolute():
            path = PROJECT_ROOT / p
        if not path.exists():
            return {"success": False, "error": f"图片不存在: {path}"}
        img_paths.append(path)

    # 2. 上传图片（上传接口固定使用默认 www 域，OSS 返回的 URL 对各模型端点均通用）
    print(f"[1/4] 上传 {len(img_paths)} 张参考图片...", file=sys.stderr)
    image_urls = []
    for i, path in enumerate(img_paths):
        print(f"  上传 {path.name} ({i+1}/{len(img_paths)}) ...", file=sys.stderr)
        url = upload_image(path, api_key, base_url)
        image_urls.append(url)
        print(f"  已上传: {url[:60]}...", file=sys.stderr)

    # 3. 构建 payload（aspectRatio / resolution 仅在模型支持时加入）
    payload: dict = {
        "imageUrls": image_urls,
        "prompt":    prompt,
    }
    if cfg["supports_aspect_ratio"]:
        payload["aspectRatio"] = aspect_ratio
    elif aspect_ratio:
        print(
            f"  [提示] 模型 {model} 的 aspectRatio 枚举过窄，已省略该字段；"
            f"请在 prompt 中用文字说明想要的比例（例如 'aspect ratio 21:9' / '比例 21:9'）。"
            f"当前 --aspect-ratio='{aspect_ratio}' 未写入 payload。",
            file=sys.stderr,
        )
    if cfg["supports_resolution"]:
        payload["resolution"] = resolution
    elif resolution:
        print(f"  [提示] 模型 {model} 不支持 resolution 参数，已忽略传入的 '{resolution}'",
              file=sys.stderr)

    # 4. 提交任务
    print(f"[2/4] 提交生图任务（模型: {cfg['display_name']}）...", file=sys.stderr)
    print(f"  endpoint: {model_base_url.rstrip('/')}/{cfg['endpoint']}", file=sys.stderr)
    print(f"  prompt: {prompt[:80]}{'...' if len(prompt)>80 else ''}", file=sys.stderr)
    info_parts = [f"model={model}"]
    if cfg["supports_aspect_ratio"]:
        info_parts.insert(0, f"aspectRatio={aspect_ratio}")
    if cfg["supports_resolution"]:
        info_parts.insert(-1 if len(info_parts) > 1 else 0, f"resolution={resolution}")
    print(f"  " + "  ".join(info_parts), file=sys.stderr)
    task_id = submit_task(payload, api_key, model_base_url, model=model)
    print(f"  taskId={task_id}", file=sys.stderr)

    # 5. 轮询结果（与提交使用同一 base_url，确保 gpt-image-2 在 rhtv 子域查询）
    print(f"[3/4] 等待生图完成（最长 {max_poll_seconds}s）...", file=sys.stderr)
    result_urls = poll_task(
        task_id, api_key, model_base_url,
        interval=get_poll_interval_seconds(),
        max_time=max_poll_seconds,
    )
    print(f"  生图完成，获得 {len(result_urls)} 张图片", file=sys.stderr)

    # 6. 下载保存
    print(f"[4/4] 下载保存图片...", file=sys.stderr)
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
        "model":        model,
        "endpoint":     cfg["endpoint"],
        "base_url":     model_base_url,
    }


# ── CLI 入口 ──────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RH 全能图片PRO-图生图 CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "可用模型（--model）:\n"
            "  pro          (默认) 全能图片PRO：细节精准，适合产品精修与最终出图。\n"
            "               最多 10 张参考图，支持 resolution 1k/2k/4k。\n"
            "  flash        Banana2 Flash：价格低、特征保留强，适合批量创意/pro 繁忙备用。\n"
            "               最多 10 张参考图，支持 resolution 1k/2k/4k。\n"
            "  gpt-image-2  [实验性] GPT-image 2（ChatGPT 系）：仅在用户明确点名时使用，\n"
            "               API 功能不完善、稳定性待验证。\n"
            "               最多 2 张参考图；不支持 resolution；aspectRatio 枚举过窄，\n"
            "               已不写入 payload，请在 prompt 中用文字表达比例（例如\n"
            "               'aspect ratio 21:9' / '比例 21:9'）。"
        )
    )
    parser.add_argument("--images",       nargs="+", required=True,
                        help="参考图片路径（可多张，支持绝对路径或相对于项目根目录的路径）")

    # --prompt 与 --prompt-file 二选一
    prompt_group = parser.add_mutually_exclusive_group(required=True)
    prompt_group.add_argument("--prompt",
                        help="图像描述提示词（英文效果最佳）。"
                             "⚠️ PowerShell 中 $ 会被展开为变量，含 $ 符号时请改用 --prompt-file。")
    prompt_group.add_argument("--prompt-file",
                        help="从 UTF-8 文本文件读取提示词（推荐：彻底避免 PowerShell/cmd 特殊字符转义问题）。"
                             "路径可为绝对路径或相对于项目根目录的路径。")
    parser.add_argument("--model",        default=DEFAULT_MODEL,
                        choices=list(MODEL_CONFIGS.keys()),
                        help="生图模型：pro（默认，细节精准）/ flash（价格低，批量创意）/ "
                             "gpt-image-2（[实验性] 仅用户明确点名时使用）")
    parser.add_argument("--aspect-ratio", default="3:4",
                        choices=["1:1","16:9","9:16","4:3","3:4","3:2","2:3","5:4","4:5","21:9"],
                        help="输出图片比例（默认 3:4；gpt-image-2 不接受该字段，"
                             "请改在 prompt 中用文字写明比例，此处传入会被忽略）")
    parser.add_argument("--resolution",   default="2k",
                        choices=["1k","2k","4k"],
                        help="输出分辨率（默认 2k；gpt-image-2 暂不支持，传入会被忽略）")
    parser.add_argument("--output-dir",   default=str(DEFAULT_OUTPUT_DIR),
                        help="图片保存根目录")
    parser.add_argument("--label",        default="",
                        help="输出文件名标签（留空则使用 prompt 前 30 字）")
    parser.add_argument("--max-poll-seconds", type=int, default=None,
                        help="轮询等待最长时间（秒）；省略时读取 config/.env 的 RH_API_MAX_POLLING_TIME，未配置则 600")
    args = parser.parse_args()

    # 解析 prompt：优先 --prompt-file，其次 --prompt
    if args.prompt_file:
        pf = Path(args.prompt_file)
        if not pf.is_absolute():
            pf = PROJECT_ROOT / pf
        if not pf.exists():
            print(json.dumps({"success": False, "error": f"prompt-file 不存在: {pf}"}, ensure_ascii=False))
            sys.exit(1)
        prompt_text = pf.read_text(encoding="utf-8").strip()
        if not prompt_text:
            print(json.dumps({"success": False, "error": f"prompt-file 内容为空: {pf}"}, ensure_ascii=False))
            sys.exit(1)
    else:
        prompt_text = args.prompt

    max_poll = (
        args.max_poll_seconds
        if args.max_poll_seconds is not None
        else get_default_max_poll_seconds()
    )

    result = run(
        images      = args.images,
        prompt      = prompt_text,
        aspect_ratio= args.aspect_ratio,
        resolution  = args.resolution,
        output_dir  = Path(args.output_dir),
        label       = args.label,
        max_poll_seconds=max_poll,
        model       = args.model,
    )

    # 输出 JSON 结果
    print(json.dumps(result, ensure_ascii=False, indent=2))
    sys.exit(0 if result.get("success") else 1)


if __name__ == "__main__":
    main()
