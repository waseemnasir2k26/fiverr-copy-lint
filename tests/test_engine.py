import json
import runpy
import subprocess
import sys
from pathlib import Path

import pytest

from fiverr_copy_lint.cli import main
from fiverr_copy_lint.engine import check, load_catalogue
from fiverr_copy_lint.fixes import apply_fixes
from fiverr_copy_lint.report import render_json, render_rules_md, render_sarif

ROOT = Path(__file__).resolve().parent.parent
META, RULES = load_catalogue()


def fired(text, ttype="message"):
    return {f.rule_id for f in check(text, ttype).findings}


# ------------------------------------------------------------- obfuscation / evasion
@pytest.mark.parametrize("text,rule", [
    ("add me on g m a i l", "OP-003"),
    ("g.m.a.i.l is fine", "OP-003"),
    ("my w.h.a.t.s.a.p.p is open", "OP-006"),
    ("W H A T S A P P me", "OP-006"),
    ("wh4tsapp me", "OP-006"),
    ("ｗｈａｔｓａｐｐ", "OP-006"),          # full-width letters
    ("whаtsapp", "OP-006"),                                           # Cyrillic a
    ("what​sapp", "OP-006"),                                          # zero-width space
    ("john (at) gmail (dot) com", "OP-002"),
    ("john at gmail dot com", "OP-002"),
    ("john [at] site [dot] io", "OP-002"),
    ("call zero three zero zero one two three four five", "OP-005"),
    ("reach me on +1 (555) 123-4567", "OP-004"),
    ("03001234567", "OP-004"),
    ("send via payp4l", "PAY-001"),
    ("P a y P a l works", "PAY-001"),
    ("pa.y me later", "PAY-006"),
    ("t3l3gr4m me", "OP-007"),
    ("t.me/someone", "OP-015"),
    ("s k y p e", "OP-008"),
    ("let’s have a call", "OP-012"),                                     # curly apostrophe
])
def test_evasion_is_caught(text, rule):
    assert rule in fired(text), f"{text!r} should trigger {rule}, got {fired(text)}"


@pytest.mark.parametrize("text", [
    "I will respond within a day and share a first draft.",
    "Order number 1234 and package 3 include 2 revisions.",
    "The 2026-10-12 delivery covers 5 pages.",
    "Please review the attached brief in the order chat.",
])
def test_no_false_positive_on_ordinary_copy(text):
    assert check(text, "message").findings == [], [f.rule_id for f in check(text, "message").findings]


def test_offsets_point_at_original_text_after_normalisation():
    text = "hi there, add me on whаts​app ok"
    f = [x for x in check(text, "message").findings if x.rule_id == "OP-006"][0]
    assert text[f.start:f.end].endswith("ts​app")
    assert f.line == 1 and f.column == f.start + 1


def test_phone_digit_bounds():
    assert "OP-004" not in fired("my order number is 12345678")      # 8 digits
    assert "OP-004" in fired("my order number is 123456789")         # 9 digits
    assert "OP-004" not in fired("id 1234567890123456")              # 16 digits


def test_fiverr_links_are_allowed_other_links_are_not():
    assert "OP-015" not in fired("see https://www.fiverr.com/someone/gig")
    assert "OP-015" in fired("see https://example.com/page")
    assert "OP-015" in fired("see example.com/page")


def test_rules_respect_text_type():
    assert "PAY-006" in fired("please pay the invoice", "message")
    assert "PAY-006" not in fired("pay-per-click campaigns", "description")
    assert "SEO-001" not in fired("x" * 200, "message")


# ------------------------------------------------------------------- heuristics
def test_title_length_boundary():
    assert "SEO-001" not in fired("I will " + "a" * 73, "title")        # 80 chars
    assert "SEO-001" in fired("I will " + "a" * 74, "title")            # 81 chars


def test_keyword_stuffing_threshold_in_title():
    assert "SEO-002" not in fired("I will design logo design for startups", "title")
    assert "SEO-002" in fired("I will design logo design and logo design again logo", "title")


def test_caps_ratio():
    assert "SEO-003" in fired("I WILL BUILD YOUR WEBSITE TODAY", "title")
    assert "SEO-003" not in fired("I will build your WordPress site with SEO and AI", "title")


def test_missing_i_will_is_only_for_titles():
    assert "SEO-005" in fired("Logo design", "title")
    assert "SEO-005" not in fired("Logo design", "description")


# ------------------------------------------------------------------- score
def test_score_is_bounded_and_banded():
    r = check("clean friendly message with a normal question about the brief", "message")
    assert r.score == 0 and r.band == "low"
    worst = check(Path(ROOT / "examples/bad-message.txt").read_text(encoding="utf-8"), "message")
    assert worst.score == 100 and worst.band == "high"


def test_score_monotonic_when_adding_risky_phrases():
    phrases = [rule.examples["bad"] for rule in RULES
               if rule.kind == "regex" and rule.examples["type"] == "message"]
    assert len(phrases) >= 10
    text, last = "Hi Sara, thanks for the brief.", 0
    base = check(text, "message").score
    assert base == 0
    for p in phrases:
        text = text + " " + p + "."
        s = check(text, "message").score
        assert s >= last, f"score dropped from {last} to {s} after adding {p!r}"
        last = s
    assert last > 0


def test_each_risky_phrase_never_lowers_a_clean_message_score():
    clean = "Thanks for the brief, I will start with a sketch today."
    base = check(clean, "message").score
    for rule in RULES:
        if rule.kind == "regex" and rule.examples["type"] == "message":
            assert check(clean + " " + rule.examples["bad"], "message").score >= base


# ------------------------------------------------------------------- --fix
FIXABLE = [r for r in RULES if r.fixable]


def test_there_are_fixable_rules():
    assert len(FIXABLE) >= 20


@pytest.mark.parametrize("rule", FIXABLE, ids=[r.id for r in FIXABLE])
def test_fix_round_trip_relints_clean_on_fixable_rules(rule):
    ex = rule.examples
    rep = check(ex["bad"], ex["type"])
    fixed, n = apply_fixes(ex["bad"], rep)
    assert n >= 1 and fixed != ex["bad"]
    again = {f.rule_id for f in check(fixed, ex["type"]).findings}
    fixable_ids = {r.id for r in FIXABLE}
    assert not (again & fixable_ids), f"{rule.id}: fixed text still triggers {again & fixable_ids}: {fixed!r}"


def test_fix_round_trip_on_example_file():
    text = (ROOT / "examples/bad-message.txt").read_text(encoding="utf-8")
    fixed, n = apply_fixes(text, check(text, "message"))
    assert n >= 5
    left = {f.rule_id for f in check(fixed, "message").findings} & {r.id for r in FIXABLE}
    assert not left, (left, fixed)
    assert "Fiverr" in fixed and "@" not in fixed and "PayPal" not in fixed


def test_fix_uses_the_documented_safe_sentence():
    fixed, _ = apply_fixes("Email me at a@b.com", check("Email me at a@b.com", "message"))
    assert fixed == "Let's keep everything in Fiverr's inbox so you're protected"


def test_fix_keeps_capitalisation_and_leaves_unfixable_alone():
    t = "Contact me. Fake reviews sold here."
    fixed, _ = apply_fixes(t, check(t, "message"))
    assert fixed.startswith("Message me here.")
    assert "Fake reviews" in fixed  # REV-004 has no auto-fix


# ------------------------------------------------------------------- SARIF / json / md
def test_sarif_shape():
    rep = check("Email me at a@b.com, pay me via PayPal", "message")
    doc = json.loads(render_sarif([("msg.txt", rep)]))
    assert doc["version"] == "2.1.0" and doc["$schema"].endswith("sarif-2.1.0.json")
    run = doc["runs"][0]
    assert run["tool"]["driver"]["name"] == "fiverr-copy-lint"
    assert len(run["tool"]["driver"]["rules"]) == len(RULES)
    assert run["results"]
    ids = [r["id"] for r in run["tool"]["driver"]["rules"]]
    for res in run["results"]:
        assert res["level"] in ("error", "warning", "note")
        assert ids[res["ruleIndex"]] == res["ruleId"]
        loc = res["locations"][0]["physicalLocation"]
        assert loc["artifactLocation"]["uri"] == "msg.txt"
        assert loc["region"]["startLine"] >= 1 and loc["region"]["charLength"] > 0
        assert res["message"]["text"]


def test_json_report_fields():
    d = json.loads(render_json(check("add me on skype", "message"), "x.txt"))
    assert {"source", "type", "score", "band", "counts", "findings", "disclaimer"} <= set(d)
    f = d["findings"][0]
    assert {"rule", "severity", "start", "end", "line", "column", "text", "why", "suggestion"} <= set(f)
    assert "Not affiliated" in d["disclaimer"]


# ------------------------------------------------------------------- CLI
def run_cli(args, stdin=None):
    return subprocess.run([sys.executable, "-m", "fiverr_copy_lint", *args], input=stdin, capture_output=True,
                          text=True, encoding="utf-8", cwd=ROOT)


def test_cli_exit_codes_and_stdin():
    bad = run_cli(["check", "-"], "email me at a@b.com")
    assert bad.returncode == 1 and "OP-001" in bad.stdout
    good = run_cli(["check", "-"], "Thanks, I will send the first draft today.")
    assert good.returncode == 0
    assert run_cli(["check", "-", "--fail-on", "never"], "email me at a@b.com").returncode == 0


def test_cli_fix_outputs_text_on_stdout():
    r = run_cli(["check", "-", "--fix"], "Email me at a@b.com")
    assert r.stdout.strip() == "Let's keep everything in Fiverr's inbox so you're protected"


def test_cli_formats_on_examples():
    for fmt in ("json", "sarif", "md", "text"):
        r = run_cli(["check", "examples/bad-gig-title.txt", "--type", "title", "--format", fmt])
        assert r.returncode == 1 and r.stdout.strip()
    assert run_cli(["check", "examples/good-gig-description.txt", "examples/good-gig-title.txt"]).returncode == 0


def test_cli_missing_file_is_exit_2():
    assert run_cli(["check", "does-not-exist.txt"]).returncode == 2


def test_cli_rules_and_explain():
    r = run_cli(["rules"])
    assert "OP-006" in r.stdout and "COMMUNITY-OBSERVED" in r.stdout
    assert json.loads(run_cli(["rules", "--format", "json"]).stdout)["rules"]
    e = run_cli(["explain", "PAY-004"])
    assert e.returncode == 0 and "Pay outside" in e.stdout
    assert run_cli(["explain", "NOPE-1"]).returncode == 2


def test_main_in_process_version(capsys):
    with pytest.raises(SystemExit):
        main(["--version"])
    assert "1.0.0" in capsys.readouterr().out


# ------------------------------------------------------------------- generated artefacts stay in sync
def test_rules_json_matches_generator():
    mod = runpy.run_path(str(ROOT / "tools/gen_rules.py"))
    assert (ROOT / "fiverr_copy_lint/rules.json").read_text(encoding="utf-8") == mod["text"]


def test_docs_rules_md_is_current():
    assert (ROOT / "docs/rules.md").read_text(encoding="utf-8") == render_rules_md() + "\n"


def test_examples_behave_as_named():
    assert check((ROOT / "examples/good-gig-description.txt").read_text(encoding="utf-8"), "description").score == 0
    assert check((ROOT / "examples/good-gig-title.txt").read_text(encoding="utf-8"), "title").score == 0
    assert check((ROOT / "examples/bad-gig-title.txt").read_text(encoding="utf-8"), "title").score >= 50
