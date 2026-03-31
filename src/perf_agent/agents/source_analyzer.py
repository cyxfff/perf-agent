from __future__ import annotations

from pathlib import Path
import subprocess

from perf_agent.models.report import SourceFinding
from perf_agent.models.state import AnalysisState


class SourceAnalyzer:
    def run(self, state: AnalysisState) -> AnalysisState:
        if not state.source_files or not state.hypotheses:
            state.add_audit("source_analyzer", "skipped source analysis", source_files=len(state.source_files))
            return state

        ordered = sorted(state.hypotheses, key=lambda item: item.confidence, reverse=True)
        top = ordered[0]
        findings: list[SourceFinding] = []
        findings.extend(self._addr2line_findings(state, top.kind))

        prioritized_files = self._prioritize_files(state)
        hot_symbols = self._hot_symbols(state)
        for file_path in prioritized_files[:120]:
            if len(findings) >= 10:
                break
            path = Path(file_path)
            try:
                lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                continue
            findings.extend(self._scan_hot_symbols(path, lines, hot_symbols, top.kind))
            findings.extend(self._scan_file(path, lines, top.kind))

        state.source_findings = self._deduplicate(findings)[:8]
        state.add_audit(
            "source_analyzer",
            "completed source scan",
            finding_count=len(state.source_findings),
            top_hypothesis=top.kind,
            addr2line_mapped=sum(1 for item in state.source_findings if item.mapping_method == "addr2line"),
        )
        return state

    def _addr2line_findings(self, state: AnalysisState, hypothesis_kind: str) -> list[SourceFinding]:
        executable = self._target_executable_path(state)
        if executable is None or not executable.exists() or not state.environment.supports_addr2line:
            return []

        frame_observations = [
            observation
            for observation in state.observations
            if observation.metric == "hot_frame_sample_pct"
            and observation.labels.get("ip")
            and self._dso_matches_target(observation.labels.get("dso", ""), executable)
        ]
        if not frame_observations:
            return []

        unique_by_ip: dict[str, object] = {}
        for observation in frame_observations:
            ip = observation.labels.get("ip", "")
            if ip not in unique_by_ip:
                unique_by_ip[ip] = observation
        selected = sorted(
            unique_by_ip.values(),
            key=lambda item: float(item.value) if isinstance(item.value, (int, float)) else 0.0,
            reverse=True,
        )[:8]
        if not selected:
            return []

        addresses = [f"0x{item.labels.get('ip', '').lower().lstrip('0x')}" for item in selected if item.labels.get("ip")]
        resolved = self._addr2line_batch(executable, addresses)
        findings: list[SourceFinding] = []
        for observation, address in zip(selected, addresses):
            mapping = resolved.get(address)
            if mapping is None:
                continue
            symbol_name, file_hint, line_no = mapping
            if line_no <= 0:
                continue
            resolved_path = self._resolve_source_path(state, file_hint)
            if resolved_path is None:
                continue
            snippet, start_line, end_line = self._snippet_context(resolved_path, line_no)
            findings.append(
                SourceFinding(
                    file_path=str(resolved_path),
                    line_no=line_no,
                    line_end=end_line,
                    symbol_hint=symbol_name or observation.labels.get("symbol"),
                    issue_type="addr2line 热点定位",
                    rationale=(
                        f"perf record 样本中 {observation.labels.get('symbol', symbol_name or '未知符号')} 占 "
                        f"{float(observation.value):.2f}%，地址 {address} 通过 addr2line 映射到该源码位置。"
                    ),
                    snippet=snippet,
                    related_hypothesis=hypothesis_kind,
                    mapping_method="addr2line",
                    confidence=round(float(observation.normalized_value or 0.0), 4),
                )
            )
        return findings

    def _hot_symbols(self, state: AnalysisState) -> list[str]:
        symbols: list[str] = []
        for observation in state.observations:
            symbol = observation.labels.get("symbol")
            if observation.metric in {"hot_symbol_pct", "hot_frame_sample_pct"} and symbol and not symbol.startswith("0x") and symbol not in symbols:
                symbols.append(symbol)
        return symbols[:8]

    def _prioritize_files(self, state: AnalysisState) -> list[str]:
        files = list(state.source_files)
        executable_name = ""
        if state.executable_path:
            executable_name = Path(state.executable_path).stem.lower()
        elif state.target_cmd:
            executable_name = Path(state.target_cmd[0]).stem.lower()
        if not executable_name:
            return files

        matching = [item for item in files if executable_name in Path(item).stem.lower()]
        if matching:
            return matching
        return files

    def _scan_file(self, path: Path, lines: list[str], hypothesis_kind: str) -> list[SourceFinding]:
        findings: list[SourceFinding] = []
        rules = self._rules_for(hypothesis_kind)
        for index, line in enumerate(lines, start=1):
            lowered = line.lower()
            for issue_type, keywords, rationale in rules:
                if any(keyword in lowered for keyword in keywords):
                    snippet, start_line, end_line = self._snippet_context(path, index, lines=lines)
                    findings.append(
                        SourceFinding(
                            file_path=str(path),
                            line_no=index,
                            line_end=end_line,
                            symbol_hint=self._symbol_hint(lines, index),
                            issue_type=issue_type,
                            rationale=rationale,
                            snippet=snippet,
                            related_hypothesis=hypothesis_kind,
                            mapping_method="heuristic",
                            confidence=0.35,
                        )
                    )
                    if len(findings) >= 2:
                        return findings
        return findings

    def _scan_hot_symbols(
        self,
        path: Path,
        lines: list[str],
        hot_symbols: list[str],
        hypothesis_kind: str,
    ) -> list[SourceFinding]:
        findings: list[SourceFinding] = []
        simplified = [self._simplify_symbol(item) for item in hot_symbols]
        for index, line in enumerate(lines, start=1):
            lowered = line.lower()
            for symbol in simplified:
                if not symbol:
                    continue
                if symbol.lower() not in lowered:
                    continue
                snippet, start_line, end_line = self._snippet_context(path, index, lines=lines)
                findings.append(
                    SourceFinding(
                        file_path=str(path),
                        line_no=index,
                        line_end=end_line,
                        symbol_hint=symbol,
                        issue_type="热点函数定位",
                        rationale=f"perf record / report 显示热点符号 {symbol}，该源码位置与热点调用路径直接相关。",
                        snippet=snippet,
                        related_hypothesis=hypothesis_kind,
                        mapping_method="symbol_scan",
                        confidence=0.5,
                    )
                )
                if len(findings) >= 3:
                    return findings
        return findings

    def _rules_for(self, hypothesis_kind: str) -> list[tuple[str, tuple[str, ...], str]]:
        mapping = {
            "cpu_bound": [
                ("热点循环", ("for (", "while (", "std::sin", "std::cos", "sqrt(", "exp("), "检测到疑似高频计算循环或数学函数调用。"),
                ("大规模向量处理", ("std::vector", "reserve(", "push_back("), "检测到可能参与高频数据处理的容器代码。"),
                ("并发工作函数", ("std::thread", "emplace_back([", "worker("), "检测到并发工作单元入口，CPU 消耗可能分散在多个线程或子进程。"),
                ("多进程分发", ("fork(", "waitpid(", "pipe("), "检测到多进程 fanout 或进程间协作代码，CPU 时间可能由父子进程共同消耗。"),
            ],
            "lock_contention": [
                ("锁竞争", ("std::mutex", "std::lock_guard", "std::unique_lock", "pthread_mutex"), "检测到互斥锁相关代码，可能与锁竞争有关。"),
                ("共享临界区", ("shared_", "global_", "critical"), "检测到共享状态或临界区命名痕迹。"),
                ("等待与唤醒", ("condition_variable", "notify_one", "notify_all", "futex"), "检测到等待/唤醒相关代码，可能与锁竞争或线程协作有关。"),
            ],
            "scheduler_issue": [
                ("线程调度压力", ("std::thread", "pthread_create", "sleep_for", "yield", "condition_variable"), "检测到线程创建、等待或调度相关代码。"),
                ("多进程调度压力", ("fork(", "waitpid(", "clone(", "exec"), "检测到多进程派生与回收代码，调度开销可能与进程并发有关。"),
            ],
            "io_bound": [
                ("I/O 热点", ("ifstream", "ofstream", "fread", "fwrite", "read(", "write(", "open("), "检测到文件或系统 I/O 调用。"),
            ],
            "memory_bound": [
                ("内存访问热点", ("new ", "malloc(", "memcpy(", "memmove(", "unordered_map"), "检测到可能带来较高内存访问开销的代码。"),
            ],
            "branch_mispredict": [
                ("分支预测风险", ("if (", "switch (", "?:", "likely", "unlikely"), "检测到高频分支判断代码。"),
            ],
        }
        return mapping.get(hypothesis_kind, [])

    def _symbol_hint(self, lines: list[str], line_no: int) -> str | None:
        start = max(0, line_no - 6)
        for candidate in reversed(lines[start:line_no]):
            stripped = candidate.strip()
            if "(" in stripped and ")" in stripped and "{" in stripped:
                return stripped[:120]
        return None

    def _simplify_symbol(self, symbol: str) -> str:
        text = symbol.strip()
        if "::" in text:
            text = text.split("::")[-1]
        if "(" in text and not text.startswith("("):
            text = text.split("(", 1)[0]
        return text.strip(" *&")

    def _snippet_context(
        self,
        path: Path,
        line_no: int,
        radius: int = 2,
        lines: list[str] | None = None,
    ) -> tuple[str, int, int]:
        source_lines = lines
        if source_lines is None:
            try:
                source_lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
            except OSError:
                return ("", line_no, line_no)
        start = max(1, line_no - radius)
        end = min(len(source_lines), line_no + radius)
        snippet_lines = [
            f"{index:>4} | {source_lines[index - 1]}"
            for index in range(start, end + 1)
        ]
        return ("\n".join(snippet_lines), start, end)

    def _addr2line_batch(self, executable: Path, addresses: list[str]) -> dict[str, tuple[str | None, str, int]]:
        if not addresses:
            return {}
        try:
            completed = subprocess.run(
                ["addr2line", "-Cfe", str(executable), *addresses],
                capture_output=True,
                text=True,
                encoding="utf-8",
                errors="replace",
                timeout=15,
                check=False,
            )
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return {}
        lines = [line.strip() for line in completed.stdout.splitlines()]
        resolved: dict[str, tuple[str | None, str, int]] = {}
        for index, address in enumerate(addresses):
            base = index * 2
            if base + 1 >= len(lines):
                break
            symbol_name = lines[base] or None
            file_line = lines[base + 1]
            file_hint, line_no = self._split_file_line(file_line)
            resolved[address] = (symbol_name, file_hint, line_no)
        return resolved

    def _split_file_line(self, raw: str) -> tuple[str, int]:
        if ":" not in raw:
            return raw, 0
        file_hint, line_text = raw.rsplit(":", 1)
        try:
            return file_hint, int(line_text)
        except ValueError:
            return file_hint, 0

    def _resolve_source_path(self, state: AnalysisState, file_hint: str) -> Path | None:
        if not file_hint or file_hint == "??":
            return None
        hint_path = Path(file_hint)
        if hint_path.is_absolute() and hint_path.exists():
            return hint_path
        if state.source_dir:
            candidate = Path(state.source_dir) / hint_path
            if candidate.exists():
                return candidate
        hint_suffix = str(hint_path).replace("\\", "/")
        for source_file in state.source_files:
            normalized = source_file.replace("\\", "/")
            if normalized.endswith(hint_suffix):
                return Path(source_file)
            if Path(source_file).name == hint_path.name:
                return Path(source_file)
        return None

    def _target_executable_path(self, state: AnalysisState) -> Path | None:
        executable = state.executable_path or (state.target_cmd[0] if state.target_cmd else None)
        if not executable:
            return None
        candidate = Path(executable).expanduser()
        return candidate if candidate.exists() else None

    def _dso_matches_target(self, dso: str, executable: Path) -> bool:
        dso_path = dso.strip()
        if not dso_path or dso_path in {"[unknown]", "[kernel.kallsyms]"}:
            return False
        if dso_path == str(executable):
            return True
        return Path(dso_path).name == executable.name

    def _deduplicate(self, findings: list[SourceFinding]) -> list[SourceFinding]:
        ordered = sorted(findings, key=lambda item: (item.mapping_method != "addr2line", -(item.confidence or 0.0), item.file_path, item.line_no))
        unique: list[SourceFinding] = []
        seen: set[tuple[str, int, str, str | None]] = set()
        for item in ordered:
            key = (item.file_path, item.line_no, item.issue_type, item.symbol_hint)
            if key in seen:
                continue
            seen.add(key)
            unique.append(item)
        return unique
