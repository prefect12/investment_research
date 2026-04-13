#!/usr/bin/env python3
"""股票研究报告的共享 schema 与校验工具。"""

from __future__ import annotations

import json
import re
from datetime import datetime
from pathlib import Path
from typing import Any

REQUIRED_TOP_LEVEL = [
    "meta",
    "current_status",
    "summary",
    "investment_case",
    "company_history",
    "management",
    "business_quality",
    "industry",
    "financials",
    "capital_allocation",
    "valuation",
    "market_behavior",
    "crisis_archive",
    "debate",
    "research_process",
    "open_questions",
    "sources",
]

ALLOWED_CONCLUSIONS = {"正向", "观察", "回避"}
ALLOWED_EVIDENCE_LABELS = {"已证实", "高可信推断", "待验证"}
ALLOWED_PREDICTION_RESULTS = {"正确", "部分正确", "错误", "无法验证"}
MIN_COMPLETE_REPORT_SOURCES = 100
MIN_SOURCE_KIND_COVERAGE = 6


def load_dossier(path: str | Path) -> dict[str, Any]:
    with Path(path).expanduser().open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("dossier 顶层必须是 JSON 对象")
    return data


def slugify(text: str) -> str:
    normalized = re.sub(r"[^a-zA-Z0-9]+", "-", text.strip().lower()).strip("-")
    return normalized or "company"


def dossier_slug(data: dict[str, Any]) -> str:
    meta = data.get("meta", {})
    ticker = str(meta.get("ticker", "")).strip()
    company_name = str(meta.get("company_name", "")).strip()
    joined = "-".join(part for part in [ticker, company_name] if part)
    return slugify(joined or "company-dossier")


def timestamp_slug() -> str:
    return datetime.now().strftime("%Y%m%dT%H%M%S")


def default_output_dir(
    data: dict[str, Any],
    base_dir: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    if output_dir:
        return Path(output_dir).expanduser()
    return Path(base_dir).expanduser() / dossier_slug(data)


def validate_dossier(data: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_TOP_LEVEL:
        if key not in data:
            errors.append(f"缺少顶层字段: {key}")

    if errors:
        return errors, warnings

    meta = _require_dict(data, "meta", errors)
    report_brief = data.get("report_brief")
    report_method = data.get("report_method")
    current_status = _require_dict(data, "current_status", errors)
    summary = _require_dict(data, "summary", errors)
    investment_case = _require_dict(data, "investment_case", errors)
    company_history = _require_dict(data, "company_history", errors)
    management = _require_dict(data, "management", errors)
    business_quality = _require_dict(data, "business_quality", errors)
    industry = _require_dict(data, "industry", errors)
    financials = _require_dict(data, "financials", errors)
    capital_allocation = _require_dict(data, "capital_allocation", errors)
    valuation = _require_dict(data, "valuation", errors)
    market_behavior = _require_dict(data, "market_behavior", errors)
    crisis_archive = _require_dict(data, "crisis_archive", errors)
    debate = _require_dict(data, "debate", errors)
    research_process = _require_dict(data, "research_process", errors)
    open_questions = _require_dict(data, "open_questions", errors)
    sources = _require_dict(data, "sources", errors)

    _require_keys(meta, ["company_name", "ticker", "research_date", "conclusion", "thesis"], "meta", errors)
    if isinstance(report_brief, dict):
        _require_keys(
            report_brief,
            ["what_company_is", "current_action", "why_now", "core_bet", "market_is_pricing", "main_error_risk", "payoff_sources", "next_checks"],
            "report_brief",
            errors,
        )
    else:
        warnings.append("缺少顶层字段: report_brief，将在渲染时使用兼容默认值。")

    if isinstance(report_method, dict):
        _require_keys(
            report_method,
            ["scope_statement", "information_collected", "research_modules", "decision_steps", "limitations"],
            "report_method",
            errors,
        )
    else:
        warnings.append("缺少顶层字段: report_method，将在渲染时使用兼容默认值。")
    _require_keys(
        current_status,
        ["as_of", "status_summary", "valuation_summary", "price_action_summary", "snapshot_metrics", "price_levels"],
        "current_status",
        errors,
    )
    _require_keys(
        summary,
        ["support_points", "risk_points", "open_questions", "management_judgment", "valuation_judgment"],
        "summary",
        errors,
    )
    _require_keys(
        investment_case,
        [
            "why_now",
            "macro_context",
            "regime_position",
            "regime_mechanism",
            "market_expectation",
            "variant_perception",
            "falsifiers",
            "monitoring_metrics",
        ],
        "investment_case",
        errors,
    )
    _require_keys(company_history, ["eras", "timeline"], "company_history", errors)
    _require_keys(management, ["leaders", "interviews", "predictions", "judgment"], "management", errors)
    _require_keys(
        business_quality,
        ["overview", "revenue_breakdown", "moat_summary", "moat_points", "customers", "pricing", "product_cadence", "customer_voice"],
        "business_quality",
        errors,
    )
    _require_keys(industry, ["overview", "value_chain", "competitors"], "industry", errors)
    _require_keys(financials, ["overview", "key_points", "red_flags"], "financials", errors)
    _require_keys(capital_allocation, ["overview", "actions"], "capital_allocation", errors)
    _require_keys(valuation, ["overview", "historical_range", "peer_comparison", "scenarios"], "valuation", errors)
    _require_keys(market_behavior, ["overview", "regime_context", "stock_phases", "style_exposures"], "market_behavior", errors)
    _require_keys(crisis_archive, ["cases"], "crisis_archive", errors)
    _require_keys(debate, ["bull_case", "bear_case", "mispricing_hypothesis"], "debate", errors)
    _require_keys(
        research_process,
        ["workflow_summary", "todo_summary", "search_cycles", "completion_reason", "next_actions", "open_items"],
        "research_process",
        errors,
    )
    _require_keys(open_questions, ["items"], "open_questions", errors)
    _require_keys(sources, ["items"], "sources", errors)

    conclusion = meta.get("conclusion")
    if conclusion not in ALLOWED_CONCLUSIONS:
        errors.append(f"meta.conclusion 必须是 {sorted(ALLOWED_CONCLUSIONS)} 之一")

    _require_list(summary, "support_points", errors)
    _require_list(summary, "risk_points", errors)
    _require_list(summary, "open_questions", errors)
    if isinstance(report_brief, dict):
        _require_list(report_brief, "payoff_sources", errors)
        _require_list(report_brief, "next_checks", errors)
    if isinstance(report_method, dict):
        _require_list(report_method, "information_collected", errors)
        _require_list(report_method, "research_modules", errors)
        _require_list(report_method, "decision_steps", errors)
        _require_list(report_method, "limitations", errors)
    _require_list(current_status, "snapshot_metrics", errors)
    _require_list(current_status, "price_levels", errors)
    _require_list(investment_case, "falsifiers", errors)
    _require_list(investment_case, "monitoring_metrics", errors)
    _require_list(research_process, "todo_summary", errors)
    _require_list(research_process, "search_cycles", errors)
    _require_list(research_process, "next_actions", errors)
    _require_list(research_process, "open_items", errors)

    _validate_list_items(current_status.get("snapshot_metrics"), "current_status.snapshot_metrics", ["label", "value"], errors)
    _validate_list_items(current_status.get("price_levels"), "current_status.price_levels", ["label", "value"], errors)
    _validate_list_items(
        business_quality.get("revenue_breakdown"),
        "business_quality.revenue_breakdown",
        ["segment", "share", "trend", "comment"],
        errors,
    )
    _validate_list_items(company_history.get("eras"), "company_history.eras", ["name", "date_range", "summary"], errors)
    _validate_list_items(
        company_history.get("timeline"),
        "company_history.timeline",
        ["date", "era", "category", "title", "detail"],
        errors,
    )
    _validate_list_items(management.get("leaders"), "management.leaders", ["name", "role", "tenure_start"], errors)
    _validate_list_items(
        management.get("interviews"),
        "management.interviews",
        ["leader", "date", "title", "outlet", "url", "takeaway"],
        errors,
    )
    _validate_list_items(
        management.get("predictions"),
        "management.predictions",
        ["leader", "date", "topic", "statement", "result", "analysis"],
        errors,
    )
    _validate_list_items(capital_allocation.get("actions"), "capital_allocation.actions", ["date", "type", "summary"], errors)
    _validate_list_items(valuation.get("peer_comparison"), "valuation.peer_comparison", ["company", "comparison"], errors)
    _validate_list_items(valuation.get("scenarios"), "valuation.scenarios", ["name", "thesis", "implication"], errors)
    _validate_list_items(market_behavior.get("stock_phases"), "market_behavior.stock_phases", ["name", "date_range", "summary"], errors)
    _validate_list_items(crisis_archive.get("cases"), "crisis_archive.cases", ["date", "title", "summary"], errors)
    _validate_list_items(
        research_process.get("todo_summary"),
        "research_process.todo_summary",
        ["module", "status", "progress", "useful_source_count", "summary"],
        errors,
    )
    _validate_list_items(
        research_process.get("search_cycles"),
        "research_process.search_cycles",
        ["query", "intent", "outcome", "decision"],
        errors,
    )
    _validate_list_items(
        research_process.get("open_items"),
        "research_process.open_items",
        ["title", "module", "priority", "status"],
        errors,
    )
    _validate_list_items(sources.get("items"), "sources.items", ["id", "title", "kind", "url"], errors)

    for item in management.get("predictions", []) or []:
        if not isinstance(item, dict):
            continue
        if item.get("result") not in ALLOWED_PREDICTION_RESULTS:
            errors.append(
                "management.predictions.result 必须是 "
                f"{sorted(ALLOWED_PREDICTION_RESULTS)} 之一"
            )

    _validate_investor_lenses(data, errors, warnings)

    _validate_optional_evidence_labels(data, errors)
    _validate_source_depth(data, errors, warnings)
    _validate_source_references(data, warnings)

    return errors, warnings


def _validate_investor_lenses(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    section = data.get("investor_lenses")
    if section is None:
        if isinstance(data.get("investor_master_views"), dict):
            warnings.append("检测到旧字段 investor_master_views，建议迁移到 investor_lenses。")
        else:
            warnings.append("缺少顶层字段: investor_lenses，将在渲染时使用兼容默认值。")
        return

    if not isinstance(section, dict):
        errors.append("investor_lenses 必须是对象")
        return

    _require_keys(section, ["overview", "views"], "investor_lenses", errors)
    _require_list(section, "views", errors)
    _validate_list_items(
        section.get("views"),
        "investor_lenses.views",
        [
            "investor",
            "framework_focus",
            "fit_assessment",
            "would_likely_invest",
            "why",
            "positives",
            "concerns",
            "must_believe",
            "judgment_change_conditions",
            "key_checks",
        ],
        errors,
    )
    for index, item in enumerate(section.get("views", []) or []):
        if not isinstance(item, dict):
            continue
        if isinstance(item.get("key_checks"), list):
            _validate_list_items(
                item.get("key_checks"),
                f"investor_lenses.views[{index}].key_checks",
                ["criterion", "assessment", "evidence"],
                errors,
            )


def _require_dict(data: dict[str, Any], key: str, errors: list[str]) -> dict[str, Any]:
    value = data.get(key)
    if not isinstance(value, dict):
        errors.append(f"{key} 必须是对象")
        return {}
    return value


def _require_keys(node: dict[str, Any], keys: list[str], prefix: str, errors: list[str]) -> None:
    for key in keys:
        if key not in node:
            errors.append(f"缺少字段: {prefix}.{key}")


def _require_list(node: dict[str, Any], key: str, errors: list[str]) -> None:
    value = node.get(key)
    if not isinstance(value, list):
        errors.append(f"{key} 必须是数组")


def _validate_list_items(value: Any, path: str, required_keys: list[str], errors: list[str]) -> None:
    if not isinstance(value, list):
        errors.append(f"{path} 必须是数组")
        return
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            errors.append(f"{path}[{index}] 必须是对象")
            continue
        for key in required_keys:
            if key not in item:
                errors.append(f"缺少字段: {path}[{index}].{key}")


def _validate_optional_evidence_labels(node: Any, errors: list[str], path: str = "root") -> None:
    if isinstance(node, dict):
        if "evidence_label" in node and node["evidence_label"] not in ALLOWED_EVIDENCE_LABELS:
            errors.append(f"{path}.evidence_label 必须是 {sorted(ALLOWED_EVIDENCE_LABELS)} 之一")
        for key, value in node.items():
            _validate_optional_evidence_labels(value, errors, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            _validate_optional_evidence_labels(value, errors, f"{path}[{index}]")


def _validate_source_references(data: dict[str, Any], warnings: list[str]) -> None:
    source_items = data.get("sources", {}).get("items", [])
    if not isinstance(source_items, list):
        return

    known_ids = {
        item.get("id")
        for item in source_items
        if isinstance(item, dict) and isinstance(item.get("id"), str) and item.get("id").strip()
    }
    if not known_ids:
        return

    referenced_ids = _collect_source_ids(data)
    missing_ids = sorted(source_id for source_id in referenced_ids if source_id not in known_ids)
    if missing_ids:
        warnings.append(f"存在未定义的 source_ids: {', '.join(missing_ids)}")


def _validate_source_depth(data: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    source_items = data.get("sources", {}).get("items", [])
    if not isinstance(source_items, list):
        return

    source_count = len([item for item in source_items if isinstance(item, dict)])
    if source_count < MIN_COMPLETE_REPORT_SOURCES:
        errors.append(
            "sources.items 数量不足："
            f"完整报告至少需要 {MIN_COMPLETE_REPORT_SOURCES} 条公开信息源，当前仅 {source_count} 条"
        )

    kinds = {
        str(item.get("kind", "")).strip()
        for item in source_items
        if isinstance(item, dict) and str(item.get("kind", "")).strip()
    }
    if len(kinds) < MIN_SOURCE_KIND_COVERAGE:
        warnings.append(
            "来源类型覆盖偏窄："
            f"建议至少覆盖 {MIN_SOURCE_KIND_COVERAGE} 类 source kind，当前仅 {len(kinds)} 类"
        )


def _collect_source_ids(node: Any) -> set[str]:
    collected: set[str] = set()
    if isinstance(node, dict):
        if "source_ids" in node and isinstance(node["source_ids"], list):
            collected.update(
                str(value).strip()
                for value in node["source_ids"]
                if isinstance(value, str) and value.strip()
            )
        for value in node.values():
            collected.update(_collect_source_ids(value))
    elif isinstance(node, list):
        for value in node:
            collected.update(_collect_source_ids(value))
    return collected
