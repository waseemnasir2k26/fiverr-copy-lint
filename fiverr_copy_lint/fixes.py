"""--fix: rewrite risky spans with safe alternatives."""
from __future__ import annotations

import re

from .engine import SEV_RANK, check, get_rule, load_catalogue


def _replacement(rule, matched: str) -> str:
    return rule.rewrite_map.get(matched.strip().lower(), rule.rewrite)


def apply_fixes(text: str, report) -> tuple[str, int]:
    """Return (fixed_text, number_of_spans_replaced). Heuristic findings and unfixable rules are left alone."""
    meta, _ = load_catalogue()
    safe = meta["safe_sentence"]
    edits = []
    for f in report.findings:
        rule = get_rule(f.rule_id)
        if rule is not None and rule.fixable:
            edits.append((f.start, f.end, _replacement(rule, f.text), SEV_RANK[rule.severity]))
    edits.sort()
    # Merge neighbouring replacements ("pay me directly via PayPal") into the first one.
    gap_ok = re.compile(r"^\s*(?:(?:via|through|on|at|using|with|by|and|or|&|,)\s*)?$", re.I)
    merged = []
    for e in edits:
        if merged and gap_ok.match(text[merged[-1][1]:e[0]]):
            last = merged[-1]
            rep = e[2] if e[3] > last[3] else last[2]
            merged[-1] = (last[0], e[1], rep, max(last[3], e[3]))
        else:
            merged.append(e)
    out = text
    for start, end, rep, _sev in reversed(merged):
        before = out[:start]
        if rep.startswith(("Let's", "Fiverr's")):
            before = re.sub(r"\b(?:on|at|via|through|using|by)\s+$", "", before, flags=re.I)
        if re.search(r"\b[Aa]n $", before) and rep[:1].lower() not in "aeiou":
            before = re.sub(r"\b([Aa])n $", r"\1 ", before)
        if re.search(r"(?:^|[.!?\n])\s*$", before) and rep[:1].islower():
            rep = rep[0].upper() + rep[1:]
        out = before + rep + out[end:]
    # two adjacent contact findings should not leave the same sentence twice
    pat = re.compile(r"(%s)(?:[\s.,;:!\-]*%s)+" % (re.escape(safe), re.escape(safe)))
    out = pat.sub(r"\1", out)
    out = re.sub(r"[ \t]{2,}", " ", out)
    return out, len(edits)


def fix_text(text: str, text_type: str):
    report = check(text, text_type)
    fixed, n = apply_fixes(text, report)
    return fixed, n, report
