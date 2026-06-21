# 向量检索系统 · 速查

**模型**:Qwen3-Embedding-8B(SiliconFlow,4096 维,instruction-aware)
**索引位置**:`vector_index/vectors.npz` + `vector_index/metadata.parquet`
**当前规模**:173 条切片(2026-06-20 重建,精简发行版实际内容)
**重建耗时**:约 46 秒 / ¥0.04

---

## 目录结构

```
工具/向量检索/
├── chunking.py         # 统一切片模块(file-type router)
├── scan_archives.py    # 扫描/切片/成本估算(Phase 0)
├── embedder.py         # SiliconFlow Embedding 客户端
├── reranker.py         # SiliconFlow Rerank 客户端(精排层)
├── build_index.py      # 全量构建(Phase 1)
├── update_index.py     # 增量更新(推荐日常使用)
├── query_rewriter.py   # Query 改写器(口语化 → 结构化)
├── search.py           # 语义检索接口(Phase 2,集成改写+精排)
├── vector_index/       # 索引产物
│   ├── vectors.npz
│   ├── metadata.parquet
│   ├── index_info.json
│   ├── scan_report.md
│   └── scan_report.json
└── README.md           # 本文件
```

---

## 常用命令

### 检索(日常使用)

```powershell
# AI 消费模式(JSON 输出)
python 工具/向量检索/search.py "查询" --top 5 --json

# 带完整正文(准备喂给 Prompt)
python 工具/向量检索/search.py "查询" --top 3 --json --full

# 按域过滤
python 工具/向量检索/search.py "查询" --domain 品牌规范 --json
python 工具/向量检索/search.py "查询" --domain E_平面与海报 --json
python 工具/向量检索/search.py "查询" --domain 00_通识原则 --json

# 按切片类型过滤
python 工具/向量检索/search.py "查询" --type P_CASE --json       # P 域成功案例
python 工具/向量检索/search.py "查询" --type PRINCIPLE --json    # 通识原则
python 工具/向量检索/search.py "查询" --type BRAND --json        # 品牌规范条款
python 工具/向量检索/search.py "查询" --type RECORD --json       # 参考库学习记录

# 人类阅读模式(可看正文)
python 工具/向量检索/search.py "查询" --top 3 --text

# 【推荐】用户口语化查询 → 自动扩展术语再检索
python 工具/向量检索/search.py "帮我做个好看的促销图 NEBILITY 塑身衣 美国市场" --rewrite --top 5 --json
```

### Query 改写(口语化 → 结构化)

自然语言需求中常缺关键检索术语,`--rewrite` 会按词表自动扩展:

```powershell
# 独立用(只看扩展结果,不做检索)
python 工具/向量检索/query_rewriter.py "帮我做个促销图 NEBILITY 塑身衣 美国市场"
# 输出 → 扩展为: ... promotional banner poster CTA 折扣 版式 shapewear bodysuit ...

# 集成用(扩展 + 检索一步到位)
python 工具/向量检索/search.py "口语化查询" --rewrite --json
```

**实测效果**:同一个口语化 query,加 `--rewrite` 后 Top5 主题准确率从 3/5 提升到 5/5,核心案例排名从第 5 位提升到第 2 位。

改写器覆盖 6 维度:task_type / brand / product / region / platform / style。品牌名自动从 `品牌规范/` 下的目录读取。

### Rerank 精排(cross-encoder)

向量检索是"双塔近似",rerank 是"交叉编码器",精度显著更高。粗排召回 top-20 → rerank 精排到 top-5:

```powershell
# 【推荐】最强组合:改写 + 精排 + 完整正文
python 工具/向量检索/search.py "查询" --rewrite --rerank --top 5 --json --full

# 调大粗排池(默认 20,复杂任务可提到 40)
python 工具/向量检索/search.py "查询" --rerank --rerank-pool 40

# 独立测试 reranker
python 工具/向量检索/reranker.py
```

**实测**:"帮我做个好看的促销图 NEBILITY 塑身衣 美国市场" 一个 query,加 rerank 后 P 域 NEBILITY 塑身衣促销成功案例从 Top5 仅 1 条 → Top5 命中 4 条。

**成本**:默认用 `Pro/BAAI/bge-reranker-v2-m3`,单次调用约 ¥0.001~0.003(取决于粗排池大小与文档长度)。主控中心每次生成交接卡 B 约 1 次检索 → 月成本低于 ¥1。

**API 失败自动降级**:rerank 调用异常时会回退为向量粗排的 top_k 结果,stderr 输出告警,不阻塞流程。

## 当前索引覆盖


| 域               | 文件      | 切片       | 类型                         |
| --------------- | ------- | -------- | -------------------------- |
| 参考库(通识原则为主)   | 13      | 113      | PRINCIPLE / RECORD / INDEX |
| 品牌规范            | 10      | 18       | BRAND                      |
| 场景知识库 K1-K4    | 14      | 42       | SCENE_KB                   |
| **合计**          | **37**  | **173**  |                            |


**注 1**:本工作区为**精简发行版**,参考库仅含通识原则 + 顶层说明;E/F/G/H/J/N 等域记录、P 域成功案例在本工作区不存在(故无 RECORD/P_CASE 主力切片)。学习新素材后用 `update_index.py` 增量扩充。
**注 2**:能力模块 M1-M18 已于 V8.0 转为 `.cursor/skills/` 下的 Skill,由 Cursor 原生按需加载,不再纳入向量索引(`scan_capability_modules` 已弃用为空壳)。`--type MODULE` 过滤现返回空。
**注 3**:场景知识库仍可用 `--type SCENE_KB` 精确过滤。

### 增量更新(M10/M17 学习后 / P 域入库后 · 推荐)

```powershell
# 常规增量:只嵌新增或修改的切片,复用其余
python 工具/向量检索/update_index.py

# 试运行(看看有多少变更,不调 API)
python 工具/向量检索/update_index.py --dry-run

# 强制全量重建(等价 build_index.py --force)
python 工具/向量检索/update_index.py --full
```

**复用策略**:按 `(source_path, text_hash)` 作为匹配键 —— 即使记录 index 偏移导致 chunk_id 改变,只要正文不变就复用旧向量,**无调用成本**。

### 全量重建(首次构建 / 切片算法变更时)

```powershell
# 先扫描看规模和成本
python 工具/向量检索/scan_archives.py

# 全量重建(会提示确认)
python 工具/向量检索/build_index.py --force

# 测试小批量(10 条)
python 工具/向量检索/build_index.py --limit 10
```

---

## 切片类型(type 字段)


| 类型          | 含义                          | 典型来源                   |
| ----------- | --------------------------- | ---------------------- |
| `RECORD`    | 单条参考记录(按 `--- 记录 #N ---` 切) | 参考库 E/F/G/N 子文件        |
| `PRINCIPLE` | 单条通识原则(按 `## PX-NNN` 切)     | `00_通识原则/P1~P7.txt`    |
| `BRAND`     | 品牌规范章节                      | `品牌规范/[品牌]/视觉系统/*.txt` |
| `P_CATALOG` | P 域分类索引                     | `P_生图成功案例库/P1~P5.txt`  |
| `P_CASE`    | P 域单个成功案例(prompt+meta)      | `P_生图成功案例库/P-XXX-*/`   |
| `INDEX`     | 全局索引文件(已默认排除)               | `*_域索引.txt`            |
| `STUB`      | 已细分的空壳文件(已跳过)               | 细分后的母文件                |
| `DEFAULT`   | 其他切片                        | 场景知识库等                 |


---

## 分数参考线

### 向量分(vector_score · 余弦相似度)


| 分数          | 含义    | 处置    |
| ----------- | ----- | ----- |
| ≥ 0.70      | 强相关   | 直接采纳  |
| 0.55 – 0.70 | 相关    | 候选池   |
| 0.40 – 0.55 | 弱相关   | 仅参考概念 |
| < 0.40      | 几乎不相关 | 忽略    |


### Rerank 分(rerank_score,范围 0-1,分辨率更高)


| 分数          | 含义         |
| ----------- | ---------- |
| ≥ 0.95      | 极高相关(近乎完美) |
| 0.80 – 0.95 | 强相关(直接可用)  |
| 0.50 – 0.80 | 相关(作候选)    |
| 0.20 – 0.50 | 弱相关(概念参考)  |
| < 0.20      | 几乎不相关      |


---

## 配置(`config/.env`)

```
SILICONFLOW_API_KEY=sk-...
SILICONFLOW_BASE_URL=https://api.siliconflow.cn/v1

# Embedding
EMBEDDING_MODEL=Qwen/Qwen3-Embedding-8B
EMBEDDING_DIM=4096
EMBEDDING_BATCH_SIZE=10
EMBEDDING_TIMEOUT=60
EMBEDDING_MAX_RPM=1600

# Rerank(可选)
RERANK_MODEL=Pro/BAAI/bge-reranker-v2-m3
RERANK_TIMEOUT=60
RERANK_MAX_RPM=1200
```

---

## 集成点(主控中心)

- **④ 阶段门**:生成【参考精炼摘要 B】前调一次向量检索,召回 top-K 候选
- **③.5 P 域门**:P 域案例复用检查走 `--type P_CASE`
- **品牌加载后**:按需抽取品牌条款走 `--domain 品牌规范 --type BRAND`

详细规则见 `.cursor/rules/vector-search-integration.mdc`。

---

## 已知限制 / 待办

- **搜索延迟**:每次查询需重新 embed(~2-3 秒,可接受)
- **索引大小**:173 条 × 4096 维 × 4 字节 ≈ 2.7 MB(vectors.npz 压缩后约 1.67 MB),可全量加载到内存
- **改写器词表**:目前为硬编码(见 `query_rewriter.py`),可按项目演进扩充或后续迁移到 YAML 外部配置

