---
name: linkfox-amazon-reviews
description: 按ASIN获取并分析亚马逊商品评论，支持15个站点(含美国站)，按星级筛选评论。当用户提到亚马逊评论、美国站评论、商品评价、买家投诉、差评、好评、星级评分、评论分析、评论情感、产品改良建议、Vine评论、已验证购买评论、竞品评论研究、Amazon reviews, US reviews, Amazon.com reviews, product feedback, negative review analysis, positive review analysis, star rating filter, review sentiment analysis, product improvement insights, Vine reviews, competitor reviews, customer feedback时触发此技能。边界：当用户要求多个 ASIN/多个竞品的综合竞品分析、横向对比、详细/简析分层、可视化看板或战略沉淀时，本 Skill 只能作为评论数据源，不能作为最终输出；必须优先交给 amazon-competitor-analysis-controller 或 amazon-multi-asin-visual-synthesizer。
---

# Amazon Product Reviews

Fetch and analyze Amazon product reviews to help sellers extract actionable insights from customer feedback.

## Core Concepts

This tool retrieves real customer reviews for a given Amazon ASIN across **15 marketplaces**. You can control how many reviews to fetch per star rating (1-5 stars, up to 100 each), sort by recency or helpfulness, and apply various filters. When the user asks to download reviews without specifying a smaller sample, fetch the maximum supported window: **500 reviews total** by requesting 100 reviews for each star bucket. Only one ASIN per request; for multiple ASINs, make separate calls.

## Routing Guardrail

This Skill is a review data source and review-analysis helper. It must not be used as the final Skill for multi-ASIN competitor synthesis.

Use `amazon-competitor-analysis-controller` or `amazon-multi-asin-visual-synthesizer` instead when the user asks for any of the following:

- Multiple ASINs or multiple competitors with "detailed analysis", "brief/simple analysis", "详细/简析", or "部分详细其他简要".
- Cross-ASIN comparison, competitive landscape,综合分析, 横向对比, 对比总结, 可视化看板, strategic summary, heatmap, Kano, or positioning chart.
- A `_compare_<timestamp>` directory or complete per-ASIN artifacts such as `visual.json`, `metadata.json`, `reviews_aggregate.json`, or `review_evidence.json`.

If local `*_reviews_US.json` files are provided together with ASINs and a competitor-analysis request, do not treat those files as the complete input. Route back to `amazon-competitor-analysis-controller` so the agent can actively fetch/generate page metadata, images, single-ASIN reports, review aggregation, and synthesis artifacts. Label a result as review-driven degraded analysis only when the user explicitly restricts the task to local review files, disables page/API fetching, or upstream acquisition fails after reasonable fallback attempts. Do not present Markdown tables or a hand-written HTML page as a completed multi-ASIN competitor dashboard.

## API Routing

US and non-US marketplaces use different backend endpoints. Route by marketplace:

- **US** → `scripts/amazon_us_reviews.py`, pass `marketplace: "US"`. See `references/api_us.md`
- **Others** → `scripts/amazon_reviews.py`, pass `domainCode: "<code>"`. See `references/api.md`

### Default Download Policy

- If the user says "download reviews", "get reviews", or otherwise requests review data without a smaller count, **always request the API maximum**.
- US marketplace maximum mode: call `scripts/amazon_us_reviews.py` with no count fields, or explicitly pass `star1Num=100`, `star2Num=100`, `star3Num=100`, `star4Num=100`, `star5Num=100`, `allStarsNum=0`, and `formatType="all_formats"`. This yields up to 500 reviews across all variants/formats, subject to availability per star bucket.
- Do **not** use `allStarsNum=100` as the default for downloads. That returns only one mixed all-star sample of up to 100 reviews.
- Do **not** use `formatType="current_format"` as the default for downloads. It can miss reviews from other colors/sizes/variants on the same listing.
- If the user explicitly asks for a smaller sample, a single star rating, positive reviews, critical reviews, media reviews, or a keyword filter, honor that narrower request instead.

## Parameter Guide

| Parameter | Type | Required | Scope | Description | Default |
|-----------|------|----------|-------|-------------|---------|
| asin | string | Yes | All | Amazon product ASIN | - |
| star1Num | integer | No | All | 1-star reviews to fetch (0-100) | Non-US: 10, US: 0 |
| star2Num | integer | No | All | 2-star reviews to fetch (0-100) | Non-US: 10, US: 0 |
| star3Num | integer | No | All | 3-star reviews to fetch (0-100) | Non-US: 10, US: 0 |
| star4Num | integer | No | All | 4-star reviews to fetch (0-100) | Non-US: 10, US: 0 |
| star5Num | integer | No | All | 5-star reviews to fetch (0-100) | Non-US: 10, US: 0 |
| sortBy | string | No | All | `recent` (newest) or `helpful` (most helpful) | `recent` |
| formatType | string | No | All | `current_format` or `all_formats`. Default download mode should use `all_formats` to maximize coverage. | US max download: `all_formats`; otherwise `current_format` |
| domainCode | string | No | Non-US | Marketplace code (see Supported Marketplaces) | `ca` |
| filterByKeyword | string | No | Non-US | Filter reviews by keyword (max 1000 chars) | - |
| reviewerType | string | No | Non-US | `all_reviews` or `avp_only_reviews` (verified only) | `all_reviews` |
| mediaType | string | No | Non-US | `all_contents` or `media_reviews_only` | `all_contents` |
| marketplace | string | No | US | Fixed value `US` | `US` |
| allStarsNum | integer | No | US | Reviews across all stars (0-100); active when star1-5Num are all 0. Use only for intentional small mixed samples, not max downloads. | 10 |
| positiveNum | integer | No | US | 4-5 star positive reviews (0-100) | 0 |
| criticalNum | integer | No | US | 1-3 star critical reviews (0-100) | 0 |

## Supported Marketplaces

| Marketplace | Code |
|-------------|------|
| United States | `US` |
| Canada | `ca` |
| United Kingdom | `co.uk` |
| Germany | `de` |
| France | `fr` |
| Italy | `it` |
| Spain | `es` |
| Japan | `co.jp` |
| India | `in` |
| Australia | `com.au` |
| Brazil | `com.br` |
| Mexico | `com.mx` |
| Netherlands | `nl` |
| Sweden | `se` |
| United Arab Emirates | `ae` |

US uses the `marketplace` parameter; all others use `domainCode`. Always confirm the user's intended marketplace.

## Usage Examples

**1. Fetch US reviews — maximum download (default for "download reviews")**
```json
{"asin": "B08N5WRWNW", "marketplace": "US", "star1Num": 100, "star2Num": 100, "star3Num": 100, "star4Num": 100, "star5Num": 100, "allStarsNum": 0, "sortBy": "recent", "formatType": "all_formats"}
```

**2. Fetch US reviews — small balanced snapshot**
```json
{"asin": "B08N5WRWNW", "marketplace": "US", "allStarsNum": 20, "sortBy": "recent"}
```

**3. Fetch negative reviews with keyword filter (Germany)**
```json
{"asin": "B08N5WRWNW", "domainCode": "de", "star1Num": 30, "star2Num": 30, "filterByKeyword": "quality", "reviewerType": "avp_only_reviews"}
```

**4. Fetch 5-star reviews with media (Japan)**
```json
{"asin": "B08N5WRWNW", "domainCode": "co.jp", "star5Num": 50, "star1Num": 0, "star2Num": 0, "star3Num": 0, "star4Num": 0, "sortBy": "helpful", "mediaType": "media_reviews_only"}
```

## Display Rules

1. **Present data clearly**: Show reviews grouped by star rating with key fields: rating, title, text, date, verified status, helpful count.
2. **Summarize when appropriate**: For many reviews, provide a theme/pain-point summary before listing individuals.
3. **Highlight actionable insights**: Call out recurring complaints in negative reviews; note praised features in positive reviews.
4. **Vine and verified labels**: Clearly indicate Vine Voice and verified purchase status.
5. **Media indicators**: Note when reviews include images or videos.
6. **Response normalization**: US reviews return `rating` as full text (e.g., "5.0 out of 5 stars") and `numberOfHelpful` as string — extract numeric values for consistent display. US reviews may also include `attributes` (color, size, etc.) — display them to show which variant was reviewed.
7. **Error handling**: When a query fails, explain the reason based on the response message and suggest adjusting parameters.
8. **Single ASIN limitation**: If the user asks about multiple ASINs, make separate requests for each.

## Important Limitations

- **One ASIN per request**: Only a single ASIN can be queried at a time.
- **Per-star cap**: Each star rating returns max 100 reviews per request. Therefore the practical maximum is up to 500 reviews when requesting 1-star through 5-star buckets at 100 each.
- **Parameter scope**: `filterByKeyword`, `reviewerType`, `mediaType` are only available for non-US marketplaces; `allStarsNum`, `positiveNum`, `criticalNum` are only available for the US marketplace.
- **No historical snapshots**: Reviews are fetched in real-time.
- **Review text language**: Reviews are returned in their original language as posted.

## User Expression & Scenario Quick Reference

**Applicable** — Tasks involving Amazon product reviews:

| User Says | Scenario |
|-----------|----------|
| "Show me the reviews for this ASIN" | Direct review lookup |
| "Get US reviews for B08N5WRWNW" | Marketplace-specific lookup |
| "What are customers complaining about" | Negative review analysis |
| "Get me all the 1-star reviews" | Star-filtered retrieval |
| "Any common issues in the bad reviews" | Pain point mining |
| "What do people like about this product" | Positive review analysis |
| "Find reviews mentioning 'battery'" | Keyword-filtered reviews (non-US) |
| "Show me reviews with photos" | Media-filtered reviews (non-US) |
| "Verified purchase reviews only" | Reviewer-type filtering (non-US) |
| "Help me analyze competitor reviews" | Competitor review research |
| "Product improvement suggestions from reviews" | Actionable insight extraction |

**Not applicable** — Needs beyond product review data:

- ABA search term data / keyword research (use ABA Data Explorer instead)
- Sales estimation or revenue analysis
- Listing copywriting or A+ content creation
- Advertising / PPC strategy
- Pricing strategy or profit margin calculations

**Boundary judgment**: If "product research" or "competitor analysis" boils down to reading customer reviews for specific ASINs, this skill applies. If it involves search volume, keyword rankings, sales estimates, or market sizing, it does not.

**Feedback:**

Auto-detect and report feedback via the Feedback API when any of the following apply:
1. The functionality or purpose described in this skill does not match actual behavior
2. The skill's results do not match the user's intent
3. The user expresses dissatisfaction or praise about this skill
4. Anything you believe could be improved

Call the feedback API as specified in the references. Do not interrupt the user's flow.

<!-- LF_LARGE_RESPONSE_BLOCK -->
## Handling Large Responses

To avoid overflowing the agent context, persist the response to disk and extract only the fields you need:

```
python scripts/response_io.py run --script scripts/amazon_reviews.py --out-dir <DIR> --params-file <params.json>
python scripts/response_io.py read <file> --fields "<paths>"   # or --path "<JMESPath>"
```

> Pick `--out-dir` outside any git working tree (e.g. `/tmp/...` on Unix, `%TEMP%/...` on Windows). Persisted responses may contain PII, pricing, or auth-sensitive data — do not commit them. Files are not auto-deleted; clean up when the task is done.

> This skill exposes multiple entry scripts: `amazon_reviews.py`, `amazon_us_reviews.py`. Pass `--script scripts/<name>.py` to choose the one you need.

`run` writes the full response to a file and emits only a schema preview + file path. `read` projects specific fields, with `--limit/--offset` for slicing and `--format json|jsonl|csv|table` for output.

**Windows / PowerShell rule**: prefer `--params-file` instead of inline JSON. Create the params file with `ConvertTo-Json -Compress | Set-Content -Encoding UTF8`, then pass it with `--params-file`. Do not pipe Python code with Chinese literal paths through `PowerShell here-string | python -`; this can turn paths into `????` under the active console encoding. Use `Join-Path` and `-LiteralPath` for Chinese directories.

**Failure-file rule**: if the wrapped API fails, `response_io.py` writes captured stdout as `*.failed.json`. Only files ending exactly in `__<label>.json` with `exit_code=0` in the preview and `size_bytes>0` are valid data sources. Never select files with a broad pattern like `*reviews_linkfox_raw*.json`, because it may include failed or stale files.

**When to prefer this pattern** — apply your judgment based on the response characteristics, e.g.:
- High field count per record, or fields you don't need
- Batch/paginated results (multiple items per call)
- Long-text fields (descriptions, reviews, HTML, time series)
- Output reused across later steps rather than consumed immediately

For small, single-use responses, calling the main script directly is fine.

⚠️ The preview is a truncated schema + sample, not the full data. Any field-level decision must read from the persisted file via `read`.
<!-- /LF_LARGE_RESPONSE_BLOCK -->

---
*For more high-quality, professional cross-border e-commerce skills, visit [LinkFox Skills](https://skill.linkfox.com/).*
