"""otool README metadata and section-only updates; no target execution."""

from __future__ import annotations

import math
import re
from typing import Any


UNAVAILABLE = "not available (not exposed by harness)"


def metadata_fields(attempts: list[dict[str, Any]]) -> dict[str, str]:
    """Use completed attempt records, excluding later reviewer/formatter usage."""
    fields = {
        "Reproduced by": "LLM agent (see recorded reproduction status)",
        "Agent/harness": "OpenCode (version not recorded)",
        "Attempts": str(len(attempts)),
    }
    models = sorted({str(m) for a in attempts for m in (a.get("opencode") or {}).get("models", [])})
    configured = sorted({str(a["model"]) for a in attempts if a.get("model")})
    fields["Model"] = ", ".join(models) if models else UNAVAILABLE
    fields["Configured model (request)"] = ", ".join(configured) if configured else UNAVAILABLE
    agents = sorted({str(a["agent"]) for a in attempts if a.get("agent")})
    fields["Configured agent"] = ", ".join(agents) if agents else "OpenCode default agent"
    starts = [str(a["started_at"]) for a in attempts if a.get("started_at")]
    ends = [str(a["ended_at"]) for a in attempts if a.get("ended_at")]
    fields["Start time"] = min(starts) if len(starts) == len(attempts) and starts else UNAVAILABLE
    fields["End time"] = max(ends) if len(ends) == len(attempts) and ends else UNAVAILABLE

    def numeric(value: Any) -> bool:
        return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)

    times = [a.get("wall_time_seconds") for a in attempts]
    fields["Elapsed time (sum of attempts)"] = (
        f"{sum(times):.3f} seconds" if times and all(numeric(v) for v in times) else UNAVAILABLE
    )

    def reported(record: dict[str, Any], key: str) -> bool:
        # Legacy parsers initialized absent fields to zero. Such zeroes cannot
        # be distinguished from reported zeroes without a presence marker.
        value = record.get(key)
        if not numeric(value):
            return False
        if "reported_fields" in record:
            return key in record["reported_fields"]
        return value != 0

    def total(key: str) -> str:
        records = [a.get("opencode") or {} for a in attempts]
        if not records or not all(reported(r, key) for r in records):
            return UNAVAILABLE
        value = sum(r[key] for r in records)
        return str(value)

    for title, key in (
        ("Input tokens", "input_tokens"),
        ("Output tokens", "output_tokens"),
        ("Reasoning tokens", "reasoning_tokens"),
        ("Cache read tokens", "cache_read_tokens"),
        ("Cache write tokens", "cache_write_tokens"),
        ("Total tokens (reported)", "reported_total_tokens"),
        ("Cost (OpenCode reported; currency not recorded)", "cost"),
    ):
        fields[title] = total(key)
    fields["Telemetry source"] = "Completed OpenCode attempt records; unreported values remain unavailable"
    fields["Scope"] = "Reproduction attempts only; metadata and evaluator usage excluded"
    return fields


def render_metadata_section(fields: dict[str, str]) -> str:
    def escape(value: str) -> str:
        return value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace("|", "&#124;").replace("\n", " ").replace("\r", " ")

    return "\n".join([
        "## Reproduction metadata", "",
        "Populated after reproduction from completed OpenCode records.", "",
        "| Field | Value |", "| --- | --- |",
        *(f"| {escape(key)} | {escape(value)} |" for key, value in fields.items()),
        "",
    ])


def replace_metadata_section(readme: str, replacement: str) -> str:
    """Replace only the metadata section, preserving adjacent text and shell facts."""
    headings: list[tuple[int, int, str]] = []
    fence: str | None = None
    offset = 0
    for line in readme.splitlines(keepends=True):
        stripped = line.lstrip()
        fence_match = re.match(r"(`{3,}|~{3,})", stripped)
        if fence_match:
            marker = fence_match.group(1)
            if fence is None:
                fence = marker
            elif marker[0] == fence[0] and len(marker) >= len(fence):
                fence = None
        elif fence is None:
            match = re.match(r"^(#{1,6})[ \t]+(.+?)\s*#*\s*$", line)
            if match:
                headings.append((offset, len(match.group(1)), match.group(2).strip()))
        offset += len(line)
    sections = [(i, h) for i, h in enumerate(headings) if h[2].casefold() == "reproduction metadata"]
    if len(sections) > 1:
        raise ValueError("Multiple Reproduction metadata sections; refusing ambiguous update")
    newline = "\r\n" if "\r\n" in readme else "\n"
    if not sections:
        if fence is not None:
            raise ValueError("Unclosed Markdown fence; refusing to append metadata")
        return readme + ("" if readme.endswith(newline * 2) else newline * 2) + replacement.replace("\n", newline)
    index, (start, level, _) = sections[0]
    end = next((pos for pos, depth, _ in headings[index + 1:] if depth <= level), len(readme))
    body = readme[start:end]
    shell_lines = [line for line in body.splitlines() if re.match(
        r"^\s*(?:[-*]\s+\*\*|\|\s*)(?:User shell|Command-runner shell)(?:\*\*|:|\s*\|)",
        line, re.IGNORECASE,
    )]
    replacement = re.sub(r"^## ", "#" * level + " ", replacement, count=1)
    if shell_lines:
        replacement = replacement.rstrip() + "\n\nShell facts recorded during reproduction:\n\n" + "\n".join(shell_lines) + "\n"
    return readme[:start] + (replacement.rstrip() + "\n\n").replace("\n", newline) + readme[end:]
