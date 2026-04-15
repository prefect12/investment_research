#!/usr/bin/env python3
"""把股票研究 dossier JSON 渲染成单文件最终报告。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Any

from bundle_schema import append_artifact_record, load_bundle, save_bundle
from dossier_schema import load_dossier, validate_dossier


LABEL_MAP = {
    "what_company_is": "这家公司本质上是什么",
    "current_action": "当前动作",
    "why_now": "为什么是现在",
    "core_bet": "核心下注点",
    "market_is_pricing": "市场当前在定价什么",
    "main_error_risk": "主要误判风险",
    "payoff_sources": "赔率来源",
    "next_checks": "下一步核验",
    "scope_statement": "研究范围",
    "information_collected": "收集的信息",
    "research_modules": "研究模块",
    "decision_steps": "形成判断的步骤",
    "limitations": "局限",
    "as_of": "截至日期",
    "status_summary": "当前状态",
    "valuation_summary": "估值状态",
    "price_action_summary": "股价表现",
    "snapshot_metrics": "关键快照",
    "price_levels": "价格位置",
    "support_points": "支持点",
    "risk_points": "风险点",
    "open_questions": "开放问题",
    "management_judgment": "管理层判断",
    "valuation_judgment": "估值判断",
    "macro_context": "宏观背景",
    "regime_position": "所处阶段",
    "regime_mechanism": "传导机制",
    "market_expectation": "市场预期",
    "variant_perception": "预期差",
    "falsifiers": "证伪条件",
    "monitoring_metrics": "跟踪指标",
    "overview": "概览",
    "revenue_breakdown": "收入拆解",
    "moat_summary": "护城河总结",
    "moat_points": "护城河要点",
    "customers": "客户结构",
    "pricing": "定价方式",
    "product_cadence": "产品节奏",
    "customer_voice": "客户反馈",
    "value_chain": "价值链",
    "competitors": "竞争对手",
    "key_points": "关键点",
    "red_flags": "红旗",
    "actions": "资本配置动作",
    "historical_range": "历史区间",
    "peer_comparison": "同业对比",
    "scenarios": "情景分析",
    "regime_context": "市场环境",
    "stock_phases": "股价阶段",
    "style_exposures": "风格暴露",
    "cases": "危机案例",
    "bull_case": "多头观点",
    "bear_case": "空头观点",
    "mispricing_hypothesis": "错价假说",
    "workflow_summary": "流程总结",
    "todo_summary": "待办摘要",
    "search_cycles": "搜索轮次",
    "completion_reason": "完成原因",
    "next_actions": "后续动作",
    "open_items": "未收敛事项",
    "current_stage": "当前阶段",
    "layer_counts": "分层计数",
    "review_cycles": "复盘记录",
    "items": "条目",
    "views": "视角列表",
    "kind": "类型",
    "publisher": "发布方",
    "date": "日期",
    "id": "编号",
    "framework_focus": "框架关注点",
    "fit_assessment": "匹配度",
    "would_likely_invest": "是否可能投资",
    "must_believe": "必须相信什么",
    "judgment_change_conditions": "判断改变条件",
    "key_checks": "关键核验点",
    "criterion": "核验点",
    "assessment": "判断",
    "evidence": "依据",
    "source_ids": "来源编号",
    "label": "指标",
    "value": "数值",
    "note": "备注",
    "share": "占比",
    "trend": "趋势",
    "comment": "说明",
    "date_range": "时间区间",
    "summary": "总结",
    "leadership": "主导管理层",
    "strategy_moves": "关键动作",
    "operating_outcomes": "经营结果",
    "stock_phase": "股价阶段",
    "lessons": "经验教训",
    "tags": "标签",
    "role": "职位",
    "tenure_start": "任职开始",
    "tenure_end": "任职结束",
    "background": "背景",
    "style": "管理风格",
    "key_moves": "关键动作",
    "major_wins": "主要成功",
    "major_errors": "主要失误",
    "impact_summary": "长期影响",
    "outlet": "出处",
    "format": "形式",
    "topics": "主题",
    "takeaway": "核心收获",
    "quote": "短引文",
    "topic": "主题",
    "statement": "原始判断",
    "horizon": "观察期限",
    "result": "结果",
    "outcome": "后续结果",
    "analysis": "分析",
    "capability": "体现能力",
    "positives": "正面点",
    "concerns": "担忧点",
    "why": "原因",
    "priority": "优先级",
    "status": "状态",
    "progress": "进度",
    "useful_source_count": "有效来源数",
    "query": "搜索词",
    "intent": "搜索意图",
    "decision": "复盘决策",
    "candidate_result_count": "候选结果数",
    "timestamp": "时间",
    "todo_title": "对应待办",
    "type": "类型",
    "implication": "含义",
    "comparison": "对比结论",
    "position": "竞争位置",
    "watch_for": "观察点",
    "why_it_matters": "重要性",
    "detail": "说明",
    "stock_move": "股价反应",
    "relative_move": "相对表现",
    "evidence_label": "证据状态",
}

PREFERRED_TITLE_FIELDS = (
    "name",
    "title",
    "label",
    "investor",
    "leader",
    "segment",
    "company",
    "date",
    "module",
    "text",
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="渲染股票研究最终报告。")
    parser.add_argument("--input", required=True, help="结构化 dossier JSON 路径")
    parser.add_argument("--output", help="报告输出路径；默认写到 dossier 同目录下的 report.md")
    return parser.parse_args()


def display_label(key: str) -> str:
    return LABEL_MAP.get(key, key.replace("_", " "))


def is_empty(value: Any) -> bool:
    return value in ("", None, [], {})


def scalar_to_text(value: Any) -> str:
    if value is None:
        return "未提供"
    return str(value).strip() or "未提供"


def markdown_link(title: str, url: str) -> str:
    safe_title = title.replace("[", r"\[").replace("]", r"\]")
    return f"[{safe_title}]({url})"


def pick_entry_title(item: dict[str, Any], fallback: str) -> tuple[str, str | None]:
    for key in PREFERRED_TITLE_FIELDS:
        value = str(item.get(key, "")).strip()
        if value:
            return value, key
    return fallback, None


def render_scalar_list(items: list[Any]) -> list[str]:
    lines: list[str] = []
    for item in items:
        text = scalar_to_text(item)
        if text != "未提供":
            lines.append(f"- {text}")
    return lines or ["- 未提供"]


def render_mapping(mapping: dict[str, Any], *, heading_level: int, omit_keys: set[str] | None = None) -> list[str]:
    lines: list[str] = []
    omit_keys = omit_keys or set()
    for key, value in mapping.items():
        if key in omit_keys:
            continue
        if is_empty(value):
            continue
        label = display_label(key)
        if isinstance(value, str):
            lines.append(f"- **{label}**：{value.strip()}")
            continue
        if isinstance(value, list):
            lines.append(f"- **{label}**：")
            for row in render_list(value, heading_level=heading_level + 1):
                lines.append(f"  {row}" if row else "")
            continue
        if isinstance(value, dict):
            lines.append(f"- **{label}**：")
            nested = render_mapping(value, heading_level=heading_level + 1)
            for row in nested or ["- 未提供"]:
                lines.append(f"  {row}")
            continue
        lines.append(f"- **{label}**：{scalar_to_text(value)}")
    return lines or ["- 未提供"]


def render_list(items: list[Any], *, heading_level: int) -> list[str]:
    if not items:
        return ["- 未提供"]
    if all(not isinstance(item, (dict, list)) for item in items):
        return render_scalar_list(items)

    lines: list[str] = []
    for index, item in enumerate(items, start=1):
        if isinstance(item, dict):
            title, title_key = pick_entry_title(item, f"条目 {index}")
            lines.append(f"{'#' * min(heading_level, 6)} {title}")
            omit_keys = {title_key} if title_key else set()
            lines.extend(render_mapping(item, heading_level=heading_level + 1, omit_keys=omit_keys))
            lines.append("")
            continue
        if isinstance(item, list):
            lines.append(f"{'#' * min(heading_level, 6)} 条目 {index}")
            lines.extend(render_list(item, heading_level=heading_level + 1))
            lines.append("")
            continue
        lines.append(f"- {scalar_to_text(item)}")
    while lines and not lines[-1]:
        lines.pop()
    return lines or ["- 未提供"]


def render_section(title: str, content: dict[str, Any], *, level: int = 2) -> list[str]:
    lines = [f"{'#' * level} {title}", ""]
    section_lines = render_mapping(content, heading_level=level + 1)
    lines.extend(section_lines)
    lines.append("")
    return lines


def render_text_block(title: str, text: str | None, *, level: int = 3) -> list[str]:
    clean = (text or "").strip()
    if not clean:
        return []
    return [f"{'#' * level} {title}", "", clean, ""]


def render_bullet_block(title: str, items: list[Any], *, level: int = 3) -> list[str]:
    if not items:
        return []
    return [f"{'#' * level} {title}", "", *render_list(items, heading_level=level + 1), ""]


def render_report_brief_section(content: dict[str, Any]) -> list[str]:
    lines = ["## 执行摘要", ""]
    lines.extend(render_text_block("公司画像", str(content.get("what_company_is", "")).strip()))
    lines.extend(render_text_block("当前动作", str(content.get("current_action", "")).strip()))
    lines.extend(render_text_block("为什么是现在", str(content.get("why_now", "")).strip()))
    lines.extend(render_text_block("核心下注点", str(content.get("core_bet", "")).strip()))
    lines.extend(render_text_block("市场当前在定价什么", str(content.get("market_is_pricing", "")).strip()))
    lines.extend(render_text_block("主要误判风险", str(content.get("main_error_risk", "")).strip()))
    lines.extend(render_bullet_block("赔率来源", content.get("payoff_sources", [])))
    lines.extend(render_bullet_block("下一步核验", content.get("next_checks", [])))
    return lines or ["## 执行摘要", "", "- 未提供", ""]


def render_report_method_section(content: dict[str, Any]) -> list[str]:
    lines = ["## 研究方法", ""]
    lines.extend(render_text_block("研究范围", str(content.get("scope_statement", "")).strip()))
    lines.extend(render_bullet_block("已收集的信息", content.get("information_collected", [])))
    lines.extend(render_bullet_block("覆盖模块", content.get("research_modules", [])))
    lines.extend(render_bullet_block("形成判断的步骤", content.get("decision_steps", [])))
    lines.extend(render_bullet_block("局限", content.get("limitations", [])))
    return lines or ["## 研究方法", "", "- 未提供", ""]


def render_current_status_section(content: dict[str, Any]) -> list[str]:
    lines = ["## 当前状态", ""]
    as_of = str(content.get("as_of", "")).strip()
    if as_of:
        lines.append(f"截至 {as_of}。")
        lines.append("")
    lines.extend(render_text_block("状态概览", str(content.get("status_summary", "")).strip()))
    lines.extend(render_text_block("估值位置", str(content.get("valuation_summary", "")).strip()))
    lines.extend(render_text_block("股价表现", str(content.get("price_action_summary", "")).strip()))
    lines.extend(render_bullet_block("关键快照", content.get("snapshot_metrics", [])))
    lines.extend(render_bullet_block("价格位置", content.get("price_levels", [])))
    return lines or ["## 当前状态", "", "- 未提供", ""]


def render_summary_section(content: dict[str, Any]) -> list[str]:
    lines = ["## 摘要判断", ""]
    lines.extend(render_bullet_block("支撑判断", content.get("support_points", [])))
    lines.extend(render_bullet_block("主要风险", content.get("risk_points", [])))
    lines.extend(render_bullet_block("仍待回答的问题", content.get("open_questions", [])))
    lines.extend(render_text_block("管理层判断", str(content.get("management_judgment", "")).strip()))
    lines.extend(render_text_block("估值判断", str(content.get("valuation_judgment", "")).strip()))
    return lines or ["## 摘要判断", "", "- 未提供", ""]


def render_investment_case_section(content: dict[str, Any]) -> list[str]:
    lines = ["## 投资主线", ""]
    lines.extend(render_text_block("为什么是现在", str(content.get("why_now", "")).strip()))
    lines.extend(render_text_block("宏观背景", str(content.get("macro_context", "")).strip()))
    lines.extend(render_text_block("所处阶段", str(content.get("regime_position", "")).strip()))
    lines.extend(render_text_block("传导机制", str(content.get("regime_mechanism", "")).strip()))
    lines.extend(render_text_block("市场预期", str(content.get("market_expectation", "")).strip()))
    lines.extend(render_text_block("预期差", str(content.get("variant_perception", "")).strip()))
    lines.extend(render_bullet_block("证伪条件", content.get("falsifiers", [])))
    lines.extend(render_bullet_block("跟踪指标", content.get("monitoring_metrics", [])))
    return lines or ["## 投资主线", "", "- 未提供", ""]


def render_company_history_section(content: dict[str, Any]) -> list[str]:
    lines = ["## 公司历史", ""]
    lines.extend(render_bullet_block("阶段划分", content.get("eras", [])))
    lines.extend(render_bullet_block("关键时间线", content.get("timeline", [])))
    return lines or ["## 公司历史", "", "- 未提供", ""]


def render_management_section(content: dict[str, Any]) -> list[str]:
    lines = ["## 管理层", ""]
    lines.extend(render_bullet_block("核心管理层", content.get("leaders", [])))
    lines.extend(render_bullet_block("访谈与公开表态", content.get("interviews", [])))
    lines.extend(render_bullet_block("历史预判复盘", content.get("predictions", [])))
    lines.extend(render_text_block("综合判断", str(content.get("judgment", "")).strip()))
    return lines or ["## 管理层", "", "- 未提供", ""]


def render_sources(items: list[dict[str, Any]]) -> list[str]:
    lines = ["## 来源附录", ""]
    if not items:
        lines.append("- 未提供来源。")
        lines.append("")
        return lines

    for index, item in enumerate(items, start=1):
        title = str(item.get("title", "")).strip() or f"来源 {index}"
        url = str(item.get("url", "")).strip()
        header = markdown_link(title, url) if url else title
        lines.append(f"### {index}. {header}")
        meta_parts = []
        for key in ("kind", "publisher", "date", "id"):
            value = str(item.get(key, "")).strip()
            if value:
                meta_parts.append(f"{display_label(key)}：{value}")
        if meta_parts:
            lines.append(f"- {' | '.join(meta_parts)}")
        note = str(item.get("note", "")).strip()
        if note:
            lines.append(f"- 备注：{note}")
        lines.append("")
    return lines


def render_document(data: dict[str, Any]) -> str:
    meta = data.get("meta", {})
    company_name = str(meta.get("company_name", "未命名公司")).strip() or "未命名公司"
    ticker = str(meta.get("ticker", "")).strip()
    exchange = str(meta.get("exchange", "")).strip()
    research_date = str(meta.get("research_date", "")).strip()
    conclusion = str(meta.get("conclusion", "未定")).strip() or "未定"
    thesis = str(meta.get("thesis", "")).strip()

    lines = [f"# {company_name} 投资研究报告", ""]
    meta_line = " | ".join(part for part in [ticker, exchange, research_date] if part)
    if meta_line:
        lines.append(meta_line)
        lines.append("")
    lines.append(f"**结论**：{conclusion}")
    if thesis:
        lines.append("")
        lines.append(f"**核心 thesis**：{thesis}")
    lines.append("")

    lines.extend(
        [
            "## 文档目录",
            "",
            "- 执行摘要",
            "- 研究方法",
            "- 当前状态",
            "- 投资主线",
            "- 公司历史",
            "- 管理层",
            "- 业务质量与行业",
            "- 财务、资本配置与估值",
            "- 市场行为、危机与争议",
            "- 投资大师视角",
            "- 研究过程与开放问题",
            "- 来源附录",
            "",
        ]
    )

    lines.extend(render_report_brief_section(data.get("report_brief", {})))
    lines.extend(render_report_method_section(data.get("report_method", {})))
    lines.extend(render_current_status_section(data.get("current_status", {})))
    lines.extend(render_summary_section(data.get("summary", {})))
    lines.extend(render_investment_case_section(data.get("investment_case", {})))
    lines.extend(render_company_history_section(data.get("company_history", {})))
    lines.extend(render_management_section(data.get("management", {})))
    lines.extend(render_section("业务质量", data.get("business_quality", {})))
    lines.extend(render_section("行业与竞争", data.get("industry", {})))
    lines.extend(render_section("财务质量", data.get("financials", {})))
    lines.extend(render_section("资本配置", data.get("capital_allocation", {})))
    lines.extend(render_section("估值", data.get("valuation", {})))
    lines.extend(render_section("市场行为", data.get("market_behavior", {})))
    lines.extend(render_section("危机档案", data.get("crisis_archive", {})))
    lines.extend(render_section("多空争议", data.get("debate", {})))
    lines.extend(render_section("投资大师视角", data.get("investor_lenses", {})))
    lines.extend(render_section("研究过程", data.get("research_process", {})))
    lines.extend(render_section("开放问题", data.get("open_questions", {})))
    lines.extend(render_sources(data.get("sources", {}).get("items", [])))

    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n"


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser()

    try:
        dossier = load_dossier(input_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 dossier: {exc}")
        return 1

    errors, warnings = validate_dossier(dossier)
    if errors:
        print("[错误] dossier 校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1
    if warnings:
        print("[警告] 继续渲染，但发现以下问题：")
        for warning in warnings:
            print(f"- {warning}")

    output_path = Path(args.output).expanduser() if args.output else input_path.parent / "report.md"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(render_document(dossier), encoding="utf-8")
    print(f"[完成] 最终报告: {output_path}")

    bundle_path = input_path.parent / "bundle.json"
    if bundle_path.exists():
        try:
            bundle = load_bundle(bundle_path)
            append_artifact_record(
                bundle,
                owner="system-renderer",
                module="final-assembly",
                path=str(output_path),
                kind="rendered-report",
                title="最终研究报告",
                note="render_dossier_report.py 已生成单文件最终报告",
                todo_ids=["todo-dossier-assembly"],
                layer="artifacts",
                value_tier="used_in_dossier",
            )
            save_bundle(bundle, bundle_path)
            print(f"[完成] bundle 已记录报告渲染结果: {bundle_path}")
        except Exception as exc:  # noqa: BLE001
            print(f"[警告] 无法回写 bundle 报告渲染记录: {exc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
