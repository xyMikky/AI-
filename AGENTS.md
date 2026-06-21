# Project Agent Instructions

## Project Skill Priority

This repository is a Codex Skill project. For every task in this workspace, prefer the project-local Skills under `.codex/skills/` over system Skills with similar capabilities.

Default routing rule:

1. Check whether a project-local Skill matches the user's request.
2. If a matching project Skill exists, use it as the primary workflow.
3. Use `project-skill-router` as the first stop when the right project Skill is not obvious.
4. Use system Skills only when:
   - the user explicitly asks for a system/built-in Skill or tool,
   - no project-local Skill covers the task,
   - the project-local Skill depends on a system tool for execution,
   - or higher-priority platform instructions require it.

Do not bypass project Skills merely because a system Skill has a broader description.

## Default Routing Map

Use these project-local Skills first:

| Task Type | Preferred Project Skill |
|---|---|
| Image generation, image editing, img2img, txt2img, product photo edits, interior edits | `project-image-generation-router` |
| Image prompt building | `ai-image-prompt-builder` |
| Image pre/post logic checks | `ai-image-logic-checker` |
| RunningHub image-to-image execution | `rh-image-pro-img2img` |
| RunningHub text-to-image execution | `rh-image-pro-txt2img` |
| Amazon competitor analysis, ASIN analysis, multi-ASIN reports | `amazon-competitor-analysis-controller` |
| Quick Amazon competitor analysis | `amazon-competitor-quick-analyzer` |
| Amazon image extraction | `amazon-image-extractor` |
| Amazon reviews | `linkfox-amazon-reviews` |
| Amazon ABA/search term research | `linkfox-aba-data-explorer` |
| Amazon SIF keyword or traffic analysis | `linkfox-sif-asin-keywords`, `linkfox-sif-asin-summary`, `linkfox-sif-keyword-traffic` |
| Product title analysis | `linkfox-product-title-analyze` |
| Brand/logo/color/type/UI/print/detail-page design | corresponding design Skills under `.codex/skills/` |
| Brand asset sheet or color palette generation | `brand-asset-sheet`, `color-palette-generator` |
| Reference library or brand-spec learning | `reference-library-learner`, `brand-spec-learner` |
| Skill creation, conversion, structure cleanup | `skill-converter` |
| Project logic diagnostics | `logic-chain-diagnostic` |
| Workflow or work-log tasks | `agent-workflow-designer` if present, otherwise `work-log-manager` |

## Image Generation Special Rule

For ordinary image generation or image editing in this repository, do not use the system `imagegen` Skill by default.

Use:

`project-image-generation-router` -> `ai-image-prompt-builder` -> `ai-image-logic-checker` -> `rh-image-pro-img2img` or `rh-image-pro-txt2img`

This sequence is mandatory. Do not manually write the final generation prompt inside the execution step. The prompt must be produced or normalized by `ai-image-prompt-builder` first, then checked by `ai-image-logic-checker`, and only then passed to the RunningHub execution Skill.

Before calling any image-generation script or API, show the complete prompt handoff in the current conversation so the user can review what will be sent to the model. Do not leave the prompt visible only inside shell commands, Python code, JSON output, or local prompt files.

Use the system `imagegen` Skill only when the user explicitly asks for the built-in/system/OpenAI image generator or says not to use the project Skill chain.
