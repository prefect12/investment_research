# Equity Investment Dossier

一个面向上市公司的 **all-in-one 投资研究 skill / 工具包**。  
它把“研究一家公司”拆成一个 **todo 驱动、持续复盘、全量落盘、可多 agent 协作** 的闭环，并最终生成：

- 本地 `research bundle`
- `dossier.json`
- 多页 HTML 研究报告
- 一份可回溯“研究是怎么做出来的”的 `research_process`

> 适合：从 0 到 1 深入研究一家上市公司，并把研究过程与结论沉淀成本地结构化资产。  
> 不适合：只想临时问几个问题、只做一次性浅层摘要。

---

## 核心特性

- **Todo 驱动**：先建研究待办，再推进搜索与模块合成
- **全量过程落盘**：query、候选结果、review、原始文件、提取文本、claims、笔记都会保存
- **按阶段分层保存**：`foundation / module / gap_close / assembly`
- **多 agent 协作**：主 agent 管父级 todo，子 agent 负责模块研究与候选 question todo
- **研究闭环**：每轮搜索后都要 review 已有信息，再决定下一步搜索方向
- **可组装最终报告**：从 `research bundle` 组装 `dossier.json`，再渲染为多页 HTML

---

## 整体架构

```mermaid
flowchart LR
  A[用户 / 主 Agent] --> B[SKILL.md<br/>流程入口]
  B --> C[references/*.md<br/>规则 / 行业 / 输出契约]
  B --> D[agents/openai.yaml<br/>默认提示]

  B --> E[init_research_bundle.py]
  E --> F[research bundle]

  F --> F1[bundle.json]
  F --> F2[TODO.md]
  F --> F3[search/queries|results|reviews/<stage>]
  F --> F4[raw|extracted|working|promoted|artifacts/<stage>]

  A --> G[record_search_round.py]
  G --> F

  A --> H[record_bundle_research.py]
  H --> F

  A --> I[review_research_progress.py]
  I --> F
  I --> G

  J[模块 Agent 输出 JSON patch] --> K[merge_module_output.py]
  K --> F

  F --> L[assemble_dossier_from_bundle.py]
  L --> M[dossier.json]
  M --> N[validate_dossier_json.py]
  M --> O[render_dossier_html.py]
  O --> P[多页 HTML 报告]

  F --> Q[bundle_status.py / validate_research_bundle.py]
```

---

## 研究数据目录结构

初始化后会生成一个本地 `research bundle`：

```text
research-bundle/
├── bundle.json
├── TODO.md
├── search/
│   ├── queries/{foundation,module,gap_close,assembly}/
│   ├── results/{foundation,module,gap_close,assembly}/
│   └── reviews/{foundation,module,gap_close,assembly}/
├── raw/{foundation,module,gap_close,assembly}/
├── extracted/{foundation,module,gap_close,assembly}/
├── working/{foundation,module,gap_close,assembly}/
├── promoted/{foundation,module,gap_close,assembly}/
├── artifacts/{foundation,module,gap_close,assembly}/
└── dossier.json
```

---

## 生命周期

`bundle.json` 会维护研究阶段：

```text
initialized
  -> research_started
  -> foundation_ready
  -> module_ready
  -> report_ready
```

实际文件保存阶段使用：

```text
foundation / module / gap_close / assembly
```

---

## 仓库结构

```text
.
├── SKILL.md
├── README.md
├── .gitignore
├── agents/
│   └── openai.yaml
├── references/
│   ├── source-map.md
│   ├── output-schema.md
│   ├── evidence-rules.md
│   ├── research-bundle-schema.md
│   ├── multi-agent-contracts.md
│   └── sector-*.md
└── scripts/
    ├── init_research_bundle.py
    ├── record_search_round.py
    ├── record_bundle_research.py
    ├── review_research_progress.py
    ├── merge_module_output.py
    ├── bundle_status.py
    ├── validate_research_bundle.py
    ├── assemble_dossier_from_bundle.py
    ├── validate_dossier_json.py
    └── render_dossier_html.py
```

---

## 环境要求

- Python **3.9+**
- 当前脚本使用标准库即可运行，无额外第三方依赖

---

## 快速开始

### 1）初始化研究 bundle

```bash
python3 scripts/init_research_bundle.py \
  --company "Tesla, Inc." \
  --ticker TSLA \
  --exchange NASDAQ \
  --research-date 2026-04-13
```

查看当前状态：

```bash
python3 scripts/bundle_status.py --input /tmp/equity-dossiers/tsla/research-bundle
```

> 默认输出目录是 `/tmp/equity-dossiers/<ticker-or-company-slug>/`  
> 如果不想写到 `/tmp`，可以显式传 `--base-dir` 或 `--output-dir`

---

### 2）记录一轮搜索

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

---

### 3）拿到有价值材料后立刻落盘

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

---

### 4）每轮搜索后做 review，决定下一步

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

---

### 5）组装与渲染最终报告

```bash
python3 scripts/assemble_dossier_from_bundle.py \
  --input /tmp/equity-dossiers/tsla/research-bundle

python3 scripts/validate_dossier_json.py \
  --input /tmp/equity-dossiers/tsla/research-bundle/dossier.json

python3 scripts/render_dossier_html.py \
  --input /tmp/equity-dossiers/tsla/research-bundle/dossier.json
```

---

## 关键脚本说明

| 脚本 | 作用 |
|---|---|
| `init_research_bundle.py` | 初始化 bundle、TODO 和分层目录 |
| `record_search_round.py` | 记录 query 与候选结果，并写入 `search/` |
| `record_bundle_research.py` | 记录 source / extraction / claim / note / artifact，并复制文件入分层目录 |
| `review_research_progress.py` | 记录 review cycle，更新 todo，派生下一步搜索方向 |
| `merge_module_output.py` | 合并模块 agent 产出的结构化 patch |
| `bundle_status.py` | 查看 bundle 阶段、todo 与落盘计数 |
| `validate_research_bundle.py` | 校验 bundle 结构与 workflow 完整性 |
| `assemble_dossier_from_bundle.py` | 从 bundle 组装 `dossier.json` |
| `validate_dossier_json.py` | 校验最终 dossier |
| `render_dossier_html.py` | 渲染多页 HTML 报告 |

---

## 多 agent 协作原则

- **主 agent**
  - 初始化 bundle
  - 维护父级 todo
  - 组织搜索与 review
  - 决定搜索方向与收敛条件

- **子 agent**
  - 负责某一模块的来源收集、提取与结构化输出
  - 可以提出候选 question todo
  - 不直接接管整体研究计划

详细契约见：

- `references/multi-agent-contracts.md`

---

## 参考资料

建议最少先读这些 reference：

- `references/source-map.md`
- `references/output-schema.md`
- `references/evidence-rules.md`
- `references/research-bundle-schema.md`
- `references/multi-agent-contracts.md`

行业维度再额外读取一份对应的 `sector-*.md`。

---

## 发布到 GitHub 前的注意事项

- 运行时目录 `.omx/` 不应提交
- `__pycache__/`、`.DS_Store`、临时日志不应提交
- 默认生成的研究输出位于 `/tmp/equity-dossiers/...`，不会自动进入仓库
- 如果你把 bundle 或 HTML 输出目录改到仓库内，请额外忽略这些产物目录

---

## 安全与合规说明

本仓库适合保存：

- 研究流程脚本
- 结构定义
- 模板与 reference

不建议直接提交：

- 账户密钥
- 私有研究材料
- 受版权限制的整份原始内容
- 含隐私信息的运行日志

---

## 免责声明

本项目用于研究流程组织与信息沉淀，不构成任何投资建议。  
请自行核验数据来源、时间点与结论。
