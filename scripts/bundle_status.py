#!/usr/bin/env python3
"""显示 research bundle 的 workflow、分层文件数与完成状态。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bundle_schema import (
    bundle_dir_from_input,
    bundle_file_counts,
    bundle_has_active_todo,
    bundle_has_research_content,
    bundle_has_progress,
    bundle_path_from_input,
    bundle_progress,
    load_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="显示 research bundle 的当前进度。")
    parser.add_argument("--input", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument("--fail-if-empty", action="store_true", help="如果仍是空壳初始化状态，则返回非 0")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.input).expanduser())
    bundle_dir = bundle_dir_from_input(bundle_path)

    try:
        bundle = load_bundle(bundle_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 bundle: {exc}")
        return 1

    meta = bundle.get("dossier_seed", {}).get("meta", {})
    progress = bundle_progress(bundle)
    file_counts = bundle_file_counts(bundle_dir)
    workflow = bundle.get("workflow", {})
    next_actions = workflow.get("next_actions", []) if isinstance(workflow, dict) else []
    search_journal = workflow.get("search_journal", []) if isinstance(workflow, dict) else []
    review_cycles = workflow.get("review_cycles", []) if isinstance(workflow, dict) else []

    print(f"公司: {meta.get('company_name', '未知公司')} ({meta.get('ticker', 'N/A')})")
    print(f"bundle: {bundle_path}")
    print(f"updated_at: {bundle.get('updated_at', '')}")
    print("")
    print("[Workflow]")
    print(f"- current_stage: {progress['current_stage']}")
    print(f"- research_started/foundation_ready/module_ready/report_ready: {progress['research_started']}/{progress['foundation_ready']}/{progress['module_ready']}/{progress['report_ready']}")
    print(f"- parent_todo_done: {progress['parent_todo_done']}/{progress['parent_todo_total']}")
    print(f"- question_todo_total: {progress['question_todo_total']}")
    print(f"- todo_total: {progress['todo_total']}")
    print(f"- todo_done: {progress['todo_done']}")
    print(f"- todo_in_progress: {progress['todo_in_progress']}")
    print(f"- todo_blocked: {progress['todo_blocked']}")
    print(f"- todo_todo: {progress['todo_todo']}")
    print(f"- open_p0_count: {progress['open_p0_count']}")
    print(f"- open_p1_count: {progress['open_p1_count']}")
    print(f"- completion_percent: {progress['completion_percent']}%")
    if progress['focus_parent_todo']:
        print(f"- focus_parent_todo: {progress['focus_parent_todo']}")
    if progress['focus_question_todo']:
        print(f"- focus_question_todo: {progress['focus_question_todo']}")

    print("")
    print("[Research Assets]")
    print(f"- module_outputs: {progress['module_outputs']}")
    print(f"- query_records: {progress['query_records']}")
    print(f"- result_records: {progress['result_records']}")
    print(f"- source_records: {progress['source_records']}")
    print(f"- extraction_records: {progress['extraction_records']}")
    print(f"- claim_records: {progress['claim_records']}")
    print(f"- note_records: {progress['note_records']}")
    print(f"- review_records: {progress['review_records']}")
    print(f"- artifact_records: {progress['artifact_records']}")
    print(f"- search_journal: {progress['search_journal']}")
    print(f"- review_cycles: {progress['review_cycles']}")
    print(f"- promoted_source_count: {progress['promoted_source_count']}")

    print("")
    print("[目录文件数]")
    print(f"- search/queries: {file_counts['search_queries']}")
    print(f"- search/results: {file_counts['search_results']}")
    print(f"- search/reviews: {file_counts['search_reviews']}")
    print(f"- raw: {file_counts['raw']}")
    print(f"- extracted: {file_counts['extracted']}")
    print(f"- working: {file_counts['working']}")
    print(f"- promoted: {file_counts['promoted']}")
    print(f"- artifacts: {file_counts['artifacts']}")

    if next_actions:
        print("")
        print("[下一步]")
        for item in next_actions[:6]:
            print(f"- {item}")

    if search_journal:
        print("")
        print("[最近搜索]")
        for item in search_journal[-3:]:
            if not isinstance(item, dict):
                continue
            print(
                f"- {item.get('timestamp', '')} | {item.get('outcome', '')} | "
                f"{item.get('query', '') or item.get('summary', '')}"
            )

    if review_cycles:
        print("")
        print("[最近复盘]")
        for item in review_cycles[-3:]:
            if not isinstance(item, dict):
                continue
            print(f"- {item.get('timestamp', '')} | {item.get('decision', '') or item.get('findings', '')}")

    print("")
    if progress["report_ready"]:
        print("[状态] bundle 已满足完整报告门槛")
        return 0
    if bundle_has_research_content(bundle):
        print("[状态] bundle 已进入研究闭环，后续继续按 todo -> search -> review 推进")
    elif bundle_has_progress(bundle):
        print("[状态] bundle 已有少量活动记录，但还没形成完整研究闭环")
    else:
        print("[状态] bundle 目前还是初始化骨架")

    if args.fail_if_empty and not bundle_has_research_content(bundle):
        return 1
    if args.fail_if_empty and not bundle_has_active_todo(bundle) and not progress["report_ready"]:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
