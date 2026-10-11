"""Builds docs/demo.cast (asciicast v2) from the CLI's REAL output.

The text on screen is captured by actually running the commands below; only the typing
delays are synthetic. It is a scripted recording, not a live terminal session.

  python tools/make_cast.py
  asciinema play docs/demo.cast
"""
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "docs" / "demo.cast"

STEPS = [
    ("fiverr-copy-lint check examples/bad-message.txt --fix", ["check", "examples/bad-message.txt", "--fix"], True),
]


def run(args):
    p = subprocess.run([sys.executable, "-m", "fiverr_copy_lint", *args], capture_output=True, text=True,
                       encoding="utf-8", cwd=ROOT)
    return p.stderr + p.stdout  # report (stderr) first, then fixed text (stdout)


def main():
    events, t = [], 0.5
    header = {"version": 2, "width": 110, "height": 40, "timestamp": 1760227200,
              "title": "fiverr-copy-lint: why was my Fiverr message blocked?", "env": {"SHELL": "/bin/bash", "TERM": "xterm-256color"}}

    def emit(text, dt):
        nonlocal t
        t += dt
        events.append([round(t, 3), "o", text])

    for shown, args, _ in STEPS:
        emit("$ ", 0.2)
        for ch in shown:
            emit(ch, 0.045)
        emit("\r\n", 0.5)
        out = run(args).replace("\r\n", "\n").rstrip("\n")
        lines = out.split("\n")
        for line in lines:
            emit(line + "\r\n", 0.06)
        emit("\r\n", 0.8)
    emit("$ ", 0.2)
    OUT.write_text(json.dumps(header) + "\n" + "\n".join(json.dumps(e) for e in events) + "\n", encoding="utf-8")
    print(f"wrote {OUT} ({len(events)} events)")


if __name__ == "__main__":
    main()
