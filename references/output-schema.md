# Dossier 输出 Schema

用这个文件约束结构化 dossier JSON。默认流程应先完成 `research bundle`，再从 bundle 组装 dossier，最后渲染页面。

## 顶层字段

新版本默认应包含 `report_brief`、`report_method` 和 `investor_lenses`。

```json
{
  "meta": {},
  "report_brief": {},
  "report_method": {},
  "current_status": {},
  "summary": {},
  "investment_case": {},
  "company_history": {},
  "management": {},
  "business_quality": {},
  "industry": {},
  "financials": {},
  "capital_allocation": {},
  "valuation": {},
  "market_behavior": {},
  "crisis_archive": {},
  "debate": {},
  "investor_lenses": {},
  "open_questions": {},
  "sources": {}
}
```

## `meta`

```json
{
  "company_name": "Microsoft",
  "ticker": "MSFT",
  "exchange": "NASDAQ",
  "research_date": "2026-04-12",
  "analyst": "Codex",
  "conclusion": "正向",
  "thesis": "一句话 thesis"
}
```

- `conclusion` 只允许：`正向`、`观察`、`回避`

## `report_brief`

用于执行摘要页最上方的压缩判断，直接回答“现在该不该投、为什么是现在、最可能错在哪、赔率来自哪里”。

```json
{
  "what_company_is": "这家公司本质上是什么",
  "current_action": "观察",
  "why_now": "为什么是现在",
  "core_bet": "这笔判断真正赌的变量是什么",
  "market_is_pricing": "市场当前在定价什么",
  "main_error_risk": "最可能错在哪",
  "payoff_sources": ["赔率来自哪里"],
  "next_checks": ["下一步最该验证什么"]
}
```

## `report_method`

用于封面后的导读页，说明这份报告做了什么、收集了哪些信息、如何形成判断。

```json
{
  "scope_statement": "这份报告的研究范围和目标",
  "information_collected": ["收集了哪些类型的信息"],
  "research_modules": ["覆盖了哪些研究模块"],
  "decision_steps": ["如何一步步形成当前判断"],
  "limitations": ["这份报告的主要局限"]
}
```

## `current_status`

```json
{
  "as_of": "2026-04-12",
  "status_summary": "公司当前处于什么状态",
  "valuation_summary": "当前估值所处位置",
  "price_action_summary": "近期股价、年内表现、距离高点位置等直观总结",
  "snapshot_metrics": [
    {
      "label": "当前股价",
      "value": "$421",
      "note": "示例占位"
    }
  ],
  "price_levels": [
    {
      "label": "距52周高点",
      "value": "-3.1%",
      "note": "示例占位"
    }
  ]
}
```

## `summary`

```json
{
  "support_points": ["..."],
  "risk_points": ["..."],
  "open_questions": ["..."],
  "management_judgment": "一句话管理层判断",
  "valuation_judgment": "一句话估值判断"
}
```

## `investment_case`

```json
{
  "why_now": "为什么是现在",
  "macro_context": "当前时代背景、利率环境、政策周期与传导机制",
  "regime_position": "当前属于顺风、逆风，还是检验真质量阶段",
  "regime_mechanism": "这个判断是如何传导到收入、利润率、现金流、估值和市场预期的",
  "market_expectation": "市场当前在定价什么",
  "variant_perception": "你的预期差",
  "falsifiers": ["哪些情况会让 thesis 失效"],
  "monitoring_metrics": [
    {
      "name": "Azure 增速",
      "why_it_matters": "解释为什么重要",
      "watch_for": "要观察什么"
    }
  ]
}
```

## `company_history`

```json
{
  "eras": [
    {
      "name": "云转型期",
      "date_range": "2014-至今",
      "summary": "这一时期的核心结论",
      "leadership": "谁掌舵",
      "strategy_moves": ["..."],
      "operating_outcomes": ["..."],
      "stock_phase": "股价与估值阶段总结",
      "lessons": ["..."],
      "tags": ["cloud", "replatforming"],
      "source_ids": ["src-10k-2024"]
    }
  ],
  "timeline": [
    {
      "date": "2014-02-04",
      "era": "云转型期",
      "category": "management_change",
      "title": "Satya Nadella 任 CEO",
      "detail": "事件说明",
      "stock_move": "股价阶段反应",
      "relative_move": "相对指数或同行表现",
      "evidence_label": "已证实",
      "tags": ["ceo", "cloud"],
      "source_ids": ["src-proxy-2014"]
    }
  ]
}
```

## `management`

```json
{
  "leaders": [
    {
      "name": "Satya Nadella",
      "role": "CEO",
      "tenure_start": "2014-02-04",
      "tenure_end": "",
      "background": "任前背景",
      "style": "风格总结",
      "key_moves": ["..."],
      "major_wins": ["..."],
      "major_errors": ["..."],
      "impact_summary": "长期影响",
      "tags": ["cloud", "capital-allocation"],
      "source_ids": ["src-proxy-2024"]
    }
  ],
  "interviews": [
    {
      "leader": "Satya Nadella",
      "date": "2015-10-06",
      "title": "会议或采访标题",
      "outlet": "来源机构",
      "format": "podcast",
      "url": "https://example.com",
      "topics": ["cloud", "culture"],
      "takeaway": "本次材料最重要结论",
      "quote": "必要时保留短引文",
      "source_ids": ["src-interview-1"]
    }
  ],
  "predictions": [
    {
      "leader": "Satya Nadella",
      "date": "2016-01-01",
      "topic": "云业务",
      "statement": "当时的前瞻表态",
      "horizon": "2-5年",
      "result": "正确",
      "outcome": "后来发生了什么",
      "analysis": "为什么对或错",
      "capability": "战略预判",
      "tags": ["cloud"],
      "source_ids": ["src-interview-1"]
    }
  ],
  "judgment": "对管理层长期远见与可信度的总结"
}
```

## `investor_lenses`

```json
{
  "overview": "哪些投资大师最可能看懂这家公司、最可能愿意买、最不可能买",
  "views": [
    {
      "investor": "沃伦·巴菲特",
      "framework_focus": ["护城河", "稳健财务", "优秀管理层", "可持续成长", "高股东回报", "估值合理"],
      "fit_assessment": "高匹配",
      "would_likely_invest": "可能会研究，但未必会买",
      "why": "直接回答他今天为什么可能愿意投资或为什么还不会投。",
      "positives": ["..."],
      "concerns": ["..."],
      "must_believe": ["..."],
      "judgment_change_conditions": ["..."],
      "key_checks": [
        {
          "criterion": "护城河",
          "assessment": "强",
          "evidence": "用数据或公开信息解释为什么",
          "source_ids": ["src-1"]
        }
      ],
      "source_ids": ["src-1", "src-2"]
    }
  ]
}
```

- `overview` 要先给总判断，再展开逐个大师。
- `framework_focus` 只写该大师最核心的投资坐标，不要堆空话。
- `fit_assessment` 建议用：`高匹配`、`中匹配`、`低匹配`。
- `would_likely_invest` 要直接回答“今天是否可能愿意投资”，例如：`可能会研究，但未必会买`、`倾向观望`、`大概率不会投资`。
- `why` 必须落到这家公司，而不是复述大师名言。
- `positives`、`concerns`、`must_believe`、`judgment_change_conditions` 都要结合公司数据与公开信息，不要只写哲学口号。
- `key_checks` 要写这些大师最可能进一步核验的项目，例如护城河、资本回报、估值、管理层可信度、宏观敏感度、复利持续性。

## 其余 section

- `business_quality`
  - 必填：`overview`、`revenue_breakdown`、`moat_summary`、`moat_points`、`customers`、`pricing`、`product_cadence`、`customer_voice`
- `industry`
  - 必填：`overview`、`value_chain`、`competitors`
- `financials`
  - 必填：`overview`、`key_points`、`red_flags`
- `capital_allocation`
  - 必填：`overview`、`actions`
- `valuation`
  - 必填：`overview`、`historical_range`、`peer_comparison`、`scenarios`
- `market_behavior`
  - 必填：`overview`、`regime_context`、`stock_phases`、`style_exposures`
- `crisis_archive`
  - 必填：`cases`
- `debate`
  - 必填：`bull_case`、`bear_case`、`mispricing_hypothesis`
- `investor_lenses`
  - 新版本默认应填：`overview`、`views`
- `open_questions`
  - 必填：`items`
- `sources`
  - 必填：`items`

## 通用 item 形状

### `actions`

```json
{
  "date": "2023-01-01",
  "type": "buyback",
  "summary": "动作内容",
  "outcome": "结果或评价",
  "evidence_label": "已证实",
  "tags": ["capital-allocation"],
  "source_ids": ["src-10k-2023"]
}
```

### `competitors` / `peer_comparison`

```json
{
  "company": "Amazon",
  "ticker": "AMZN",
  "comparison": "为什么它是重要对比对象",
  "source_ids": ["src-peer-1"]
}
```

### `sources.items`

完整报告默认应至少提供约 100 条 `sources.items`，并覆盖多个来源 bucket；如果只有十几条来源，应视为草稿而不是完整成品。

```json
{
  "id": "src-10k-2024",
  "title": "Form 10-K 2024",
  "kind": "sec-filing",
  "publisher": "Microsoft",
  "date": "2024-07-30",
  "url": "https://example.com",
  "note": "来源说明"
}
```

### `snapshot_metrics` / `price_levels`

```json
{
  "label": "总市值",
  "value": "$3.1T",
  "note": "示例占位"
}
```

### `revenue_breakdown`

```json
{
  "segment": "Intelligent Cloud",
  "share": "43%",
  "trend": "+19%",
  "comment": "核心增长引擎",
  "source_ids": ["src-10k-2025"]
}
```

### `investor_lenses.views[].key_checks`

```json
{
  "criterion": "安全边际",
  "assessment": "偏弱",
  "evidence": "当前估值已经明显高于其历史低位区间",
  "source_ids": ["src-valuation-1"]
}
```

## 页面固定区块

页面按固定区块渲染：

1. 结论面板
2. 当前状态快照
3. 业务快照、营收拆解与护城河
4. 多空观点
5. 投资大师视角
6. 当前投资判断与预期差
7. 估值
8. 股价与市场行为
9. 行业与竞争
10. 财务与会计质量
11. 资本配置全史
12. 公司时间线
13. 管理层更替地图
14. 管理层访谈索引
15. 管理层预判复盘
16. 危机档案
17. 待验证问题
18. 来源附录
