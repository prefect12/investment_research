# 多 Agent 契约

这个文件定义主 agent、子 agent、todo 分层和模块 ownership。

## 一句话原则

- **主 agent 管流程与父级 todo。**
- **子 agent 管模块执行与候选问题。**
- **所有搜索与研究过程先落本地 bundle。**
- **最终 HTML 只在主 agent 完成组装后生成。**

## 主 agent 职责

主 agent 负责：

1. 初始化 `research bundle`
2. 维护父级 todo 与 `TODO.md`
3. 选择当前优先级最高的问题待办
4. 决定何时扇出子 agent
5. 汇总 query/result/source/review 信息
6. 在 review 后更新搜索方向
7. 接收子 agent 提交的候选 question todo，并决定是否落盘
8. 合并模块 patch
9. 运行校验、组装 dossier、渲染 HTML

主 agent 不应该把所有正文都自己写完再反填 bundle。

## 子 agent 职责

子 agent 负责：

- 在自己的模块边界内搜集资料
- 提交结构化模块 patch
- 提交来源、claims、笔记、artifacts
- 如果发现新缺口，提出**候选** question todo
- 不直接篡改别的模块的父级 todo

子 agent 默认**不拥有父级 todo 的最终裁决权**。父级 todo 的关闭、阻塞、降级、改方向，由主 agent 在 review 后统一更新。

## todo 分层

### 父级 todo（parent）

父级 todo 是主 agent 的研究控制面板，常见模块包括：

- `research-foundation`
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
- `source-coverage-pass`
- `final-assembly`

### 问题 todo（question）

question todo 用来驱动具体搜索与验证动作，例如：

- 找最近 10-K / 年报 / proxy
- 找最近 earnings release / conference call transcript
- 找 IR deck / investor day
- 找 CEO / CFO 关键访谈入口
- 找估值与市场预期基础数据
- 核验某条管理层前瞻表态是否兑现
- 补某个争议点的反方证据

子 agent 可以新增候选 question todo，但应通过主 agent review 后写入。

## 搜索闭环责任

### 每个执行单元都遵循同一循环

1. 选择一个 todo
2. 发起一轮搜索
3. 记录 query 与候选结果
4. 把有价值的来源/提取/文件落盘
5. 回看已有结果
6. 决定下一轮搜索方向或关闭该 todo

### 关键要求

- 不要只汇报“我看了很多网页”。要把 query、候选结果、来源、笔记、review 写到 bundle。
- 不要只交最终答案。过程数据也要保存。
- 不要在没有 review 的情况下机械堆搜索。

## 返回信封

所有模块仍然返回同一个结构化信封：

```json
{
  "section": "management",
  "owner": "management-profile-agent",
  "summary": "一句话说明本模块最重要结论",
  "data": {},
  "source_additions": [],
  "raw_notes": [],
  "extracted_claims": [],
  "artifacts": [],
  "gaps": [],
  "conflicts": []
}
```

约束：

- `data` 必须是 partial dossier patch
- `source_additions` 必须是结构化来源
- `gaps` 要明确写缺口
- `conflicts` 要明确写冲突
- `raw_notes/extracted_claims/artifacts` 尽量交，不要浪费过程材料

## 固定模块 ownership

### 1. `company-history`

- 负责：era 划分、关键转折、组织演化、重大事件
- 输出到：`company_history`

### 2. `management-profile`

- 负责：创始人、董事长、CEO、CFO、关键高管画像
- 输出到：`management.leaders`

### 3. `management-interviews`

- 负责：股东信、电话会、投资者日、访谈与公开表态索引
- 输出到：`management.interviews`

### 4. `prediction-review`

- 负责：管理层前瞻表态抽取与事后复盘
- 输出到：`management.predictions`、`management.judgment`

### 5. `business-quality`

- 负责：产品、客户、预算来源、采购链路、价格、产品节奏、客户反馈
- 输出到：`business_quality`

### 6. `industry-competition`

- 负责：价值链、竞争对手、利润池、替代威胁、多空争议
- 输出到：`industry`、`debate`

### 7. `financial-quality`

- 负责：利润质量、现金流、会计红旗、资本配置、危机档案
- 输出到：`financials`、`capital_allocation`、`crisis_archive`

### 8. `market-valuation`

- 负责：股价阶段、历史估值、市场预期、预期差
- 输出到：`investment_case`、`valuation`、`market_behavior`

### 9. `macro-regime`

- 负责：时代背景、利率环境、政策与风格切换，以及传导到经营和估值的机制
- 输出到：`investment_case.macro_context`、`market_behavior.regime_context`

### 10. `investor-master-views`

- 负责：按不同投资框架并行审视公司
- 主 agent 应继续拆分为多个 investor-style 子 agent
- 每个子 agent 只拥有自己那一项 `investor_lenses.views`

### 11. `sector-specialist`

- 负责：行业专属指标、估值口径、监管路径与特殊风险

## 大师视角额外规则

每位大师子 agent：

- 必须明确回答“今天是否可能愿意投资”
- 必须写这家公司，而不是写大师名言
- 必须给出可验证的 `must_believe` 与 `judgment_change_conditions`
- 达里奥视角必须显式写宏观与风险平衡
- 格雷厄姆视角必须显式写安全边际与资产负债表
- 林奇视角必须显式写一线体验、产品与渠道验证

## 合并与冲突规则

- 先把模块结果写进 bundle，再统一 assemble
- 同一事实冲突时优先保留一级来源
- 一级来源之间冲突时显式写入 `conflicts`
- 找不到资料就写 `gaps`，不要沉默跳过
- 不要让子 agent 直接写最终 HTML prose

## 推荐协作节奏

1. 主 agent 选一个父级 todo / question todo
2. 扇出相关模块子 agent
3. 子 agent 先交 query/result/source/review 材料，再交模块 patch
4. 主 agent 做 review，决定是否继续搜索、创建新 question todo、关闭旧 todo
5. 阶段门槛满足后再进入 assembly
