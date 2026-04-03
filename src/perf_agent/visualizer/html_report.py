from __future__ import annotations

import json
import re
from html import escape
from typing import Any, Callable

from perf_agent.models.state import AnalysisState

NOISE_SYMBOL_PATTERNS = (
    "__libc_start_main",
    "__libc_start_call_main",
    "_start",
    "start_thread",
    "__clone",
    "clone",
    "__sched",
)
TIMELINE_PREFERRED_METRICS = ("ipc", "cache_misses", "context_switches", "cycles", "instructions")
TOPDOWN_METRICS = (
    "topdown_fe_bound_pct",
    "topdown_be_bound_pct",
    "topdown_retiring_pct",
    "topdown_bad_spec_pct",
    "tma_memory_bound_pct",
    "tma_fetch_latency_pct",
    "tma_branch_mispredicts_pct",
)


def render_html_report(state: AnalysisState, kind_labeler: Callable[[str], str] | None = None) -> str:
    report = state.final_report
    if report is None:
        return "<!doctype html><html><body><h1>性能分析报告</h1><p>未生成报告。</p></body></html>"

    label = kind_labeler or (lambda item: item)
    payload = _build_payload(state, label)
    payload_json = json.dumps(payload, ensure_ascii=False).replace("</", "<\\/")
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>性能分析报告</title>
  <style>
    :root {{
      --bg: #eef5ff;
      --panel: rgba(248, 252, 255, 0.9);
      --panel-strong: rgba(251, 254, 255, 0.98);
      --ink: #0f2238;
      --muted: #5f7390;
      --muted-strong: #28405e;
      --line: rgba(70, 112, 168, 0.18);
      --line-strong: rgba(70, 112, 168, 0.32);
      --accent: #2563eb;
      --accent-soft: rgba(37, 99, 235, 0.12);
      --accent-2: #0f5d91;
      --accent-2-soft: rgba(15, 93, 145, 0.12);
      --shadow: 0 22px 60px rgba(19, 54, 99, 0.09);
      --radius-xl: 28px;
      --radius-lg: 20px;
      --radius-md: 14px;
      --mono: "JetBrains Mono", "SFMono-Regular", "Cascadia Code", "Fira Code", ui-monospace, monospace;
      --sans: "IBM Plex Sans", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Source Han Sans SC", sans-serif;
      --serif: "Iowan Old Style", "Noto Serif CJK SC", "Source Han Serif SC", Georgia, serif;
    }}
    * {{ box-sizing: border-box; }}
    html {{ scroll-behavior: smooth; }}
    body {{
      margin: 0;
      min-height: 100vh;
      color: var(--ink);
      font-family: var(--sans);
      background:
        radial-gradient(circle at 12% 10%, rgba(37,99,235,0.12), transparent 22%),
        radial-gradient(circle at 88% 12%, rgba(14,116,144,0.1), transparent 24%),
        linear-gradient(180deg, #f4f8fd 0%, #ebf2fb 44%, #e8f0fa 100%);
    }}
    body::before {{
      content: "";
      position: fixed;
      inset: 0;
      pointer-events: none;
      opacity: 0.28;
      background-image:
        linear-gradient(rgba(255,255,255,0.3) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.28) 1px, transparent 1px);
      background-size: 32px 32px;
      mask-image: radial-gradient(circle at center, black 48%, transparent 100%);
    }}
    .page {{
      max-width: 1380px;
      margin: 0 auto;
      padding: 28px 24px 56px;
    }}
    .hero {{
      position: relative;
      overflow: hidden;
      padding: 30px 30px 26px;
      border-radius: var(--radius-xl);
      border: 1px solid var(--line);
      background:
        linear-gradient(135deg, rgba(255,255,255,0.98) 0%, rgba(245,250,255,0.96) 52%, rgba(235,244,255,0.92) 100%);
      box-shadow: var(--shadow);
      backdrop-filter: blur(18px);
    }}
    .hero::after {{
      content: "";
      position: absolute;
      width: 320px;
      height: 320px;
      right: -80px;
      top: -90px;
      border-radius: 999px;
      background: radial-gradient(circle, rgba(37,99,235,0.16), transparent 68%);
    }}
    .eyebrow {{
      font-size: 12px;
      letter-spacing: 0.16em;
      text-transform: uppercase;
      color: var(--muted);
      margin-bottom: 10px;
    }}
    .hero h1 {{
      margin: 0;
      max-width: 900px;
      font-size: clamp(30px, 4vw, 52px);
      line-height: 1.06;
      letter-spacing: -0.04em;
      font-weight: 760;
      font-family: var(--serif);
    }}
    .hero-sub {{
      margin-top: 14px;
      max-width: 760px;
      color: var(--muted-strong);
      font-size: 15px;
      line-height: 1.7;
    }}
    .hero-grid {{
      display: grid;
      grid-template-columns: 1.2fr 0.8fr;
      gap: 18px;
      margin-top: 26px;
    }}
    .hero-main {{
      display: flex;
      flex-direction: column;
      gap: 14px;
    }}
    .hero-meta {{
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 12px;
    }}
    .metric-card, .panel, .chart-card, .observation-card, .source-card, .hypothesis-card {{
      border-radius: var(--radius-lg);
      border: 1px solid var(--line);
      background: var(--panel);
      box-shadow: var(--shadow);
      backdrop-filter: blur(16px);
    }}
    .metric-card {{
      padding: 16px 18px;
    }}
    .metric-label {{
      font-size: 12px;
      letter-spacing: 0.08em;
      text-transform: uppercase;
      color: var(--muted);
    }}
    .metric-value {{
      margin-top: 8px;
      font-size: 30px;
      font-weight: 720;
      line-height: 1;
    }}
    .metric-footnote {{
      margin-top: 8px;
      font-size: 13px;
      color: var(--muted-strong);
    }}
    .chip-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 16px;
    }}
    .chip {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(37, 99, 235, 0.16);
      background: rgba(255,255,255,0.6);
      color: var(--muted-strong);
      font-size: 13px;
      font-weight: 600;
    }}
    .chip--accent {{
      background: var(--accent-soft);
      color: #1746a2;
      border-color: rgba(37, 99, 235, 0.24);
    }}
    .chip--teal {{
      background: var(--accent-2-soft);
      color: #0b4e79;
      border-color: rgba(15, 93, 145, 0.24);
    }}
    .toolbar {{
      position: sticky;
      top: 14px;
      z-index: 10;
      display: grid;
      grid-template-columns: 1fr auto;
      gap: 14px;
      margin: 22px 0;
      padding: 14px 16px;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(248, 252, 255, 0.9);
      backdrop-filter: blur(18px);
      box-shadow: 0 12px 30px rgba(19, 54, 99, 0.06);
    }}
    .tab-row, .filter-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      align-items: center;
    }}
    .tab-button, .filter-chip, .ghost-button, .inline-toggle {{
      appearance: none;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.78);
      color: var(--muted-strong);
      border-radius: 999px;
      padding: 9px 14px;
      font: inherit;
      font-size: 13px;
      cursor: pointer;
      transition: 160ms ease;
    }}
    .tab-button:hover, .filter-chip:hover, .ghost-button:hover, .inline-toggle:hover {{
      transform: translateY(-1px);
      border-color: var(--line-strong);
    }}
    .tab-button.is-active, .filter-chip.is-active {{
      background: linear-gradient(135deg, rgba(37,99,235,0.16), rgba(14,116,144,0.14));
      color: var(--ink);
      border-color: rgba(37,99,235,0.28);
      box-shadow: inset 0 0 0 1px rgba(255,255,255,0.4);
    }}
    .search-shell {{
      display: flex;
      align-items: center;
      gap: 10px;
      min-width: 280px;
      padding: 0 12px;
      border-radius: 999px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.78);
    }}
    .search-shell input {{
      width: 100%;
      border: 0;
      outline: 0;
      background: transparent;
      color: var(--ink);
      font: inherit;
      padding: 10px 0;
    }}
    .tab-pane {{
      display: none;
      margin-top: 18px;
    }}
    .tab-pane.is-active {{
      display: block;
    }}
    .report-section {{
      margin-top: 26px;
    }}
    .report-section + .report-section {{
      margin-top: 18px;
    }}
    .section-kicker {{
      margin-bottom: 8px;
      color: var(--accent);
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.16em;
      text-transform: uppercase;
    }}
    .layout {{
      display: grid;
      grid-template-columns: 0.92fr 1.08fr;
      gap: 18px;
    }}
    .stack {{
      display: grid;
      gap: 18px;
    }}
    .panel {{
      padding: 20px 22px;
    }}
    .panel h2, .panel h3 {{
      margin: 0 0 14px;
      font-size: 18px;
      letter-spacing: -0.03em;
    }}
    .panel-list {{
      display: grid;
      gap: 10px;
      margin: 0;
      padding: 0;
      list-style: none;
    }}
    .panel-list li {{
      padding: 11px 12px;
      border-radius: 12px;
      background: rgba(255,255,255,0.64);
      border: 1px solid rgba(111,95,76,0.08);
      line-height: 1.65;
      color: var(--muted-strong);
    }}
    .panel-list li strong {{
      color: var(--ink);
    }}
    .grid {{
      display: grid;
      gap: 18px;
    }}
    .grid--2 {{
      grid-template-columns: repeat(2, minmax(0, 1fr));
    }}
    .grid--3 {{
      grid-template-columns: repeat(3, minmax(0, 1fr));
    }}
    .section-head {{
      display: flex;
      justify-content: space-between;
      align-items: end;
      gap: 16px;
      margin-bottom: 16px;
    }}
    .section-head h2 {{
      margin: 0;
      font-size: 24px;
      letter-spacing: -0.04em;
    }}
    .section-head p {{
      margin: 6px 0 0;
      color: var(--muted);
      font-size: 14px;
    }}
    .section-lead {{
      margin: 8px 0 18px;
      max-width: 880px;
      color: var(--muted-strong);
      font-size: 15px;
      line-height: 1.8;
    }}
    .hypothesis-grid, .source-grid, .chart-grid, .evidence-grid {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    }}
    .chart-strip {{
      display: grid;
      gap: 16px;
      grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    }}
    .hypothesis-card, .source-card, .chart-card, .observation-card {{
      padding: 18px;
    }}
    .metric-card, .panel, .chart-card, .observation-card, .source-card, .hypothesis-card,
    .panel-list li, .artifact-item, .meta-pill, .callout, .hint, .metric-value, .metric-footnote,
    .obs-value, .obs-source, .obs-tags, .chart-label strong, .chart-label span, .code-line, .code-line-no,
    .expandable summary, .expandable-body, .hero-sub, .section-lead {{
      min-width: 0;
      overflow-wrap: anywhere;
      word-break: break-word;
    }}
    .chart-card {{
      position: relative;
      overflow: hidden;
      transition: transform 180ms ease, box-shadow 180ms ease, border-color 180ms ease;
    }}
    .chart-card.is-zoomable {{
      cursor: zoom-in;
    }}
    .chart-card.is-zoomable:hover {{
      transform: translateY(-2px);
      box-shadow: 0 24px 56px rgba(19, 54, 99, 0.12);
      border-color: rgba(37, 99, 235, 0.26);
    }}
    .chart-card h3 {{
      margin: 0;
      padding-right: 92px;
    }}
    .chart-card .hint {{
      margin-top: 10px;
    }}
    .zoom-button {{
      position: absolute;
      top: 14px;
      right: 14px;
      appearance: none;
      border: 1px solid rgba(70,112,168,0.16);
      background: rgba(255,255,255,0.88);
      color: var(--muted-strong);
      border-radius: 999px;
      padding: 8px 12px;
      font: inherit;
      font-size: 12px;
      font-weight: 700;
      letter-spacing: 0.02em;
      cursor: pointer;
      transition: 160ms ease;
      box-shadow: 0 8px 20px rgba(19, 54, 99, 0.08);
    }}
    .zoom-button:hover {{
      transform: translateY(-1px);
      border-color: rgba(37, 99, 235, 0.26);
      color: var(--ink);
    }}
    .hypothesis-top {{
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: start;
    }}
    .hypothesis-title {{
      font-size: 18px;
      letter-spacing: -0.03em;
      font-weight: 700;
      font-family: var(--serif);
    }}
    .confidence {{
      font-family: var(--mono);
      font-size: 12px;
      color: var(--muted);
      white-space: nowrap;
    }}
    .bar {{
      position: relative;
      height: 10px;
      border-radius: 999px;
      background: rgba(70,112,168,0.12);
      overflow: hidden;
      margin: 14px 0 12px;
    }}
    .bar > span {{
      position: absolute;
      inset: 0 auto 0 0;
      border-radius: 999px;
      background: linear-gradient(90deg, #1d4ed8 0%, #3b82f6 48%, #0f5d91 100%);
    }}
    .meta-line {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 12px;
    }}
    .meta-pill {{
      padding: 5px 9px;
      border-radius: 999px;
      background: rgba(255,255,255,0.78);
      border: 1px solid rgba(70,112,168,0.12);
      color: var(--muted-strong);
      font-size: 12px;
      font-weight: 600;
    }}
    .chart-list {{
      display: grid;
      gap: 12px;
      margin-top: 14px;
    }}
    .chart-row {{
      display: grid;
      gap: 6px;
    }}
    .chart-label {{
      display: flex;
      justify-content: space-between;
      gap: 14px;
      align-items: start;
      font-size: 13px;
    }}
    .chart-label strong {{
      font-weight: 640;
      flex: 1;
    }}
    .chart-value {{
      color: var(--muted);
      font-family: var(--mono);
      font-size: 12px;
      white-space: nowrap;
    }}
    .line-chart {{
      width: 100%;
      height: 230px;
      border-radius: 16px;
      background: linear-gradient(180deg, rgba(255,255,255,0.86), rgba(237,244,253,0.96));
      border: 1px solid rgba(70,112,168,0.12);
      padding: 10px;
    }}
    .command-shell {{
      padding: 16px 18px;
      border-radius: 18px;
      border: 1px solid rgba(70,112,168,0.16);
      background: linear-gradient(180deg, rgba(17,34,56,0.98), rgba(20,44,72,0.98));
      color: #e9f2ff;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }}
    .command-band {{
      padding: 20px 24px;
      border-radius: 22px;
      border: 1px solid rgba(70,112,168,0.16);
      background: linear-gradient(180deg, rgba(250,253,255,0.98), rgba(242,248,255,0.96));
      box-shadow: var(--shadow);
    }}
    .command-caption {{
      margin-bottom: 8px;
      color: rgba(210,227,255,0.72);
      font-size: 12px;
      letter-spacing: 0.12em;
      text-transform: uppercase;
    }}
    .command-band .command-caption {{
      margin-bottom: 0;
      color: var(--muted);
    }}
    .command-primary {{
      margin-top: 12px;
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid rgba(37,99,235,0.12);
      background: linear-gradient(180deg, rgba(14,35,60,0.96), rgba(20,44,72,0.98));
      color: #edf4ff;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.06);
    }}
    .command-line {{
      font-family: var(--mono);
      font-size: 13px;
      line-height: 1.8;
      white-space: pre-wrap;
      overflow-wrap: anywhere;
    }}
    .command-meta-row {{
      display: flex;
      flex-wrap: wrap;
      gap: 10px;
      margin-top: 14px;
    }}
    .command-meta-pill {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
      padding: 8px 12px;
      border-radius: 999px;
      border: 1px solid rgba(70,112,168,0.12);
      background: rgba(255,255,255,0.8);
      color: var(--muted-strong);
      font-size: 12px;
      max-width: 100%;
      overflow-wrap: anywhere;
    }}
    .command-notes {{
      display: grid;
      gap: 10px;
      margin-top: 14px;
    }}
    .command-note {{
      padding: 11px 12px;
      border-radius: 12px;
      border: 1px solid rgba(70,112,168,0.12);
      background: rgba(255,255,255,0.72);
      color: var(--muted-strong);
      line-height: 1.7;
    }}
    .evidence-columns {{
      display: grid;
      gap: 18px;
      grid-template-columns: 1.05fr 0.95fr;
    }}
    .analysis-note {{
      padding: 12px 14px;
      border-radius: 14px;
      border: 1px solid rgba(70,112,168,0.14);
      background: rgba(255,255,255,0.76);
      color: var(--muted-strong);
      line-height: 1.75;
    }}
    .hotspot-share {{
      font-family: var(--mono);
      font-size: 13px;
      color: var(--accent);
      white-space: nowrap;
    }}
    .chart-card[data-chart-view='line'] .line-chart,
    .chart-card[data-chart-view='distribution'] .chart-list {{
      margin-top: 14px;
    }}
    .chart-modal {{
      position: fixed;
      inset: 0;
      z-index: 40;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 28px;
      background: rgba(9, 23, 41, 0.56);
      backdrop-filter: blur(10px);
    }}
    .chart-modal.is-open {{
      display: flex;
    }}
    .chart-modal-panel {{
      position: relative;
      width: min(1100px, 100%);
      max-height: min(88vh, 980px);
      overflow: auto;
      padding: 28px 28px 24px;
      border-radius: 26px;
      border: 1px solid rgba(255,255,255,0.18);
      background:
        linear-gradient(180deg, rgba(252, 254, 255, 0.98) 0%, rgba(245, 250, 255, 0.97) 100%);
      box-shadow: 0 30px 80px rgba(9, 23, 41, 0.28);
    }}
    .chart-modal-panel h3 {{
      margin: 0;
      font-size: clamp(24px, 2.4vw, 34px);
      letter-spacing: -0.04em;
    }}
    .chart-modal-sub {{
      margin-top: 10px;
      color: var(--muted-strong);
      font-size: 14px;
      line-height: 1.75;
    }}
    .chart-modal-body {{
      margin-top: 22px;
    }}
    .chart-modal-body .line-chart {{
      height: min(60vh, 520px);
      padding: 14px;
    }}
    .chart-modal-body .chart-list {{
      gap: 16px;
    }}
    .chart-modal-body .chart-label {{
      font-size: 14px;
    }}
    .chart-modal-body .chart-value {{
      font-size: 13px;
    }}
    .chart-modal-close {{
      position: sticky;
      top: 0;
      margin-left: auto;
      display: inline-flex;
      align-items: center;
      justify-content: center;
      width: 40px;
      height: 40px;
      border: 1px solid rgba(70,112,168,0.16);
      background: rgba(255,255,255,0.92);
      color: var(--muted-strong);
      border-radius: 999px;
      font: inherit;
      font-size: 22px;
      line-height: 1;
      cursor: pointer;
    }}
    .chart-modal-close:hover {{
      border-color: rgba(37, 99, 235, 0.28);
      color: var(--ink);
    }}
    body.has-modal {{
      overflow: hidden;
    }}
    .obs-grid {{
      display: grid;
      gap: 14px;
      grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    }}
    .obs-metric {{
      font-family: var(--mono);
      font-size: 12px;
      color: var(--muted);
      letter-spacing: 0.02em;
    }}
    .obs-value {{
      margin-top: 8px;
      font-size: 24px;
      font-weight: 720;
      line-height: 1.08;
      letter-spacing: -0.03em;
      word-break: break-word;
    }}
    .obs-source {{
      margin-top: 10px;
      color: var(--muted-strong);
      font-size: 13px;
    }}
    .obs-tags {{
      margin-top: 12px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.6;
    }}
    .callout {{
      padding: 14px 16px;
      border-radius: 16px;
      border: 1px solid rgba(37,99,235,0.16);
      background: linear-gradient(180deg, rgba(37,99,235,0.08), rgba(255,255,255,0.78));
      color: var(--muted-strong);
      line-height: 1.7;
    }}
    .expandable {{
      display: grid;
      gap: 8px;
      margin-top: 2px;
    }}
    .expandable details {{
      border-radius: 12px;
      border: 1px solid rgba(70,112,168,0.12);
      background: rgba(255,255,255,0.74);
      overflow: hidden;
    }}
    .expandable summary {{
      list-style: none;
      cursor: pointer;
      padding: 10px 12px;
      font-family: var(--mono);
      font-size: 12px;
      color: var(--muted-strong);
      display: flex;
      align-items: center;
      gap: 10px;
    }}
    .expandable summary::-webkit-details-marker {{
      display: none;
    }}
    .expandable details[open] summary {{
      border-bottom: 1px solid rgba(70,112,168,0.12);
      background: rgba(255,255,255,0.88);
    }}
    .expandable-body {{
      padding: 12px;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.75;
      color: var(--ink);
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .source-meta {{
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin: 12px 0;
    }}
    .code-block {{
      display: grid;
      gap: 0;
      border-radius: 16px;
      border: 1px solid rgba(70,112,168,0.12);
      overflow: hidden;
      background: #112238;
      color: #eaf2ff;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.02);
    }}
    .code-row {{
      display: grid;
      grid-template-columns: 64px 1fr;
      gap: 0;
      font-family: var(--mono);
      font-size: 12px;
      line-height: 1.7;
    }}
    .code-row:nth-child(odd) {{
      background: rgba(255,255,255,0.02);
    }}
    .code-line-no {{
      padding: 8px 10px;
      color: rgba(214,228,255,0.52);
      border-right: 1px solid rgba(255,255,255,0.08);
      user-select: none;
      text-align: right;
    }}
    .code-line {{
      padding: 8px 12px;
      white-space: pre-wrap;
      word-break: break-word;
    }}
    .raw-shell {{
      overflow: hidden;
      border-radius: 18px;
      border: 1px solid var(--line);
      background: rgba(255,255,255,0.7);
    }}
    .raw-table {{
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
    }}
    .raw-table th, .raw-table td {{
      padding: 11px 12px;
      text-align: left;
      border-bottom: 1px solid rgba(70,112,168,0.1);
      vertical-align: top;
    }}
    .raw-table thead th {{
      position: sticky;
      top: 0;
      background: rgba(248,242,234,0.96);
      color: var(--muted);
      font-size: 12px;
      letter-spacing: 0.04em;
      text-transform: uppercase;
    }}
    .raw-table code {{
      font-family: var(--mono);
      font-size: 12px;
      color: var(--muted-strong);
    }}
    .empty {{
      padding: 24px;
      border-radius: 18px;
      border: 1px dashed rgba(70,112,168,0.24);
      text-align: center;
      color: var(--muted);
      background: rgba(255,255,255,0.45);
    }}
    .hint {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.7;
    }}
    .artifact-list {{
      display: grid;
      gap: 8px;
      margin-top: 10px;
    }}
    .artifact-item {{
      padding: 10px 12px;
      border-radius: 12px;
      background: rgba(255,255,255,0.72);
      border: 1px solid rgba(70,112,168,0.08);
      font-family: var(--mono);
      font-size: 12px;
      word-break: break-word;
    }}
    .mono {{
      font-family: var(--mono);
    }}
    [data-filterable][hidden] {{
      display: none !important;
    }}
    @media (max-width: 1120px) {{
      .hero-grid, .layout, .evidence-columns {{
        grid-template-columns: 1fr;
      }}
      .toolbar {{
        grid-template-columns: 1fr;
      }}
    }}
    @media (max-width: 760px) {{
      .page {{
        padding: 18px 14px 40px;
      }}
      .hero {{
        padding: 24px 20px 20px;
      }}
      .metric-value {{
        font-size: 24px;
      }}
      .grid--2, .grid--3 {{
        grid-template-columns: 1fr;
      }}
      .search-shell {{
        min-width: 100%;
      }}
      .code-row {{
        grid-template-columns: 48px 1fr;
      }}
      .chart-modal {{
        padding: 12px;
      }}
      .chart-modal-panel {{
        padding: 18px 16px 16px;
        max-height: 92vh;
      }}
      .chart-card h3 {{
        padding-right: 0;
      }}
      .zoom-button {{
        position: static;
        margin-top: 12px;
      }}
    }}
  </style>
</head>
<body>
  <div class="page">
    <section class="hero">
      <div class="eyebrow">Performance Investigation Report</div>
      <h1>{_inline(report.executive_summary, limit=160)}</h1>
      <div class="chip-row">
        {_hero_chips(state, label)}
      </div>
      <div class="hero-meta" style="margin-top:22px">
        {_metric_card("目标命令", _compact_path(' '.join(report.target.command) or 'PID 附着模式', 92), _inline(report.target.executable_path or '未提供', 96))}
        {_metric_card("源码规模", str(report.target.source_file_count), _inline(report.target.source_dir or '未提供', 96))}
        {_metric_card("实验轮次", str(state.verification_rounds_done + 1), f"<span class='mono'>{len(state.actions_taken)}</span> 个动作")}
        {_metric_card("总体置信度", f"{report.confidence_overall:.2f}", f"{len(state.hypotheses)} 个候选瓶颈")}
      </div>
    </section>

    <section class="toolbar">
      <div class="filter-row">
        {_render_filter_chips(state, label)}
      </div>
      <div class="filter-row">
        <div class="search-shell">
          <span class="mono">/</span>
          <input type="search" placeholder="搜索函数名、文件路径、指标名..." data-search-input>
        </div>
      </div>
    </section>

    <section class="report-section">
      <div class="section-kicker">01 / 环境</div>
      <div class="section-head">
        <div>
          <h2>运行环境</h2>
        </div>
      </div>
      <div class="grid grid--2">
        <div class="panel">
          <ul class="panel-list">
            {_panel_items(report.environment_summary, empty="未采集到环境摘要。")}
          </ul>
        </div>
        <div class="panel">
          <ul class="panel-list">
            {_panel_items(_environment_capacity_items(state), empty="当前没有补充环境能力说明。")}
          </ul>
        </div>
      </div>
    </section>

    <section class="report-section">
      <div class="section-kicker">02 / 运行</div>
      <div class="section-head">
        <div>
          <h2>程序运行命令</h2>
        </div>
      </div>
      <div class="command-band">
        <div class="command-caption">Launch Command</div>
        <div class="command-primary">
          <div class="command-line">{escape(' '.join(report.target.command) if report.target.command else 'PID 附着模式')}</div>
        </div>
        <div class="command-meta-row">
          <div class="command-meta-pill">可执行文件: {escape(report.target.executable_path or '未提供')}</div>
          <div class="command-meta-pill">参数个数: {max(0, len(report.target.command) - 1) if report.target.command else 0}</div>
          <div class="command-meta-pill">源码目录: {escape(report.target.source_dir or '未提供')}</div>
        </div>
      </div>
      <div class="grid grid--2">
        <div class="panel">
          <div class="command-notes">
            {_render_command_notes(state)}
          </div>
        </div>
        <div class="panel">
          <ul class="panel-list">
            {_panel_items(report.experiment_history, empty="未记录实验历史。")}
          </ul>
        </div>
      </div>
    </section>

    <section class="report-section">
      <div class="section-kicker">03 / 结论</div>
      <div class="section-head">
        <div>
          <h2>整合结论和证据</h2>
        </div>
      </div>
      <div class="evidence-columns">
        <div class="stack">
          <div class="panel">
            <div class="callout">{_inline(report.executive_summary, limit=260)}</div>
            <div class="hypothesis-grid" style="margin-top:16px">
              {_render_hypothesis_cards(state, label)}
            </div>
          </div>
          <div class="panel">
            <div class="section-head">
              <div>
                <h3>关键 observation</h3>
              </div>
            </div>
            <div class="obs-grid">
              {_render_observation_cards(state)}
            </div>
          </div>
        </div>
        <div class="stack">
          <div class="panel">
            <div class="section-head">
              <div>
                <h3>证据摘要</h3>
              </div>
            </div>
            <ul class="panel-list">
              {_panel_items(report.evidence_summary, empty="未生成证据摘要。")}
            </ul>
          </div>
          <div class="panel">
            <div class="section-head">
              <div>
                <h3>支持与反证</h3>
              </div>
            </div>
            <ul class="panel-list">
              {_panel_items(report.supporting_evidence[:6] + report.rejected_alternatives[:3] + report.recommended_next_steps[:3], empty="当前没有可展示的结论补充说明。")}
            </ul>
          </div>
        </div>
      </div>
    </section>

    <section class="report-section">
      <div class="section-kicker">04 / 图表</div>
      <div class="section-head">
        <div>
          <h2>关键图表</h2>
        </div>
      </div>
      <div class="chart-strip">
        {_render_chart_cards(state, report.chart_specs, label, temporal_only=False)}
        {_render_distribution_cards(state)}
      </div>
      <div class="panel" style="margin-top:18px">
        <div class="section-head">
          <div>
            <h3>图表解读</h3>
          </div>
        </div>
        <div class="grid">
          {_render_analysis_notes(_chart_analysis_items(state, report.chart_specs, section="static"))}
        </div>
      </div>
    </section>

    <section class="report-section">
      <div class="section-kicker">05 / 动态</div>
      <div class="section-head">
        <div>
          <h2>动态行为</h2>
        </div>
      </div>
      <div class="chart-strip">
        {_render_chart_cards(state, report.chart_specs, label, temporal_only=True)}
      </div>
      <div class="panel" style="margin-top:18px">
        <div class="section-head">
          <div>
            <h3>动态行为分析</h3>
          </div>
        </div>
        <div class="grid">
          {_render_analysis_notes(_chart_analysis_items(state, report.chart_specs, section="temporal"))}
        </div>
      </div>
    </section>

    <section class="report-section">
      <div class="section-kicker">06 / 热点</div>
      <div class="section-head">
        <div>
          <h2>热点函数与源码片段</h2>
        </div>
      </div>
      <div class="source-grid">
        {_render_hotspot_spotlights(state, label)}
      </div>
      <div class="panel" style="margin-top:18px">
        <div class="section-head">
          <div>
            <h3>更多源码线索</h3>
          </div>
        </div>
        <div class="source-grid">
          {_render_source_cards(state, label)}
        </div>
      </div>
    </section>

    <section class="report-section">
      <div class="section-kicker">07 / 附录</div>
      <div class="stack">
        <div class="panel">
          <div class="section-head">
            <div>
              <h2>证据明细</h2>
            </div>
          </div>
          <div class="obs-grid">
            {_render_evidence_cards(state)}
          </div>
        </div>
        <div class="panel">
          <div class="section-head">
            <div>
              <h2>原始 observation 视图</h2>
            </div>
          </div>
          <details class="expandable">
            <summary><span class="mono">展开原始 observation 表</span></summary>
            <div class="raw-shell">
              <table class="raw-table">
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
                  {_render_raw_observation_rows(state)}
                </tbody>
              </table>
            </div>
          </details>
        </div>
      </div>
    </section>
  </div>

  <div class="chart-modal" data-chart-modal aria-hidden="true">
    <div class="chart-modal-panel" role="dialog" aria-modal="true" aria-labelledby="chart-modal-title">
      <button class="chart-modal-close" type="button" aria-label="关闭放大视图" data-chart-modal-close>×</button>
      <h3 id="chart-modal-title">图表预览</h3>
      <p class="chart-modal-sub" data-chart-modal-sub>点击空白区域或按 Esc 也可以关闭。</p>
      <div class="chart-modal-body" data-chart-modal-body></div>
    </div>
  </div>

  <script id="report-data" type="application/json">{payload_json}</script>
  <script>
    (() => {{
      const root = document;
      const data = JSON.parse(document.getElementById("report-data").textContent);
      let activeTab = "overview";
      let activeKind = "all";
      let query = "";

      const tabButtons = Array.from(root.querySelectorAll("[data-tab-button]"));
      const panes = Array.from(root.querySelectorAll("[data-tab-pane]"));
      const searchInput = root.querySelector("[data-search-input]");
      const modal = root.querySelector("[data-chart-modal]");
      const modalTitle = root.querySelector("#chart-modal-title");
      const modalSub = root.querySelector("[data-chart-modal-sub]");
      const modalBody = root.querySelector("[data-chart-modal-body]");
      const modalClose = root.querySelector("[data-chart-modal-close]");

      function normalize(text) {{
        return String(text || "").toLowerCase();
      }}

      function applyState() {{
        tabButtons.forEach((button) => {{
          const isActive = button.dataset.tabButton === activeTab;
          button.classList.toggle("is-active", isActive);
        }});
        panes.forEach((pane) => {{
          pane.classList.toggle("is-active", pane.dataset.tabPane === activeTab);
        }});

        root.querySelectorAll("[data-filter-chip]").forEach((chip) => {{
          chip.classList.toggle("is-active", chip.dataset.filterChip === activeKind);
        }});

        root.querySelectorAll("[data-filterable]").forEach((node) => {{
          const kind = node.dataset.kind || "all";
          const hay = normalize(node.dataset.search || "");
          const kindMatched = activeKind === "all" || kind === activeKind || kind.split("|").includes(activeKind);
          const queryMatched = !query || hay.includes(query);
          node.hidden = !(kindMatched && queryMatched);
        }});
      }}

      tabButtons.forEach((button) => {{
        button.addEventListener("click", () => {{
          activeTab = button.dataset.tabButton;
          applyState();
        }});
      }});

      root.querySelectorAll("[data-filter-chip]").forEach((chip) => {{
        chip.addEventListener("click", () => {{
          activeKind = chip.dataset.filterChip || "all";
          applyState();
        }});
      }});

      if (searchInput) {{
        searchInput.addEventListener("input", (event) => {{
          query = normalize(event.target.value);
          applyState();
        }});
      }}

      function closeModal() {{
        if (!modal) {{
          return;
        }}
        modal.classList.remove("is-open");
        modal.setAttribute("aria-hidden", "true");
        document.body.classList.remove("has-modal");
        if (modalBody) {{
          modalBody.innerHTML = "";
        }}
      }}

      function openChartCard(card) {{
        if (!modal || !modalBody || !modalTitle) {{
          return;
        }}
        const title = card.dataset.modalTitle || card.querySelector("h3")?.textContent || "图表预览";
        const description = card.dataset.modalDescription || card.querySelector(".hint")?.textContent || "点击空白区域或按 Esc 关闭。";
        const clone = card.cloneNode(true);
        clone.classList.remove("is-zoomable");
        clone.querySelectorAll("[data-chart-zoom-button]").forEach((button) => button.remove());
        modalTitle.textContent = title;
        if (modalSub) {{
          modalSub.textContent = description;
        }}
        modalBody.innerHTML = "";
        modalBody.appendChild(clone);
        modal.classList.add("is-open");
        modal.setAttribute("aria-hidden", "false");
        document.body.classList.add("has-modal");
      }}

      root.querySelectorAll("[data-chart-card]").forEach((card) => {{
        card.classList.add("is-zoomable");
        card.addEventListener("click", (event) => {{
          if (event.target.closest("[data-chart-zoom-button]")) {{
            return;
          }}
          openChartCard(card);
        }});
        card.addEventListener("keydown", (event) => {{
          if (event.key === "Enter" || event.key === " ") {{
            event.preventDefault();
            openChartCard(card);
          }}
        }});
      }});

      root.querySelectorAll("[data-chart-zoom-button]").forEach((button) => {{
        button.addEventListener("click", (event) => {{
          event.preventDefault();
          event.stopPropagation();
          const card = button.closest("[data-chart-card]");
          if (card) {{
            openChartCard(card);
          }}
        }});
      }});

      if (modalClose) {{
        modalClose.addEventListener("click", closeModal);
      }}
      if (modal) {{
        modal.addEventListener("click", (event) => {{
          if (event.target === modal) {{
            closeModal();
          }}
        }});
      }}
      document.addEventListener("keydown", (event) => {{
        if (event.key === "Escape") {{
          closeModal();
        }}
      }});

      applyState();
      window.__PERF_REPORT_DATA__ = data;
    }})();
  </script>
</body>
</html>
"""


def _build_payload(state: AnalysisState, label: Callable[[str], str]) -> dict[str, Any]:
    report = state.final_report
    assert report is not None
    hypotheses = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
    observations = sorted(state.observations, key=lambda item: (item.source, item.metric, item.scope))
    return {
        "hypothesisKinds": [item.kind for item in hypotheses],
        "observationCount": len(observations),
        "sourceFindingCount": len(report.source_findings),
        "labels": {item.kind: label(item.kind) for item in hypotheses},
    }


def _hero_chips(state: AnalysisState, label: Callable[[str], str]) -> str:
    report = state.final_report
    assert report is not None
    top = max((item.confidence for item in state.hypotheses), default=0.0)
    chips = [
        f"<span class='chip chip--accent'>Top hypothesis {_inline(label(state.hypotheses[0].kind), 32) if state.hypotheses else '未知'} </span>"
        if state.hypotheses
        else "<span class='chip chip--accent'>尚未形成瓶颈候选</span>",
        f"<span class='chip chip--teal'>置信度 {top:.2f}</span>",
        f"<span class='chip'>Observation {len(state.observations)}</span>",
        f"<span class='chip'>源码定位 {len(report.source_findings)}</span>",
        f"<span class='chip'>动作 {len(state.actions_taken)}</span>",
    ]
    return "".join(chips)


def _metric_card(title: str, value_html: str, footnote_html: str) -> str:
    return (
        "<div class='metric-card'>"
        f"<div class='metric-label'>{escape(title)}</div>"
        f"<div class='metric-value'>{value_html}</div>"
        f"<div class='metric-footnote'>{footnote_html}</div>"
        "</div>"
    )


def _panel_items(items: list[str], empty: str) -> str:
    if not items:
        return f"<li>{_inline(empty, 120)}</li>"
    return "".join(f"<li>{_inline(item, 220)}</li>" for item in items)


def _render_hypothesis_cards(state: AnalysisState, label: Callable[[str], str]) -> str:
    hypotheses = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
    if not hypotheses:
        return "<div class='empty'>当前还没有生成候选瓶颈。</div>"
    cards = []
    for item in hypotheses:
        ids = ", ".join(item.supporting_observation_ids[:8]) or "无"
        search_text = " ".join([item.kind, label(item.kind), item.summary, ids, " ".join(item.reasoning_basis)])
        cards.append(
            "<article class='hypothesis-card' "
            f"data-filterable data-kind='{_attr(item.kind)}' data-search='{_attr(search_text)}'>"
            "<div class='hypothesis-top'>"
            f"<div class='hypothesis-title'>{_inline(label(item.kind), 34)}</div>"
            f"<div class='confidence'>confidence={item.confidence:.2f}</div>"
            "</div>"
            f"<div class='bar'><span style='width:{max(6, int(item.confidence * 100))}%'></span></div>"
            f"<p class='hint'>{_inline(item.summary, 220)}</p>"
            "<div class='meta-line'>"
            f"<span class='meta-pill'>{'需要继续验证' if item.needs_verification else '证据基本充分'}</span>"
            f"<span class='meta-pill'>{len(item.supporting_observation_ids)} 条支持证据</span>"
            f"<span class='meta-pill'>{len(item.contradicting_observation_ids)} 条反证</span>"
            "</div>"
            "<div class='expandable' style='margin-top:12px'>"
            f"{_expandable_inline('支持证据 ID', ids, limit=56)}"
            f"{_expandable_inline('推理依据', '；'.join(item.reasoning_basis) or '未记录', limit=72)}"
            "</div>"
            "</article>"
        )
    return "".join(cards)


def _render_chart_cards(
    state: AnalysisState,
    chart_specs,
    label: Callable[[str], str],
    *,
    temporal_only: bool,
) -> str:
    cards: list[str] = []
    for chart_spec in chart_specs:
        is_temporal = chart_spec.focus == "temporal_behavior"
        if temporal_only != is_temporal:
            continue
        body, chart_view = _render_chart_body(state, chart_spec, label)
        if not body:
            continue
        cards.append(
            "<article class='chart-card' tabindex='0' role='button' data-chart-card "
            f"data-chart-view='{_attr(chart_view)}' "
            f"data-modal-title='{_attr(chart_spec.title)}' "
            f"data-modal-description='{_attr(chart_spec.rationale)}'>"
            "<button class='zoom-button' type='button' data-chart-zoom-button>放大</button>"
            f"<h3>{_inline(chart_spec.title, 52)}</h3>"
            f"{body}"
            "</article>"
        )
    if cards:
        return "".join(cards)
    return "<div class='empty'>当前没有足够可靠的时间序列数据。</div>" if temporal_only else "<div class='empty'>当前没有足够可靠的图表数据。</div>"


def _render_distribution_cards(state: AnalysisState) -> str:
    cards = []
    for title, metric, key, suffix in (
        ("热点函数分布", "hot_symbol_pct", "symbol", "%"),
        ("进程级样本拆账", "process_sample_pct", "pid", "%"),
        ("线程级样本拆账", "thread_sample_pct", "tid", "%"),
    ):
        rows = _distribution_rows(state, metric, key, suffix=suffix)
        if not rows:
            continue
        cards.append(
            "<article class='chart-card' tabindex='0' role='button' data-chart-card "
            "data-chart-view='distribution' "
            f"data-modal-title='{_attr(title)}' "
            "data-modal-description='分布图支持放大查看，便于阅读较长的函数名、线程名和进程名。' "
            "data-filterable data-kind='all' "
            f"data-search='{_attr(title + ' ' + ' '.join(row['full'] for row in rows))}'>"
            "<button class='zoom-button' type='button' data-chart-zoom-button>放大</button>"
            f"<h3>{escape(title)}</h3>"
            "<div class='chart-list'>"
            + "".join(_chart_row(row["short"], row["full"], row["value"], suffix) for row in rows)
            + "</div></article>"
        )
    topdown = _topdown_rows(state)
    if topdown:
        cards.append(
            "<article class='chart-card' tabindex='0' role='button' data-chart-card "
            "data-chart-view='distribution' "
            "data-modal-title='Top-Down / TMA 拆分' "
            "data-modal-description='异常值已经做过过滤，放大后更适合对比不同 bound 方向的占比。' "
            "data-filterable data-kind='all' data-search='topdown frontend backend memory'>"
            "<button class='zoom-button' type='button' data-chart-zoom-button>放大</button>"
            "<h3>Top-Down / TMA 拆分</h3>"
            "<div class='chart-list'>"
            + "".join(_chart_row(row["short"], row["full"], row["value"], "%") for row in topdown)
            + "</div></article>"
        )
    return "".join(cards) if cards else "<div class='empty'>当前没有足够的分布型图表数据。</div>"


def _render_source_cards(state: AnalysisState, label: Callable[[str], str]) -> str:
    findings = state.final_report.source_findings if state.final_report is not None else []
    if not findings:
        return "<div class='empty'>当前没有可展示的源码定位结果。</div>"
    cards = []
    for item in findings:
        hypothesis_key = item.related_hypothesis or "all"
        hypothesis_text = label(item.related_hypothesis) if item.related_hypothesis else "未标注"
        line_suffix = f"-{item.line_end}" if item.line_end and item.line_end != item.line_no else ""
        search_text = " ".join(
            [
                item.file_path,
                item.issue_type,
                item.rationale,
                item.symbol_hint or "",
                item.related_hypothesis or "",
            ]
        )
        confidence_pill = (
            f"<span class='meta-pill'>置信度 {item.confidence:.2f}</span>"
            if item.confidence is not None
            else "<span class='meta-pill'>置信度未提供</span>"
        )
        cards.append(
            "<article class='source-card' "
            f"data-filterable data-kind='{_attr(hypothesis_key)}' data-search='{_attr(search_text)}'>"
            f"<h3>{_inline(item.issue_type, 42)}</h3>"
            "<div class='source-meta'>"
            f"<span class='meta-pill'>{_inline(hypothesis_text, 26)}</span>"
            f"<span class='meta-pill'>{_inline(item.mapping_method or '未知', 24)}</span>"
            f"{confidence_pill}"
            + "</div>"
            f"{_expandable_inline('文件', f'{item.file_path}:{item.line_no}{line_suffix}', limit=74)}"
            f"{_expandable_inline('符号', item.symbol_hint or '未记录', limit=74)}"
            f"<p class='hint' style='margin-top:12px'>{_inline(item.rationale, 240)}</p>"
            f"{_render_code_block(item.snippet, item.line_no)}"
            "</article>"
        )
    return "".join(cards)


def _render_observation_cards(state: AnalysisState) -> str:
    observations = _select_focus_observations(state)
    if not observations:
        return "<div class='empty'>当前没有关键 observation。</div>"
    cards = []
    for item in observations:
        label_summary = ", ".join(f"{key}={value}" for key, value in item.labels.items() if value) or "无额外标签"
        cards.append(
            "<article class='observation-card'>"
            f"<div class='obs-metric'>{_inline(_metric_label(item.metric), 42)}</div>"
            f"<div class='obs-value'>{_inline(_format_value(item.value, item.unit), 72)}</div>"
            f"<div class='obs-source'>{_inline(f'{item.source} · {item.scope}', 48)}</div>"
            f"<div class='obs-tags'>{_inline(label_summary, 120)}</div>"
            "</article>"
        )
    return "".join(cards)


def _render_evidence_cards(state: AnalysisState) -> str:
    supported_ids = set()
    for hypothesis in state.hypotheses:
        supported_ids.update(hypothesis.supporting_observation_ids)
    observations = [item for item in state.observations if item.id in supported_ids and _observation_visible(item)]
    observations = sorted(observations, key=lambda item: (item.source, item.metric))[:24]
    if not observations:
        observations = _select_focus_observations(state)
    if not observations:
        return "<div class='empty'>当前没有可展示的证据 observation。</div>"
    cards = []
    id_to_kinds = _observation_to_hypotheses(state)
    for item in observations:
        kinds = id_to_kinds.get(item.id, ["all"])
        search_text = " ".join([item.id, item.source, item.metric, str(item.value), " ".join(item.labels.values())])
        cards.append(
            "<article class='observation-card' "
            f"data-filterable data-kind='{_attr('|'.join(kinds))}' data-search='{_attr(search_text)}'>"
            f"<div class='obs-metric'>{_inline(f'{item.id} · {_metric_label(item.metric)}', 72)}</div>"
            f"<div class='obs-value'>{_inline(_format_value(item.value, item.unit), 80)}</div>"
            f"<div class='obs-source'>{_inline(f'{item.source} · {item.scope} · {item.category}', 72)}</div>"
            f"<div class='obs-tags'>{_inline(', '.join(f'{k}={v}' for k, v in item.labels.items() if v) or '无额外标签', 140)}</div>"
            "</article>"
        )
    return "".join(cards)


def _render_raw_observation_rows(state: AnalysisState) -> str:
    observations = [item for item in state.observations if _observation_visible(item)]
    observations = sorted(observations, key=lambda item: (item.source, item.metric, item.scope))[:180]
    if not observations:
        return "<tr><td colspan='6'>当前没有 observation。</td></tr>"
    rows = []
    for item in observations:
        labels = ", ".join(f"{key}={value}" for key, value in item.labels.items() if value) or "-"
        rows.append(
            "<tr data-filterable data-kind='all' "
            f"data-search='{_attr(' '.join([item.id, item.source, item.metric, str(item.value), labels]))}'>"
            f"<td><code>{escape(item.id)}</code></td>"
            f"<td>{_inline(item.source, 24)}</td>"
            f"<td>{_expandable_inline('', item.metric, limit=36)}</td>"
            f"<td>{_inline(_format_value(item.value, item.unit), 42)}</td>"
            f"<td>{_inline(item.scope, 18)}</td>"
            f"<td>{_expandable_inline('', labels, limit=62)}</td>"
            "</tr>"
        )
    return "".join(rows)


def _render_filter_chips(state: AnalysisState, label: Callable[[str], str]) -> str:
    hypotheses = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
    chips = ["<button class='filter-chip is-active' data-filter-chip='all'>全部</button>"]
    for item in hypotheses[:6]:
        chips.append(
            f"<button class='filter-chip' data-filter-chip='{_attr(item.kind)}'>{_inline(label(item.kind), 24)}</button>"
        )
    return "".join(chips)


def _render_chart_body(state: AnalysisState, chart_spec, label: Callable[[str], str]) -> tuple[str, str]:
    if chart_spec.chart_id == "hypothesis-confidence":
        hypotheses = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
        return (
            "<div class='chart-list'>"
            + "".join(
                _chart_row(label(item.kind), label(item.kind), item.confidence * 100.0, "%", searchable=item.summary)
                for item in hypotheses[:5]
            )
            + "</div>"
        , "distribution") if hypotheses else ("", "distribution")
    if chart_spec.chart_id == "hotspot-symbols":
        rows = _distribution_rows(state, "hot_symbol_pct", "symbol", suffix="%")
        return (
            "<div class='chart-list'>" + "".join(_chart_row(row["short"], row["full"], row["value"], "%") for row in rows) + "</div>",
            "distribution",
        ) if rows else ("", "distribution")
    if chart_spec.chart_id == "process-sample-breakdown":
        rows = _distribution_rows(state, "process_sample_pct", "pid", suffix="%")
        return (
            "<div class='chart-list'>" + "".join(_chart_row(row["short"], row["full"], row["value"], "%") for row in rows) + "</div>",
            "distribution",
        ) if rows else ("", "distribution")
    if chart_spec.chart_id == "thread-sample-breakdown":
        rows = _distribution_rows(state, "thread_sample_pct", "tid", suffix="%")
        return (
            "<div class='chart-list'>" + "".join(_chart_row(row["short"], row["full"], row["value"], "%") for row in rows) + "</div>",
            "distribution",
        ) if rows else ("", "distribution")
    if chart_spec.chart_id == "topdown-breakdown":
        rows = _topdown_rows(state)
        return (
            "<div class='chart-list'>" + "".join(_chart_row(row["short"], row["full"], row["value"], "%") for row in rows) + "</div>",
            "distribution",
        ) if rows else ("", "distribution")
    if chart_spec.chart_type == "multiline" and chart_spec.metrics:
        svg = _render_timeline_multi_line_chart(state, chart_spec.metrics)
        return (svg, "line") if svg else ("", "line")
    if chart_spec.chart_type == "line" and chart_spec.metrics:
        svg = _render_timeline_line_chart(state, chart_spec.metrics[0])
        return (svg, "line") if svg else ("", "line")
    return "", "distribution"


def _distribution_rows(state: AnalysisState, metric: str, label_key: str, suffix: str = "") -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    for observation in state.observations:
        if observation.metric != metric:
            continue
        label_text = _distribution_label(observation, label_key)
        value = _normalize_percent(observation.value, strict_upper_bound=100.0)
        if value is None:
            continue
        items.append(
            {
                "full": label_text,
                "short": _compact_identifier(label_text, limit=52),
                "value": value,
                "suffix": suffix,
            }
        )
    if metric == "hot_symbol_pct":
        filtered = [
            item
            for item in items
            if item["value"] >= 10.0 and not _is_noise_symbol(item["full"]) and not _is_library_symbol(item["full"])
        ]
        if filtered:
            items = filtered
    return items[:6]


def _topdown_rows(state: AnalysisState) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for metric in TOPDOWN_METRICS:
        candidates = [
            observation
            for observation in state.observations
            if observation.metric == metric and isinstance(observation.value, (int, float))
        ]
        if not candidates:
            continue
        observation = candidates[-1]
        value = _normalize_percent(observation.value, strict_upper_bound=100.0)
        if value is None:
            continue
        rows.append({"full": metric, "short": _metric_label(metric), "value": value})
    return rows[:6]


def _timeline_cards(state: AnalysisState) -> list[str]:
    cards: list[str] = []
    available = _available_timeline_metrics(state)
    for metric in TIMELINE_PREFERRED_METRICS:
        if metric not in available:
            continue
        svg = _render_timeline_line_chart(state, metric)
        if not svg:
            continue
        cards.append(
            "<article class='chart-card' tabindex='0' role='button' data-chart-card "
            "data-chart-view='line' "
            f"data-modal-title='{_attr(_metric_label(metric) + ' 时间序列')}' "
            "data-modal-description='点击后会放大成阅读友好的时间序列视图，更适合观察阶段性抖动、拐点和退化时刻。' "
            "data-filterable data-kind='all' "
            f"data-search='{_attr(metric)}'>"
            "<button class='zoom-button' type='button' data-chart-zoom-button>放大</button>"
            f"<h3>{_inline(_metric_label(metric) + ' 时间序列', 40)}</h3>"
            f"{svg}</article>"
        )
    return cards[:3]


def _render_timeline_line_chart(state: AnalysisState, metric: str) -> str:
    return _render_timeline_multi_line_chart(state, [metric])


def _render_timeline_multi_line_chart(state: AnalysisState, metrics: list[str]) -> str:
    series = []
    for metric in metrics:
        points = _timeline_points(state, metric)
        if len(points) < 2:
            continue
        series.append((metric, points))
    if not series:
        return ""

    xs = [x for _, points in series for x, _ in points]
    ys = [y for _, points in series for _, y in points]
    min_x, max_x = min(xs), max(xs)
    percent_like = all(metric.endswith("_pct") or metric.endswith("_rate_pct") for metric, _ in series)
    min_y = 0.0 if percent_like else min(ys)
    max_y = 100.0 if percent_like else max(ys)
    if min_y == max_y:
        max_y += 1.0

    width = 620
    height = 240
    left = 54
    right = 26
    top = 26
    bottom = 62
    plot_w = width - left - right
    plot_h = height - top - bottom
    colors = ["#2563eb", "#0f766e", "#d97706", "#7c3aed", "#dc2626"]
    grid_lines = []
    for ratio in (0.0, 0.25, 0.5, 0.75, 1.0):
        y = top + (1.0 - ratio) * plot_h
        value = min_y + (max_y - min_y) * ratio
        grid_lines.append(
            f"<line x1='{left}' y1='{y:.2f}' x2='{left + plot_w}' y2='{y:.2f}' stroke='rgba(70,112,168,0.18)' stroke-width='1' />"
            f"<text x='8' y='{y + 4:.2f}' font-size='12' fill='#5f7390'>{value:.1f}{'%' if percent_like else ''}</text>"
        )

    paths = []
    legends = []
    for index, (metric, points) in enumerate(series):
        color = colors[index % len(colors)]
        path_parts = []
        dots = []
        for x, y in points:
            plot_x = left + (0 if max_x == min_x else (x - min_x) / (max_x - min_x) * plot_w)
            plot_y = top + (1.0 - (y - min_y) / (max_y - min_y)) * plot_h
            path_parts.append(f"{plot_x:.2f},{plot_y:.2f}")
            dots.append(
                f"<circle cx='{plot_x:.2f}' cy='{plot_y:.2f}' r='2.8' fill='{color}'>"
                f"<title>{escape(_metric_label(metric))}: {y:.2f}{'%' if metric.endswith('_pct') else ''} @ {x:.2f}s</title></circle>"
            )
        path_d = " L ".join(path_parts)
        paths.append(
            f"<path d='M {path_d}' fill='none' stroke='{color}' stroke-width='3.4' stroke-linecap='round' stroke-linejoin='round' />"
            + "".join(dots)
        )
        legend_x = left + index * 132
        legends.append(
            f"<g><line x1='{legend_x}' y1='{height - 24}' x2='{legend_x + 18}' y2='{height - 24}' stroke='{color}' stroke-width='4' stroke-linecap='round' />"
            f"<text x='{legend_x + 24}' y='{height - 20}' font-size='12' fill='#28405e'>{escape(_metric_label(metric))}</text></g>"
        )

    return (
        f"<svg class='line-chart' viewBox='0 0 {width} {height}' role='img' aria-label='{_attr(','.join(metrics))}'>"
        + "".join(grid_lines)
        + f"<line x1='{left}' y1='{top + plot_h}' x2='{left + plot_w}' y2='{top + plot_h}' stroke='rgba(70,112,168,0.26)' stroke-width='1.2' />"
        + f"<line x1='{left}' y1='{top}' x2='{left}' y2='{top + plot_h}' stroke='rgba(70,112,168,0.26)' stroke-width='1.2' />"
        + "".join(paths)
        + f"<text x='{left}' y='{height - 40}' font-size='12' fill='#5f7390'>{min_x:.2f}s</text>"
        + f"<text x='{left + plot_w - 28}' y='{height - 40}' font-size='12' fill='#5f7390'>{max_x:.2f}s</text>"
        + "".join(legends)
        + "</svg>"
    )


def _timeline_points(state: AnalysisState, metric: str) -> list[tuple[float, float]]:
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
    return points


def _chart_row(short_text: str, full_text: str, value: float, suffix: str, searchable: str | None = None) -> str:
    width = max(8, min(100, int(value)))
    label_block = _expandable_inline("", full_text, limit=52, custom_compact=short_text)
    return (
        "<div class='chart-row'>"
        "<div class='chart-label'>"
        f"<strong>{label_block}</strong>"
        f"<span class='chart-value'>{value:.2f}{escape(suffix)}</span>"
        "</div>"
        f"<div class='bar'><span style='width:{width}%'></span></div>"
        "</div>"
    )


def _render_artifacts(artifacts: list[str]) -> str:
    if not artifacts:
        return "<div class='empty'>当前没有产物路径。</div>"
    return "".join(f"<div class='artifact-item'>{_inline(path, 108)}</div>" for path in artifacts)


def _select_focus_observations(state: AnalysisState):
    wanted_metrics = {
        "ipc",
        "cycles",
        "instructions",
        "cache_misses",
        "cache_miss_rate_pct",
        "branch_misses",
        "branch_miss_rate_pct",
        "l1_miss_rate_pct",
        "l2_miss_rate_pct",
        "l3_miss_rate_pct",
        "llc_miss_rate_pct",
        "context_switches",
        "cpu_utilization_pct",
        "process_sample_pct",
        "thread_sample_pct",
        "topdown_be_bound_pct",
        "topdown_fe_bound_pct",
        "topdown_retiring_pct",
        "topdown_bad_spec_pct",
    }
    supported_ids = []
    for hypothesis in sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)[:3]:
        supported_ids.extend(hypothesis.supporting_observation_ids[:4])
    chosen = []
    seen = set()
    for observation in state.observations:
        if observation.id in supported_ids or observation.metric in wanted_metrics:
            if observation.id in seen:
                continue
            seen.add(observation.id)
            chosen.append(observation)
    return chosen[:10]


def _observation_to_hypotheses(state: AnalysisState) -> dict[str, list[str]]:
    mapping: dict[str, list[str]] = {}
    for hypothesis in state.hypotheses:
        for obs_id in hypothesis.supporting_observation_ids:
            mapping.setdefault(obs_id, []).append(hypothesis.kind)
    return mapping


def _observation_visible(observation) -> bool:
    if observation.metric != "hot_symbol_pct":
        return True
    symbol = observation.labels.get("symbol", "")
    value = _normalize_percent(observation.value, strict_upper_bound=100.0)
    if value is None or value < 10.0:
        return False
    if _is_noise_symbol(symbol) or _is_library_symbol(symbol):
        return False
    return True


def _available_timeline_metrics(state: AnalysisState) -> set[str]:
    counts: dict[str, int] = {}
    for observation in state.observations:
        if observation.labels.get("series_type") != "timeline":
            continue
        counts[observation.metric] = counts.get(observation.metric, 0) + 1
    return {metric for metric, count in counts.items() if count >= 2}


def _render_code_block(snippet: str, line_start: int) -> str:
    text = _sanitize_block(snippet)
    lines = text.splitlines() or [""]
    parsed_lines: list[tuple[int | None, str]] = []
    numbered_count = 0
    for line in lines:
        match = re.match(r"^\s*(\d+)\s*\|\s?(.*)$", line)
        if match:
            numbered_count += 1
            parsed_lines.append((int(match.group(1)), match.group(2)))
        else:
            parsed_lines.append((None, line))
    use_embedded_numbers = numbered_count >= max(1, len(lines) // 2)
    rows = []
    current = line_start
    for embedded_line_no, line in parsed_lines:
        display_line_no = embedded_line_no if use_embedded_numbers and embedded_line_no is not None else current
        rows.append(
            "<div class='code-row'>"
            f"<div class='code-line-no'>{display_line_no}</div>"
            f"<div class='code-line'>{escape(line) if line else '&nbsp;'}</div>"
            "</div>"
        )
        current += 1
    return "<div class='code-block'>" + "".join(rows) + "</div>"


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


def _is_noise_symbol(name: str) -> bool:
    lowered = name.lower()
    return any(pattern in lowered for pattern in NOISE_SYMBOL_PATTERNS)


def _is_library_symbol(name: str) -> bool:
    lowered = name.lower()
    if lowered.startswith("__") or lowered.startswith("std::"):
        return True
    if lowered.startswith("operator new") or lowered.startswith("operator delete"):
        return True
    if "@@glibc" in lowered or "libstdc++" in lowered or "libm" in lowered:
        return True
    if "__cos" in lowered or "__sin" in lowered or "__mem" in lowered:
        return True
    if lowered.startswith("pthread_") or "malloc" in lowered or "free" in lowered:
        return True
    return False


def _metric_label(metric: str) -> str:
    labels = {
        "ipc": "IPC",
        "cpi": "CPI",
        "cycles": "Cycles",
        "instructions": "Instructions",
        "cache_misses": "Cache Misses",
        "cache_miss_rate_pct": "Cache Miss Rate",
        "cache_mpki": "Cache MPKI",
        "branch_misses": "Branch Misses",
        "branch_miss_rate_pct": "Branch Miss Rate",
        "branch_mpki": "Branch MPKI",
        "context_switches": "Context Switches",
        "l1_miss_rate_pct": "L1 Miss Rate",
        "l1_mpki": "L1 MPKI",
        "l2_miss_rate_pct": "L2 Miss Rate",
        "l2_mpki": "L2 MPKI",
        "l3_miss_rate_pct": "L3 Miss Rate",
        "l3_mpki": "L3 MPKI",
        "llc_miss_rate_pct": "LLC Miss Rate",
        "llc_mpki": "LLC MPKI",
        "cpu_utilization_pct": "CPU 利用率",
        "hot_symbol_pct": "热点函数占比",
        "process_sample_pct": "进程样本占比",
        "thread_sample_pct": "线程样本占比",
        "topdown_be_bound_pct": "Backend Bound",
        "topdown_fe_bound_pct": "Frontend Bound",
        "topdown_retiring_pct": "Retiring",
        "topdown_bad_spec_pct": "Bad Speculation",
        "tma_memory_bound_pct": "Memory Bound",
        "tma_fetch_latency_pct": "Fetch Latency",
        "tma_branch_mispredicts_pct": "Branch Mispredicts",
    }
    return labels.get(metric, metric.replace("_", " "))


def _format_value(value: Any, unit: str | None) -> str:
    if isinstance(value, float):
        rendered = f"{value:.2f}"
    else:
        rendered = str(value)
    if unit:
        rendered = f"{rendered} {unit}"
    return rendered


def _normalize_percent(value: Any, strict_upper_bound: float) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    if parsed > strict_upper_bound * 10:
        return None
    return min(parsed, strict_upper_bound)


def _expandable_inline(label: str, text: str, limit: int = 64, custom_compact: str | None = None) -> str:
    sanitized = _sanitize_inline(text)
    compact = custom_compact or _compact_identifier(sanitized, limit=limit)
    if len(sanitized) <= limit and compact == sanitized:
        if label:
            return f"<span class='mono'>{escape(label)}: {escape(sanitized)}</span>"
        return f"<span class='mono'>{escape(sanitized)}</span>"
    summary = f"{escape(label)}: {escape(compact)}" if label else escape(compact)
    return (
        "<div class='expandable'>"
        "<details>"
        f"<summary>{summary}<span class='inline-toggle'>展开</span></summary>"
        f"<div class='expandable-body'>{escape(sanitized)}</div>"
        "</details>"
        "</div>"
    )


def _compact_identifier(value: str, limit: int = 64) -> str:
    text = _sanitize_inline(value)
    if "::" in text:
        segments = text.split("::")
        if len(segments) > 3:
            text = "…::" + "::".join(segments[-3:])
    text = re.sub(r"<[^<>]{16,}>", "<…>", text)
    text = re.sub(r"\([^()]{18,}\)", "(…)", text)
    text = re.sub(r"\s+", " ", text).strip()
    return _smart_truncate(text, limit)


def _compact_path(value: str, limit: int = 72) -> str:
    text = _sanitize_inline(value)
    if len(text) <= limit:
        return escape(text)
    parts = text.split("/")
    if len(parts) > 4:
        text = "/".join([parts[0], "…", *parts[-3:]])
    return escape(_smart_truncate(text, limit))


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
    head = max(8, int(limit * 0.56))
    tail = max(5, limit - head - 3)
    return f"{value[:head]}...{value[-tail:]}"


def _inline(value: str, limit: int = 72) -> str:
    text = _sanitize_inline(value)
    display = _smart_truncate(text, limit)
    return f"<span title='{_attr(text)}'>{escape(display)}</span>"


def _attr(value: str) -> str:
    return escape(_sanitize_inline(value), quote=True)


def _format_frequency_range(environment) -> str:
    def compact(value: str | None) -> str | None:
        if not value:
            return None
        text = value.strip()
        if text.endswith("%"):
            return text
        try:
            mhz = float(text)
        except ValueError:
            return text
        if mhz >= 1000:
            return f"{mhz / 1000:.2f} GHz"
        return f"{mhz:.0f} MHz"

    min_freq = compact(environment.cpu_min_mhz)
    max_freq = compact(environment.cpu_max_mhz)
    scaling = compact(environment.cpu_scaling_mhz)
    if min_freq and max_freq:
        summary = f"{min_freq} - {max_freq}"
    elif max_freq:
        summary = f"最高 {max_freq}"
    elif min_freq:
        summary = f"最低 {min_freq}"
    else:
        summary = "未知"
    if scaling and scaling.endswith("%"):
        summary = f"{summary}，当前缩放 {scaling}"
    elif scaling and scaling != summary:
        summary = f"{summary}，当前 {scaling}"
    return summary


def _format_cache_line(environment) -> str:
    parts = []
    for label, value in (
        ("L1d", environment.l1d_cache),
        ("L1i", environment.l1i_cache),
        ("L2", environment.l2_cache),
        ("L3", environment.l3_cache),
    ):
        if value:
            parts.append(f"{label} {value}")
    return " / ".join(parts) if parts else "未知"


def _environment_capacity_items(state: AnalysisState) -> list[str]:
    environment = state.environment
    items = [
        f"操作系统: {environment.os_name or '未知'}",
        f"频率范围: {_format_frequency_range(environment)}",
        f"缓存配置: {_format_cache_line(environment)}",
        f"NUMA: {environment.numa_nodes if environment.numa_nodes is not None else '未知'} 节点",
        f"符号状态: {'保留符号' if environment.executable_has_symbols else '可能缺失'}",
        f"隔离运行: {environment.selected_sandbox_runtime or 'none'}",
    ]
    return items


def _render_command_notes(state: AnalysisState) -> str:
    items = _command_context_items(state)
    if not items:
        items = ["当前命令没有检测到额外的启动器、绑核或环境注入信息。"]
    return "".join(f"<div class='command-note'>{_inline(item, 220)}</div>" for item in items)


def _command_context_items(state: AnalysisState) -> list[str]:
    command = list(state.target_cmd)
    if not command and state.executable_path:
        command = [state.executable_path, *state.target_args]
    if not command:
        return ["当前是 PID 附着模式，未记录完整启动命令。"]

    items: list[str] = []
    head_names = [segment.rsplit("/", 1)[-1] for segment in command]
    lower = [token.lower() for token in head_names]

    if any(token in {"mpirun", "mpiexec", "orterun"} for token in lower):
        proc_count = _first_option_value(command, ["-np", "-n"])
        suffix = f"，申请的并发进程数约为 {proc_count}" if proc_count else ""
        items.append(f"检测到 MPI 启动器，程序通过多进程并行方式运行{suffix}。")
    if "taskset" in lower:
        cpu_list = _first_option_value(command, ["-c", "--cpu-list"])
        items.append(f"检测到 taskset 绑核{f'，CPU 列表为 {cpu_list}' if cpu_list else ''}。")
    if "numactl" in lower:
        cpu_bind = _first_option_value(command, ["--physcpubind", "-C"])
        mem_bind = _first_option_value(command, ["--membind", "-m"])
        detail = []
        if cpu_bind:
            detail.append(f"CPU 绑定 {cpu_bind}")
        if mem_bind:
            detail.append(f"内存节点 {mem_bind}")
        items.append(f"检测到 numactl 启动参数{'，' + '，'.join(detail) if detail else ''}。")

    env_assignments = [token for token in command[:6] if "=" in token and not token.startswith("-")]
    if env_assignments:
        items.append(f"命令前缀包含环境变量注入: {', '.join(env_assignments[:4])}。")
    if state.cwd:
        items.append(f"工作目录: {state.cwd}。")
    if state.source_dir:
        items.append(f"源码目录: {state.source_dir}，当前索引源码文件 {len(state.source_files)} 个。")
    if state.build_cmd:
        items.append(f"构建命令: {' '.join(state.build_cmd)}。")
    return items


def _first_option_value(command: list[str], options: list[str]) -> str | None:
    for index, token in enumerate(command[:-1]):
        if token in options:
            return command[index + 1]
    return None


def _chart_analysis_items(state: AnalysisState, chart_specs, section: str) -> list[str]:
    items: list[str] = []
    top = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
    if top and section == "static":
        items.append(f"当前主要结论是 {top[0].summary}")
    relevant_specs = [spec for spec in chart_specs if (spec.focus == "temporal_behavior") == (section == "temporal")]
    for chart_spec in relevant_specs[:4]:
        items.append(f"{chart_spec.title}: {chart_spec.rationale}")
    if section == "static":
        hotspot_rows = _distribution_rows(state, "hot_symbol_pct", "symbol", suffix="%")
        if hotspot_rows:
            hottest = hotspot_rows[0]
            items.append(f"perf record 显示最热符号是 {hottest['full']}，样本占比约 {hottest['value']:.2f}%。")
        thread_rows = _distribution_rows(state, "thread_sample_pct", "tid", suffix="%")
        if len(thread_rows) >= 2:
            spread = ", ".join(f"{row['short']} {row['value']:.1f}%" for row in thread_rows[:3])
            items.append(f"线程级样本拆账用于判断并发工作是否均匀分布；当前主要线程分布为 {spread}。")
    else:
        timeline_metrics = _prioritized_timeline_metrics(_available_timeline_metrics(state))
        if timeline_metrics:
            items.append(f"当前已形成的动态指标包括 {', '.join(_metric_label(metric) for metric in timeline_metrics[:6])}。")
        for metric in (
            "cache_miss_rate_pct",
            "cache_mpki",
            "l1_miss_rate_pct",
            "l1_mpki",
            "l2_miss_rate_pct",
            "l2_mpki",
            "llc_miss_rate_pct",
            "llc_mpki",
            "ipc",
            "cpi",
            "branch_miss_rate_pct",
            "branch_mpki",
        ):
            summary = _timeline_variation_summary(state, metric)
            if summary:
                items.append(summary)
    return items[:6]


def _timeline_variation_summary(state: AnalysisState, metric: str) -> str | None:
    points = _timeline_points(state, metric)
    if len(points) < 2:
        return None
    values = [value for _, value in points]
    min_value = min(values)
    max_value = max(values)
    delta = max_value - min_value
    if metric.endswith("_pct") and delta < 1.0:
        return None
    if metric == "ipc" and delta < 0.08:
        return None
    peak_time = max(points, key=lambda item: item[1])[0]
    low_time = min(points, key=lambda item: item[1])[0]
    unit = "%" if metric.endswith("_pct") else ""
    return (
        f"{_metric_label(metric)} 在 {low_time:.2f}s 到 {peak_time:.2f}s 之间出现明显波动，"
        f"区间范围约为 {min_value:.2f}{unit} 到 {max_value:.2f}{unit}。"
    )


def _prioritized_timeline_metrics(metrics: set[str]) -> list[str]:
    order = [
        "cache_miss_rate_pct",
        "cache_mpki",
        "l1_miss_rate_pct",
        "l1_mpki",
        "l2_miss_rate_pct",
        "l2_mpki",
        "l3_miss_rate_pct",
        "l3_mpki",
        "llc_miss_rate_pct",
        "llc_mpki",
        "ipc",
        "cpi",
        "branch_miss_rate_pct",
        "branch_mpki",
        "context_switches",
        "cache_misses",
        "branches",
        "branch_misses",
        "cache_references",
    ]
    ranked = [metric for metric in order if metric in metrics]
    extras = sorted(metric for metric in metrics if metric not in ranked)
    return ranked + extras


def _render_analysis_notes(items: list[str]) -> str:
    if not items:
        return "<div class='analysis-note'>当前没有额外的图表解读说明。</div>"
    return "".join(f"<div class='analysis-note'>{_inline(item, 260)}</div>" for item in items)


def _render_hotspot_spotlights(state: AnalysisState, label: Callable[[str], str]) -> str:
    findings = state.final_report.source_findings if state.final_report is not None else []
    rows = _distribution_rows(state, "hot_symbol_pct", "symbol", suffix="%")
    if not rows and not findings:
        return "<div class='empty'>当前没有可展示的热点函数或源码映射。</div>"

    cards: list[str] = []
    used_findings: set[int] = set()
    for row in rows[:6]:
        finding_index, finding = _match_finding_for_symbol(row["full"], findings)
        if finding_index is not None:
            used_findings.add(finding_index)
        hypothesis_text = label(finding.related_hypothesis) if finding and finding.related_hypothesis else "热点路径"
        cards.append(
            "<article class='source-card' data-filterable data-kind='all' "
            f"data-search='{_attr(row['full'] + ' ' + (finding.file_path if finding else '') + ' ' + (finding.rationale if finding else ''))}'>"
            "<div class='hypothesis-top'>"
            f"<div class='hypothesis-title'>{_inline(_compact_identifier(row['full'], 88), 120)}</div>"
            f"<div class='hotspot-share'>{row['value']:.2f}% samples</div>"
            "</div>"
            "<div class='source-meta'>"
            f"<span class='meta-pill'>{_inline(hypothesis_text, 26)}</span>"
            f"<span class='meta-pill'>perf record 热点</span>"
            + (
                f"<span class='meta-pill'>{_inline(finding.mapping_method or '源码映射', 20)}</span>"
                if finding
                else "<span class='meta-pill'>暂未映射源码</span>"
            )
            + "</div>"
            f"{_expandable_inline('函数', row['full'], limit=78, custom_compact=row['short'])}"
            + (
                f"{_expandable_inline('文件', f'{finding.file_path}:{finding.line_no}' if finding else '未映射', limit=78)}"
                if finding
                else ""
            )
            + (
                f"<p class='hint' style='margin-top:12px'>{_inline(finding.rationale, 220)}</p>{_render_code_block(finding.snippet, finding.line_no)}"
                if finding
                else "<p class='hint' style='margin-top:12px'>当前已经识别到热点符号，但还没有对应的源码片段可展示。</p>"
            )
            + "</article>"
        )

    for index, finding in enumerate(findings):
        if index in used_findings:
            continue
        hypothesis_text = label(finding.related_hypothesis) if finding.related_hypothesis else "源码线索"
        cards.append(
            "<article class='source-card' data-filterable data-kind='all' "
            f"data-search='{_attr((finding.symbol_hint or '') + ' ' + finding.file_path + ' ' + finding.rationale)}'>"
            "<div class='hypothesis-top'>"
            f"<div class='hypothesis-title'>{_inline(finding.symbol_hint or finding.issue_type, 96)}</div>"
            "<div class='hotspot-share'>source map</div>"
            "</div>"
            "<div class='source-meta'>"
            f"<span class='meta-pill'>{_inline(hypothesis_text, 26)}</span>"
            f"<span class='meta-pill'>{_inline(finding.mapping_method or '源码映射', 20)}</span>"
            "</div>"
            f"{_expandable_inline('文件', f'{finding.file_path}:{finding.line_no}', limit=78)}"
            f"<p class='hint' style='margin-top:12px'>{_inline(finding.rationale, 220)}</p>"
            f"{_render_code_block(finding.snippet, finding.line_no)}"
            "</article>"
        )
    return "".join(cards[:8])


def _match_finding_for_symbol(symbol: str, findings: list) -> tuple[int | None, Any | None]:
    normalized_symbol = _normalize_symbol(symbol)
    for index, finding in enumerate(findings):
        hint = _normalize_symbol(finding.symbol_hint or "")
        if normalized_symbol and hint and (normalized_symbol in hint or hint in normalized_symbol):
            return index, finding
    return None, None


def _normalize_symbol(value: str) -> str:
    text = _sanitize_inline(value).lower()
    text = re.sub(r"<[^>]+>", "", text)
    return re.sub(r"\s+", "", text)
