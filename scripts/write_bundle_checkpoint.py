#!/usr/bin/env python3
"""为 research bundle 生成可续跑的断点检查点。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bundle_schema import (
    ALLOWED_TODO_STAGES,
    bundle_path_from_input,
    load_bundle,
    save_bundle,
    write_bundle_checkpoint,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="为 research bundle 写入断点检查点文件。")
    parser.add_argument("--input", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument("--stage", choices=sorted(ALLOWED_TODO_STAGES), help="显式指定 checkpoint 所属阶段")
    parser.add_argument("--label", default="manual-checkpoint", help="checkpoint 标签")
    parser.add_argument("--owner", default="main-agent", help="写入 checkpoint 的 agent")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(Path(args.input).expanduser())

    try:
        bundle = load_bundle(bundle_path)
        checkpoint = write_bundle_checkpoint(
            bundle,
            bundle_path,
            stage=args.stage or "",
            label=args.label,
            owner=args.owner,
        )
        save_bundle(bundle, bundle_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法写入 checkpoint: {exc}")
        return 1

    print(f"[完成] bundle: {bundle_path}")
    print(f"[checkpoint] {checkpoint['checkpoint_id']} ({checkpoint['stage']})")
    print(f"[markdown] {checkpoint['markdown_path']}")
    print(f"[json] {checkpoint['json_path']}")
    print(f"[latest] {checkpoint['latest_markdown']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
