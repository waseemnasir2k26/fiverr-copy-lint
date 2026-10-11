"""The browser playground must behave exactly like the Python engine (same rules.json)."""
import json
import re
import runpy
import shutil
import subprocess
from pathlib import Path

import pytest

from fiverr_copy_lint.engine import check, load_catalogue
from fiverr_copy_lint.fixes import apply_fixes

ROOT = Path(__file__).resolve().parent.parent
NODE = shutil.which("node")


def build_cases():
    cases = []
    _, rules = load_catalogue()
    for r in rules:
        cases.append((r.examples["bad"], r.examples["type"]))
        cases.append((r.examples["good"], r.examples["type"]))
    for name, t in (("bad-message", "message"), ("bad-gig-title", "title"), ("good-gig-description", "description")):
        cases.append(((ROOT / "examples" / f"{name}.txt").read_text(encoding="utf-8"), t))
    return cases


def js_results(cases, tmp_path):
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    script = re.search(r'<script id="engine">(.*?)</script>', html, re.S).group(1)
    harness = script + (
        "\nconst cases = JSON.parse(require('fs').readFileSync(0,'utf8'));\n"
        "console.log(JSON.stringify(cases.map(([t,ty])=>{const r=lint(t,ty);"
        "return {score:r.score,ids:r.findings.map(f=>f.rule+':'+f.start+'-'+f.end),fixed:applyFixes(t,r)};})));\n"
    )
    f = tmp_path / "harness.js"
    f.write_text(harness, encoding="utf-8")
    p = subprocess.run([NODE, str(f)], input=json.dumps(cases), capture_output=True, text=True, encoding="utf-8")
    assert p.returncode == 0, p.stderr
    return json.loads(p.stdout)


@pytest.mark.skipif(NODE is None, reason="node not installed")
def test_js_engine_matches_python_engine_on_every_fixture(tmp_path):
    cases = build_cases()
    got = js_results(cases, tmp_path)
    assert len(got) == len(cases) and len(cases) > 90
    for (text, ty), js in zip(cases, got):
        rep = check(text, ty)
        py_ids = sorted(f"{f.rule_id}:{f.start}-{f.end}" for f in rep.findings)
        js_ids = sorted(js["ids"])
        if any(ord(c) > 0xFFFF for c in text):
            # JS offsets count UTF-16 units, Python counts code points: compare rule ids only
            py_ids = sorted(i.split(":")[0] for i in py_ids)
            js_ids = sorted(i.split(":")[0] for i in js_ids)
        assert js_ids == py_ids, (text[:60], ty)
        assert js["score"] == rep.score, (text[:60], ty)
        assert js["fixed"] == apply_fixes(text, rep)[0], (text[:60], ty)


def test_playground_is_in_sync_with_rules_json():
    mod = runpy.run_path(str(ROOT / "tools" / "build_playground.py"))
    assert (ROOT / "docs" / "index.html").read_text(encoding="utf-8") == mod["build"]()


def test_playground_has_no_external_requests():
    html = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
    assert not re.search(r'(?:src)="https?://', html)
    assert "fetch(" not in html and "XMLHttpRequest" not in html
