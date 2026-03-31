from __future__ import annotations

from html import escape
from typing import Callable

from perf_agent.models.state import AnalysisState


def render_html_report(state: AnalysisState, kind_labeler: Callable[[str], str] | None = None) -> str:
    report = state.final_report
    if report is None:
        return "<html><body><h1>性能分析报告</h1><p>未生成报告。</p></body></html>"

    label = kind_labeler or (lambda item: item)
    observations = sorted(state.observations, key=lambda item: (item.source, item.metric, item.scope))
    hypotheses = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
    top_confidence = max((item.confidence for item in hypotheses), default=0.0)

    observation_rows = "\n".join(_render_observation_row(item) for item in observations[:80])
    hypothesis_cards = "\n".join(_render_hypothesis_card(item, label) for item in hypotheses)
    environment_items = "\n".join(f"<li>{_inline(item)}</li>" for item in report.environment_summary)
    history_items = "\n".join(f"<li>{_inline(item)}</li>" for item in report.experiment_history)
    evidence_items = "\n".join(f"<li>{_inline(item)}</li>" for item in report.evidence_summary)
    chart_cards = "\n".join(_render_chart_card(state, item, label) for item in report.chart_specs)
    source_cards = "\n".join(_render_source_card(item, label) for item in report.source_findings)

    source_section = (
        f"<p><strong>源码目录:</strong> {_inline(state.source_dir or '未提供')}</p>"
        f"<p><strong>已索引源码文件:</strong> {len(state.source_files)}</p>"
        f"<p><strong>语言:</strong> {_inline(', '.join(state.source_language_hints) or '未知')}</p>"
    )

    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>性能分析报告</title>
  <style>
    :root {{
      --panel: #fffdf8;
      --ink: #1f2937;
      --muted: #5b6470;
      --accent: #c55b3c;
      --line: #e8ddce;
      --code: #fff7ee;
      --chip: #f6eadb;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      font-family: Georgia, "Iowan Old Style", serif;
      color: var(--ink);
      background: radial-gradient(circle at top right, #f9e7db, transparent 28%), linear-gradient(180deg, #f7f1e7 0%, #efe7db 100%);
    }}
    .page {{
      max-width: 1200px;
      margin: 0 auto;
      padding: 32px 20px 48px;
    }}
    .hero, .card, table {{
      background: var(--panel);
      border: 1px solid var(--line);
      box-shadow: 0 12px 30px rgba(71, 48, 29, 0.06);
    }}
    .hero {{
      border-radius: 20px;
      padding: 28px;
    }}
    h1, h2, h3, h4 {{ margin: 0 0 12px; }}
    p, li, td, th {{ line-height: 1.6; }}
    ul {{ margin: 0; padding-left: 20px; }}
    .grid {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
      gap: 16px;
      margin-top: 20px;
    }}
    .card {{
      border-radius: 18px;
      padding: 18px;
    }}
    .card + .card {{ margin-top: 16px; }}
    .source-card {{
      padding: 20px;
    }}
    .bar {{
      height: 10px;
      background: #efe5d9;
      border-radius: 999px;
      overflow: hidden;
      margin: 10px 0 14px;
    }}
    .bar span {{
      display: block;
      height: 100%;
      background: linear-gradient(90deg, var(--accent), #e38e62);
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin-top: 12px;
      border-radius: 18px;
      overflow: hidden;
    }}
    th, td {{
      text-align: left;
      padding: 12px 14px;
      border-bottom: 1px solid var(--line);
      font-size: 14px;
      vertical-align: top;
    }}
    th {{
      background: #fbf5ed;
      color: var(--muted);
    }}
    .section {{ margin-top: 24px; }}
    .muted {{ color: var(--muted); }}
    .pill {{
      display: inline-block;
      padding: 4px 10px;
      border-radius: 999px;
      background: var(--chip);
      color: #7a4a31;
      font-size: 12px;
      margin-right: 8px;
      margin-bottom: 8px;
    }}
    .code {{
      background: var(--code);
      border: 1px solid var(--line);
      border-radius: 14px;
      padding: 12px 14px;
      overflow-x: auto;
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      font-size: 13px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .two-col {{
      display: grid;
      grid-template-columns: 1.15fr 0.85fr;
      gap: 16px;
    }}
    .inline-code {{
      font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
      background: #f7efe4;
      padding: 1px 6px;
      border-radius: 8px;
      font-size: 12px;
    }}
    @media (max-width: 880px) {{
      .two-col {{
        grid-template-columns: 1fr;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <p class="muted">自动化实验设计型性能分析</p>
      <h1>{_inline(report.executive_summary, limit=160)}</h1>
      <div class="grid">
        <div class="card">
          <h3>分析目标</h3>
          <p>{_inline(' '.join(report.target.command) or 'PID 附着模式', limit=100)}</p>
          <p class="muted">可执行文件: {_inline(report.target.executable_path or '未提供', limit=72)}</p>
        </div>
        <div class="card">
          <h3>最高置信度</h3>
          <div class="bar"><span style="width:{top_confidence * 100:.0f}%"></span></div>
          <p>{top_confidence:.2f}</p>
        </div>
        <div class="card">
          <h3>源码上下文</h3>
          {source_section}
        </div>
      </div>
    </section>

    <section class="section two-col">
      <div>
        <div class="card">
          <h2>运行环境</h2>
          <ul>
            {environment_items or '<li>未采集到环境信息。</li>'}
          </ul>
        </div>
        <div class="card" style="margin-top:16px">
          <h2>实验设计与执行</h2>
          <ul>
            {history_items or '<li>未记录实验历史。</li>'}
          </ul>
        </div>
      </div>
      <div>
        <div class="card">
          <h2>证据摘要</h2>
          <ul>
            {evidence_items or '<li>未生成证据摘要。</li>'}
          </ul>
        </div>
        <div class="card" style="margin-top:16px">
          <h2>候选瓶颈</h2>
          {hypothesis_cards or "<p>未生成瓶颈候选。</p>"}
        </div>
      </div>
    </section>

    <section class="section">
      <h2>证据图表</h2>
      <div class="grid">
        {chart_cards or "<div class='card'><p>当前没有足够的图表数据。</p></div>"}
      </div>
    </section>

    <section class="section">
      <h2>源码定位与片段</h2>
      <div class="grid">
        {source_cards or "<div class='card source-card'><p>当前没有可展示的源码定位结果。</p></div>"}
      </div>
    </section>

    <section class="section">
      <h2>关键观测</h2>
      <table>
        <thead>
          <tr>
            <th>ID</th>
            <th>来源</th>
            <th>指标</th>
            <th>值</th>
            <th>范围</th>
            <th>标签</th>
          </tr>
        </thead>
        <tbody>
          {observation_rows or "<tr><td colspan='6'>当前没有 observation。</td></tr>"}
        </tbody>
      </table>
    </section>
  </div>
</body>
</html>
"""


def _render_hypothesis_card(item, label: Callable[[str], str]) -> str:
    return (
        "<div class='card hypothesis'>"
        f"<h3>{_inline(label(item.kind), limit=48)}</h3>"
        f"<div class='bar'><span style='width:{item.confidence * 100:.0f}%'></span></div>"
        f"<p>{_inline(item.summary, limit=160)}</p>"
        f"<p><strong>置信度:</strong> {item.confidence:.2f}</p>"
        f"<p><strong>支持证据:</strong> {_inline(', '.join(item.supporting_observation_ids) or '无', limit=84)}</p>"
        f"<p><strong>验证状态:</strong> {'需要继续验证' if item.needs_verification else '证据已基本充分'}</p>"
        "</div>"
    )


def _render_source_card(item, label: Callable[[str], str]) -> str:
    hypothesis_text = label(item.related_hypothesis) if item.related_hypothesis else "未标注"
    line_suffix = f"-{item.line_end}" if item.line_end and item.line_end != item.line_no else ""
    confidence_text = f"{item.confidence:.2f}" if item.confidence is not None else "未提供"
    return (
        "<div class='card source-card'>"
        f"<h3>{_inline(item.issue_type, limit=60)}</h3>"
        f"<p class='muted'>{_inline(item.file_path, limit=96)}:{item.line_no}{line_suffix}</p>"
        f"<p><span class='pill'>{_inline(hypothesis_text, limit=24)}</span>"
        f"<span class='pill'>{_inline(item.mapping_method or '未知', limit=24)}</span>"
        f"<span class='pill'>置信度 {confidence_text}</span></p>"
        f"<p>{_inline(item.rationale, limit=220)}</p>"
        f"<div class='code'>{_block(item.snippet)}</div>"
        "</div>"
    )


def _render_observation_row(item) -> str:
    labels = ", ".join(f"{key}={value}" for key, value in item.labels.items() if value) or "-"
    return (
        "<tr>"
        f"<td>{_inline(item.id, limit=18)}</td>"
        f"<td>{_inline(item.source, limit=22)}</td>"
        f"<td>{_inline(item.metric, limit=42)}</td>"
        f"<td>{_inline(str(item.value), limit=42)}</td>"
        f"<td>{_inline(item.scope, limit=18)}</td>"
        f"<td>{_inline(labels, limit=84)}</td>"
        "</tr>"
    )


def _render_chart_card(state: AnalysisState, chart_spec, label: Callable[[str], str]) -> str:
    svg = ""
    if chart_spec.chart_id == "hypothesis-confidence":
        svg = _render_hypothesis_bar_chart(state, label)
    elif chart_spec.chart_id == "hotspot-symbols":
        svg = _render_distribution_chart(state, "hot_symbol_pct", "symbol", suffix="%")
    elif chart_spec.chart_id == "process-sample-breakdown":
        svg = _render_distribution_chart(state, "process_sample_pct", "pid", suffix="%")
    elif chart_spec.chart_id == "thread-sample-breakdown":
        svg = _render_distribution_chart(state, "thread_sample_pct", "tid", suffix="%")
    elif chart_spec.chart_id == "topdown-breakdown":
        svg = _render_topdown_chart(state, chart_spec.metrics)
    elif chart_spec.chart_type == "line" and chart_spec.metrics:
        svg = _render_timeline_line_chart(state, chart_spec.metrics[0])

    if not svg:
        return ""
    return (
        "<div class='card'>"
        f"<h3>{_inline(chart_spec.title, limit=64)}</h3>"
        f"<p class='muted'>{_inline(chart_spec.rationale, limit=160)}</p>"
        f"{svg}"
        "</div>"
    )


def _render_hypothesis_bar_chart(state: AnalysisState, label: Callable[[str], str]) -> str:
    hypotheses = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
    if not hypotheses:
        return "<p>暂无数据。</p>"
    rows = []
    for item in hypotheses[:5]:
        width = max(8, int(item.confidence * 100))
        rows.append(
            f"<div style='margin:10px 0'>"
            f"<div style='font-size:13px'>{_inline(label(item.kind), limit=30)} {item.confidence:.2f}</div>"
            f"<div class='bar'><span style='width:{width}%'></span></div>"
            f"</div>"
        )
    return "".join(rows)


def _render_timeline_line_chart(state: AnalysisState, metric: str) -> str:
    points = []
    for observation in state.observations:
        if observation.metric != metric or observation.labels.get("series_type") != "timeline":
            continue
        try:
            x = float(observation.labels.get("time_bucket_sec", "0"))
            y = float(observation.value)
        except (TypeError, ValueError):
            continue
        points.append((x, y))
    points.sort(key=lambda item: item[0])
    if len(points) < 2:
        return ""
    xs = [item[0] for item in points]
    ys = [item[1] for item in points]
    min_x, max_x = min(xs), max(xs)
    min_y, max_y = min(ys), max(ys)
    width = 360
    height = 180
    path_parts = []
    for x, y in points:
        plot_x = 28 + (0 if max_x == min_x else (x - min_x) / (max_x - min_x) * (width - 56))
        plot_y = 150 - (0 if max_y == min_y else (y - min_y) / (max_y - min_y) * 110)
        path_parts.append(f"{plot_x:.1f},{plot_y:.1f}")
    path_d = " L ".join(path_parts)
    return (
        f"<svg viewBox='0 0 {width} {height}' width='100%' height='{height}' role='img' aria-label='{_attr(metric)}'>"
        "<line x1='28' y1='150' x2='332' y2='150' stroke='#cab9a2' stroke-width='1' />"
        "<line x1='28' y1='24' x2='28' y2='150' stroke='#cab9a2' stroke-width='1' />"
        f"<path d='M {path_d}' fill='none' stroke='#c55b3c' stroke-width='3' stroke-linecap='round' stroke-linejoin='round' />"
        f"<text x='28' y='168' font-size='11' fill='#5b6470'>{min_x:.2f}s</text>"
        f"<text x='282' y='168' font-size='11' fill='#5b6470'>{max_x:.2f}s</text>"
        f"<text x='34' y='20' font-size='11' fill='#5b6470'>{max_y:.2f}</text>"
        f"<text x='34' y='148' font-size='11' fill='#5b6470'>{min_y:.2f}</text>"
        "</svg>"
    )


def _render_distribution_chart(state: AnalysisState, metric: str, label_key: str, suffix: str = "") -> str:
    items: list[tuple[str, float]] = []
    for observation in state.observations:
        if observation.metric != metric:
            continue
        label_text = _distribution_label(observation, label_key)
        try:
            pct = float(observation.value)
        except (TypeError, ValueError):
            continue
        items.append((label_text, pct))
    if not items:
        return ""
    rows = []
    for name, value in items[:6]:
        rows.append(
            f"<div style='margin:10px 0'>"
            f"<div style='font-size:13px' title='{_attr(name)}'>{_inline(name, limit=56)} {value:.2f}{suffix}</div>"
            f"<div class='bar'><span style='width:{max(8, int(min(value, 100.0)))}%'></span></div>"
            f"</div>"
        )
    return "".join(rows)


def _render_topdown_chart(state: AnalysisState, metrics: list[str]) -> str:
    values: list[tuple[str, float]] = []
    for metric in metrics:
        candidates = [
            observation
            for observation in state.observations
            if observation.metric == metric and isinstance(observation.value, (int, float))
        ]
        if not candidates:
            continue
        observation = candidates[-1]
        values.append((metric, float(observation.value)))
    if not values:
        return ""
    rows = []
    for metric, value in values[:6]:
        rows.append(
            f"<div style='margin:10px 0'>"
            f"<div style='font-size:13px'>{_inline(metric, limit=40)} {value:.2f}%</div>"
            f"<div class='bar'><span style='width:{max(8, int(min(value, 100.0)))}%'></span></div>"
            f"</div>"
        )
    return "".join(rows)


def _distribution_label(observation, label_key: str) -> str:
    comm = observation.labels.get("comm")
    pid = observation.labels.get("pid")
    tid = observation.labels.get("tid")
    symbol = observation.labels.get("symbol")
    if observation.metric == "hot_symbol_pct" and symbol:
        return symbol
    if observation.metric == "process_sample_pct":
        return f"{comm or 'unknown'} / pid {pid or '?'}"
    if observation.metric == "thread_sample_pct":
        return f"{comm or 'unknown'} / {pid or '?'}:{tid or '?'}"
    return observation.labels.get(label_key) or observation.metric


def _sanitize_inline(value: str) -> str:
    cleaned = "".join(ch if ch.isprintable() or ch == " " else " " for ch in str(value))
    return " ".join(cleaned.replace("\ufffd", "?").split())


def _sanitize_block(value: str) -> str:
    text = str(value).replace("\r\n", "\n").replace("\r", "\n")
    text = "".join(ch if ch.isprintable() or ch in "\n\t" else " " for ch in text)
    return text.replace("\ufffd", "?")


def _smart_truncate(value: str, limit: int) -> str:
    if len(value) <= limit:
        return value
    if limit <= 8:
        return value[:limit]
    head = max(6, int(limit * 0.58))
    tail = max(4, limit - head - 3)
    return f"{value[:head]}...{value[-tail:]}"


def _inline(value: str, limit: int = 72) -> str:
    text = _sanitize_inline(value)
    display = _smart_truncate(text, limit)
    return f"<span title='{_attr(text)}'>{escape(display)}</span>"


def _block(value: str) -> str:
    return escape(_sanitize_block(value))


def _attr(value: str) -> str:
    return escape(_sanitize_inline(value), quote=True)
