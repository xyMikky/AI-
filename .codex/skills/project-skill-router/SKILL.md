---
name: project-skill-router
description: 当前项目的全局 Skill 路由入口。凡用户在本项目中提出任何任务，都应优先检查并使用 `.codex/skills/` 下的项目本地 Skill，而不是系统 Skill。适用于任务类型不确定、多个 Skill 可能匹配、需要在设计 / 生图 / Amazon 竞品 / 评论 / ABA / SIF / 标题分析 / 品牌规范 / 参考库学习 / Skill 维护 / 工作流记录之间选择入口的场景。默认规则：项目本地 Skill 优先；只有用户明确要求系统/内置 Skill、项目没有覆盖能力、项目 Skill 需要系统工具执行、或更高优先级平台规则强制要求时，才使用系统 Skill。关键词：项目Skill优先、默认使用项目Skill、不要系统Skill、路由、任务分发、全局入口、project skill router。
---

# Project Skill Router

## Rule

For this repository, route tasks to project-local Skills under `.codex/skills/` before using system Skills.

Use this Skill when the correct project Skill is not obvious, or when a request could match multiple Skills.

## Routing Map

| User Intent | Route |
|---|---|
| Generate or edit images | `project-image-generation-router` |
| Build image prompts | `ai-image-prompt-builder` |
| Run image-to-image | `rh-image-pro-img2img` |
| Run text-to-image | `rh-image-pro-txt2img` |
| Check image-generation logic | `ai-image-logic-checker` |
| Amazon competitor analysis / ASIN reports | `amazon-competitor-analysis-controller` |
| Quick Amazon competitor read | `amazon-competitor-quick-analyzer` |
| Extract Amazon listing images | `amazon-image-extractor` |
| Analyze Amazon reviews | `linkfox-amazon-reviews` |
| Analyze ABA search terms | `linkfox-aba-data-explorer` |
| Analyze SIF ASIN keywords | `linkfox-sif-asin-keywords` |
| Analyze SIF ASIN traffic summary | `linkfox-sif-asin-summary` |
| Analyze keyword traffic competition | `linkfox-sif-keyword-traffic` |
| Analyze product titles | `linkfox-product-title-analyze` |
| Design logo / color / typography / UI / print / detail page | corresponding design Skill |
| Learn brand specs | `brand-spec-learner` |
| Learn references | `reference-library-learner` |
| Create brand asset sheet | `brand-asset-sheet` |
| Generate color palette image | `color-palette-generator` |
| Convert or maintain Skills | `skill-converter` |
| Diagnose project logic chain | `logic-chain-diagnostic` |
| Manage work logs | `work-log-manager` |

## Boundary

System Skills are allowed only as execution helpers or fallback when:

- the user explicitly requests them,
- no project-local Skill covers the task,
- a project Skill says to use that system tool,
- or higher-priority platform instructions require the system Skill.

When in doubt, choose the project Skill first and explain the routing briefly.

