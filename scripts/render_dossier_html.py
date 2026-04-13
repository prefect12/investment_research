#!/usr/bin/env python3
"""把股票研究 dossier JSON 渲染成多页完整研究报告。"""

from __future__ import annotations

import argparse
import html
import sys
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from dossier_schema import default_output_dir, load_dossier, validate_dossier


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="渲染股票研究报告 HTML。")
    parser.add_argument("--input", required=True, help="结构化 dossier JSON 路径")
    parser.add_argument("--base-dir", default="/tmp/equity-dossiers", help="默认输出根目录")
    parser.add_argument("--output-dir", help="多页报告输出目录；默认 /tmp/equity-dossiers/<slug>/")
    return parser.parse_args()


def esc(value: Any) -> str:
    return html.escape(str(value))


def nl2br(value: str) -> str:
    return "<br>".join(esc(value).splitlines())


def compact_link_label(url: str) -> str:
    host = urlparse(url).netloc.strip().lower()
    return host.removeprefix("www.") or "链接"


LABEL_MAP = {
    "background": "背景",
    "style": "风格",
    "key_moves": "关键动作",
    "major_wins": "主要成功",
    "major_errors": "主要错误",
    "impact_summary": "长期影响",
    "kind": "类型",
    "publisher": "发布方",
    "date": "日期",
    "summary": "摘要",
    "outcome": "结果",
    "thesis": "核心假设",
    "implication": "估值含义",
    "topic": "主题",
    "topics": "主题",
    "takeaway": "核心结论",
    "quote": "关键原话",
    "statement": "当时表态",
    "analysis": "复盘分析",
    "capability": "能力维度",
    "horizon": "观察窗口",
    "criterion": "核验点",
    "assessment": "判断",
    "evidence": "依据",
}

VALUE_MAP = {
    "kind": {
        "ir-page": "投资者关系页面",
        "macro-official": "宏观官方材料",
        "sec-filing": "SEC 文件",
        "regulatory": "监管材料",
        "market-data": "市场数据",
        "annual-report": "年报",
        "earnings-release": "财报新闻稿",
        "conference-call": "电话会",
        "investor-presentation": "投资者演示材料",
        "proxy": "委托书",
        "transcript": "文字实录",
        "interview": "采访",
    }
}


def display_label(key: str) -> str:
    return LABEL_MAP.get(key, key.replace("_", " "))


def display_value(key: str, value: Any) -> Any:
    if isinstance(value, str):
        return VALUE_MAP.get(key, {}).get(value, value)
    return value


def render_text(value: Any) -> str:
    if value is None:
        return '<p class="muted">未提供。</p>'
    if isinstance(value, str):
        if not value.strip():
            return '<p class="muted">未提供。</p>'
        return f"<p>{nl2br(value)}</p>"
    if isinstance(value, list):
        if not value:
            return '<p class="muted">未提供。</p>'
        if all(isinstance(item, str) for item in value):
            items = "".join(f"<li>{nl2br(item)}</li>" for item in value if item.strip())
            return f'<ul class="bullet-list">{items}</ul>' if items else '<p class="muted">未提供。</p>'
        items = "".join(f"<li>{render_inline_mapping(item)}</li>" for item in value)
        return f'<ul class="bullet-list">{items}</ul>' if items else '<p class="muted">未提供。</p>'
    if isinstance(value, dict):
        return render_mapping(value)
    return f"<p>{esc(value)}</p>"


def render_inline_mapping(value: Any) -> str:
    if isinstance(value, dict):
        pieces = []
        for key, item in value.items():
            if item in ("", None, [], {}):
                continue
            label = esc(display_label(key))
            pieces.append(f"<strong>{label}</strong>: {esc(display_value(key, item))}")
        return " | ".join(pieces) if pieces else "未提供"
    if isinstance(value, str):
        return nl2br(value)
    return esc(value)


def render_mapping(value: dict[str, Any]) -> str:
    rows = []
    for key, item in value.items():
        if item in ("", None, [], {}):
            continue
        label = esc(display_label(key))
        rows.append(f"<dt>{label}</dt><dd>{render_text(display_value(key, item))}</dd>")
    if not rows:
        return '<p class="muted">未提供。</p>'
    return f'<dl class="definition-list">{"".join(rows)}</dl>'


def render_metric_pills(items: list[tuple[str, Any]]) -> str:
    pills = []
    for label, raw_value in items:
        value = str(raw_value).strip()
        if not value:
            continue
        pills.append(
            '<span class="metric-pill">'
            f'<span class="metric-pill-label">{esc(label)}</span>'
            f'<span class="metric-pill-value">{nl2br(value)}</span>'
            "</span>"
        )
    if not pills:
        return ""
    return f'<div class="metric-pill-row">{"".join(pills)}</div>'


def render_revenue_breakdown_cards(items: list[Any], sources: dict[str, dict[str, Any]], limit: int | None = None) -> str:
    revenue_cards = []
    for item in items[:limit] if isinstance(limit, int) else items:
        if not isinstance(item, dict):
            continue
        pill_html = render_metric_pills(
            [
                ("收入占比", item.get("share", "")),
                ("趋势", item.get("trend", "")),
            ]
        )
        comment = str(item.get("comment", "")).strip()
        body = pill_html
        if comment:
            body += f'<p class="entry-note">{nl2br(comment)}</p>'
        elif not pill_html:
            body = '<p class="muted">未提供。</p>'
        revenue_cards.append(
            filterable_card(
                title=str(item.get("segment", "未命名业务")),
                body=body,
                search=" ".join(
                    [
                        str(item.get("segment", "")),
                        str(item.get("share", "")),
                        str(item.get("trend", "")),
                        str(item.get("comment", "")),
                    ]
                ),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )
    if not revenue_cards:
        return "<p class='muted'>未提供营收拆解。</p>"
    return f'<div class="card-grid revenue-breakdown-grid">{"".join(revenue_cards)}</div>'


def render_check_list(items: list[dict[str, Any]] | None) -> str:
    if not isinstance(items, list) or not items:
        return ""

    rows = []
    for item in items:
        if not isinstance(item, dict):
            continue
        criterion = str(item.get("criterion", "")).strip()
        assessment = str(item.get("assessment", "")).strip()
        evidence = str(item.get("evidence", "")).strip()
        if not any([criterion, assessment, evidence]):
            continue

        pieces = []
        if criterion:
            pieces.append(f"<strong>{esc(criterion)}</strong>")
        if assessment:
            pieces.append(f"判断：{esc(assessment)}")
        if evidence:
            pieces.append(f"依据：{esc(evidence)}")
        rows.append(f"<li>{'；'.join(pieces)}</li>")

    if not rows:
        return ""
    return f'<ul class="check-list">{"".join(rows)}</ul>'


def badge(text: str, tone: str = "") -> str:
    rendered = text
    if tone == "conclusion":
        rendered = conclusion_badge_text(text)
    classes = "badge"
    if tone:
        classes += f" {tone}"
    return f'<span class="{classes}">{esc(rendered)}</span>'


def humanize_conclusion_text(value: Any) -> str:
    text = str(value).strip()
    mapping = {
        "正向": "正向，已经具备进入研究清单或建立仓位的理由",
        "观察": "继续观察，先跟踪验证，不急于出手",
        "回避": "暂时回避，当前不进入",
    }
    return mapping.get(text, text)


def conclusion_badge_text(value: Any) -> str:
    text = str(value).strip()
    mapping = {
        "正向": "结论：正向",
        "观察": "结论：继续观察",
        "回避": "结论：暂时回避",
    }
    return mapping.get(text, text or "未定")


def source_index(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    items = data.get("sources", {}).get("items", [])
    index: dict[str, dict[str, Any]] = {}
    if not isinstance(items, list):
        return index
    for item in items:
        if isinstance(item, dict) and item.get("id"):
            index[str(item["id"])] = item
    return index


def render_source_links(source_ids: list[str] | None, sources: dict[str, dict[str, Any]]) -> str:
    if not source_ids:
        return ""
    links = []
    seen_labels: set[str] = set()
    for source_id in source_ids:
        source = sources.get(source_id)
        if not source:
            missing_label = str(source_id).strip()
            if missing_label in seen_labels:
                continue
            seen_labels.add(missing_label)
            links.append(f'<span class="source-link missing">{esc(missing_label)}</span>')
            continue
        label = str(source.get("publisher") or source.get("title") or source_id).strip()
        if not label or label in seen_labels:
            continue
        seen_labels.add(label)
        url = source.get("url", "")
        if url:
            links.append(f'<a class="source-link" href="{esc(url)}" target="_blank" rel="noreferrer">{esc(label)}</a>')
        else:
            links.append(f'<span class="source-link">{esc(label)}</span>')
    return f'<p class="source-strip"><span class="source-label">来源：</span>{" · ".join(links)}</p>' if links else ""


def card_attrs(*, search: str = "", person: str = "", era: str = "", tags: list[str] | None = None, evidence: str = "", result: str = "") -> str:
    tag_value = " ".join(tags or [])
    attrs = {
        "data-search": search,
        "data-person": person,
        "data-era": era,
        "data-tags": tag_value,
        "data-evidence": evidence,
        "data-result": result,
    }
    return " ".join(f'{key}="{esc(value)}"' for key, value in attrs.items() if value)


def filterable_card(
    *,
    title: str,
    subtitle: str = "",
    body: str = "",
    search: str = "",
    person: str = "",
    era: str = "",
    tags: list[str] | None = None,
    evidence: str = "",
    result: str = "",
    source_ids: list[str] | None = None,
    sources: dict[str, dict[str, Any]] | None = None,
) -> str:
    meta = []
    if subtitle:
        meta.append(f'<p class="card-subtitle">{esc(subtitle)}</p>')
    if evidence:
        meta.append(badge(evidence, "evidence"))
    if result:
        meta.append(badge(result, "result"))
    tag_html = "".join(badge(tag, "tag") for tag in (tags or []))
    source_html = render_source_links(source_ids or [], sources or {})
    return (
        f'<article class="entry filterable" {card_attrs(search=search, person=person, era=era, tags=tags, evidence=evidence, result=result)}>'
        '<div class="entry-head">'
        f"<h4>{esc(title)}</h4>"
        f"<div class='card-meta'>{''.join(meta)}{tag_html}</div>"
        "</div>"
        f"<div class='entry-body'>{body}</div>"
        f"{source_html}"
        "</article>"
    )


def section_block(
    section_id: str,
    title: str,
    content: str,
    *,
    open_by_default: bool = False,
    extra_class: str = "",
) -> str:
    classes = "report-section"
    if extra_class:
        classes += f" {extra_class}"
    return (
        f'<section id="{esc(section_id)}" class="{classes}" data-section="{esc(section_id)}">'
        f'<div class="section-title">{esc(title)}</div>'
        f'<div class="section-body">{content}</div>'
        "</section>"
    )


def two_column_cards(items: list[tuple[str, Any]]) -> str:
    cards = []
    for label, value in items:
        cards.append(
            '<article class="report-block report-note">'
            f"<h4>{esc(label)}</h4>"
            f"{render_text(value)}"
            "</article>"
        )
    return f'<div class="report-columns report-columns-tight">{"".join(cards)}</div>'


def render_table(headers: list[str], rows: list[list[str]], *, dense: bool = False) -> str:
    if not rows:
        return '<p class="muted">未提供。</p>'
    head_html = "".join(f"<th>{esc(header)}</th>" for header in headers)
    body_html = "".join(
        "<tr>" + "".join(f"<td>{cell}</td>" for cell in row) + "</tr>"
        for row in rows
    )
    class_name = "report-table dense" if dense else "report-table"
    return f'<div class="table-wrap"><table class="{class_name}"><thead><tr>{head_html}</tr></thead><tbody>{body_html}</tbody></table></div>'


def parse_number(value: Any) -> float | None:
    if isinstance(value, (int, float)):
        return float(value)
    if not isinstance(value, str):
        return None
    raw = value.replace(",", "").strip()
    try:
        return float(raw)
    except ValueError:
        return None


def render_company_route_visual(data: dict[str, Any]) -> str:
    eras = [item for item in data["company_history"].get("eras", []) if isinstance(item, dict)]
    if not eras:
        return '<p class="muted">未提供公司阶段路线图。</p>'

    era_items = []
    for idx, era in enumerate(eras, start=1):
        date_range = str(era.get("date_range", "")).strip()
        summary = str(era.get("summary", "")).strip()
        era_items.append(
            '<article class="history-era-card">'
            f'<p class="history-era-index">{idx:02d}</p>'
            '<div class="history-era-head">'
            f'<h4>{esc(str(era.get("name", "未命名阶段")))}</h4>'
            "</div>"
            + (f'<p class="history-era-meta">{esc(date_range)}</p>' if date_range else "")
            + (f'<p class="history-era-summary">{nl2br(summary)}</p>' if summary else "")
            + "</article>"
        )

    return (
        '<article class="visual-block">'
        '<h3 class="subheading">阶段总览</h3>'
        '<p class="visual-note">这里只保留章节目录式摘要。细节放到下方竖版时间轴里，不在这里重复展开。</p>'
        '<div class="history-era-overview">'
        + "".join(era_items)
        + "</div>"
        + "</article>"
    )


def render_price_visual(data: dict[str, Any]) -> str:
    market = data.get("market_behavior", {})
    candles = [
        item for item in market.get("price_candles", [])
        if isinstance(item, dict)
        and all(parse_number(item.get(key)) is not None for key in ["open", "high", "low", "close"])
    ]
    if candles:
        width = 1080
        height = 300
        margin_left = 50
        margin_right = 24
        margin_top = 26
        margin_bottom = 38
        plot_w = width - margin_left - margin_right
        plot_h = height - margin_top - margin_bottom
        lows = [parse_number(item["low"]) for item in candles]
        highs = [parse_number(item["high"]) for item in candles]
        min_low = min(v for v in lows if v is not None)
        max_high = max(v for v in highs if v is not None)
        value_span = max(max_high - min_low, 1.0)
        step = plot_w / max(len(candles), 1)
        body_width = max(step * 0.45, 8)

        def y_for(value: float) -> float:
            return margin_top + (max_high - value) / value_span * plot_h

        grid = []
        for pct in [0.0, 0.25, 0.5, 0.75, 1.0]:
            price = min_low + (1 - pct) * value_span
            y = margin_top + pct * plot_h
            grid.append(f'<line x1="{margin_left}" y1="{y:.1f}" x2="{width - margin_right}" y2="{y:.1f}" class="svg-grid" />')
            grid.append(f'<text x="{margin_left - 10}" y="{y + 4:.1f}" class="svg-axis" text-anchor="end">{price:.0f}</text>')

        candles_svg = []
        for idx, item in enumerate(candles):
            x = margin_left + step * idx + step / 2
            open_v = parse_number(item["open"]) or 0.0
            high_v = parse_number(item["high"]) or 0.0
            low_v = parse_number(item["low"]) or 0.0
            close_v = parse_number(item["close"]) or 0.0
            rising = close_v >= open_v
            color = "#1f6a4f" if rising else "#9a3d2d"
            body_top = y_for(max(open_v, close_v))
            body_bottom = y_for(min(open_v, close_v))
            body_height = max(body_bottom - body_top, 2.0)
            candles_svg.append(f'<line x1="{x:.1f}" y1="{y_for(high_v):.1f}" x2="{x:.1f}" y2="{y_for(low_v):.1f}" stroke="{color}" stroke-width="1.5" />')
            candles_svg.append(
                f'<rect x="{x - body_width/2:.1f}" y="{body_top:.1f}" width="{body_width:.1f}" height="{body_height:.1f}" '
                f'fill="{color if rising else "#ffffff"}" stroke="{color}" stroke-width="1.5" />'
            )
            if idx in {0, len(candles) // 2, len(candles) - 1}:
                candles_svg.append(
                    f'<text x="{x:.1f}" y="{height - 14}" class="svg-axis" text-anchor="middle">{esc(str(item.get("date", "")))}</text>'
                )

        svg = (
            f'<svg viewBox="0 0 {width} {height}" class="report-svg" role="img" aria-label="股价 K 线示意图">'
            + "".join(grid)
            + "".join(candles_svg)
            + "</svg>"
        )
        return (
            '<article class="visual-block">'
            '<h3 class="subheading">股价变化图</h3>'
            '<p class="visual-note">如果 dossier 提供价格序列，这里会优先渲染 K 线或价格路径图。当前示例使用占位行情数据，仅用于展示版式。</p>'
            + svg
            + "</article>"
        )

    phases = [item for item in market.get("stock_phases", []) if isinstance(item, dict)]
    if not phases:
        return '<p class="muted">未提供股价变化图。</p>'
    rows = [
        [
            esc(str(item.get("name", ""))),
            esc(str(item.get("date_range", ""))),
            esc(str(item.get("summary", ""))),
        ]
        for item in phases
    ]
    return (
        '<article class="visual-block">'
        '<h3 class="subheading">股价阶段变化</h3>'
        '<p class="visual-note">当前没有价格序列数据，退化为阶段表。未来提供价格数据后可自动渲染 K 线或价格路径图。</p>'
        + render_table(["阶段", "时间", "说明"], rows, dense=True)
        + "</article>"
    )


def render_summary(data: dict[str, Any], layout_label: str = "", report_label: str = "股票研究报告") -> str:
    meta = data["meta"]
    current_status = data["current_status"]
    summary = data["summary"]
    management = data["management"]
    valuation = data["valuation"]

    stat_items = current_status.get("snapshot_metrics", [])[:6]
    stats = "".join(
        '<div class="stat-card">'
        f'<span class="stat-label">{esc(item.get("label", ""))}</span>'
        f'<strong>{esc(item.get("value", ""))}</strong>'
        f'<p class="stat-note">{esc(item.get("note", ""))}</p>'
        "</div>"
        for item in stat_items
        if isinstance(item, dict)
    )

    support = render_text(summary.get("support_points", []))
    risk = render_text(summary.get("risk_points", []))
    questions = render_text(summary.get("open_questions", []))

    management_judgment = summary.get("management_judgment") or management.get("judgment", "")
    valuation_judgment = summary.get("valuation_judgment") or valuation.get("overview", "")
    market_overview = current_status.get("price_action_summary", "")
    variant_badge = badge(f"布局：{layout_label}") if layout_label else ""

    return f"""
    <header class="hero">
      <div class="hero-copy">
        <p class="eyebrow">{esc(report_label)}</p>
        <h1>{esc(meta.get("company_name", "未知公司"))} <span>{esc(meta.get("ticker", ""))}</span></h1>
        <div class="hero-meta">
          {badge(meta.get("conclusion", "未定"), "conclusion")}
          {variant_badge}
          <span>研究日期：{esc(meta.get("research_date", ""))}</span>
          <span>状态日期：{esc(current_status.get("as_of", ""))}</span>
          <span>交易所：{esc(meta.get("exchange", ""))}</span>
          <span>分析者：{esc(meta.get("analyst", "Codex"))}</span>
        </div>
        <p class="hero-thesis">{nl2br(meta.get("thesis", ""))}</p>
      </div>
      <div class="hero-stats">{stats}</div>
    </header>
    <section class="summary-grid">
      <article class="panel">
        <h3>支持点</h3>
        {support}
      </article>
      <article class="panel danger">
        <h3>风险点</h3>
        {risk}
      </article>
      <article class="panel neutral">
        <h3>待验证问题</h3>
        {questions}
      </article>
    </section>
    <section class="summary-grid compact">
      <article class="panel compact-panel">
        <h3>管理层结论</h3>
        {render_text(management_judgment)}
      </article>
      <article class="panel compact-panel">
        <h3>估值一句话判断</h3>
        {render_text(valuation_judgment)}
      </article>
      <article class="panel compact-panel">
        <h3>当前市场位置</h3>
        {render_text(market_overview)}
      </article>
    </section>
    """


def render_current_status(data: dict[str, Any]) -> str:
    section = data["current_status"]
    metric_rows = [
        [esc(str(item.get("label", ""))), esc(str(item.get("value", ""))), esc(str(item.get("note", "")))]
        for item in section.get("snapshot_metrics", [])
        if isinstance(item, dict)
    ]
    level_rows = [
        [esc(str(item.get("label", ""))), esc(str(item.get("value", ""))), esc(str(item.get("note", "")))]
        for item in section.get("price_levels", [])
        if isinstance(item, dict)
    ]
    return (
        '<div class="report-columns">'
        + "".join(
            [
                f'<article class="report-block"><h3>公司当前状态</h3>{render_text(section.get("status_summary", ""))}</article>',
                f'<article class="report-block"><h3>当前估值位置</h3>{render_text(section.get("valuation_summary", ""))}</article>',
                f'<article class="report-block"><h3>近期股价与位置</h3>{render_text(section.get("price_action_summary", ""))}</article>',
            ]
        )
        + "</div>"
        + '<h3 class="subheading">直观指标</h3>'
        + render_table(["指标", "当前值", "说明"], metric_rows, dense=True)
        + '<h3 class="subheading">价格位置</h3>'
        + render_table(["位置", "当前值", "说明"], level_rows, dense=True)
    )


def render_business_snapshot(data: dict[str, Any]) -> str:
    section = data["business_quality"]
    sources = source_index(data)
    return (
        '<div class="report-columns">'
        + "".join(
            [
                f'<article class="report-block"><h3>业务概览</h3>{render_text(section.get("overview", ""))}</article>',
                f'<article class="report-block"><h3>护城河总结</h3>{render_text(section.get("moat_summary", ""))}</article>',
                f'<article class="report-block"><h3>护城河构成</h3>{render_text(section.get("moat_points", []))}</article>',
            ]
        )
        + "</div>"
        + '<h3 class="subheading">营收拆解</h3>'
        + render_revenue_breakdown_cards(section.get("revenue_breakdown", []), sources, limit=8)
    )


def normalize_investor_lenses(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("investor_lenses")
    if isinstance(raw, dict):
        views = raw.get("views", [])
        overview = raw.get("overview", "")
    else:
        legacy = data.get("investor_master_views") or {}
        overview = legacy.get("overall_judgment", "")
        views = []
        for item in legacy.get("profiles", []) or []:
            if not isinstance(item, dict):
                continue
            raw_checks = item.get("key_checks", []) or []
            checks = []
            for check in raw_checks:
                if isinstance(check, dict):
                    criterion = str(check.get("criterion", "")).strip()
                    assessment = str(check.get("assessment", "")).strip()
                    evidence = str(check.get("evidence", "")).strip()
                    if criterion or assessment or evidence:
                        checks.append(
                            {
                                "criterion": criterion,
                                "assessment": assessment,
                                "evidence": evidence,
                            }
                        )
                else:
                    text = str(check).strip()
                    if text:
                        checks.append({"criterion": text, "assessment": "", "evidence": ""})

            positives = [str(x).strip() for x in item.get("why_yes", []) if str(x).strip()]
            concerns = [str(x).strip() for x in item.get("why_no", []) if str(x).strip()]
            why_parts = []
            if positives:
                why_parts.append("支持点：" + "；".join(positives[:2]))
            if concerns:
                why_parts.append("顾虑：" + "；".join(concerns[:2]))

            views.append(
                {
                    "investor": str(item.get("master", "")).strip(),
                    "framework_focus": [str(x).strip() for x in item.get("philosophy_anchor", []) if str(x).strip()],
                    "fit_assessment": "",
                    "would_likely_invest": str(item.get("could_invest", "")).strip(),
                    "why": "；".join(part for part in why_parts if part),
                    "positives": positives,
                    "concerns": concerns,
                    "must_believe": [str(x).strip() for x in raw_checks if str(x).strip()],
                    "judgment_change_conditions": [
                        str(x).strip() for x in item.get("judgment_change_conditions", []) if str(x).strip()
                    ],
                    "key_checks": checks,
                    "source_ids": item.get("source_ids", []),
                }
            )

    normalized_views = []
    for item in views:
        if not isinstance(item, dict):
            continue
        normalized_views.append(item)

    return {"overview": overview, "views": normalized_views}


def render_investor_lenses(data: dict[str, Any]) -> str:
    section = normalize_investor_lenses(data)
    sources = source_index(data)
    quick_reads = []
    for item in section.get("views", []):
        if not isinstance(item, dict):
            continue
        investor = str(item.get("investor", "")).strip() or "未命名投资大师"
        framework = "、".join(str(x) for x in item.get("framework_focus", []) if str(x).strip())
        verdict = str(item.get("would_likely_invest", "")).strip()
        checks = "；".join(
            str(x.get("criterion", ""))
            for x in item.get("key_checks", [])[:2]
            if isinstance(x, dict) and str(x.get("criterion", "")).strip()
        )
        parts = [f"<strong>{esc(investor)}</strong>"]
        if verdict:
            parts.append(f"当前判断：{esc(verdict)}")
        if framework:
            parts.append(f"框架重心：{esc(framework)}")
        if checks:
            parts.append(f"最先核验：{esc(checks)}")
        quick_reads.append(f"<li>{'。'.join(parts)}。</li>")

    lens_entries = []
    for item in section.get("views", []):
        if not isinstance(item, dict):
            continue
        focus_tags = "".join(badge(str(x), "tag") for x in item.get("framework_focus", []) if str(x).strip())
        verdict_tags = "".join(
            badge(text, tone)
            for text, tone in [
                (str(item.get("fit_assessment", "")), "tag"),
                (str(item.get("would_likely_invest", "")), "conclusion"),
            ]
            if text
        )
        body = render_mapping(
            {
                "核心框架": item.get("framework_focus", []),
                "简短判断": item.get("why", ""),
                "为什么可能愿意投": item.get("positives", []),
                "为什么可能不会投": item.get("concerns", []),
                "最想先核验什么": item.get("must_believe", []),
                "什么会改变判断": item.get("judgment_change_conditions", []),
            }
        )
        checklist = render_check_list(item.get("key_checks", []))
        lens_entries.append(
            '<article class="entry">'
            '<div class="entry-head">'
            f'<div><h4>{esc(str(item.get("investor", "未命名投资大师")))}</h4>'
            f'<p class="card-subtitle">{esc(str(item.get("would_likely_invest", "")))}</p></div>'
            f"<div class='card-meta'>{verdict_tags}</div>"
            "</div>"
            f"<div class='card-meta'>{focus_tags}</div>"
            + body
            + ('<h3 class="subheading">框架检查项</h3>' + checklist if checklist else "")
            + render_source_links(item.get("source_ids", []), sources)
            + "</article>"
        )

    return (
        '<div class="report-columns">'
        + "".join(
            [
                f'<article class="report-block"><h3>总判断</h3>{render_text(section.get("overview", ""))}</article>',
            ]
        )
        + "</div>"
        + '<h3 class="subheading">快速浏览</h3>'
        + (f'<ul class="bullet-list narrative-list">{"".join(quick_reads)}</ul>' if quick_reads else '<p class="muted">未提供投资大师视角摘要。</p>')
        + '<h3 class="subheading">逐位展开</h3>'
        + f'<div>{"".join(lens_entries) or "<p class=\'muted\'>未提供投资大师视角。</p>"}</div>'
    )


def render_investment_case(data: dict[str, Any]) -> str:
    section = data["investment_case"]
    metric_rows = [
        [
            esc(str(item.get("name", ""))),
            esc(str(item.get("why_it_matters", ""))),
            esc(str(item.get("watch_for", ""))),
        ]
        for item in section.get("monitoring_metrics", [])
        if isinstance(item, dict)
    ]
    return (
        '<div class="report-columns">'
        + "".join(
            [
                f'<article class="report-block"><h3>为什么当前时点值得看</h3>{render_text(section.get("why_now", ""))}</article>',
                f'<article class="report-block"><h3>时代背景与利率环境</h3>{render_text(section.get("macro_context", ""))}</article>',
                f'<article class="report-block"><h3>公司当前处在什么阶段</h3>{render_text(section.get("regime_position", ""))}</article>',
                f'<article class="report-block"><h3>外部环境如何传导到公司</h3>{render_text(section.get("regime_mechanism", ""))}</article>',
                f'<article class="report-block"><h3>市场当前在定价什么</h3>{render_text(section.get("market_expectation", ""))}</article>',
                f'<article class="report-block"><h3>你和市场的核心分歧</h3>{render_text(section.get("variant_perception", ""))}</article>',
                f'<article class="report-block"><h3>失效条件</h3>{render_text(section.get("falsifiers", []))}</article>',
            ]
        )
        + "</div>"
        + '<h3 class="subheading">关键跟踪指标</h3>'
        + render_table(["指标", "为什么重要", "要观察什么"], metric_rows)
    )


def render_company_history(data: dict[str, Any]) -> str:
    sources = source_index(data)
    eras = [item for item in data["company_history"].get("eras", []) if isinstance(item, dict)]
    era_map = {str(item.get("name", "")).strip(): item for item in eras if str(item.get("name", "")).strip()}

    timeline_parts = []
    current_era = ""
    for item in data["company_history"].get("timeline", []):
        if not isinstance(item, dict):
            continue

        era_name = str(item.get("era", "")).strip()
        if era_name and era_name != current_era:
            era = era_map.get(era_name, {})
            era_range = str(era.get("date_range", "")).strip()
            era_summary = str(era.get("summary", "")).strip()
            strategy_moves = [str(entry).strip() for entry in era.get("strategy_moves", []) if str(entry).strip()]
            marker_extra = ""
            if strategy_moves:
                marker_extra = (
                    f'<p class="history-marker-extra"><strong>阶段主线：</strong>{esc(" / ".join(strategy_moves[:4]))}</p>'
                )
            timeline_parts.append(
                '<article class="history-era-marker">'
                f'<div class="history-date-lane"><p class="history-era-marker-range">{esc(era_range)}</p></div>'
                '<div class="history-rail"><span class="history-era-dot"></span></div>'
                '<div class="history-era-marker-card">'
                '<p class="history-marker-kicker">阶段切换</p>'
                f'<h4>{esc(era_name)}</h4>'
                + (f'<p class="history-marker-summary">{nl2br(era_summary)}</p>' if era_summary else "")
                + marker_extra
                + render_source_links(era.get("source_ids", []), sources)
                + "</div>"
                "</article>"
            )
            current_era = era_name

        meta = []
        category = str(item.get("category", "")).strip()
        if category:
            meta.append(badge(translate_category(category), "evidence"))
        evidence_label = str(item.get("evidence_label", "")).strip()
        if evidence_label:
            meta.append(badge(evidence_label, "tag"))
        era = str(item.get("era", "")).strip()
        if era:
            meta.append(badge(era, "tag"))

        notes = []
        stock_move = str(item.get("stock_move", "")).strip()
        if stock_move:
            notes.append(f"<p><strong>市场反应：</strong>{nl2br(stock_move)}</p>")
        relative_move = str(item.get("relative_move", "")).strip()
        if relative_move:
            notes.append(f"<p><strong>相对位置：</strong>{nl2br(relative_move)}</p>")

        timeline_parts.append(
            '<article class="history-timeline-item">'
            f'<div class="history-date-lane"><p class="history-event-date">{esc(str(item.get("date", "")))}</p></div>'
            '<div class="history-rail"><span class="history-event-dot"></span></div>'
            '<div class="history-event-card">'
            + (f"<div class='card-meta'>{''.join(meta)}</div>" if meta else "")
            + f'<h4>{esc(str(item.get("title", "未命名事件")))}</h4>'
            + render_text(item.get("detail", ""))
            + (f'<div class="history-event-notes">{"".join(notes)}</div>' if notes else "")
            + render_source_links(item.get("source_ids", []), sources)
            + "</div>"
            "</article>"
        )

    timeline_html = (
        '<div class="history-timeline">'
        + "".join(timeline_parts)
        + "</div>"
        if timeline_parts
        else '<p class="muted">未提供关键时间线。</p>'
    )

    return render_company_route_visual(data) + '<h3 class="subheading">关键节点时间轴</h3>' + timeline_html


def render_management(data: dict[str, Any]) -> str:
    sources = source_index(data)
    leaders_html = []
    for item in data["management"].get("leaders", []):
        if not isinstance(item, dict):
            continue
        tenure_end = item.get("tenure_end") or "至今"
        body = render_mapping(
            {
                "背景": item.get("background", ""),
                "风格": item.get("style", ""),
                "关键动作": item.get("key_moves", []),
                "主要成功": item.get("major_wins", []),
                "主要错误": item.get("major_errors", []),
                "长期影响": item.get("impact_summary", ""),
            }
        )
        leaders_html.append(
            filterable_card(
                title=str(item.get("name", "未命名管理层")),
                subtitle=f"{item.get('role', '')} | {item.get('tenure_start', '')} - {tenure_end}",
                body=body,
                search=" ".join(
                    [
                        str(item.get("name", "")),
                        str(item.get("role", "")),
                        str(item.get("background", "")),
                        str(item.get("style", "")),
                        str(item.get("impact_summary", "")),
                    ]
                ),
                person=str(item.get("name", "")),
                tags=item.get("tags", []),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )

    interviews_html = []
    for item in data["management"].get("interviews", []):
        if not isinstance(item, dict):
            continue
        body = render_mapping(
            {
                "主题": item.get("topics", []),
                "核心结论": item.get("takeaway", ""),
                "关键原话": item.get("quote", ""),
            }
        )
        interviews_html.append(
            filterable_card(
                title=str(item.get("title", "未命名访谈")),
                subtitle=f"{item.get('leader', '')} | {item.get('date', '')} | {item.get('outlet', '')}",
                body=body,
                search=" ".join(
                    [
                        str(item.get("leader", "")),
                        str(item.get("title", "")),
                        str(item.get("outlet", "")),
                        str(item.get("takeaway", "")),
                    ]
                ),
                person=str(item.get("leader", "")),
                tags=item.get("topics", []),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )

    predictions_html = []
    for item in data["management"].get("predictions", []):
        if not isinstance(item, dict):
            continue
        body = render_mapping(
            {
                "当时表态": item.get("statement", ""),
                "后续结果": item.get("outcome", ""),
                "复盘分析": item.get("analysis", ""),
                "能力维度": item.get("capability", ""),
                "观察窗口": item.get("horizon", ""),
            }
        )
        predictions_html.append(
            filterable_card(
                title=str(item.get("topic", "未命名预判")),
                subtitle=f"{item.get('leader', '')} | {item.get('date', '')}",
                body=body,
                search=" ".join(
                    [
                        str(item.get("leader", "")),
                        str(item.get("topic", "")),
                        str(item.get("statement", "")),
                        str(item.get("outcome", "")),
                        str(item.get("analysis", "")),
                    ]
                ),
                person=str(item.get("leader", "")),
                tags=item.get("tags", []),
                result=str(item.get("result", "")),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )

    return (
        '<article class="panel stretch">'
        "<h3>管理层长期结论</h3>"
        f"{render_text(data['management'].get('judgment', ''))}"
        "</article>"
        '<h3 class="subheading">管理层更替地图</h3>'
        f'<div class="card-grid">{"".join(leaders_html) or "<p class=\'muted\'>未提供管理层资料。</p>"}</div>'
        '<h3 class="subheading">重要访谈索引</h3>'
        f'<div class="card-grid">{"".join(interviews_html) or "<p class=\'muted\'>未提供访谈索引。</p>"}</div>'
        '<h3 class="subheading">管理层预判复盘</h3>'
        f'<div class="card-grid">{"".join(predictions_html) or "<p class=\'muted\'>未提供预判复盘。</p>"}</div>'
    )


def render_business_quality(data: dict[str, Any]) -> str:
    section = data["business_quality"]
    sources = source_index(data)

    return (
        two_column_cards(
            [
                ("业务概览", section.get("overview", "")),
                ("护城河总结", section.get("moat_summary", "")),
                ("护城河构成", section.get("moat_points", [])),
                ("客户与需求强度", section.get("customers", "")),
                ("价格历史与定价能力", section.get("pricing", "")),
                ("产品节奏", section.get("product_cadence", "")),
                ("客户声音", section.get("customer_voice", "")),
            ]
        )
        + '<h3 class="subheading">营收拆解</h3>'
        + render_revenue_breakdown_cards(section.get("revenue_breakdown", []), sources)
    )


def render_industry(data: dict[str, Any]) -> str:
    section = data["industry"]
    competitor_rows = [
        [
            esc(str(item.get("company", ""))),
            esc(str(item.get("ticker", ""))),
            esc(str(item.get("comparison", ""))),
        ]
        for item in section.get("competitors", [])
        if isinstance(item, dict)
    ]
    return (
        '<div class="report-columns">'
        + "".join(
            [
                f'<article class="report-block"><h3>行业结构</h3>{render_text(section.get("overview", ""))}</article>',
                f'<article class="report-block"><h3>价值链与利润池</h3>{render_text(section.get("value_chain", ""))}</article>',
            ]
        )
        + "</div>"
        + '<h3 class="subheading">关键对手与替代者</h3>'
        + render_table(["公司", "代码", "比较要点"], competitor_rows)
    )


def render_financials(data: dict[str, Any]) -> str:
    section = data["financials"]
    return (
        '<div class="report-columns">'
        + "".join(
            [
                f'<article class="report-block"><h3>财务质量总览</h3>{render_text(section.get("overview", ""))}</article>',
                f'<article class="report-block"><h3>关键正面点</h3>{render_text(section.get("key_points", []))}</article>',
                f'<article class="report-block"><h3>会计与财务红旗</h3>{render_text(section.get("red_flags", []))}</article>',
            ]
        )
        + "</div>"
    )


def render_capital_allocation(data: dict[str, Any]) -> str:
    section = data["capital_allocation"]
    sources = source_index(data)
    action_cards = []
    for item in section.get("actions", []):
        if not isinstance(item, dict):
            continue
        action_cards.append(
            filterable_card(
                title=str(item.get("type", "未命名动作")),
                subtitle=str(item.get("date", "")),
                body=render_mapping({"summary": item.get("summary", ""), "outcome": item.get("outcome", "")}),
                search=" ".join([str(item.get("type", "")), str(item.get("summary", "")), str(item.get("outcome", ""))]),
                tags=item.get("tags", []),
                evidence=str(item.get("evidence_label", "")),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )
    return (
        '<article class="panel stretch">'
        "<h3>资本配置总览</h3>"
        f"{render_text(section.get('overview', ''))}"
        "</article>"
        '<h3 class="subheading">关键动作</h3>'
        f'<div class="card-grid">{"".join(action_cards) or "<p class=\'muted\'>未提供资本配置动作。</p>"}</div>'
    )


def render_valuation(data: dict[str, Any]) -> str:
    section = data["valuation"]
    sources = source_index(data)
    peer_cards = []
    for item in section.get("peer_comparison", []):
        if not isinstance(item, dict):
            continue
        peer_cards.append(
            filterable_card(
                title=f"{item.get('company', '未命名公司')} {item.get('ticker', '')}".strip(),
                body=render_text(item.get("comparison", "")),
                search=" ".join([str(item.get("company", "")), str(item.get("ticker", "")), str(item.get("comparison", ""))]),
                tags=item.get("tags", []),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )

    scenario_cards = []
    for item in section.get("scenarios", []):
        if not isinstance(item, dict):
            continue
        scenario_cards.append(
            filterable_card(
                title=translate_scenario_name(str(item.get("name", "未命名情景"))),
                body=render_mapping({"thesis": item.get("thesis", ""), "implication": item.get("implication", "")}),
                search=" ".join([str(item.get("name", "")), str(item.get("thesis", "")), str(item.get("implication", ""))]),
                tags=item.get("tags", []),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )

    return (
        two_column_cards(
            [
                ("当前估值判断", section.get("overview", "")),
                ("历史估值区间", section.get("historical_range", "")),
            ]
        )
        + '<h3 class="subheading">同行估值对比</h3>'
        + f'<div class="card-grid">{"".join(peer_cards) or "<p class=\'muted\'>未提供同行估值对比。</p>"}</div>'
        + '<h3 class="subheading">情景分析</h3>'
        + f'<div class="card-grid">{"".join(scenario_cards) or "<p class=\'muted\'>未提供情景分析。</p>"}</div>'
    )


def render_market_behavior(data: dict[str, Any]) -> str:
    section = data["market_behavior"]
    phase_rows = [
        [
            esc(str(item.get("name", ""))),
            esc(str(item.get("date_range", ""))),
            esc(str(item.get("summary", ""))),
            esc("；".join(str(driver) for driver in item.get("drivers", [])[:4] if str(driver).strip())),
        ]
        for item in section.get("stock_phases", [])
        if isinstance(item, dict)
    ]
    return (
        '<div class="report-columns">'
        + "".join(
            [
                f'<article class="report-block"><h3>股价与市场行为总览</h3>{render_text(section.get("overview", ""))}</article>',
                f'<article class="report-block"><h3>宏观环境如何影响股价与估值</h3>{render_text(section.get("regime_context", ""))}</article>',
                f'<article class="report-block"><h3>风格暴露</h3>{render_text(section.get("style_exposures", []))}</article>',
            ]
        )
        + "</div>"
        + render_price_visual(data)
        + '<h3 class="subheading">股价阶段复盘</h3>'
        + render_table(["阶段", "时间范围", "表现摘要", "主要驱动"], phase_rows)
    )


def render_crisis_archive(data: dict[str, Any]) -> str:
    section = data["crisis_archive"]
    sources = source_index(data)
    cards = []
    for item in section.get("cases", []):
        if not isinstance(item, dict):
            continue
        cards.append(
            filterable_card(
                title=str(item.get("title", "未命名危机")),
                subtitle=str(item.get("date", "")),
                body=render_mapping({"summary": item.get("summary", ""), "outcome": item.get("outcome", "")}),
                search=" ".join([str(item.get("title", "")), str(item.get("date", "")), str(item.get("summary", "")), str(item.get("outcome", ""))]),
                era=str(item.get("era", "")),
                tags=item.get("tags", []),
                evidence=str(item.get("evidence_label", "")),
                source_ids=item.get("source_ids", []),
                sources=sources,
            )
        )
    return f'<div class="card-grid">{"".join(cards) or "<p class=\'muted\'>未提供危机档案。</p>"}</div>'


def render_debate(data: dict[str, Any]) -> str:
    section = data["debate"]
    return two_column_cards(
        [
            ("多方观点", section.get("bull_case", "")),
            ("空方观点", section.get("bear_case", "")),
            ("误定价假设", section.get("mispricing_hypothesis", "")),
        ]
    )


def translate_category(category: str) -> str:
    mapping = {
        "founding": "成立",
        "capital_markets": "资本市场",
        "management_change": "管理层变动",
        "strategy_shift": "战略转向",
        "mna": "并购",
        "m_and_a": "并购",
        "capital_allocation": "资本配置",
        "regulation": "监管",
        "capacity": "产能扩张",
        "product": "产品节点",
        "product_launch": "产品发布",
        "deliveries": "交付",
        "earnings": "财报",
        "index_event": "指数事件",
        "restructuring": "组织调整",
        "product_cycle": "产品周期",
        "earnings_inflection": "业绩拐点",
        "crisis": "危机",
        "market_repricing": "市场重定价",
        "macro_regime": "宏观环境",
    }
    return mapping.get(category, category or "未分类")


def translate_scenario_name(name: str) -> str:
    mapping = {
        "Bull": "多头情景",
        "Base": "基准情景",
        "Bear": "空头情景",
    }
    return mapping.get(name, name)


def render_open_questions(data: dict[str, Any]) -> str:
    return '<article class="panel stretch"><h3>待验证问题</h3>' + render_text(data["open_questions"].get("items", [])) + "</article>"


def render_sources(data: dict[str, Any]) -> str:
    rows = []
    for index, item in enumerate(data["sources"].get("items", []), start=1):
        if not isinstance(item, dict):
            continue
        meta_parts = [
            str(item.get("publisher", "")).strip(),
            str(item.get("date", "")).strip(),
            str(display_value("kind", item.get("kind", ""))).strip(),
        ]
        meta_line = " | ".join(esc(part) for part in meta_parts if part)
        note = str(item.get("note", "")).strip()
        link = str(item.get("url", "")).strip()
        line_parts = [f'<span class="reference-title">{esc(str(item.get("title", "未命名来源")))}</span>']
        if meta_line:
            line_parts.append(f'<span class="reference-meta">{meta_line}</span>')
        if link:
            line_parts.append(
                f'<a class="reference-link" href="{esc(link)}" target="_blank" rel="noreferrer">{esc(compact_link_label(link))}</a>'
            )
        if note:
            compact_note = " / ".join(part.strip() for part in note.splitlines() if part.strip())
            if compact_note:
                line_parts.append(f'<span class="reference-note">{esc(compact_note)}</span>')
        rows.append(
            '<li class="reference-item">'
            f'<span class="reference-number">[{index}]</span>'
            '<div class="reference-body">'
            + '<p class="reference-line">'
            + '<span class="reference-sep"> · </span>'.join(line_parts)
            + "</p>"
            + "</div>"
            "</li>"
        )
    return f'<ol class="reference-list">{"".join(rows) or "<p class=\'muted\'>未提供来源。</p>"}</ol>'


def search_outcome_label(value: str) -> str:
    mapping = {
        "no_hit": "未命中",
        "duplicate": "重复线索",
        "lead": "候选线索",
        "evidence": "支撑证据",
        "counterevidence": "反方证据",
    }
    return mapping.get(str(value).strip(), str(value).strip() or "未分类")


def render_research_process(data: dict[str, Any]) -> str:
    section = data.get("research_process", {}) or {}
    todo_summary = [item for item in section.get("todo_summary", []) if isinstance(item, dict)]
    search_cycles = [item for item in section.get("search_cycles", []) if isinstance(item, dict)]
    open_items = [item for item in section.get("open_items", []) if isinstance(item, dict)]
    review_cycles = [item for item in section.get("review_cycles", []) if isinstance(item, dict)]
    next_actions = as_text_list(section.get("next_actions", []))
    layer_counts = section.get("layer_counts", {}) if isinstance(section.get("layer_counts", {}), dict) else {}

    module_total = len(todo_summary)
    done_modules = len([item for item in todo_summary if str(item.get("status", "")).strip() == "已完成"])
    useful_sources = sum(int(item.get("useful_source_count", 0) or 0) for item in todo_summary)
    metrics = render_metrics_strip(
        [
            ("当前阶段", str(section.get("current_stage", "initialized") or "initialized")),
            ("模块进度", f"{done_modules}/{module_total}" if module_total else "0/0"),
            ("关键搜索轮次", str(len(search_cycles))),
            ("复盘次数", str(len(review_cycles))),
            ("Useful Sources", str(useful_sources)),
            ("未关闭事项", str(len(open_items))),
        ]
    )

    todo_cards = []
    for item in todo_summary:
        pill_html = render_metric_pills(
            [
                ("状态", item.get("status", "")),
                ("进度", item.get("progress", "")),
                ("useful", item.get("useful_source_count", "")),
            ]
        )
        body = pill_html + render_text(item.get("summary", ""))
        todo_cards.append(
            filterable_card(
                title=str(item.get("module", "未命名模块")),
                subtitle=str(item.get("status", "")),
                body=body,
                search=" ".join(
                    [
                        str(item.get("module", "")),
                        str(item.get("status", "")),
                        str(item.get("summary", "")),
                    ]
                ),
            )
        )

    search_cards = []
    for item in search_cycles[-8:]:
        body = (
            f"<p><strong>意图：</strong>{nl2br(str(item.get('intent', '')).strip() or '未提供')}</p>"
            f"<p><strong>结果：</strong>{nl2br(str(item.get('decision', '')).strip() or '未提供')}</p>"
            f"<p><strong>候选结果数：</strong>{int(item.get('candidate_result_count', 0) or 0)}</p>"
        )
        todo_title = str(item.get("todo_title", "")).strip()
        if todo_title:
            body += f"<p><strong>关联待办：</strong>{nl2br(todo_title)}</p>"
        search_cards.append(
            filterable_card(
                title=str(item.get("query", "")).strip() or "未命名搜索",
                subtitle=" | ".join(
                    part
                    for part in [
                        str(item.get("timestamp", "")).strip(),
                        search_outcome_label(str(item.get("outcome", "")).strip()),
                    ]
                    if part
                ),
                body=body,
                search=" ".join(
                    [
                        str(item.get("query", "")),
                        str(item.get("intent", "")),
                        str(item.get("decision", "")),
                    ]
                ),
            )
        )

    review_cards = []
    for item in review_cycles[-5:]:
        actions = as_text_list(item.get("next_actions", []))
        body = (
            f"<p><strong>结论：</strong>{nl2br(str(item.get('decision', '')).strip() or '未提供')}</p>"
            f"<p><strong>下一步：</strong>{nl2br('；'.join(actions) or '未提供')}</p>"
        )
        review_cards.append(
            filterable_card(
                title=str(item.get("timestamp", "")).strip() or "复盘记录",
                subtitle=str(section.get("current_stage", "initialized") or "initialized"),
                body=body,
                search=" ".join(
                    [
                        str(item.get("timestamp", "")),
                        str(item.get("decision", "")),
                        " ".join(actions),
                    ]
                ),
            )
        )

    open_item_lines = [
        f"[{str(item.get('priority', '')).strip()}] {str(item.get('title', '')).strip()} "
        f"({str(item.get('module', '')).strip()} / {str(item.get('status', '')).strip()})"
        for item in open_items
        if str(item.get("title", "")).strip()
    ]

    layer_lines = [f"{key}: {int(value or 0)}" for key, value in layer_counts.items()]

    parts = [
        '<section class="report-note-box">'
        '<h2>研究闭环摘要</h2>'
        f"{render_text(section.get('workflow_summary', ''))}"
        f"{metrics}"
        f"{render_text(section.get('completion_reason', ''))}"
        "</section>"
    ]

    if todo_cards:
        parts.append(
            '<section class="report-note-box"><h2>模块待办完成概览</h2><p>这里只展示压缩后的模块进度；完整 todo 与搜索原文留在本地 bundle。</p></section>'
            + f'<div class="card-grid">{"".join(todo_cards)}</div>'
        )

    if search_cards:
        parts.append(
            '<section class="report-note-box"><h2>关键搜索转向节点</h2><p>这里保留影响研究方向的关键搜索轮次，而不是完整日志回放。</p></section>'
            + f'<div class="card-grid">{"".join(search_cards)}</div>'
        )

    if review_cards:
        parts.append(
            '<section class="report-note-box"><h2>关键复盘节点</h2><p>每次 review 都会回看已有结果，再决定下一步搜索方向。</p></section>'
            + f'<div class="card-grid">{"".join(review_cards)}</div>'
        )

    parts.append(
        '<section class="guide-grid">'
        + render_method_card("分层记录计数", layer_lines or ["暂无分层记录。"])
        + render_method_card("仍未关闭的事项", open_item_lines or ["当前没有高优先级未关闭事项。"])
        + render_method_card("下一步动作", next_actions or ["当前已经接近完成，可进入组装与页面检查。"])
        + "</section>"
    )
    return "".join(parts)


def as_text_list(value: Any) -> list[str]:
    if isinstance(value, list):
        return [str(item).strip() for item in value if str(item).strip()]
    if isinstance(value, str) and value.strip():
        return [value.strip()]
    return []


def first_non_empty(*values: Any) -> str:
    for value in values:
        text = str(value).strip()
        if text:
            return text
    return ""


def source_bucket_label(kind: str) -> str:
    mapping = {
        "annual-report": "财报与年报",
        "sec-filing": "监管与申报文件",
        "proxy": "治理与委托书",
        "earnings-release": "财报新闻稿",
        "conference-call": "电话会与实录",
        "transcript": "电话会与实录",
        "investor-presentation": "投资者材料",
        "ir-page": "投资者关系页面",
        "interview": "管理层访谈与公开表态",
        "market-data": "市场与估值数据",
        "macro-official": "宏观与政策材料",
        "regulatory": "监管材料",
    }
    return mapping.get(kind, "其他公开资料")


def source_bucket_counts(data: dict[str, Any]) -> list[tuple[str, int]]:
    counts: dict[str, int] = {}
    for item in data.get("sources", {}).get("items", []) or []:
        if not isinstance(item, dict):
            continue
        label = source_bucket_label(str(item.get("kind", "")).strip())
        counts[label] = counts.get(label, 0) + 1
    return sorted(counts.items(), key=lambda item: (-item[1], item[0]))


def collect_coverage_gaps(data: dict[str, Any]) -> list[str]:
    gaps = []
    sources_count = len(data.get("sources", {}).get("items", []) or [])
    management = data.get("management", {})
    valuation = data.get("valuation", {})
    business_quality = data.get("business_quality", {})
    investor_lenses = normalize_investor_lenses(data)

    if sources_count < 100:
        gaps.append("公开来源数量明显不足；完整报告至少应整合约 100 条公开信息源。")
    if len(management.get("interviews", []) or []) < 2:
        gaps.append("管理层公开访谈样本较少，风格与表态复盘可能不够完整。")
    if len(management.get("predictions", []) or []) < 2:
        gaps.append("管理层前瞻判断样本较少，执行复盘的把握度有限。")
    if len(business_quality.get("revenue_breakdown", []) or []) < 2:
        gaps.append("业务拆分颗粒度偏粗，分部盈利质量仍需进一步核验。")
    if len(valuation.get("peer_comparison", []) or []) < 2:
        gaps.append("同行估值对照较少，横向比较仍可继续扩展。")
    if not (investor_lenses.get("overview") or investor_lenses.get("views")):
        gaps.append("多框架投资视角未补齐，跨方法论检验不完整。")

    return gaps[:4]


def normalize_report_brief(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("report_brief") or {}
    summary = data.get("summary", {})
    investment_case = data.get("investment_case", {})
    valuation = data.get("valuation", {})
    current_status = data.get("current_status", {})
    business_quality = data.get("business_quality", {})

    next_checks = as_text_list(raw.get("next_checks")) or as_text_list(summary.get("open_questions"))
    if not next_checks:
        next_checks = [
            str(item.get("name", "")).strip()
            for item in investment_case.get("monitoring_metrics", []) or []
            if isinstance(item, dict) and str(item.get("name", "")).strip()
        ]

    payoff_sources = as_text_list(raw.get("payoff_sources"))
    if not payoff_sources:
        for candidate in [
            investment_case.get("variant_perception", ""),
            valuation.get("overview", ""),
            investment_case.get("market_expectation", ""),
        ]:
            text = str(candidate).strip()
            if text:
                payoff_sources.append(text)
        payoff_sources = payoff_sources[:3]

    return {
        "what_company_is": first_non_empty(
            raw.get("what_company_is", ""),
            business_quality.get("overview", ""),
            current_status.get("status_summary", ""),
        ),
        "current_action": humanize_conclusion_text(
            first_non_empty(raw.get("current_action", ""), data.get("meta", {}).get("conclusion", "未定"))
        ),
        "why_now": first_non_empty(raw.get("why_now", ""), investment_case.get("why_now", "")),
        "core_bet": first_non_empty(raw.get("core_bet", ""), investment_case.get("variant_perception", ""), data.get("meta", {}).get("thesis", "")),
        "market_is_pricing": first_non_empty(raw.get("market_is_pricing", ""), investment_case.get("market_expectation", "")),
        "main_error_risk": first_non_empty(
            raw.get("main_error_risk", ""),
            next(iter(as_text_list(summary.get("risk_points"))), ""),
            next(iter(as_text_list(investment_case.get("falsifiers"))), ""),
        ),
        "payoff_sources": payoff_sources,
        "next_checks": next_checks[:4],
    }


def normalize_report_method(data: dict[str, Any]) -> dict[str, Any]:
    raw = data.get("report_method") or {}
    meta = data.get("meta", {})
    current_status = data.get("current_status", {})
    bucket_counts = source_bucket_counts(data)
    information_collected = as_text_list(raw.get("information_collected"))
    if not information_collected:
        information_collected = [label for label, _ in bucket_counts[:6]]
    if not information_collected:
        information_collected = [
            "财报与监管文件",
            "电话会与投资者材料",
            "管理层访谈与公开表态",
            "行业与竞争材料",
            "市场与估值数据",
        ]

    research_modules = as_text_list(raw.get("research_modules"))
    if not research_modules:
        research_modules = [
            "当前状态与市场位置",
            "业务结构与营收拆解",
            "行业与竞争格局",
            "管理层与执行复盘",
            "财务质量与资本配置",
            "估值、预期差与赔率",
            "历史阶段、危机与关键转折",
            "多框架投资视角",
        ]

    decision_steps = as_text_list(raw.get("decision_steps"))
    if not decision_steps:
        decision_steps = [
            "先识别市场当前在定价什么，再确定这家公司真正的核心矛盾。",
            "再按业务、行业、管理层、财务与资本配置拆出支持点与风险点。",
            "然后交叉核验估值、市场预期差、反证条件与监控指标。",
            "最后收束为当前结论、主要错误风险与后续验证重点。",
        ]

    limitations = as_text_list(raw.get("limitations")) or collect_coverage_gaps(data)
    if not limitations:
        limitations = [
            "本报告仅基于公开资料，不包含渠道调研、管理层交流和未公开经营数据。",
            "估值、市场行为与赔率判断强依赖研究日期与状态日期。",
        ]

    scope_statement = first_non_empty(
        raw.get("scope_statement", ""),
        f"本报告基于截至 {current_status.get('as_of', meta.get('research_date', '研究日'))} 的公开资料完成一次性调研，"
        "目标是把业务、管理层、财务、估值和市场预期差压缩成一套可直接阅读的完整研究报告。",
    )

    return {
        "scope_statement": scope_statement,
        "information_collected": information_collected,
        "research_modules": research_modules,
        "decision_steps": decision_steps,
        "limitations": limitations,
        "bucket_counts": bucket_counts,
    }


def build_report_page_specs(cover_filename: str = "index.html") -> list[dict[str, str]]:
    return [
        {
            "id": "cover",
            "filename": cover_filename,
            "nav_label": "目录",
            "kicker": "封面与目录",
            "title": "完整股票研究报告",
            "deck": "这是一份基于公开资料完成的一次性调研报告，目标是把公司研究组织成一套可直接阅读的多页完整成品。",
        },
        {
            "id": "guide",
            "filename": "guide.html",
            "nav_label": "导读",
            "kicker": "导读与方法",
            "title": "这份报告做了什么，如何形成判断",
            "deck": "先明确收集了哪些信息、覆盖了哪些模块、如何一步步形成判断，再进入正式章节。",
        },
        {
            "id": "summary",
            "filename": "01-executive-summary.html",
            "nav_label": "执行摘要",
            "kicker": "第 1 章",
            "title": "执行摘要与当前结论",
            "deck": "先回答现在该不该投、为什么是当前时点、最容易错在哪，以及赔率来自哪里。",
        },
        {
            "id": "business-industry",
            "filename": "02-business-industry.html",
            "nav_label": "业务与行业",
            "kicker": "第 2 章",
            "title": "业务结构、护城河与行业竞争",
            "deck": "这一章解决公司到底靠什么赚钱、核心护城河是否成立，以及竞争格局如何影响中长期胜负手。",
        },
        {
            "id": "management-execution",
            "filename": "03-management-execution.html",
            "nav_label": "管理层",
            "kicker": "第 3 章",
            "title": "管理层、执行记录与公开表态复盘",
            "deck": "这一章聚焦谁在掌舵、历史上做对了什么、做错了什么，以及公开表态与结果之间的偏差。",
        },
        {
            "id": "financials-capital",
            "filename": "04-financials-capital-allocation.html",
            "nav_label": "财务与资本配置",
            "kicker": "第 4 章",
            "title": "财务质量、现金流与资本配置",
            "deck": "这一章判断利润质量是否扎实、现金流是否可信，以及资本配置是否在为长期股东创造价值。",
        },
        {
            "id": "valuation-market",
            "filename": "05-valuation-market.html",
            "nav_label": "估值与市场",
            "kicker": "第 5 章",
            "title": "估值、市场预期差与赔率来源",
            "deck": "这一章解释市场正在交易什么、估值隐含了哪些前提、你的分歧点和回报来源可能来自哪里。",
        },
        {
            "id": "history-crisis",
            "filename": "06-history-crisis.html",
            "nav_label": "历史与危机",
            "kicker": "第 6 章",
            "title": "公司历史阶段、关键转折与危机档案",
            "deck": "这一章把公司放回时间线里，理解今天的业务形态和市场印象究竟是如何形成的。",
        },
        {
            "id": "investor-lenses",
            "filename": "07-investor-lenses.html",
            "nav_label": "大师视角",
            "kicker": "第 7 章",
            "title": "多框架投资视角",
            "deck": "这一章用不同投资哲学重新审视同一家公司，看哪些框架会买、哪些框架会回避，以及它们分别在核验什么。",
        },
        {
            "id": "sources",
            "filename": "08-sources.html",
            "nav_label": "来源附录",
            "kicker": "第 8 章",
            "title": "来源附录与核验线索",
            "deck": "这一章集中展示来源与引用线索，方便读者顺着原始材料继续追查和交叉核验。",
        },
    ]


def render_tag_row(items: list[str], class_name: str = "tag-chip") -> str:
    tags = [f'<span class="{class_name}">{esc(item)}</span>' for item in items if str(item).strip()]
    if not tags:
        return ""
    return f'<div class="tag-row">{"".join(tags)}</div>'


def render_metrics_strip(metrics: list[tuple[str, str]]) -> str:
    cards = []
    for label, value in metrics:
        text = str(value).strip()
        if not text:
            continue
        cards.append(
            '<article class="metric-card">'
            f'<p class="metric-label">{esc(label)}</p>'
            f'<strong>{esc(text)}</strong>'
            "</article>"
        )
    if not cards:
        return ""
    return f'<section class="metric-strip">{"".join(cards)}</section>'


def render_catalog_cards(page_specs: list[dict[str, str]]) -> str:
    chapter_pages = [page for page in page_specs if page["id"] != "cover"]
    cards = []
    for index, page in enumerate(chapter_pages, start=1):
        cards.append(
            '<li class="toc-item">'
            f'<a class="toc-link" href="{esc(page["filename"])}">'
            f'<span class="toc-index">{index:02d}</span>'
            '<div class="toc-meta">'
            f'<p class="toc-kicker">{esc(page["kicker"])}</p>'
            f'<h3>{esc(page["nav_label"])}</h3>'
            "</div>"
            f'<p class="toc-desc">{esc(page["deck"])}</p>'
            '<span class="toc-cta">进入章节</span>'
            "</a>"
            "</li>"
        )
    return f'<ol class="toc-list">{"".join(cards)}</ol>'


def render_bucket_cards(bucket_counts: list[tuple[str, int]]) -> str:
    cards = []
    for label, count in bucket_counts[:8]:
        cards.append(
            '<article class="bucket-card">'
            f'<p class="metric-label">{esc(label)}</p>'
            f"<strong>{count}</strong>"
            "</article>"
        )
    if not cards:
        return '<p class="muted">未统计到来源分类。</p>'
    return f'<section class="bucket-grid">{"".join(cards)}</section>'


def render_architecture_svg(data: dict[str, Any]) -> str:
    method = normalize_report_method(data)
    info_nodes = [item[:10] for item in method.get("information_collected", [])[:5]]
    if len(info_nodes) < 5:
        info_nodes += ["行业资料", "估值数据", "治理材料"][: 5 - len(info_nodes)]
    module_nodes = [
        "当前状态",
        "业务护城河",
        "行业竞争",
        "管理层执行",
        "财务质量",
        "资本配置",
        "估值市场",
        "历史危机",
    ]
    output_nodes = ["执行摘要", "正文各章", "大师视角", "来源附录"]

    def rect(x: int, y: int, w: int, h: int, title: str, fill: str, stroke: str, subtitle: str = "") -> str:
        title_y = y + 28
        subtitle_y = y + 48
        title_html = f'<text x="{x + 12}" y="{title_y}" class="arch-title">{esc(title)}</text>'
        subtitle_html = (
            f'<text x="{x + 12}" y="{subtitle_y}" class="arch-subtitle">{esc(subtitle)}</text>' if subtitle else ""
        )
        return (
            f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="14" fill="{fill}" stroke="{stroke}" stroke-width="1.4" />'
            + title_html
            + subtitle_html
        )

    pieces = [
        '<svg viewBox="0 0 1180 700" class="architecture-svg" role="img" aria-label="研究架构图">',
        '<defs><marker id="arch-arrow" markerWidth="10" markerHeight="10" refX="7" refY="3" orient="auto"><path d="M0,0 L0,6 L8,3 z" fill="#8fa0b8"/></marker></defs>',
        '<rect x="34" y="78" width="1112" height="112" rx="24" fill="#fcfaf4" stroke="#e3d8c4" stroke-width="1.2"/>',
        '<rect x="34" y="226" width="1112" height="196" rx="24" fill="#fbfdf9" stroke="#d7ddd9" stroke-width="1.2"/>',
        '<rect x="34" y="458" width="1112" height="90" rx="24" fill="#fafcff" stroke="#d9e2ee" stroke-width="1.2"/>',
        '<rect x="34" y="584" width="1112" height="84" rx="24" fill="#fdf8fb" stroke="#ead7e6" stroke-width="1.2"/>',
        '<text x="60" y="106" class="arch-layer">输入资料</text>',
        '<text x="60" y="254" class="arch-layer">研究模块</text>',
        '<text x="60" y="486" class="arch-layer">判断框架</text>',
        '<text x="60" y="612" class="arch-layer">报告输出</text>',
    ]

    input_positions = [(68, 124), (282, 124), (496, 124), (710, 124), (924, 124)]
    for (x, y), label in zip(input_positions, info_nodes, strict=False):
        pieces.append(rect(x, y, 160, 48, label, "#fffaf0", "#dcc9a8"))

    pieces.append(rect(430, 278, 320, 58, "并行研究模块", "#eef7f0", "#caddcf", "分模块研究与统一归并"))
    module_positions = [
        (86, 350), (344, 350), (602, 350), (860, 350),
        (86, 402), (344, 402), (602, 402), (860, 402),
    ]
    for (x, y), label in zip(module_positions, module_nodes, strict=False):
        pieces.append(rect(x, y, 190, 40, label, "#f1faf3", "#d2e1d5"))

    judgment_positions = [(90, 494), (384, 494), (678, 494)]
    judgment_nodes = ["支持点", "风险点", "反证条件与监控点"]
    for (x, y), label in zip(judgment_positions, judgment_nodes, strict=False):
        width = 220 if label != "反证条件与监控点" else 408
        pieces.append(rect(x, y, width, 34, label, "#f2f7fd", "#d5e1ef"))

    output_positions = [(120, 620), (370, 620), (620, 620), (870, 620)]
    for (x, y), label in zip(output_positions, output_nodes, strict=False):
        pieces.append(rect(x, y, 190, 34, label, "#fcf5fb", "#ead7e6"))

    pieces.extend(
        [
            '<path d="M 590 190 L 590 278" class="arch-line-strong" marker-end="url(#arch-arrow)"/>',
            '<path d="M 590 336 L 590 366" class="arch-line-strong"/>',
            '<path d="M 160 366 L 1020 366" class="arch-line"/>',
            '<path d="M 181 366 L 181 350" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 439 366 L 439 350" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 697 366 L 697 350" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 955 366 L 955 350" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 181 366 L 181 402" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 439 366 L 439 402" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 697 366 L 697 402" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 955 366 L 955 402" class="arch-line" marker-end="url(#arch-arrow)"/>',
            '<path d="M 590 442 L 590 494" class="arch-line-strong" marker-end="url(#arch-arrow)"/>',
            '<path d="M 590 528 L 590 620" class="arch-line-strong" marker-end="url(#arch-arrow)"/>',
        ]
    )

    pieces.append(
        '<text x="590" y="34" text-anchor="middle" class="arch-main-title">equity-investment-dossier 研究架构图</text>'
    )
    pieces.append(
        '<text x="590" y="58" text-anchor="middle" class="arch-main-subtitle">先收集资料，再分模块研究，最后收束成当前结论与完整报告</text>'
    )
    pieces.append("</svg>")
    return "".join(pieces)


def render_architecture_window(data: dict[str, Any]) -> str:
    return (
        '<details class="architecture-details" open>'
        '<summary>展开研究架构图，查看这份报告如何从公开资料走到最终判断</summary>'
        '<div class="window-shell">'
        '<div class="window-bar">'
        '<span class="window-dot red"></span>'
        '<span class="window-dot amber"></span>'
        '<span class="window-dot green"></span>'
        '<span class="window-title">equity-investment-dossier / research-architecture</span>'
        '</div>'
        '<div class="window-body">'
        '<p class="window-note">这张图不是正文内容，而是告诉读者：这份报告输入了哪些信息、做了哪些研究模块、如何把材料收束为最终判断。</p>'
        f'{render_architecture_svg(data)}'
        '</div>'
        '</div>'
        '</details>'
    )


def render_flow_diagram() -> str:
    steps = [
        ("01", "资料输入", "读取财报、电话会、访谈、行业与市场材料。"),
        ("02", "模块研究", "拆成业务、行业、管理层、财务、估值、历史等模块。"),
        ("03", "交叉验证", "把支持点、风险点、反证条件和证据线索放到同一框架里对照。"),
        ("04", "投资判断", "最终收束为当前结论、赔率来源、主要错误风险与后续监控点。"),
    ]
    pieces = []
    for num, title, note in steps:
        pieces.append(
            '<article class="guide-stage">'
            '<div class="guide-stage-head">'
            f'<span class="guide-stage-number">{esc(num)}</span>'
            f'<h3>{esc(title)}</h3>'
            "</div>"
            f'<p>{esc(note)}</p>'
            "</article>"
        )
    return f'<section class="guide-sequence">{"".join(pieces)}</section>'


def render_method_card(title: str, value: Any) -> str:
    return (
        '<article class="guide-sheet">'
        f"<h3>{esc(title)}</h3>"
        f"{render_text(value)}"
        "</article>"
    )


def render_cover_signal_rows(rows: list[tuple[str, Any]]) -> str:
    pieces = []
    for label, value in rows:
        if value in ("", None, [], {}):
            continue
        pieces.append(
            '<div class="cover-signal-row">'
            f'<p class="cover-signal-label">{esc(label)}</p>'
            f'<div class="cover-signal-body">{render_text(value)}</div>'
            "</div>"
        )
    if not pieces:
        return ""
    return f'<div class="cover-signal-list">{"".join(pieces)}</div>'


def render_global_nav(page_specs: list[dict[str, str]], current_id: str) -> str:
    links = []
    for page in page_specs:
        classes = "is-current" if page["id"] == current_id else ""
        class_attr = f' class="{classes}"' if classes else ""
        links.append(f'<a href="{esc(page["filename"])}"{class_attr}>{esc(page["nav_label"])}</a>')
    return f'<nav class="report-nav report-nav-global">{"".join(links)}</nav>'


def render_local_nav(sections: list[tuple[str, str, str]]) -> str:
    links = []
    for section_id, nav_label, _ in sections:
        links.append(f'<a href="#{esc(section_id)}">{esc(nav_label)}</a>')
    if not links:
        return ""
    return f'<nav class="section-jump">{"" .join(links)}</nav>'


def render_page_pager(page_specs: list[dict[str, str]], current_id: str) -> str:
    current_index = next((index for index, page in enumerate(page_specs) if page["id"] == current_id), 0)
    prev_page = page_specs[current_index - 1] if current_index > 0 else None
    next_page = page_specs[current_index + 1] if current_index + 1 < len(page_specs) else None
    prev_html = (
        f'<a class="pager-link" href="{esc(prev_page["filename"])}">← {esc(prev_page["nav_label"])}</a>'
        if prev_page
        else '<span class="pager-link muted">已到开头</span>'
    )
    next_html = (
        f'<a class="pager-link" href="{esc(next_page["filename"])}">{esc(next_page["nav_label"])} →</a>'
        if next_page
        else '<span class="pager-link muted">已到结尾</span>'
    )
    return f'<div class="pager">{prev_html}{next_html}</div>'


def render_cover_page(data: dict[str, Any], page_specs: list[dict[str, str]]) -> str:
    meta = data["meta"]
    current_status = data["current_status"]
    brief = normalize_report_brief(data)
    method = normalize_report_method(data)
    read_path = [
        "先看导读，知道这份报告收集了什么、如何形成判断。",
        "再按执行摘要、业务与行业、管理层、财务与资本配置、估值与市场的顺序阅读。",
        "最后用历史、危机、大师视角和来源附录做反向核验。",
    ]
    signal_rows = [
        ("当前结论", brief.get("current_action", "")),
        ("为什么是当前时点", brief.get("why_now", "")),
        ("最容易错在哪", brief.get("main_error_risk", "")),
        ("下一步核验", brief.get("next_checks", [])),
    ]

    return (
        '<section class="cover-hero cover-hero-grid">'
        '<div class="cover-copy">'
        '<p class="cover-report-label">Investment Dossier / 一次性研究报告</p>'
        '<p class="page-kicker">研究对象</p>'
        f'<h1>{esc(meta.get("company_name", "未知公司"))} <span>{esc(meta.get("ticker", ""))}</span></h1>'
        f'<div class="hero-meta">{badge(meta.get("conclusion", "未定"), "conclusion")}<span>研究日期：{esc(meta.get("research_date", ""))}</span><span>状态日期：{esc(current_status.get("as_of", ""))}</span><span>交易所：{esc(meta.get("exchange", ""))}</span><span>分析者：{esc(meta.get("analyst", "Codex"))}</span></div>'
        f'<p class="cover-abstract">{nl2br(meta.get("thesis", ""))}</p>'
        f'<p class="cover-note">{nl2br(brief.get("what_company_is", method.get("scope_statement", "")))}</p>'
        f'{render_tag_row(method.get("information_collected", []))}'
        '</div>'
        '<aside class="cover-side">'
        '<article class="cover-panel">'
        '<h3>一眼看懂当前判断</h3>'
        f'{render_cover_signal_rows(signal_rows)}'
        '</article>'
        '<article class="cover-panel">'
        '<h3>这份报告做了什么</h3>'
        f'<p>{nl2br(method.get("scope_statement", ""))}</p>'
        f'{render_text(read_path)}'
        '</article>'
        '</aside>'
        '</section>'
        + render_architecture_window(data)
        + '<section class="report-note-box cover-note-box">'
        '<h2>目录</h2>'
        '<p>下面是整份报告的书签目录。阅读顺序已经按研究逻辑排好，你可以顺着往下读，也可以直接跳到关心的章节。</p>'
        '</section>'
        + render_catalog_cards(page_specs)
    )


def render_guide_page(data: dict[str, Any]) -> str:
    method = normalize_report_method(data)
    read_order = [
        "先看执行摘要，理解当前结论、主要错误风险和赔率来自哪里。",
        "再看业务、管理层、财务与估值章节，判断 thesis 是否站得住。",
        "最后再回到历史、危机、大师视角和来源，做反向核验。",
    ]
    return (
        render_flow_diagram()
        + '<section class="guide-grid">'
        + render_method_card("本报告收集了什么", method.get("information_collected", []))
        + render_method_card("本报告做了哪些调研", method.get("research_modules", []))
        + render_method_card("如何一步步形成判断", method.get("decision_steps", []))
        + render_method_card("这份报告怎么读", read_order)
        + "</section>"
        + '<section class="report-note-box">'
        '<h2>主要资料类型</h2>'
        '<p>这里不展示机械的数量卡，只说明这份报告主要依赖了哪些类型的公开资料。</p>'
        f'{render_tag_row([label for label, _ in method.get("bucket_counts", [])])}'
        '</section>'
        + '<section class="report-note-box">'
        '<h2>主要局限</h2>'
        f'{render_text(method.get("limitations", []))}'
        '</section>'
    )


def render_summary_questions(data: dict[str, Any]) -> str:
    brief = normalize_report_brief(data)
    cards = [
        ("当前适不适合出手", brief.get("current_action", "")),
        ("为什么是当前时点", brief.get("why_now", "")),
        ("我最可能错在哪", brief.get("main_error_risk", "")),
        ("赔率来自哪里", brief.get("payoff_sources", [])),
    ]
    html_cards = []
    for title, value in cards:
        html_cards.append(
            '<article class="question-card">'
            f"<h3>{esc(title)}</h3>"
            f"{render_text(value)}"
            "</article>"
        )
    return f'<section class="question-grid">{"".join(html_cards)}</section>'


def build_chapter_sections(data: dict[str, Any], chapter_id: str) -> tuple[str, list[tuple[str, str, str]]]:
    if chapter_id == "summary":
        intro = render_summary_questions(data) + render_summary(data, report_label="完整研究报告")
        sections = [
            ("current-status", "当前状态", render_current_status(data)),
            ("thesis", "当前结论与时点理由", render_investment_case(data)),
            ("debate", "多空观点", render_debate(data)),
            ("open-questions", "待验证问题", render_open_questions(data)),
        ]
        return intro, sections
    if chapter_id == "business-industry":
        intro = '<section class="report-note-box"><h2>这一章看什么</h2><p>先理解公司赚钱结构和护城河，再判断行业位置和竞争关系。只有业务质量与行业位置都站得住，后面的估值才有意义。</p></section>'
        sections = [
            ("business-snapshot", "业务快照", render_business_snapshot(data)),
            ("business-quality", "业务深挖", render_business_quality(data)),
            ("industry", "行业与竞争", render_industry(data)),
        ]
        return intro, sections
    if chapter_id == "management-execution":
        intro = '<section class="report-note-box"><h2>这一章看什么</h2><p>管理层章节不是人物介绍，而是用过往任期、公开表态和结果复盘去判断可信度、执行力和治理风险。</p></section>'
        sections = [
            ("management", "管理层与执行复盘", render_management(data)),
        ]
        return intro, sections
    if chapter_id == "financials-capital":
        intro = '<section class="report-note-box"><h2>这一章看什么</h2><p>这里重点看利润质量、现金流、资本支出和资本配置，判断公司是不是“故事很强、报表很脆”。</p></section>'
        sections = [
            ("financials", "财务质量", render_financials(data)),
            ("capital-allocation", "资本配置", render_capital_allocation(data)),
        ]
        return intro, sections
    if chapter_id == "valuation-market":
        intro = '<section class="report-note-box"><h2>这一章看什么</h2><p>这一章专门回答市场在交易什么、当前估值要求什么前提、你的分歧点在哪里，以及潜在赔率来自什么地方。</p></section>'
        sections = [
            ("valuation", "估值", render_valuation(data)),
            ("market-behavior", "股价与市场行为", render_market_behavior(data)),
        ]
        return intro, sections
    if chapter_id == "history-crisis":
        intro = '<section class="report-note-box"><h2>这一章看什么</h2><p>历史和危机部分帮助你把今天的公司放回时间轴里，避免只盯着当前季度而忽略长期演化。</p></section>'
        sections = [
            ("history", "公司时间线与阶段地图", render_company_history(data)),
            ("crisis", "危机档案", render_crisis_archive(data)),
        ]
        return intro, sections
    if chapter_id == "investor-lenses":
        intro = '<section class="report-note-box"><h2>这一章看什么</h2><p>这一章不是主结论，而是把同一家公司放进不同投资框架里做补充检验，看哪些前提最关键、哪些框架天然不接受这家公司。</p></section>'
        sections = [
            ("investor-lenses", "多框架投资视角", render_investor_lenses(data)),
        ]
        return intro, sections
    if chapter_id == "sources":
        bucket_counts = source_bucket_counts(data)
        intro = (
            '<section class="report-note-box"><h2>这一章看什么</h2><p>来源附录负责给出继续追查的线索，而不是重复正文结论。读者可以从这里直接回到原始材料。</p></section>'
            + render_bucket_cards(bucket_counts)
        )
        sections = [
            ("sources", "来源附录", render_sources(data)),
        ]
        return intro, sections
    return "", []


def build_report_css() -> str:
    return """
    :root {
      --paper: #e9dfd0;
      --paper-deep: #e0d4c2;
      --panel: rgba(255, 252, 246, 0.96);
      --panel-strong: #fffdfa;
      --ink: #20252f;
      --muted: #5d6875;
      --line: #d3c7b8;
      --line-strong: #b7a78f;
      --accent: #153b6b;
      --accent-strong: #0e2d52;
      --accent-soft: #e8eef7;
      --warn: #8b5b15;
      --danger: #8a3d32;
      --mono: "SF Mono", "Menlo", "Monaco", "Courier New", monospace;
    }
    * { box-sizing: border-box; }
    html { scroll-behavior: smooth; }
    body {
      margin: 0;
      color: var(--ink);
      font-family: "PingFang SC", "Hiragino Sans GB", "Microsoft YaHei", sans-serif;
      background:
        radial-gradient(circle at top left, rgba(255, 255, 255, 0.74), transparent 34%),
        linear-gradient(180deg, #efe7da 0%, #e8dece 52%, #e2d8ca 100%);
      line-height: 1.68;
      position: relative;
    }
    body::before {
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.34;
      background:
        linear-gradient(180deg, rgba(255, 255, 255, 0.18), rgba(255, 255, 255, 0)),
        repeating-linear-gradient(90deg, transparent 0 119px, rgba(21, 59, 107, 0.035) 119px 120px);
    }
    a { color: var(--accent); }
    .page-shell {
      position: relative;
      z-index: 1;
      max-width: 1600px;
      margin: 0 auto;
      padding: 1.1rem 1.8rem 3rem;
    }
    .topbar {
      position: sticky;
      top: 0;
      z-index: 30;
      background: linear-gradient(to bottom, rgba(239, 231, 218, 0.98), rgba(239, 231, 218, 0.9));
      backdrop-filter: blur(8px);
      padding: 0.35rem 0 0.9rem;
    }
    .report-nav {
      display: flex;
      gap: 0.45rem;
      overflow-x: auto;
      white-space: nowrap;
      padding: 0.25rem 0 0.18rem;
      border-bottom: 1px solid #c9baa3;
    }
    .report-nav a {
      text-decoration: none;
      padding: 0.5rem 0.66rem 0.58rem;
      border-bottom: 2px solid transparent;
      color: var(--muted);
      font-size: 0.84rem;
      font-family: var(--mono);
      letter-spacing: 0.04em;
    }
    .report-nav a:hover,
    .report-nav a.is-current {
      color: var(--ink);
      border-color: #9fb4cf;
    }
    .page-hero,
    .cover-hero {
      position: relative;
      overflow: hidden;
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98) 0%, rgba(255, 251, 244, 0.96) 100%);
      border: 1px solid var(--line);
      border-top: 4px solid var(--accent);
      padding: 1.35rem 1.45rem 1.45rem;
      box-shadow: 0 14px 28px rgba(31, 37, 47, 0.06);
      margin-top: 0.55rem;
    }
    .page-hero::before,
    .cover-hero::before {
      content: "";
      position: absolute;
      inset: 0 0 0 auto;
      width: 36%;
      background: linear-gradient(135deg, rgba(21, 59, 107, 0.06), transparent 58%);
      pointer-events: none;
    }
    .page-hero.page-hero-cover {
      padding: 1rem 1.2rem 1.05rem;
    }
    .page-kicker,
    .chapter-kicker {
      margin: 0 0 0.45rem;
      letter-spacing: 0.08em;
      font-size: 0.75rem;
      color: var(--muted);
      font-family: var(--mono);
    }
    h1, h2, h3, h4 {
      font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
      margin-top: 0;
      color: #182230;
      font-weight: 700;
    }
    .page-hero h1,
    .cover-hero h1 {
      font-size: clamp(2rem, 3.2vw, 3rem);
      margin-bottom: 0.38rem;
      line-height: 1.14;
    }
    .cover-hero h1 span {
      font-size: 0.42em;
      color: var(--muted);
      margin-left: 0.5rem;
      font-family: var(--mono);
    }
    .page-deck,
    .cover-abstract,
    .cover-note {
      margin: 0.2rem 0 0;
      font-size: 1rem;
      line-height: 1.75;
    }
    .cover-note {
      color: var(--muted);
    }
    main > section + section,
    main > details + section,
    main > section + details,
    main > details + details {
      margin-top: 1.2rem;
    }
    details {
      display: block;
    }
    .metric-strip,
    .bucket-grid,
    .question-grid {
      display: grid;
      gap: 0.95rem;
      margin-top: 1rem;
    }
    .metric-strip {
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
    }
    .bucket-grid {
      grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
    }
    .question-grid {
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }
    .guide-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 1rem;
    }
    .metric-card,
    .bucket-card,
    .question-card,
    .guide-sheet,
    .report-note-box {
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(252, 248, 241, 0.98));
      border: 1px solid var(--line);
      border-top: 3px solid #dfd1bc;
      padding: 1rem 1.05rem;
      min-width: 0;
    }
    .metric-label {
      margin: 0 0 0.25rem;
      color: var(--muted);
      font-size: 0.76rem;
      letter-spacing: 0.04em;
      font-family: var(--mono);
    }
    .metric-card strong,
    .bucket-card strong {
      display: block;
      font-size: 1.2rem;
      line-height: 1.2;
    }
    .report-note-box h2 {
      margin-bottom: 0.45rem;
      font-size: 1.15rem;
    }
    .report-note-box {
      box-shadow: 0 10px 22px rgba(31, 37, 47, 0.04);
    }
    .tag-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.5rem;
      margin-top: 0.85rem;
    }
    .tag-chip {
      display: inline-flex;
      align-items: center;
      padding: 0.22rem 0.56rem;
      border-radius: 999px;
      background: #f7f7f4;
      border: 1px solid #ddd4c6;
      color: var(--muted);
      font-size: 0.76rem;
      font-family: var(--mono);
    }
    .cover-hero-grid {
      display: grid;
      grid-template-columns: minmax(0, 1.55fr) minmax(360px, 0.95fr);
      gap: 1.25rem;
      align-items: start;
    }
    .cover-copy {
      display: grid;
      gap: 0.5rem;
    }
    .cover-report-label {
      margin: 0;
      color: var(--accent);
      font-family: var(--mono);
      font-size: 0.8rem;
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }
    .cover-side {
      display: grid;
      gap: 1rem;
    }
    .cover-panel {
      border: 1px solid var(--line);
      background: rgba(247, 248, 249, 0.78);
      padding: 1rem 1.05rem;
      box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.6);
    }
    .cover-panel h3 {
      margin-bottom: 0.55rem;
      font-size: 1.02rem;
    }
    .cover-signal-list {
      display: grid;
      gap: 0.75rem;
    }
    .cover-signal-row {
      padding-top: 0.72rem;
      border-top: 1px solid rgba(183, 167, 143, 0.5);
    }
    .cover-signal-row:first-child {
      padding-top: 0;
      border-top: none;
    }
    .cover-signal-label {
      margin: 0 0 0.2rem;
      color: var(--muted);
      font-size: 0.76rem;
      font-family: var(--mono);
      letter-spacing: 0.06em;
    }
    .cover-signal-body p,
    .cover-signal-body ul {
      margin-bottom: 0;
    }
    .cover-panel p:last-child,
    .cover-panel ul:last-child {
      margin-bottom: 0;
    }
    .architecture-details {
      border: 1px solid var(--line);
      background: rgba(255, 252, 246, 0.95);
      box-shadow: 0 12px 26px rgba(31, 37, 47, 0.05);
    }
    .architecture-details summary {
      list-style: none;
      cursor: pointer;
      color: var(--accent-strong);
      font-weight: 700;
      letter-spacing: 0.02em;
      padding: 0.92rem 1.05rem;
      font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
    }
    .architecture-details summary::-webkit-details-marker {
      display: none;
    }
    .architecture-details summary::before {
      content: "▸";
      display: inline-block;
      margin-right: 0.45rem;
      transition: transform 140ms ease;
    }
    .architecture-details[open] summary::before {
      transform: rotate(90deg);
    }
    .window-shell {
      border-top: 1px solid var(--line);
      background: #fffdf8;
      overflow: hidden;
    }
    .window-bar {
      display: flex;
      align-items: center;
      gap: 0.45rem;
      padding: 0.62rem 0.75rem;
      background: linear-gradient(180deg, #f7f0e3 0%, #efe5d3 100%);
      border-bottom: 1px solid #d7cfbf;
    }
    .window-dot {
      width: 0.72rem;
      height: 0.72rem;
      border-radius: 999px;
      display: inline-block;
    }
    .window-dot.red {
      background: #d97166;
    }
    .window-dot.amber {
      background: #d9b25f;
    }
    .window-dot.green {
      background: #7ba371;
    }
    .window-title {
      margin-left: 0.3rem;
      color: var(--muted);
      font-size: 0.84rem;
      font-family: var(--mono);
    }
    .window-body {
      padding: 0.95rem 1rem 1.05rem;
      background: radial-gradient(circle at top left, rgba(255, 255, 255, 0.88), rgba(250, 247, 240, 0.95));
    }
    .window-note {
      margin: 0 0 0.75rem;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .architecture-svg {
      display: block;
      width: 100%;
      height: auto;
      background: #fffdf8;
      border: 1px solid #e5ddd0;
    }
    .arch-main-title {
      font-family: "Avenir Next Condensed", "DIN Condensed", "PingFang SC", sans-serif;
      font-size: 28px;
      fill: #1f2d3d;
      font-weight: 700;
    }
    .arch-main-subtitle {
      font-size: 13px;
      fill: #667384;
    }
    .arch-layer {
      font-size: 16px;
      fill: #455569;
      font-weight: 700;
    }
    .arch-title {
      font-size: 14px;
      fill: #223042;
      font-weight: 700;
    }
    .arch-subtitle {
      font-size: 12px;
      fill: #6a7688;
    }
    .arch-line,
    .arch-line-strong {
      fill: none;
      stroke: #99a7bc;
      stroke-width: 1.6;
      stroke-linecap: round;
    }
    .arch-line-strong {
      stroke: #6f809a;
      stroke-width: 2.1;
    }
    .toc-list {
      list-style: none;
      padding: 0;
      margin: 0;
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(251, 247, 240, 0.98));
      border: 1px solid var(--line);
      box-shadow: 0 12px 24px rgba(31, 37, 47, 0.04);
    }
    .toc-item + .toc-item {
      border-top: 1px solid var(--line);
    }
    .toc-link {
      display: grid;
      grid-template-columns: 78px 190px minmax(0, 1fr) auto;
      gap: 1.05rem;
      align-items: center;
      padding: 1.05rem 1.15rem;
      text-decoration: none;
      color: inherit;
      transition: background 140ms ease;
    }
    .toc-link:hover {
      background: rgba(255, 255, 255, 0.62);
    }
    .toc-index {
      font-family: var(--mono);
      color: var(--accent);
      font-size: 0.92rem;
      letter-spacing: 0.06em;
    }
    .toc-meta h3 {
      margin: 0;
      font-size: 1.06rem;
    }
    .toc-kicker {
      margin: 0 0 0.14rem;
      color: var(--muted);
      font-size: 0.75rem;
      letter-spacing: 0.05em;
      font-family: var(--mono);
    }
    .toc-desc {
      margin: 0;
      color: var(--muted);
      line-height: 1.65;
    }
    .toc-cta {
      color: var(--accent);
      font-size: 0.88rem;
      font-weight: 700;
      white-space: nowrap;
    }
    .guide-sequence {
      display: grid;
      grid-template-columns: repeat(4, minmax(0, 1fr));
      gap: 1rem;
    }
    .guide-stage {
      position: relative;
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(252, 248, 241, 0.98));
      border: 1px solid var(--line);
      border-top: 3px solid #cfd8e5;
      padding: 1rem 1rem 1.08rem;
      box-shadow: 0 10px 20px rgba(31, 37, 47, 0.04);
    }
    .guide-stage-head {
      display: flex;
      align-items: center;
      gap: 0.7rem;
      margin-bottom: 0.55rem;
    }
    .guide-stage-number {
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 1.95rem;
      height: 1.95rem;
      border-radius: 999px;
      background: var(--accent-soft);
      color: var(--accent);
      font-weight: 700;
      font-size: 0.8rem;
      font-family: var(--mono);
      flex: 0 0 auto;
    }
    .guide-stage h3 {
      margin: 0;
      font-size: 1rem;
    }
    .guide-stage p {
      margin: 0;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .guide-sheet h3 {
      margin-bottom: 0.55rem;
      font-size: 1.06rem;
    }
    .guide-sheet p:last-child,
    .guide-sheet ul:last-child {
      margin-bottom: 0;
    }
    .section-jump {
      display: flex;
      gap: 0.35rem;
      overflow-x: auto;
      white-space: nowrap;
      margin: 0.95rem 0;
      padding-bottom: 0.1rem;
      border-bottom: 1px solid #d8d1c7;
    }
    .section-jump a {
      text-decoration: none;
      padding: 0.45rem 0.6rem;
      color: var(--muted);
      font-size: 0.88rem;
      border-bottom: 2px solid transparent;
    }
    .section-jump a:hover {
      color: var(--ink);
      border-color: #b9c6d6;
    }
    .pager {
      display: flex;
      justify-content: space-between;
      gap: 0.8rem;
      margin-top: 1.1rem;
      padding-top: 0.9rem;
      border-top: 1px solid var(--line);
    }
    .pager-link {
      color: var(--accent);
      text-decoration: none;
      font-weight: 600;
    }
    .hero {
      position: relative;
      overflow: hidden;
      margin-top: 1.3rem;
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(252, 248, 241, 0.98));
      border: 1px solid var(--line);
      padding: 1.18rem 1.35rem 1.22rem;
      display: grid;
      grid-template-columns: minmax(0, 2.1fr) minmax(340px, 1fr);
      gap: 1rem 1.3rem;
      box-shadow: 0 12px 24px rgba(31, 37, 47, 0.04);
    }
    .hero::before {
      content: "";
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 4px;
      background: linear-gradient(90deg, rgba(21, 59, 107, 0.92), rgba(21, 59, 107, 0.18) 44%, rgba(21, 59, 107, 0.04));
      opacity: 0.58;
    }
    .eyebrow {
      margin: 0 0 0.5rem;
      text-transform: uppercase;
      letter-spacing: 0.14em;
      font-size: 0.72rem;
      color: var(--muted);
    }
    h1 span {
      font-size: 0.48em;
      color: var(--muted);
      margin-left: 0.35rem;
    }
    .hero-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem 0.8rem;
      margin-bottom: 0.7rem;
      color: var(--muted);
      font-size: 0.84rem;
      font-family: var(--mono);
    }
    .hero-thesis {
      font-size: 1rem;
      line-height: 1.75;
      margin: 0;
    }
    .hero-stats {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 0.35rem;
    }
    .stat-card {
      padding: 0.65rem 0.7rem;
      background: #fbfcfd;
      border: 1px solid var(--line);
    }
    .stat-label {
      display: block;
      color: var(--muted);
      font-size: 0.75rem;
      margin-bottom: 0.2rem;
    }
    .stat-card strong {
      display: block;
      font-size: 1.05rem;
      color: var(--ink);
      margin-bottom: 0.15rem;
    }
    .stat-note {
      margin: 0;
      font-size: 0.75rem;
      color: var(--muted);
    }
    .summary-grid {
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 0.95rem;
      margin-top: 1rem;
    }
    .summary-grid.compact {
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }
    .panel {
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(252, 248, 241, 0.98));
      border: 1px solid var(--line);
      border-top: 3px solid #dfd1bc;
      padding: 0.95rem 1rem;
    }
    .panel.danger {
      background: #fff8f6;
    }
    .panel.neutral {
      background: #fffbf3;
    }
    .compact-panel p {
      margin-bottom: 0;
    }
    .report-section {
      scroll-margin-top: 4.5rem;
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(252, 248, 241, 0.98));
      border: 1px solid var(--line);
      box-shadow: 0 12px 24px rgba(31, 37, 47, 0.04);
    }
    .section-title {
      padding: 1rem 1.2rem 0.85rem;
      font-family: "Songti SC", "STSong", "Noto Serif CJK SC", serif;
      font-size: 1.2rem;
      background: #f6f0e7;
      border-bottom: 1px solid var(--line);
    }
    .section-body {
      padding: 1.05rem 1.2rem 1.3rem;
    }
    .subheading {
      margin: 1rem 0 0.55rem;
      font-size: 1rem;
    }
    .report-columns {
      display: block;
      margin-bottom: 0.9rem;
    }
    .report-columns-tight {
      margin-bottom: 0.7rem;
    }
    .report-block,
    .report-note {
      padding-top: 0.62rem;
      border-top: 2px solid #dde1e8;
      background: transparent;
      margin-bottom: 1rem;
    }
    .report-block h3,
    .report-note h4 {
      margin-bottom: 0.3rem;
      font-size: 1rem;
    }
    .report-note p:last-child,
    .report-block p:last-child {
      margin-bottom: 0;
    }
    .card-grid {
      display: block;
    }
    .revenue-breakdown-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 0.95rem;
    }
    .revenue-breakdown-grid .entry {
      margin: 0;
      padding: 1rem 1rem 1.08rem;
      border: 1px solid var(--line);
      background: linear-gradient(180deg, rgba(255, 253, 248, 0.98), rgba(252, 248, 241, 0.98));
      border-top: 3px solid #dfd1bc;
    }
    .revenue-breakdown-grid .entry:first-child {
      padding-top: 1rem;
    }
    .entry {
      padding: 1.05rem 0 1.2rem;
      border-top: 1px solid var(--line);
    }
    .entry:first-child {
      padding-top: 0;
      border-top: none;
    }
    .entry-head {
      display: block;
      margin-bottom: 0.45rem;
    }
    .entry h4 {
      margin-bottom: 0.18rem;
      font-size: 1.08rem;
      line-height: 1.35;
      font-weight: 700;
      color: #182b43;
    }
    .card-subtitle {
      margin: 0 0 0.5rem;
      color: var(--muted);
      font-size: 0.82rem;
    }
    .card-meta {
      display: flex;
      flex-wrap: wrap;
      gap: 0.35rem;
      margin: 0.28rem 0 0.2rem;
      align-items: center;
    }
    .badge {
      display: inline-flex;
      align-items: center;
      padding: 0.12rem 0.42rem;
      border-radius: 999px;
      font-size: 0.72rem;
      background: var(--accent-soft);
      color: var(--accent);
      border: 1px solid #d7e3f6;
      font-family: var(--mono);
    }
    .badge.conclusion {
      background: #e7eef8;
      font-weight: 700;
    }
    .badge.result {
      background: #fff5e8;
      color: var(--warn);
      border-color: #f0dfbf;
    }
    .badge.evidence {
      background: #f1f4f9;
      color: #374151;
    }
    .badge.tag {
      background: #f8fafc;
    }
    .entry-body p:first-child {
      margin-top: 0;
    }
    .definition-list {
      display: grid;
      grid-template-columns: 92px minmax(0, 1fr);
      gap: 0.38rem 0.85rem;
      margin: 0;
    }
    .definition-list dt {
      color: var(--muted);
      font-size: 0.76rem;
      font-weight: 700;
      line-height: 1.35;
      letter-spacing: 0.04em;
      padding-top: 0.12rem;
    }
    .definition-list dd {
      margin: 0;
      font-size: 0.97rem;
      line-height: 1.6;
      padding-bottom: 0.24rem;
    }
    .definition-list dd p {
      margin: 0;
    }
    .metric-pill-row {
      display: flex;
      flex-wrap: wrap;
      gap: 0.45rem;
      margin: 0.05rem 0 0.55rem;
    }
    .metric-pill {
      display: inline-flex;
      align-items: baseline;
      gap: 0.32rem;
      padding: 0.2rem 0.55rem;
      border-radius: 999px;
      border: 1px solid #dde4ed;
      background: #f8fafc;
    }
    .metric-pill-label {
      color: var(--muted);
      font-size: 0.7rem;
      font-weight: 700;
      letter-spacing: 0.04em;
      font-family: var(--mono);
    }
    .metric-pill-value {
      color: var(--ink);
      font-size: 0.86rem;
      font-weight: 700;
    }
    .entry-note {
      margin: 0.1rem 0 0;
      line-height: 1.68;
    }
    .bullet-list,
    .check-list {
      margin: 0.1rem 0 0 1.1rem;
      padding: 0;
      line-height: 1.6;
    }
    .check-list li + li,
    .bullet-list li + li {
      margin-top: 0.4rem;
    }
    .source-strip {
      margin-top: 0.5rem;
      color: var(--muted);
      font-size: 0.84rem;
      line-height: 1.6;
    }
    .source-label {
      color: var(--muted);
      font-weight: 600;
      margin-right: 0.18rem;
    }
    .source-link {
      color: var(--accent);
      text-decoration: none;
      border-bottom: 1px solid #cbd7e6;
    }
    .source-link.missing {
      color: var(--danger);
      border-bottom-color: #efcbc8;
    }
    .table-wrap {
      overflow-x: auto;
      margin-bottom: 0.95rem;
    }
    .report-table {
      width: 100%;
      border-collapse: collapse;
      background: #fff;
      font-size: 0.93rem;
    }
    .report-table thead th {
      text-align: left;
      padding: 0.66rem 0.72rem;
      background: #f7f7f3;
      border-bottom: 1.5px solid #9ba4b1;
      font-weight: 700;
      white-space: nowrap;
    }
    .report-table tbody td {
      padding: 0.66rem 0.72rem;
      border-bottom: 1px solid var(--line);
      vertical-align: top;
    }
    .report-table.dense thead th,
    .report-table.dense tbody td {
      padding: 0.52rem 0.62rem;
      font-size: 0.9rem;
    }
    .visual-block {
      margin: 0.2rem 0 1rem;
    }
    .visual-note {
      margin: 0.2rem 0 0.8rem;
      color: var(--muted);
      font-size: 0.9rem;
    }
    .history-era-overview {
      margin: 0;
    }
    .history-era-card {
      display: grid;
      grid-template-columns: 42px minmax(0, 1fr);
      column-gap: 0.8rem;
      padding: 0.72rem 0 0.78rem;
      border-top: 1px solid var(--line);
    }
    .history-era-card:first-child {
      padding-top: 0;
      border-top: none;
    }
    .history-era-index {
      margin: 0.08rem 0 0;
      color: #8e7a58;
      font-size: 0.78rem;
      font-variant-numeric: tabular-nums;
      letter-spacing: 0.06em;
    }
    .history-era-head {
      margin-bottom: 0.08rem;
    }
    .history-era-head h4 {
      margin-bottom: 0;
      font-size: 0.98rem;
    }
    .history-era-meta {
      margin: 0;
      color: var(--muted);
      font-size: 0.82rem;
    }
    .history-era-summary {
      margin: 0.18rem 0 0;
      color: #344256;
      font-size: 0.92rem;
      line-height: 1.6;
    }
    .history-timeline {
      --history-date-col: 118px;
      --history-rail-col: 34px;
      position: relative;
      margin: 0.2rem 0 0;
    }
    .history-timeline::before {
      content: "";
      position: absolute;
      top: 0.35rem;
      bottom: 0.35rem;
      left: calc(var(--history-date-col) + (var(--history-rail-col) / 2) - 1px);
      width: 2px;
      background: linear-gradient(180deg, #d7e0ea 0%, #bcc8d8 100%);
    }
    .history-timeline-item,
    .history-era-marker {
      position: relative;
      display: grid;
      grid-template-columns: var(--history-date-col) var(--history-rail-col) minmax(0, 1fr);
      gap: 0.9rem;
      padding: 0 0 0.95rem;
    }
    .history-date-lane {
      padding-top: 0.12rem;
      text-align: right;
    }
    .history-event-date,
    .history-era-marker-range {
      margin: 0;
      color: var(--muted);
      font-size: 0.86rem;
      font-variant-numeric: tabular-nums;
    }
    .history-rail {
      position: relative;
      display: flex;
      justify-content: center;
    }
    .history-event-dot,
    .history-era-dot {
      position: relative;
      z-index: 1;
      margin-top: 0.3rem;
      border-radius: 999px;
      border: 2px solid #fff;
      box-shadow: 0 0 0 4px #f6f2e8;
    }
    .history-event-dot {
      width: 12px;
      height: 12px;
      background: var(--accent);
    }
    .history-era-dot {
      width: 16px;
      height: 16px;
      background: var(--warn);
    }
    .history-event-card,
    .history-era-marker-card {
      border: 1px solid var(--line);
      padding: 0.85rem 0.95rem;
      min-width: 0;
    }
    .history-event-card {
      background: #fbfcfd;
    }
    .history-era-marker-card {
      background: #f8f3e8;
      border-color: #dcc9a8;
    }
    .history-event-card h4,
    .history-era-marker-card h4 {
      margin-bottom: 0.3rem;
      font-size: 1rem;
    }
    .history-marker-kicker {
      margin: 0 0 0.2rem;
      color: var(--muted);
      font-size: 0.76rem;
      letter-spacing: 0.04em;
    }
    .history-marker-summary {
      margin: 0.22rem 0 0;
    }
    .history-marker-extra {
      margin: 0.38rem 0 0;
      color: var(--muted);
      font-size: 0.9rem;
    }
    .history-event-notes {
      margin-top: 0.45rem;
      padding-top: 0.42rem;
      border-top: 1px dashed #d6dee8;
    }
    .history-event-notes p {
      margin: 0.2rem 0 0;
      color: var(--muted);
      font-size: 0.92rem;
    }
    .report-svg {
      width: 100%;
      height: auto;
      display: block;
      border: 1px solid var(--line);
      background: #fff;
    }
    .reference-list {
      list-style: none;
      padding: 0;
      margin: 0;
    }
    .reference-item {
      display: flex;
      gap: 0.7rem;
      padding: 0.45rem 0;
      border-top: 1px solid var(--line);
    }
    .reference-item:first-child {
      border-top: none;
      padding-top: 0;
    }
    .reference-number {
      flex: 0 0 2.4rem;
      color: var(--muted);
      font-variant-numeric: tabular-nums;
    }
    .reference-body {
      min-width: 0;
    }
    .reference-line {
      margin: 0;
      line-height: 1.65;
    }
    .reference-title {
      font-weight: 700;
    }
    .reference-meta,
    .reference-note {
      color: var(--muted);
      font-size: 0.9rem;
    }
    .reference-sep {
      color: var(--muted);
      font-size: 0.88rem;
    }
    .reference-link {
      color: var(--accent);
      font-size: 0.9rem;
    }
    footer {
      padding: 1.1rem 0 1.3rem;
      color: var(--muted);
      font-size: 0.82rem;
      font-family: var(--mono);
    }
    .muted {
      color: var(--muted);
    }
    @media (max-width: 1120px) {
      .cover-hero-grid {
        grid-template-columns: 1fr;
      }
      .toc-link {
        grid-template-columns: 78px 170px minmax(0, 1fr);
      }
      .toc-cta {
        grid-column: 3;
      }
      .guide-sequence {
        grid-template-columns: repeat(2, minmax(0, 1fr));
      }
      .guide-grid {
        grid-template-columns: 1fr;
      }
      .hero {
        grid-template-columns: 1fr;
      }
      .summary-grid,
      .summary-grid.compact {
        grid-template-columns: 1fr;
      }
    }
    @media (max-width: 760px) {
      .page-shell {
        padding: 0.75rem 0.8rem 2rem;
      }
      .toc-link {
        grid-template-columns: 1fr;
        gap: 0.45rem;
      }
      .toc-cta {
        grid-column: auto;
      }
      .guide-sequence {
        grid-template-columns: 1fr;
      }
      .hero-stats {
        grid-template-columns: 1fr;
      }
      .history-timeline {
        --history-date-col: 0px;
        --history-rail-col: 24px;
      }
      .history-timeline::before {
        left: 11px;
      }
      .history-era-card {
        grid-template-columns: 34px minmax(0, 1fr);
        column-gap: 0.65rem;
      }
      .history-timeline-item,
      .history-era-marker {
        grid-template-columns: var(--history-rail-col) minmax(0, 1fr);
        gap: 0.7rem;
      }
      .history-date-lane {
        grid-column: 2;
        text-align: left;
        padding-top: 0;
        margin-bottom: -0.15rem;
      }
      .history-rail {
        grid-row: 1 / span 2;
        grid-column: 1;
      }
      .history-event-card,
      .history-era-marker-card {
        grid-column: 2;
      }
      .history-event-dot,
      .history-era-dot {
        margin-top: 0.15rem;
      }
      .reference-item {
        display: block;
      }
      .reference-number {
        display: inline-block;
        margin-bottom: 0.3rem;
      }
    }
    """


def build_report_shell(
    *,
    data: dict[str, Any],
    input_path: Path,
    page_specs: list[dict[str, str]],
    current_id: str,
    title: str,
    kicker: str,
    deck: str,
    body_html: str,
) -> str:
    meta = data["meta"]
    current_status = data["current_status"]
    nav_html = render_global_nav(page_specs, current_id)
    pager_html = render_page_pager(page_specs, current_id)
    hero_html = ""
    if current_id != "cover":
        hero_html = (
            '<section class="page-hero">'
            f'<p class="page-kicker">{esc(kicker)}</p>'
            f'<h1>{esc(title)}</h1>'
            '<div class="hero-meta">'
            f'{badge(meta.get("conclusion", "未定"), "conclusion")}'
            f'<span>研究日期：{esc(meta.get("research_date", ""))}</span>'
            f'<span>状态日期：{esc(current_status.get("as_of", ""))}</span>'
            f'<span>交易所：{esc(meta.get("exchange", ""))}</span>'
            f'<span>分析者：{esc(meta.get("analyst", "Codex"))}</span>'
            "</div>"
            f'<p class="page-deck">{nl2br(deck)}</p>'
            "</section>"
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(meta.get('company_name', '股票研究报告'))} - {esc(title)}</title>
  <style>
    {build_report_css()}
  </style>
</head>
<body>
  <div class="page-shell">
    <div class="topbar">
      {nav_html}
    </div>
    <main>
      {hero_html}
      {body_html}
      {pager_html}
      <footer>
        <p>输入文件：{esc(str(input_path))}</p>
        <p>说明：本报告基于公开资料完成一次性调研，输出为多页网页研究报告。</p>
      </footer>
    </main>
  </div>
</body>
</html>
"""


def build_multipage_report(data: dict[str, Any], input_path: Path, cover_filename: str = "index.html") -> dict[str, str]:
    page_specs = build_report_page_specs(cover_filename)
    pages: dict[str, str] = {}

    for page in page_specs:
        page_id = page["id"]
        if page_id == "cover":
            body_html = render_cover_page(data, page_specs)
        elif page_id == "guide":
            body_html = render_guide_page(data)
        else:
            intro_html, sections = build_chapter_sections(data, page_id)
            section_nav = render_local_nav(sections)
            body_sections = "".join(
                section_block(section_id, section_title, content)
                for section_id, section_title, content in sections
            )
            body_html = intro_html + section_nav + body_sections

        pages[page["filename"]] = build_report_shell(
            data=data,
            input_path=input_path,
            page_specs=page_specs,
            current_id=page_id,
            title=page["title"],
            kicker=page["kicker"],
            deck=page["deck"],
            body_html=body_html,
        )

    return pages


def build_html(data: dict[str, Any], input_path: Path) -> str:
    nav_items = [
        ("current-status", "当前状态", render_current_status(data)),
        ("business-snapshot", "业务快照", render_business_snapshot(data)),
        ("debate", "多空观点", render_debate(data)),
        ("investor-lenses", "大师视角", render_investor_lenses(data)),
        ("thesis", "当前投资判断", render_investment_case(data)),
        ("valuation", "估值", render_valuation(data)),
        ("market-behavior", "股价与市场", render_market_behavior(data)),
        ("industry", "行业与竞争", render_industry(data)),
        ("financials", "财务质量", render_financials(data)),
        ("capital-allocation", "资本配置", render_capital_allocation(data)),
        ("history", "公司时间线", render_company_history(data)),
        ("management", "管理层", render_management(data)),
        ("business-quality", "业务深挖", render_business_quality(data)),
        ("crisis", "危机档案", render_crisis_archive(data)),
        ("open-questions", "待验证问题", render_open_questions(data)),
        ("sources", "来源附录", render_sources(data)),
    ]
    nav_html = '<nav class="report-nav">' + "".join(
        f'<a href="#{esc(section_id)}">{esc(nav_label)}</a>'
        for section_id, nav_label, _ in nav_items
    ) + "</nav>"
    body_html = render_summary_questions(data) + render_summary(data, report_label="完整研究报告") + "".join(
        section_block(section_id, section_title, content)
        for section_id, section_title, content in nav_items
    )
    meta = data.get("meta", {})
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{esc(meta.get('company_name', '股票研究报告'))} - 单页研究档案</title>
  <style>
    {build_report_css()}
  </style>
</head>
<body>
  <div class="page-shell">
    <div class="topbar">
      {nav_html}
    </div>
    <main>
      {body_html}
      <footer>
        <p>输入文件：{esc(str(input_path))}</p>
        <p>说明：页面为单文件静态 HTML，保留完整阅读流，适合连续滚动浏览与局部迭代排版。</p>
      </footer>
    </main>
  </div>
</body>
</html>
"""


def main() -> int:
    args = parse_args()
    input_path = Path(args.input).expanduser()

    try:
        dossier = load_dossier(input_path)
    except Exception as exc:  # noqa: BLE001
        print(f"[错误] 无法读取 dossier: {exc}")
        return 1

    errors, warnings = validate_dossier(dossier)
    if errors:
        print("[错误] dossier 校验失败：")
        for error in errors:
            print(f"- {error}")
        return 1

    if warnings:
        print("[警告] 继续渲染，但发现以下问题：")
        for warning in warnings:
            print(f"- {warning}")

    output_dir = default_output_dir(
        dossier,
        base_dir=args.base_dir,
        output_dir=args.output_dir,
    )
    output_dir.mkdir(parents=True, exist_ok=True)

    pages = build_multipage_report(dossier, input_path)
    for filename, html_output in pages.items():
        page_path = output_dir / filename
        page_path.write_text(html_output, encoding="utf-8")
        print(f"[完成] 报告页: {page_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
