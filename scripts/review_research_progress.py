#!/usr/bin/env python3
"""记录一次研究复盘，并持续更新 todo / search_journal / review 归档。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bundle_schema import (
    ALLOWED_TODO_STAGES,
    SEARCH_REVIEW_SUBDIR,
    append_non_blocking_open_questions,
    append_review_cycle,
    bundle_dir_from_input,
    bundle_path_from_input,
    bundle_progress,
    link_research_to_todo,
    load_bundle,
    save_bundle,
    unique_id,
    update_todo_items,
    upsert_todo_items,
    write_bundle_checkpoint,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="记录研究复盘，并更新 todo 与搜索方向。")
    parser.add_argument("--bundle", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument("--owner", default="main-agent", help="执行复盘的 agent")
    parser.add_argument("--stage", choices=sorted(ALLOWED_TODO_STAGES), help="强制指定 review 所属阶段")
    parser.add_argument("--todo-id", action="append", default=[], help="本次 review 主要检视的 todo id，可重复传入")
    parser.add_argument("--query-id", action="append", default=[], help="本次 review 检视的 query id，可重复传入")
    parser.add_argument("--result-id", action="append", default=[], help="本次 review 检视的 result id，可重复传入")
    parser.add_argument("--basis", default="", help="本轮复盘基于哪些已有材料、搜索结果或缺口")
    parser.add_argument("--findings", default="", help="本轮复盘发现了什么")
    parser.add_argument("--decision", default="", help="本轮复盘的方向决策")
    parser.add_argument("--next-action", action="append", default=[], help="复盘后决定的下一步动作，可重复传入")
    parser.add_argument("--new-todo-json", action="append", default=[], help="新派生 todo 的 JSON 文件；可为单对象或数组")
    parser.add_argument("--open-question-json", action="append", default=[], help="转为 non-blocking open question 的 JSON 文件；可为单对象或数组")
    parser.add_argument("--set-status", action="append", default=[], help="按 todo_id=status 更新状态，可重复传入")
    parser.add_argument("--append-note", action="append", default=[], help="按 todo_id=note 追加笔记，可重复传入")
    parser.add_argument("--no-checkpoint", action="store_true", help="本次 review 完成后不自动写入 checkpoint")
    return parser.parse_args()


def normalize_strings(values: list[str]) -> list[str]:
    return [str(item).strip() for item in values if str(item).strip()]


def parse_status_pairs(values: list[str]) -> dict[str, str]:
    parsed: dict[str, str] = {}
    for item in values:
        key, sep, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        if not sep or not key or not value:
            raise ValueError("set-status 参数格式必须是 todo_id=status")
        parsed[key] = value
    return parsed


def parse_note_pairs(values: list[str]) -> dict[str, list[str]]:
    parsed: dict[str, list[str]] = {}
    for item in values:
        key, sep, value = item.partition("=")
        key = key.strip()
        value = value.strip()
        if not sep or not key or not value:
            raise ValueError("append-note 参数格式必须是 todo_id=note")
        parsed.setdefault(key, []).append(value)
    return parsed


def load_object_items(path_str: str, *, label: str) -> list[dict[str, Any]]:
    path = Path(path_str).expanduser()
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    raise ValueError(f"{path} 必须是 {label} JSON 对象或对象数组")


def load_todo_items(path_str: str) -> list[dict[str, Any]]:
    return load_object_items(path_str, label="todo")


def load_open_question_items(path_str: str) -> list[dict[str, Any]]:
    return load_object_items(path_str, label="open question")


def infer_stage(
    bundle: dict[str, Any],
    explicit_stage: str,
    todo_ids: list[str],
    new_todos: list[dict[str, Any]],
    open_questions: list[dict[str, Any]],
) -> str:
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
    for item in new_todos:
        stage = str(item.get("stage", "")).strip()
        if stage in ALLOWED_TODO_STAGES:
            return stage
    for item in open_questions:
        todo_item = todo_index.get(str(item.get("from_todo_id", "")).strip())
        if todo_item and str(todo_item.get("stage", "")).strip() in ALLOWED_TODO_STAGES:
            return str(todo_item.get("stage", "")).strip()
    current_stage = str(workflow.get("current_stage", "")).strip()
    if current_stage in {"initialized", "research_started", "foundation_ready"}:
        return "foundation"
    if current_stage == "module_ready":
        return "module"
    if current_stage == "report_ready":
        return "assembly"
    return "module"


def decorate_new_todos(new_todos: list[dict[str, Any]], review_id: str, stage: str) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for item in new_todos:
        todo = dict(item)
        todo.setdefault("derived_from", review_id)
        todo.setdefault("stage", stage)
        if todo.get("parent_id") and not todo.get("level"):
            todo["level"] = "question"
        decorated.append(todo)
    return decorated


def decorate_open_questions(open_questions: list[dict[str, Any]], review_id: str) -> list[dict[str, Any]]:
    decorated: list[dict[str, Any]] = []
    for item in open_questions:
        question = dict(item)
        question.setdefault("linked_review_id", review_id)
        decorated.append(question)
    return decorated


def save_review_snapshot(
    bundle_dir: Path,
    *,
    review_id: str,
    stage: str,
    payload: dict[str, Any],
) -> str:
    relpath = (SEARCH_REVIEW_SUBDIR / stage / f"{review_id}.json").as_posix()
    path = bundle_dir / relpath
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return relpath


def attach_review_to_search_journal(bundle: dict[str, Any], review_id: str, query_ids: set[str], result_ids: set[str]) -> None:
    workflow = bundle.get("workflow", {})
    if not isinstance(workflow, dict):
        return
    for item in workflow.get("search_journal", []):
        if not isinstance(item, dict):
            continue
        journal_query_id = str(item.get("query_id", "")).strip()
        journal_result_ids = {str(value).strip() for value in item.get("result_ids", []) if str(value).strip()}
        if (journal_query_id and journal_query_id in query_ids) or (result_ids and journal_result_ids.intersection(result_ids)):
            item["review_id"] = review_id


def sync_review_record(bundle: dict[str, Any], review_id: str, *, stage_after: str, saved_path: str) -> None:
    workflow = bundle.get("workflow", {})
    if isinstance(workflow, dict):
        for item in workflow.get("review_cycles", []):
            if isinstance(item, dict) and str(item.get("id", "")).strip() == review_id:
                item["stage_after"] = stage_after
                item["saved_path"] = saved_path
                break
    assets = bundle.get("research_assets", {})
    if isinstance(assets, dict):
        for item in assets.get("review_records", []):
            if isinstance(item, dict) and str(item.get("id", "")).strip() == review_id:
                item["stage_after"] = stage_after
                item["saved_path"] = saved_path
                break


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.bundle).expanduser())
    bundle_dir = bundle_dir_from_input(bundle_path)
    checkpoint_info: dict[str, str] | None = None
    checkpoint_warning = ""

    try:
        bundle = load_bundle(bundle_path)
        reviewed_todo_ids = normalize_strings(args.todo_id)
        reviewed_query_ids = normalize_strings(args.query_id)
        reviewed_result_ids = normalize_strings(args.result_id)
        if not any(
            [
                reviewed_todo_ids,
                reviewed_query_ids,
                reviewed_result_ids,
                str(args.basis).strip(),
                str(args.findings).strip(),
                str(args.decision).strip(),
                args.next_action,
                args.new_todo_json,
                args.open_question_json,
                args.set_status,
                args.append_note,
            ]
        ):
            raise ValueError("没有提供任何复盘内容或变更")

        review_id = unique_id("review")
        raw_new_todos: list[dict[str, Any]] = []
        for path_str in args.new_todo_json:
            raw_new_todos.extend(load_todo_items(path_str))
        raw_open_questions: list[dict[str, Any]] = []
        for path_str in args.open_question_json:
            raw_open_questions.extend(load_open_question_items(path_str))
        stage = infer_stage(bundle, args.stage or "", reviewed_todo_ids, raw_new_todos, raw_open_questions)
        new_todos = decorate_new_todos(raw_new_todos, review_id, stage)
        open_questions = decorate_open_questions(raw_open_questions, review_id)

        progress_before = bundle_progress(bundle)
        status_updates = parse_status_pairs(args.set_status)
        note_updates = parse_note_pairs(args.append_note)
        for item in open_questions:
            from_todo_id = str(item.get("from_todo_id", "")).strip()
            text = str(item.get("text", "")).strip()
            if not from_todo_id:
                continue
            status_updates.setdefault(from_todo_id, "dropped")
            if text:
                note_updates.setdefault(from_todo_id, []).append(f"在 {review_id} 中转为 non-blocking open question：{text}")

        created_todo_ids = upsert_todo_items(bundle, new_todos) if new_todos else []
        if status_updates or note_updates:
            update_todo_items(bundle, status_updates=status_updates, note_updates=note_updates)
        created_open_question_ids = append_non_blocking_open_questions(bundle, open_questions) if open_questions else []

        review_entry = append_review_cycle(
            bundle,
            {
                "id": review_id,
                "reviewed_query_ids": reviewed_query_ids,
                "reviewed_result_ids": reviewed_result_ids,
                "reviewed_todo_ids": reviewed_todo_ids,
                "basis": args.basis,
                "findings": args.findings,
                "decision": args.decision,
                "spawned_todo_ids": created_todo_ids,
                "next_actions": args.next_action,
                "stage_before": progress_before["current_stage"],
                "stage_after": progress_before["current_stage"],
                "owner": args.owner,
            },
        )

        attach_review_to_search_journal(bundle, review_id, set(reviewed_query_ids), set(reviewed_result_ids))
        note_text = args.decision or args.findings or args.basis
        for todo_id in reviewed_todo_ids:
            link_research_to_todo(
                bundle,
                todo_id=todo_id,
                review_id=review_id,
                note=note_text,
                promote_to_in_progress=False,
            )

        progress_after = bundle_progress(bundle)
        review_snapshot = {
            "review_cycle": {
                **review_entry,
                "stage_after": progress_after["current_stage"],
            },
            "owner": args.owner,
            "stage": stage,
            "reviewed_query_ids": reviewed_query_ids,
            "reviewed_result_ids": reviewed_result_ids,
            "reviewed_todo_ids": reviewed_todo_ids,
            "created_todo_ids": created_todo_ids,
            "created_open_question_ids": created_open_question_ids,
            "status_updates": status_updates,
            "note_updates": note_updates,
            "open_questions": open_questions,
        }
        saved_path = save_review_snapshot(bundle_dir, review_id=review_id, stage=stage, payload=review_snapshot)
        sync_review_record(bundle, review_id, stage_after=progress_after["current_stage"], saved_path=saved_path)

        save_bundle(bundle, bundle_path)
        if not args.no_checkpoint:
            try:
                checkpoint_info = write_bundle_checkpoint(
                    bundle,
                    bundle_path,
                    stage=stage,
                    label="review-checkpoint",
                    owner=args.owner,
                )
                save_bundle(bundle, bundle_path)
            except Exception as checkpoint_exc:  # noqa: BLE001
                checkpoint_warning = str(checkpoint_exc)
        final_progress = bundle_progress(bundle)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法记录研究复盘: {exc}")
        return 1

    print(f"[完成] bundle: {bundle_path}")
    print(f"[review] {review_id} -> {saved_path}")
    if created_todo_ids:
        print(f"[新增 todo] {', '.join(created_todo_ids)}")
    if created_open_question_ids:
        print(f"[新增开放问题] {', '.join(created_open_question_ids)}")
    if reviewed_todo_ids:
        print(f"[已关联 todo] {', '.join(reviewed_todo_ids)}")
    if checkpoint_info:
        print(f"[checkpoint] {checkpoint_info['latest_markdown']}")
    elif checkpoint_warning:
        print(f"[警告] checkpoint 写入失败: {checkpoint_warning}")
    print(
        f"[累计] stage={final_progress['current_stage']} reviews={final_progress['review_cycles']} "
        f"todos={final_progress['todo_total']} done={final_progress['todo_done']} "
        f"in_progress={final_progress['todo_in_progress']} open_questions={final_progress['non_blocking_open_question_count']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
