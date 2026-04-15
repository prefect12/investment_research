# Equity Investment Dossier

一个面向上市公司的 **深度投资研究 skill / 工作流工具包**。  
它把“研究一家公开交易公司”从一次性对话，变成一个 **todo 驱动、持续复盘、全量落盘、可多 agent 协作** 的本地研究闭环。

> 这套 skill 现在不靠版本号区分新旧产物。  
> 默认做法是：**每次初始化直接创建一个全新的隔离目录**，避免旧残留混入。

最终你得到的不只是几段分析文字，而是一整套可回溯的研究资产：

- `research bundle`
- `dossier.json`
- 单文件最终研究报告
- 可解释研究过程的 `research_process`

---

## 这是什么

这个仓库包含一套用于股票研究的 skill 说明、研究规则、bundle schema 和辅助脚本，目标是解决下面这个问题：

> 很多 AI 研究流程只能“当场回答”，但不能把搜索、筛选、提取、复盘、组装的全过程稳定沉淀下来。

`equity-investment-dossier` 的思路是：

1. 先建立本地 `research bundle`
2. 用 todo 驱动研究拆解
3. 每次搜索都先 start 落盘，再 complete 回填结果
4. 拿到有价值的信息后立刻落盘
5. 每轮结束都回看已有证据，再决定下一步
6. review 时持续更新 todo，并把不再阻塞但仍值得跟踪的问题转成 non-blocking open questions
7. 达到完整门槛后，再从 bundle 组装 dossier 并渲染成报告

---

## 为什么和普通“问 AI”不一样

### 1. 不是一次性回答，而是长期可累积的研究资产

- 搜索 query 会保存
- 候选结果会保存
- review 决策会保存
- 原始文件 / 提取文本 / 笔记 / claims 会保存

### 2. 不是线性写作，而是闭环研究

每轮搜索后都要求：

- 检查已经拿到的东西
- 判断缺口在哪里
- 调整下一轮搜索方向
- 持续更新 todo，直到完成

### 3. 不是只给结论，而是给“研究过程”

这套 skill 会把“为什么最终得出这个判断”体现在结构化 bundle 和最终报告里，而不是只给一个黑盒结论。

---

## 适合谁

适合：

- 想系统研究一家上市公司的个人投资者
- 想把多 agent 研究流程沉淀到本地的人
- 想输出可回看、可验证、可追加的研究报告的人

不太适合：

- 只想快速问几个事实问题
- 只想要一段简短摘要
- 不打算保存研究过程的人

---

## 你会得到什么

### 研究过程资产

- `bundle.json`：研究主状态
- `TODO.md`：主 todo 与 question todo
- `search/`：搜索 query / result / review 快照
- `raw/`：原始文件
- `extracted/`：提取或清洗后的文本
- `working/`：中间工作材料
- `promoted/`：进入高价值层的材料
- `artifacts/`：模块附加产物

### 最终报告资产

- `dossier.json`
- 单文件最终研究报告
- 独立的“研究过程”审计章节与可筛选的来源附录

---

## 核心能力

- **Todo 驱动研究**：不是边搜边乱记，而是围绕 todo 推进
- **全量过程落盘**：query、候选结果、review、source、extraction、note、artifact 都可保存
- **分阶段保存**：`foundation / module / gap_close / assembly`
- **自动断点续跑**：每次 review 后自动生成 `CHECKPOINT-LATEST.md/json` 与分层 checkpoint 快照
- **多 agent 协作**：主 agent 维护父级 todo，子 agent 负责模块推进
- **模块化组装**：先沉淀 bundle，再合并模块 patch，再组装 dossier
- **最终渲染交付**：从 bundle 生成 `dossier.json` 和单文件最终研究报告
- **默认最强模式**：active todo 不清零、来源不够、校验/渲染没完成，都不算结束

---

## 工作流概览

```mermaid
flowchart TD
    A["用户 / 主 Agent"] --> B["SKILL.md"]
    B --> C["references/*.md"]
    B --> D["agents/openai.yaml"]
    B --> E["init_research_bundle.py"]

    E --> F["research bundle"]

    A --> G["record_search_round.py"]
    G --> F

    A --> H["record_bundle_research.py"]
    H --> F

    A --> I["review_research_progress.py"]
    I --> F

    J["module patch"] --> K["merge_module_output.py"]
    K --> F

    F --> L["assemble_dossier_from_bundle.py"]
    L --> M["dossier.json"]
    M --> N["validate_dossier_json.py"]
    M --> O["render_dossier_report.py"]
    O --> P["Final report"]

    F --> Q["bundle_status.py / validate_research_bundle.py"]
```

---

## 研究 bundle 结构

```text
research-bundle/
├── bundle.json
├── TODO.md
├── search/
│   ├── queries/
│   ├── results/
│   └── reviews/
├── raw/
├── extracted/
├── working/
├── promoted/
├── artifacts/
└── dossier.json
```

这些目录内部会继续按阶段分层：

```text
foundation / module / gap_close / assembly
```

---

## 生命周期

bundle 会维护研究状态：

```text
initialized
  -> research_started
  -> foundation_ready
  -> module_ready
  -> report_ready
```

`report_ready` 默认要求：

- `P0` todo 清零
- 没有 active todo
- 尾部问题已转成 non-blocking open questions
- promoted sources 达到完整阈值且 bucket 覆盖达标
- bundle / dossier / render 三步证据齐全

## 防卡住 / 防上下文爆炸

- 不要长时间连续只搜索不复盘；建议最多连续 2-3 轮 search 就做一次 review
- 长来源原文、表格、候选结果明细直接落到 bundle 文件层，不要把大段原文塞进会话
- 每次 `review_research_progress.py` 完成后，默认自动生成：
  - `CHECKPOINT-LATEST.md`
  - `CHECKPOINT-LATEST.json`
  - `artifacts/<stage>/checkpoints/checkpoint-*.md`
  - `artifacts/<stage>/checkpoints/checkpoint-*.json`
- 如果出现 compact 失败、stream disconnected、CLI 卡住，不要重做搜索，直接从最新 checkpoint 和 bundle 继续

## 目录隔离原则

- 每次 `init_research_bundle.py` 默认创建一个新的 run 目录
- 默认路径形如：`~/.codex/data/equity-dossiers/<ticker-or-company-slug>/run-<timestamp>/research-bundle/`
- 不复用旧目录，避免旧 query / raw / dossier / 报告残留污染当前研究
- 如果你显式传 `--output-dir` 且目录非空，脚本会拒绝继续
- 如果你确实想覆盖显式目录，需手动传 `--clean-output-dir`

---

## 快速开始

### 1）初始化 bundle

```bash
python3 scripts/init_research_bundle.py \
  --company "Tesla, Inc." \
  --ticker TSLA \
  --exchange NASDAQ \
  --research-date 2026-04-13
```

初始化后，先把终端输出的 bundle 目录记成：

```bash
BUNDLE_DIR="<init 命令输出的 research-bundle 目录>"
```

查看状态：

```bash
python3 scripts/bundle_status.py \
  --input "$BUNDLE_DIR"
```

> 默认会新建隔离目录：`~/.codex/data/equity-dossiers/<ticker-or-company-slug>/run-<timestamp>/research-bundle/`  
> 也可以用环境变量 `CODEX_EQUITY_DOSSIERS_DIR` 或显式 `--base-dir` 覆盖

### 2）每次搜索都先落盘

```bash
# 搜索前先预落盘
python3 scripts/record_search_round.py \
  --bundle "$BUNDLE_DIR" \
  --mode start \
  --owner main-agent \
  --module research-foundation \
  --todo-id todo-question-foundation-filings \
  --query "Tesla 2025 annual report 10-k sec" \
  --reason "补齐一级 filing 来源"

# 搜索后立刻补齐同一轮结果
python3 scripts/record_search_round.py \
  --bundle "$BUNDLE_DIR" \
  --mode complete \
  --owner main-agent \
  --module research-foundation \
  --todo-id todo-question-foundation-filings \
  --query-id <上一步输出的 query-id> \
  --search-id <上一步输出的 search-id> \
  --result-url https://www.sec.gov/example-10k \
  --result-title "Tesla Annual Report" \
  --result-source-kind filing \
  --outcome evidence \
  --result-summary "命中官方 10-K"
```

说明：

- `--mode start` 会先把 query 以 `pending` 状态写入 `bundle.json`、`search/queries/`、`search/results/`
- `--mode complete` 会用同一个 `query_id/search_id` 回填候选结果与 summary
- 这样就算会话中断，**每次搜索**也至少已经有一条本地落盘记录，不会整段丢失

### 3）把有价值的材料立刻落盘

```bash
python3 scripts/record_bundle_research.py \
  --bundle "$BUNDLE_DIR" \
  --owner financial-quality-agent \
  --module financial-quality \
  --todo-id todo-question-foundation-filings \
  --query-id <query-id> \
  --result-id <result-id> \
  --source-id src-tsla-10k-2025 \
  --source-title "Tesla Annual Report 2025" \
  --source-kind filing \
  --source-url https://www.sec.gov/example-10k \
  --copy-file /tmp/tsla-10k.txt \
  --bucket raw \
  --filename src-tsla-10k-2025.txt
```

### 4）做 review，决定下一步方向

```bash
python3 scripts/review_research_progress.py \
  --bundle "$BUNDLE_DIR" \
  --owner main-agent \
  --todo-id todo-question-foundation-filings \
  --basis "已拿到 10-K 和 proxy" \
  --findings "基础 filing 已够，下一步补 earnings call 与 IR material" \
  --decision "关闭当前 filing todo，转向 earnings 与 IR" \
  --set-status todo-question-foundation-filings=done \
  --next-action "搜索最近 earnings release" \
  --next-action "搜索 investor day / deck"
```

### 5）组装与渲染最终报告

```bash
python3 scripts/assemble_dossier_from_bundle.py \
  --input "$BUNDLE_DIR"

python3 scripts/validate_dossier_json.py \
  --input "$BUNDLE_DIR/dossier.json"

python3 scripts/render_dossier_report.py \
  --input "$BUNDLE_DIR/dossier.json"
```

---

## 目录说明

```text
.
├── SKILL.md
├── README.md
├── .gitignore
├── agents/
├── references/
└── scripts/
```

### `SKILL.md`

给 agent 的主要执行说明，定义完整研究闭环。

### `references/`

放研究规则、输出 schema、多 agent 契约和行业特化参考。

### `scripts/`

放 bundle 初始化、记录搜索、记录研究材料、review、校验、组装与渲染脚本。

### `agents/`

放面向具体 agent 接口的默认 prompt / 配置。

---

## 关键脚本

| 脚本 | 作用 |
|---|---|
| `init_research_bundle.py` | 初始化 bundle、TODO 与目录结构 |
| `record_search_round.py` | 记录每次搜索的 start / complete 两阶段落盘 |
| `record_bundle_research.py` | 记录 source / extraction / claim / note / artifact |
| `review_research_progress.py` | 记录 review，并更新 todo 与下一步动作 |
| `merge_module_output.py` | 合并模块产出的结构化 patch |
| `bundle_status.py` | 查看当前阶段、todo、搜索与文件计数 |
| `write_bundle_checkpoint.py` | 手动生成断点 checkpoint，便于会话中断后续跑 |
| `validate_research_bundle.py` | 校验 bundle 结构与 workflow |
| `assemble_dossier_from_bundle.py` | 从 bundle 组装 dossier |
| `validate_dossier_json.py` | 校验最终 dossier JSON |
| `render_dossier_report.py` | 输出单文件最终研究报告 |

---

## 多 agent 协作方式

### 主 agent

- 初始化 bundle
- 建立与维护父级 todo
- 定期 review 研究进展
- 决定下一轮搜索方向
- 负责最后收敛与组装

### 子 agent

- 负责模块研究
- 负责来源搜集与提取
- 负责模块 patch 输出
- 可以提出候选 question todo

详细约定见：

- `references/multi-agent-contracts.md`

---

## 参考文档

建议最少先读这些：

- `references/source-map.md`
- `references/output-schema.md`
- `references/evidence-rules.md`
- `references/research-bundle-schema.md`
- `references/multi-agent-contracts.md`

如果是行业特化公司，再补读对应的 `sector-*.md`。

---

## 运行要求

- Python 3.9+
- 当前脚本以标准库为主
- 默认产物会写到 `~/.codex/data/equity-dossiers/<slug>/run-<timestamp>/research-bundle/`

---

## 当前定位

这个仓库更适合：

- 深度研究流程
- 研究自动化实验
- 多 agent 协作研究
- 把一次性研究升级成可追踪、可迭代的研究系统

它目前不是：

- 实时行情系统
- 券商级数据库
- 交易执行工具

---

## 安全提示

建议不要把下面这些内容直接提交到仓库：

- API keys
- 私有研究材料
- 带隐私信息的日志
- 受版权限制的完整原文材料

运行时目录 `.omx/`、缓存与日志文件也不建议提交，仓库已通过 `.gitignore` 做基础忽略。

---

## 免责声明

本项目用于研究流程组织、信息沉淀和报告生成，不构成任何投资建议。  
请自行核验数据来源、口径、时点与结论。
