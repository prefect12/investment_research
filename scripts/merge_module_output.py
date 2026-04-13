#!/usr/bin/env python3
"""把单个模块输出合并进 research bundle。"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bundle_schema import bundle_path_from_input, load_bundle, merge_module_output, save_bundle


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="合并模块输出到 research bundle。")
    parser.add_argument("--bundle", required=True, help="bundle.json 路径，或 bundle 所在目录")
    parser.add_argument("--module", required=True, help="模块输出 JSON 路径")
    parser.add_argument("--keep-existing", action="store_true", help="保留相同 section+owner 的旧结果，而不是替换")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    bundle_path = bundle_path_from_input(args.bundle)
    module_path = Path(args.module).expanduser()

    try:
        bundle = load_bundle(bundle_path)
        module_output = json.loads(module_path.read_text(encoding="utf-8"))
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取输入: {exc}")
        return 1

    try:
        merged = merge_module_output(bundle, module_output, replace_existing=not args.keep_existing)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 模块输出不合法: {exc}")
        return 1

    save_bundle(merged, bundle_path)
    print(f"[完成] 已更新 bundle: {bundle_path}")
    print(f"[模块] {module_output.get('section', 'unknown')} / {module_output.get('owner', 'unknown')}")
    print(f"[累计模块数] {len(merged.get('module_outputs', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
