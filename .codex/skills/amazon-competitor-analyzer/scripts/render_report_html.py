"""
将竞品分析 Markdown 报告渲染为「可视化看板式」HTML。

特性：
1) 左侧展示套图缩略列 + A+ 模块（含横向切换交互）
2) 右侧展示分析正文（Markdown 渲染）
3) 顶部摘要卡（品牌、评分、评价、模块数等）
4) 装饰性图标与卡片化排版，提升可读性
"""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import re
import sys
from pathlib import Path
from typing import Any, Dict, List

import markdown


CSS = """
:root {
  --bg: #f3f4f8;
  --card: #ffffff;
  --text: #101828;
  --muted: #667085;
  --line: #e4e7ec;
  --brand: #2563eb;
  --accent: #e11d48;
  --ok: #16a34a;
  --shadow: 0 8px 24px rgba(16, 24, 40, 0.06);
}
* { box-sizing: border-box; }
body {
  margin: 0;
  background: radial-gradient(circle at top left, #eef2ff 0, #f3f4f8 36%, #f8fafc 100%);
  color: var(--text);
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "PingFang SC", "Microsoft YaHei", Arial, sans-serif;
}
.page {
  width: calc(100vw - 16px);
  max-width: none;
  margin: 8px auto 20px;
  padding: 0 4px;
}
.layout {
  display: grid;
  grid-template-columns: 560px minmax(0, 1fr);
  gap: 12px;
}
.panel {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow);
}
.left-wrap {
  position: sticky;
  top: 12px;
  align-self: start;
  padding: 10px;
  max-height: calc(100vh - 24px);
  overflow: auto;
}
.section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 700;
  color: #344054;
  margin: 8px 2px 10px;
}
.icon-dot {
  width: 10px;
  height: 10px;
  border-radius: 99px;
  background: linear-gradient(135deg, var(--brand), var(--accent));
}
.gallery-preview {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: #f8fafc;
}
.gallery-main {
  width: 100%;
  max-height: 760px;
  object-fit: contain;
  background: #f8fafc;
  display: block;
}
.thumbs {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
  padding: 8px;
  border-top: 1px solid var(--line);
}
.thumbs img {
  width: 100%;
  aspect-ratio: 3 / 4;
  object-fit: cover;
  border-radius: 6px;
  border: 2px solid transparent;
  cursor: pointer;
}
.thumbs img.active {
  border-color: var(--brand);
}
.aplus-stream {
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}
.aplus-card {
  border: 0;
  border-radius: 0;
  overflow: hidden;
  margin: 0;
  background: #fff;
}
.aplus-head {
  display: none;
}
.aplus-stage {
  position: relative;
  min-height: 0;
  background: transparent;
}
.aplus-slide {
  display: none;
  position: relative;
}
.aplus-slide.active {
  display: block;
}
.aplus-slide img {
  width: 100%;
  height: auto;
  display: block;
}
.aplus-tag {
  position: absolute;
  left: 10px;
  bottom: 10px;
  padding: 4px 10px;
  background: rgba(15, 23, 42, 0.82);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  letter-spacing: 0.8px;
  border-radius: 6px;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  pointer-events: none;
  z-index: 2;
  box-shadow: 0 2px 6px rgba(0, 0, 0, 0.18);
  -webkit-backdrop-filter: blur(3px);
  backdrop-filter: blur(3px);
}
.aplus-nav {
  position: absolute;
  top: 50%;
  transform: translateY(-50%);
  width: 30px;
  height: 30px;
  border-radius: 99px;
  border: 0;
  background: rgba(15, 23, 42, 0.65);
  color: #fff;
  cursor: pointer;
}
.aplus-prev { left: 8px; }
.aplus-next { right: 8px; }
.aplus-dots {
  position: absolute;
  left: 0;
  right: 0;
  bottom: 8px;
  display: flex;
  justify-content: center;
  gap: 6px;
  padding: 0;
  pointer-events: auto;
}
.aplus-dot {
  width: 8px;
  height: 8px;
  border-radius: 99px;
  background: #cbd5e1;
  cursor: pointer;
}
.aplus-dot.active {
  width: 20px;
  border-radius: 12px;
  background: #2563eb;
}
.right-wrap {
  padding: 12px;
}
.hero {
  padding: 14px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, #111827, #1f2937 46%, #334155);
  color: #fff;
  border-radius: 14px;
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}
.hero-text { flex: 1 1 360px; min-width: 0; }
.hero h1 {
  margin: 0;
  font-size: 24px;
  line-height: 1.35;
}
.hero p {
  margin: 8px 0 0;
  color: #cbd5e1;
  font-size: 13px;
}
.hero-link {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  background: linear-gradient(135deg, #ff9900 0%, #ff6f00 100%);
  color: #fff;
  font-size: 13px;
  font-weight: 700;
  text-decoration: none;
  border-radius: 999px;
  border: 1px solid rgba(255, 255, 255, 0.25);
  white-space: nowrap;
  flex-shrink: 0;
  box-shadow: 0 4px 12px rgba(255, 111, 0, 0.25);
  transition: transform 0.15s ease, box-shadow 0.15s ease, filter 0.15s ease;
  align-self: center;
}
.hero-link:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 18px rgba(255, 111, 0, 0.45);
  filter: brightness(1.05);
}
.hero-link .hl-arrow {
  font-size: 14px;
  font-weight: 800;
  margin-left: 2px;
}
/* 浮动悬浮按钮：仅在滚动出 hero 区域后才出现，避免与 hero 内按钮在顶部重复 */
.amazon-fab {
  position: fixed;
  top: 14px;
  right: 16px;
  z-index: 1000;
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 8px 14px;
  background: rgba(15, 23, 42, 0.92);
  color: #fff;
  border: 1px solid rgba(255, 153, 0, 0.55);
  border-radius: 999px;
  font-size: 12px;
  font-weight: 700;
  text-decoration: none;
  box-shadow: 0 6px 14px rgba(0, 0, 0, 0.22);
  opacity: 0;
  pointer-events: none;
  transform: translateY(-6px);
  transition: opacity 0.25s ease, transform 0.25s ease, background 0.15s ease, border-color 0.15s ease;
  -webkit-backdrop-filter: blur(6px);
  backdrop-filter: blur(6px);
}
.amazon-fab.is-visible {
  opacity: 1;
  pointer-events: auto;
  transform: translateY(0);
}
.amazon-fab:hover {
  background: rgba(255, 111, 0, 0.96);
  border-color: rgba(255, 255, 255, 0.6);
}
.amazon-fab .fab-icon { font-size: 14px; }
/* 交互式评论看板入口：紫色变体，与 Amazon 橙形成区分 */
.hero-link.hero-dash {
  background: linear-gradient(135deg, #7c3aed 0%, #4f46e5 100%);
  box-shadow: 0 4px 12px rgba(79, 70, 229, 0.28);
}
.hero-link.hero-dash:hover {
  box-shadow: 0 8px 18px rgba(79, 70, 229, 0.45);
}
.amazon-fab.dash-fab {
  top: 54px;
  border-color: rgba(124, 58, 237, 0.6);
}
.amazon-fab.dash-fab:hover {
  background: rgba(79, 70, 229, 0.96);
}
/* KV-table 内 ASIN 等可点击值的链接样式 */
.kv-link {
  color: #1d4ed8;
  text-decoration: none;
  font-weight: 700;
  border-bottom: 1px dashed rgba(29, 78, 216, 0.4);
  transition: color 0.15s ease, border-color 0.15s ease;
}
.kv-link:hover {
  color: #ea580c;
  border-color: #ea580c;
}
.kv-link-arrow {
  display: inline-block;
  margin-left: 4px;
  font-size: 11px;
  color: #ea580c;
  font-weight: 800;
}
.summary-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 10px;
  margin-bottom: 12px;
}
.summary {
  border: 1px solid var(--line);
  border-radius: 12px;
  padding: 10px 12px;
  background: #fff;
}
.summary .k {
  font-size: 12px;
  color: var(--muted);
}
.summary .v {
  margin-top: 4px;
  font-size: 18px;
  font-weight: 700;
}
.visual-board {
  display: grid;
  gap: 12px;
  margin-bottom: 12px;
}
.visual-block {
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 16px;
  box-shadow: var(--shadow);
  padding: 14px;
}
.visual-block h2 {
  margin: 0 0 10px;
  font-size: 18px;
  line-height: 1.35;
  display: flex;
  align-items: center;
  gap: 8px;
}
.visual-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
}
.mini-card {
  min-height: 118px;
  border: 1px solid #eceff3;
  border-radius: 14px;
  background: #f8f8fb;
  padding: 12px;
}
.mini-card-title {
  display: flex;
  align-items: center;
  gap: 6px;
  margin-bottom: 8px;
  font-weight: 800;
  color: #111827;
}
.mini-card-title .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: #111827;
}
.pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}
.pill {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 999px;
  border: 2px solid #111827;
  background: #fff;
  color: #b91c1c;
  font-size: 12px;
  font-weight: 700;
  white-space: nowrap;
}
.pill.dark {
  background: #050505;
  color: #fff;
}
.mini-card p {
  margin: 0;
  font-size: 13px;
  line-height: 1.65;
  color: #344054;
}
.swatches {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}
.swatch {
  width: 22px;
  height: 22px;
  border-radius: 2px;
  border: 1px solid #9ca3af;
}
.score-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.score-card {
  border-radius: 14px;
  border: 1px solid #eceff3;
  background: #fbfcff;
  padding: 10px 12px;
}
.score-head {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  font-size: 14px;
  font-weight: 800;
}
.score-num {
  color: #2563eb;
  white-space: nowrap;
}
.bar {
  height: 8px;
  background: #e5e7eb;
  border-radius: 999px;
  overflow: hidden;
  margin: 9px 0 7px;
}
.bar span {
  display: block;
  height: 100%;
  background: linear-gradient(90deg, #2563eb, #e11d48);
  border-radius: 999px;
}
.score-card p {
  margin: 0;
  font-size: 12px;
  line-height: 1.55;
  color: #475467;
}
.action-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 10px;
}
.action-card {
  border-radius: 14px;
  padding: 12px;
  border: 1px solid #eceff3;
  background: #fff;
}
.action-card.good { background: #f0fdf4; }
.action-card.bad { background: #fff1f2; }
.action-card.borrow { background: #eff6ff; }
.action-card.avoid { background: #fff7ed; }
.action-card h3 {
  margin: 0 0 8px;
  font-size: 15px;
}
.action-card ul {
  margin: 0 0 0 18px;
  padding: 0;
  font-size: 13px;
  line-height: 1.65;
}
.kv-table {
  width: 100%;
  border-collapse: separate;
  border-spacing: 0;
  font-size: 13px;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}
.kv-table tr + tr td { border-top: 1px solid var(--line); }
.kv-table td {
  padding: 10px 14px;
  vertical-align: top;
}
.kv-table .kv-k {
  width: 28%;
  background: #f8fafc;
  color: var(--muted);
  font-weight: 600;
}
.kv-table .kv-v {
  color: var(--text);
}
.kv-table .kv-sub td {
  background: #eef2f7;
  color: var(--muted);
  font-weight: 700;
  font-size: 12px;
  letter-spacing: .02em;
  padding: 7px 14px;
}
.info-list {
  list-style: none;
  margin: 0;
  padding: 0;
}
.info-list li {
  display: flex;
  gap: 10px;
  padding: 8px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 13px;
  line-height: 1.65;
}
.info-list li:last-child { border-bottom: none; }
.info-list .li-icon {
  flex: 0 0 22px;
  color: var(--brand);
}
.visual-quote {
  margin: 0;
  padding: 14px 16px;
  border-left: 4px solid var(--brand);
  background: #eff6ff;
  border-radius: 10px;
  font-size: 14px;
  color: var(--text);
  line-height: 1.7;
}
.visual-warn {
  padding: 12px 14px;
  background: #fff7ed;
  border: 1px dashed #fb923c;
  border-radius: 10px;
  font-size: 13px;
  color: #b45309;
}
.visual-warn code {
  background: #fde68a;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 12px;
}
.step-ladder {
  display: grid;
  gap: 10px;
}
.step-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 14px;
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
  align-items: center;
}
.step-num {
  min-width: 50px;
  height: 50px;
  padding: 0 14px;
  border-radius: 999px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  font-weight: 800;
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  color: #fff;
  letter-spacing: 0.5px;
  white-space: nowrap;
  flex-shrink: 0;
}
.step-num.is-long {
  font-size: 13px;
  letter-spacing: 0.3px;
}
.step-body p {
  margin: 6px 0 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
}
.step-title {
  font-size: 15px;
  font-weight: 700;
  color: var(--text);
}
.layer-stack {
  display: grid;
  gap: 8px;
}
.layer-row {
  display: grid;
  grid-template-columns: 130px 1fr;
  gap: 12px;
  padding: 12px 14px;
  border-radius: 12px;
  background: #f8fafc;
  border-left: 4px solid var(--layer-color, var(--brand));
}
.layer-pill {
  background: var(--layer-color, var(--brand));
  color: #fff;
  font-size: 12px;
  font-weight: 700;
  border-radius: 999px;
  padding: 4px 10px;
  align-self: start;
  width: fit-content;
}
.layer-name {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
.layer-body p {
  margin: 4px 0 0;
  font-size: 13px;
  color: var(--muted);
  line-height: 1.7;
}
.two-col {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.two-col-card {
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--line);
  background: #fff;
}
.two-col-card.seller { background: #f0f9ff; border-color: #bae6fd; }
.two-col-card.buyer  { background: #fef3f2; border-color: #fecdd3; }
.two-col-card.good   { background: #f0fdf4; border-color: #bbf7d0; }
.two-col-card.bad    { background: #fef2f2; border-color: #fecaca; }
.two-col-card h3 {
  margin: 0 0 8px;
  font-size: 14px;
  color: var(--text);
}
.two-col-card ul {
  margin: 0 0 0 18px;
  padding: 0;
  font-size: 13px;
  line-height: 1.7;
}
.metric-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
}
.metric-card {
  position: relative;
  padding: 14px 14px 14px 18px;
  background: #fff;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}
.metric-card::before {
  content: "";
  position: absolute;
  left: 0;
  top: 0;
  bottom: 0;
  width: 4px;
  background: var(--metric-color, var(--brand));
}
.metric-label {
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.metric-value {
  font-size: 16px;
  font-weight: 700;
  color: var(--text);
  line-height: 1.45;
}
.metric-hint {
  margin-top: 6px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
}
.keyword-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.kw-pill {
  padding: 6px 12px;
  border-radius: 999px;
  font-size: 12px;
  border: 1px solid var(--line);
  background: #fff;
  color: var(--text);
}
.kw-pill.kw-l1 {
  background: #f1f5f9;
  color: #475569;
  font-size: 11px;
}
.kw-pill.kw-l2 {
  background: #eff6ff;
  border-color: #bfdbfe;
  color: #1d4ed8;
}
.kw-pill.kw-l3 {
  background: linear-gradient(135deg, #2563eb 0%, #7c3aed 100%);
  border-color: transparent;
  color: #fff;
  font-weight: 700;
  font-size: 13px;
}
/* 重点强化 ================================================================ */
.hl {
  font-weight: 700;
  color: #0f172a;
  background: linear-gradient(180deg, transparent 60%, #fde68a 60%);
  padding: 0 2px;
  border-radius: 2px;
}
.hl-mark {
  background: #fef08a;
  color: #78350f;
  padding: 0 4px;
  border-radius: 4px;
  font-weight: 700;
}
.num-pct {
  color: #1d4ed8;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.num-rank {
  color: #b91c1c;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
}
.num-star {
  color: #b45309;
  font-weight: 700;
  background: #fef3c7;
  padding: 0 6px;
  border-radius: 999px;
  font-variant-numeric: tabular-nums;
}
.verdict-good {
  color: #15803d;
  font-weight: 700;
}
.verdict-warn {
  color: #b45309;
  font-weight: 700;
}
.verdict-bad {
  color: #b91c1c;
  font-weight: 700;
}
/* verdict-headline 「问题本质 punchline」开门见山大字卡 */
.verdict-host {
  border-left: 6px solid var(--vh-accent, #b91c1c);
  background: linear-gradient(135deg, #fff 0%, #fef2f2 100%);
}
.verdict-headline {
  padding: 4px 0;
}
.vh-tag {
  display: inline-block;
  background: var(--vh-accent, #b91c1c);
  color: #fff;
  font-size: 12px;
  font-weight: 800;
  padding: 4px 12px;
  border-radius: 999px;
  letter-spacing: 1px;
  margin-bottom: 12px;
}
.vh-text {
  font-size: 22px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.6;
  letter-spacing: 0.3px;
}
.vh-text .hl {
  background: linear-gradient(180deg, transparent 55%, #fde68a 55%);
}
/* best-for-grid 适合谁 / 不适合谁 */
.best-for-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}
.bf-card {
  border-radius: 14px;
  padding: 14px;
  border: 1px solid var(--line);
}
.bf-card.best { background: #f0fdf4; border-color: #86efac; }
.bf-card.avoid { background: #fef2f2; border-color: #fca5a5; }
.bf-head {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 10px;
}
.bf-badge {
  font-size: 11px;
  font-weight: 800;
  padding: 3px 10px;
  border-radius: 999px;
  letter-spacing: 0.5px;
}
.bf-card.best .bf-badge { background: #16a34a; color: #fff; }
.bf-card.avoid .bf-badge { background: #dc2626; color: #fff; }
.bf-title {
  font-size: 14px;
  font-weight: 700;
  color: var(--text);
}
.bf-card ul {
  list-style: none;
  margin: 0;
  padding: 0;
}
.bf-item {
  padding: 8px 0;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
}
.bf-item:last-child { border-bottom: none; }
.bf-label {
  font-size: 13px;
  color: var(--text);
  font-weight: 600;
}
.bf-hint {
  margin-top: 4px;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
}
.bf-note {
  margin-top: 10px;
  padding: 10px 14px;
  background: #f1f5f9;
  border-radius: 10px;
  font-size: 13px;
  color: var(--muted);
  border-left: 3px solid #94a3b8;
}
/* feature-breakdown 结构解释三段式 */
.feature-breakdown {
  display: grid;
  gap: 10px;
}
.fb-card {
  padding: 14px 16px;
  background: linear-gradient(135deg, #eff6ff 0%, #fff 100%);
  border: 1px solid #bfdbfe;
  border-radius: 14px;
}
.fb-part {
  font-size: 14px;
  font-weight: 700;
  color: #1e3a8a;
  margin-bottom: 8px;
}
.fb-flow {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  font-size: 13px;
}
.fb-step {
  padding: 6px 10px;
  border-radius: 8px;
  background: #fff;
  border: 1px solid var(--line);
  color: var(--text);
  font-weight: 600;
}
.fb-step.mech { border-color: #93c5fd; color: #1d4ed8; }
.fb-step.feel { border-color: #86efac; color: #15803d; background: #f0fdf4; }
.fb-arrow {
  color: #6b7280;
  font-weight: 800;
  font-size: 16px;
}
.fb-en {
  margin-top: 8px;
  padding: 6px 10px;
  background: #0f172a;
  color: #e2e8f0;
  border-radius: 8px;
  font-size: 12px;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  letter-spacing: 0.3px;
}
/* look-suite 场景图 Look 命名 */
.look-suite {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
}
.ls-card {
  padding: 14px 12px;
  border-radius: 14px;
  background: #fff;
  border: 1px solid var(--line);
  border-top: 4px solid var(--ls-accent, var(--brand));
  text-align: center;
}
.ls-icon {
  font-size: 24px;
  margin-bottom: 6px;
}
.ls-name {
  font-size: 14px;
  font-weight: 800;
  color: var(--text);
}
.ls-en {
  margin-top: 4px;
  font-size: 11px;
  color: var(--ls-accent, var(--muted));
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
  letter-spacing: 0.5px;
}
.ls-card p {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
  line-height: 1.6;
}
/* review-sentiment 评论情感解析 */
.rs-hist {
  display: grid;
  gap: 6px;
  margin-bottom: 14px;
  padding: 12px 14px;
  background: #f8fafc;
  border-radius: 12px;
  border: 1px solid var(--line);
}
.rs-hist-row {
  display: grid;
  grid-template-columns: 36px 1fr 48px;
  gap: 10px;
  align-items: center;
  font-size: 12px;
}
.rs-hist-label {
  font-weight: 700;
  color: var(--text);
}
.rs-hist-bar {
  height: 10px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}
.rs-hist-bar span {
  display: block;
  height: 100%;
  border-radius: 999px;
  transition: width 0.5s ease;
}
.rs-hist-pct {
  font-weight: 700;
  color: var(--muted);
  text-align: right;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
.rs-kw-wrap {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
  margin-bottom: 14px;
}
.rs-kw-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text);
}
.rs-kw-group {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.rs-kw {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 5px 10px;
  border-radius: 999px;
  font-size: 12px;
  font-weight: 600;
  border: 1px solid;
}
.rs-kw.pos {
  background: #f0fdf4;
  color: #15803d;
  border-color: #86efac;
}
.rs-kw.neg {
  background: #fef2f2;
  color: #b91c1c;
  border-color: #fca5a5;
}
.rs-kw-count {
  font-size: 10px;
  font-weight: 800;
  padding: 1px 5px;
  border-radius: 999px;
  background: rgba(0, 0, 0, 0.08);
}
/* review-sentiment 内嵌加权词云 */
.rs-cloud-title {
  font-size: 13px;
  font-weight: 700;
  margin-bottom: 8px;
  color: var(--text);
}
.rs-cloud {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px 12px;
  padding: 14px 16px;
  margin-bottom: 14px;
  background: #f8fafc;
  border: 1px solid var(--line);
  border-radius: 12px;
  line-height: 1.5;
}
.rs-cloud-pill {
  display: inline-flex;
  align-items: baseline;
  gap: 4px;
  font-weight: 700;
  border-radius: 999px;
  padding: 2px 10px;
  line-height: 1.4;
}
.rs-cloud-pill.lv1 { font-size: 12px; opacity: 0.78; }
.rs-cloud-pill.lv2 { font-size: 16px; }
.rs-cloud-pill.lv3 { font-size: 22px; }
.rs-cloud-pill.pos {
  background: #f0fdf4;
  color: #15803d;
  border: 1px solid #bbf7d0;
}
.rs-cloud-pill.neg {
  background: #fef2f2;
  color: #b91c1c;
  border: 1px solid #fecaca;
}
.rs-cloud-count {
  font-size: 0.62em;
  font-weight: 800;
  opacity: 0.7;
}
.rs-cloud-legend {
  display: flex;
  gap: 14px;
  margin: -6px 0 14px;
  font-size: 11px;
  color: var(--muted);
}
.rs-cloud-legend .pos b { color: #15803d; }
.rs-cloud-legend .neg b { color: #b91c1c; }
.rs-voice-list {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;
}
.rs-voice {
  margin: 0;
  padding: 12px 14px;
  background: #fffbeb;
  border-left: 4px solid #f59e0b;
  border-radius: 10px;
  font-size: 13px;
  line-height: 1.7;
  color: var(--text);
}
.rs-voice p {
  margin: 0;
}
.rs-voice-stars {
  font-size: 13px;
  color: #f59e0b;
  margin-bottom: 6px;
  letter-spacing: 1px;
}
.rs-voice-dim {
  color: #fde68a;
}
.rs-voice-meta {
  margin-top: 6px;
  font-size: 11px;
  color: var(--muted);
}
.rs-gap-wrap {
  margin-bottom: 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  overflow: hidden;
}
.rs-gap-header {
  padding: 10px 14px;
  background: linear-gradient(135deg, #fef2f2, #fff);
  font-weight: 700;
  font-size: 13px;
  color: #b91c1c;
  border-bottom: 1px solid var(--line);
}
.rs-gap-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}
.rs-gap-table th {
  background: #f8fafc;
  padding: 8px 10px;
  text-align: left;
  font-size: 11px;
  font-weight: 700;
  color: var(--muted);
  text-transform: uppercase;
  letter-spacing: 0.5px;
  border-bottom: 1px solid var(--line);
}
.rs-gap-table td {
  padding: 10px;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
  vertical-align: top;
  line-height: 1.6;
}
.rs-gap-table tr:last-child td { border-bottom: none; }
.rs-gap-page { background: #f0f9ff; color: #0369a1; width: 45%; }
.rs-gap-arrow {
  text-align: center;
  font-weight: 800;
  color: #94a3b8;
  width: 30px;
}
.rs-gap-review { background: #fef2f2; color: #b91c1c; width: 45%; }
.rs-summary {
  padding: 10px 14px;
  background: #f1f5f9;
  border-radius: 10px;
  font-size: 13px;
  color: var(--muted);
  border-left: 3px solid #94a3b8;
  line-height: 1.7;
}
.content-card {
  background: var(--card);
  border: 1px solid var(--line);
  border-radius: 14px;
  box-shadow: var(--shadow);
  padding: 18px 20px;
}
.content-card h1,
.content-card h2,
.content-card h3 {
  line-height: 1.35;
}
.content-card h1 {
  margin-top: 0;
  border-bottom: 2px solid var(--line);
  padding-bottom: 10px;
}
.content-card h2 {
  border-left: 4px solid var(--brand);
  padding-left: 10px;
  margin-top: 24px;
}
.content-card table {
  width: 100%;
  border-collapse: collapse;
  margin: 10px 0 14px;
  font-size: 14px;
}
.content-card th,
.content-card td {
  border: 1px solid var(--line);
  padding: 9px 10px;
  vertical-align: top;
}
.content-card th {
  background: #f9fafb;
  text-align: left;
}
.meta {
  margin-top: 12px;
  color: var(--muted);
  font-size: 12px;
}
.meta-card {
  margin-top: 10px;
  padding: 10px 14px;
  background: #fff;
  border: 1px dashed var(--line);
  border-radius: 10px;
  color: var(--muted);
  font-size: 12px;
  text-align: right;
}
/* w5h2-grid 5W2H 购买行为分析 ======================================== */
.w5h2-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 10px;
}
.w5h2-card {
  padding: 14px;
  border: 1px solid var(--line);
  border-radius: 14px;
  background: linear-gradient(135deg, #f8fafc 0%, #fff 100%);
  border-top: 3px solid var(--w-accent, #2563eb);
}
.w5h2-key {
  display: inline-block;
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0;
  color: #fff;
  background: var(--w-accent, #2563eb);
  padding: 3px 10px;
  border-radius: 999px;
}
.w5h2-head {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  margin-bottom: 8px;
}
.w5h2-zh,
.w5h2-label { font-size: 14px; font-weight: 700; color: var(--text); }
.w5h2-q { font-size: 12px; color: var(--muted); margin-bottom: 8px; line-height: 1.5; }
.w5h2-finding,
.w5h2-value { font-size: 13px; color: #344054; line-height: 1.65; }
.w5h2-ev {
  margin-top: 8px;
  font-size: 11px;
  color: var(--muted);
  border-top: 1px dashed var(--line);
  padding-top: 6px;
  line-height: 1.5;
}
/* persona-cards 客户画像 ============================================= */
.persona-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 12px;
}
.persona-card {
  border: 1px solid var(--line);
  border-radius: 16px;
  background: #fff;
  overflow: hidden;
}
.persona-head {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px;
  background: linear-gradient(135deg, #eef2ff 0%, #f8fafc 100%);
  border-bottom: 1px solid var(--line);
}
.persona-avatar {
  width: 46px;
  height: 46px;
  border-radius: 50%;
  background: #fff;
  border: 2px solid var(--brand);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 24px;
  flex-shrink: 0;
}
.persona-name { font-size: 15px; font-weight: 800; color: var(--text); }
.persona-tags { display: flex; flex-wrap: wrap; gap: 4px; margin-top: 4px; }
.persona-tag {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #e0e7ff;
  color: #4338ca;
  font-weight: 600;
}
.persona-body { padding: 6px 14px; }
.persona-row {
  display: flex;
  gap: 8px;
  padding: 7px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 13px;
  line-height: 1.6;
}
.persona-row:last-of-type { border-bottom: none; }
.persona-row-k { flex: 0 0 56px; color: var(--muted); font-weight: 700; }
.persona-row-v { color: #344054; }
.persona-quote {
  margin: 8px 14px 14px;
  padding: 10px 12px;
  background: #fffbeb;
  border-left: 3px solid #f59e0b;
  border-radius: 8px;
  font-size: 12px;
  color: #92400e;
  line-height: 1.6;
}
.persona-quote p { margin: 0; }
/* kano-model Kano 模型真实需求 ======================================= */
.kano-stack { display: grid; gap: 10px; }
.kano-group {
  border: 1px solid var(--line);
  border-radius: 14px;
  overflow: hidden;
  border-left: 5px solid var(--kano-color, #2563eb);
}
.kano-group-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 10px;
  padding: 10px 14px;
  background: var(--kano-bg, #f8fafc);
  flex-wrap: wrap;
}
.kano-cat { font-size: 14px; font-weight: 800; color: var(--kano-color, #2563eb); }
.kano-cat-en {
  font-size: 11px;
  color: var(--muted);
  font-weight: 600;
  font-family: ui-monospace, "SF Mono", Menlo, Consolas, monospace;
}
.kano-desc { font-size: 11px; color: var(--muted); }
.kano-list { list-style: none; margin: 0; padding: 8px 14px 12px; }
.kano-item {
  padding: 7px 0;
  border-bottom: 1px dashed var(--line);
  font-size: 13px;
  line-height: 1.6;
}
.kano-item:last-child { border-bottom: none; }
.kano-need { font-weight: 600; color: var(--text); }
.kano-ev { margin-top: 3px; font-size: 11px; color: var(--muted); line-height: 1.5; }
/* dev-watchpoints 产品开发注意点 ===================================== */
.dev-list { display: grid; gap: 10px; }
.dev-card {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 12px;
  padding: 12px 14px;
  border: 1px solid var(--line);
  border-radius: 12px;
  background: #fff;
  align-items: start;
}
.dev-pri {
  font-size: 12px;
  font-weight: 800;
  color: #fff;
  padding: 4px 10px;
  border-radius: 8px;
  white-space: nowrap;
  align-self: start;
  background: var(--dev-color, #2563eb);
}
.dev-point { font-size: 14px; font-weight: 700; color: var(--text); line-height: 1.5; }
.dev-rationale { margin-top: 4px; font-size: 12px; color: var(--muted); line-height: 1.6; }
.dev-cat {
  display: inline-block;
  margin-top: 6px;
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 999px;
  background: #f1f5f9;
  color: #475569;
  font-weight: 600;
}
@media (max-width: 1200px) {
  .layout { grid-template-columns: 1fr; }
  .left-wrap { position: static; max-height: none; }
  .summary-grid { grid-template-columns: repeat(2, 1fr); }
  .visual-grid,
  .score-grid,
  .action-grid { grid-template-columns: 1fr; }
  .w5h2-grid,
  .persona-grid { grid-template-columns: 1fr; }
}
"""


JS = """
function initGallery() {
  const root = document.querySelector('.gallery-preview');
  if (!root) return;
  const main = root.querySelector('.gallery-main');
  const thumbs = Array.from(root.querySelectorAll('.thumbs img'));
  thumbs.forEach((t) => {
    t.addEventListener('click', () => {
      main.src = t.dataset.full;
      thumbs.forEach((x) => x.classList.remove('active'));
      t.classList.add('active');
    });
  });
}

function initAplusCarousels() {
  const cards = Array.from(document.querySelectorAll('.aplus-card[data-slider="1"]'));
  cards.forEach((card) => {
    const slides = Array.from(card.querySelectorAll('.aplus-slide'));
    const dots = Array.from(card.querySelectorAll('.aplus-dot'));
    const prev = card.querySelector('.aplus-prev');
    const next = card.querySelector('.aplus-next');
    let idx = 0;
    const apply = () => {
      slides.forEach((s, i) => s.classList.toggle('active', i === idx));
      dots.forEach((d, i) => d.classList.toggle('active', i === idx));
    };
    prev.addEventListener('click', () => {
      idx = (idx - 1 + slides.length) % slides.length;
      apply();
    });
    next.addEventListener('click', () => {
      idx = (idx + 1) % slides.length;
      apply();
    });
    dots.forEach((d, i) => d.addEventListener('click', () => {
      idx = i;
      apply();
    }));
    apply();
  });
}

function initFloatingAmazonFab() {
  const fabs = Array.from(document.querySelectorAll('.amazon-fab'));
  const hero = document.querySelector('.hero');
  if (!fabs.length) return;
  if (!hero || !('IntersectionObserver' in window)) {
    fabs.forEach((f) => f.classList.add('is-visible'));
    return;
  }
  const obs = new IntersectionObserver(([entry]) => {
    fabs.forEach((f) => f.classList.toggle('is-visible', !entry.isIntersecting));
  }, { threshold: 0, rootMargin: '0px 0px -10px 0px' });
  obs.observe(hero);
}

document.addEventListener('DOMContentLoaded', () => {
  initGallery();
  initAplusCarousels();
  initFloatingAmazonFab();
});
"""


HTML_TEMPLATE = """<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>__TITLE__</title>
  <style>__CSS__</style>
</head>
<body>
  __FLOATING__
  <div class="page">
    <div class="layout">
      __LEFT__
      __RIGHT__
    </div>
  </div>
  <script>__JS__</script>
</body>
</html>
"""


# ----------------------------------------------------------------------------
# Amazon 原网址跳转支持
# - 通过模块级变量在渲染期间共享 source_url（来自 metadata.json.source_url）
# - 三处入口：hero 胶囊按钮 / kv-table ASIN 行自动链接 / 右上角浮动悬浮按钮
# ----------------------------------------------------------------------------
_CURRENT_SOURCE_URL: str = ""
# 同目录存在 review_dashboard.html 时，注入"交互式评论看板"跳转入口（相对路径，离线可用）
_CURRENT_DASHBOARD: str = ""
# 来自 metadata.json.specs 的产品参数（格式自适应，可能为空）。
# kv-table 声明 "specs_from_metadata": true 时自动注入，无参数则自动省略。
_CURRENT_SPECS: List[Dict[str, str]] = []

# 英文参数标签 → 中文展示名（仅命中才翻译，未命中保留原英文，保证对任意品类自适应）。
_SPEC_LABEL_ZH: Dict[str, str] = {
    "brand": "品牌",
    "power source": "供电方式",
    "color": "颜色",
    "item weight": "整机重量",
    "product weight": "整机重量",
    "hose length": "软管长度",
    "product dimensions": "产品尺寸",
    "item dimensions l x w x h": "产品尺寸",
    "package dimensions": "包装尺寸",
    "tank volume": "水箱容量",
    "capacity": "容量",
    "maximum pressure": "最大压力",
    "material": "材质",
    "style": "款式",
    "size": "尺寸",
    "voltage": "电压",
    "wattage": "功率",
    "battery": "电池",
    "model number": "型号",
    "item model number": "型号",
    "model name": "型号名称",
    "upc": "UPC",
    "ean": "EAN",
    "manufacturer": "制造商",
    "country of origin": "原产地",
    "special feature": "特色功能",
    "included components": "包含组件",
    "number of items": "件数",
    "recommended uses for product": "推荐用途",
    "surface recommendation": "适用表面",
}


def _spec_label_zh(label: str) -> str:
    """命中映射则译为中文，否则原样返回（适配任意产品的未知参数）。"""
    return _SPEC_LABEL_ZH.get((label or "").strip().lower(), label)


def _hero_amazon_link(url: str) -> str:
  """Hero 横幅右侧的 Amazon 橙色胶囊按钮。url 为空时返回空串。"""
  if not url:
    return ""
  href = html.escape(url, quote=True)
  return (
    f'<a class="hero-link" href="{href}" target="_blank" rel="noopener" '
    f'title="在 Amazon 打开当前商品页">'
    f'<span>🛒 在 Amazon 打开</span><span class="hl-arrow">↗</span>'
    f'</a>'
  )


def _hero_dashboard_link(rel: str) -> str:
  """Hero 横幅的"交互式评论看板"紫色胶囊按钮。rel 为空时返回空串。"""
  if not rel:
    return ""
  href = html.escape(rel, quote=True)
  return (
    f'<a class="hero-link hero-dash" href="{href}" '
    f'title="打开交互式评论分析看板（多维图表 + 时间范围框选联动）">'
    f'<span>📊 交互式评论看板</span><span class="hl-arrow">→</span>'
    f'</a>'
  )


def _floating_dashboard_link(rel: str) -> str:
  """页面右上角浮动的"评论看板"悬浮按钮。rel 为空时返回空串。"""
  if not rel:
    return ""
  href = html.escape(rel, quote=True)
  return (
    f'<a class="amazon-fab dash-fab" href="{href}" '
    f'title="打开交互式评论分析看板">'
    f'<span class="fab-icon">📊</span><span>评论看板</span><span>→</span>'
    f'</a>'
  )


def _floating_amazon_link(url: str) -> str:
  """页面右上角的浮动悬浮按钮。url 为空时返回空串。"""
  if not url:
    return ""
  href = html.escape(url, quote=True)
  return (
    f'<a class="amazon-fab" href="{href}" target="_blank" rel="noopener" '
    f'title="在 Amazon 打开当前商品页">'
    f'<span class="fab-icon">🛒</span><span>查看原网址</span><span>↗</span>'
    f'</a>'
  )


def parse_args() -> argparse.Namespace:
  parser = argparse.ArgumentParser(description="将竞品分析 Markdown 渲染为可视化 HTML")
  parser.add_argument("--input", required=True, help="Markdown 文件路径")
  parser.add_argument("--output", default="", help="输出 HTML 路径；默认为输入文件同目录下的 index.html")
  return parser.parse_args()


def to_html(md_text: str) -> str:
  return markdown.markdown(
    md_text,
    extensions=["tables", "fenced_code", "nl2br", "sane_lists"],
    output_format="html5",
  )


def load_json(path: Path) -> Dict[str, Any]:
  if not path.exists():
    return {}
  try:
    return json.loads(path.read_text(encoding="utf-8"))
  except Exception:
    return {}


def rel_or_uri(path_str: str, base_dir: Path) -> str:
  p = Path(path_str)
  if not p.is_absolute():
    return html.escape(path_str.replace("\\", "/"))
  try:
    rel = p.relative_to(base_dir)
    return html.escape(str(rel).replace("\\", "/"))
  except Exception:
    return html.escape(p.as_uri())


def extract_score(md_text: str) -> str:
  m = re.search(r"加权总分[^\\n]*\\*\\*([0-9]+(?:\\.[0-9])?)", md_text)
  return m.group(1) if m else "-"


def strip_md(text: str) -> str:
  text = re.sub(r"`([^`]+)`", r"\1", text)
  text = re.sub(r"\*\*([^*]+)\*\*", r"\1", text)
  text = re.sub(r"\*([^*]+)\*", r"\1", text)
  text = text.replace("&nbsp;", " ")
  return text.strip()


def extract_section(md_text: str, heading_prefix: str) -> str:
  pattern = rf"^##\s+{re.escape(heading_prefix)}.*?(?=^##\s+|\Z)"
  m = re.search(pattern, md_text, flags=re.M | re.S)
  return m.group(0) if m else ""


def parse_markdown_table(section: str) -> List[List[str]]:
  lines = [line.strip() for line in section.splitlines() if line.strip().startswith("|")]
  rows: List[List[str]] = []
  for line in lines:
    cells = [strip_md(c.strip()) for c in line.strip("|").split("|")]
    if not cells:
      continue
    if all(re.fullmatch(r":?-{3,}:?", c.replace(" ", "")) for c in cells):
      continue
    rows.append(cells)
  if rows and any(c in ("维度", "项") for c in rows[0]):
    rows = rows[1:]
  return rows


def extract_bullet_items(section: str, limit: int = 3) -> List[str]:
  out: List[str] = []
  for line in section.splitlines():
    s = line.strip()
    if not s.startswith("- "):
      continue
    out.append(strip_md(s[2:]))
    if len(out) >= limit:
      break
  return out


def pills_for_dimension(name: str, text: str) -> List[str]:
  mapping = {
    "色彩应用": ["黑色主导", "品牌红点睛", "克制都市感"],
    "模特 / 受众": ["年轻女性", "多元面孔", "轻熟龄"],
    "摄影风格": ["棚拍", "户外街拍", "柔和光线"],
    "整体调性": ["时尚单品", "功能弱化", "day-to-night"],
    "拍摄方式": ["棚拍定妆", "准买家秀", "细节特写"],
  }
  if name in mapping:
    return mapping[name]
  words = re.findall(r"[A-Za-z][A-Za-z -]{2,}|[\u4e00-\u9fff]{2,6}", text)
  return words[:3]


def swatches_for_text(text: str) -> List[str]:
  """从分析文字中提取可视色卡。优先保证文字提到的颜色都有对应色块。"""
  rules = [
    (r"黑色|黑|black", "#050505"),
    (r"品牌红|Nebility Red|红色|红|red", "#d4112f"),
    (r"棕色|棕|brown", "#9b7447"),
    (r"蓝色|牛仔|blue|denim", "#6f85a8"),
    (r"白色|白|white", "#ffffff"),
    (r"米|米灰|浅米|cream|beige", "#c9c2b8"),
  ]
  colors: List[str] = []
  for pattern, color in rules:
    if re.search(pattern, text, flags=re.IGNORECASE) and color not in colors:
      colors.append(color)
  return colors


def style_visual_html(md_text: str) -> str:
  section = extract_section(md_text, "二、风格五标签")
  rows = parse_markdown_table(section)
  cards = []
  for dim, desc, *_ in rows:
    pills = pills_for_dimension(dim, desc)
    pill_html = "".join(
      f'<span class="pill {"dark" if i == 0 else ""}">{html.escape(p)}</span>'
      for i, p in enumerate(pills)
    )
    swatch_colors = swatches_for_text(desc) if "色彩" in dim else []
    swatches = ""
    if "色彩" in dim:
      swatch_html = "".join(
        f'<span class="swatch" style="background:{c}"></span>' for c in swatch_colors
      )
      swatches = f'<div class="swatches">{swatch_html}</div>' if swatch_html else ""
    cards.append(
      f"""
      <div class="mini-card">
        <div class="mini-card-title"><span class="dot"></span>{html.escape(dim)}</div>
        <div class="pill-row">{pill_html}</div>
        <p>{html.escape(desc)}</p>
        {swatches}
      </div>
      """
    )
  return "".join(cards)


def score_visual_html(md_text: str) -> str:
  section = extract_section(md_text, "六、关键维度评分")
  rows = parse_markdown_table(section)
  cards = []
  for dim, score, comment, *_ in rows:
    m = re.search(r"([0-9]+(?:\.[0-9])?)", score)
    value = float(m.group(1)) if m else 0
    width = max(0, min(100, int(value / 5 * 100)))
    cards.append(
      f"""
      <div class="score-card">
        <div class="score-head"><span>{html.escape(dim)}</span><span class="score-num">{html.escape(score)}</span></div>
        <div class="bar"><span style="width:{width}%"></span></div>
        <p>{html.escape(comment)}</p>
      </div>
      """
    )
  return "".join(cards)


def action_visual_html(md_text: str) -> str:
  sections = [
    ("七、优势亮点", "good", "优势亮点"),
    ("八、不足问题", "bad", "不足问题"),
    ("九、可借鉴点", "borrow", "可借鉴点"),
    ("十、规避方向", "avoid", "规避方向"),
  ]
  cards = []
  for heading, cls, title in sections:
    items = extract_bullet_items(extract_section(md_text, heading), limit=3)
    li_html = "".join(f"<li>{html.escape(x)}</li>" for x in items)
    cards.append(f'<div class="action-card {cls}"><h3>{title}</h3><ul>{li_html}</ul></div>')
  return "".join(cards)


def build_visual_board(md_text: str) -> str:
  """Fallback：无 visual.json 时，从 Markdown 启发式生成默认看板。"""
  return f"""
  <section class="visual-board">
    <div class="visual-block">
      <h2>🎨 风格五标签 · 视觉摘要</h2>
      <div class="visual-grid">
        {style_visual_html(md_text)}
      </div>
    </div>

    <div class="visual-block">
      <h2>⭐ 关键评分 · 一眼看懂</h2>
      <div class="score-grid">
        {score_visual_html(md_text)}
      </div>
    </div>

    <div class="visual-block">
      <h2>✅ 行动结论 · 借鉴 / 规避</h2>
      <div class="action-grid">
        {action_visual_html(md_text)}
      </div>
    </div>
  </section>
  """


# ============================================================================
# Data-driven 渲染器：按 type 派发
#
# AI 通过同目录 visual.json 自由声明本次报告要展示哪些可视化模块。
# Python 只负责把 type 翻译成 HTML，不再约束章节标题与字段名。
#
# 已支持的 type:
#   - tag-cards    : 胶囊 + 色卡 + 描述（风格摘要类）
#   - score-cards  : 评分 + 进度条
#   - action-cards : 行动结论（good / bad / borrow / avoid 四色）
#   - kv-table     : 简表（键值对）
#   - info-list    : 列表
#   - quote        : 高亮引用
#   - custom-html  : AI 直接给 HTML（终极逃生口）
#
# 未匹配的 type 会输出占位提示，提醒人工/AI 检查 visual.json。
# ============================================================================


def _esc(text: Any) -> str:
  return html.escape(str(text)) if text is not None else ""


# ----------------------------------------------------------------------------
# 重点强化（rich text）：让 AI 在文字内容字段里用一组轻量级标记加重关键信息。
# - **xxx**     → 加粗 + 深色（语义：重点）
# - ==xxx==     → 黄底高亮（语义：警示 / 必须留意）
# 同时自动识别"无歧义"的数字类强信号并染色：
# - 百分比、★ 评分、排名 #530、整数 + 评价数等
# 这层只用于内容字段（desc / comment / text / hint / bullets ...），
# 标题 / 标签 / 短词字段仍走 _esc 不加重，避免"哪里都黑"。
# ----------------------------------------------------------------------------

_PLACEHOLDER_TEMPLATE = "\x00RH{i}\x00"

_AUTO_PATTERNS = [
  # ★ 评分（1.0 ★、3.5★、★★★★）。优先匹配避免被百分比规则吃掉
  (re.compile(r"(\d+(?:\.\d+)?\s*★+|★+)"), "num-star"),
  # 排名编号 #530、#243,735
  (re.compile(r"#\d{1,3}(?:,\d{3})*"), "num-rank"),
  # 百分比 86% / 14% Spandex
  (re.compile(r"\d+(?:\.\d+)?%"), "num-pct"),
]

_VERDICT_PATTERNS = [
  (re.compile(r"未建立|未承接|失分|失守|不通过|缺位|类目错位|过弱|无效流量入口"), "verdict-bad"),
  (re.compile(r"中等偏下|中等偏上|刚及格|存在(?:阶层差|错位|风险)|爬坡|可改善"), "verdict-warn"),
  (re.compile(r"已建立|完整|对齐|图文一一对应|有效"), "verdict-good"),
]


def _autohl(text: str) -> str:
  """在已 escape 的 HTML 字符串里做自动加重（不重入受 markup 保护的区段）。"""
  def repl(cls):
    return lambda m: f'<span class="{cls}">{m.group(0)}</span>'

  for pat, cls in _AUTO_PATTERNS:
    text = pat.sub(repl(cls), text)
  for pat, cls in _VERDICT_PATTERNS:
    text = pat.sub(repl(cls), text)
  return text


def _rich_text(text: Any) -> str:
  """对内容字段做"显式 markup + 自动加重"两层强化。"""
  if text is None:
    return ""
  raw = str(text)
  if not raw:
    return ""

  # 第一步：抽出 **粗** 与 ==高亮== 区段，替换为占位符，避免后续 escape 破坏
  protected: List[str] = []

  def _protect(open_tag: str, close_tag: str):
    def replacer(m: re.Match) -> str:
      inner = html.escape(m.group(1))
      # 显式加重段内仍可享受自动数字 / 评级高亮
      inner = _autohl(inner)
      idx = len(protected)
      protected.append(f"{open_tag}{inner}{close_tag}")
      return _PLACEHOLDER_TEMPLATE.format(i=idx)
    return replacer

  out = re.sub(r"\*\*(.+?)\*\*", _protect('<strong class="hl">', "</strong>"), raw)
  out = re.sub(r"==(.+?)==", _protect('<mark class="hl-mark">', "</mark>"), out)

  # 第二步：剩余文本 escape + 自动加重
  out = html.escape(out)
  out = _autohl(out)

  # 第三步：把占位符还原成保护好的 HTML
  for i, html_frag in enumerate(protected):
    out = out.replace(_PLACEHOLDER_TEMPLATE.format(i=i), html_frag)

  return out


# 大标题前的 emoji 自动剥离（仅作用于 section h2 大标题；
# hero / summary 的 icon、action-cards / two-column-list 内的子卡标题保持不变）。
_EMOJI_PREFIX_RE = re.compile(
  r"^[\s\u2300-\u23FF\u2500-\u27BF\u2B00-\u2BFF\uFE0F"
  r"\U0001F000-\U0001FAFF\U0001F100-\U0001F1FF]+"
)


def _strip_emoji_prefix(text: str) -> str:
  if not text:
    return text
  return _EMOJI_PREFIX_RE.sub("", text).lstrip()


def _wrap_block(title: str, body: str, extra_class: str = "") -> str:
  if not body.strip():
    return ""
  cls = f"visual-block {extra_class}".strip()
  clean_title = _strip_emoji_prefix(title) if title else ""
  title_html = f"<h2>{_esc(clean_title)}</h2>" if clean_title else ""
  return f'<div class="{cls}">{title_html}{body}</div>'


def render_tag_cards(section: Dict[str, Any]) -> str:
  items = section.get("items") or []
  cards = []
  for item in items:
    name = item.get("name", "")
    desc = item.get("desc", "")
    pills = item.get("pills") or []
    swatches = item.get("swatches") or []
    pill_html = "".join(
      f'<span class="pill {"dark" if i == 0 else ""}">{_esc(p)}</span>'
      for i, p in enumerate(pills)
    )
    swatch_html = ""
    if swatches:
      blocks = "".join(
        f'<span class="swatch" style="background:{_esc(c)}"></span>' for c in swatches
      )
      swatch_html = f'<div class="swatches">{blocks}</div>'
    cards.append(
      f"""
      <div class="mini-card">
        <div class="mini-card-title"><span class="dot"></span>{_esc(name)}</div>
        <div class="pill-row">{pill_html}</div>
        <p>{_rich_text(desc)}</p>
        {swatch_html}
      </div>
      """
    )
  body = f'<div class="visual-grid">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_score_cards(section: Dict[str, Any]) -> str:
  items = section.get("items") or []
  cards = []
  for item in items:
    name = item.get("name", "")
    score = item.get("score") or item.get("display") or ""
    max_v = float(item.get("max") or 5)
    raw_value = item.get("value")
    if raw_value is None:
      m = re.search(r"([0-9]+(?:\.[0-9])?)", str(score))
      raw_value = float(m.group(1)) if m else 0
    try:
      value = float(raw_value)
    except (TypeError, ValueError):
      value = 0
    width = max(0, min(100, int(value / max_v * 100))) if max_v else 0
    comment = item.get("comment") or item.get("desc") or ""
    cards.append(
      f"""
      <div class="score-card">
        <div class="score-head"><span>{_esc(name)}</span><span class="score-num">{_rich_text(score)}</span></div>
        <div class="bar"><span style="width:{width}%"></span></div>
        <p>{_rich_text(comment)}</p>
      </div>
      """
    )
  body = f'<div class="score-grid">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_action_cards(section: Dict[str, Any]) -> str:
  items = section.get("items") or []
  default_variant_title = {
    "good": "优势亮点",
    "bad": "不足问题",
    "borrow": "可借鉴点",
    "avoid": "规避方向",
  }
  cards = []
  for item in items:
    variant = item.get("variant", "good")
    title = item.get("title") or default_variant_title.get(variant, "")
    bullets = item.get("bullets") or []
    li_html = "".join(f"<li>{_rich_text(b)}</li>" for b in bullets)
    cards.append(f'<div class="action-card {_esc(variant)}"><h3>{_esc(title)}</h3><ul>{li_html}</ul></div>')
  body = f'<div class="action-grid">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_kv_table(section: Dict[str, Any]) -> str:
  rows = section.get("rows") or []
  trs = []
  manual_keys: set = set()
  for row in rows:
    if not isinstance(row, (list, tuple)) or len(row) < 2:
      continue
    k_raw = str(row[0] or "").strip()
    v_raw = str(row[1] or "").strip()
    manual_keys.add(k_raw.lower())
    v_html = _rich_text(row[1])
    # ASIN 行自动链接到 Amazon 原网址（前提：metadata 提供了 source_url）
    if (
      _CURRENT_SOURCE_URL
      and k_raw.upper() == "ASIN"
      and v_raw
      and v_raw not in ("-", "—", "N/A")
    ):
      href = html.escape(_CURRENT_SOURCE_URL, quote=True)
      v_html = (
        f'<a class="kv-link" href="{href}" target="_blank" rel="noopener" '
        f'title="在 Amazon 打开">{v_html}'
        f'<span class="kv-link-arrow">↗</span></a>'
      )
    trs.append(
      f'<tr><td class="kv-k">{_esc(row[0])}</td><td class="kv-v">{v_html}</td></tr>'
    )

  # 自动注入产品参数（格式自适应）：当 section 声明 specs_from_metadata 且 metadata 抽到了
  # specs 时，追加一个「产品参数」子区。参数标签命中映射则译中文、否则保留原文；
  # 与手写行的标签（中英文）去重；metadata 无 specs 时本段不输出任何内容。
  if section.get("specs_from_metadata") and _CURRENT_SPECS:
    spec_trs: List[str] = []
    for item in _CURRENT_SPECS:
      label = str((item or {}).get("label") or "").strip()
      value = str((item or {}).get("value") or "").strip()
      if not label or not value:
        continue
      zh = _spec_label_zh(label)
      # 去重：英文原标签、中文标签若已被手写行覆盖则跳过（如 品牌/Brand）
      if label.lower() in manual_keys or zh.strip().lower() in manual_keys:
        continue
      manual_keys.add(label.lower())
      manual_keys.add(zh.strip().lower())
      spec_trs.append(
        f'<tr><td class="kv-k">{_esc(zh)}</td><td class="kv-v">{_esc(value)}</td></tr>'
      )
    if spec_trs:
      sub_title = _esc(section.get("specs_title") or "产品参数")
      trs.append(f'<tr class="kv-sub"><td colspan="2">{sub_title}</td></tr>')
      trs.extend(spec_trs)

  body = f'<table class="kv-table">{"".join(trs)}</table>'
  return _wrap_block(section.get("title", ""), body)


def render_info_list(section: Dict[str, Any]) -> str:
  items = section.get("items") or []
  icon = section.get("icon") or "•"
  lis = "".join(
    f'<li><span class="li-icon">{_esc(icon)}</span><span>{_rich_text(x)}</span></li>'
    for x in items
  )
  body = f'<ul class="info-list">{lis}</ul>'
  return _wrap_block(section.get("title", ""), body)


def render_quote(section: Dict[str, Any]) -> str:
  text = section.get("text") or ""
  if not text:
    return ""
  body = f'<blockquote class="visual-quote">{_rich_text(text)}</blockquote>'
  return _wrap_block(section.get("title", ""), body)


def render_custom_html(section: Dict[str, Any]) -> str:
  raw = section.get("html") or ""
  if not raw:
    return ""
  return _wrap_block(section.get("title", ""), raw)


def render_step_ladder(section: Dict[str, Any]) -> str:
  """阶梯式编号卡片，适用于卖点排序、流程步骤等。

  items: [{name, desc, badge?}, ...]
  """
  items = section.get("items") or []
  cards = []
  for i, item in enumerate(items, 1):
    badge = item.get("badge") or f"{i:02d}"
    name = item.get("name", "")
    desc = item.get("desc", "")
    badge_cls = "step-num is-long" if len(str(badge)) > 3 else "step-num"
    cards.append(
      f"""
      <div class="step-card">
        <div class="{badge_cls}">{_esc(badge)}</div>
        <div class="step-body">
          <div class="step-title">{_esc(name)}</div>
          <p>{_rich_text(desc)}</p>
        </div>
      </div>
      """
    )
  body = f'<div class="step-ladder">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_info_layers(section: Dict[str, Any]) -> str:
  """带色彩编号的信息层级卡片，适用于「内容层级 / A+ 分层」类。

  items: [{layer, name, desc, color?}, ...]
  """
  items = section.get("items") or []
  default_colors = ["#2563eb", "#0891b2", "#7c3aed", "#db2777", "#ea580c", "#16a34a", "#475569"]
  rows = []
  for i, item in enumerate(items):
    layer = item.get("layer") or f"第 {i+1} 层"
    name = item.get("name", "")
    desc = item.get("desc", "")
    color = item.get("color") or default_colors[i % len(default_colors)]
    rows.append(
      f"""
      <div class="layer-row" style="--layer-color:{_esc(color)}">
        <div class="layer-pill">{_esc(layer)}</div>
        <div class="layer-body">
          <div class="layer-name">{_esc(name)}</div>
          <p>{_rich_text(desc)}</p>
        </div>
      </div>
      """
    )
  body = f'<div class="layer-stack">{"".join(rows)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_two_column_list(section: Dict[str, Any]) -> str:
  """两列并排列表，适用于「卖家诉求 vs 消费者关注 / 对比」类。

  columns: [{title, variant?, bullets[]}, {title, variant?, bullets[]}]
  """
  cols = section.get("columns") or []
  blocks = []
  for col in cols[:2]:
    variant = col.get("variant") or "default"
    title = col.get("title", "")
    bullets = col.get("bullets") or []
    lis = "".join(f"<li>{_rich_text(b)}</li>" for b in bullets)
    blocks.append(
      f'<div class="two-col-card {_esc(variant)}"><h3>{_esc(title)}</h3><ul>{lis}</ul></div>'
    )
  body = f'<div class="two-col">{"".join(blocks)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_metric_grid(section: Dict[str, Any]) -> str:
  """指标网格，适用于「品牌沉淀现状 / 关键数据」类小卡组。

  items: [{label, value, hint?, status?}, ...]
  status 可选: ok | warn | bad | info（影响左侧色带）
  """
  items = section.get("items") or []
  status_color = {
    "ok": "#16a34a",
    "warn": "#f59e0b",
    "bad": "#dc2626",
    "info": "#2563eb",
  }
  cards = []
  for item in items:
    label = item.get("label", "")
    value = item.get("value", "")
    hint = item.get("hint", "")
    status = item.get("status") or "info"
    color = status_color.get(status, "#2563eb")
    cards.append(
      f"""
      <div class="metric-card" style="--metric-color:{_esc(color)}">
        <div class="metric-label">{_esc(label)}</div>
        <div class="metric-value">{_rich_text(value)}</div>
        {f'<div class="metric-hint">{_rich_text(hint)}</div>' if hint else ''}
      </div>
      """
    )
  body = f'<div class="metric-grid">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_keyword_cloud(section: Dict[str, Any]) -> str:
  """关键词胶囊云，适用于「卖家话术高频词 / 关键词」展示。

  items: [str, ...] 或 [{text, level?}, ...]
  level: 1（弱）| 2（中）| 3（强）
  """
  items = section.get("items") or []
  pills = []
  for item in items:
    if isinstance(item, str):
      text, level = item, 2
    else:
      text = item.get("text", "")
      level = int(item.get("level") or 2)
    level = max(1, min(3, level))
    pills.append(f'<span class="kw-pill kw-l{level}">{_esc(text)}</span>')
  body = f'<div class="keyword-cloud">{"".join(pills)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_keyword_arch(section: Dict[str, Any]) -> str:
  """关键词架构（SIF 流量词反查）：核心指标条 + 流量词表。

  metrics:  [{label, value, hint?, status?}]（自然词数 / 广告词数 / 自然流量占比 / 头部词搜索量 等）
  keywords: [{kw, kw_zh?, nat_rank?, ad_rank?, search_vol?, traffic_share_pct?, positions[]?, markers[]?}]
  note?:    底部说明
  """
  status_color = {"ok": "#16a34a", "warn": "#f59e0b", "bad": "#dc2626", "info": "#2563eb"}
  mcards = []
  for it in (section.get("metrics") or []):
    color = status_color.get(it.get("status") or "info", "#2563eb")
    hint = it.get("hint", "")
    mcards.append(
      f'<div class="metric-card" style="--metric-color:{_esc(color)}">'
      f'<div class="metric-label">{_esc(it.get("label", ""))}</div>'
      f'<div class="metric-value">{_rich_text(it.get("value", ""))}</div>'
      f'{f"<div class=metric-hint>{_rich_text(hint)}</div>" if hint else ""}</div>'
    )
  mgrid = f'<div class="metric-grid">{"".join(mcards)}</div>' if mcards else ""

  rows = []
  for k in (section.get("keywords") or []):
    kw = _esc(k.get("kw", ""))
    zh = _esc(k.get("kw_zh") or "")
    nr = k.get("nat_rank")
    ar = k.get("ad_rank")
    nr_s = ("#%s" % nr) if nr not in (None, "", 0) else "—"
    ar_s = ("#%s" % ar) if ar not in (None, "", 0) else "—"
    sv = k.get("search_vol")
    sv_s = ("{:,}".format(int(sv))) if isinstance(sv, (int, float)) else "—"
    ts = k.get("traffic_share_pct")
    ts_s = ("%s%%" % ts) if ts not in (None, "") else "—"
    tagvals = list((k.get("positions") or [])[:4]) + list((k.get("markers") or [])[:3])
    tags = "".join('<span class="ka-tag">%s</span>' % _esc(t) for t in tagvals)
    zh_html = ('<br><span class="ka-zh">%s</span>' % zh) if zh else ""
    rows.append(
      '<tr><td><b>%s</b>%s</td><td class="c">%s</td><td class="c">%s</td>'
      '<td class="r">%s</td><td class="r hl">%s</td><td>%s</td></tr>'
      % (kw, zh_html, nr_s, ar_s, sv_s, ts_s, tags)
    )
  table = ""
  if rows:
    table = (
      '<style>.ka-table{width:100%;border-collapse:collapse;font-size:13px;margin-top:10px}'
      '.ka-table th{background:#f6f7f9;text-align:left;padding:8px 10px;font-weight:700;color:#475569}'
      '.ka-table td{padding:7px 10px;border-bottom:1px solid #eef0f3;vertical-align:top}'
      '.ka-table td.c{text-align:center}.ka-table td.r{text-align:right}'
      '.ka-table td.hl{font-weight:700;color:#2563eb}.ka-zh{color:#999;font-size:12px}'
      '.ka-tag{display:inline-block;background:#eef2f7;color:#475569;border-radius:6px;'
      'padding:1px 7px;margin:1px 4px 1px 0;font-size:11px}</style>'
      '<div style="overflow-x:auto"><table class="ka-table"><thead><tr>'
      '<th>流量词</th><th style="text-align:center">自然排名</th>'
      '<th style="text-align:center">广告排名</th><th style="text-align:right">周搜索量</th>'
      '<th style="text-align:right">流量占比</th><th>展示位 / 标记</th>'
      '</tr></thead><tbody>' + "".join(rows) + '</tbody></table></div>'
    )
  note = section.get("note", "")
  note_html = ('<p class="read">%s</p>' % _rich_text(note)) if note else ""
  return _wrap_block(section.get("title", ""), mgrid + table + note_html)


def render_traffic_entry(section: Dict[str, Any]) -> str:
  """流量入口结构（SIF ASIN 流量来源）：自然 vs 各类广告/推荐 的 100% 曝光占比条。

  composition: [{label, ratio, color?}]（ratio 为 0–1，渲染时归一到 100%）
  metrics?:    [{label, value, hint?, status?}]
  period?:     {total?, in?, out?, prev?}  周期新进/退出词
  note?:       底部说明
  """
  def _f(x):
    try:
      return float(x)
    except (TypeError, ValueError):
      return 0.0

  comp = section.get("composition") or []
  default_colors = ["#2fae8f", "#3b82c4", "#8b5cf6", "#d6457f", "#f0a539", "#6b7280"]
  total = sum(max(0.0, _f(c.get("ratio"))) for c in comp) or 1.0
  bar, legend = [], []
  for i, c in enumerate(comp):
    pct = max(0.0, _f(c.get("ratio"))) / total * 100
    col = c.get("color") or default_colors[i % len(default_colors)]
    lbl = _esc(c.get("label", ""))
    if pct > 0:
      bar.append('<div title="%s %.1f%%" style="width:%.2f%%;background:%s;height:100%%"></div>'
                 % (lbl, pct, pct, _esc(col)))
    legend.append(
      '<span style="display:inline-flex;align-items:center;margin:2px 14px 2px 0;font-size:13px">'
      '<i style="width:11px;height:11px;border-radius:3px;background:%s;display:inline-block;margin-right:5px"></i>'
      '%s<b style="margin-left:5px;color:#333">%.1f%%</b></span>' % (_esc(col), lbl, pct)
    )
  bar_html = ('<div style="display:flex;width:100%%;height:26px;border-radius:8px;'
              'overflow:hidden;border:1px solid #eee">%s</div>' % "".join(bar)) if bar else ""
  legend_html = ('<div style="margin-top:10px">%s</div>' % "".join(legend)) if legend else ""

  status_color = {"ok": "#16a34a", "warn": "#f59e0b", "bad": "#dc2626", "info": "#2563eb"}
  mcards = []
  for it in (section.get("metrics") or []):
    color = status_color.get(it.get("status") or "info", "#2563eb")
    hint = it.get("hint", "")
    mcards.append(
      f'<div class="metric-card" style="--metric-color:{_esc(color)}">'
      f'<div class="metric-label">{_esc(it.get("label", ""))}</div>'
      f'<div class="metric-value">{_rich_text(it.get("value", ""))}</div>'
      f'{f"<div class=metric-hint>{_rich_text(hint)}</div>" if hint else ""}</div>'
    )
  mgrid = ('<div class="metric-grid" style="margin-top:12px">%s</div>' % "".join(mcards)) if mcards else ""

  period = section.get("period") or {}
  chips = ""
  if period:
    def _chip(t, v, c):
      return ('<span style="display:inline-block;background:%s;color:#fff;border-radius:8px;'
              'padding:3px 10px;margin:2px 6px 2px 0;font-size:12px">%s %s</span>' % (c, t, v))
    parts = []
    if period.get("total") is not None:
      parts.append(_chip("流量词总数", period.get("total"), "#475569"))
    if period.get("in") is not None:
      parts.append(_chip("新进词 +", period.get("in"), "#16a34a"))
    if period.get("out") is not None:
      parts.append(_chip("退出词 -", period.get("out"), "#dc2626"))
    chips = '<div style="margin-top:10px">%s</div>' % "".join(parts)

  note = section.get("note", "")
  note_html = ('<p class="read">%s</p>' % _rich_text(note)) if note else ""
  return _wrap_block(section.get("title", ""), bar_html + legend_html + mgrid + chips + note_html)


def render_verdict_headline(section: Dict[str, Any]) -> str:
  """报告开门见山的「问题本质」punchline 大字卡。

  字段:
    headline: 主诊断（30-60 字，强约束）
    tag?:     左上小标签，默认 "问题本质"
    accent?:  色调，默认红色 #b91c1c；可选 'warn'(琥珀) / 'info'(蓝)
  """
  headline = section.get("headline") or section.get("text") or ""
  tag = section.get("tag") or "问题本质"
  accent_map = {"warn": "#b45309", "info": "#1d4ed8", "danger": "#b91c1c"}
  accent = accent_map.get(section.get("accent", "danger"), "#b91c1c")
  if not headline.strip():
    return ""
  body = f"""
  <div class="verdict-headline" style="--vh-accent:{_esc(accent)}">
    <div class="vh-tag">{_esc(tag)}</div>
    <div class="vh-text">{_rich_text(headline)}</div>
  </div>
  """
  return _wrap_block(section.get("title", ""), body, extra_class="verdict-host")


def render_best_for_grid(section: Dict[str, Any]) -> str:
  """适合谁 / 不适合谁双列网格 —— 预期管理视角。

  字段:
    best_for:  [str | {label, hint}]  应该筛进来的人
    not_for:   [str | {label, hint}]  应该挡掉的高预期错配人群
    note?:     底部短结论，例如「当前页面是否在做这个筛选」
  """
  best = section.get("best_for") or []
  notfor = section.get("not_for") or []

  def _items_html(items: List[Any], variant: str) -> str:
    rows: List[str] = []
    for it in items:
      if isinstance(it, str):
        label, hint = it, ""
      else:
        label = it.get("label", "")
        hint = it.get("hint", "")
      hint_html = f'<div class="bf-hint">{_rich_text(hint)}</div>' if hint else ""
      rows.append(
        f'<li class="bf-item"><div class="bf-label">{_rich_text(label)}</div>{hint_html}</li>'
      )
    return "".join(rows)

  best_html = f"""
  <div class="bf-card best">
    <div class="bf-head"><span class="bf-badge">✓ Best For</span><span class="bf-title">适合人群</span></div>
    <ul>{_items_html(best, 'best')}</ul>
  </div>
  """
  not_html = f"""
  <div class="bf-card avoid">
    <div class="bf-head"><span class="bf-badge">✗ Not For</span><span class="bf-title">应规避人群</span></div>
    <ul>{_items_html(notfor, 'avoid')}</ul>
  </div>
  """
  note = section.get("note")
  note_html = f'<div class="bf-note">{_rich_text(note)}</div>' if note else ""
  body = f'<div class="best-for-grid">{best_html}{not_html}</div>{note_html}'
  return _wrap_block(section.get("title", ""), body)


def render_feature_breakdown(section: Dict[str, Any]) -> str:
  """结构解释三段式 ——「部位 + 机制 + 用户感受」专业方法论。

  替代「Soft / Stretchy / Comfortable」式口号化卖点。

  字段:
    items: [{part, mechanism, feel, en?}]
      part:      部位（如「透视网纱领口」）
      mechanism: 机制（如「透气 + 无窒息感设计」）
      feel:      用户感受（如「久戴不勒颈」）
      en?:       英文卖点行（可贴回 Amazon bullets）
  """
  items = section.get("items") or []
  cards = []
  for item in items:
    part = item.get("part", "")
    mech = item.get("mechanism", "")
    feel = item.get("feel", "")
    en = item.get("en", "")
    en_html = f'<div class="fb-en">{_esc(en)}</div>' if en else ""
    cards.append(
      f"""
      <div class="fb-card">
        <div class="fb-part">📍 {_rich_text(part)}</div>
        <div class="fb-flow">
          <span class="fb-step mech">{_rich_text(mech)}</span>
          <span class="fb-arrow">→</span>
          <span class="fb-step feel">{_rich_text(feel)}</span>
        </div>
        {en_html}
      </div>
      """
    )
  body = f'<div class="feature-breakdown">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_review_sentiment(section: Dict[str, Any]) -> str:
  """评论情感解析模块 —— 真实买家声音 vs 页面叙事的对照。

  字段:
    histogram: [{star, percent}]                   星级直方图（来自 metadata.reviews.histogram）
    positive_keywords: [str | {text, count?}]      好评关键词
    critical_keywords: [str | {text, count?}]      差评关键词
    real_voice: [{stars, text, id?, variation?}]   直接展示 1-3 条买家原话
    gap_table: [{page_says, review_says}]          页面卖点 vs review 抱怨对照表
    summary?: str                                  底部一句话提炼
  """
  hist = section.get("histogram") or []
  hist_html = ""
  if hist:
    color_map = {5: "#16a34a", 4: "#65a30d", 3: "#ca8a04", 2: "#ea580c", 1: "#dc2626"}
    rows = []
    for row in sorted(hist, key=lambda r: -int(r.get("star", 0))):
      star = int(row.get("star", 0))
      pct = float(row.get("percent", 0))
      bar_color = color_map.get(star, "#94a3b8")
      rows.append(
        f"""
        <div class="rs-hist-row">
          <span class="rs-hist-label">{star}★</span>
          <div class="rs-hist-bar"><span style="width:{pct}%;background:{bar_color}"></span></div>
          <span class="rs-hist-pct">{pct:g}%</span>
        </div>
        """
      )
    hist_html = f'<div class="rs-hist">{"".join(rows)}</div>'

  def _kw_block(items: List[Any], variant: str) -> str:
    if not items:
      return ""
    pills = []
    for it in items:
      if isinstance(it, str):
        text, count = it, None
      else:
        text, count = it.get("text", ""), it.get("count")
      count_html = f'<span class="rs-kw-count">×{count}</span>' if count else ""
      pills.append(f'<span class="rs-kw {variant}">{_esc(text)}{count_html}</span>')
    return f'<div class="rs-kw-group {variant}">{"".join(pills)}</div>'

  pos = _kw_block(section.get("positive_keywords") or [], "pos")
  neg = _kw_block(section.get("critical_keywords") or [], "neg")
  kw_html = ""
  if pos or neg:
    pos_label = '<div class="rs-kw-title">✓ 好评高频词</div>' + pos if pos else ""
    neg_label = '<div class="rs-kw-title">✗ 差评高频词</div>' + neg if neg else ""
    kw_html = f'<div class="rs-kw-wrap">{pos_label}{neg_label}</div>'

  # 加权词云子块：字号随 level(1-3) 缩放，正面绿 / 负面红
  cloud_items = section.get("word_cloud") or []
  cloud_html = ""
  if cloud_items:
    pills = []
    for it in cloud_items:
      if isinstance(it, str):
        text, level, sentiment, count = it, 2, "pos", None
      else:
        text = it.get("text", "")
        level = max(1, min(3, int(it.get("level") or 2)))
        sentiment = "neg" if it.get("sentiment") == "neg" else "pos"
        count = it.get("count")
      if not str(text).strip():
        continue
      count_html = f'<span class="rs-cloud-count">×{count}</span>' if count else ""
      pills.append(
        f'<span class="rs-cloud-pill lv{level} {sentiment}">{_esc(text)}{count_html}</span>'
      )
    if pills:
      cloud_html = (
        '<div class="rs-cloud-title">☁️ 评论词云（字号随提及频次）</div>'
        '<div class="rs-cloud-legend">'
        '<span class="pos"><b>● 好评向</b></span>'
        '<span class="neg"><b>● 差评向</b></span></div>'
        f'<div class="rs-cloud">{"".join(pills)}</div>'
      )

  voices = section.get("real_voice") or []
  voice_html = ""
  if voices:
    cards = []
    for v in voices:
      stars = v.get("stars")
      txt = v.get("text", "")
      # variation 容错：兼容 dict / str / list 三种写法，避免传字符串时
      # "for k in var" 误把字符串当 dict 迭代导致 "string indices must be integers"
      var_raw = v.get("variation") or ""
      if isinstance(var_raw, dict):
        var_str = " · ".join(
          f"{str(k).capitalize()}: {var_raw[k]}" for k in var_raw if var_raw.get(k)
        )
      elif isinstance(var_raw, (list, tuple)):
        var_str = " · ".join(str(x) for x in var_raw if x)
      else:
        var_str = str(var_raw).strip()
      var_html = f'<div class="rs-voice-meta">{_esc(var_str)}</div>' if var_str else ""
      star_html = ""
      if stars is not None:
        try:
          n = int(round(float(stars)))
          star_html = '<div class="rs-voice-stars">' + "★" * n + "<span class=\"rs-voice-dim\">" + "☆" * (5 - n) + "</span></div>"
        except (TypeError, ValueError):
          pass
      cards.append(f'<blockquote class="rs-voice">{star_html}<p>{_rich_text(txt)}</p>{var_html}</blockquote>')
    voice_html = f'<div class="rs-voice-list">{"".join(cards)}</div>'

  gap_rows = section.get("gap_table") or []
  gap_html = ""
  if gap_rows:
    rows = []
    for g in gap_rows:
      page_says = g.get("page_says", "")
      review_says = g.get("review_says", "")
      rows.append(
        f"<tr><td class='rs-gap-page'>{_rich_text(page_says)}</td>"
        f"<td class='rs-gap-arrow'>→</td>"
        f"<td class='rs-gap-review'>{_rich_text(review_says)}</td></tr>"
      )
    gap_html = (
      '<div class="rs-gap-wrap">'
      '<div class="rs-gap-header">🆚 页面卖点 vs 真实评论 · 预期管理缝隙</div>'
      '<table class="rs-gap-table">'
      '<thead><tr><th>页面是这么说的</th><th></th><th>买家实际反馈</th></tr></thead>'
      f'<tbody>{"".join(rows)}</tbody>'
      '</table>'
      '</div>'
    )

  summary = section.get("summary")
  summary_html = f'<div class="rs-summary">{_rich_text(summary)}</div>' if summary else ""

  body = f"{hist_html}{kw_html}{cloud_html}{voice_html}{gap_html}{summary_html}"
  return _wrap_block(section.get("title", ""), body)


def render_look_suite(section: Dict[str, Any]) -> str:
  """场景图 Look 命名建议 ——「Jeans Look / Skirt Look / Blazer Look」式拆解。

  字段:
    items: [{name, desc?, accent?, en?}]
  """
  items = section.get("items") or []
  default_accents = ["#1d4ed8", "#0891b2", "#7c3aed", "#db2777", "#ea580c", "#16a34a"]
  cards = []
  for i, item in enumerate(items):
    name = item.get("name", "")
    desc = item.get("desc", "")
    en = item.get("en", "")
    accent = item.get("accent") or default_accents[i % len(default_accents)]
    en_html = f'<div class="ls-en">{_esc(en)}</div>' if en else ""
    desc_html = f'<p>{_rich_text(desc)}</p>' if desc else ""
    cards.append(
      f"""
      <div class="ls-card" style="--ls-accent:{_esc(accent)}">
        <div class="ls-icon">👗</div>
        <div class="ls-name">{_esc(name)}</div>
        {en_html}
        {desc_html}
      </div>
      """
    )
  body = f'<div class="look-suite">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_w5h2_grid(section: Dict[str, Any]) -> str:
  """5W2H 客户购买行为分析 —— Who / What / When / Where / Why / How / How much。

  把"卖给谁、卖什么、何时何地、为何买、怎么决策、花多少"拆成 7 张卡，
  让竞品定位与购买逻辑一目了然。

  字段:
    items: [{key, zh?, q?, finding, evidence?, accent?}]
      key:       5W2H 维度英文（Who / What / When / Where / Why / How / How much）
      zh:        中文小标题（如"谁在买"）
      q:         该维度要回答的问题（灰字提示）
      finding:   竞品在该维度上的实际打法 / 推断结论
      evidence?: 依据（评论变体 / 页面定位 / bullets 关键词）
  """
  items = section.get("items") or []
  accent_map = {
    "who": "#2563eb", "what": "#0891b2", "when": "#7c3aed",
    "where": "#db2777", "why": "#dc2626", "how": "#ea580c",
    "how much": "#16a34a", "howmuch": "#16a34a", "how-much": "#16a34a",
  }
  cards = []
  for it in items:
    key = str(it.get("key") or "")
    accent = it.get("accent") or accent_map.get(key.strip().lower(), "#2563eb")
    zh = it.get("zh") or it.get("label") or it.get("title") or ""
    q = it.get("q") or it.get("question") or ""
    finding = (
      it.get("finding")
      or it.get("value")
      or it.get("desc")
      or it.get("text")
      or it.get("answer")
      or ""
    )
    ev = it.get("evidence") or ""
    zh_html = f'<span class="w5h2-label w5h2-zh">{_esc(zh)}</span>' if zh else ""
    q_html = f'<div class="w5h2-q">{_esc(q)}</div>' if q else ""
    ev_html = f'<div class="w5h2-ev">📎 {_rich_text(ev)}</div>' if ev else ""
    cards.append(
      f"""
      <div class="w5h2-card" style="--w-accent:{_esc(accent)}">
        <div class="w5h2-head">
          <span class="w5h2-key">{_esc(key)}</span>
          {zh_html}
        </div>
        {q_html}
        <div class="w5h2-finding w5h2-value">{_rich_text(finding)}</div>
        {ev_html}
      </div>
      """
    )
  body = f'<div class="w5h2-grid">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_persona_cards(section: Dict[str, Any]) -> str:
  """客户画像卡 —— 把抽象受众落成 1-N 个有名有姓的典型买家。

  字段:
    items: [{name, emoji?, tags[], demographic?, scenario?, motivation?, pain?, quote?}]
      name:        画像名（如"通勤塑形党 · Linda"）
      emoji:       头像 emoji，默认 👤
      tags:        标签（年龄段 / 身份 / 价格敏感度等）
      demographic: 人群画像
      scenario:    典型使用场景
      motivation:  核心购买动机
      pain:        主要顾虑 / 痛点
      quote:       一句代表性买家原话（来自评论证据）
  """
  items = section.get("items") or []
  cards = []
  for it in items:
    name = it.get("name") or ""
    emoji = it.get("emoji") or "👤"
    tags = it.get("tags") or []
    tag_html = "".join(f'<span class="persona-tag">{_esc(t)}</span>' for t in tags)
    rows = []
    for label, val in (
      ("画像", it.get("demographic")),
      ("场景", it.get("scenario")),
      ("动机", it.get("motivation")),
      ("顾虑", it.get("pain")),
    ):
      if val:
        rows.append(
          f'<div class="persona-row"><div class="persona-row-k">{label}</div>'
          f'<div class="persona-row-v">{_rich_text(val)}</div></div>'
        )
    quote = it.get("quote")
    quote_html = (
      f'<blockquote class="persona-quote"><p>“{_rich_text(quote)}”</p></blockquote>'
      if quote else ""
    )
    cards.append(
      f"""
      <div class="persona-card">
        <div class="persona-head">
          <div class="persona-avatar">{_esc(emoji)}</div>
          <div>
            <div class="persona-name">{_esc(name)}</div>
            <div class="persona-tags">{tag_html}</div>
          </div>
        </div>
        <div class="persona-body">{"".join(rows)}</div>
        {quote_html}
      </div>
      """
    )
  body = f'<div class="persona-grid">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


_KANO_META = {
  "must-be": ("基本型需求", "Must-be", "缺失即差评、做到也不加分（保命线）", "#dc2626", "#fef2f2"),
  "must_be": ("基本型需求", "Must-be", "缺失即差评、做到也不加分（保命线）", "#dc2626", "#fef2f2"),
  "basic": ("基本型需求", "Must-be", "缺失即差评、做到也不加分（保命线）", "#dc2626", "#fef2f2"),
  "one-dimensional": ("期望型需求", "One-dimensional", "越好越满意、线性正相关（拉开差距）", "#ea580c", "#fff7ed"),
  "one_dimensional": ("期望型需求", "One-dimensional", "越好越满意、线性正相关（拉开差距）", "#ea580c", "#fff7ed"),
  "performance": ("期望型需求", "One-dimensional", "越好越满意、线性正相关（拉开差距）", "#ea580c", "#fff7ed"),
  "attractive": ("兴奋型需求", "Attractive", "超出预期的惊喜、差异化爆点", "#16a34a", "#f0fdf4"),
  "delight": ("兴奋型需求", "Attractive", "超出预期的惊喜、差异化爆点", "#16a34a", "#f0fdf4"),
  "indifferent": ("无差异需求", "Indifferent", "有没有都无所谓、勿过度投入", "#64748b", "#f8fafc"),
  "reverse": ("反向型需求", "Reverse", "做了反而引发反感、需谨慎", "#7c3aed", "#f5f3ff"),
}


def render_kano_model(section: Dict[str, Any]) -> str:
  """Kano 模型真实需求 —— 把买家需求按"基本 / 期望 / 兴奋 / 无差异 / 反向"分类。

  从评论证据反推：差评里"理应有却没有"的 = 基本型；好评/差评里"越多越满意"
  的 = 期望型；惊喜原话 = 兴奋型。指导本品做产品时"先保命、再拉分、后造爆点"。

  字段:
    groups: [{kano, items[]}]
      kano: must-be | one-dimensional | attractive | indifferent | reverse
      items: [str] 或 [{need, evidence?}]
  """
  groups = section.get("groups") or []
  blocks = []
  for g in groups:
    kano = str(g.get("kano") or g.get("category") or "").strip().lower()
    zh, en, desc, color, bg = _KANO_META.get(
      kano, (g.get("label") or kano or "需求", "", "", "#2563eb", "#f8fafc")
    )
    items = g.get("items") or []
    lis = []
    for it in items:
      if isinstance(it, str):
        need, ev = it, ""
      else:
        need = it.get("need") or it.get("text") or ""
        ev = it.get("evidence") or ""
      ev_html = f'<div class="kano-ev">📎 {_rich_text(ev)}</div>' if ev else ""
      lis.append(
        f'<li class="kano-item"><div class="kano-need">{_rich_text(need)}</div>{ev_html}</li>'
      )
    blocks.append(
      f"""
      <div class="kano-group" style="--kano-color:{_esc(color)};--kano-bg:{_esc(bg)}">
        <div class="kano-group-head">
          <div><span class="kano-cat">{_esc(zh)}</span> <span class="kano-cat-en">{_esc(en)}</span></div>
          <div class="kano-desc">{_esc(desc)}</div>
        </div>
        <ul class="kano-list">{"".join(lis)}</ul>
      </div>
      """
    )
  body = f'<div class="kano-stack">{"".join(blocks)}</div>'
  return _wrap_block(section.get("title", ""), body)


def render_dev_watchpoints(section: Dict[str, Any]) -> str:
  """产品开发注意点 —— 把竞品分析的洞察落成做本品时的可执行清单。

  字段:
    items: [{priority, point, rationale?, category?, accent?}]
      priority:  优先级（P0 / P1 / P2 或 高 / 中 / 低）
      point:     一句话注意点
      rationale: 依据（来自评论/Kano/5W2H 的推断）
      category:  类型（must-fix 必须修复 / improve 持续改进 / innovate 创新爆点）
  """
  items = section.get("items") or []
  pri_color = {
    "p0": "#dc2626", "p1": "#ea580c", "p2": "#2563eb", "p3": "#64748b",
    "高": "#dc2626", "中": "#ea580c", "低": "#64748b",
  }
  cat_label = {
    "must-fix": "必须修复", "must_fix": "必须修复",
    "improve": "持续改进", "innovate": "创新爆点",
  }
  cards = []
  for it in items:
    pri = str(it.get("priority") or "P1")
    color = it.get("accent") or pri_color.get(pri.strip().lower(), "#2563eb")
    point = it.get("point") or it.get("text") or ""
    rationale = it.get("rationale") or it.get("desc") or ""
    cat = it.get("category") or it.get("kind") or ""
    cat_disp = cat_label.get(str(cat).strip().lower(), cat)
    rat_html = f'<div class="dev-rationale">{_rich_text(rationale)}</div>' if rationale else ""
    cat_html = f'<div class="dev-cat">{_esc(cat_disp)}</div>' if cat_disp else ""
    cards.append(
      f"""
      <div class="dev-card">
        <span class="dev-pri" style="--dev-color:{_esc(color)}">{_esc(pri)}</span>
        <div>
          <div class="dev-point">{_rich_text(point)}</div>
          {rat_html}
          {cat_html}
        </div>
      </div>
      """
    )
  body = f'<div class="dev-list">{"".join(cards)}</div>'
  return _wrap_block(section.get("title", ""), body)


SECTION_RENDERERS = {
  "tag-cards": render_tag_cards,
  "score-cards": render_score_cards,
  "action-cards": render_action_cards,
  "kv-table": render_kv_table,
  "info-list": render_info_list,
  "quote": render_quote,
  "custom-html": render_custom_html,
  "step-ladder": render_step_ladder,
  "info-layers": render_info_layers,
  "two-column-list": render_two_column_list,
  "metric-grid": render_metric_grid,
  "keyword-cloud": render_keyword_cloud,
  "keyword-arch": render_keyword_arch,
  "traffic-entry": render_traffic_entry,
  "verdict-headline": render_verdict_headline,
  "best-for-grid": render_best_for_grid,
  "feature-breakdown": render_feature_breakdown,
  "look-suite": render_look_suite,
  "review-sentiment": render_review_sentiment,
  "w5h2-grid": render_w5h2_grid,
  "persona-cards": render_persona_cards,
  "kano-model": render_kano_model,
  "dev-watchpoints": render_dev_watchpoints,
}


def render_section(section: Dict[str, Any]) -> str:
  if not isinstance(section, dict):
    return ""
  stype = section.get("type", "")
  renderer = SECTION_RENDERERS.get(stype)
  if renderer is None:
    fallback = (
      f'<div class="visual-warn">⚠️ 未识别的 section type: <code>{_esc(stype)}</code>。'
      f"请在 visual.json 中改用受支持的类型，或使用 <code>custom-html</code> 自定义渲染。</div>"
    )
    return _wrap_block(section.get("title", ""), fallback)
  return renderer(section)


def build_visual_board_from_data(data: Dict[str, Any]) -> str:
  sections = data.get("sections") or []
  body = "".join(render_section(s) for s in sections)
  if not body.strip():
    return ""
  return f'<section class="visual-board">{body}</section>'


def _ensure_star_text(value: float) -> str:
  return f"{value:.1f} ★"


def _find_metric_item(data: Dict[str, Any], label: str) -> Dict[str, Any] | None:
  for sec in data.get("sections") or []:
    if sec.get("type") != "metric-grid":
      continue
    for item in sec.get("items") or []:
      if item.get("label") == label:
        return item
  return None


def _find_score_item(data: Dict[str, Any], name: str) -> Dict[str, Any] | None:
  for sec in data.get("sections") or []:
    if sec.get("type") != "score-cards":
      continue
    for item in sec.get("items") or []:
      if item.get("name") == name:
        return item
  return None


def _update_summary_total(data: Dict[str, Any], total: float) -> None:
  new_val = f"{total:.1f} / 5.0"
  for card in data.get("summary") or []:
    if card.get("label") == "加权总分":
      old_val = str(card.get("value") or "")
      # 证据护栏重算覆盖作者手写总分时打印告警，避免"分数被静默改写"导致
      # md/visual/html 不一致（旧坑：作者写 3.1，评分卡加权和 3.3，被静默改成 3.3）
      old_num = re.search(r"([0-9]+(?:\.[0-9])?)", old_val)
      if old_num and abs(float(old_num.group(1)) - round(total, 1)) >= 0.05:
        print(
          f"[⚠️ 总分护栏覆盖] visual.json 手写加权总分 {old_num.group(1)} "
          f"与 5 维评分卡加权和 {total:.1f} 不一致，已按评分卡重算为 {new_val}。"
          f"请同步修正 .md 与 visual.json 的总分，使三处一致。",
          file=sys.stderr,
        )
      card["value"] = new_val


def apply_evidence_guards(data: Dict[str, Any]) -> Dict[str, Any]:
  """证据护栏：把易错字段绑定到 evidence，避免拍脑袋估算。

  当前强制项：
  - evidence.logo_mentions（例如 ["g01_04", "g02_01"]）
    -> 自动回填「Logo 出现位置」文案
    -> 自动校正「品牌沉淀」score-card（<=2 次时上限 2.5）
    -> 自动重算 summary 的加权总分（沿用 0.25/0.20/0.20/0.15/0.20）
  """
  if not isinstance(data, dict):
    return data

  evidence = data.get("evidence") or {}
  logo_mentions = evidence.get("logo_mentions")
  if not isinstance(logo_mentions, list):
    return data

  # 1) 用证据数组回填 metric-grid 中的 Logo 出现位置
  metric_logo = _find_metric_item(data, "Logo 出现位置")
  count = len(logo_mentions)
  mention_text = " / ".join(str(x) for x in logo_mentions) if logo_mentions else "无"
  if metric_logo is not None:
    metric_logo["value"] = f"{count} 次（{mention_text}）" if count else "0 次"
    metric_logo["hint"] = "证据来源：visual.json.evidence.logo_mentions"
    metric_logo["status"] = "ok" if count >= 3 else ("warn" if count == 2 else "bad")

  # 2) 品牌沉淀评分护栏（防止又写成 3.0/3.5 这类与证据冲突的分）
  brand_score = _find_score_item(data, "品牌沉淀")
  if brand_score is not None:
    try:
      value = float(brand_score.get("value"))
    except Exception:
      m = re.search(r"([0-9]+(?:\.[0-9])?)", str(brand_score.get("score", "")))
      value = float(m.group(1)) if m else 0.0
    if count <= 2 and value > 2.5:
      value = 2.5
      brand_score["comment"] = (
        f"依据证据数组，Logo 仅 {count} 次出现（{mention_text}），"
        "其余模块无品牌字样；纯黑细字且无视觉锤配对，品牌沉淀上限按 2.5 控制。"
      )
    brand_score["value"] = value
    brand_score["score"] = _ensure_star_text(value)

  # 3) 重算总分（仅在 5 维评分存在时）
  weights = {
    "视觉一致性": 0.25,
    "信息层级": 0.20,
    "图文契合度": 0.20,
    "连贯叙事效率": 0.15,
    "品牌沉淀": 0.20,
  }
  got: Dict[str, float] = {}
  for k in weights:
    it = _find_score_item(data, k)
    if it is None:
      continue
    try:
      got[k] = float(it.get("value"))
    except Exception:
      m = re.search(r"([0-9]+(?:\.[0-9])?)", str(it.get("score", "")))
      got[k] = float(m.group(1)) if m else 0.0
  if len(got) == len(weights):
    total = sum(got[k] * weights[k] for k in weights)
    _update_summary_total(data, total)

  return data


def build_summary_from_data(
  data: Dict[str, Any],
  metadata: Dict[str, Any],
  report: Dict[str, Any],
  score: str,
) -> str:
  """visual.json 内 hero / summary 字段优先，未配置则回退到原默认摘要。"""
  hero = data.get("hero") or {}
  hero_title = hero.get("title") or "📊 Amazon 竞品分析可视化看板"
  hero_sub = hero.get("subtitle") or "把分析文字、套图与 A+ 内容放在同一视图中，降低来回切换成本。"

  summary_cards = data.get("summary")
  if not summary_cards:
    return build_summary(metadata, report, score)

  card_html = "".join(
    f'<div class="summary"><div class="k">{_esc(c.get("icon", ""))} {_esc(c.get("label", ""))}</div>'
    f'<div class="v">{_esc(c.get("value", "-"))}</div></div>'
    for c in summary_cards
  )

  notes_html = ""
  notes = data.get("summary_notes") or []
  if notes:
    note_blocks = "".join(
      f'<div class="summary" style="grid-column: 1 / -1;">'
      f'<div class="k">{_esc(n.get("icon", ""))} {_esc(n.get("label", ""))}</div>'
      f'<div class="v" style="font-size:16px;">{_esc(n.get("value", "-"))}</div></div>'
      for n in notes
    )
    notes_html = f'<section class="summary-grid">{note_blocks}</section>'

  url = (metadata.get("source_url") or "").strip() if metadata else ""
  hero_link_html = _hero_amazon_link(url)
  dash_link_html = _hero_dashboard_link(_CURRENT_DASHBOARD)
  return f"""
  <section class="hero">
    <div class="hero-text">
      <h1>{_esc(hero_title)}</h1>
      <p>{_esc(hero_sub)}</p>
    </div>
    {dash_link_html}
    {hero_link_html}
  </section>
  <section class="summary-grid">
    {card_html}
  </section>
  {notes_html}
  """


def build_left_panel(report: Dict[str, Any], base_dir: Path) -> str:
  gallery_files: List[str] = (report.get("gallery") or {}).get("files") or []
  aplus_groups: List[Dict[str, Any]] = (report.get("aplus") or {}).get("groups") or []

  gallery_main = ""
  thumbs_html = ""
  if gallery_files:
    gallery_main = rel_or_uri(gallery_files[0], base_dir)
    thumb_nodes = []
    for i, g in enumerate(gallery_files):
      src = rel_or_uri(g, base_dir)
      active = "active" if i == 0 else ""
      thumb_nodes.append(
        f'<img src="{src}" data-full="{src}" class="{active}" alt="gallery-{i+1}" />'
      )
    thumbs_html = "\n".join(thumb_nodes)

  aplus_nodes = []
  for g in aplus_groups:
    files = g.get("files") or []
    idx = g.get("index", 0)
    if not files:
      continue
    slide_nodes = []
    dot_nodes = []
    multi = len(files) > 1
    for i, f in enumerate(files):
      src = rel_or_uri(f, base_dir)
      active = "active" if i == 0 else ""
      tag_text = f"g{idx:02d}-{i+1}" if multi else f"g{idx:02d}"
      slide_nodes.append(
        f'<div class="aplus-slide {active}">'
        f'<img src="{src}" alt="aplus-g{idx}-{i+1}" />'
        f'<span class="aplus-tag">{tag_text}</span>'
        f'</div>'
      )
      dot_nodes.append(f'<span class="aplus-dot {"active" if i == 0 else ""}"></span>')
    is_slider = "1" if len(files) > 1 else "0"
    nav_html = ""
    dots_html = ""
    if len(files) > 1:
      nav_html = (
        '<button class="aplus-nav aplus-prev" aria-label="prev">‹</button>'
        '<button class="aplus-nav aplus-next" aria-label="next">›</button>'
      )
      dots_html = f'<div class="aplus-dots">{"".join(dot_nodes)}</div>'
    aplus_nodes.append(
      f"""
      <div class="aplus-card" data-slider="{is_slider}">
        <div class="aplus-stage">
          {''.join(slide_nodes)}
          {nav_html}
          {dots_html}
        </div>
      </div>
      """
    )

  return f"""
  <aside class="panel left-wrap">
    <div class="section-title"><span class="icon-dot"></span>套图侧栏预览</div>
    <div class="gallery-preview">
      <img class="gallery-main" src="{gallery_main}" alt="gallery-main" />
      <div class="thumbs">
        {thumbs_html}
      </div>
    </div>
    <div class="section-title"><span class="icon-dot"></span>A+ 模块预览（含横向切换）</div>
    <div class="aplus-stream">
      {''.join(aplus_nodes)}
    </div>
  </aside>
  """


def build_summary(metadata: Dict[str, Any], report: Dict[str, Any], score: str) -> str:
  brand = html.escape(str(metadata.get("brand") or "-"))
  rating = metadata.get("rating")
  rating_text = f"{rating}" if rating is not None else "-"
  rating_count = metadata.get("rating_count") or "-"
  gallery_count = (report.get("gallery") or {}).get("downloaded_count") or "-"
  aplus_count = (report.get("aplus") or {}).get("group_count") or "-"
  bsr = "-"
  ranks = metadata.get("category_rank") or []
  if ranks:
    first = ranks[0]
    bsr = f'{first.get("rank", "-")} · {first.get("category", "-")}'
  url = (metadata.get("source_url") or "").strip() if metadata else ""
  hero_link_html = _hero_amazon_link(url)
  dash_link_html = _hero_dashboard_link(_CURRENT_DASHBOARD)
  return f"""
  <section class="hero">
    <div class="hero-text">
      <h1>📊 Amazon 竞品分析可视化看板</h1>
      <p>把分析文字、套图与 A+ 内容放在同一视图中，降低来回切换成本。</p>
    </div>
    {dash_link_html}
    {hero_link_html}
  </section>
  <section class="summary-grid">
    <div class="summary"><div class="k">🏷 品牌</div><div class="v">{brand}</div></div>
    <div class="summary"><div class="k">⭐ 星级 / 评价</div><div class="v">{rating_text} / {rating_count}</div></div>
    <div class="summary"><div class="k">🧩 套图 / A+模块</div><div class="v">{gallery_count} / {aplus_count}</div></div>
    <div class="summary"><div class="k">🎯 加权总分</div><div class="v">{score}</div></div>
  </section>
  <section class="summary-grid">
    <div class="summary" style="grid-column: 1 / -1;">
      <div class="k">📌 类目排名（首条）</div><div class="v" style="font-size:16px;">{html.escape(bsr)}</div>
    </div>
  </section>
  """


def build_right_panel(
  md_html: str,
  metadata: Dict[str, Any],
  report: Dict[str, Any],
  score: str,
  md_text: str,
  visual_data: Dict[str, Any] | None = None,
) -> str:
  # 默认策略：当 visual.json 存在且 sections 非空时，默认隐藏 Markdown 全文
  # （AI 既然写了 visual.json 就说明信息已在卡片里，再贴一遍 md 全文是冗余）。
  # 若 AI 想保留 md 全文做参照，在 visual.json 显式写 "hide_full_markdown": false。
  if visual_data:
    summary = build_summary_from_data(visual_data, metadata, report, score)
    visual_board = build_visual_board_from_data(visual_data)
    if not visual_board:
      visual_board = build_visual_board(md_text)
    has_sections = bool(visual_data.get("sections"))
    if "hide_full_markdown" in visual_data:
      hide_md = bool(visual_data.get("hide_full_markdown"))
    else:
      hide_md = has_sections
  else:
    summary = build_summary(metadata, report, score)
    visual_board = build_visual_board(md_text)
    hide_md = False
  generated = dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
  content_block = (
    f'<div class="meta-card">🕒 生成时间：{generated}</div>'
    if hide_md
    else f"""
    <article class="content-card">
      {md_html}
      <div class="meta">🕒 生成时间：{generated}</div>
    </article>
    """
  )
  return f"""
  <main class="right-wrap">
    {summary}
    {visual_board}
    {content_block}
  </main>
  """


def main() -> int:
  args = parse_args()
  in_path = Path(args.input).expanduser().resolve()
  if not in_path.exists():
    raise FileNotFoundError(f"输入文件不存在: {in_path}")

  base_dir = in_path.parent
  # 默认输出固定为同目录下的 index.html（与交互式评论看板 review_dashboard.html 互联）。
  # 历史版本默认输出 competitor_analysis.html，现统一改为 index.html，便于直接作为目录首页打开。
  out_path = (
    Path(args.output).expanduser().resolve()
    if args.output
    else base_dir / "index.html"
  )

  md_text = in_path.read_text(encoding="utf-8", errors="ignore")
  md_html = to_html(md_text)
  score = extract_score(md_text)

  report = load_json(base_dir / "report.json")
  metadata = load_json(base_dir / "metadata.json")

  global _CURRENT_SOURCE_URL, _CURRENT_DASHBOARD, _CURRENT_SPECS
  _CURRENT_SOURCE_URL = (metadata.get("source_url") or "").strip() if isinstance(metadata, dict) else ""
  _CURRENT_DASHBOARD = "review_dashboard.html" if (base_dir / "review_dashboard.html").exists() else ""
  _CURRENT_SPECS = (metadata.get("specs") or []) if isinstance(metadata, dict) else []

  visual_path = base_dir / "visual.json"
  visual_data: Dict[str, Any] | None = None
  if visual_path.exists():
    try:
      visual_data = json.loads(visual_path.read_text(encoding="utf-8"))
      if not isinstance(visual_data, dict):
        print(f"[warn] visual.json 顶层应是 object，已忽略：{visual_path}")
        visual_data = None
      else:
        visual_data = apply_evidence_guards(visual_data)
    except Exception as exc:
      print(f"[warn] 解析 visual.json 失败，已回退到启发式渲染：{exc}")
      visual_data = None
  else:
    msg = (
      "\n"
      "================================================================\n"
      "[WARN] 未发现 visual.json，已回退到启发式渲染（含 Markdown 全文区）。\n"
      f"       建议在同目录补一份 visual.json 以获得纯卡片化效果：\n"
      f"       {visual_path}\n"
      "       数据契约见 .codex/skills/amazon-competitor-analyzer/SKILL.md §4.1。\n"
      "================================================================\n"
    )
    try:
      print(msg)
    except UnicodeEncodeError:
      print(msg.encode("ascii", "replace").decode("ascii"))

  left_panel = build_left_panel(report, base_dir)
  right_panel = build_right_panel(md_html, metadata, report, score, md_text, visual_data)

  floating_html = _floating_dashboard_link(_CURRENT_DASHBOARD) + _floating_amazon_link(_CURRENT_SOURCE_URL)

  full_html = (
    HTML_TEMPLATE.replace("__TITLE__", html.escape(in_path.stem))
    .replace("__CSS__", CSS)
    .replace("__FLOATING__", floating_html)
    .replace("__LEFT__", left_panel)
    .replace("__RIGHT__", right_panel)
    .replace("__JS__", JS)
  )

  out_path.write_text(full_html, encoding="utf-8")
  print(f"[ok] html generated: {out_path}")
  return 0


if __name__ == "__main__":
  raise SystemExit(main())
