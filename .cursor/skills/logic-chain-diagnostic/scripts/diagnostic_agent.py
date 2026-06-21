#!/usr/bin/env python3
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
"""
AI设计师助手 · 智能体逻辑链路诊断引擎
Logic Chain Diagnostic Agent

检查维度：
  D1 文件存在性 — 主控中心引用的所有文件是否真实存在
  D2 模块注册一致性 — 模块目录中的文件与主控中心注册表是否一一对应
  D3 规则引用完整性 — .cursor/rules 中的规则是否引用了真实存在的文件
  D4 Skill 完整性 — 每个 Skill 目录是否有 SKILL.md 和必要脚本
  D5 参考库索引一致性 — 域索引与子文件是否对齐
  D6 品牌目录完整性 — 已注册品牌的目录结构是否完整
  D7 场景知识库覆盖度 — K1-K4 是否有文件
  D8 人物库/场景库索引 — 索引文件是否存在
  D9 调用链路连通性 — 从触发词到模块到输出的完整链路是否可达
  D10 交叉引用一致性 — 规则间相互引用的文件是否都存在
"""

import os
import sys
import re
import json
from pathlib import Path
from datetime import datetime

# ─────────────────────────────────────────
# 配置
# ─────────────────────────────────────────

class DiagnosticConfig:
    """诊断配置 V8.0：双层 Skill 架构（业务 18 + 工具 9）+ 主控中心瘦身 + Rules 精简"""

    CORE_FILES = {
        "主控中心": "主控中心.txt",
    }

    # V8.0：18 个业务 Skill（旧 M1-M18 全量 Skill 化）
    # MODULE_REGISTRY 在 V8.0 中作为"业务 Skill 注册表"，不再指向 .txt 文件
    MODULE_REGISTRY = {
        "M1":  ".cursor/skills/brand-logo-designer/SKILL.md",
        "M2":  ".cursor/skills/color-system-designer/SKILL.md",
        "M3":  ".cursor/skills/typography-designer/SKILL.md",
        "M4":  ".cursor/skills/ui-ux-designer/SKILL.md",
        "M5":  ".cursor/skills/print-poster-designer/SKILL.md",
        "M6":  ".cursor/skills/non-ai-design-reviewer/SKILL.md",
        "M7":  ".cursor/skills/design-proposal-writer/SKILL.md",
        "M8":  ".cursor/skills/ai-image-prompt-builder/SKILL.md",
        "M9":  ".cursor/skills/ai-image-aesthetic-scorer/SKILL.md",
        "M10": ".cursor/skills/reference-library-learner/SKILL.md",
        "M11": ".cursor/skills/market-platform-analyzer/SKILL.md",
        "M12": ".cursor/skills/design-relation-visualizer/SKILL.md",
        "M13": ".cursor/skills/design-requirement-guide/SKILL.md",
        "M14": ".cursor/skills/video-prompt-designer/SKILL.md",
        "M15": ".cursor/skills/detail-page-designer/SKILL.md",
        "M16": ".cursor/skills/ai-image-logic-checker/SKILL.md",
        "M17": ".cursor/skills/brand-spec-learner/SKILL.md",
        "M18": ".cursor/skills/logic-chain-diagnostic/SKILL.md",
    }

    # V8.0：保留的强制 Rule（8 条硬约束 + 4 条流程协调 = 12 条）
    RULE_FILES = [
        ".cursor/rules/ai-designer-assistant.mdc",
        ".cursor/rules/batch-image-concurrent.mdc",
        ".cursor/rules/color-palette-authority.mdc",
        ".cursor/rules/design-must-use-main-control.mdc",
        ".cursor/rules/image-logic-check.mdc",
        ".cursor/rules/mandatory-requirement-guidance.mdc",
        ".cursor/rules/p-domain-save.mdc",
        ".cursor/rules/prompt-hygiene-no-internal-ids.mdc",
        ".cursor/rules/ref-image-must-include.mdc",
        ".cursor/rules/user-color-preferences.mdc",
        ".cursor/rules/vector-search-integration.mdc",
        ".cursor/rules/x-domain-save.mdc",
    ]

    # V8.0：双层 Skill 注册表（业务 18 + 工具 9 = 27，logic-chain-diagnostic 双重身份不重复计数）
    SKILL_DIRS = {
        # ── 业务层 Skill（18 个）
        "brand-logo-designer":          ".cursor/skills/brand-logo-designer/SKILL.md",
        "color-system-designer":        ".cursor/skills/color-system-designer/SKILL.md",
        "typography-designer":          ".cursor/skills/typography-designer/SKILL.md",
        "ui-ux-designer":               ".cursor/skills/ui-ux-designer/SKILL.md",
        "print-poster-designer":        ".cursor/skills/print-poster-designer/SKILL.md",
        "non-ai-design-reviewer":       ".cursor/skills/non-ai-design-reviewer/SKILL.md",
        "design-proposal-writer":       ".cursor/skills/design-proposal-writer/SKILL.md",
        "ai-image-prompt-builder":      ".cursor/skills/ai-image-prompt-builder/SKILL.md",
        "ai-image-aesthetic-scorer":    ".cursor/skills/ai-image-aesthetic-scorer/SKILL.md",
        "reference-library-learner":    ".cursor/skills/reference-library-learner/SKILL.md",
        "market-platform-analyzer":     ".cursor/skills/market-platform-analyzer/SKILL.md",
        "design-relation-visualizer":   ".cursor/skills/design-relation-visualizer/SKILL.md",
        "design-requirement-guide":     ".cursor/skills/design-requirement-guide/SKILL.md",
        "video-prompt-designer":        ".cursor/skills/video-prompt-designer/SKILL.md",
        "detail-page-designer":         ".cursor/skills/detail-page-designer/SKILL.md",
        "ai-image-logic-checker":       ".cursor/skills/ai-image-logic-checker/SKILL.md",
        "brand-spec-learner":           ".cursor/skills/brand-spec-learner/SKILL.md",
        "logic-chain-diagnostic":       ".cursor/skills/logic-chain-diagnostic/SKILL.md",
        # ── 工具层 Skill（8 个，logic-chain-diagnostic 已在业务层注册不重复）
        "ai-persona-architect":         ".cursor/skills/ai-persona-architect/SKILL.md",
        "brand-asset-sheet":            ".cursor/skills/brand-asset-sheet/SKILL.md",
        "color-palette-generator":      ".cursor/skills/color-palette-generator/SKILL.md",
        "layout-reference-analyzer":    ".cursor/skills/layout-reference-analyzer/SKILL.md",
        "nano-banana-prompt-guide":     ".cursor/skills/nano-banana-prompt-guide/SKILL.md",
        "rh-image-pro-img2img":         ".cursor/skills/rh-image-pro-img2img/SKILL.md",
        "rh-image-pro-txt2img":         ".cursor/skills/rh-image-pro-txt2img/SKILL.md",
        "skill-converter":              ".cursor/skills/skill-converter/SKILL.md",
    }

    SKILL_SCRIPTS = {
        "rh-image-pro-img2img": [
            ".cursor/skills/rh-image-pro-img2img/scripts/generate_image.py",
            ".cursor/skills/rh-image-pro-img2img/scripts/brand_asset_sheet.py",
        ],
        "rh-image-pro-txt2img": [
            ".cursor/skills/rh-image-pro-txt2img/scripts/generate_image_t2i.py",
        ],
        "brand-asset-sheet": [
            ".cursor/skills/brand-asset-sheet/scripts/generate_brand_asset_sheet.py",
        ],
        "color-palette-generator": [
            ".cursor/skills/color-palette-generator/scripts/generate_color_palette.py",
        ],
        "logic-chain-diagnostic": [
            ".cursor/skills/logic-chain-diagnostic/scripts/diagnostic_agent.py",
        ],
    }

    REF_LIBRARY_DOMAINS = {
        "A": {"dir": "参考库/A_品牌与Logo",         "archive": "品牌参考档案.txt"},
        "B": {"dir": "参考库/B_配色系统",            "archive": "配色参考档案.txt"},
        "C": {"dir": "参考库/C_排版字体",            "archive": "排版参考档案.txt"},
        "D": {"dir": "参考库/D_UI界面",              "archive": "UI参考档案.txt"},
        "E": {"dir": "参考库/E_平面与海报",          "archive": "平面参考档案.txt"},
        "F": {"dir": "参考库/F_摄影风格",            "archive": "摄影参考档案.txt"},
        "G": {"dir": "参考库/G_插画与图形",          "archive": "插画参考档案.txt"},
        "H": {"dir": "参考库/H_3D与渲染",            "archive": "3D参考档案.txt"},
        "I": {"dir": "参考库/I_动效与视频",          "archive": "动效参考档案.txt"},
        "J": {"dir": "参考库/J_空间与产品",          "archive": "空间产品参考档案.txt"},
        "L": {"dir": "参考库/L_口播文案库",          "archive": "口播文案参考档案.txt"},
        "N": {"dir": "参考库/N_详情页设计",          "archive": None},
        "P": {"dir": "参考库/P_生图成功案例库",      "archive": None},
        "V": {"dir": "参考库/V_视频脚本库",          "archive": None},
        "Z": {"dir": "参考库/Z_禁忌案例",            "archive": "禁忌风格档案.txt"},
    }

    REF_INDEX_FILES = {
        "参考总索引": "参考库/参考索引.txt",
        "通识原则索引": "参考库/00_通识原则/通识原则索引.txt",
        "设计DNA档案": "参考库/00_通识原则/设计DNA档案.txt",
        "人物库索引": "参考库/人物库/人物库索引.txt",
        "场景库索引": "参考库/场景库/场景库索引.txt",
        "P域索引(生图成功案例库)": "参考库/P_生图成功案例库/P_域索引.txt",
    }

    UNIVERSAL_PRINCIPLES = [
        "参考库/00_通识原则/P1_构图与空间分配.txt",
        "参考库/00_通识原则/P2_色彩策略与情绪映射.txt",
        "参考库/00_通识原则/P3_信息层级与视觉引导.txt",
        "参考库/00_通识原则/P4_视觉叙事与符号语言.txt",
        "参考库/00_通识原则/P5_材质光影与质感表达.txt",
        "参考库/00_通识原则/P6_功能可视化与标注系统.txt",
        "参考库/00_通识原则/P7_受众心理与转化工程.txt",
    ]

    SCENE_KNOWLEDGE = {
        "场景知识库主控": "场景知识库/场景知识库主控.txt",
        "K1_地域市场": "场景知识库/K1_地域市场/",
        "K2_电商与平台": "场景知识库/K2_电商与平台/",
        "K3_受众画像": "场景知识库/K3_受众画像/",
        "K4_内容类型": "场景知识库/K4_内容类型/",
    }

    BRAND_SPEC = {
        "品牌规范主控": "品牌规范/品牌规范主控.txt",
        "品牌目录模板": "品牌规范/_品牌目录模板/",
    }

    BRAND_TEMPLATE_FILES = [
        "品牌档案.txt",
        "品牌索引.txt",
        "视觉系统/Logo系统.txt",
        "视觉系统/品牌语气.txt",
        "视觉系统/字体系统.txt",
        "视觉系统/影像风格.txt",
        "视觉系统/禁忌清单.txt",
        "视觉系统/版式规范.txt",
        "视觉系统/色彩系统.txt",
    ]

    PERSON_LIBRARY_SUBDIRS = ["东亚", "欧美_白皙", "欧美_橄榄肤", "南亚", "深色肤"]
    SCENE_LIBRARY_SUBDIRS = ["室内", "户外", "纯色渐变", "商业场景"]

    # V8.0：触发词到 Skill 名的映射（用于链路检查 D11）
    TRIGGER_ROUTES = {
        "logo|标志|品牌|VI|视觉识别|商标":         "brand-logo-designer",
        "配色|颜色|色彩|色调|色值|色板":           "color-system-designer",
        "字体|排版|字号|行高|字重|版式":           "typography-designer",
        "APP|界面|交互|原型|组件|按钮|页面":       "ui-ux-designer",
        "印刷海报|折页|展架|易拉宝|名片":          "print-poster-designer",
        "评审|改稿|Figma评审|印前":                "non-ai-design-reviewer",
        "提案|汇报|PPT|方案|说服客户":             "design-proposal-writer",
        "生成|生图|图生图|文生图|海报|Banner":     "ai-image-prompt-builder",
        "评估这张图|审美评分|对比评估":             "ai-image-aesthetic-scorer",
        "开始学习|继续学习|学习素材":               "reference-library-learner",
        "场景分析|目标市场|平台规范":               "market-platform-analyzer",
        "可视化|关系图谱|知识图谱|结构图":          "design-relation-visualizer",
        "需求引导|不知道怎么开始|帮我想想":          "design-requirement-guide",
        "视频|分镜|口播|可灵|Kling|TikTok":        "video-prompt-designer",
        "详情页|listing|A\\+|宝贝详情":             "detail-page-designer",
        "学习品牌|初始化品牌|创建品牌":             "brand-spec-learner",
        "检查系统|诊断链路|系统巡检|全面诊断":      "logic-chain-diagnostic",
    }

    # V8.0：规则间互相引用关系（V8.0 已合并 6 条 Rule，剩余引用关系简化）
    RULE_CROSS_REFS = {
        "design-must-use-main-control.mdc": [
            "mandatory-requirement-guidance.mdc",
            "ref-image-must-include.mdc",
            "image-logic-check.mdc",
        ],
        "image-logic-check.mdc": [
            "design-must-use-main-control.mdc",
        ],
        "ref-image-must-include.mdc": [
            "image-logic-check.mdc",
        ],
        "color-palette-authority.mdc": [
            "image-logic-check.mdc",
        ],
        "user-color-preferences.mdc": [
            "color-palette-authority.mdc",
            "image-logic-check.mdc",
        ],
        "vector-search-integration.mdc": [
            "p-domain-save.mdc",
        ],
    }

    # V8.0：主控中心主流程阶段门（指向 V8.0 Skill 路径）
    MAIN_FLOW_GATES = {
        "①_主控中心":           ["主控中心.txt"],
        "②_需求引导":           [".cursor/skills/design-requirement-guide/SKILL.md"],
        "③_场景分析":           [".cursor/skills/market-platform-analyzer/SKILL.md"],
        "④_配色协同(可选)":     [".cursor/skills/color-system-designer/SKILL.md"],
        "⑤_排版协同(可选)":     [".cursor/skills/typography-designer/SKILL.md"],
        "⑥_构图协同(可选)":     [".cursor/skills/print-poster-designer/SKILL.md"],
        "⑦_AI生图Prompt构造":  [".cursor/skills/ai-image-prompt-builder/SKILL.md"],
        "⑦.5_品牌资产合成":     [".cursor/skills/brand-asset-sheet/SKILL.md"],
        "⑦.6_色卡渲染(可选)":   [".cursor/skills/color-palette-generator/SKILL.md"],
        "⑦.9_版式分析(可选)":   [".cursor/skills/layout-reference-analyzer/SKILL.md"],
        "⑧_PreGen逻辑检查":    [".cursor/skills/ai-image-logic-checker/SKILL.md"],
        "⑨_调用生图":           [".cursor/skills/rh-image-pro-img2img/SKILL.md"],
        "⑩_PostGen逻辑检查":   [".cursor/skills/ai-image-logic-checker/SKILL.md"],
        "⑪_审美评分":           [".cursor/skills/ai-image-aesthetic-scorer/SKILL.md"],
    }


# ─────────────────────────────────────────
# 诊断引擎
# ─────────────────────────────────────────

class DiagnosticResult:
    """单条诊断结果"""
    def __init__(self, dimension: str, item: str, status: str, detail: str = ""):
        self.dimension = dimension
        self.item = item
        self.status = status   # ✅ / ⚠️ / ❌
        self.detail = detail

    def __repr__(self):
        return f"{self.status} [{self.dimension}] {self.item}: {self.detail}"


class DiagnosticEngine:
    """智能体逻辑链路诊断引擎"""

    def __init__(self, root_path: str):
        self.root = Path(root_path)
        self.config = DiagnosticConfig()
        self.results: list[DiagnosticResult] = []
        self.stats = {"pass": 0, "warn": 0, "fail": 0}

    def _exists(self, rel_path: str) -> bool:
        full = self.root / rel_path
        return full.exists()

    def _is_dir(self, rel_path: str) -> bool:
        full = self.root / rel_path
        return full.is_dir()

    def _add(self, dim: str, item: str, status: str, detail: str = ""):
        self.results.append(DiagnosticResult(dim, item, status, detail))
        if status == "✅":
            self.stats["pass"] += 1
        elif status == "⚠️":
            self.stats["warn"] += 1
        else:
            self.stats["fail"] += 1

    # ─── D1：核心文件存在性 ───
    def check_d1_core_files(self):
        dim = "D1-核心文件"
        for name, path in self.config.CORE_FILES.items():
            if self._exists(path):
                self._add(dim, name, "✅", f"文件存在: {path}")
            else:
                self._add(dim, name, "❌", f"文件缺失: {path}")

    # ─── D2：模块注册一致性 ───
    def check_d2_module_registry(self):
        dim = "D2-模块注册"

        # 检查注册表中的文件是否都存在
        for mid, path in self.config.MODULE_REGISTRY.items():
            if self._exists(path):
                self._add(dim, mid, "✅", f"模块文件存在: {path}")
            else:
                self._add(dim, mid, "❌", f"模块文件缺失: {path}")

        # V8.0：检查 .cursor/skills/ 中是否有未注册的业务 Skill
        # （旧 V7.9 检查"能力模块/"目录，V8.0 已 Skill 化）
        skills_dir = self.root / ".cursor" / "skills"
        if skills_dir.is_dir():
            registered_skill_paths = set(self.config.MODULE_REGISTRY.values())
            registered_skill_paths.update(self.config.SKILL_DIRS.values())
            for sub in skills_dir.iterdir():
                if sub.is_dir():
                    skill_md = sub / "SKILL.md"
                    if skill_md.exists():
                        rel = f".cursor/skills/{sub.name}/SKILL.md"
                        if rel not in registered_skill_paths:
                            self._add(dim, f"未注册 Skill: {sub.name}", "⚠️",
                                      "Skill 目录存在但未在配置注册表中")

    # ─── D3：规则文件完整性 ───
    def check_d3_rule_files(self):
        dim = "D3-规则文件"
        for path in self.config.RULE_FILES:
            if self._exists(path):
                self._add(dim, Path(path).stem, "✅", f"规则文件存在: {path}")
            else:
                self._add(dim, Path(path).stem, "❌", f"规则文件缺失: {path}")

        # 检查目录中是否有未注册的规则
        rule_dir = self.root / ".cursor" / "rules"
        if rule_dir.is_dir():
            registered = set(Path(p).name for p in self.config.RULE_FILES)
            for f in rule_dir.iterdir():
                if f.is_file() and f.suffix == ".mdc" and f.name not in registered:
                    self._add(dim, f"未注册规则: {f.name}", "⚠️",
                              "规则文件存在但未在诊断配置中注册")

    # ─── D4：Skill 完整性 ───
    def check_d4_skills(self):
        dim = "D4-Skill完整性"
        for name, skill_path in self.config.SKILL_DIRS.items():
            if self._exists(skill_path):
                self._add(dim, f"{name}/SKILL.md", "✅", "Skill 入口文件存在")
            else:
                self._add(dim, f"{name}/SKILL.md", "❌", f"Skill 入口缺失: {skill_path}")

        for skill_name, scripts in self.config.SKILL_SCRIPTS.items():
            for script_path in scripts:
                if self._exists(script_path):
                    self._add(dim, f"{skill_name}/{Path(script_path).name}", "✅", "脚本存在")
                else:
                    self._add(dim, f"{skill_name}/{Path(script_path).name}", "❌",
                              f"关键脚本缺失: {script_path}")

        # 检查未注册的 Skill 目录
        skills_dir = self.root / ".cursor" / "skills"
        if skills_dir.is_dir():
            registered = set(self.config.SKILL_DIRS.keys())
            for d in skills_dir.iterdir():
                if d.is_dir() and d.name not in registered:
                    skill_md = d / "SKILL.md"
                    if skill_md.exists():
                        self._add(dim, f"未注册Skill: {d.name}", "⚠️",
                                  "Skill 目录存在但未在诊断配置中注册")
                    else:
                        self._add(dim, f"无效Skill目录: {d.name}", "⚠️",
                                  "目录存在但无 SKILL.md 入口文件")

    # ─── D5：参考库索引一致性 ───
    def check_d5_ref_library(self):
        dim = "D5-参考库"

        # 索引文件
        for name, path in self.config.REF_INDEX_FILES.items():
            if self._exists(path):
                self._add(dim, name, "✅", f"索引文件存在: {path}")
            else:
                self._add(dim, name, "❌", f"索引文件缺失: {path}")

        # 域目录和档案文件
        for code, info in self.config.REF_LIBRARY_DOMAINS.items():
            domain_dir = info["dir"]
            if self._is_dir(domain_dir):
                self._add(dim, f"{code}域目录", "✅", f"目录存在: {domain_dir}")
            else:
                self._add(dim, f"{code}域目录", "❌", f"目录缺失: {domain_dir}")
                continue

            # 域索引
            index_file = f"{domain_dir}/{code}_域索引.txt"
            if self._exists(index_file):
                self._add(dim, f"{code}域索引", "✅", f"域索引存在: {index_file}")
            else:
                if code in ("A", "I", "Z"):
                    self._add(dim, f"{code}域索引", "⚠️",
                              f"{code}域无域索引文件（部分域可能设计上不需要）")
                else:
                    self._add(dim, f"{code}域索引", "⚠️", f"域索引缺失: {index_file}")

            # 参考档案
            if info["archive"]:
                archive_path = f"{domain_dir}/{info['archive']}"
                if self._exists(archive_path):
                    self._add(dim, f"{code}域参考档案", "✅", f"档案存在: {archive_path}")
                else:
                    self._add(dim, f"{code}域参考档案", "❌", f"档案缺失: {archive_path}")

        # 通识原则文件
        for path in self.config.UNIVERSAL_PRINCIPLES:
            name = Path(path).stem
            if self._exists(path):
                self._add(dim, name, "✅", f"通识原则文件存在")
            else:
                self._add(dim, name, "❌", f"通识原则文件缺失: {path}")

    # ─── D6：品牌目录完整性 ───
    def check_d6_brand_spec(self):
        dim = "D6-品牌规范"

        # 主控文件
        for name, path in self.config.BRAND_SPEC.items():
            if path.endswith("/"):
                if self._is_dir(path.rstrip("/")):
                    self._add(dim, name, "✅", f"目录存在: {path}")
                else:
                    self._add(dim, name, "❌", f"目录缺失: {path}")
            else:
                if self._exists(path):
                    self._add(dim, name, "✅", f"文件存在: {path}")
                else:
                    self._add(dim, name, "❌", f"文件缺失: {path}")

        # 模板完整性
        template_dir = "品牌规范/_品牌目录模板"
        for tpl_file in self.config.BRAND_TEMPLATE_FILES:
            full_tpl = f"{template_dir}/{tpl_file}"
            if self._exists(full_tpl):
                self._add(dim, f"模板/{tpl_file}", "✅", "模板文件存在")
            else:
                self._add(dim, f"模板/{tpl_file}", "❌", f"模板文件缺失: {full_tpl}")

        # 已注册品牌检查
        brand_dir = self.root / "品牌规范"
        if brand_dir.is_dir():
            for d in brand_dir.iterdir():
                if d.is_dir() and d.name != "_品牌目录模板" and not d.name.startswith("."):
                    brand_name = d.name
                    for tpl_file in self.config.BRAND_TEMPLATE_FILES:
                        brand_file = f"品牌规范/{brand_name}/{tpl_file}"
                        if self._exists(brand_file):
                            self._add(dim, f"{brand_name}/{tpl_file}", "✅", "品牌文件存在")
                        else:
                            self._add(dim, f"{brand_name}/{tpl_file}", "❌",
                                      f"品牌文件缺失: {brand_file}")

    # ─── D7：场景知识库覆盖度 ───
    def check_d7_scene_knowledge(self):
        dim = "D7-场景知识库"
        for name, path in self.config.SCENE_KNOWLEDGE.items():
            if path.endswith("/"):
                dir_path = path.rstrip("/")
                if self._is_dir(dir_path):
                    dir_full = self.root / dir_path
                    txt_files = [f for f in dir_full.iterdir() if f.suffix == ".txt"]
                    if txt_files:
                        self._add(dim, name, "✅", f"目录含 {len(txt_files)} 个知识文件")
                    else:
                        self._add(dim, name, "⚠️", "目录存在但无知识文件")
                else:
                    self._add(dim, name, "❌", f"目录缺失: {dir_path}")
            else:
                if self._exists(path):
                    self._add(dim, name, "✅", f"文件存在: {path}")
                else:
                    self._add(dim, name, "❌", f"文件缺失: {path}")

    # ─── D8：人物库/场景库结构 ───
    def check_d8_person_scene_library(self):
        dim = "D8-人物/场景库"

        for subdir in self.config.PERSON_LIBRARY_SUBDIRS:
            path = f"参考库/人物库/{subdir}"
            if self._is_dir(path):
                self._add(dim, f"人物库/{subdir}", "✅", "子目录存在")
            else:
                self._add(dim, f"人物库/{subdir}", "⚠️", f"子目录缺失: {path}")

        for subdir in self.config.SCENE_LIBRARY_SUBDIRS:
            path = f"参考库/场景库/{subdir}"
            if self._is_dir(path):
                self._add(dim, f"场景库/{subdir}", "✅", "子目录存在")
            else:
                self._add(dim, f"场景库/{subdir}", "⚠️", f"子目录缺失: {path}")

    # ─── D9：主流程链路连通性 ───
    def check_d9_main_flow(self):
        dim = "D9-主流程链路"
        for gate_name, required_files in self.config.MAIN_FLOW_GATES.items():
            if not required_files:
                self._add(dim, gate_name, "✅", "动态阶段门（运行时确定依赖）")
                continue
            all_ok = True
            missing = []
            for f in required_files:
                if not self._exists(f):
                    all_ok = False
                    missing.append(f)
            if all_ok:
                self._add(dim, gate_name, "✅", f"阶段门依赖完整 ({len(required_files)} 文件)")
            else:
                self._add(dim, gate_name, "❌",
                          f"阶段门依赖缺失: {', '.join(missing)}")

    # ─── D10：规则间交叉引用 ───
    def check_d10_cross_references(self):
        dim = "D10-交叉引用"
        for rule_file, refs in self.config.RULE_CROSS_REFS.items():
            rule_path = f".cursor/rules/{rule_file}"
            if not self._exists(rule_path):
                self._add(dim, rule_file, "❌", f"规则文件本身不存在: {rule_path}")
                continue
            for ref in refs:
                ref_path = f".cursor/rules/{ref}"
                if self._exists(ref_path):
                    self._add(dim, f"{rule_file} → {ref}", "✅", "被引用规则存在")
                else:
                    self._add(dim, f"{rule_file} → {ref}", "❌",
                              f"被引用规则缺失: {ref_path}")

    # ─── D11：触发词路由可达性（V8.0：路由到 Skill 名） ───
    def check_d11_trigger_routes(self):
        dim = "D11-触发词路由"
        # V8.0：TRIGGER_ROUTES 的 value 是 Skill 名，需在 SKILL_DIRS 中查路径
        for triggers, skill_name in self.config.TRIGGER_ROUTES.items():
            skill_path = self.config.SKILL_DIRS.get(skill_name)
            trigger_display = triggers.split("|")[0]
            if skill_path and self._exists(skill_path):
                self._add(dim, f'"{trigger_display}..." → {skill_name}', "✅",
                          f"触发词可路由到已存在的 Skill")
            else:
                self._add(dim, f'"{trigger_display}..." → {skill_name}', "❌",
                          f"触发词目标 Skill 不存在: {skill_path}")

    # ─── D12：参考库原始素材目录 ───
    def check_d12_archive_dirs(self):
        dim = "D12-原始素材归档"
        archive_domains = {
            "E": "参考库/E_平面与海报/原始素材",
            "F": "参考库/F_摄影风格/原始素材",
            "G": "参考库/G_插画与图形/原始素材",
            "C": "参考库/C_排版字体/原始素材",
            "N": "参考库/N_详情页设计/原始素材",
        }
        for code, path in archive_domains.items():
            if self._is_dir(path):
                dir_full = self.root / path
                files = [f for f in dir_full.iterdir() if f.is_file()]
                self._add(dim, f"{code}域原始素材", "✅",
                          f"目录存在, 含 {len(files)} 个文件")
            else:
                self._add(dim, f"{code}域原始素材", "⚠️",
                          f"原始素材目录缺失: {path}（学习模块归档时自动创建）")

    # ─── 执行全部诊断 ───
    def run_all(self) -> str:
        self.results.clear()
        self.stats = {"pass": 0, "warn": 0, "fail": 0}

        self.check_d1_core_files()
        self.check_d2_module_registry()
        self.check_d3_rule_files()
        self.check_d4_skills()
        self.check_d5_ref_library()
        self.check_d6_brand_spec()
        self.check_d7_scene_knowledge()
        self.check_d8_person_scene_library()
        self.check_d9_main_flow()
        self.check_d10_cross_references()
        self.check_d11_trigger_routes()
        self.check_d12_archive_dirs()

        return self.format_report()

    def format_report(self) -> str:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        total = sum(self.stats.values())
        health = self.stats["pass"] / total * 100 if total > 0 else 0

        if health >= 95:
            health_icon = "🟢"
            health_text = "优秀"
        elif health >= 80:
            health_icon = "🟡"
            health_text = "良好（有待改进）"
        elif health >= 60:
            health_icon = "🟠"
            health_text = "需要关注"
        else:
            health_icon = "🔴"
            health_text = "严重问题"

        lines = []
        lines.append("=" * 60)
        lines.append("   AI设计师助手 · 智能体逻辑链路诊断报告")
        lines.append(f"   诊断时间: {now}")
        lines.append("=" * 60)
        lines.append("")
        lines.append(f"  {health_icon} 系统健康度: {health:.1f}% — {health_text}")
        lines.append(f"  ✅ 通过: {self.stats['pass']}  ⚠️ 警告: {self.stats['warn']}  ❌ 失败: {self.stats['fail']}")
        lines.append("")

        # 按维度分组
        dims: dict[str, list[DiagnosticResult]] = {}
        for r in self.results:
            dims.setdefault(r.dimension, []).append(r)

        for dim_name, items in dims.items():
            fails = [i for i in items if i.status == "❌"]
            warns = [i for i in items if i.status == "⚠️"]
            passes = [i for i in items if i.status == "✅"]

            if fails:
                dim_icon = "❌"
            elif warns:
                dim_icon = "⚠️"
            else:
                dim_icon = "✅"

            lines.append(f"{'─' * 56}")
            lines.append(f"  {dim_icon} {dim_name}  (✅{len(passes)} ⚠️{len(warns)} ❌{len(fails)})")
            lines.append(f"{'─' * 56}")

            # 只显示失败和警告的详细信息（节省篇幅）
            for item in fails + warns:
                lines.append(f"    {item.status} {item.item}")
                if item.detail:
                    lines.append(f"       └─ {item.detail}")

            if not fails and not warns:
                lines.append(f"    全部通过 ({len(passes)} 项)")

            lines.append("")

        # 问题汇总
        all_fails = [r for r in self.results if r.status == "❌"]
        all_warns = [r for r in self.results if r.status == "⚠️"]

        if all_fails:
            lines.append("=" * 60)
            lines.append("  ❌ 关键问题清单（必须修复）")
            lines.append("=" * 60)
            for i, r in enumerate(all_fails, 1):
                lines.append(f"  {i}. [{r.dimension}] {r.item}")
                lines.append(f"     {r.detail}")
            lines.append("")

        if all_warns:
            lines.append("=" * 60)
            lines.append("  ⚠️ 改进建议清单")
            lines.append("=" * 60)
            for i, r in enumerate(all_warns, 1):
                lines.append(f"  {i}. [{r.dimension}] {r.item}")
                lines.append(f"     {r.detail}")
            lines.append("")

        if not all_fails and not all_warns:
            lines.append("=" * 60)
            lines.append("  🎉 所有检查项全部通过！系统链路完全畅通。")
            lines.append("=" * 60)

        lines.append("")
        lines.append(f"  诊断完成. 共检查 {total} 项.")
        return "\n".join(lines)

    def export_json(self) -> str:
        """导出 JSON 格式的诊断结果"""
        data = {
            "timestamp": datetime.now().isoformat(),
            "stats": self.stats,
            "health_pct": round(self.stats["pass"] / sum(self.stats.values()) * 100, 1)
                          if sum(self.stats.values()) > 0 else 0,
            "results": [
                {
                    "dimension": r.dimension,
                    "item": r.item,
                    "status": r.status,
                    "detail": r.detail,
                }
                for r in self.results
            ],
        }
        return json.dumps(data, ensure_ascii=False, indent=2)


# ─────────────────────────────────────────
# 入口
# ─────────────────────────────────────────

def main():
    import argparse
    parser = argparse.ArgumentParser(description="AI设计师助手 · 逻辑链路诊断")
    parser.add_argument("--root", default=None, help="项目根路径（默认自动检测）")
    parser.add_argument("--json", action="store_true", help="输出 JSON 格式")
    parser.add_argument("--dimension", default=None,
                        help="仅检查指定维度 (d1-d12)")
    args = parser.parse_args()

    root = args.root
    if root is None:
        script_dir = Path(__file__).resolve().parent
        for p in [script_dir] + list(script_dir.parents):
            if (p / "主控中心.txt").exists():
                root = str(p)
                break
        if root is None:
            root = os.getcwd()

    engine = DiagnosticEngine(root)

    if args.dimension:
        dim_map = {
            "d1": engine.check_d1_core_files,
            "d2": engine.check_d2_module_registry,
            "d3": engine.check_d3_rule_files,
            "d4": engine.check_d4_skills,
            "d5": engine.check_d5_ref_library,
            "d6": engine.check_d6_brand_spec,
            "d7": engine.check_d7_scene_knowledge,
            "d8": engine.check_d8_person_scene_library,
            "d9": engine.check_d9_main_flow,
            "d10": engine.check_d10_cross_references,
            "d11": engine.check_d11_trigger_routes,
            "d12": engine.check_d12_archive_dirs,
        }
        check_fn = dim_map.get(args.dimension.lower())
        if check_fn:
            check_fn()
        else:
            print(f"未知维度: {args.dimension}. 可选: {', '.join(dim_map.keys())}")
            sys.exit(1)
    else:
        engine.run_all()

    if args.json:
        print(engine.export_json())
    else:
        print(engine.format_report())


if __name__ == "__main__":
    main()
