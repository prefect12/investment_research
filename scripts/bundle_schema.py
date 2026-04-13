#!/usr/bin/env python3
"""research bundle 的 schema、workflow 状态和组装工具。"""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from dossier_schema import dossier_slug

BUNDLE_VERSION = 3

ALLOWED_TODO_KINDS = {
    "source-gathering",
    "fact-verification",
    "module-synthesis",
    "gap-followup",
}
ALLOWED_TODO_LEVELS = {"parent", "question"}
ALLOWED_TODO_STAGES = {"foundation", "module", "gap_close", "assembly"}
ALLOWED_TODO_PRIORITIES = {"P0", "P1", "P2"}
ALLOWED_TODO_STATUSES = {"todo", "in_progress", "done", "blocked", "dropped"}
ALLOWED_SEARCH_OUTCOMES = {"no_hit", "duplicate", "lead", "evidence", "counterevidence"}
USEFUL_SEARCH_OUTCOMES = {"lead", "evidence", "counterevidence"}
ALLOWED_RESULT_DISPOSITIONS = {"candidate", "opened", "skipped", "duplicate", "discarded", "promoted"}
ALLOWED_SOURCE_STAGES = {"candidate", "captured", "downloaded", "extracted", "promoted"}
ALLOWED_VALUE_TIERS = {"candidate", "useful", "used_in_dossier"}
ALLOWED_STAGES = {"initialized", "research_started", "foundation_ready", "module_ready", "report_ready"}

SEARCH_QUERY_SUBDIR = Path("search/queries")
SEARCH_RESULT_SUBDIR = Path("search/results")
SEARCH_REVIEW_SUBDIR = Path("search/reviews")
DEFAULT_BUNDLE_DIRS = [
    SEARCH_QUERY_SUBDIR,
    SEARCH_RESULT_SUBDIR,
    SEARCH_REVIEW_SUBDIR,
    Path("raw"),
    Path("extracted"),
    Path("working"),
    Path("promoted"),
    Path("artifacts"),
]

RESEARCH_ASSET_KEYS = [
    "query_records",
    "result_records",
    "source_records",
    "extraction_records",
    "claim_records",
    "note_records",
    "review_records",
    "artifact_records",
]

DEFAULT_REQUIRED_MODULES = [
    "company-history",
    "management-profile",
    "management-interviews",
    "prediction-review",
    "business-quality",
    "industry-competition",
    "financial-quality",
    "market-valuation",
    "macro-regime",
    "investor-master-views",
    "sector-specialist",
]

DEFAULT_MINIMUM_SOURCE_BUCKETS = [
    "财报与年报",
    "监管与申报文件",
    "电话会与实录",
    "投资者材料",
    "管理层访谈与公开表态",
    "市场与估值数据",
]

DEFAULT_PARENT_TODO_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "id": "todo-foundation-primary-sources",
        "module": "research-foundation",
        "title": "补齐一级来源与研究起始材料",
        "kind": "source-gathering",
        "level": "parent",
        "stage": "foundation",
        "priority": "P0",
        "done_criteria": [
            "已建立 filing / earnings / IR / management / market data 的基础来源池",
            "至少完成一轮 useful search 与方向复盘",
        ],
    },
    {
        "id": "todo-company-history",
        "module": "company-history",
        "title": "完成公司历史阶段与关键转折梳理",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P1",
        "done_criteria": [
            "已形成 era 划分与关键时间线草稿",
            "重大转折已有来源支撑",
        ],
    },
    {
        "id": "todo-management-profile",
        "module": "management-profile",
        "title": "完成管理层任期、风格与权力结构梳理",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P1",
        "done_criteria": [
            "关键管理层人物档案完整",
            "proxy / 官方团队页 / 关键资料已覆盖",
        ],
    },
    {
        "id": "todo-management-interviews",
        "module": "management-interviews",
        "title": "补齐电话会、访谈与公开表态材料",
        "kind": "source-gathering",
        "level": "parent",
        "stage": "module",
        "priority": "P1",
        "done_criteria": [
            "管理层访谈索引可用于 prediction-review",
            "至少覆盖 earnings call / IR material / 公开访谈中的两类",
        ],
    },
    {
        "id": "todo-prediction-review",
        "module": "prediction-review",
        "title": "完成管理层前瞻判断复盘",
        "kind": "fact-verification",
        "level": "parent",
        "stage": "module",
        "priority": "P1",
        "depends_on": ["todo-management-interviews"],
        "done_criteria": [
            "至少抽出数条可复盘的前瞻表态",
            "每条表态已有结果判断或明确无法验证说明",
        ],
    },
    {
        "id": "todo-business-quality",
        "module": "business-quality",
        "title": "完成业务结构、客户与护城河判断",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P0",
        "done_criteria": [
            "业务结构与收入拆解可直接进入 dossier",
            "关键客户、产品与价格逻辑已有证据支撑",
        ],
    },
    {
        "id": "todo-industry-competition",
        "module": "industry-competition",
        "title": "完成行业格局、竞争对手与多空争议梳理",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P0",
        "done_criteria": [
            "主要竞争对手与价值链位置明确",
            "bull / bear 争议点已形成结构化结论",
        ],
    },
    {
        "id": "todo-financial-quality",
        "module": "financial-quality",
        "title": "完成财务质量、现金流与资本配置核验",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P0",
        "done_criteria": [
            "收入、利润、现金流、capex 与红旗点已有结构化判断",
            "资本配置动作与约束已梳理清楚",
        ],
    },
    {
        "id": "todo-market-valuation",
        "module": "market-valuation",
        "title": "完成估值、市场预期差与赔率来源判断",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P0",
        "done_criteria": [
            "当前估值位置与历史区间明确",
            "市场预期与预期差已有清晰结论",
        ],
    },
    {
        "id": "todo-macro-regime",
        "module": "macro-regime",
        "title": "完成宏观 regime、政策周期与传导链条分析",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P1",
        "done_criteria": [
            "利率、政策或风格变量对经营与估值的传导已写清",
            "已判断当前属于顺风、逆风或检验真质量阶段",
        ],
    },
    {
        "id": "todo-investor-master-views",
        "module": "investor-master-views",
        "title": "完成多框架投资大师视角补充检验",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "module",
        "priority": "P1",
        "done_criteria": [
            "主要投资框架视角已补齐",
            "每个框架都回答了会不会投、为什么、会核验什么",
        ],
    },
    {
        "id": "todo-sector-specialist",
        "module": "sector-specialist",
        "title": "补齐行业专属指标、估值口径与监管路径",
        "kind": "fact-verification",
        "level": "parent",
        "stage": "module",
        "priority": "P1",
        "done_criteria": [
            "行业特有指标和估值口径明确",
            "行业专属监管或风险路径已有说明",
        ],
    },
    {
        "id": "todo-source-coverage",
        "module": "source-coverage-pass",
        "title": "补齐来源覆盖与附录质量检查",
        "kind": "gap-followup",
        "level": "parent",
        "stage": "gap_close",
        "priority": "P1",
        "done_criteria": [
            "promoted sources 达到完整报告阈值",
            "关键 source bucket 覆盖达标",
        ],
    },
    {
        "id": "todo-dossier-assembly",
        "module": "final-assembly",
        "title": "完成 dossier 组装、校验与 HTML 渲染",
        "kind": "module-synthesis",
        "level": "parent",
        "stage": "assembly",
        "priority": "P1",
        "depends_on": [
            "todo-business-quality",
            "todo-industry-competition",
            "todo-financial-quality",
            "todo-market-valuation",
        ],
        "done_criteria": [
            "bundle 校验通过",
            "dossier 校验通过",
            "多页 HTML 已生成并可检查",
        ],
    },
]

DEFAULT_QUESTION_TODO_BLUEPRINTS: list[dict[str, Any]] = [
    {
        "id": "todo-question-foundation-filings",
        "parent_id": "todo-foundation-primary-sources",
        "module": "research-foundation",
        "title": "收集 filing / 年报 / proxy 等一级来源",
        "kind": "source-gathering",
        "level": "question",
        "stage": "foundation",
        "priority": "P0",
        "done_criteria": ["已拿到最近年度 filing、proxy 或同等级监管材料"],
    },
    {
        "id": "todo-question-foundation-earnings",
        "parent_id": "todo-foundation-primary-sources",
        "module": "research-foundation",
        "title": "收集最新 earnings release / conference call / transcript",
        "kind": "source-gathering",
        "level": "question",
        "stage": "foundation",
        "priority": "P0",
        "done_criteria": ["已拿到最近财报新闻稿与至少一类电话会材料"],
    },
    {
        "id": "todo-question-foundation-ir",
        "parent_id": "todo-foundation-primary-sources",
        "module": "research-foundation",
        "title": "收集 IR deck、investor day、管理层官方材料",
        "kind": "source-gathering",
        "level": "question",
        "stage": "foundation",
        "priority": "P1",
        "done_criteria": ["IR / investor day 等官方材料已建立索引"],
    },
    {
        "id": "todo-question-foundation-management",
        "parent_id": "todo-foundation-primary-sources",
        "module": "research-foundation",
        "title": "收集管理层访谈与公开表态入口来源",
        "kind": "source-gathering",
        "level": "question",
        "stage": "foundation",
        "priority": "P1",
        "done_criteria": ["管理层访谈入口来源已形成最小样本池"],
    },
    {
        "id": "todo-question-foundation-market-data",
        "parent_id": "todo-foundation-primary-sources",
        "module": "research-foundation",
        "title": "收集股价、估值与市场预期基础数据来源",
        "kind": "source-gathering",
        "level": "question",
        "stage": "foundation",
        "priority": "P1",
        "done_criteria": ["价格、估值和共识预期来源已建立最小覆盖"],
    },
]

EMPTY_DOSSIER_TEMPLATE: dict[str, Any] = {
    "meta": {
        "company_name": "",
        "ticker": "",
        "exchange": "",
        "research_date": "",
        "analyst": "Codex",
        "conclusion": "观察",
        "thesis": "",
    },
    "report_brief": {
        "what_company_is": "",
        "current_action": "",
        "why_now": "",
        "core_bet": "",
        "market_is_pricing": "",
        "main_error_risk": "",
        "payoff_sources": [],
        "next_checks": [],
    },
    "report_method": {
        "scope_statement": "",
        "information_collected": [],
        "research_modules": [],
        "decision_steps": [],
        "limitations": [],
    },
    "current_status": {
        "as_of": "",
        "status_summary": "",
        "valuation_summary": "",
        "price_action_summary": "",
        "snapshot_metrics": [],
        "price_levels": [],
    },
    "summary": {
        "support_points": [],
        "risk_points": [],
        "open_questions": [],
        "management_judgment": "",
        "valuation_judgment": "",
    },
    "investment_case": {
        "why_now": "",
        "macro_context": "",
        "regime_position": "",
        "regime_mechanism": "",
        "market_expectation": "",
        "variant_perception": "",
        "falsifiers": [],
        "monitoring_metrics": [],
    },
    "company_history": {"eras": [], "timeline": []},
    "management": {"leaders": [], "interviews": [], "predictions": [], "judgment": ""},
    "business_quality": {
        "overview": "",
        "revenue_breakdown": [],
        "moat_summary": "",
        "moat_points": [],
        "customers": "",
        "pricing": "",
        "product_cadence": "",
        "customer_voice": "",
    },
    "industry": {"overview": "", "value_chain": "", "competitors": []},
    "financials": {"overview": "", "key_points": [], "red_flags": []},
    "capital_allocation": {"overview": "", "actions": []},
    "valuation": {"overview": "", "historical_range": "", "peer_comparison": [], "scenarios": []},
    "market_behavior": {"overview": "", "regime_context": "", "stock_phases": [], "style_exposures": []},
    "crisis_archive": {"cases": []},
    "debate": {"bull_case": "", "bear_case": "", "mispricing_hypothesis": ""},
    "investor_lenses": {"overview": "", "views": []},
    "research_process": {
        "workflow_summary": "",
        "todo_summary": [],
        "search_cycles": [],
        "completion_reason": "",
        "next_actions": [],
        "open_items": [],
        "current_stage": "initialized",
        "layer_counts": {},
        "review_cycles": [],
    },
    "open_questions": {"items": []},
    "sources": {"items": []},
}

REQUIRED_BUNDLE_KEYS = [
    "bundle_version",
    "created_at",
    "updated_at",
    "dossier_seed",
    "module_outputs",
    "research_assets",
    "workflow",
]

REQUIRED_MODULE_KEYS = [
    "section",
    "owner",
    "summary",
    "data",
    "source_additions",
    "gaps",
    "conflicts",
]

REQUIRED_WORKFLOW_KEYS = [
    "todo_items",
    "search_journal",
    "review_cycles",
    "current_stage",
    "completion_gates",
    "next_actions",
    "summary",
]


def timestamp_iso() -> str:
    return datetime.now().strftime("%Y-%m-%dT%H:%M:%S")


def unique_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now().strftime('%Y%m%d%H%M%S%f')}"


def bundle_path_from_input(path: str | Path) -> Path:
    candidate = Path(path).expanduser()
    if candidate.is_dir():
        return candidate / "bundle.json"
    return candidate


def bundle_dir_from_input(path: str | Path) -> Path:
    return bundle_path_from_input(path).parent


def default_bundle_dir(
    dossier_seed: dict[str, Any],
    base_dir: str | Path,
    output_dir: str | Path | None = None,
) -> Path:
    if output_dir:
        return Path(output_dir).expanduser()
    return Path(base_dir).expanduser() / dossier_slug(dossier_seed) / "research-bundle"


def default_todo_markdown_path(path: str | Path) -> Path:
    return bundle_dir_from_input(path) / "TODO.md"


def ensure_bundle_dirs(bundle_dir: str | Path) -> None:
    root = Path(bundle_dir).expanduser()
    root.mkdir(parents=True, exist_ok=True)
    staged_roots = [
        SEARCH_QUERY_SUBDIR,
        SEARCH_RESULT_SUBDIR,
        SEARCH_REVIEW_SUBDIR,
        Path("raw"),
        Path("extracted"),
        Path("working"),
        Path("promoted"),
        Path("artifacts"),
    ]
    for relative in DEFAULT_BUNDLE_DIRS:
        (root / relative).mkdir(parents=True, exist_ok=True)
    for relative in staged_roots:
        for stage in sorted(ALLOWED_TODO_STAGES | {"misc"}):
            (root / relative / stage).mkdir(parents=True, exist_ok=True)


def load_bundle(path: str | Path) -> dict[str, Any]:
    bundle_path = bundle_path_from_input(path)
    with bundle_path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("research bundle 顶层必须是 JSON 对象")
    return data


def save_bundle(bundle: dict[str, Any], path: str | Path) -> Path:
    bundle_path = bundle_path_from_input(path)
    ensure_bundle_dirs(bundle_path.parent)
    normalized = refresh_bundle_state(bundle)
    bundle_path.write_text(json.dumps(normalized, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    default_todo_markdown_path(bundle_path).write_text(render_todo_markdown(normalized), encoding="utf-8")
    return bundle_path


def init_bundle(dossier_seed: dict[str, Any]) -> dict[str, Any]:
    bundle = {
        "bundle_version": BUNDLE_VERSION,
        "created_at": timestamp_iso(),
        "updated_at": timestamp_iso(),
        "dossier_seed": deep_merge(EMPTY_DOSSIER_TEMPLATE, dossier_seed),
        "module_outputs": [],
        "research_assets": {key: [] for key in RESEARCH_ASSET_KEYS},
        "workflow": init_workflow(),
    }
    return refresh_bundle_state(bundle)


def init_workflow() -> dict[str, Any]:
    return {
        "todo_items": [_normalize_todo_item(item) for item in DEFAULT_PARENT_TODO_BLUEPRINTS + DEFAULT_QUESTION_TODO_BLUEPRINTS],
        "search_journal": [],
        "review_cycles": [],
        "current_stage": "initialized",
        "completion_gates": _normalize_completion_gates({}),
        "next_actions": [],
        "summary": {},
    }


def refresh_bundle_state(bundle: dict[str, Any]) -> dict[str, Any]:
    workflow = bundle.get("workflow")
    if not isinstance(workflow, dict):
        workflow = init_workflow()
        bundle["workflow"] = workflow

    bundle.setdefault("module_outputs", [])
    bundle["research_assets"] = _normalize_research_assets(bundle.get("research_assets", {}))
    workflow["todo_items"] = _normalize_todo_items(workflow.get("todo_items", []))
    workflow["search_journal"] = _normalize_search_journal(workflow.get("search_journal", []))
    workflow["review_cycles"] = _normalize_review_cycles(workflow.get("review_cycles", []))
    workflow["completion_gates"] = _normalize_completion_gates(workflow.get("completion_gates", {}))
    workflow["current_stage"] = _determine_current_stage(bundle)
    workflow["summary"] = _build_workflow_summary(bundle)
    workflow["next_actions"] = _build_next_actions(bundle)
    bundle["updated_at"] = timestamp_iso()
    return bundle


def validate_bundle(bundle: dict[str, Any]) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []

    for key in REQUIRED_BUNDLE_KEYS:
        if key not in bundle:
            errors.append(f"缺少 bundle 字段: {key}")

    if errors:
        return errors, warnings

    if bundle.get("bundle_version") != BUNDLE_VERSION:
        warnings.append(f"bundle_version={bundle.get('bundle_version')}，当前脚本期望 {BUNDLE_VERSION}")

    dossier_seed = bundle.get("dossier_seed")
    if not isinstance(dossier_seed, dict):
        errors.append("dossier_seed 必须是对象")
        return errors, warnings

    meta = dossier_seed.get("meta")
    if not isinstance(meta, dict):
        errors.append("dossier_seed.meta 必须是对象")
    else:
        for key in ["company_name", "ticker", "research_date"]:
            if not str(meta.get(key, "")).strip():
                errors.append(f"dossier_seed.meta.{key} 不能为空")

    module_outputs = bundle.get("module_outputs")
    if not isinstance(module_outputs, list):
        errors.append("module_outputs 必须是数组")
    else:
        for index, item in enumerate(module_outputs):
            if not isinstance(item, dict):
                errors.append(f"module_outputs[{index}] 必须是对象")
                continue
            for key in REQUIRED_MODULE_KEYS:
                if key not in item:
                    errors.append(f"缺少字段: module_outputs[{index}].{key}")
            if not isinstance(item.get("data", {}), dict):
                errors.append(f"module_outputs[{index}].data 必须是对象")
            for list_key in ["source_additions", "gaps", "conflicts"]:
                if not isinstance(item.get(list_key, []), list):
                    errors.append(f"module_outputs[{index}].{list_key} 必须是数组")
            for optional_key in ["raw_notes", "extracted_claims", "artifacts"]:
                if optional_key in item and not isinstance(item.get(optional_key), list):
                    errors.append(f"module_outputs[{index}].{optional_key} 必须是数组")

    research_assets = bundle.get("research_assets")
    if not isinstance(research_assets, dict):
        errors.append("research_assets 必须是对象")
    else:
        for key in RESEARCH_ASSET_KEYS:
            if not isinstance(research_assets.get(key, []), list):
                errors.append(f"research_assets.{key} 必须是数组")

    for index, item in enumerate(research_assets.get("query_records", []) if isinstance(research_assets, dict) else []):
        if not isinstance(item, dict):
            errors.append(f"research_assets.query_records[{index}] 必须是对象")
            continue
        for key in ["id", "timestamp", "query"]:
            if not str(item.get(key, "")).strip():
                errors.append(f"query_records[{index}] 缺少必填字段: {key}")

    known_query_ids = {
        str(item.get("id", "")).strip()
        for item in research_assets.get("query_records", [])
        if isinstance(research_assets, dict) and isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    known_source_ids = {
        str(item.get("id", "")).strip()
        for item in research_assets.get("source_records", [])
        if isinstance(research_assets, dict) and isinstance(item, dict) and str(item.get("id", "")).strip()
    }

    for index, item in enumerate(research_assets.get("result_records", []) if isinstance(research_assets, dict) else []):
        if not isinstance(item, dict):
            errors.append(f"research_assets.result_records[{index}] 必须是对象")
            continue
        for key in ["id", "query_id", "url", "title", "disposition"]:
            if not str(item.get(key, "")).strip():
                errors.append(f"result_records[{index}] 缺少必填字段: {key}")
        if str(item.get("query_id", "")).strip() and str(item.get("query_id", "")).strip() not in known_query_ids:
            warnings.append(f"result_records[{index}].query_id 引用了未知 query: {item.get('query_id', '')}")
        if item.get("disposition") not in ALLOWED_RESULT_DISPOSITIONS:
            errors.append(f"result_records[{index}].disposition 非法")

    for index, item in enumerate(research_assets.get("source_records", []) if isinstance(research_assets, dict) else []):
        if not isinstance(item, dict):
            errors.append(f"research_assets.source_records[{index}] 必须是对象")
            continue
        for key in ["id", "title", "url"]:
            if not str(item.get(key, "")).strip():
                errors.append(f"source_records[{index}] 缺少必填字段: {key}")
        stage = str(item.get("stage", "")).strip()
        if stage and stage not in ALLOWED_SOURCE_STAGES:
            errors.append(f"source_records[{index}].stage 非法")
        if stage == "promoted" and not str(item.get("kind", "")).strip():
            errors.append(f"source_records[{index}] 为 promoted 但缺少 kind")
        if str(item.get("query_id", "")).strip() and str(item.get("query_id", "")).strip() not in known_query_ids:
            warnings.append(f"source_records[{index}].query_id 引用了未知 query: {item.get('query_id', '')}")

    for index, item in enumerate(research_assets.get("extraction_records", []) if isinstance(research_assets, dict) else []):
        if not isinstance(item, dict):
            errors.append(f"research_assets.extraction_records[{index}] 必须是对象")
            continue
        for key in ["id", "source_id", "path"]:
            if not str(item.get(key, "")).strip():
                errors.append(f"extraction_records[{index}] 缺少必填字段: {key}")
        if str(item.get("source_id", "")).strip() and str(item.get("source_id", "")).strip() not in known_source_ids:
            warnings.append(f"extraction_records[{index}].source_id 引用了未知 source: {item.get('source_id', '')}")

    for key in ["claim_records", "note_records", "review_records", "artifact_records"]:
        for index, item in enumerate(research_assets.get(key, []) if isinstance(research_assets, dict) else []):
            if not isinstance(item, dict):
                errors.append(f"research_assets.{key}[{index}] 必须是对象")

    _validate_workflow(bundle, errors, warnings)

    if not bundle_has_activity(bundle):
        warnings.append("bundle 目前仍是空壳：只有目录与默认 todo，尚未真正开始研究。")
    elif not bundle_has_research_content(bundle):
        warnings.append("bundle 已有 workflow，但仍未落下搜索、review 或研究资产。")

    return errors, warnings


def append_research_assets(
    bundle: dict[str, Any],
    *,
    query_records: list[Any] | None = None,
    result_records: list[Any] | None = None,
    source_records: list[Any] | None = None,
    extraction_records: list[Any] | None = None,
    claim_records: list[Any] | None = None,
    note_records: list[Any] | None = None,
    review_records: list[Any] | None = None,
    artifact_records: list[Any] | None = None,
) -> dict[str, Any]:
    assets = bundle.setdefault("research_assets", {key: [] for key in RESEARCH_ASSET_KEYS})
    for key in RESEARCH_ASSET_KEYS:
        assets.setdefault(key, [])

    payload_map = {
        "query_records": list(query_records or []),
        "result_records": list(result_records or []),
        "source_records": list(source_records or []),
        "extraction_records": list(extraction_records or []),
        "claim_records": list(claim_records or []),
        "note_records": list(note_records or []),
        "review_records": list(review_records or []),
        "artifact_records": list(artifact_records or []),
    }
    for key, records in payload_map.items():
        assets[key] = merge_list_values(assets.get(key, []), records, ("research_assets", key))
    return refresh_bundle_state(bundle)


def upsert_todo_items(
    bundle: dict[str, Any],
    items: list[dict[str, Any]],
    *,
    replace_existing: bool = True,
) -> list[str]:
    workflow = bundle.setdefault("workflow", init_workflow())
    existing = [item for item in workflow.get("todo_items", []) if isinstance(item, dict)]
    seen_ids = {str(item.get("id", "")).strip() for item in existing}
    normalized_items: list[dict[str, Any]] = []

    for item in items:
        normalized = _normalize_todo_item(item)
        todo_id = str(normalized.get("id", "")).strip()
        if not todo_id:
            continue
        if replace_existing:
            existing = [row for row in existing if str(row.get("id", "")).strip() != todo_id]
        elif todo_id in seen_ids:
            continue
        normalized_items.append(normalized)
        seen_ids.add(todo_id)

    workflow["todo_items"] = existing + normalized_items
    refresh_bundle_state(bundle)
    return [str(item.get("id", "")).strip() for item in normalized_items]


def update_todo_items(
    bundle: dict[str, Any],
    *,
    status_updates: dict[str, str] | None = None,
    note_updates: dict[str, list[str]] | None = None,
) -> dict[str, Any]:
    workflow = bundle.setdefault("workflow", init_workflow())
    todo_items = workflow.get("todo_items", [])
    status_updates = status_updates or {}
    note_updates = note_updates or {}

    for item in todo_items:
        if not isinstance(item, dict):
            continue
        todo_id = str(item.get("id", "")).strip()
        if todo_id in status_updates:
            item["status"] = status_updates[todo_id]
            item["last_updated"] = timestamp_iso()
        if todo_id in note_updates:
            item["notes"] = merge_list_values(item.get("notes", []), note_updates[todo_id], ("workflow", "todo_items", "notes"))
            item["last_updated"] = timestamp_iso()
    return refresh_bundle_state(bundle)


def link_research_to_todo(
    bundle: dict[str, Any],
    *,
    todo_id: str = "",
    query_ids: list[str] | None = None,
    result_ids: list[str] | None = None,
    source_ids: list[str] | None = None,
    claim_ids: list[str] | None = None,
    artifact_ids: list[str] | None = None,
    search_id: str = "",
    review_id: str = "",
    note: str = "",
    promote_to_in_progress: bool = True,
) -> dict[str, Any]:
    if not todo_id:
        return refresh_bundle_state(bundle)

    workflow = bundle.setdefault("workflow", init_workflow())
    for item in workflow.get("todo_items", []):
        if not isinstance(item, dict) or str(item.get("id", "")).strip() != todo_id:
            continue
        if query_ids:
            item["related_query_ids"] = merge_list_values(item.get("related_query_ids", []), query_ids, ("workflow", "todo_items", "related_query_ids"))
        if result_ids:
            item["related_result_ids"] = merge_list_values(item.get("related_result_ids", []), result_ids, ("workflow", "todo_items", "related_result_ids"))
        if source_ids:
            item["related_source_ids"] = merge_list_values(item.get("related_source_ids", []), source_ids, ("workflow", "todo_items", "related_source_ids"))
        if claim_ids:
            item["related_claim_ids"] = merge_list_values(item.get("related_claim_ids", []), claim_ids, ("workflow", "todo_items", "related_claim_ids"))
        if artifact_ids:
            item["related_artifact_ids"] = merge_list_values(item.get("related_artifact_ids", []), artifact_ids, ("workflow", "todo_items", "related_artifact_ids"))
        if search_id:
            item["linked_search_ids"] = merge_list_values(item.get("linked_search_ids", []), [search_id], ("workflow", "todo_items", "linked_search_ids"))
        if review_id:
            item["linked_review_ids"] = merge_list_values(item.get("linked_review_ids", []), [review_id], ("workflow", "todo_items", "linked_review_ids"))
        if note:
            item["notes"] = merge_list_values(item.get("notes", []), [note], ("workflow", "todo_items", "notes"))
        if promote_to_in_progress and item.get("status") == "todo":
            item["status"] = "in_progress"
        item["last_updated"] = timestamp_iso()
        break
    return refresh_bundle_state(bundle)


def append_search_journal_entry(bundle: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    workflow = bundle.setdefault("workflow", init_workflow())
    normalized = _normalize_search_entry(entry, bundle=bundle)
    journal = [
        item
        for item in workflow.get("search_journal", [])
        if not (isinstance(item, dict) and str(item.get("id", "")).strip() == str(normalized.get("id", "")).strip())
    ]
    journal.append(normalized)
    workflow["search_journal"] = journal
    refresh_bundle_state(bundle)
    return normalized


def append_review_cycle(bundle: dict[str, Any], entry: dict[str, Any]) -> dict[str, Any]:
    workflow = bundle.setdefault("workflow", init_workflow())
    normalized = _normalize_review_cycle(entry)
    cycles = [
        item
        for item in workflow.get("review_cycles", [])
        if not (isinstance(item, dict) and str(item.get("id", "")).strip() == str(normalized.get("id", "")).strip())
    ]
    cycles.append(normalized)
    workflow["review_cycles"] = cycles
    append_research_assets(bundle, review_records=[normalized])
    return normalized


def merge_module_output(
    bundle: dict[str, Any],
    module_output: dict[str, Any],
    *,
    replace_existing: bool = True,
) -> dict[str, Any]:
    _validate_single_module_output(module_output)

    outputs = list(bundle.get("module_outputs", []))
    if replace_existing:
        outputs = [
            item
            for item in outputs
            if not (
                str(item.get("section", "")).strip() == str(module_output.get("section", "")).strip()
                and str(item.get("owner", "")).strip() == str(module_output.get("owner", "")).strip()
            )
        ]
    outputs.append(module_output)
    bundle["module_outputs"] = outputs

    owner = str(module_output.get("owner", "")).strip()
    module = str(module_output.get("section", "")).strip()
    promoted_sources = [
        _normalize_source_record(
            {
                **item,
                "owner": item.get("owner", owner),
                "module": item.get("module", module),
                "stage": item.get("stage", "promoted"),
                "value_tier": item.get("value_tier", "used_in_dossier"),
            }
        )
        for item in module_output.get("source_additions", [])
        if isinstance(item, dict)
    ]
    note_records = [
        _normalize_note_record({"owner": owner, "module": module, "note": str(item), "layer": "working", "value_tier": "useful"})
        for item in module_output.get("raw_notes", [])
        if str(item).strip()
    ]
    artifact_records = []
    for item in module_output.get("artifacts", []):
        if isinstance(item, dict):
            artifact = dict(item)
            artifact.setdefault("owner", owner)
            artifact.setdefault("module", module)
            artifact.setdefault("layer", artifact.get("layer", "working"))
            artifact_records.append(_normalize_artifact_record(artifact))
        else:
            artifact_records.append(_normalize_artifact_record({"owner": owner, "module": module, "path": str(item), "layer": "working"}))

    claim_records = [
        _normalize_claim_record({**item, "owner": item.get("owner", owner), "module": item.get("module", module), "value_tier": item.get("value_tier", "useful")})
        for item in module_output.get("extracted_claims", [])
        if isinstance(item, dict)
    ]

    append_research_assets(
        bundle,
        source_records=promoted_sources,
        claim_records=claim_records,
        note_records=note_records,
        artifact_records=artifact_records,
    )
    return refresh_bundle_state(bundle)


def assemble_dossier(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized_bundle = refresh_bundle_state(deepcopy(bundle))
    dossier = deep_merge({}, EMPTY_DOSSIER_TEMPLATE)
    dossier = deep_merge(dossier, normalized_bundle.get("dossier_seed", {}))

    all_gaps: list[str] = []
    all_conflicts: list[str] = []
    module_sources: list[Any] = []

    for item in normalized_bundle.get("module_outputs", []):
        if not isinstance(item, dict):
            continue
        dossier = deep_merge(dossier, item.get("data", {}))
        all_gaps.extend(str(entry).strip() for entry in item.get("gaps", []) if str(entry).strip())
        all_conflicts.extend(str(entry).strip() for entry in item.get("conflicts", []) if str(entry).strip())
        for source in item.get("source_additions", []):
            if not isinstance(source, dict):
                continue
            promoted = dict(source)
            promoted.setdefault("stage", "promoted")
            promoted.setdefault("value_tier", "used_in_dossier")
            module_sources.append(promoted)

    dossier_sources = collect_promoted_sources(normalized_bundle) + module_sources
    dossier.setdefault("sources", {}).setdefault("items", [])
    dossier["sources"]["items"] = merge_list_values(dossier["sources"]["items"], dossier_sources, ("sources", "items"))

    limitations = dossier.setdefault("report_method", {}).setdefault("limitations", [])
    if all_gaps:
        limitations = merge_list_values(limitations, [f"研究缺口：{item}" for item in all_gaps], ("report_method", "limitations"))
    if all_conflicts:
        limitations = merge_list_values(limitations, [f"待核冲突：{item}" for item in all_conflicts], ("report_method", "limitations"))
    dossier["report_method"]["limitations"] = limitations

    info_collected = dossier.setdefault("report_method", {}).setdefault("information_collected", [])
    info_collected = merge_list_values(
        info_collected,
        [
            f"搜索查询 {len(normalized_bundle.get('research_assets', {}).get('query_records', []))} 轮",
            f"候选结果 {len(normalized_bundle.get('research_assets', {}).get('result_records', []))} 条",
            f"原始来源 {len(normalized_bundle.get('research_assets', {}).get('source_records', []))} 条",
            f"提取文本 {len(normalized_bundle.get('research_assets', {}).get('extraction_records', []))} 条",
        ],
        ("report_method", "information_collected"),
    )
    dossier["report_method"]["information_collected"] = info_collected

    research_modules = dossier.setdefault("report_method", {}).setdefault("research_modules", [])
    research_modules = merge_list_values(research_modules, _completed_parent_module_titles(normalized_bundle), ("report_method", "research_modules"))
    dossier["report_method"]["research_modules"] = research_modules

    decision_steps = dossier.setdefault("report_method", {}).setdefault("decision_steps", [])
    decision_steps = merge_list_values(decision_steps, _decision_step_summaries(normalized_bundle), ("report_method", "decision_steps"))
    dossier["report_method"]["decision_steps"] = decision_steps

    dossier["research_process"] = assemble_research_process(normalized_bundle)
    return dossier


def assemble_research_process(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized_bundle = refresh_bundle_state(deepcopy(bundle))
    workflow = normalized_bundle.get("workflow", {})
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    todo_items = [item for item in workflow.get("todo_items", []) if isinstance(item, dict)]
    search_journal = [item for item in workflow.get("search_journal", []) if isinstance(item, dict)]
    review_cycles = [item for item in workflow.get("review_cycles", []) if isinstance(item, dict)]

    parent_todos = _parent_todos(todo_items)
    child_map = _question_children_map(todo_items)
    todo_summary = []
    for item in _sort_todos(parent_todos):
        todo_id = str(item.get("id", "")).strip()
        children = child_map.get(todo_id, [])
        done_children = len([child for child in children if child.get("status") in {"done", "dropped"}])
        total_children = len(children)
        useful_source_count = len(
            [
                record
                for record in normalized_bundle.get("research_assets", {}).get("source_records", [])
                if isinstance(record, dict)
                and str(record.get("module", "")).strip() == str(item.get("module", "")).strip()
                and str(record.get("value_tier", "candidate")).strip() in {"useful", "used_in_dossier"}
            ]
        )
        open_titles = [
            str(child.get("title", "")).strip()
            for child in _sort_open_todos(children)
            if str(child.get("title", "")).strip()
        ]
        if item.get("status") == "done":
            module_status = "已完成"
        elif item.get("status") == "blocked":
            module_status = "阻塞"
        elif item.get("status") == "in_progress":
            module_status = "进行中"
        else:
            module_status = "待处理"
        progress_text = f"{done_children}/{total_children}" if total_children else ("1/1" if item.get("status") == "done" else "0/1")
        todo_summary.append(
            {
                "module": str(item.get("module", "")).strip() or str(item.get("title", "")).strip(),
                "status": module_status,
                "progress": progress_text,
                "useful_source_count": useful_source_count,
                "summary": "；".join(open_titles[:3]) if open_titles else ("该模块当前没有未关闭的 question todo。" if children else "当前按父级 todo 推进。"),
            }
        )

    todo_title_index = {str(item.get("id", "")).strip(): str(item.get("title", "")).strip() for item in todo_items}
    search_cycles = []
    for item in search_journal[-8:]:
        result_ids = [value for value in item.get("result_ids", []) if str(value).strip()]
        search_cycles.append(
            {
                "query": str(item.get("query", "")).strip(),
                "intent": str(item.get("reason", "")).strip(),
                "outcome": str(item.get("outcome", "")).strip(),
                "decision": "；".join(str(value).strip() for value in item.get("next_actions", []) if str(value).strip()) or str(item.get("summary", "")).strip(),
                "todo_title": todo_title_index.get(str(item.get("todo_id", "")).strip(), ""),
                "timestamp": str(item.get("timestamp", "")).strip(),
                "candidate_result_count": len(result_ids),
            }
        )

    open_items = []
    for item in _sort_open_todos(todo_items)[:12]:
        open_items.append(
            {
                "title": str(item.get("title", "")).strip(),
                "module": str(item.get("module", "")).strip(),
                "priority": str(item.get("priority", "")).strip(),
                "status": str(item.get("status", "")).strip(),
            }
        )

    layer_counts = {
        key: len(normalized_bundle.get("research_assets", {}).get(key, []))
        for key in RESEARCH_ASSET_KEYS
    }
    compact_reviews = [
        {
            "timestamp": str(item.get("timestamp", "")).strip(),
            "decision": str(item.get("decision", "")).strip(),
            "next_actions": _normalize_string_list(item.get("next_actions", [])),
        }
        for item in review_cycles[-5:]
    ]
    workflow_summary = (
        f"这次研究采用 todo 驱动 + 全量过程落盘的闭环流程推进。当前阶段为 {workflow.get('current_stage', 'initialized')}，"
        f"累计记录 query {layer_counts['query_records']} 轮、候选结果 {layer_counts['result_records']} 条、review {layer_counts['review_records']} 次，"
        f"promoted 来源 {summary.get('promoted_source_count', 0)} 条。"
    )

    return {
        "workflow_summary": workflow_summary,
        "todo_summary": todo_summary,
        "search_cycles": search_cycles,
        "completion_reason": _build_completion_reason(normalized_bundle),
        "next_actions": list(workflow.get("next_actions", [])),
        "open_items": open_items,
        "current_stage": workflow.get("current_stage", "initialized"),
        "layer_counts": layer_counts,
        "review_cycles": compact_reviews,
    }


def collect_bundle_sources(bundle: dict[str, Any]) -> list[Any]:
    sources = []
    research_assets = bundle.get("research_assets", {})
    if isinstance(research_assets, dict):
        sources.extend(research_assets.get("source_records", []))
    for item in bundle.get("module_outputs", []):
        if isinstance(item, dict):
            sources.extend(item.get("source_additions", []))
    return sources


def collect_promoted_sources(bundle: dict[str, Any]) -> list[dict[str, Any]]:
    promoted = []
    for item in bundle.get("research_assets", {}).get("source_records", []):
        if not isinstance(item, dict):
            continue
        stage = str(item.get("stage", "candidate")).strip() or "candidate"
        value_tier = str(item.get("value_tier", "candidate")).strip() or "candidate"
        if stage == "promoted" or value_tier == "used_in_dossier":
            promoted.append(item)
    return promoted


def bundle_progress(bundle: dict[str, Any]) -> dict[str, Any]:
    normalized = refresh_bundle_state(deepcopy(bundle))
    research_assets = normalized.get("research_assets", {})
    workflow = normalized.get("workflow", {})
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    todo_counts = summary.get("todo_counts", {}) if isinstance(summary, dict) else {}
    parent_counts = summary.get("parent_todo_counts", {}) if isinstance(summary, dict) else {}

    return {
        "module_outputs": len(normalized.get("module_outputs", [])),
        "query_records": len(research_assets.get("query_records", [])),
        "result_records": len(research_assets.get("result_records", [])),
        "source_records": len(research_assets.get("source_records", [])),
        "extraction_records": len(research_assets.get("extraction_records", [])),
        "claim_records": len(research_assets.get("claim_records", [])),
        "note_records": len(research_assets.get("note_records", [])),
        "review_records": len(research_assets.get("review_records", [])),
        "artifact_records": len(research_assets.get("artifact_records", [])),
        "sources_total": len(collect_bundle_sources(normalized)),
        "search_journal": len(workflow.get("search_journal", [])) if isinstance(workflow, dict) else 0,
        "review_cycles": len(workflow.get("review_cycles", [])) if isinstance(workflow, dict) else 0,
        "todo_total": len(workflow.get("todo_items", [])) if isinstance(workflow, dict) else 0,
        "todo_done": int(todo_counts.get("done", 0)),
        "todo_in_progress": int(todo_counts.get("in_progress", 0)),
        "todo_blocked": int(todo_counts.get("blocked", 0)),
        "todo_todo": int(todo_counts.get("todo", 0)),
        "todo_dropped": int(todo_counts.get("dropped", 0)),
        "parent_todo_total": int(summary.get("parent_todo_total", 0)),
        "parent_todo_done": int(parent_counts.get("done", 0)),
        "question_todo_total": int(summary.get("question_todo_total", 0)),
        "open_p0_count": int(summary.get("open_p0_count", 0)),
        "open_p1_count": int(summary.get("open_p1_count", 0)),
        "completion_percent": int(summary.get("completion_percent", 0)),
        "useful_search_count": int(summary.get("useful_search_count", 0)),
        "promoted_source_count": int(summary.get("promoted_source_count", 0)),
        "current_stage": str(summary.get("current_stage", workflow.get("current_stage", "initialized"))).strip(),
        "research_started": bool(summary.get("research_started", False)),
        "foundation_ready": bool(summary.get("foundation_ready", False)),
        "module_ready": bool(summary.get("module_ready", False)),
        "report_ready": bool(summary.get("report_ready", False)),
        "focus_parent_todo": str(summary.get("focus_parent_todo", "")).strip(),
        "focus_question_todo": str(summary.get("focus_question_todo", "")).strip(),
    }


def bundle_has_progress(bundle: dict[str, Any]) -> bool:
    progress = bundle_progress(bundle)
    tracked_keys = [
        "query_records",
        "result_records",
        "review_cycles",
        "search_journal",
        "module_outputs",
        "source_records",
        "extraction_records",
        "claim_records",
        "note_records",
        "artifact_records",
    ]
    return any(progress.get(key, 0) > 0 for key in tracked_keys)


def bundle_has_activity(bundle: dict[str, Any]) -> bool:
    return bundle_has_progress(bundle)


def bundle_has_research_content(bundle: dict[str, Any]) -> bool:
    progress = bundle_progress(bundle)
    tracked_keys = [
        "query_records",
        "result_records",
        "review_cycles",
        "module_outputs",
        "source_records",
        "extraction_records",
        "claim_records",
        "note_records",
        "artifact_records",
    ]
    return any(progress.get(key, 0) > 0 for key in tracked_keys)


def bundle_has_active_todo(bundle: dict[str, Any]) -> bool:
    workflow = refresh_bundle_state(deepcopy(bundle)).get("workflow", {})
    todo_items = workflow.get("todo_items", []) if isinstance(workflow, dict) else []
    return any(
        isinstance(item, dict) and str(item.get("status", "")).strip() in {"todo", "in_progress", "blocked"}
        for item in todo_items
    )


def bundle_file_counts(bundle_dir: str | Path) -> dict[str, int]:
    root = Path(bundle_dir).expanduser()
    folder_map = {
        "search_queries": SEARCH_QUERY_SUBDIR,
        "search_results": SEARCH_RESULT_SUBDIR,
        "search_reviews": SEARCH_REVIEW_SUBDIR,
        "raw": Path("raw"),
        "extracted": Path("extracted"),
        "working": Path("working"),
        "promoted": Path("promoted"),
        "artifacts": Path("artifacts"),
    }
    counts: dict[str, int] = {}
    for key, relative in folder_map.items():
        folder = root / relative
        counts[key] = sum(1 for item in folder.rglob("*") if item.is_file()) if folder.exists() else 0
    return counts


def render_todo_markdown(bundle: dict[str, Any]) -> str:
    normalized = refresh_bundle_state(deepcopy(bundle))
    workflow = normalized.get("workflow", {})
    summary = workflow.get("summary", {})
    todo_items = [item for item in workflow.get("todo_items", []) if isinstance(item, dict)]
    search_journal = [item for item in workflow.get("search_journal", []) if isinstance(item, dict)]
    review_cycles = [item for item in workflow.get("review_cycles", []) if isinstance(item, dict)]
    meta = normalized.get("dossier_seed", {}).get("meta", {})
    parent_todos = _parent_todos(todo_items)
    question_todos = _question_todos(todo_items)

    lines = [
        f"# {meta.get('company_name', '研究任务')} TODO",
        "",
        f"- Ticker: {meta.get('ticker', 'N/A')}",
        f"- 研究日期: {meta.get('research_date', '')}",
        f"- 当前阶段: {workflow.get('current_stage', 'initialized')}",
        f"- 父级完成度: {summary.get('completion_percent', 0)}%",
        f"- 报告就绪: {'是' if summary.get('report_ready') else '否'}",
        f"- Query / Result / Review: {summary.get('query_count', 0)} / {summary.get('result_count', 0)} / {summary.get('review_count', 0)}",
        f"- Promoted Sources: {summary.get('promoted_source_count', 0)}",
        "",
        "## 下一步动作",
    ]

    next_actions = workflow.get("next_actions", []) if isinstance(workflow, dict) else []
    if next_actions:
        lines.extend(f"- {item}" for item in next_actions)
    else:
        lines.append("- 暂无建议动作。")

    lines.extend(["", "## 父级待办"])
    for status, title in [("in_progress", "进行中"), ("todo", "待开始"), ("blocked", "阻塞"), ("done", "已完成")]:
        lines.append(f"### {title}")
        items = [item for item in parent_todos if str(item.get("status", "")).strip() == status]
        if not items:
            lines.append("- 无")
            continue
        for item in _sort_todos(items):
            lines.append(f"- [{item.get('priority', 'P1')}] {item.get('title', '')} (`{item.get('module', '')}` / {item.get('stage', '')})")

    lines.extend(["", "## 问题待办（question todos）"])
    open_questions = _sort_open_todos(question_todos)
    if not open_questions:
        lines.append("- 当前没有未关闭的问题待办。")
    else:
        for item in open_questions[:12]:
            parent_id = str(item.get("parent_id", "")).strip()
            lines.append(f"- [{item.get('priority', 'P1')}] {item.get('title', '')} (`{item.get('module', '')}` / parent={parent_id or 'none'})")

    lines.extend(["", "## 最近搜索循环"])
    if not search_journal:
        lines.append("- 尚无搜索记录。")
    else:
        for item in reversed(search_journal[-5:]):
            query = str(item.get("query", "")).strip() or "未命名查询"
            outcome = str(item.get("outcome", "")).strip()
            summary_text = str(item.get("summary", "")).strip()
            lines.append(f"- {item.get('timestamp', '')} | {outcome} | {query}")
            if summary_text:
                lines.append(f"  - {summary_text}")

    lines.extend(["", "## 最近复盘"])
    if not review_cycles:
        lines.append("- 尚无 review 记录。")
    else:
        for item in reversed(review_cycles[-5:]):
            decision = str(item.get("decision", "")).strip() or "未记录决策"
            lines.append(f"- {item.get('timestamp', '')} | {decision}")
            for action in _normalize_string_list(item.get("next_actions", []))[:3]:
                lines.append(f"  - 下一步: {action}")

    lines.extend(["", "## 完成判定"])
    lines.append(f"- {_build_completion_reason(normalized)}")
    return "\n".join(lines).strip() + "\n"


def deep_merge(base: Any, patch: Any, path: tuple[str, ...] = ()) -> Any:
    if patch in (None, "", [], {}):
        return deepcopy(base)
    if base in (None, "", [], {}):
        return deepcopy(patch)

    if isinstance(base, dict) and isinstance(patch, dict):
        merged = deepcopy(base)
        for key, value in patch.items():
            merged[key] = deep_merge(merged.get(key), value, path + (key,))
        return merged

    if isinstance(base, list) and isinstance(patch, list):
        return merge_list_values(base, patch, path)

    return deepcopy(patch)


def merge_list_values(base: list[Any], patch: list[Any], path: tuple[str, ...]) -> list[Any]:
    merged = deepcopy(base)
    if not patch:
        return merged

    keyed_paths = {
        ("sources", "items"),
        ("workflow", "todo_items"),
        ("workflow", "search_journal"),
        ("workflow", "review_cycles"),
        *(("research_assets", key) for key in RESEARCH_ASSET_KEYS),
    }
    if path in keyed_paths:
        seen: set[str] = set()
        normalized: list[Any] = []
        for item in merged + patch:
            if not isinstance(item, dict):
                if item not in normalized:
                    normalized.append(deepcopy(item))
                continue
            key = str(item.get("id") or item.get("path") or item.get("saved_path") or item.get("note") or item.get("query") or "").strip()
            if key and key in seen:
                continue
            if key:
                seen.add(key)
            normalized.append(deepcopy(item))
        return normalized

    if all(isinstance(item, str) for item in merged + patch):
        seen_str: set[str] = set()
        normalized_strings: list[str] = []
        for item in merged + patch:
            text = str(item).strip()
            if not text or text in seen_str:
                continue
            seen_str.add(text)
            normalized_strings.append(text)
        return normalized_strings

    if all(isinstance(item, dict) and str(item.get("id", "")).strip() for item in merged + patch):
        seen_ids: set[str] = set()
        normalized_dicts: list[dict[str, Any]] = []
        for item in merged + patch:
            item_id = str(item.get("id", "")).strip()
            if item_id in seen_ids:
                continue
            seen_ids.add(item_id)
            normalized_dicts.append(deepcopy(item))
        return normalized_dicts

    return merged + deepcopy(patch)


def source_bucket_label(kind: str) -> str:
    mapping = {
        "annual-report": "财报与年报",
        "sec-filing": "监管与申报文件",
        "proxy": "监管与申报文件",
        "earnings-release": "财报与年报",
        "conference-call": "电话会与实录",
        "transcript": "电话会与实录",
        "investor-presentation": "投资者材料",
        "ir-page": "投资者材料",
        "interview": "管理层访谈与公开表态",
        "market-data": "市场与估值数据",
        "macro-official": "宏观与政策材料",
        "regulatory": "监管与申报文件",
        "filing": "监管与申报文件",
    }
    return mapping.get(str(kind).strip(), "其他公开资料")


def _normalize_research_assets(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}
    assets = {key: value.get(key, []) for key in RESEARCH_ASSET_KEYS}
    return {
        "query_records": _normalize_record_list(assets.get("query_records", []), _normalize_query_record),
        "result_records": _normalize_record_list(assets.get("result_records", []), _normalize_result_record),
        "source_records": _normalize_record_list(assets.get("source_records", []), _normalize_source_record),
        "extraction_records": _normalize_record_list(assets.get("extraction_records", []), _normalize_extraction_record),
        "claim_records": _normalize_record_list(assets.get("claim_records", []), _normalize_claim_record),
        "note_records": _normalize_record_list(assets.get("note_records", []), _normalize_note_record),
        "review_records": _normalize_record_list(assets.get("review_records", []), _normalize_review_record),
        "artifact_records": _normalize_record_list(assets.get("artifact_records", []), _normalize_artifact_record),
    }


def _normalize_record_list(value: Any, normalizer: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized: list[dict[str, Any]] = []
    seen_ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        record = normalizer(item)
        record_id = str(record.get("id", "")).strip() or str(record.get("path", "")).strip() or str(record.get("saved_path", "")).strip()
        if record_id and record_id in seen_ids:
            continue
        if record_id:
            seen_ids.add(record_id)
        normalized.append(record)
    return normalized


def _normalize_todo_items(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        value = DEFAULT_PARENT_TODO_BLUEPRINTS + DEFAULT_QUESTION_TODO_BLUEPRINTS
    normalized = []
    seen_ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        todo = _normalize_todo_item(item)
        todo_id = str(todo.get("id", "")).strip()
        if not todo_id or todo_id in seen_ids:
            continue
        seen_ids.add(todo_id)
        normalized.append(todo)
    return normalized


def _normalize_todo_item(item: dict[str, Any]) -> dict[str, Any]:
    module = str(item.get("module", "")).strip()
    parent_id = str(item.get("parent_id", "")).strip()
    level = str(item.get("level", "question" if parent_id else "parent")).strip() or ("question" if parent_id else "parent")
    stage = str(item.get("stage", _infer_todo_stage(module))).strip() or _infer_todo_stage(module)
    todo = {
        "id": str(item.get("id", "")).strip(),
        "parent_id": parent_id,
        "module": module,
        "title": str(item.get("title", "")).strip(),
        "kind": str(item.get("kind", "module-synthesis")).strip() or "module-synthesis",
        "level": level if level in ALLOWED_TODO_LEVELS else ("question" if parent_id else "parent"),
        "stage": stage if stage in ALLOWED_TODO_STAGES else _infer_todo_stage(module),
        "priority": str(item.get("priority", "P1")).strip() or "P1",
        "status": str(item.get("status", "todo")).strip() or "todo",
        "done_criteria": _normalize_string_list(item.get("done_criteria", [])),
        "depends_on": _normalize_string_list(item.get("depends_on", [])),
        "derived_from": str(item.get("derived_from", "")).strip(),
        "related_query_ids": _normalize_string_list(item.get("related_query_ids", [])),
        "related_result_ids": _normalize_string_list(item.get("related_result_ids", [])),
        "related_source_ids": _normalize_string_list(item.get("related_source_ids", [])),
        "related_claim_ids": _normalize_string_list(item.get("related_claim_ids", [])),
        "related_artifact_ids": _normalize_string_list(item.get("related_artifact_ids", [])),
        "linked_search_ids": _normalize_string_list(item.get("linked_search_ids", [])),
        "linked_review_ids": _normalize_string_list(item.get("linked_review_ids", [])),
        "notes": _normalize_string_list(item.get("notes", [])),
        "last_updated": str(item.get("last_updated", "")).strip() or timestamp_iso(),
    }
    return todo


def _normalize_search_journal(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized = []
    seen_ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        entry = _normalize_search_entry(item)
        entry_id = str(entry.get("id", "")).strip()
        if not entry_id or entry_id in seen_ids:
            continue
        seen_ids.add(entry_id)
        normalized.append(entry)
    return normalized


def _normalize_search_entry(item: dict[str, Any], *, bundle: dict[str, Any] | None = None) -> dict[str, Any]:
    timestamp = str(item.get("timestamp", "")).strip() or timestamp_iso()
    entry_id = str(item.get("id", "")).strip() or unique_id("search")
    entry = {
        "id": entry_id,
        "timestamp": timestamp,
        "module": str(item.get("module", "")).strip(),
        "todo_id": str(item.get("todo_id", "")).strip(),
        "query": str(item.get("query", "")).strip(),
        "reason": str(item.get("reason", "")).strip(),
        "based_on": str(item.get("based_on", "")).strip(),
        "outcome": str(item.get("outcome", "lead")).strip() or "lead",
        "captured_urls": _normalize_string_list(item.get("captured_urls", [])),
        "saved_paths": _normalize_string_list(item.get("saved_paths", [])),
        "promoted_source_ids": _normalize_string_list(item.get("promoted_source_ids", [])),
        "new_todo_ids": _normalize_string_list(item.get("new_todo_ids", [])),
        "next_actions": _normalize_string_list(item.get("next_actions", [])),
        "summary": str(item.get("summary", "")).strip(),
        "query_id": str(item.get("query_id", "")).strip(),
        "result_ids": _normalize_string_list(item.get("result_ids", [])),
        "review_id": str(item.get("review_id", "")).strip(),
    }
    if bundle is not None and not entry["query_id"]:
        query_records = bundle.get("research_assets", {}).get("query_records", [])
        if isinstance(query_records, list) and query_records:
            last_query = query_records[-1]
            if isinstance(last_query, dict):
                entry["query_id"] = str(last_query.get("id", "")).strip()
    return entry


def _normalize_review_cycles(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    normalized = []
    seen_ids: set[str] = set()
    for item in value:
        if not isinstance(item, dict):
            continue
        cycle = _normalize_review_cycle(item)
        cycle_id = str(cycle.get("id", "")).strip()
        if not cycle_id or cycle_id in seen_ids:
            continue
        seen_ids.add(cycle_id)
        normalized.append(cycle)
    return normalized


def _normalize_review_cycle(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip() or unique_id("review"),
        "timestamp": str(item.get("timestamp", "")).strip() or timestamp_iso(),
        "reviewed_query_ids": _normalize_string_list(item.get("reviewed_query_ids", [])),
        "reviewed_result_ids": _normalize_string_list(item.get("reviewed_result_ids", [])),
        "reviewed_todo_ids": _normalize_string_list(item.get("reviewed_todo_ids", [])),
        "basis": str(item.get("basis", "")).strip(),
        "findings": str(item.get("findings", "")).strip(),
        "decision": str(item.get("decision", "")).strip(),
        "spawned_todo_ids": _normalize_string_list(item.get("spawned_todo_ids", [])),
        "next_actions": _normalize_string_list(item.get("next_actions", [])),
        "stage_before": str(item.get("stage_before", "")).strip() or "initialized",
        "stage_after": str(item.get("stage_after", "")).strip() or "initialized",
        "owner": str(item.get("owner", "main-agent")).strip() or "main-agent",
        "saved_path": str(item.get("saved_path", "")).strip(),
    }


def _normalize_completion_gates(value: Any) -> dict[str, Any]:
    if not isinstance(value, dict):
        value = {}

    if any(key in value for key in ["required_modules", "minimum_source_buckets", "minimum_promoted_sources", "must_resolve_priorities"]):
        legacy_required = _normalize_string_list(value.get("required_modules", DEFAULT_REQUIRED_MODULES)) or list(DEFAULT_REQUIRED_MODULES)
        legacy_buckets = _normalize_string_list(value.get("minimum_source_buckets", DEFAULT_MINIMUM_SOURCE_BUCKETS)) or list(DEFAULT_MINIMUM_SOURCE_BUCKETS)
        legacy_min_sources = int(value.get("minimum_promoted_sources", 100) or 100)
        legacy_priorities = _normalize_string_list(value.get("must_resolve_priorities", ["P0"])) or ["P0"]
        value = {
            "research_started": {"minimum_queries": 1, "minimum_reviews": 1},
            "foundation_ready": {"required_parent_todos": ["todo-foundation-primary-sources"], "minimum_useful_searches": 1},
            "module_ready": {"required_modules": legacy_required, "must_resolve_priorities": legacy_priorities},
            "report_ready": {
                "required_modules": legacy_required,
                "minimum_source_buckets": legacy_buckets,
                "minimum_promoted_sources": legacy_min_sources,
                "must_resolve_priorities": legacy_priorities,
                "required_parent_todos": ["todo-dossier-assembly"],
            },
        }

    return {
        "research_started": {
            "minimum_queries": int(value.get("research_started", {}).get("minimum_queries", 1) or 1),
            "minimum_reviews": int(value.get("research_started", {}).get("minimum_reviews", 1) or 1),
        },
        "foundation_ready": {
            "required_parent_todos": _normalize_string_list(value.get("foundation_ready", {}).get("required_parent_todos", ["todo-foundation-primary-sources"])) or ["todo-foundation-primary-sources"],
            "minimum_useful_searches": int(value.get("foundation_ready", {}).get("minimum_useful_searches", 1) or 1),
        },
        "module_ready": {
            "required_modules": _normalize_string_list(value.get("module_ready", {}).get("required_modules", DEFAULT_REQUIRED_MODULES)) or list(DEFAULT_REQUIRED_MODULES),
            "must_resolve_priorities": _normalize_string_list(value.get("module_ready", {}).get("must_resolve_priorities", ["P0"])) or ["P0"],
        },
        "report_ready": {
            "required_modules": _normalize_string_list(value.get("report_ready", {}).get("required_modules", DEFAULT_REQUIRED_MODULES)) or list(DEFAULT_REQUIRED_MODULES),
            "minimum_source_buckets": _normalize_string_list(value.get("report_ready", {}).get("minimum_source_buckets", DEFAULT_MINIMUM_SOURCE_BUCKETS)) or list(DEFAULT_MINIMUM_SOURCE_BUCKETS),
            "minimum_promoted_sources": int(value.get("report_ready", {}).get("minimum_promoted_sources", 100) or 100),
            "must_resolve_priorities": _normalize_string_list(value.get("report_ready", {}).get("must_resolve_priorities", ["P0"])) or ["P0"],
            "required_parent_todos": _normalize_string_list(value.get("report_ready", {}).get("required_parent_todos", ["todo-dossier-assembly"])) or ["todo-dossier-assembly"],
        },
    }


def _normalize_query_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip() or unique_id("query"),
        "timestamp": str(item.get("timestamp", "")).strip() or timestamp_iso(),
        "module": str(item.get("module", "")).strip(),
        "todo_id": str(item.get("todo_id", "")).strip(),
        "query": str(item.get("query", "")).strip(),
        "reason": str(item.get("reason", "")).strip(),
        "based_on": str(item.get("based_on", "")).strip(),
        "executor": str(item.get("executor", item.get("owner", "main-agent"))).strip() or "main-agent",
        "outcome": str(item.get("outcome", "lead")).strip() or "lead",
        "saved_path": str(item.get("saved_path", "")).strip(),
    }


def _normalize_result_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip() or unique_id("result"),
        "query_id": str(item.get("query_id", "")).strip(),
        "url": str(item.get("url", "")).strip(),
        "title": str(item.get("title", "")).strip(),
        "snippet": str(item.get("snippet", "")).strip(),
        "rank": int(item.get("rank", 0) or 0),
        "disposition": str(item.get("disposition", "candidate")).strip() or "candidate",
        "source_kind": str(item.get("source_kind", item.get("kind", ""))).strip(),
        "note": str(item.get("note", "")).strip(),
        "timestamp": str(item.get("timestamp", "")).strip() or timestamp_iso(),
        "saved_path": str(item.get("saved_path", "")).strip(),
    }


def _normalize_source_record(item: dict[str, Any]) -> dict[str, Any]:
    stage = str(item.get("stage", "candidate")).strip() or "candidate"
    value_tier = str(item.get("value_tier", "candidate")).strip() or "candidate"
    if stage == "promoted":
        value_tier = "used_in_dossier"
    elif value_tier == "used_in_dossier" and stage != "promoted":
        stage = "promoted"
    return {
        "id": str(item.get("id", "")).strip() or unique_id("source"),
        "title": str(item.get("title", "")).strip(),
        "kind": str(item.get("kind", "")).strip(),
        "url": str(item.get("url", "")).strip(),
        "publisher": str(item.get("publisher", "")).strip(),
        "date": str(item.get("date", "")).strip(),
        "note": str(item.get("note", "")).strip(),
        "owner": str(item.get("owner", "main-agent")).strip() or "main-agent",
        "module": str(item.get("module", "")).strip(),
        "todo_ids": _normalize_string_list(item.get("todo_ids", [])),
        "search_id": str(item.get("search_id", "")).strip(),
        "query_id": str(item.get("query_id", "")).strip(),
        "result_id": str(item.get("result_id", "")).strip(),
        "extraction_id": str(item.get("extraction_id", "")).strip(),
        "artifact_ids": _normalize_string_list(item.get("artifact_ids", [])),
        "stage": stage if stage in ALLOWED_SOURCE_STAGES else "candidate",
        "value_tier": value_tier if value_tier in ALLOWED_VALUE_TIERS else "candidate",
        "path": str(item.get("path", "")).strip(),
        "last_updated": str(item.get("last_updated", "")).strip() or timestamp_iso(),
    }


def _normalize_extraction_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip() or unique_id("extract"),
        "source_id": str(item.get("source_id", "")).strip(),
        "artifact_id": str(item.get("artifact_id", "")).strip(),
        "path": str(item.get("path", "")).strip(),
        "method": str(item.get("method", "")).strip(),
        "note": str(item.get("note", "")).strip(),
        "owner": str(item.get("owner", "main-agent")).strip() or "main-agent",
        "module": str(item.get("module", "")).strip(),
        "value_tier": str(item.get("value_tier", "useful")).strip() or "useful",
        "last_updated": str(item.get("last_updated", "")).strip() or timestamp_iso(),
    }


def _normalize_claim_record(item: dict[str, Any]) -> dict[str, Any]:
    claim = dict(item)
    claim.setdefault("id", str(item.get("id", "")).strip() or unique_id("claim"))
    claim["id"] = str(claim.get("id", "")).strip() or unique_id("claim")
    claim["owner"] = str(claim.get("owner", "main-agent")).strip() or "main-agent"
    claim["module"] = str(claim.get("module", "")).strip()
    claim["todo_ids"] = _normalize_string_list(claim.get("todo_ids", []))
    claim["search_id"] = str(claim.get("search_id", "")).strip()
    claim["query_id"] = str(claim.get("query_id", "")).strip()
    claim["result_id"] = str(claim.get("result_id", "")).strip()
    claim["value_tier"] = str(claim.get("value_tier", "useful")).strip() or "useful"
    claim["last_updated"] = str(claim.get("last_updated", "")).strip() or timestamp_iso()
    return claim


def _normalize_note_record(item: dict[str, Any]) -> dict[str, Any]:
    note = str(item.get("note", "")).strip()
    return {
        "id": str(item.get("id", "")).strip() or unique_id("note"),
        "owner": str(item.get("owner", "main-agent")).strip() or "main-agent",
        "module": str(item.get("module", "")).strip(),
        "todo_ids": _normalize_string_list(item.get("todo_ids", [])),
        "search_id": str(item.get("search_id", "")).strip(),
        "query_id": str(item.get("query_id", "")).strip(),
        "result_id": str(item.get("result_id", "")).strip(),
        "note": note,
        "source_path": str(item.get("source_path", "")).strip(),
        "layer": str(item.get("layer", "working")).strip() or "working",
        "value_tier": str(item.get("value_tier", "useful")).strip() or "useful",
        "last_updated": str(item.get("last_updated", "")).strip() or timestamp_iso(),
    }


def _normalize_review_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip() or unique_id("review-record"),
        "timestamp": str(item.get("timestamp", "")).strip() or timestamp_iso(),
        "reviewed_query_ids": _normalize_string_list(item.get("reviewed_query_ids", [])),
        "reviewed_result_ids": _normalize_string_list(item.get("reviewed_result_ids", [])),
        "reviewed_todo_ids": _normalize_string_list(item.get("reviewed_todo_ids", [])),
        "basis": str(item.get("basis", "")).strip(),
        "findings": str(item.get("findings", "")).strip(),
        "decision": str(item.get("decision", "")).strip(),
        "spawned_todo_ids": _normalize_string_list(item.get("spawned_todo_ids", [])),
        "next_actions": _normalize_string_list(item.get("next_actions", [])),
        "stage_before": str(item.get("stage_before", "")).strip() or "initialized",
        "stage_after": str(item.get("stage_after", "")).strip() or "initialized",
        "owner": str(item.get("owner", "main-agent")).strip() or "main-agent",
        "saved_path": str(item.get("saved_path", "")).strip(),
    }


def _normalize_artifact_record(item: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(item.get("id", "")).strip() or unique_id("artifact"),
        "owner": str(item.get("owner", "main-agent")).strip() or "main-agent",
        "module": str(item.get("module", "")).strip(),
        "path": str(item.get("path", "")).strip(),
        "kind": str(item.get("kind", "artifact-file")).strip() or "artifact-file",
        "title": str(item.get("title", "")).strip(),
        "note": str(item.get("note", "")).strip(),
        "todo_ids": _normalize_string_list(item.get("todo_ids", [])),
        "search_id": str(item.get("search_id", "")).strip(),
        "query_id": str(item.get("query_id", "")).strip(),
        "result_id": str(item.get("result_id", "")).strip(),
        "source_id": str(item.get("source_id", "")).strip(),
        "layer": str(item.get("layer", "working")).strip() or "working",
        "value_tier": str(item.get("value_tier", "useful")).strip() or "useful",
        "last_updated": str(item.get("last_updated", "")).strip() or timestamp_iso(),
    }


def _normalize_string_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def _validate_workflow(bundle: dict[str, Any], errors: list[str], warnings: list[str]) -> None:
    workflow = bundle.get("workflow")
    if not isinstance(workflow, dict):
        errors.append("workflow 必须是对象")
        return

    for key in REQUIRED_WORKFLOW_KEYS:
        if key not in workflow:
            errors.append(f"缺少 workflow 字段: {key}")

    todo_items = workflow.get("todo_items")
    if not isinstance(todo_items, list):
        errors.append("workflow.todo_items 必须是数组")
        todo_items = []

    todo_ids: set[str] = set()
    for index, item in enumerate(todo_items):
        if not isinstance(item, dict):
            errors.append(f"workflow.todo_items[{index}] 必须是对象")
            continue
        for key in [
            "id",
            "parent_id",
            "module",
            "title",
            "kind",
            "level",
            "stage",
            "priority",
            "status",
            "done_criteria",
            "depends_on",
            "derived_from",
            "related_query_ids",
            "related_result_ids",
            "related_source_ids",
            "related_claim_ids",
            "related_artifact_ids",
            "linked_search_ids",
            "linked_review_ids",
            "notes",
            "last_updated",
        ]:
            if key not in item:
                errors.append(f"缺少字段: workflow.todo_items[{index}].{key}")
        todo_id = str(item.get("id", "")).strip()
        if todo_id:
            if todo_id in todo_ids:
                errors.append(f"workflow.todo_items 存在重复 id: {todo_id}")
            todo_ids.add(todo_id)
        if item.get("kind") not in ALLOWED_TODO_KINDS:
            errors.append(f"workflow.todo_items[{index}].kind 非法")
        if item.get("level") not in ALLOWED_TODO_LEVELS:
            errors.append(f"workflow.todo_items[{index}].level 非法")
        if item.get("stage") not in ALLOWED_TODO_STAGES:
            errors.append(f"workflow.todo_items[{index}].stage 非法")
        if item.get("priority") not in ALLOWED_TODO_PRIORITIES:
            errors.append(f"workflow.todo_items[{index}].priority 非法")
        if item.get("status") not in ALLOWED_TODO_STATUSES:
            errors.append(f"workflow.todo_items[{index}].status 非法")
        for key in [
            "done_criteria",
            "depends_on",
            "related_query_ids",
            "related_result_ids",
            "related_source_ids",
            "related_claim_ids",
            "related_artifact_ids",
            "linked_search_ids",
            "linked_review_ids",
            "notes",
        ]:
            if not isinstance(item.get(key, []), list):
                errors.append(f"workflow.todo_items[{index}].{key} 必须是数组")

    for index, item in enumerate(todo_items):
        if not isinstance(item, dict):
            continue
        parent_id = str(item.get("parent_id", "")).strip()
        if parent_id and parent_id not in todo_ids:
            warnings.append(f"workflow.todo_items[{index}].parent_id 引用了未知 todo: {parent_id}")
        for dep_id in item.get("depends_on", []) or []:
            if dep_id not in todo_ids:
                warnings.append(f"workflow.todo_items[{index}].depends_on 引用了未知 todo: {dep_id}")

    search_journal = workflow.get("search_journal")
    if not isinstance(search_journal, list):
        errors.append("workflow.search_journal 必须是数组")
        search_journal = []
    for index, item in enumerate(search_journal):
        if not isinstance(item, dict):
            errors.append(f"workflow.search_journal[{index}] 必须是对象")
            continue
        for key in [
            "id",
            "timestamp",
            "module",
            "todo_id",
            "query",
            "reason",
            "based_on",
            "outcome",
            "captured_urls",
            "saved_paths",
            "promoted_source_ids",
            "new_todo_ids",
            "next_actions",
            "summary",
            "query_id",
            "result_ids",
            "review_id",
        ]:
            if key not in item:
                errors.append(f"缺少字段: workflow.search_journal[{index}].{key}")
        if item.get("outcome") not in ALLOWED_SEARCH_OUTCOMES:
            errors.append(f"workflow.search_journal[{index}].outcome 非法")
        if str(item.get("todo_id", "")).strip() and str(item.get("todo_id", "")).strip() not in todo_ids:
            warnings.append(f"workflow.search_journal[{index}].todo_id 引用了未知 todo: {item.get('todo_id', '')}")
        for key in ["captured_urls", "saved_paths", "promoted_source_ids", "new_todo_ids", "next_actions", "result_ids"]:
            if not isinstance(item.get(key, []), list):
                errors.append(f"workflow.search_journal[{index}].{key} 必须是数组")

    review_cycles = workflow.get("review_cycles")
    if not isinstance(review_cycles, list):
        errors.append("workflow.review_cycles 必须是数组")
        review_cycles = []
    for index, item in enumerate(review_cycles):
        if not isinstance(item, dict):
            errors.append(f"workflow.review_cycles[{index}] 必须是对象")
            continue
        for key in [
            "id",
            "timestamp",
            "reviewed_query_ids",
            "reviewed_result_ids",
            "reviewed_todo_ids",
            "basis",
            "findings",
            "decision",
            "spawned_todo_ids",
            "next_actions",
            "stage_before",
            "stage_after",
            "owner",
            "saved_path",
        ]:
            if key not in item:
                errors.append(f"缺少字段: workflow.review_cycles[{index}].{key}")
        for key in ["reviewed_query_ids", "reviewed_result_ids", "reviewed_todo_ids", "spawned_todo_ids", "next_actions"]:
            if not isinstance(item.get(key, []), list):
                errors.append(f"workflow.review_cycles[{index}].{key} 必须是数组")

    current_stage = str(workflow.get("current_stage", "")).strip()
    if current_stage and current_stage not in ALLOWED_STAGES:
        errors.append("workflow.current_stage 非法")

    completion_gates = workflow.get("completion_gates")
    if not isinstance(completion_gates, dict):
        errors.append("workflow.completion_gates 必须是对象")
    else:
        for gate in ["research_started", "foundation_ready", "module_ready", "report_ready"]:
            if gate not in completion_gates:
                errors.append(f"缺少字段: workflow.completion_gates.{gate}")
            elif not isinstance(completion_gates.get(gate), dict):
                errors.append(f"workflow.completion_gates.{gate} 必须是对象")

    if not isinstance(workflow.get("next_actions", []), list):
        errors.append("workflow.next_actions 必须是数组")
    if not isinstance(workflow.get("summary", {}), dict):
        errors.append("workflow.summary 必须是对象")


def _build_workflow_summary(bundle: dict[str, Any]) -> dict[str, Any]:
    workflow = bundle.get("workflow", {})
    research_assets = bundle.get("research_assets", {})
    todo_items = [item for item in workflow.get("todo_items", []) if isinstance(item, dict)]
    search_journal = [item for item in workflow.get("search_journal", []) if isinstance(item, dict)]
    review_cycles = [item for item in workflow.get("review_cycles", []) if isinstance(item, dict)]
    parent_todos = _parent_todos(todo_items)
    question_todos = _question_todos(todo_items)

    todo_counts = {status: 0 for status in ALLOWED_TODO_STATUSES}
    parent_counts = {status: 0 for status in ALLOWED_TODO_STATUSES}
    for item in todo_items:
        status = str(item.get("status", "")).strip()
        if status in todo_counts:
            todo_counts[status] += 1
    for item in parent_todos:
        status = str(item.get("status", "")).strip()
        if status in parent_counts:
            parent_counts[status] += 1

    useful_entries = [item for item in search_journal if str(item.get("outcome", "")).strip() in USEFUL_SEARCH_OUTCOMES]
    last_useful = useful_entries[-1].get("timestamp", "") if useful_entries else ""
    open_p0 = len([item for item in todo_items if item.get("priority") == "P0" and item.get("status") not in {"done", "dropped"}])
    open_p1 = len([item for item in todo_items if item.get("priority") == "P1" and item.get("status") not in {"done", "dropped"}])
    parent_total = len(parent_todos)
    parent_done = len([item for item in parent_todos if item.get("status") == "done"])

    focus_parent = _sort_open_todos(parent_todos)
    focus_question = _sort_open_todos(question_todos)
    promoted_sources = collect_promoted_sources(bundle)
    stage_flags = {
        "research_started": _is_research_started(bundle),
        "foundation_ready": _is_foundation_ready(bundle),
        "module_ready": _is_module_ready(bundle),
        "report_ready": _is_report_ready(bundle),
    }

    return {
        "completion_percent": round(parent_done * 100 / parent_total) if parent_total else 0,
        "todo_counts": todo_counts,
        "parent_todo_counts": parent_counts,
        "parent_todo_total": parent_total,
        "question_todo_total": len(question_todos),
        "open_p0_count": open_p0,
        "open_p1_count": open_p1,
        "last_useful_search_at": str(last_useful).strip(),
        "query_count": len(research_assets.get("query_records", [])),
        "result_count": len(research_assets.get("result_records", [])),
        "review_count": len(review_cycles),
        "search_count": len(search_journal),
        "useful_search_count": len(useful_entries),
        "promoted_source_count": len(promoted_sources),
        "current_stage": _determine_current_stage(bundle),
        "research_started": stage_flags["research_started"],
        "foundation_ready": stage_flags["foundation_ready"],
        "module_ready": stage_flags["module_ready"],
        "report_ready": stage_flags["report_ready"],
        "focus_parent_todo": str(focus_parent[0].get("title", "")).strip() if focus_parent else "",
        "focus_question_todo": str(focus_question[0].get("title", "")).strip() if focus_question else "",
    }


def _build_next_actions(bundle: dict[str, Any]) -> list[str]:
    workflow = bundle.get("workflow", {})
    todo_items = [item for item in workflow.get("todo_items", []) if isinstance(item, dict)]
    question_todos = _sort_open_todos(_question_todos(todo_items))
    parent_todos = _sort_open_todos(_parent_todos(todo_items))
    actions: list[str] = []

    if not bundle.get("research_assets", {}).get("query_records", []):
        actions.append("先选择一个 P0 question todo，开始第一轮搜索，并使用 record_search_round.py 记录 query 与候选结果。")
    if not workflow.get("review_cycles", []):
        actions.append("第一轮搜索后立刻运行 review_research_progress.py，记录复盘结论并更新 todo。")

    for item in question_todos[:3]:
        title = str(item.get("title", "")).strip()
        module = str(item.get("module", "")).strip()
        priority = str(item.get("priority", "")).strip()
        if title:
            actions.append(f"[{priority}] 继续推进问题待办：{title}（{module}）")

    if len(actions) < 6:
        for item in parent_todos[: max(0, 6 - len(actions))]:
            title = str(item.get("title", "")).strip()
            module = str(item.get("module", "")).strip()
            priority = str(item.get("priority", "")).strip()
            if title:
                actions.append(f"[{priority}] 继续推进父级待办：{title}（{module}）")

    if not actions:
        actions.append("当前必需待办已基本完成，可进入 dossier 组装、校验与页面核验。")
    return merge_list_values([], actions, ("workflow", "next_actions"))


def _sort_open_todos(todo_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    open_items = [item for item in todo_items if item.get("status") not in {"done", "dropped"}]
    return _sort_todos(open_items)


def _sort_todos(todo_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    priority_rank = {"P0": 0, "P1": 1, "P2": 2}
    level_rank = {"question": 0, "parent": 1}
    status_rank = {"in_progress": 0, "blocked": 1, "todo": 2, "done": 3, "dropped": 4}
    return sorted(
        todo_items,
        key=lambda item: (
            priority_rank.get(str(item.get("priority", "P2")).strip(), 9),
            level_rank.get(str(item.get("level", "parent")).strip(), 9),
            status_rank.get(str(item.get("status", "todo")).strip(), 9),
            str(item.get("title", "")).strip(),
        ),
    )


def _determine_current_stage(bundle: dict[str, Any]) -> str:
    if _is_report_ready(bundle):
        return "report_ready"
    if _is_module_ready(bundle):
        return "module_ready"
    if _is_foundation_ready(bundle):
        return "foundation_ready"
    if _is_research_started(bundle):
        return "research_started"
    return "initialized"


def _is_research_started(bundle: dict[str, Any]) -> bool:
    workflow = bundle.get("workflow", {})
    research_assets = bundle.get("research_assets", {})
    gates = workflow.get("completion_gates", {}).get("research_started", {}) if isinstance(workflow, dict) else {}
    minimum_queries = int(gates.get("minimum_queries", 1) or 1)
    minimum_reviews = int(gates.get("minimum_reviews", 1) or 1)
    return (
        len(research_assets.get("query_records", [])) >= minimum_queries
        and len(workflow.get("review_cycles", [])) >= minimum_reviews
        and (len(research_assets.get("result_records", [])) > 0 or len(workflow.get("search_journal", [])) > 0)
    )


def _is_foundation_ready(bundle: dict[str, Any]) -> bool:
    if not _is_research_started(bundle):
        return False
    workflow = bundle.get("workflow", {})
    gates = workflow.get("completion_gates", {}).get("foundation_ready", {}) if isinstance(workflow, dict) else {}
    required_parent_todos = set(_normalize_string_list(gates.get("required_parent_todos", [])))
    useful_searches = len(
        [item for item in workflow.get("search_journal", []) if isinstance(item, dict) and str(item.get("outcome", "")).strip() in USEFUL_SEARCH_OUTCOMES]
    )
    minimum_useful_searches = int(gates.get("minimum_useful_searches", 1) or 1)
    done_parent_ids = {
        str(item.get("id", "")).strip()
        for item in _parent_todos([row for row in workflow.get("todo_items", []) if isinstance(row, dict)])
        if item.get("status") == "done"
    }
    return required_parent_todos.issubset(done_parent_ids) and useful_searches >= minimum_useful_searches


def _is_module_ready(bundle: dict[str, Any]) -> bool:
    workflow = bundle.get("workflow", {})
    gates = workflow.get("completion_gates", {}).get("module_ready", {}) if isinstance(workflow, dict) else {}
    required_modules = set(_normalize_string_list(gates.get("required_modules", DEFAULT_REQUIRED_MODULES)))
    must_resolve_priorities = _normalize_string_list(gates.get("must_resolve_priorities", ["P0"])) or ["P0"]
    parent_todos = _parent_todos([item for item in workflow.get("todo_items", []) if isinstance(item, dict)])
    done_modules = {str(item.get("module", "")).strip() for item in parent_todos if item.get("status") == "done"}
    if required_modules and not required_modules.issubset(done_modules):
        return False
    for priority in must_resolve_priorities:
        unresolved = [item for item in workflow.get("todo_items", []) if isinstance(item, dict) and item.get("priority") == priority and item.get("status") not in {"done", "dropped"}]
        if unresolved:
            return False
    return True


def _is_report_ready(bundle: dict[str, Any]) -> bool:
    if not _is_module_ready(bundle):
        return False
    workflow = bundle.get("workflow", {})
    gates = workflow.get("completion_gates", {}).get("report_ready", {}) if isinstance(workflow, dict) else {}
    required_parent_todos = set(_normalize_string_list(gates.get("required_parent_todos", [])))
    done_parent_ids = {
        str(item.get("id", "")).strip()
        for item in _parent_todos([row for row in workflow.get("todo_items", []) if isinstance(row, dict)])
        if item.get("status") == "done"
    }
    if required_parent_todos and not required_parent_todos.issubset(done_parent_ids):
        return False

    promoted_sources = collect_promoted_sources(bundle)
    if len(promoted_sources) < int(gates.get("minimum_promoted_sources", 0) or 0):
        return False

    covered_buckets = {source_bucket_label(str(item.get("kind", "")).strip()) for item in promoted_sources if isinstance(item, dict)}
    minimum_buckets = set(_normalize_string_list(gates.get("minimum_source_buckets", [])))
    if minimum_buckets and not minimum_buckets.issubset(covered_buckets):
        return False

    for priority in _normalize_string_list(gates.get("must_resolve_priorities", [])):
        unresolved = [
            item
            for item in workflow.get("todo_items", [])
            if isinstance(item, dict) and item.get("priority") == priority and item.get("status") not in {"done", "dropped"}
        ]
        if unresolved:
            return False
    return True


def _build_completion_reason(bundle: dict[str, Any]) -> str:
    workflow = bundle.get("workflow", {})
    summary = workflow.get("summary", {}) if isinstance(workflow, dict) else {}
    stage = workflow.get("current_stage", "initialized")
    if summary.get("report_ready"):
        return "研究已完成分阶段门槛：父级模块完成、P0 待办清零、promoted 来源达到完整报告阈值，且组装/渲染待办已关闭。"
    if stage == "initialized":
        return "当前还停留在初始化阶段：请先记录至少一轮 query/result，并完成第一次 review。"
    if stage == "research_started":
        return "研究已经启动，但 foundation gate 还未通过：请先补齐基础来源池，并关闭 research-foundation 父级待办。"
    if stage == "foundation_ready":
        return "基础来源池已建立，但核心模块仍未完成，且仍存在 P0 待办未关闭。"
    if stage == "module_ready":
        promoted = summary.get("promoted_source_count", 0)
        target = workflow.get("completion_gates", {}).get("report_ready", {}).get("minimum_promoted_sources", 100)
        return f"核心模块已完成，但完整报告门槛尚未满足：当前 promoted sources 为 {promoted}，目标 {target}，且 final assembly 待办尚未完成。"
    return "研究仍在推进，建议继续按 next_actions 搜索、落盘并复盘。"


def _validate_single_module_output(module_output: dict[str, Any]) -> None:
    missing = [key for key in REQUIRED_MODULE_KEYS if key not in module_output]
    if missing:
        raise ValueError(f"模块输出缺少字段: {', '.join(missing)}")
    if not isinstance(module_output.get("data"), dict):
        raise ValueError("模块输出的 data 必须是对象")
    for key in ["source_additions", "gaps", "conflicts"]:
        if not isinstance(module_output.get(key), list):
            raise ValueError(f"模块输出的 {key} 必须是数组")


def _infer_todo_stage(module: str) -> str:
    if module in {"research-foundation", "foundation", "source-foundation"}:
        return "foundation"
    if module in {"final-assembly", "dossier-assembly"}:
        return "assembly"
    if module in {"source-coverage-pass", "gap-close", "gap-followup"}:
        return "gap_close"
    return "module"


def _parent_todos(todo_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in todo_items if str(item.get("level", "parent")).strip() == "parent"]


def _question_todos(todo_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [item for item in todo_items if str(item.get("level", "parent")).strip() == "question"]


def _question_children_map(todo_items: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
    mapping: dict[str, list[dict[str, Any]]] = {}
    for item in _question_todos(todo_items):
        parent_id = str(item.get("parent_id", "")).strip()
        if not parent_id:
            continue
        mapping.setdefault(parent_id, []).append(item)
    return mapping


def _completed_parent_module_titles(bundle: dict[str, Any]) -> list[str]:
    workflow = bundle.get("workflow", {})
    return [
        str(item.get("title", "")).strip()
        for item in _parent_todos([row for row in workflow.get("todo_items", []) if isinstance(row, dict)])
        if item.get("status") == "done" and str(item.get("title", "")).strip()
    ]


def _decision_step_summaries(bundle: dict[str, Any]) -> list[str]:
    workflow = bundle.get("workflow", {})
    summaries = []
    for item in workflow.get("review_cycles", []):
        if not isinstance(item, dict):
            continue
        decision = str(item.get("decision", "")).strip()
        timestamp = str(item.get("timestamp", "")).strip()
        if not decision:
            continue
        text = f"{timestamp}：{decision}" if timestamp else decision
        summaries.append(text)
    return summaries
