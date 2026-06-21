"""
Phase 0 · 参考库档案扫描器(使用统一切片模块)
==============================================

扫描参考库、P域、品牌规范,按 chunking.py 的智能切片策略切成 embedding 单元,
统计质量分布、估算费用,生成现状报告。

不调用任何 API。

用法:
    python 工具/向量检索/scan_archives.py
"""

from __future__ import annotations

import json
import re
import sys
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterator

# 强制 UTF-8 输出(Windows PowerShell GBK 兼容)
try:
    sys.stdout.reconfigure(encoding="utf-8")
    sys.stderr.reconfigure(encoding="utf-8")
except Exception:
    pass

# 引入统一切片模块
sys.path.insert(0, str(Path(__file__).resolve().parent))
from chunking import Chunk, chunk_file, estimate_tokens  # noqa: E402

# ----------------------------------------------------------------------------
# 路径
# ----------------------------------------------------------------------------
SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = SCRIPT_DIR.parent.parent
REF_LIB = PROJECT_ROOT / "参考库"
BRAND_LIB = PROJECT_ROOT / "品牌规范"
MODULES_LIB = PROJECT_ROOT / "能力模块"  # [已弃用] M1-M18 于 V8.0 转为 .cursor/skills/,目录已归档
SCENE_KB_LIB = PROJECT_ROOT / "场景知识库"
OUTPUT_DIR = SCRIPT_DIR / "vector_index"
REPORT_PATH = OUTPUT_DIR / "scan_report.json"
REPORT_MD_PATH = OUTPUT_DIR / "scan_report.md"

# 跳过的顶层子目录(这些不需要 embed)
SKIP_DIRS = {"00_待学习", "00_待入库", "原始素材", "字体文件"}

# 品牌规范里要跳过的子目录
SKIP_IN_BRAND = {"_品牌目录模板"}

PRICE_PER_MILLION_TOKENS = 0.28  # CNY


# ----------------------------------------------------------------------------
# 数据
# ----------------------------------------------------------------------------
@dataclass
class DomainStats:
    domain: str
    file_count: int = 0
    chunk_count: int = 0
    skipped_files: int = 0        # STUB 或 INDEX(超长) 跳过
    total_chars: int = 0
    total_tokens: int = 0
    quality_short: int = 0        # < 200 字
    quality_ok: int = 0           # 200 - 8K tokens
    quality_long: int = 0         # > 8K tokens
    by_type: dict = None          # 记录各文件类型的块数

    def __post_init__(self):
        if self.by_type is None:
            self.by_type = defaultdict(int)


# ----------------------------------------------------------------------------
# 工具
# ----------------------------------------------------------------------------
def read_file_safely(path: Path) -> str | None:
    for enc in ("utf-8", "utf-8-sig", "gbk"):
        try:
            return path.read_text(encoding=enc)
        except UnicodeDecodeError:
            continue
        except Exception as e:
            print(f"  ! 读取失败 {path.name}: {e}", file=sys.stderr)
            return None
    return None


def iter_txt_files(root: Path, extra_skip: set[str] = frozenset()) -> Iterator[Path]:
    skip = set(SKIP_DIRS) | set(extra_skip)
    for p in root.rglob("*.txt"):
        parts = set(p.relative_to(root).parts)
        if parts & skip:
            continue
        yield p


def classify_domain_ref(path: Path) -> str:
    rel = path.relative_to(REF_LIB)
    parts = rel.parts
    if not parts:
        return "其他"
    first = parts[0]
    if first.endswith(".txt"):
        return "根目录"
    return first


def process_chunk_into_stats(chunk: Chunk, stat: DomainStats):
    stat.chunk_count += 1
    stat.total_chars += chunk.chars
    stat.total_tokens += chunk.est_tokens
    stat.by_type[chunk.source_type] += 1
    if chunk.chars < 200:
        stat.quality_short += 1
    elif chunk.est_tokens > 8000:
        stat.quality_long += 1
    else:
        stat.quality_ok += 1


# ----------------------------------------------------------------------------
# 扫描
# ----------------------------------------------------------------------------
def scan_reference_library() -> tuple[list[Chunk], dict[str, DomainStats]]:
    print(f"\n[1/5] 扫描参考库: {REF_LIB}")
    chunks: list[Chunk] = []
    stats: dict[str, DomainStats] = defaultdict(lambda: DomainStats(domain=""))

    if not REF_LIB.exists():
        print("  ! 不存在,跳过")
        return chunks, dict(stats)

    file_cnt = 0
    skipped_cnt = 0
    for txt in iter_txt_files(REF_LIB):
        domain = classify_domain_ref(txt)
        stats[domain].domain = domain
        stats[domain].file_count += 1
        file_cnt += 1
        content = read_file_safely(txt)
        if content is None:
            stats[domain].skipped_files += 1
            skipped_cnt += 1
            continue
        rel_path = str(txt.relative_to(PROJECT_ROOT))
        file_chunks = chunk_file(txt, content, rel_path, domain)
        if not file_chunks:
            stats[domain].skipped_files += 1
            skipped_cnt += 1
            continue
        for ch in file_chunks:
            chunks.append(ch)
            process_chunk_into_stats(ch, stats[domain])

    print(f"  完成: {file_cnt} 个文件,{skipped_cnt} 个跳过(STUB/过长索引),切出 {len(chunks)} 块")
    return chunks, dict(stats)


def scan_p_domain_cases() -> tuple[list[Chunk], DomainStats]:
    """扫描 P 域每个案例文件夹的 prompt.txt + meta.txt(合并为 1 块)"""
    print("\n[2/5] 扫描 P 域成功案例文件夹...")
    chunks: list[Chunk] = []
    stat = DomainStats(domain="P_成功案例_prompt")
    p_root = REF_LIB / "P_生图成功案例库"
    if not p_root.exists():
        return chunks, stat

    for case_dir in p_root.iterdir():
        if not case_dir.is_dir() or case_dir.name.startswith("00_"):
            continue
        prompt_file = case_dir / "prompt.txt"
        if not prompt_file.exists():
            continue
        meta_file = case_dir / "meta.txt"
        prompt_text = read_file_safely(prompt_file) or ""
        meta_text = read_file_safely(meta_file) or ""
        combined = (
            f"[P 域成功案例: {case_dir.name}]\n\n"
            f"=== meta ===\n{meta_text}\n\n"
            f"=== prompt ===\n{prompt_text}"
        )
        chars = len(combined)
        tokens = estimate_tokens(combined)
        rel = str(case_dir.relative_to(PROJECT_ROOT))
        ch = Chunk(
            source_path=rel,
            source_domain="P_成功案例_prompt",
            source_type="P_CASE",
            chunk_id=f"{case_dir.name}::0",
            chunk_index=0,
            text=combined,
            chars=chars,
            est_tokens=tokens,
        )
        chunks.append(ch)
        stat.file_count += 1
        process_chunk_into_stats(ch, stat)
    print(f"  完成: {stat.file_count} 个案例")
    return chunks, stat


def scan_brand_library() -> tuple[list[Chunk], DomainStats]:
    print(f"\n[3/5] 扫描品牌规范: {BRAND_LIB}")
    chunks: list[Chunk] = []
    stat = DomainStats(domain="品牌规范")
    if not BRAND_LIB.exists():
        return chunks, stat

    for txt in BRAND_LIB.rglob("*.txt"):
        # 跳过模板目录
        if any(p in SKIP_IN_BRAND for p in txt.parts):
            continue
        stat.file_count += 1
        content = read_file_safely(txt)
        if content is None:
            stat.skipped_files += 1
            continue
        rel = str(txt.relative_to(PROJECT_ROOT))
        file_chunks = chunk_file(txt, content, rel, "品牌规范")
        if not file_chunks:
            stat.skipped_files += 1
            continue
        for ch in file_chunks:
            chunks.append(ch)
            process_chunk_into_stats(ch, stat)
    print(f"  完成: {stat.file_count} 个文件,{stat.skipped_files} 跳过,切出 {stat.chunk_count} 块")
    return chunks, stat


def scan_capability_modules() -> tuple[list[Chunk], DomainStats]:
    """[已弃用 · V8.0] 能力模块 M1-M18 已转为 .cursor/skills/ 下的 Skill,
    由 Cursor 原生按需加载,不再纳入向量检索语料。保留空壳以兼容
    build_index / update_index 的导入与调用,始终返回空切片。"""
    print("\n[能力模块] 已弃用(M1-M18 → Skill,V8.0),跳过")
    return [], DomainStats(domain="能力模块")


def scan_scene_knowledge() -> tuple[list[Chunk], DomainStats]:
    """扫描 场景知识库/K1-K4/*.txt(地域/平台/受众/内容类型规范)"""
    print(f"\n[5/5] 扫描场景知识库: {SCENE_KB_LIB}")
    chunks: list[Chunk] = []
    stat = DomainStats(domain="场景知识库")
    if not SCENE_KB_LIB.exists():
        print("  ! 不存在,跳过")
        return chunks, stat

    for txt in SCENE_KB_LIB.rglob("*.txt"):
        stat.file_count += 1
        content = read_file_safely(txt)
        if content is None:
            stat.skipped_files += 1
            continue
        rel = str(txt.relative_to(PROJECT_ROOT))
        file_chunks = chunk_file(txt, content, rel, "场景知识库")
        if not file_chunks:
            stat.skipped_files += 1
            continue
        for ch in file_chunks:
            chunks.append(ch)
            process_chunk_into_stats(ch, stat)
    print(f"  完成: {stat.file_count} 个文件,{stat.skipped_files} 跳过,切出 {stat.chunk_count} 块")
    return chunks, stat


# ----------------------------------------------------------------------------
# 报告
# ----------------------------------------------------------------------------
def build_cost_estimate(total_tokens: int) -> dict:
    cost = total_tokens / 1_000_000 * PRICE_PER_MILLION_TOKENS
    return {
        "total_tokens": total_tokens,
        "total_million_tokens": round(total_tokens / 1_000_000, 4),
        "price_per_m_tokens_cny": PRICE_PER_MILLION_TOKENS,
        "est_cost_cny": round(cost, 4),
        "est_api_calls_batch10": max(1, total_tokens // 5000 + 1),
        "est_duration_seconds": round(max(10, total_tokens / 1_000_000 * 60), 1),
    }


def print_summary(all_stats: dict[str, DomainStats], total_chunks: int) -> dict:
    total_tokens = sum(s.total_tokens for s in all_stats.values())
    total_chars = sum(s.total_chars for s in all_stats.values())
    total_files = sum(s.file_count for s in all_stats.values())
    total_skipped = sum(s.skipped_files for s in all_stats.values())

    print("\n" + "=" * 82)
    print("参考库档案现状报告 (路线 B · 智能切片)")
    print("=" * 82)
    header = f"{'域':<24} {'文件':>5} {'跳过':>5} {'记录':>6} {'字符':>10} {'Tokens':>10} {'短':>4} {'正常':>5} {'长':>4}"
    print(header)
    print("-" * 82)
    for s in sorted(all_stats.values(), key=lambda x: -x.total_tokens):
        if s.file_count == 0:
            continue
        print(
            f"{s.domain:<24} {s.file_count:>5} {s.skipped_files:>5} "
            f"{s.chunk_count:>6} {s.total_chars:>10,} {s.total_tokens:>10,} "
            f"{s.quality_short:>4} {s.quality_ok:>5} {s.quality_long:>4}"
        )
    print("-" * 82)
    total_short = sum(s.quality_short for s in all_stats.values())
    total_ok = sum(s.quality_ok for s in all_stats.values())
    total_long = sum(s.quality_long for s in all_stats.values())
    print(
        f"{'合计':<24} {total_files:>5} {total_skipped:>5} "
        f"{total_chunks:>6} {total_chars:>10,} {total_tokens:>10,} "
        f"{total_short:>4} {total_ok:>5} {total_long:>4}"
    )

    # 类型分布
    type_dist = defaultdict(int)
    for s in all_stats.values():
        for t, c in s.by_type.items():
            type_dist[t] += c

    print("\n" + "=" * 82)
    print("切片类型分布")
    print("=" * 82)
    for t in sorted(type_dist.keys(), key=lambda k: -type_dist[k]):
        print(f"  {t:<14} : {type_dist[t]} 块")

    cost = build_cost_estimate(total_tokens)
    print("\n" + "=" * 82)
    print("费用与耗时估算")
    print("=" * 82)
    print(f"  Embedding Tokens 总量      : {cost['total_tokens']:,} ({cost['total_million_tokens']} M)")
    print(f"  SiliconFlow 单价            : ¥{cost['price_per_m_tokens_cny']}/M tokens")
    print(f"  预计全量首构建费用          : ¥{cost['est_cost_cny']}")
    print(f"  预计 API 调用次数           : ~{cost['est_api_calls_batch10']} 次 (batch=10)")
    print(f"  预计耗时                    : ~{cost['est_duration_seconds']} 秒")

    print("\n" + "=" * 82)
    print("质量分布")
    print("=" * 82)
    quality_rate = total_ok / max(1, total_chunks) * 100
    print(f"  正常记录(200-8K tokens)    : {total_ok:>5} ({quality_rate:.1f}%)")
    print(f"  过短记录(< 200 字)         : {total_short:>5}")
    print(f"  过长记录(> 8K tokens)      : {total_long:>5}  [需二次切分,已在 chunking 中处理]")
    print(f"  跳过文件(STUB / 巨型索引)  : {total_skipped:>5}")

    return {
        "summary": {
            "total_files": total_files,
            "skipped_files": total_skipped,
            "total_chunks": total_chunks,
            "total_chars": total_chars,
            "total_tokens": total_tokens,
            "quality_ok": total_ok,
            "quality_short": total_short,
            "quality_long": total_long,
            "quality_rate": round(quality_rate, 1),
        },
        "domains": {k: {**asdict(v), "by_type": dict(v.by_type)} for k, v in all_stats.items()},
        "type_distribution": dict(type_dist),
        "cost_estimate": cost,
    }


def write_markdown_report(report: dict, all_stats: dict, chunks: list[Chunk]):
    lines = []
    lines.append("# 参考库档案现状报告 (路线 B · 智能切片)\n")
    s = report["summary"]
    c = report["cost_estimate"]
    lines.append("## 总览\n")
    lines.append(f"- 档案文件数: **{s['total_files']}**")
    lines.append(f"- 跳过文件数: {s['skipped_files']}(STUB/巨型索引)")
    lines.append(f"- 切分记录数: **{s['total_chunks']}**")
    lines.append(f"- 总字符数: {s['total_chars']:,}")
    lines.append(f"- 估算 Tokens: **{s['total_tokens']:,}** ({c['total_million_tokens']} M)")
    lines.append(f"- 首次构建费用: **¥{c['est_cost_cny']}** (¥{c['price_per_m_tokens_cny']}/M)")
    lines.append(f"- 预计耗时: ~{c['est_duration_seconds']} 秒")
    lines.append(f"- **正常记录占比**: **{s['quality_rate']}%**\n")

    lines.append("## 各域详情\n")
    lines.append("| 域 | 文件 | 跳过 | 记录 | 字符 | Tokens | 过短 | 正常 | 过长 |")
    lines.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
    for name, st in sorted(all_stats.items(), key=lambda kv: -kv[1].total_tokens):
        if st.file_count == 0:
            continue
        lines.append(
            f"| {st.domain} | {st.file_count} | {st.skipped_files} | {st.chunk_count} | "
            f"{st.total_chars:,} | {st.total_tokens:,} | "
            f"{st.quality_short} | {st.quality_ok} | {st.quality_long} |"
        )

    lines.append("\n## 切片类型分布\n")
    lines.append("| 类型 | 块数 | 说明 |")
    lines.append("|---|---:|---|")
    desc = {
        "RECORD": "参考档案常规记录(主力,质量最高)",
        "PRINCIPLE": "通识原则(已合并小段)",
        "BRAND": "品牌规范章节",
        "MODULE": "能力模块章节(M1-M18)",
        "SCENE_KB": "场景知识库章节(K1-K4)",
        "P_CASE": "P 域案例(prompt+meta 合并)",
        "P_CATALOG": "P 域案例速查表",
        "INDEX": "索引文件摘要",
        "DEFAULT": "默认切片",
    }
    for t, n in sorted(report["type_distribution"].items(), key=lambda kv: -kv[1]):
        lines.append(f"| {t} | {n} | {desc.get(t, '')} |")

    REPORT_MD_PATH.write_text("\n".join(lines), encoding="utf-8")


# ----------------------------------------------------------------------------
# main
# ----------------------------------------------------------------------------
def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    all_chunks: list[Chunk] = []
    all_stats: dict[str, DomainStats] = {}

    ref_chunks, ref_stats = scan_reference_library()
    all_chunks.extend(ref_chunks)
    all_stats.update(ref_stats)

    p_chunks, p_stat = scan_p_domain_cases()
    if p_stat.file_count > 0:
        all_chunks.extend(p_chunks)
        all_stats[p_stat.domain] = p_stat

    brand_chunks, brand_stat = scan_brand_library()
    if brand_stat.file_count > 0:
        all_chunks.extend(brand_chunks)
        all_stats[brand_stat.domain] = brand_stat

    module_chunks, module_stat = scan_capability_modules()
    if module_stat.file_count > 0:
        all_chunks.extend(module_chunks)
        all_stats[module_stat.domain] = module_stat

    scene_chunks, scene_stat = scan_scene_knowledge()
    if scene_stat.file_count > 0:
        all_chunks.extend(scene_chunks)
        all_stats[scene_stat.domain] = scene_stat

    report = print_summary(all_stats, len(all_chunks))
    REPORT_PATH.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    write_markdown_report(report, all_stats, all_chunks)

    print("\n" + "=" * 82)
    print(f"JSON 报告     : {REPORT_PATH.relative_to(PROJECT_ROOT)}")
    print(f"Markdown 报告 : {REPORT_MD_PATH.relative_to(PROJECT_ROOT)}")
    print("=" * 82)


if __name__ == "__main__":
    main()
