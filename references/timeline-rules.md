# 时间线规则

## 目标

把“公司史”做成投资可用的证据链，而不是流水账。

## Era 划分

默认按“公司时代”而不是自然年份划分。

优先找这些拐点：

- 创始期 / 上市前后
- 核心业务模式成型
- 重大管理层更替
- 战略转型或再平台化
- 大型并购、分拆、剥离
- 资本配置风格改变
- 利率 regime、流动性 regime、政策周期变化
- 监管或危机冲击

## 老牌公司

- 先做全历史覆盖。
- 对现代模式成型前的时期可以压缩成 1 到 2 个摘要 era。
- 对现代模式成型后的时期，要拆得更细。

## 时间线 item 字段

每条关键时间线事件尽量包含：

- `date`
- `era`
- `category`
- `title`
- `detail`
- `stock_move`
- `relative_move`
- `evidence_label`
- `tags`
- `source_ids`

## 时间线 category 建议

- `management_change`
- `strategy_shift`
- `mna`
- `capital_allocation`
- `regulation`
- `product_cycle`
- `earnings_inflection`
- `crisis`
- `market_repricing`
- `macro_regime`

## 股价阶段归因

不要只写绝对涨跌。至少并列三层：

- 绝对股价阶段
- 相对指数表现
- 相对同行表现

归因时显式区分：

- 基本面变化
- 估值重估
- 市场风格
- 宏观利率 / 周期

同时回答：

- 当时的利率环境和流动性在帮忙还是在拖累
- 这家公司当时是顺风、逆风，还是在接受质量检验
- 公司是顺风扩张，还是逆风中证明了质量

## 管理层更替映射

时间线必须显式标出：

- 谁上任
- 谁离任
- 为什么换人
- 这次换人带来了什么经营或资本配置变化
