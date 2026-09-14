"""Render an otool human-readable report from a validated evaluation record."""

from __future__ import annotations

import html
import os
from pathlib import Path
import re
from typing import Any
from urllib.parse import quote


REPORT_NAME = "EVALUATION.md"
REPORT_MARKER = "<!-- cve-orchestrator evaluation report -->"


def _text(value: Any, limit: int = 500) -> str:
    plain = " ".join(str(value).split())
    if len(plain) > limit:
        plain = plain[:limit - 1] + "…"
    escaped = html.escape(plain, quote=False)
    return re.sub(r"([\\`*_{}\[\]#|])", r"\\\1", escaped)


def render_evaluation_report(record: dict[str, Any], recipe: Path) -> str:
    result = record.get("llm_result") or {}
    inventory = record.get("preflight") or {}
    lines = [
        REPORT_MARKER,
        f"# Evaluation: {_text(record.get('cve', 'unknown CVE'))}", "",
        f"**Final status: {_text(record.get('status', 'inconclusive')).upper()}**",
        "",
        _text(result.get("summary") or record.get("summary") or "No reviewer summary was available.", 900),
        "",
        "## Checklist", "",
    ]
    requirements = result.get("requirements")
    checks = {str(r.get("id")): r for r in requirements if isinstance(r, dict)} if isinstance(requirements, list) else {}
    ids = inventory.get("required_evaluation_checks") or list(checks)
    for requirement_id in ids:
        check = checks.get(requirement_id, {})
        status = check.get("status", "unverified")
        tick = "x" if status == "pass" else " "
        label = str(requirement_id).replace("_", " ").capitalize()
        line = f"- [{tick}] {_text(label)} — {_text(status).upper()}"
        evidence = check.get("evidence")
        if isinstance(evidence, list) and evidence:
            line += f": {_text(evidence[0], 220)}"
        lines.append(line)
    if not ids:
        lines.append("- [ ] No valid checklist was returned.")

    def section(title: str, values: Any, limit: int = 5) -> None:
        if not isinstance(values, list) or not values:
            return
        lines.extend(["", f"## {title}", ""])
        lines.extend(f"- {_text(item, 350)}" for item in values[:limit])
        if len(values) > limit:
            lines.append(f"- {len(values) - limit} further item(s) in the JSON record.")

    missing = list(inventory.get("missing") or [])
    if isinstance(result.get("missing_artifacts"), list):
        missing.extend(result["missing_artifacts"])
    section("Missing recipe artifacts", list(dict.fromkeys(str(v) for v in missing)))
    section("Concerns", result.get("concerns"))
    section("Validation findings", record.get("validation_errors"))
    if result.get("review"):
        lines.extend(["", "## Review notes", "", _text(result["review"], 1000)])
    section("References checked", result.get("references_checked"))
    section("References unavailable within recipe", result.get("references_unavailable"))
    section("Reviewer read commands", result.get("commands_run"), limit=3)
    lines.extend(["", "## Evaluation details", ""])
    for label, value in (
        ("Rubric", record.get("rubric_version")),
        ("Evidence scope", record.get("scope", "recipe_only")),
        ("LLM verdict", result.get("verdict")),
        ("Configured reviewer model", record.get("model")),
        ("Completed (UTC)", record.get("ended_at") or record.get("updated_at")),
        ("Duration (seconds)", record.get("wall_time_seconds")),
    ):
        if value is not None:
            lines.append(f"- {label}: {_text(value)}")
    for label, key in (("Reviewer JSON", "llm_result"), ("Validated JSON", "result")):
        path = (record.get("artifacts") or {}).get(key)
        if path:
            target = quote(os.path.relpath(path, recipe), safe="/.")
            lines.append(f"- [{label}]({target})")
    lines.extend(["", "Generated from evaluation JSON. This report is excluded from future review evidence.", ""])
    return "\n".join(lines)


def write_recipe_evaluation_report(record: dict[str, Any], recipe: Path) -> Path:
    report_path = recipe / REPORT_NAME
    if recipe.is_symlink() or report_path.is_symlink():
        raise ValueError("Refusing to write an evaluation report through a symlink")
    if report_path.exists() and not report_path.read_text(encoding="utf-8").startswith(REPORT_MARKER):
        raise ValueError(f"Refusing to overwrite an existing non-generated {REPORT_NAME}")
    report_path.write_text(render_evaluation_report(record, recipe), encoding="utf-8")
    return report_path
