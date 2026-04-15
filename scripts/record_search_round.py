#!/usr/bin/env python3
"""记录一次搜索轮次：query、候选结果快照与 search_journal。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bundle_schema import (
    ALLOWED_TODO_STAGES,
    SEARCH_QUERY_SUBDIR,
    SEARCH_RESULT_SUBDIR,
    append_research_assets,
    append_search_journal_entry,
    bundle_dir_from_input,
    bundle_path_from_input,
    bundle_progress,
    link_research_to_todo,
    load_bundle,
    save_bundle,
    unique_id,
)


STAGE_ORDER = ["foundation", "module", "gap_close", "assembly"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="记录一次搜索 query、候选结果与搜索日志。")
    parser.add_argument("--bundle", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument(
        "--mode",
        choices=["start", "complete"],
        default="complete",
        help="start=搜索前先预落盘，complete=搜索后补齐结果；默认 complete",
    )
    parser.add_argument("--owner", default="main-agent", help="执行搜索的 agent")
    parser.add_argument("--module", default="", help="当前搜索所属模块")
    parser.add_argument("--todo-id", action="append", default=[], help="关联的 todo id，可重复传入")
    parser.add_argument("--stage", choices=sorted(ALLOWED_TODO_STAGES), help="强制指定研究阶段；默认从 todo 推断")
    parser.add_argument("--query-id", default="", help="已有 query id；用于把 start 和 complete 串起来")
    parser.add_argument("--search-id", default="", help="已有 search id；用于更新同一轮搜索日志")
    parser.add_argument("--query", default="", help="搜索 query；补完已有搜索时可省略并从已有记录继承")
    parser.add_argument("--reason", default="", help="为什么做这次搜索")
    parser.add_argument("--based-on", default="", help="这次搜索基于哪些已有材料、缺口或 review 决策")
    parser.add_argument(
        "--outcome",
        choices=["pending", "no_hit", "duplicate", "lead", "evidence", "counterevidence"],
        default="",
        help="本轮搜索 outcome；start 默认 pending，complete 默认 lead",
    )
    parser.add_argument("--result-json", action="append", default=[], help="候选结果 JSON 文件；可为单对象或对象数组")
    parser.add_argument("--result-url", action="append", default=[], help="单条候选结果 URL，可重复传入")
    parser.add_argument("--result-title", action="append", default=[], help="单条候选结果标题，可重复传入")
    parser.add_argument("--result-snippet", action="append", default=[], help="单条候选结果摘要，可重复传入")
    parser.add_argument("--result-note", action="append", default=[], help="单条候选结果备注，可重复传入")
    parser.add_argument(
        "--result-disposition",
        action="append",
        default=[],
        help="单条候选结果 disposition，可重复传入；缺省为 candidate",
    )
    parser.add_argument("--result-source-kind", action="append", default=[], help="单条候选结果 source_kind，可重复传入")
    parser.add_argument("--captured-url", action="append", default=[], help="额外记录的捕获 URL，可重复传入")
    parser.add_argument("--next-action", action="append", default=[], help="本轮搜索后的建议下一步，可重复传入")
    parser.add_argument("--result-summary", default="", help="本轮搜索的简要总结")
    return parser.parse_args()


def load_json_records(path_str: str) -> list[dict[str, Any]]:
    path = Path(path_str).expanduser()
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    raise ValueError(f"{path} 必须是 JSON 对象或对象数组")


def normalize_todo_ids(values: list[str]) -> list[str]:
    return [str(item).strip() for item in values if str(item).strip()]


def unique_preserving_order(values: list[str]) -> list[str]:
    return list(dict.fromkeys(str(item).strip() for item in values if str(item).strip()))


def infer_stage(bundle: dict[str, Any], explicit_stage: str, todo_ids: list[str], module: str) -> str:
    if explicit_stage:
        return explicit_stage
    workflow = bundle.get("workflow", {}) if isinstance(bundle.get("workflow"), dict) else {}
    todo_items = workflow.get("todo_items", []) if isinstance(workflow, dict) else []
    todo_index = {
        str(item.get("id", "")).strip(): item
        for item in todo_items
        if isinstance(item, dict) and str(item.get("id", "")).strip()
    }
    for todo_id in todo_ids:
        item = todo_index.get(todo_id)
        if item and str(item.get("stage", "")).strip() in ALLOWED_TODO_STAGES:
            return str(item.get("stage", "")).strip()
    module_stage_map = {
        "research-foundation": "foundation",
        "source-coverage-pass": "gap_close",
        "final-assembly": "assembly",
    }
    if module in module_stage_map:
        return module_stage_map[module]
    return "module" if module else "foundation"


def pad(values: list[str], size: int) -> list[str]:
    if size <= 0:
        return []
    if not values:
        return [""] * size
    if len(values) >= size:
        return values[:size]
    return values + [values[-1]] * (size - len(values))


def build_inline_results(args: argparse.Namespace) -> list[dict[str, Any]]:
    urls = [str(item).strip() for item in args.result_url if str(item).strip()]
    if not urls:
        return []
    titles = pad([str(item).strip() for item in args.result_title], len(urls))
    snippets = pad([str(item).strip() for item in args.result_snippet], len(urls))
    notes = pad([str(item).strip() for item in args.result_note], len(urls))
    dispositions = pad([str(item).strip() for item in args.result_disposition], len(urls))
    source_kinds = pad([str(item).strip() for item in args.result_source_kind], len(urls))
    results = []
    for index, url in enumerate(urls, start=1):
        results.append(
            {
                "url": url,
                "title": titles[index - 1] or url,
                "snippet": snippets[index - 1],
                "rank": index,
                "disposition": dispositions[index - 1] or "candidate",
                "source_kind": source_kinds[index - 1],
                "note": notes[index - 1],
            }
        )
    return results


def load_results(args: argparse.Namespace) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for path_str in args.result_json:
        results.extend(load_json_records(path_str))
    results.extend(build_inline_results(args))
    return results


def find_query_record(bundle: dict[str, Any], query_id: str) -> dict[str, Any] | None:
    query_id = str(query_id).strip()
    if not query_id:
        return None
    assets = bundle.get("research_assets", {})
    records = assets.get("query_records", []) if isinstance(assets, dict) else []
    for item in records:
        if isinstance(item, dict) and str(item.get("id", "")).strip() == query_id:
            return item
    return None


def find_search_entry(bundle: dict[str, Any], *, search_id: str = "", query_id: str = "") -> dict[str, Any] | None:
    workflow = bundle.get("workflow", {})
    journal = workflow.get("search_journal", []) if isinstance(workflow, dict) else []
    for item in journal:
        if not isinstance(item, dict):
            continue
        if search_id and str(item.get("id", "")).strip() == search_id:
            return item
        if query_id and str(item.get("query_id", "")).strip() == query_id:
            return item
    return None


def inherited_value(*values: Any) -> str:
    for value in values:
        text = str(value or "").strip()
        if text:
            return text
    return ""


def resolve_todo_ids(
    explicit_todo_ids: list[str],
    existing_query: dict[str, Any] | None,
    existing_search: dict[str, Any] | None,
) -> list[str]:
    if explicit_todo_ids:
        return unique_preserving_order(explicit_todo_ids)
    inherited = [
        str((existing_query or {}).get("todo_id", "")).strip(),
        str((existing_search or {}).get("todo_id", "")).strip(),
    ]
    return unique_preserving_order([item for item in inherited if item])


def resolve_outcome(args: argparse.Namespace, existing_search: dict[str, Any] | None) -> str:
    explicit = str(args.outcome or "").strip()
    if explicit:
        return explicit
    if args.mode == "start":
        return "pending"
    inherited = str((existing_search or {}).get("outcome", "")).strip()
    if inherited and inherited != "pending":
        return inherited
    return "lead"


def reset_query_records(bundle: dict[str, Any], query_id: str) -> None:
    assets = bundle.setdefault("research_assets", {})
    query_records = assets.get("query_records", []) if isinstance(assets, dict) else []
    result_records = assets.get("result_records", []) if isinstance(assets, dict) else []
    if isinstance(query_records, list):
        assets["query_records"] = [
            item
            for item in query_records
            if not (isinstance(item, dict) and str(item.get("id", "")).strip() == query_id)
        ]
    if isinstance(result_records, list):
        assets["result_records"] = [
            item
            for item in result_records
            if not (isinstance(item, dict) and str(item.get("query_id", "")).strip() == query_id)
        ]


def annotate_results(
    results: list[dict[str, Any]],
    *,
    query_id: str,
    stage: str,
    owner: str,
    module: str,
    todo_ids: list[str],
    results_snapshot_relpath: str,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for index, item in enumerate(results, start=1):
        record = dict(item)
        record.setdefault("id", unique_id("result"))
        record["query_id"] = query_id
        record.setdefault("rank", index)
        record.setdefault("disposition", "candidate")
        record.setdefault("timestamp", item.get("timestamp", ""))
        record.setdefault("saved_path", results_snapshot_relpath)
        record.setdefault("note", "")
        record.setdefault("module", module)
        record.setdefault("owner", owner)
        record.setdefault("stage", stage)
        record.setdefault("todo_ids", todo_ids)
        annotated.append(record)
    return annotated


def save_snapshots(
    bundle_dir: Path,
    *,
    stage: str,
    query_record: dict[str, Any],
    result_records: list[dict[str, Any]],
    todo_ids: list[str],
    owner: str,
    module: str,
) -> tuple[str, str]:
    query_relpath = (SEARCH_QUERY_SUBDIR / stage / f"{query_record['id']}.json").as_posix()
    result_relpath = (SEARCH_RESULT_SUBDIR / stage / f"{query_record['id']}.json").as_posix()

    query_snapshot = {
        "query_record": query_record,
        "owner": owner,
        "module": module,
        "stage": stage,
        "todo_ids": todo_ids,
    }
    result_snapshot = {
        "query_id": query_record["id"],
        "query": query_record["query"],
        "owner": owner,
        "module": module,
        "stage": stage,
        "todo_ids": todo_ids,
        "results": result_records,
    }

    query_path = bundle_dir / query_relpath
    result_path = bundle_dir / result_relpath
    query_path.parent.mkdir(parents=True, exist_ok=True)
    result_path.parent.mkdir(parents=True, exist_ok=True)
    query_path.write_text(json.dumps(query_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    result_path.write_text(json.dumps(result_snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return query_relpath, result_relpath


def count_unreviewed_search_tail(bundle: dict[str, Any]) -> int:
    workflow = bundle.get("workflow", {})
    if not isinstance(workflow, dict):
        return 0
    count = 0
    for item in reversed(workflow.get("search_journal", [])):
        if not isinstance(item, dict):
            continue
        if str(item.get("review_id", "")).strip():
            break
        if str(item.get("outcome", "")).strip() == "pending":
            continue
        count += 1
    return count


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.bundle).expanduser())
    bundle_dir = bundle_dir_from_input(bundle_path)

    try:
        bundle = load_bundle(bundle_path)
        explicit_query_id = str(args.query_id or "").strip()
        explicit_search_id = str(args.search_id or "").strip()
        existing_search = find_search_entry(bundle, search_id=explicit_search_id, query_id=explicit_query_id)
        inherited_query_id = explicit_query_id or str((existing_search or {}).get("query_id", "")).strip()
        existing_query = find_query_record(bundle, inherited_query_id)
        query_id = inherited_query_id or str((existing_query or {}).get("id", "")).strip() or unique_id("query")
        search_id_hint = explicit_search_id or str((existing_search or {}).get("id", "")).strip()
        todo_ids = resolve_todo_ids(normalize_todo_ids(args.todo_id), existing_query, existing_search)
        module = inherited_value(args.module, (existing_query or {}).get("module"), (existing_search or {}).get("module"))
        stage = infer_stage(bundle, args.stage or "", todo_ids, module)
        query_text = inherited_value(args.query, (existing_query or {}).get("query"), (existing_search or {}).get("query"))
        if not query_text:
            raise ValueError("缺少 --query，且无法从 query_id/search_id 继承已有 query")
        reason = inherited_value(args.reason, (existing_query or {}).get("reason"), (existing_search or {}).get("reason"))
        based_on = inherited_value(args.based_on, (existing_query or {}).get("based_on"), (existing_search or {}).get("based_on"))
        outcome = resolve_outcome(args, existing_search)
        raw_results = [] if args.mode == "start" else load_results(args)
        start_timestamp = inherited_value((existing_query or {}).get("timestamp"), (existing_search or {}).get("timestamp"))
        provisional_query_record = {
            "id": query_id,
            "timestamp": start_timestamp,
            "module": module,
            "todo_id": todo_ids[0] if todo_ids else "",
            "query": query_text,
            "reason": reason,
            "based_on": based_on,
            "executor": args.owner,
            "outcome": outcome,
        }
        provisional_result_relpath = (SEARCH_RESULT_SUBDIR / stage / f"{query_id}.json").as_posix()
        result_records = annotate_results(
            raw_results,
            query_id=query_id,
            stage=stage,
            owner=args.owner,
            module=module,
            todo_ids=todo_ids,
            results_snapshot_relpath=provisional_result_relpath,
        )
        query_record = {
            **provisional_query_record,
            "saved_path": (SEARCH_QUERY_SUBDIR / stage / f"{query_id}.json").as_posix(),
        }
        _, result_relpath = save_snapshots(
            bundle_dir,
            stage=stage,
            query_record=query_record,
            result_records=result_records,
            todo_ids=todo_ids,
            owner=args.owner,
            module=module,
        )
        result_ids = [str(item.get("id", "")).strip() for item in result_records if str(item.get("id", "")).strip()]
        captured_urls = unique_preserving_order(
            [
                *[str(value).strip() for value in (existing_search or {}).get("captured_urls", []) if str(value).strip()],
                *[str(item).strip() for item in args.captured_url if str(item).strip()],
                *[
                    str(item.get("url", "")).strip()
                    for item in result_records
                    if isinstance(item, dict) and str(item.get("url", "")).strip()
                ],
            ]
        )
        next_actions = unique_preserving_order(
            [
                *[str(value).strip() for value in (existing_search or {}).get("next_actions", []) if str(value).strip()],
                *[str(item).strip() for item in args.next_action if str(item).strip()],
            ]
        )
        result_summary = inherited_value(args.result_summary, (existing_search or {}).get("summary"))

        reset_query_records(bundle, query_id)
        append_research_assets(bundle, query_records=[query_record], result_records=result_records)
        search_entry = append_search_journal_entry(
            bundle,
            {
                "id": search_id_hint,
                "timestamp": start_timestamp,
                "module": module,
                "todo_id": todo_ids[0] if todo_ids else "",
                "query": query_text,
                "reason": reason,
                "based_on": based_on,
                "outcome": outcome,
                "captured_urls": captured_urls,
                "saved_paths": [query_record["saved_path"], result_relpath],
                "summary": result_summary,
                "next_actions": next_actions,
                "query_id": query_id,
                "result_ids": result_ids,
            },
        )
        search_id = str(search_entry.get("id", "")).strip()
        link_kwargs = {
            "todo_id": "",
            "query_ids": [query_id],
            "result_ids": result_ids,
            "search_id": search_id,
            "note": result_summary,
            "promote_to_in_progress": True,
        }
        if args.mode == "start":
            link_kwargs["result_ids"] = []
            if not result_summary:
                link_kwargs["note"] = ""

        for todo_id in todo_ids:
            link_research_to_todo(
                bundle,
                **{**link_kwargs, "todo_id": todo_id},
            )
        save_bundle(bundle, bundle_path)
        progress = bundle_progress(bundle)
        unreviewed_tail = count_unreviewed_search_tail(bundle)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法记录搜索轮次: {exc}")
        return 1

    print(f"[完成] bundle: {bundle_path}")
    print(f"[模式] {args.mode}")
    print(f"[查询] {query_id} -> {query_record['saved_path']}")
    print(f"[结果] {len(result_records)} 条 -> {result_relpath}")
    if search_id:
        print(f"[搜索日志] {search_id}")
    if todo_ids:
        print(f"[关联 todo] {', '.join(todo_ids)}")
    print(
        f"[累计] stage={progress['current_stage']} queries={progress['query_records']} results={progress['result_records']} "
        f"searches={progress['search_journal']} reviews={progress['review_cycles']}"
    )
    if args.mode == "start":
        print("提示：这次搜索已经先落盘；拿到结果后请立刻用同一个 --query-id/--search-id 执行 --mode complete。")
    if unreviewed_tail >= 3:
        print(
            f"[警告] 已连续记录 {unreviewed_tail} 轮未复盘搜索；"
            "建议立即运行 review_research_progress.py，并写入 checkpoint，避免上下文持续膨胀导致卡住。"
        )
    return 0


if __name__ == "__main__":
    sys.exit(main())
