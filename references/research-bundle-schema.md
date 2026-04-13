# Research Bundle Schema

`research bundle` 是这个 skill 的本地中间层。它现在不是单纯的“模块 patch 暂存箱”，而是一个完整的**研究闭环状态机**：

1. 建 todo
2. 记 query
3. 存候选结果
4. 落来源/提取/笔记/文件
5. 做 review
6. 更新 todo
7. 再决定下一轮搜索方向
8. 最后组装 dossier

## 目录结构

默认路径：

```text
/tmp/equity-dossiers/<ticker-or-company-slug>/research-bundle/
```

默认目录：

```text
bundle.json
TODO.md
search/
  queries/
    foundation/
    module/
    gap_close/
    assembly/
  results/
    foundation/
    module/
    gap_close/
    assembly/
  reviews/
    foundation/
    module/
    gap_close/
    assembly/
raw/
  foundation/
  module/
  gap_close/
  assembly/
extracted/
  foundation/
  module/
  gap_close/
  assembly/
working/
  foundation/
  module/
  gap_close/
  assembly/
promoted/
  foundation/
  module/
  gap_close/
  assembly/
artifacts/
  foundation/
  module/
  gap_close/
  assembly/
```

含义：

- `search/queries/`：每轮 query 的快照
- `search/results/`：每轮候选结果列表快照
- `search/reviews/`：每轮 review 决策快照
- `raw/`：原始网页、PDF、下载文件
- `extracted/`：清洗文本、OCR 结果、结构化提取中间稿
- `working/`：草稿、临时分析、人工整理中间件
- `promoted/`：已确定会进入 dossier 的关键材料
- `artifacts/`：其他不适合归到以上分层的补充文件

## 顶层 schema

```json
{
  "bundle_version": 3,
  "created_at": "2026-04-13T12:00:00",
  "updated_at": "2026-04-13T12:00:00",
  "dossier_seed": {},
  "module_outputs": [],
  "research_assets": {
    "query_records": [],
    "result_records": [],
    "source_records": [],
    "extraction_records": [],
    "claim_records": [],
    "note_records": [],
    "review_records": [],
    "artifact_records": []
  },
  "workflow": {
    "todo_items": [],
    "search_journal": [],
    "review_cycles": [],
    "current_stage": "initialized",
    "completion_gates": {},
    "next_actions": [],
    "summary": {}
  }
}
```

## `workflow.todo_items`

todo 分两层：

- `level=parent`
  - 主 agent 维护的父级模块 todo
- `level=question`
  - 更细的搜索/验证问题；可由主 agent 创建，也可由子 agent 提候选 todo 后由主 agent 决定是否写入

每个 todo 至少包含：

- `id`
- `parent_id`
- `module`
- `title`
- `kind`
- `level`
- `stage`
- `priority`
- `status`
- `done_criteria`
- `depends_on`
- `derived_from`
- `related_query_ids`
- `related_result_ids`
- `related_source_ids`
- `related_claim_ids`
- `related_artifact_ids`
- `linked_search_ids`
- `linked_review_ids`
- `notes`

## `workflow.search_journal`

这是搜索循环摘要，不是完整原始结果仓库。完整原始结果留在 `search/queries/` 与 `search/results/`。

每条 journal 至少包含：

- `id`
- `timestamp`
- `module`
- `todo_id`
- `query`
- `reason`
- `based_on`
- `outcome`
- `captured_urls`
- `saved_paths`
- `promoted_source_ids`
- `new_todo_ids`
- `next_actions`
- `summary`
- `query_id`
- `result_ids`
- `review_id`

## `workflow.review_cycles`

这是“回看已有东西并决定下一步”的核心记录。

每条 review 至少包含：

- `id`
- `timestamp`
- `reviewed_query_ids`
- `reviewed_result_ids`
- `reviewed_todo_ids`
- `basis`
- `findings`
- `decision`
- `spawned_todo_ids`
- `next_actions`
- `stage_before`
- `stage_after`
- `owner`
- `saved_path`

## `research_assets`

### `query_records`

搜索 query 的结构化记录。原始快照另存到 `search/queries/<stage>/<query_id>.json`。

### `result_records`

候选结果池。**默认保留全部候选结果**，不要只保留最后采用的几条。

### `source_records`

真正拿来做研究的来源记录。可以经历：

- `candidate`
- `captured`
- `downloaded`
- `extracted`
- `promoted`

### `extraction_records`

从原始来源得到的文本或结构化提取记录，通常会指向 `extracted/<stage>/...`。

### `claim_records`

事实、数字、管理层表态、观点、待核验断言。

### `note_records`

人工笔记、临时分析、草稿结论。不要怕“暂时用不上”就不存。

### `review_records`

与 `workflow.review_cycles` 对应的 research asset 镜像，用于统一计数与保留。

### `artifact_records`

本地文件引用。适合挂网页快照、PDF、截图、OCR 文件、CSV、清洗文本等。

## 模块输出

`module_outputs[]` 继续保存模块 patch：

```json
{
  "section": "business-quality",
  "owner": "business-quality-agent",
  "summary": "一句话说明模块最重要结论",
  "data": {},
  "source_additions": [],
  "gaps": [],
  "conflicts": [],
  "raw_notes": [],
  "extracted_claims": [],
  "artifacts": []
}
```

它和 `research_assets` 的关系是：

- `research_assets` 保留过程材料
- `module_outputs` 保留模块化结论 patch
- `assemble_dossier_from_bundle.py` 再统一把两者转成最终 dossier

## 分阶段门槛

bundle 自动维护完成阶段：

- `initialized`
- `research_started`
- `foundation_ready`
- `module_ready`
- `report_ready`

判定逻辑示意：

- `research_started`
  - 至少有 query + result + review
- `foundation_ready`
  - 基础来源池父级 todo 已关闭，且 useful 搜索达到最小门槛
- `module_ready`
  - 核心模块父级 todo 已关闭，P0 问题已基本清空
- `report_ready`
  - assembly 父级 todo 已关闭，promoted source 与来源 bucket 达到完整报告门槛

## 强制落盘规则

- 开始搜索前必须先 `init_research_bundle.py`
- 每轮搜索必须先 `record_search_round.py`
- 有价值的来源/提取/文件必须立刻 `record_bundle_research.py`
- 每轮搜索后都应尽快 `review_research_progress.py`
- 周期性运行 `bundle_status.py` 与 `validate_research_bundle.py`
- 如果只有 bundle 和 TODO，没有 query/result/review/source/extraction/claim/note/artifact，就仍然只是初始化骨架

## 推荐闭环命令顺序

```bash
python3 scripts/init_research_bundle.py ...
python3 scripts/bundle_status.py --input <bundle-dir>
python3 scripts/record_search_round.py --bundle <bundle-dir> ...
python3 scripts/record_bundle_research.py --bundle <bundle-dir> ...
python3 scripts/review_research_progress.py --bundle <bundle-dir> ...
python3 scripts/bundle_status.py --input <bundle-dir> --fail-if-empty
python3 scripts/merge_module_output.py --bundle <bundle-dir> --module <module-json>
python3 scripts/validate_research_bundle.py --input <bundle-dir>
python3 scripts/assemble_dossier_from_bundle.py --input <bundle-dir>
```
