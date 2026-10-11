"""Command line interface."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .engine import SEV_RANK, TYPES, check, get_rule, guess_type, load_catalogue
from .fixes import apply_fixes
from .report import (render_explain, render_json, render_md, render_rules_json, render_rules_md,
                     render_rules_text, render_sarif, render_text)

DISCLAIMER = "Community-observed rules, not an official Fiverr list. Not affiliated with Fiverr."


def _read(path: str) -> tuple[str, str]:
    if path == "-":
        return "<stdin>", sys.stdin.read()
    return path, Path(path).read_text(encoding="utf-8")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="fiverr-copy-lint",
                                description="Lint Fiverr gig titles, descriptions, FAQs and messages. " + DISCLAIMER)
    p.add_argument("--version", action="version", version=f"fiverr-copy-lint {__version__}")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("check", help="lint one or more files (use - for stdin)")
    c.add_argument("files", nargs="+", metavar="file")
    c.add_argument("--type", choices=TYPES, help="text type; default guessed from the file name, else 'description' (stdin: 'message')")
    c.add_argument("--format", choices=("text", "json", "sarif", "md"), default="text")
    c.add_argument("--fix", action="store_true", help="emit rewritten text with risky spans replaced")
    c.add_argument("-i", "--in-place", action="store_true", help="with --fix, overwrite the input file")
    c.add_argument("--fail-on", choices=("error", "warn", "info", "never"), default="error",
                   help="exit 1 when a finding of this severity or worse exists (default: error)")

    r = sub.add_parser("rules", help="list the rule catalogue")
    r.add_argument("--format", choices=("text", "json", "md"), default="text")
    r.add_argument("--group")

    e = sub.add_parser("explain", help="explain one rule")
    e.add_argument("rule_id")
    return p


def cmd_check(a) -> int:
    results, fixed_by_src, worst = [], {}, 0
    for path in a.files:
        source, text = _read(path)
        ttype = a.type or ("message" if path == "-" else guess_type(path))
        rep = check(text, ttype)
        fixed = None
        if a.fix:
            fixed, _ = apply_fixes(text, rep)
            fixed_by_src[source] = fixed
            if a.in_place and path != "-":
                Path(path).write_text(fixed, encoding="utf-8", newline="")
        results.append((source, text, rep, fixed))
        if a.fail_on != "never":
            floor = SEV_RANK[a.fail_on]
            if any(SEV_RANK[f.severity] >= floor for f in rep.findings):
                worst = 1

    fmt = a.format
    if fmt == "sarif":
        print(render_sarif([(s, r) for s, _, r, _ in results]))
    elif fmt == "json":
        import json
        from .report import to_dict
        docs = [to_dict(r, s, f) for s, _, r, f in results]
        print(json.dumps(docs[0] if len(docs) == 1 else docs, indent=2, ensure_ascii=False))
    elif a.fix and fmt == "text" and len(results) == 1 and not a.in_place:
        # pipe-friendly: fixed text on stdout, report on stderr
        s, t, r, f = results[0]
        print(render_text(r, s, t), file=sys.stderr)
        sys.stdout.write(f if f.endswith("\n") else f + "\n")
    else:
        for s, t, r, f in results:
            print(render_text(r, s, t, f) if fmt == "text" else render_md(r, s, f))
            print()
    return worst


def main(argv=None) -> int:
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")
    a = build_parser().parse_args(argv)
    if a.cmd == "check":
        try:
            return cmd_check(a)
        except (OSError, UnicodeDecodeError) as exc:
            print(f"fiverr-copy-lint: {exc}", file=sys.stderr)
            return 2
    if a.cmd == "rules":
        print({"text": lambda: render_rules_text(a.group), "json": render_rules_json, "md": render_rules_md}[a.format]())
        return 0
    if a.cmd == "explain":
        rule = get_rule(a.rule_id)
        if rule is None:
            print(f"unknown rule {a.rule_id!r}. Run: fiverr-copy-lint rules", file=sys.stderr)
            return 2
        print(render_explain(rule))
        return 0
    return 2


if __name__ == "__main__":
    sys.exit(main())
