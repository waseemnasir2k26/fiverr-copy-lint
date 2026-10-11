"""Renderers: text, json, sarif, markdown, plus the rule catalogue views."""
from __future__ import annotations

import json

from .engine import load_catalogue

TOOL_URI = "https://github.com/waseemnasir2k26/fiverr-copy-lint"
LEVEL = {"error": "error", "warn": "warning", "info": "note"}


def _f(f) -> dict:
    return {
        "rule": f.rule_id, "name": f.name, "group": f.group, "severity": f.severity,
        "start": f.start, "end": f.end, "line": f.line, "column": f.column, "text": f.text,
        "why": f.rationale, "suggestion": f.suggestion, "fixable": f.fixable, "detail": f.detail,
    }


def to_dict(report, source: str, fixed: str | None = None) -> dict:
    d = {
        "source": source, "type": report.text_type, "score": report.score, "band": report.band,
        "counts": report.counts, "length": report.length, "rules_version": report.rules_version,
        "findings": [_f(f) for f in report.findings],
        "disclaimer": "Community-observed rules. Not affiliated with or endorsed by Fiverr.",
    }
    if fixed is not None:
        d["fixed"] = fixed
    return d


def render_json(report, source, fixed=None) -> str:
    return json.dumps(to_dict(report, source, fixed), indent=2, ensure_ascii=False)


def render_text(report, source, text="", fixed=None) -> str:
    lines = [f"{source} ({report.text_type}) - risk {report.score}/100 [{report.band.upper()}] "
             f"- {report.counts['error']} error, {report.counts['warn']} warn, {report.counts['info']} info"]
    if not report.findings:
        lines.append("  no findings")
    for f in report.findings:
        snippet = f.text.replace("\n", " ")
        if len(snippet) > 60:
            snippet = snippet[:57] + "..."
        lines.append(f"  {f.line}:{f.column:<3} {f.severity:<5} {f.rule_id:<8} {f.name}  [{f.start}-{f.end}]")
        lines.append(f"        found: \"{snippet}\"" + (f"  ({f.detail})" if f.detail else ""))
        lines.append(f"        why:   {f.rationale}")
        lines.append(f"        try:   {f.suggestion}")
    if fixed is not None:
        lines += ["", "fixed text:", fixed]
    return "\n".join(lines)


def render_md(report, source, fixed=None) -> str:
    out = [f"### `{source}` ({report.text_type}) - risk **{report.score}/100** ({report.band})", ""]
    if not report.findings:
        out.append("No findings.")
    else:
        out += ["| Line:Col | Severity | Rule | Found | Suggestion |", "|---|---|---|---|---|"]
        for f in report.findings:
            found = f.text.replace("|", "\\|").replace("\n", " ")[:60]
            out.append(f"| {f.line}:{f.column} | {f.severity} | `{f.rule_id}` {f.name} | `{found}` | {f.suggestion} |")
    if fixed is not None:
        out += ["", "**Fixed text**", "", "```", fixed, "```"]
    out += ["", "_Community-observed rules; not affiliated with Fiverr._"]
    return "\n".join(out)


def render_sarif(results: list) -> str:
    """results: list of (source, report). One SARIF 2.1.0 run covering every file."""
    meta, rules = load_catalogue()
    driver_rules = [{
        "id": r.id, "name": r.name,
        "shortDescription": {"text": r.name},
        "fullDescription": {"text": r.rationale},
        "help": {"text": r.suggestion},
        "defaultConfiguration": {"level": LEVEL[r.severity]},
        "properties": {"group": r.group, "tags": [r.group]},
    } for r in rules]
    index = {r.id: i for i, r in enumerate(rules)}
    sarif_results = []
    for source, rep in results:
        for f in rep.findings:
            sarif_results.append({
                "ruleId": f.rule_id, "ruleIndex": index[f.rule_id], "level": LEVEL[f.severity],
                "message": {"text": f"{f.name}: {f.rationale} Fix: {f.suggestion}" + (f" ({f.detail})" if f.detail else "")},
                "locations": [{"physicalLocation": {
                    "artifactLocation": {"uri": source.replace("\\", "/")},
                    "region": {"startLine": f.line, "startColumn": f.column,
                               "charOffset": f.start, "charLength": f.end - f.start},
                }}],
            })
    doc = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {"driver": {"name": "fiverr-copy-lint", "version": meta["version"],
                                "informationUri": TOOL_URI, "rules": driver_rules}},
            "results": sarif_results,
        }],
    }
    return json.dumps(doc, indent=2, ensure_ascii=False)


# ------------------------------------------------------------------ catalogue views
def render_rules_text(group: str | None = None) -> str:
    meta, rules = load_catalogue()
    lines = [f"fiverr-copy-lint rules v{meta['rules_version']} ({len(rules)} rules)", f"NOTE: {meta['note']}", ""]
    for r in rules:
        if group and r.group != group:
            continue
        lines.append(f"{r.id:<8} {r.severity:<5} {r.group:<20} {r.name}")
    return "\n".join(lines)


def render_rules_json() -> str:
    meta, rules = load_catalogue()
    return json.dumps({"meta": {k: meta[k] for k in ("version", "rules_version", "note")},
                       "rules": [{"id": r.id, "name": r.name, "group": r.group, "severity": r.severity,
                                  "applies": r.applies, "fixable": r.fixable} for r in rules]}, indent=2)


GROUP_TITLES = {
    "off-platform": "Off-platform contact", "payment": "Payment outside Fiverr",
    "review-manipulation": "Review manipulation", "gig-seo": "Gig SEO hygiene",
    "buyer-request": "Buyer-request spam",
}


def render_rules_md() -> str:
    meta, rules = load_catalogue()
    out = [
        "# Rule catalogue", "",
        "<!-- AUTO-GENERATED by `fiverr-copy-lint rules --format md`. Do not edit by hand. -->", "",
        f"Rules version **{meta['rules_version']}**, {len(rules)} rules.", "",
        f"> **NOTE:** {meta['note']}", "",
        "Severity weights: " + ", ".join(f"{k} = {v}" for k, v in meta["severity_weights"].items())
        + ". Risk score = sum of weights, capped at 100.", "",
    ]
    for g, title in GROUP_TITLES.items():
        grp = [r for r in rules if r.group == g]
        out += [f"## {title}", "", "| ID | Severity | Applies to | Auto-fix | What it catches |", "|---|---|---|---|---|"]
        for r in grp:
            out.append(f"| `{r.id}` | {r.severity} | {', '.join(r.applies)} | {'yes' if r.fixable else 'no'} | {r.name} |")
        out.append("")
        for r in grp:
            ex = r.examples
            out += [f"### {r.id} - {r.name}", "", f"- **Why:** {r.rationale}", f"- **Instead:** {r.suggestion}",
                    f"- **Flagged:** `{ex['bad'][:120]}`" if len(ex['bad']) < 140 else f"- **Flagged:** (long example, see rules.json)",
                    f"- **Fine:** `{ex['good'][:120]}`" if len(ex['good']) < 140 else "- **Fine:** (long example, see rules.json)", ""]
    return "\n".join(out)


def render_explain(rule) -> str:
    ex = rule.examples
    lines = [f"{rule.id} - {rule.name}", f"group:     {rule.group}", f"severity:  {rule.severity}",
             f"applies:   {', '.join(rule.applies)}", f"auto-fix:  {'yes -> ' + repr(rule.rewrite) if rule.fixable else 'no (heuristic or needs human wording)'}",
             "", f"why:       {rule.rationale}", f"instead:   {rule.suggestion}", ""]
    if len(ex["bad"]) < 200:
        lines += [f"flagged ({ex['type']}): {ex['bad']}", f"fine    ({ex['type']}): {ex['good'][:200]}"]
    return "\n".join(lines)
