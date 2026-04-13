#!/usr/bin/env python3
"""更新 research bundle 中的 todo，并自动重写 TODO.md。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from bundle_schema import bundle_path_from_input, load_bundle, save_bundle, update_todo_items, upsert_todo_items


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="更新 research bundle 的 todo。")
    parser.add_argument("--bundle", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument("--todo-json", action="append", default=[], help="todo JSON 文件；可为单对象或数组")
    parser.add_argument("--set-status", action="append", default=[], help="按 todo_id=status 更新状态，可重复传入")
    parser.add_argument("--append-note", action="append", default=[], help="按 todo_id=note 追加笔记，可重复传入")
    return parser.parse_args()


def load_todo_items(path_str: str) -> list[dict[str, Any]]:
    path = Path(path_str).expanduser()
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list) and all(isinstance(item, dict) for item in data):
        return data
    raise ValueError(f"{path} 必须是 JSON 对象或对象数组")


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


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.bundle).expanduser())

    try:
        bundle = load_bundle(bundle_path)
        todo_items: list[dict[str, Any]] = []
        for path_str in args.todo_json:
            todo_items.extend(load_todo_items(path_str))
        if todo_items:
            upsert_todo_items(bundle, todo_items)

        status_updates = parse_status_pairs(args.set_status)
        note_updates = parse_note_pairs(args.append_note)
        if status_updates or note_updates:
            update_todo_items(bundle, status_updates=status_updates, note_updates=note_updates)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法更新 todo: {exc}")
        return 1

    if not any([args.todo_json, args.set_status, args.append_note]):
        print("[错误] 没有提供任何 todo 变更。")
        return 1

    save_bundle(bundle, bundle_path)
    workflow = bundle.get("workflow", {})
    todo_items = workflow.get("todo_items", []) if isinstance(workflow, dict) else []
    print(f"[完成] bundle: {bundle_path}")
    print(f"[todo 数] {len(todo_items)}")
    print(f"[状态更新] {len(args.set_status)}")
    print(f"[笔记追加] {len(args.append_note)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
