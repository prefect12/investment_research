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
    parser.add_argument("--owner", default="main-agent", help="执行搜索的 agent")
    parser.add_argument("--module", default="", help="当前搜索所属模块")
    parser.add_argument("--todo-id", action="append", default=[], help="关联的 todo id，可重复传入")
    parser.add_argument("--stage", choices=sorted(ALLOWED_TODO_STAGES), help="强制指定研究阶段；默认从 todo 推断")
    parser.add_argument("--query", required=True, help="搜索 query")
    parser.add_argument("--reason", default="", help="为什么做这次搜索")
    parser.add_argument("--based-on", default="", help="这次搜索基于哪些已有材料、缺口或 review 决策")
    parser.add_argument(
        "--outcome",
        choices=["no_hit", "duplicate", "lead", "evidence", "counterevidence"],
        default="lead",
        help="本轮搜索暂时得到的 outcome",
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


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.bundle).expanduser())
    bundle_dir = bundle_dir_from_input(bundle_path)

    try:
        bundle = load_bundle(bundle_path)
        todo_ids = normalize_todo_ids(args.todo_id)
        stage = infer_stage(bundle, args.stage or "", todo_ids, args.module)
        raw_results = load_results(args)
        query_id = unique_id("query")
        provisional_query_record = {
            "id": query_id,
            "module": args.module,
            "todo_id": todo_ids[0] if todo_ids else "",
            "query": args.query,
            "reason": args.reason,
            "based_on": args.based_on,
            "executor": args.owner,
            "outcome": args.outcome,
        }
        provisional_result_relpath = (SEARCH_RESULT_SUBDIR / stage / f"{query_id}.json").as_posix()
        result_records = annotate_results(
            raw_results,
            query_id=query_id,
            stage=stage,
            owner=args.owner,
            module=args.module,
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
            module=args.module,
        )
        result_ids = [str(item.get("id", "")).strip() for item in result_records if str(item.get("id", "")).strip()]
        captured_urls = [str(item).strip() for item in args.captured_url if str(item).strip()]
        captured_urls.extend(
            str(item.get("url", "")).strip()
            for item in result_records
            if isinstance(item, dict) and str(item.get("url", "")).strip()
        )
        captured_urls = list(dict.fromkeys(captured_urls))

        append_research_assets(bundle, query_records=[query_record], result_records=result_records)
        search_entry = append_search_journal_entry(
            bundle,
            {
                "module": args.module,
                "todo_id": todo_ids[0] if todo_ids else "",
                "query": args.query,
                "reason": args.reason,
                "based_on": args.based_on,
                "outcome": args.outcome,
                "captured_urls": captured_urls,
                "saved_paths": [query_record["saved_path"], result_relpath],
                "summary": args.result_summary,
                "next_actions": args.next_action,
                "query_id": query_id,
                "result_ids": result_ids,
            },
        )
        search_id = str(search_entry.get("id", "")).strip()
        for todo_id in todo_ids:
            link_research_to_todo(
                bundle,
                todo_id=todo_id,
                query_ids=[query_id],
                result_ids=result_ids,
                search_id=search_id,
                note=args.result_summary,
                promote_to_in_progress=True,
            )
        save_bundle(bundle, bundle_path)
        progress = bundle_progress(bundle)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法记录搜索轮次: {exc}")
        return 1

    print(f"[完成] bundle: {bundle_path}")
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
    return 0


if __name__ == "__main__":
    sys.exit(main())
