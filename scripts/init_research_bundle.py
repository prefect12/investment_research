#!/usr/bin/env python3
"""初始化本地 research bundle。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from bundle_schema import (
    ALLOWED_TODO_STAGES,
    default_bundle_dir,
    default_todo_markdown_path,
    ensure_bundle_dirs,
    init_bundle,
    save_bundle,
)
from dossier_schema import load_dossier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="初始化 equity-investment-dossier 的 research bundle。")
    parser.add_argument("--seed-dossier", help="已有 dossier JSON；用于迁移到 research bundle")
    parser.add_argument("--company", help="公司名称")
    parser.add_argument("--ticker", help="股票代码")
    parser.add_argument("--exchange", default="", help="交易所")
    parser.add_argument("--research-date", default="", help="研究日期，YYYY-MM-DD")
    parser.add_argument("--analyst", default="Codex", help="分析者")
    parser.add_argument("--conclusion", default="观察", help="初始结论")
    parser.add_argument("--thesis", default="", help="初始 thesis")
    parser.add_argument("--base-dir", default="/tmp/equity-dossiers", help="默认 bundle 根目录")
    parser.add_argument("--output-dir", help="显式指定 bundle 目录")
    return parser.parse_args()


def build_dossier_seed(args: argparse.Namespace) -> dict:
    if args.seed_dossier:
        return load_dossier(Path(args.seed_dossier).expanduser())

    if not args.company or not args.ticker or not args.research_date:
        raise ValueError("未提供 --seed-dossier 时，必须至少提供 --company --ticker --research-date")

    return {
        "meta": {
            "company_name": args.company,
            "ticker": args.ticker,
            "exchange": args.exchange,
            "research_date": args.research_date,
            "analyst": args.analyst,
            "conclusion": args.conclusion,
            "thesis": args.thesis,
        }
    }


def print_layer_tree(bundle_dir: Path) -> None:
    staged_roots = [
        "search/queries",
        "search/results",
        "search/reviews",
        "raw",
        "extracted",
        "working",
        "promoted",
        "artifacts",
    ]
    print("[分层目录]")
    for root in staged_roots:
        print(f"- {bundle_dir / root}")
        for stage in sorted(ALLOWED_TODO_STAGES):
            print(f"  - {bundle_dir / root / stage}")


def main() -> int:
    args = parse_args()

    try:
        dossier_seed = build_dossier_seed(args)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] {exc}")
        return 1

    bundle_dir = default_bundle_dir(
        dossier_seed=dossier_seed,
        base_dir=args.base_dir,
        output_dir=args.output_dir,
    )
    ensure_bundle_dirs(bundle_dir)

    bundle = init_bundle(dossier_seed)
    bundle_path = save_bundle(bundle, bundle_dir / "bundle.json")
    todo_path = default_todo_markdown_path(bundle_path)

    print(f"[完成] bundle: {bundle_path}")
    print(f"[完成] todo: {todo_path}")
    print(f"[说明] 已创建按研究阶段分层的目录结构，默认阶段为：{', '.join(sorted(ALLOWED_TODO_STAGES))}")
    print_layer_tree(bundle_dir)
    return 0


if __name__ == "__main__":
    sys.exit(main())
