#!/usr/bin/env python3
"""把搜索后筛出的来源、提取、笔记与文件持续写入 research bundle。"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any

from bundle_schema import (
    ALLOWED_SOURCE_STAGES,
    ALLOWED_TODO_STAGES,
    ALLOWED_VALUE_TIERS,
    append_research_assets,
    append_search_journal_entry,
    bundle_dir_from_input,
    bundle_path_from_input,
    bundle_progress,
    link_research_to_todo,
    load_bundle,
    save_bundle,
    upsert_todo_items,
)


FILE_BUCKETS = ["raw", "extracted", "working", "promoted", "artifacts"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="把来源、提取、claims、笔记与文件持续写入 research bundle。")
    parser.add_argument("--bundle", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument("--owner", default="main-agent", help="当前写入动作的 owner")
    parser.add_argument("--module", default="", help="当前写入所属模块")
    parser.add_argument("--todo-id", action="append", default=[], help="关联的 todo id，可重复传入")
    parser.add_argument("--stage", choices=sorted(ALLOWED_TODO_STAGES), help="显式指定研究阶段；默认从 todo 推断")
    parser.add_argument("--query-id", default="", help="关联的 query id")
    parser.add_argument("--result-id", default="", help="关联的 result id")
    parser.add_argument("--search-id", default="", help="关联的 search journal id")

    parser.add_argument("--query", help="可选：补记本轮搜索 query（建议优先用 record_search_round.py）")
    parser.add_argument("--reason", default="", help="可选：补记搜索原因")
    parser.add_argument("--based-on", default="", help="可选：补记搜索依据")
    parser.add_argument(
        "--outcome",
        choices=["no_hit", "duplicate", "lead", "evidence", "counterevidence"],
        help="可选：补记搜索 outcome",
    )
    parser.add_argument("--captured-url", action="append", default=[], help="可选：补记本轮捕获 URL")
    parser.add_argument("--next-action", action="append", default=[], help="可选：补记下一步动作")
    parser.add_argument("--result-summary", default="", help="可选：补记本轮简短总结")

    parser.add_argument("--new-todo-json", action="append", default=[], help="新派生 todo 的 JSON 文件；可为单对象或数组")
    parser.add_argument("--promote-source", action="store_true", help="显式把 source 标记为 promoted")
    parser.add_argument("--source-stage", choices=sorted(ALLOWED_SOURCE_STAGES), default="candidate", help="source stage")
    parser.add_argument("--source-value-tier", choices=sorted(ALLOWED_VALUE_TIERS), default="candidate", help="source value_tier")
    parser.add_argument("--source-json", action="append", default=[], help="来源 JSON 文件；可为单对象或对象数组")
    parser.add_argument("--claim-json", action="append", default=[], help="claim JSON 文件；可为单对象或对象数组")
    parser.add_argument("--artifact-json", action="append", default=[], help="artifact JSON 文件；可为单对象或对象数组")
    parser.add_argument("--extraction-json", action="append", default=[], help="extraction JSON 文件；可为单对象或对象数组")

    parser.add_argument("--source-id", help="单条来源的 id")
    parser.add_argument("--source-title", help="单条来源的标题")
    parser.add_argument("--source-kind", help="单条来源的 kind")
    parser.add_argument("--source-url", help="单条来源的 URL")
    parser.add_argument("--source-publisher", default="", help="单条来源的 publisher")
    parser.add_argument("--source-date", default="", help="单条来源的日期，YYYY-MM-DD")
    parser.add_argument("--source-note", default="", help="单条来源的备注")

    parser.add_argument("--extraction-id", help="单条提取记录的 id")
    parser.add_argument("--extraction-source-id", help="单条提取记录关联的 source id")
    parser.add_argument("--extraction-method", default="", help="单条提取记录的方法说明")
    parser.add_argument("--extraction-note", default="", help="单条提取记录备注")
    parser.add_argument("--extraction-value-tier", choices=sorted(ALLOWED_VALUE_TIERS), default="useful", help="extraction value_tier")

    parser.add_argument("--note", action="append", default=[], help="直接追加一条笔记，可重复传入")
    parser.add_argument("--note-file", action="append", default=[], help="从文本文件追加笔记，可重复传入")
    parser.add_argument("--note-layer", choices=FILE_BUCKETS, default="working", help="笔记所处分层")
    parser.add_argument("--note-value-tier", choices=sorted(ALLOWED_VALUE_TIERS), default="useful", help="笔记 value_tier")

    parser.add_argument("--copy-file", help="把一个现有文件复制进 bundle 的分层目录")
    parser.add_argument("--bucket", choices=FILE_BUCKETS, default="raw", help="copy-file 的目标目录")
    parser.add_argument("--filename", help="copy-file 保存后的文件名；默认沿用原文件名")
    parser.add_argument("--artifact-id", help="copy-file 生成的 artifact id")
    parser.add_argument("--artifact-kind", default="", help="copy-file 生成的 artifact kind")
    parser.add_argument("--artifact-title", default="", help="copy-file 生成的 artifact 标题")
    parser.add_argument("--artifact-note", default="", help="copy-file 生成的 artifact 备注")
    return parser.parse_args()


def load_json_records(path_str: str) -> list[dict[str, Any]]:
    path = Path(path_str).expanduser()
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        return [data]
    if isinstance(data, list):
        if not all(isinstance(item, dict) for item in data):
            raise ValueError(f"{path} 中存在非对象条目")
        return data
    raise ValueError(f"{path} 必须是 JSON 对象或对象数组")


def load_todo_items(path_str: str) -> list[dict[str, Any]]:
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


def build_source_record(args: argparse.Namespace) -> dict[str, Any] | None:
    source_fields = [args.source_title, args.source_kind, args.source_url, args.source_publisher, args.source_date, args.source_note]
    if not any(value is not None and str(value).strip() for value in source_fields):
        return None
    missing = []
    if not args.source_id:
        missing.append("--source-id")
    if not args.source_title:
        missing.append("--source-title")
    if not args.source_kind:
        missing.append("--source-kind")
    if not args.source_url:
        missing.append("--source-url")
    if missing:
        raise ValueError(f"使用单条来源参数时，必须同时提供: {', '.join(missing)}")

    stage = "promoted" if args.promote_source else args.source_stage
    value_tier = "used_in_dossier" if stage == "promoted" else args.source_value_tier
    return {
        "id": args.source_id,
        "title": args.source_title,
        "kind": args.source_kind,
        "url": args.source_url,
        "publisher": args.source_publisher,
        "date": args.source_date,
        "note": args.source_note,
        "stage": stage,
        "value_tier": value_tier,
    }


def build_inline_extraction_record(args: argparse.Namespace) -> dict[str, Any] | None:
    inline_values = [args.extraction_id, args.extraction_source_id, args.extraction_method, args.extraction_note]
    if not any(inline_values):
        return None
    return {
        "id": args.extraction_id,
        "source_id": args.extraction_source_id or args.source_id or "",
        "method": args.extraction_method,
        "note": args.extraction_note,
        "value_tier": args.extraction_value_tier,
    }


def build_note_records(args: argparse.Namespace) -> list[dict[str, Any]]:
    note_records: list[dict[str, Any]] = []
    for note in args.note:
        text = str(note).strip()
        if text:
            note_records.append({"owner": args.owner, "note": text, "layer": args.note_layer, "value_tier": args.note_value_tier})
    for path_str in args.note_file:
        path = Path(path_str).expanduser()
        text = path.read_text(encoding="utf-8").strip()
        if text:
            note_records.append(
                {
                    "owner": args.owner,
                    "note": text,
                    "source_path": str(path),
                    "layer": args.note_layer,
                    "value_tier": args.note_value_tier,
                }
            )
    return note_records


def annotate_records(
    records: list[dict[str, Any]],
    *,
    owner: str,
    module: str,
    todo_ids: list[str],
    search_id: str,
    query_id: str,
    result_id: str,
) -> list[dict[str, Any]]:
    annotated: list[dict[str, Any]] = []
    for item in records:
        record = dict(item)
        record.setdefault("owner", owner)
        if module:
            record.setdefault("module", module)
        if todo_ids:
            record.setdefault("todo_ids", todo_ids)
        if search_id:
            record.setdefault("search_id", search_id)
        if query_id:
            record.setdefault("query_id", query_id)
        if result_id:
            record.setdefault("result_id", result_id)
        annotated.append(record)
    return annotated


def default_artifact_kind(bucket: str) -> str:
    return {
        "raw": "raw-file",
        "extracted": "extracted-file",
        "working": "working-file",
        "promoted": "promoted-file",
        "artifacts": "artifact-file",
    }.get(bucket, "artifact-file")


def artifact_value_tier(bucket: str) -> str:
    if bucket == "promoted":
        return "used_in_dossier"
    if bucket == "raw":
        return "candidate"
    return "useful"


def copy_file_into_bundle(args: argparse.Namespace, bundle_dir: Path, stage: str) -> tuple[Path | None, dict[str, Any] | None]:
    if not args.copy_file:
        return None, None

    source_path = Path(args.copy_file).expanduser()
    if not source_path.exists():
        raise FileNotFoundError(f"copy-file 不存在: {source_path}")

    target_dir = bundle_dir / args.bucket / stage
    target_dir.mkdir(parents=True, exist_ok=True)
    filename = args.filename or source_path.name
    target_path = target_dir / filename

    if source_path.resolve() != target_path.resolve():
        shutil.copy2(source_path, target_path)

    artifact_record: dict[str, Any] = {
        "owner": args.owner,
        "path": target_path.relative_to(bundle_dir).as_posix(),
        "kind": args.artifact_kind or default_artifact_kind(args.bucket),
        "layer": args.bucket,
        "value_tier": artifact_value_tier(args.bucket),
    }
    if args.artifact_id:
        artifact_record["id"] = args.artifact_id
    elif args.extraction_id:
        artifact_record["id"] = f"artifact-{args.extraction_id}"
    elif args.source_id:
        artifact_record["id"] = f"artifact-{args.source_id}-{args.bucket}"
    if args.artifact_title:
        artifact_record["title"] = args.artifact_title
    if args.artifact_note:
        artifact_record["note"] = args.artifact_note
    if args.source_id:
        artifact_record.setdefault("source_id", args.source_id)
    if args.query_id:
        artifact_record.setdefault("query_id", args.query_id)
    if args.result_id:
        artifact_record.setdefault("result_id", args.result_id)

    return target_path, artifact_record


def has_search_context(args: argparse.Namespace) -> bool:
    return any(
        [
            str(args.query or "").strip(),
            str(args.reason or "").strip(),
            str(args.based_on or "").strip(),
            str(args.outcome or "").strip(),
            args.captured_url,
            args.next_action,
            str(args.result_summary or "").strip(),
        ]
    )


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.bundle).expanduser())
    bundle_dir = bundle_dir_from_input(bundle_path)

    try:
        bundle = load_bundle(bundle_path)
        todo_ids = normalize_todo_ids(args.todo_id)
        stage = infer_stage(bundle, args.stage or "", todo_ids, args.module)

        new_todo_items: list[dict[str, Any]] = []
        for path_str in args.new_todo_json:
            new_todo_items.extend(load_todo_items(path_str))
        created_todo_ids = upsert_todo_items(bundle, new_todo_items) if new_todo_items else []

        source_records: list[dict[str, Any]] = []
        for path_str in args.source_json:
            source_records.extend(load_json_records(path_str))
        inline_source = build_source_record(args)
        if inline_source:
            source_records.append(inline_source)

        extraction_records: list[dict[str, Any]] = []
        for path_str in args.extraction_json:
            extraction_records.extend(load_json_records(path_str))
        inline_extraction = build_inline_extraction_record(args)
        if inline_extraction:
            extraction_records.append(inline_extraction)

        claim_records: list[dict[str, Any]] = []
        for path_str in args.claim_json:
            claim_records.extend(load_json_records(path_str))

        artifact_records: list[dict[str, Any]] = []
        for path_str in args.artifact_json:
            artifact_records.extend(load_json_records(path_str))

        note_records = build_note_records(args)
        copied_path, copied_artifact = copy_file_into_bundle(args, bundle_dir, stage)
        if copied_artifact:
            artifact_records.append(copied_artifact)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法准备研究写入: {exc}")
        return 1

    search_context = has_search_context(args)
    if not search_context and not any([source_records, extraction_records, claim_records, note_records, artifact_records, created_todo_ids]):
        print("[错误] 没有提供搜索日志上下文，也没有提供可写入的研究资产或新 todo。")
        return 1

    annotated_sources = annotate_records(
        source_records,
        owner=args.owner,
        module=args.module,
        todo_ids=todo_ids,
        search_id=args.search_id,
        query_id=args.query_id,
        result_id=args.result_id,
    )
    annotated_extractions = annotate_records(
        extraction_records,
        owner=args.owner,
        module=args.module,
        todo_ids=todo_ids,
        search_id=args.search_id,
        query_id=args.query_id,
        result_id=args.result_id,
    )
    annotated_claims = annotate_records(
        claim_records,
        owner=args.owner,
        module=args.module,
        todo_ids=todo_ids,
        search_id=args.search_id,
        query_id=args.query_id,
        result_id=args.result_id,
    )
    annotated_notes = annotate_records(
        note_records,
        owner=args.owner,
        module=args.module,
        todo_ids=todo_ids,
        search_id=args.search_id,
        query_id=args.query_id,
        result_id=args.result_id,
    )
    annotated_artifacts = annotate_records(
        artifact_records,
        owner=args.owner,
        module=args.module,
        todo_ids=todo_ids,
        search_id=args.search_id,
        query_id=args.query_id,
        result_id=args.result_id,
    )

    if copied_path and annotated_sources and not any(str(item.get("path", "")).strip() for item in annotated_sources):
        annotated_sources[0]["path"] = copied_path.relative_to(bundle_dir).as_posix()
    if copied_path and args.bucket == "extracted" and annotated_extractions:
        for item in annotated_extractions:
            if not str(item.get("path", "")).strip():
                item["path"] = copied_path.relative_to(bundle_dir).as_posix()
        if copied_artifact:
            artifact_id = str(copied_artifact.get("id", "")).strip()
            for item in annotated_extractions:
                if artifact_id and not str(item.get("artifact_id", "")).strip():
                    item["artifact_id"] = artifact_id

    append_research_assets(
        bundle,
        source_records=annotated_sources,
        extraction_records=annotated_extractions,
        claim_records=annotated_claims,
        note_records=annotated_notes,
        artifact_records=annotated_artifacts,
    )

    source_ids = [str(item.get("id", "")).strip() for item in annotated_sources if str(item.get("id", "")).strip()]
    claim_ids = [str(item.get("id", "")).strip() for item in annotated_claims if str(item.get("id", "")).strip()]
    artifact_ids = [str(item.get("id", "")).strip() for item in annotated_artifacts if str(item.get("id", "")).strip()]

    search_id = args.search_id
    if search_context:
        captured_urls = [str(item).strip() for item in args.captured_url if str(item).strip()]
        if not captured_urls:
            captured_urls = [
                str(item.get("url", "")).strip()
                for item in annotated_sources
                if isinstance(item, dict) and str(item.get("url", "")).strip()
            ]
        search_entry = append_search_journal_entry(
            bundle,
            {
                "id": args.search_id or "",
                "module": args.module,
                "todo_id": todo_ids[0] if todo_ids else "",
                "query": args.query or "",
                "reason": args.reason,
                "based_on": args.based_on,
                "outcome": args.outcome or ("lead" if annotated_sources else "evidence"),
                "captured_urls": captured_urls,
                "saved_paths": [copied_path.relative_to(bundle_dir).as_posix()] if copied_path else [],
                "promoted_source_ids": [
                    source_id
                    for source_id, item in zip(source_ids, annotated_sources, strict=False)
                    if str(item.get("stage", "")).strip() == "promoted"
                ],
                "new_todo_ids": created_todo_ids,
                "next_actions": args.next_action,
                "summary": args.result_summary,
                "query_id": args.query_id,
                "result_ids": [args.result_id] if args.result_id else [],
            },
        )
        search_id = str(search_entry.get("id", "")).strip()

    for todo_id in todo_ids:
        link_research_to_todo(
            bundle,
            todo_id=todo_id,
            query_ids=[args.query_id] if args.query_id else [],
            result_ids=[args.result_id] if args.result_id else [],
            source_ids=source_ids,
            claim_ids=claim_ids,
            artifact_ids=artifact_ids,
            search_id=search_id,
            note=args.result_summary or args.source_note,
            promote_to_in_progress=True,
        )

    save_bundle(bundle, bundle_path)
    progress = bundle_progress(bundle)

    print(f"[完成] bundle: {bundle_path}")
    if copied_path:
        print(f"[文件] {copied_path}")
    if created_todo_ids:
        print(f"[新增 todo] {', '.join(created_todo_ids)}")
    if search_id:
        print(f"[搜索日志] {search_id}")
    print(
        f"[新增] sources={len(annotated_sources)} extractions={len(annotated_extractions)} claims={len(annotated_claims)} "
        f"notes={len(annotated_notes)} artifacts={len(annotated_artifacts)}"
    )
    print(
        f"[累计] stage={progress['current_stage']} queries={progress['query_records']} results={progress['result_records']} "
        f"sources={progress['source_records']} extractions={progress['extraction_records']} claims={progress['claim_records']} "
        f"notes={progress['note_records']} artifacts={progress['artifact_records']} reviews={progress['review_cycles']}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
