#!/usr/bin/env python3
"""校验股票研究报告 dossier JSON。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dossier_schema import load_dossier, validate_dossier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="校验 dossier JSON 的结构和关键字段。")
    parser.add_argument("--input", required=True, help="待校验的 dossier JSON 路径")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser()

    try:
        dossier = load_dossier(input_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 dossier: {exc}")
        return 1

    errors, warnings = validate_dossier(dossier)

    meta = dossier.get("meta", {})
    company_name = meta.get("company_name", "未知公司")
    ticker = meta.get("ticker", "N/A")

    print(f"公司: {company_name} ({ticker})")
    print(f"输入文件: {input_path}")

    if warnings:
        print("\n[警告]")
        for warning in warnings:
            print(f"- {warning}")

    if errors:
        print("\n[校验失败]")
        for error in errors:
            print(f"- {error}")
        return 1

    history = dossier.get("company_history", {})
    management = dossier.get("management", {})
    sources = dossier.get("sources", {})
    investor_lenses = dossier.get("investor_lenses", {})

    print("\n[校验通过]")
    print(f"- era 数量: {len(history.get('eras', []))}")
    print(f"- 时间线事件数: {len(history.get('timeline', []))}")
    print(f"- 关键管理层数: {len(management.get('leaders', []))}")
    print(f"- 访谈条目数: {len(management.get('interviews', []))}")
    print(f"- 预判复盘数: {len(management.get('predictions', []))}")
    print(f"- 投资大师视角数: {len(investor_lenses.get('views', []))}")
    print(f"- 来源数: {len(sources.get('items', []))}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
