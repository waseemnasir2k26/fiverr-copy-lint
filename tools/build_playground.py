"""Inlines fiverr_copy_lint/rules.json into tools/playground.template.html -> docs/index.html.

  python tools/build_playground.py          rebuild docs/index.html
  python tools/build_playground.py --check  exit 1 if docs/index.html is stale
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TEMPLATE = ROOT / "tools" / "playground.template.html"
RULES = ROOT / "fiverr_copy_lint" / "rules.json"
OUT = ROOT / "docs" / "index.html"


def build() -> str:
    data = json.loads(RULES.read_text(encoding="utf-8"))
    # "</" must not appear inside the inline script
    blob = json.dumps(data, ensure_ascii=True, separators=(",", ":")).replace("</", "<\\/")
    return TEMPLATE.read_text(encoding="utf-8").replace("__RULES_JSON__", blob)


if __name__ == "__main__":
    html = build()
    if "--check" in sys.argv:
        sys.exit(0 if OUT.exists() and OUT.read_text(encoding="utf-8") == html else 1)
    OUT.write_text(html, encoding="utf-8", newline="\n")
    print(f"wrote {OUT} ({len(html)} bytes)")
