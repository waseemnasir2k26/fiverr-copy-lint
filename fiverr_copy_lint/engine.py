"""Lint engine: loads rules.json, normalises text, runs regex + heuristic rules, scores."""
from __future__ import annotations

import json
import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

RULES_PATH = Path(__file__).with_name("rules.json")
TYPES = ("title", "description", "faq", "message", "request")
SEV_RANK = {"error": 3, "warn": 2, "info": 1}

ZERO_WIDTH = {"​", "‌", "‍", "⁠", "﻿", "­", "‎", "‏"}
# Cyrillic/Greek look-alikes and typographic quotes folded to ASCII before matching.
HOMOGLYPHS = {
    "а": "a", "е": "e", "о": "o", "р": "p", "с": "c", "х": "x",
    "і": "i", "ѕ": "s", "ј": "j", "һ": "h", "ԁ": "d", "ԛ": "q",
    "ο": "o", "α": "a", "ε": "e", "ρ": "p",
    "’": "'", "‘": "'", "“": '"', "”": '"', "–": "-", "—": "-",
}


@dataclass
class Rule:
    id: str
    name: str
    group: str
    severity: str
    applies: list
    kind: str
    rationale: str
    suggestion: str
    examples: dict
    pattern: str | None = None
    flags: str = "i"
    post: str | None = None
    heuristic: str | None = None
    params: dict = field(default_factory=dict)
    rewrite: str | None = None
    rewrite_map: dict = field(default_factory=dict)
    regex: "re.Pattern | None" = None

    @property
    def fixable(self) -> bool:
        return self.rewrite is not None


@dataclass
class Finding:
    rule_id: str
    name: str
    group: str
    severity: str
    start: int
    end: int
    text: str
    rationale: str
    suggestion: str
    fixable: bool
    line: int = 1
    column: int = 1
    detail: str = ""


@dataclass
class Report:
    text_type: str
    score: int
    band: str
    findings: list
    counts: dict
    length: int
    rules_version: str


@lru_cache(maxsize=1)
def load_catalogue(path: str | None = None):
    p = Path(path) if path else RULES_PATH
    data = json.loads(p.read_text(encoding="utf-8"))
    rules = []
    for r in data["rules"]:
        rule = Rule(
            id=r["id"], name=r["name"], group=r["group"], severity=r["severity"], applies=r["applies"],
            kind=r["kind"], rationale=r["rationale"], suggestion=r["suggestion"], examples=r["examples"],
            pattern=r.get("pattern"), flags=r.get("flags", "i"), post=r.get("post"),
            heuristic=r.get("heuristic"), params=r.get("params", {}), rewrite=r.get("rewrite"),
            rewrite_map=r.get("rewrite_map", {}),
        )
        if rule.kind == "regex":
            f = re.UNICODE | (re.IGNORECASE if "i" in rule.flags else 0)
            rule.regex = re.compile(rule.pattern, f)
        rules.append(rule)
    return data["meta"], rules


def get_rule(rule_id: str):
    _, rules = load_catalogue()
    for r in rules:
        if r.id.lower() == rule_id.lower():
            return r
    return None


def normalise(text: str):
    """NFKC-fold, strip zero-width chars, fold look-alikes; returns (normalised, index map to original)."""
    out, idx = [], []
    for i, ch in enumerate(text):
        if ch in ZERO_WIDTH:
            continue
        ch = HOMOGLYPHS.get(ch, ch)
        for c in unicodedata.normalize("NFKC", ch):
            out.append(c)
            idx.append(i)
    return "".join(out), idx


def _post_ok(rule: Rule, matched: str) -> bool:
    if not rule.post:
        return True
    kind, _, arg = rule.post.partition(":")
    if kind == "digits":
        lo, hi = (int(x) for x in arg.split("-"))
        return lo <= sum(c.isdigit() for c in matched) <= hi
    return True


def _is_emoji(ch: str, ranges) -> bool:
    o = ord(ch)
    return any(lo <= o <= hi for lo, hi in ranges)


def _words(text: str):
    return list(re.finditer(r"[^\W_]+(?:['\-][^\W_]+)*", text, re.UNICODE))


# ---------------------------------------------------------------- heuristics
# Each returns a list of (start, end, detail) on the ORIGINAL text.
def h_title_length(text, rule, meta, ttype):
    mx = rule.params["max"]
    body = text.rstrip()
    if len(body) > mx:
        return [(mx, len(body), f"{len(body)} characters, limit is {mx}")]
    return []


def h_keyword_stuffing(text, rule, meta, ttype):
    stop = set(meta["stopwords"])
    ws = _words(text)
    seen: dict = {}
    for m in ws:
        w = m.group(0).lower()
        if len(w) >= 4 and w not in stop and not w.isdigit():
            seen.setdefault(w, []).append(m)
    out = []
    p = rule.params
    for w, ms in seen.items():
        n = len(ms)
        if ttype == "title":
            if n >= p["title_min"]:
                out.append((ms[p["title_min"] - 1].start(), ms[-1].end(), f"'{w}' appears {n} times"))
        elif n >= p["body_min"] and n / max(len(ws), 1) >= p["body_density"]:
            out.append((ms[p["body_min"] - 1].start(), ms[-1].end(), f"'{w}' appears {n} times in {len(ws)} words"))
    return out


def h_caps_ratio(text, rule, meta, ttype):
    p = rule.params
    letters = [c for c in text if c.isalpha()]
    if len(letters) < p["min_letters"]:
        return []
    ratio = sum(c.isupper() for c in letters) / len(letters)
    limit = p["title"] if ttype == "title" else p["other"]
    if ratio > limit:
        return [(0, len(text.rstrip()), f"{ratio:.0%} of letters are capitals (limit {limit:.0%})")]
    return []


def h_emoji_spam(text, rule, meta, ttype):
    ranges = meta["emoji_ranges"]
    pos = [i for i, c in enumerate(text) if _is_emoji(c, ranges)]
    limit = rule.params["title"] if ttype == "title" else rule.params["other"]
    if len(pos) >= limit:
        return [(pos[0], pos[-1] + 1, f"{len(pos)} emoji (limit {limit - 1})")]
    return []


def h_missing_i_will(text, rule, meta, ttype):
    t = text.lstrip()
    if t and not re.match(r"i\s+will\b", t, re.I):
        start = len(text) - len(t)
        return [(start, min(len(text.rstrip()), start + 24), "title does not start with 'I will'")]
    return []


def h_short_description(text, rule, meta, ttype):
    n = len(_words(text))
    if n < rule.params["min_words"]:
        return [(0, len(text.rstrip()), f"{n} words, aim for {rule.params['min_words']}+")]
    return []


def h_keyword_dump(text, rule, meta, ttype):
    n = rule.params["min_items"]
    pat = re.compile(r"(?:[^,.\n]{1,28},\s*){%d,}[^,.\n]{1,28}" % (n - 1))
    return [(m.start(), m.end(), f"{n}+ comma-separated keywords") for m in pat.finditer(text)]


def h_short_request(text, rule, meta, ttype):
    n = len(_words(text))
    if n < rule.params["min_words"]:
        return [(0, len(text.rstrip()), f"{n} words, aim for {rule.params['min_words']}+")]
    return []


HEURISTICS = {
    "title_length": h_title_length, "keyword_stuffing": h_keyword_stuffing, "caps_ratio": h_caps_ratio,
    "emoji_spam": h_emoji_spam, "missing_i_will": h_missing_i_will, "short_description": h_short_description,
    "keyword_dump": h_keyword_dump, "short_request": h_short_request,
}


def _line_col(text: str, offset: int):
    line = text.count("\n", 0, offset) + 1
    col = offset - (text.rfind("\n", 0, offset) + 1) + 1
    return line, col


def _resolve_overlaps(findings):
    """Keep the strongest of any overlapping regex findings (severity, then span length)."""
    ordered = sorted(findings, key=lambda f: (-SEV_RANK[f.severity], -(f.end - f.start), f.start))
    kept = []
    for f in ordered:
        if all(f.end <= k.start or f.start >= k.end for k in kept):
            kept.append(f)
    return kept


def band_for(score: int, meta) -> str:
    label = meta["bands"][0][1]
    for floor, name in meta["bands"]:
        if score >= floor:
            label = name
    return label


def check(text: str, text_type: str = "message", rules=None) -> Report:
    if text_type not in TYPES:
        raise ValueError(f"unknown type {text_type!r}; choose from {', '.join(TYPES)}")
    meta, all_rules = load_catalogue()
    active = [r for r in (rules or all_rules) if text_type in r.applies]
    norm, idx = normalise(text)

    regex_hits, other = [], []
    for r in active:
        if r.kind == "regex":
            for m in r.regex.finditer(norm):
                if m.end() == m.start() or not _post_ok(r, m.group(0)):
                    continue
                s, e = idx[m.start()], idx[m.end() - 1] + 1
                regex_hits.append(Finding(r.id, r.name, r.group, r.severity, s, e, text[s:e],
                                          r.rationale, r.suggestion, r.fixable))
        else:
            for s, e, detail in HEURISTICS[r.heuristic](text, r, meta, text_type):
                other.append(Finding(r.id, r.name, r.group, r.severity, s, e, text[s:e],
                                     r.rationale, r.suggestion, False, detail=detail))
    findings = _resolve_overlaps(regex_hits) + other
    findings.sort(key=lambda f: (f.start, -SEV_RANK[f.severity], f.rule_id))
    for f in findings:
        f.line, f.column = _line_col(text, f.start)
    weights = meta["severity_weights"]
    score = min(100, sum(weights[f.severity] for f in findings))
    counts = {s: sum(1 for f in findings if f.severity == s) for s in ("error", "warn", "info")}
    return Report(text_type, score, band_for(score, meta), findings, counts, len(text), meta["rules_version"])


def guess_type(path: str, default: str = "description") -> str:
    name = Path(path).stem.lower()
    for t in TYPES:
        if t in name:
            return t
    if "dm" in name or "reply" in name or "inbox" in name:
        return "message"
    return default
