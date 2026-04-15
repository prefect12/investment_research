#!/usr/bin/env python3
"""校验 research bundle 的结构、workflow、分层文件数与完成状态。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bundle_schema import (
    append_artifact_record,
    bundle_dir_from_input,
    bundle_file_counts,
    bundle_has_active_todo,
    bundle_has_progress,
    bundle_path_from_input,
    bundle_progress,
    load_bundle,
    save_bundle,
    validate_bundle,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 research bundle JSON。")
    parser.add_argument("--input", required=True, help="bundle.json 路径，或 bundle 所在目录")
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

    errors, warnings = validate_bundle(bundle)
    meta = bundle.get("dossier_seed", {}).get("meta", {})
    print(f"公司: {meta.get('company_name', '未知公司')} ({meta.get('ticker', 'N/A')})")
    print(f"输入文件: {bundle_path}")

    if warnings:
        print("\n[警告]")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\n[校验失败]")
        for error in errors:
            print(f"- {error}")
        return 1

    append_artifact_record(
        bundle,
        owner="system-validator",
        module="final-assembly",
        path=str(bundle_path),
        kind="validation-bundle",
        title="Research Bundle 校验通过",
        note="validate_research_bundle.py 校验通过",
        todo_ids=["todo-dossier-assembly"],
        layer="artifacts",
        value_tier="useful",
    )
    save_bundle(bundle, bundle_path)

    progress = bundle_progress(bundle)
    file_counts = bundle_file_counts(bundle_dir)
    print("\n[校验通过]")
    print(f"- current_stage: {progress['current_stage']}")
    print(f"- research_started/foundation_ready/module_ready/report_ready: {progress['research_started']}/{progress['foundation_ready']}/{progress['module_ready']}/{progress['report_ready']}")
    print(f"- 模块输出数: {progress['module_outputs']}")
    print(f"- query_records 数: {progress['query_records']}")
    print(f"- result_records 数: {progress['result_records']}")
    print(f"- source_records 数: {progress['source_records']}")
    print(f"- extraction_records 数: {progress['extraction_records']}")
    print(f"- claim_records 数: {progress['claim_records']}")
    print(f"- note_records 数: {progress['note_records']}")
    print(f"- review_records 数: {progress['review_records']}")
    print(f"- artifact_records 数: {progress['artifact_records']}")
    print(f"- search_journal 数: {progress['search_journal']}")
    print(f"- review_cycles 数: {progress['review_cycles']}")
    print(f"- todo 总数: {progress['todo_total']}")
    print(f"- todo 已完成: {progress['todo_done']}")
    print(f"- todo 进行中: {progress['todo_in_progress']}")
    print(f"- todo 阻塞: {progress['todo_blocked']}")
    print(f"- active_todo_count: {progress['active_todo_count']}")
    print(f"- open_p0_count: {progress['open_p0_count']}")
    print(f"- open_p1_count: {progress['open_p1_count']}")
    print(f"- open_p2_count: {progress['open_p2_count']}")
    print(f"- completion_percent: {progress['completion_percent']}%")
    print(f"- pending_search_count: {progress['pending_search_count']}")
    print(f"- promoted_source_count: {progress['promoted_source_count']}")
    print(f"- non_blocking_open_question_count: {progress['non_blocking_open_question_count']}")
    print(f"- completed_validation_steps: {', '.join(progress['completed_validation_steps']) or '无'}")
    print(f"- missing_validation_steps: {', '.join(progress['missing_validation_steps']) or '无'}")
    print(f"- search/queries 文件数: {file_counts['search_queries']}")
    print(f"- search/results 文件数: {file_counts['search_results']}")
    print(f"- search/reviews 文件数: {file_counts['search_reviews']}")
    print(f"- raw 文件数: {file_counts['raw']}")
    print(f"- extracted 文件数: {file_counts['extracted']}")
    print(f"- working 文件数: {file_counts['working']}")
    print(f"- promoted 文件数: {file_counts['promoted']}")
    print(f"- artifacts 文件数: {file_counts['artifacts']}")
    if progress["foundation_ready_missing"] or progress["module_ready_missing"] or progress["report_ready_missing"]:
        if progress["foundation_ready_missing"]:
            print("- foundation_ready_missing:")
            for item in progress["foundation_ready_missing"][:6]:
                print(f"  - {item}")
        if progress["module_ready_missing"]:
            print("- module_ready_missing:")
            for item in progress["module_ready_missing"][:6]:
                print(f"  - {item}")
        if progress["report_ready_missing"]:
            print("- report_ready_missing:")
            for item in progress["report_ready_missing"][:8]:
                print(f"  - {item}")

    if not bundle_has_progress(bundle):
        print("- 状态: 仍是空 bundle；只是完成了初始化，还没有真正记录 query/result/review 或研究资产。")
    elif not bundle_has_active_todo(bundle) and not progress["report_ready"]:
        print("- 状态: 当前没有 active todo，但报告也还没 ready，建议检查 workflow。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
