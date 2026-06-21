"""
统一切片模块
==============

把参考库 / 品牌规范档案切成 embedding 单元。Phase 0 扫描与 Phase 1 构建共用。

核心策略(file-type router):
  - RECORD     : 按 "--- 记录 #N ---" 分隔,每条独立成块
  - PRINCIPLE  : 按 "## PX-NNN" 分隔,小段自动合并到 >= MIN_CHARS
  - INDEX      : 跳过(目录型内容无检索价值)
  - STUB       : 跳过(已细分的空壳文件)
  - P_CATALOG  : 整个文件 1 块(P 域案例速查表)
  - BRAND      : 按章节切 + 小段合并
  - DEFAULT    : 按常规分隔符切 + 小段合并 + 长段拆分

所有切片都携带档案头元信息(标题/领域),让向量自带上下文。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

# ----------------------------------------------------------------------------
# 参数
# ----------------------------------------------------------------------------
MIN_CHARS = 200               # 记录单元最小字符数(合并阈值)
MAX_TOKENS = 6000             # 记录单元最大 tokens(超过二次切分)
TARGET_TOKENS = 2500          # 长段拆分时的目标长度
STUB_MAX_CHARS = 500          # 低于此且含"已细分"关键词 → STUB
INDEX_MAX_TOKENS = 10_000     # 索引文件若超此大小直接跳过(目录没意义)

# ----------------------------------------------------------------------------
# 文件类型分类
# ----------------------------------------------------------------------------

INDEX_NAME_KEYWORDS = [
    "_域索引", "域索引.txt", "参考索引", "主控助手",
    "通识原则索引", "品牌规范主控", "品牌索引", "使用说明", "归档说明",
    "投放说明", "待入库说明", "注册表", "README",
    "场景知识库主控", "主控中心.txt",
]

STUB_SIGNATURES = ["已细分", "请加载 ", "请加载", "→见", "─见"]


def classify_file(path: Path, content: str) -> str:
    """返回文件类型:INDEX / STUB / PRINCIPLE / P_CATALOG / BRAND / RECORD / DEFAULT"""
    name = path.name
    parts = path.parts

    # 索引类文件(按文件名命中)
    if any(kw in name for kw in INDEX_NAME_KEYWORDS):
        return "INDEX"

    # 已细分空壳:内容极短且含典型提示
    stripped = content.strip()
    if len(stripped) < STUB_MAX_CHARS:
        if any(sig in stripped for sig in STUB_SIGNATURES):
            return "STUB"

    # P 域案例列表子文件(P1_xxx.txt / P2_xxx.txt ...),非 prompt.txt
    if "P_生图成功案例库" in parts and re.match(r"^P\d+_", name):
        return "P_CATALOG"

    # 通识原则
    if "00_通识原则" in parts:
        return "PRINCIPLE"

    # 品牌规范
    if "品牌规范" in parts:
        return "BRAND"

    # 能力模块
    if "能力模块" in parts:
        return "MODULE"

    # 场景知识库
    if "场景知识库" in parts:
        return "SCENE_KB"

    # 人物库 / 场景库索引(已在 INDEX 里,保险)
    if name in {"人物库索引.txt", "场景库索引.txt"}:
        return "INDEX"

    return "RECORD"


# ----------------------------------------------------------------------------
# Token 估算
# ----------------------------------------------------------------------------
def estimate_tokens(text: str) -> int:
    if not text:
        return 0
    chinese = len(re.findall(r"[\u4e00-\u9fff]", text))
    other = len(text) - chinese
    return int(chinese * 1.4 + other * 0.30)


# ----------------------------------------------------------------------------
# 数据类
# ----------------------------------------------------------------------------
@dataclass
class Chunk:
    source_path: str       # 档案相对路径
    source_domain: str     # 域(参考库一级目录或"品牌规范")
    source_type: str       # INDEX/STUB/PRINCIPLE/P_CATALOG/BRAND/RECORD/DEFAULT
    chunk_id: str          # 稳定 ID(source_stem + "/" + index)
    chunk_index: int
    text: str              # 实际待 embed 的文本(含档案头)
    chars: int
    est_tokens: int

    @property
    def preview(self) -> str:
        return self.text.replace("\n", " ")[:80]


# ----------------------------------------------------------------------------
# 工具:档案头提取
# ----------------------------------------------------------------------------
_HEADER_LINE_RE = re.compile(r"^\s*(#+\s*.+|>.*)$")


def extract_archive_header(content: str, max_header_lines: int = 6) -> str:
    """提取档案开头的 markdown 标题/引用块作为上下文头。"""
    lines = content.splitlines()
    header_lines = []
    for ln in lines[:max_header_lines * 2]:
        s = ln.strip()
        if not s:
            if header_lines:
                break
            continue
        if s.startswith("#") or s.startswith(">"):
            header_lines.append(s)
        else:
            break
        if len(header_lines) >= max_header_lines:
            break
    return "\n".join(header_lines)


# ----------------------------------------------------------------------------
# 分隔符正则(按文件类型动态选择)
# ----------------------------------------------------------------------------
# RECORD 类型:"--- 记录 #N · YYYY-MM-DD ---"
RECORD_SPLIT_RE = re.compile(
    r"(?m)^[-─━=]{2,4}\s*记录\s*#?\d+[^-─━=\n]*[-─━=]{2,}\s*$"
)

# PRINCIPLE 类型:"## PN-NNN · 标题"
PRINCIPLE_HEADER_RE = re.compile(r"(?m)^##\s+[PMF]\d+[-·]\S*.*$")

# 通用章节分隔(用于 BRAND / DEFAULT)
GENERIC_CHAPTER_RE = re.compile(
    r"(?m)^(?:"
    r"#{2,4}\s+.+"                    # ## 标题
    r"|[-─━=]{5,}"                    # 长分隔线
    r")\s*$"
)

# 过长段落二次切分:按句末 / 空行
LONG_SEG_SPLIT_RE = re.compile(r"(?:\n\s*\n)|(?<=[。！？!?.])\s+")


# ----------------------------------------------------------------------------
# 核心切片函数
# ----------------------------------------------------------------------------
def _split_by_regex_keep_header(text: str, pattern: re.Pattern) -> list[str]:
    """按分隔符切,但保留分隔符作为下一个片段的起始行。"""
    matches = list(pattern.finditer(text))
    if not matches:
        return [text]
    result = []
    # 第一段(分隔符之前的内容)
    first_end = matches[0].start()
    if first_end > 0:
        head = text[:first_end].strip()
        if head:
            result.append(head)
    # 各段
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        seg = text[start:end].strip()
        if seg:
            result.append(seg)
    return result


def _merge_small(segments: list[str], min_chars: int = MIN_CHARS) -> list[str]:
    """把小于 min_chars 的段落合并到前一段(或后一段)。"""
    if not segments:
        return []
    merged: list[str] = []
    for seg in segments:
        if not merged:
            merged.append(seg)
            continue
        # 若当前段太短 + 合并到前段后不超 MAX → 合并到前段
        if len(seg) < min_chars:
            combined = merged[-1] + "\n\n" + seg
            if estimate_tokens(combined) <= MAX_TOKENS:
                merged[-1] = combined
                continue
        # 若前段太短 + 当前段不大 → 同样合并
        if len(merged[-1]) < min_chars:
            combined = merged[-1] + "\n\n" + seg
            if estimate_tokens(combined) <= MAX_TOKENS:
                merged[-1] = combined
                continue
        merged.append(seg)
    return merged


def _split_too_long(segments: list[str], max_tokens: int = MAX_TOKENS) -> list[str]:
    """对超长段落做二次切分。"""
    result = []
    for seg in segments:
        if estimate_tokens(seg) <= max_tokens:
            result.append(seg)
            continue
        # 切
        sub_parts = LONG_SEG_SPLIT_RE.split(seg)
        buffer = ""
        for part in sub_parts:
            part = part.strip()
            if not part:
                continue
            candidate = (buffer + "\n\n" + part) if buffer else part
            if estimate_tokens(candidate) > TARGET_TOKENS:
                if buffer:
                    result.append(buffer)
                buffer = part
            else:
                buffer = candidate
        if buffer:
            result.append(buffer)
    return result


def _wrap_with_header(text: str, header: str, title: str) -> str:
    """给切片包上档案头上下文。"""
    if header:
        return f"{header}\n\n{text}"
    if title:
        return f"# {title}\n\n{text}"
    return text


# ----------------------------------------------------------------------------
# 入口:按类型切片
# ----------------------------------------------------------------------------
def chunk_file(
    path: Path,
    content: str,
    relative_path: str,
    domain: str,
) -> list[Chunk]:
    """把一个档案文件切成 Chunk 列表。返回空列表 = 不 embed。"""
    content = content.strip()
    if len(content) < 40:
        return []

    ftype = classify_file(path, content)

    # STUB:不 embed
    if ftype == "STUB":
        return []

    # INDEX:整文件 1 块(但限长,避免大索引文件吞掉额度)
    if ftype == "INDEX":
        tokens = estimate_tokens(content)
        if tokens > INDEX_MAX_TOKENS:
            return []
        # 只保留前 1500 tokens 作为目录摘要
        if tokens > 1500:
            content = content[: int(len(content) * 1500 / tokens)]
        return [_make_chunk(path, relative_path, domain, ftype, 0, content, content)]

    # P_CATALOG:整文件 1 块
    if ftype == "P_CATALOG":
        if estimate_tokens(content) > MAX_TOKENS:
            # 超长的案例列表也按 DEFAULT 处理
            pass
        else:
            return [_make_chunk(path, relative_path, domain, ftype, 0, content, content)]

    # 提取档案头(前 6 行的 # 标题和 > 引用)
    header = extract_archive_header(content)
    title = path.stem

    # 按文件类型选分隔符
    if ftype == "RECORD":
        segments = _split_by_regex_keep_header(content, RECORD_SPLIT_RE)
        if len(segments) <= 1:
            segments = _split_by_regex_keep_header(content, GENERIC_CHAPTER_RE)
    elif ftype == "PRINCIPLE":
        segments = _split_by_regex_keep_header(content, PRINCIPLE_HEADER_RE)
    elif ftype in ("BRAND", "P_CATALOG", "MODULE", "SCENE_KB"):
        segments = _split_by_regex_keep_header(content, GENERIC_CHAPTER_RE)
    else:  # DEFAULT
        segments = _split_by_regex_keep_header(content, GENERIC_CHAPTER_RE)

    # 合并短段
    segments = _merge_small(segments, MIN_CHARS)
    # 拆分长段
    segments = _split_too_long(segments, MAX_TOKENS)
    # 最终过滤:丢弃仍然 < 40 字的残段
    segments = [s for s in segments if len(s.strip()) >= 40]

    # 包装档案头
    chunks = []
    for i, seg in enumerate(segments):
        wrapped = _wrap_with_header(seg, header, title)
        chunks.append(_make_chunk(path, relative_path, domain, ftype, i, seg, wrapped))
    return chunks


def _make_chunk(
    path: Path,
    relative_path: str,
    domain: str,
    ftype: str,
    idx: int,
    raw: str,
    wrapped: str,
) -> Chunk:
    return Chunk(
        source_path=relative_path,
        source_domain=domain,
        source_type=ftype,
        chunk_id=f"{path.stem}::{idx}",
        chunk_index=idx,
        text=wrapped,
        chars=len(wrapped),
        est_tokens=estimate_tokens(wrapped),
    )
