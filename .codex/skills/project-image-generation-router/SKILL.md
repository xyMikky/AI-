---
name: project-image-generation-router
description: 当前项目的默认生图路由 Skill。凡用户在本项目中要求生成图片、编辑图片、图生图、文生图、改图、换背景、换装、改内饰、产品图重绘、海报/Banner/电商主图、风格转换、测试生图能力，必须优先使用本项目 Skill 链路，而不是系统 imagegen。图生图或有参考图时路由到 ai-image-prompt-builder → ai-image-logic-checker → rh-image-pro-img2img；纯文本生图时路由到 ai-image-prompt-builder → ai-image-logic-checker → rh-image-pro-txt2img；生成后按需调用 ai-image-logic-checker Post-Gen 和 ai-image-aesthetic-scorer。仅当用户明确要求“系统 imagegen / 内置 imagegen / OpenAI image generation / 不使用项目 Skill”时才绕过本路由。
---

# Project Image Generation Router

## Default Rule

In this project, image generation defaults to the project-local RunningHub Skill chain.

Do not use the system `imagegen` Skill for ordinary image generation or image editing requests in this repository. Use the system image generator only when the user explicitly asks for it.

## Routing

Use this routing table:

| User Request | Route |
|---|---|
| Edit an existing image, image-to-image, reference-image generation, change interior, replace background, change clothing, style transfer | `ai-image-prompt-builder` -> `ai-image-logic-checker` -> `rh-image-pro-img2img` |
| Generate from text only, poster concept, product scene without an input image | `ai-image-prompt-builder` -> `ai-image-logic-checker` -> `rh-image-pro-txt2img` |
| Video prompt or first-frame planning | `video-prompt-designer`, then call `ai-image-prompt-builder` only for static frame generation |
| Detail page module images | `detail-page-designer`, then call `ai-image-prompt-builder` for each image module |
| Prompt-only methodology request | `image-prompt-designer` only when the user asks for a portable/general prompt-writing method |

## Required Flow

1. Identify whether the task is image-to-image or text-to-image.
2. Build a production prompt with `ai-image-prompt-builder`.
3. Run the pre-generation gate in `ai-image-logic-checker`.
4. Execute:
   - `rh-image-pro-img2img` for image-to-image.
   - `rh-image-pro-txt2img` for text-to-image.
5. Save outputs in `生成结果输出/`.
6. Run post-generation checks when an output image is available.

## Mandatory Handoff Contract

The image execution Skills must receive a handoff from `ai-image-prompt-builder`. Do not skip this step, even when the user request is short.

Before any execution Skill calls a script or API, the full handoff must be shown in the current conversation output. The user should be able to see the actual `final_prompt` without opening shell commands, code, JSON logs, or local files.

The handoff should include:

```text
[Project Image Prompt Handoff]
source_skill: ai-image-prompt-builder
task_type: img2img | txt2img
input_images: image 1 = <path or role>
final_prompt: <prompt to pass to RunningHub>
aspect_ratio: <ratio>
resolution: <1k|2k|4k>
model: pro | flash | gpt-image-2 | gpt-image-2-official
pre_gen_notes: <logic/color/reference constraints for ai-image-logic-checker>
```

If this handoff is missing, route back to `ai-image-prompt-builder` instead of calling `rh-image-pro-img2img` or `rh-image-pro-txt2img` directly.

## Boundary

This Skill is only a router. It does not write the final prompt itself and does not call image APIs directly.
