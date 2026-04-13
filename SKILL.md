---
name: equity-investment-dossier
description: 面向上市公司的 all-in-one 一次性投资研究报告生成技能。用在需要从 0 到 1 研究一家公开交易公司、先把多 agent 研究结果沉淀到本地 research bundle、再组装成 dossier 并生成一套多页 HTML 完整研究报告、并让读者快速理解这份报告做了什么、收集了哪些信息、如何形成当前判断时使用。覆盖公司历史分期、管理层更替、公开采访与前瞻判断、业务/客户/竞争/财务/资本配置/危机/估值/市场预期差分析，默认生成一套多页网页研究报告。
---

# Equity Investment Dossier

## 概览

用这个 skill 把“研究一家上市公司”变成一个**todo 驱动、持续复盘、全量落盘**的闭环：

1. 先初始化本地 `research bundle`
2. 主 agent 建立父级 todo，并持续维护 `TODO.md`
3. 每轮搜索先记录 query 与候选结果
4. 拿到有价值的信息后，立刻把来源、提取、笔记、文件落盘
5. 主 agent 定期 review 已有东西，决定下一轮搜索方向
6. 直到分阶段门槛完成，再组装 dossier 并渲染 HTML

默认产出不是普通 memo，而是：

- 本地 `research bundle`
- `dossier.json`
- 多页 HTML 研究报告
- 一份能解释“这份研究怎么做出来的”的 `research_process`

## 执行原则

- **必须先 init bundle，再开始正式搜索。**
- **所有搜索过程数据都要落盘。** query、候选结果、review、原始文件、提取文本、claims、笔记都不能只停留在终端。
- **所有过程文件都按研究阶段分层保存。** 默认阶段：`foundation` / `module` / `gap_close` / `assembly`。
- **主 agent 维护父级 todo；子 agent 只负责完成模块任务，或提出候选 question todo。**
- **每轮搜索后必须回看已经有的东西，再决定下一轮。** 不要机械堆 query。
- **默认保留全部候选结果。** 候选结果先存，再在 review 中判断是否继续打开、提取、promote。
- **不要直接把零散材料揉成最终报告。** 先沉淀 bundle，再组装 dossier。
- **完整报告默认需要足够广的来源覆盖。** 十几条来源只能算草稿，不算完整交付。

## 默认闭环流程

### 0. 先读基础 reference

至少先读：

- `references/source-map.md`
- `references/output-schema.md`
- `references/evidence-rules.md`
- `references/research-bundle-schema.md`
- `references/multi-agent-contracts.md`

按行业再额外读取唯一一份 sector reference：

- 软件与互联网：`references/sector-software-internet.md`
- 半导体与硬件：`references/sector-semiconductor-hardware.md`
- 消费、工业与周期：`references/sector-consumer-industrial-cyclical.md`
- 金融与保险：`references/sector-financial-insurance.md`
- REIT：`references/sector-reit.md`
- 生物医药：`references/sector-biopharma.md`
- 其余一般经营型公司：`references/sector-general-operating.md`

### 1. 初始化 bundle

```bash
python3 scripts/init_research_bundle.py --company "Tesla, Inc." --ticker TSLA --exchange NASDAQ --research-date 2026-04-13
python3 scripts/bundle_status.py --input /tmp/equity-dossiers/tsla/research-bundle
```

初始化后应该看到：

- `bundle.json`
- `TODO.md`
- `search/queries/<stage>/`
- `search/results/<stage>/`
- `search/reviews/<stage>/`
- `raw/<stage>/`
- `extracted/<stage>/`
- `working/<stage>/`
- `promoted/<stage>/`
- `artifacts/<stage>/`

### 2. 先看 todo，再开始第一轮搜索

主 agent 要先看 `TODO.md` 或运行：

```bash
python3 scripts/bundle_status.py --input /tmp/equity-dossiers/tsla/research-bundle --fail-if-empty
```

优先从 P0 question todo 开始。默认是 foundation 阶段的基础来源池问题。

### 3. 记录一次搜索轮次

每轮搜索先用 `record_search_round.py` 记录 query 与候选结果：

```bash
python3 scripts/record_search_round.py \
  --bundle /tmp/equity-dossiers/tsla/research-bundle \
  --owner main-agent \
  --module research-foundation \
  --todo-id todo-question-foundation-filings \
  --query "Tesla 2025 annual report 10-k sec" \
  --reason "补齐一级 filing 来源" \
  --result-url https://www.sec.gov/example-10k \
  --result-title "Tesla Annual Report" \
  --result-source-kind filing
```

这一步会：

- 写入 `research_assets.query_records`
- 写入 `research_assets.result_records`
- 写入 `workflow.search_journal`
- 把 query / result 快照分别落到 `search/queries/<stage>/` 和 `search/results/<stage>/`

### 4. 有用材料立刻落盘

拿到原始文件、提取文本、claims、笔记或来源后，立刻用 `record_bundle_research.py`：

```bash
python3 scripts/record_bundle_research.py \
  --bundle /tmp/equity-dossiers/tsla/research-bundle \
  --owner financial-quality-agent \
  --module financial-quality \
  --todo-id todo-question-foundation-filings \
  --query-id <query-id> \
  --result-id <result-id> \
  --source-id src-tsla-10k-2025 \
  --source-title "Tesla Annual Report 2025" \
  --source-kind filing \
  --source-url https://www.sec.gov/example-10k \
  --copy-file /tmp/tsla-10k.html \
  --bucket raw \
  --filename src-tsla-10k-2025.html
```

如果已经提取了文本或清洗结果，也继续写入：

```bash
python3 scripts/record_bundle_research.py \
  --bundle /tmp/equity-dossiers/tsla/research-bundle \
  --owner financial-quality-agent \
  --module financial-quality \
  --todo-id todo-question-foundation-filings \
  --source-id src-tsla-10k-2025 \
  --extraction-id extract-tsla-10k-2025 \
  --extraction-source-id src-tsla-10k-2025 \
  --copy-file /tmp/tsla-10k.txt \
  --bucket extracted \
  --filename extract-tsla-10k-2025.txt \
  --note "10-K 文本已清洗，可继续抽取 revenue / margin / capex claims"
```

### 5. 每轮搜索后必须复盘

搜索不是线性的。主 agent 要持续回看已经有的 query / result / source / note，然后用 `review_research_progress.py` 决定下一步：

```bash
python3 scripts/review_research_progress.py \
  --bundle /tmp/equity-dossiers/tsla/research-bundle \
  --owner main-agent \
  --todo-id todo-question-foundation-filings \
  --basis "已拿到 10-K 和最近 proxy" \
  --findings "一级来源基础够了，下一步应补 conference call 与 IR material" \
  --decision "关闭 filing question todo，转向 earnings 与 IR" \
  --set-status todo-question-foundation-filings=done \
  --next-action "搜索最近 earnings release" \
  --next-action "搜索 investor day / deck"
```

如果需要派生新 question todo，也在这里创建。子 agent 可以提候选 todo，主 agent 统一写入 bundle。

### 6. 模块输出继续合并

模块 agent 产出结构化 patch 后，再合并：

```bash
python3 scripts/merge_module_output.py --bundle /tmp/equity-dossiers/tsla/research-bundle --module /path/to/module-output.json
```

### 7. 周期性检查状态

```bash
python3 scripts/bundle_status.py --input /tmp/equity-dossiers/tsla/research-bundle --fail-if-empty
python3 scripts/validate_research_bundle.py --input /tmp/equity-dossiers/tsla/research-bundle
```

### 8. 组装与渲染

```bash
python3 scripts/assemble_dossier_from_bundle.py --input /tmp/equity-dossiers/tsla/research-bundle
python3 scripts/validate_dossier_json.py --input /tmp/equity-dossiers/tsla/research-bundle/dossier.json
python3 scripts/render_dossier_html.py --input /tmp/equity-dossiers/tsla/research-bundle/dossier.json
```

## 分阶段完成标准

bundle 会自动维护这些阶段：

- `initialized`
- `research_started`
- `foundation_ready`
- `module_ready`
- `report_ready`

实际搜索与文件保存阶段使用：

- `foundation`
- `module`
- `gap_close`
- `assembly`

不要自己随意发明新阶段名。

## 模块编排

固定模块不变：

- `company-history`
- `management-profile`
- `management-interviews`
- `prediction-review`
- `business-quality`
- `industry-competition`
- `financial-quality`
- `market-valuation`
- `macro-regime`
- `investor-master-views`
- `sector-specialist`

详细 ownership 与返回契约见：`references/multi-agent-contracts.md`

## 脚本

- `scripts/init_research_bundle.py`
  - 初始化 bundle、TODO 和按阶段分层目录。
- `scripts/record_search_round.py`
  - 记录一轮 query 和候选结果，并把快照落到 `search/`。
- `scripts/record_bundle_research.py`
  - 记录来源、提取、claims、笔记、artifact，并把文件复制到分层目录。
- `scripts/review_research_progress.py`
  - 记录 review cycle，更新 todo，必要时派生新 todo。
- `scripts/merge_module_output.py`
  - 合并模块 patch。
- `scripts/bundle_status.py`
  - 查看阶段、todo、query/result/review 计数与分层文件数。
- `scripts/validate_research_bundle.py`
  - 校验 bundle 结构与 workflow。
- `scripts/assemble_dossier_from_bundle.py`
  - 从 bundle 组装 dossier。
- `scripts/render_dossier_html.py`
  - 渲染多页 HTML 报告。

## References

- `references/research-bundle-schema.md`
  - 读 bundle 的目录、字段、阶段和落盘规则时使用。
- `references/multi-agent-contracts.md`
  - 读主 agent / 子 agent 的 todo 分工、模块 ownership 和返回契约时使用。
- `references/output-schema.md`
  - 读 dossier JSON 结构时使用。
- `references/source-map.md`
  - 读来源 bucket 与优先级时使用。
- `references/evidence-rules.md`
  - 读证据等级与冲突处理规则时使用。
- `references/timeline-rules.md`
  - 读 timeline / era 规则时使用。
- `references/interview-extraction.md`
  - 读管理层访谈与预判抽取方法时使用。
- `references/valuation-rules.md`
  - 读估值与市场行为分析框架时使用。

## 默认路径

如果用户没有指定输出路径，默认写到：

```text
/tmp/equity-dossiers/<ticker-or-company-slug>/
```

不要把默认生成物写回 skill 仓库，除非用户明确要求。
