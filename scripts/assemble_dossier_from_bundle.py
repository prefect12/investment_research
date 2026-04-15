#!/usr/bin/env python3
"""从 research bundle 组装最终 dossier JSON。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bundle_schema import append_artifact_record, assemble_dossier, bundle_path_from_input, load_bundle, save_bundle, validate_bundle
from dossier_schema import validate_dossier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="从 research bundle 组装 dossier JSON。")
    parser.add_argument("--input", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument("--output", help="输出 dossier.json 路径；默认写到 bundle 同目录")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.input).expanduser())

    try:
        bundle = load_bundle(bundle_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 bundle: {exc}")
        return 1

    bundle_errors, bundle_warnings = validate_bundle(bundle)
    if bundle_warnings:
        print("[bundle 警告]")
        for warning in bundle_warnings:
            print(f"- {warning}")
    if bundle_errors:
        print("[错误] bundle 校验失败：")
        for error in bundle_errors:
            print(f"- {error}")
        return 1

    dossier = assemble_dossier(bundle)
    dossier_errors, dossier_warnings = validate_dossier(dossier)
    if dossier_warnings:
        print("[dossier 警告]")
        for warning in dossier_warnings:
            print(f"- {warning}")
    if dossier_errors:
        print("[错误] 组装后的 dossier 校验失败：")
        for error in dossier_errors:
            print(f"- {error}")
        return 1

    output_path = Path(args.output).expanduser() if args.output else bundle_path.parent / "dossier.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(dossier, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    append_artifact_record(
        bundle,
        owner="system-assembler",
        module="final-assembly",
        path=str(output_path),
        kind="dossier-json",
        title="最终 dossier JSON",
        note="assemble_dossier_from_bundle.py 已完成组装",
        todo_ids=["todo-dossier-assembly"],
        layer="artifacts",
        value_tier="used_in_dossier",
    )
    save_bundle(bundle, bundle_path)

    print(f"[完成] dossier: {output_path}")
    print(f"[来源数] {len(dossier.get('sources', {}).get('items', []))}")
    print(f"[开放问题数] {len(dossier.get('open_questions', {}).get('items', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
