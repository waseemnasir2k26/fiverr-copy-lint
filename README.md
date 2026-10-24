# fiverr-copy-lint

Your Fiverr message got blocked and the error does not say which word did it. This is a free, offline linter that finds the phrase, explains why, and suggests a safe rewrite.

> Not affiliated with, endorsed by or connected to Fiverr. Fiverr does not publish its filter. These rules are community-observed (field tests plus common policy themes), not an official list. A clean result is not a guarantee, and a finding is not proof of a block. Do not use this to move a buyer off the platform; the rewrites keep the conversation inside Fiverr.

- Lints gig **titles, descriptions, FAQs, buyer messages and buyer-request replies**.
- 46 rules in 5 groups: off-platform contact, outside payment, review manipulation, gig SEO hygiene, buyer-request spam. All live in one versioned [`rules.json`](fiverr_copy_lint/rules.json).
- Catches evasion too: spaced letters, leetspeak, look-alike and zero-width characters, `(at)` / `(dot)` emails, spelled-out digits.
- Scores text 0-100 (low / medium / high) and gives a reason and a "try this instead" per finding.
- `--fix` rewrites the rules that can be fixed automatically; the rest tell you how to fix them by hand.
- Python standard library only. CLI, GitHub Action, Claude skill and a browser playground.

## Quickstart

```bash
pip install git+https://github.com/waseemnasir2k26/fiverr-copy-lint

# lint a message you are about to send
echo "Hi! You can pay me via PayPal or WhatsApp +92 300 1234567" | fiverr-copy-lint check - --type message

# rewritten text on stdout, report on stderr
echo "Email me at sam@example.com" | fiverr-copy-lint check - --fix

# browse rules, or ask why one exists
fiverr-copy-lint rules
fiverr-copy-lint explain OP-006
```

No install: clone the repo and run `python -m fiverr_copy_lint check yourfile.txt`. Python 3.10+.

## Example

```text
<stdin> (message) - risk 88/100 [HIGH] - 4 error, 1 warn, 0 info
  1:24  error PAY-001  Outside payment service
        found: "PayPal"
        why:   Naming an outside payment service is blocked: all payments must go through Fiverr.
        try:   Remove it; the buyer pays through Fiverr checkout.
  1:35  error OP-006   WhatsApp
        found: "add me on WhatsApp"
        try:   Remove it; offer to continue in the Fiverr inbox.
```

`--fix` is a starting point. It swaps risky spans for safe wording; read the result and tidy the grammar.

## What gets flagged

| You wrote | Rule |
| --- | --- |
| An email address, including `name (at) site (dot) com` | `OP-001` to `OP-003` |
| A phone number, or digits spelled out | `OP-004`, `OP-005` |
| WhatsApp, Telegram, Skype, Discord, WeChat, Zoom | `OP-006` to `OP-011` |
| "Call me", "DM me", "my website", external links, @handles | `OP-012` to `OP-018` |
| PayPal, Venmo, bank transfer, crypto, "pay me directly" | `PAY-001` to `PAY-006` |
| "Leave me a 5 star review", a bonus for a review | `REV-001` to `REV-004` |

Gig SEO hygiene covers title length over 80 characters, one keyword repeated 3+ times, ALL CAPS, emoji spam, short descriptions, keyword dumps and "guaranteed #1 ranking" style claims. Full list: [`docs/rules.md`](docs/rules.md).

## Score and exit codes

`score = min(100, 20 x errors + 8 x warnings + 2 x infos)`. Bands: 0-19 low, 20-49 medium, 50+ high. Exit codes: `0` clean, `1` findings at or above `--fail-on` (default `error`), `2` usage or file error. Output formats: `text`, `json`, `sarif`, `md`.

## GitHub Action

```yaml
- uses: actions/checkout@v4
- uses: waseemnasir2k26/fiverr-copy-lint@v1.0.0
  with:
    path: gig/title.txt gig/description.txt
    fail-on: error
    sarif-output: results.sarif # optional
```

File names containing `title`, `description`, `faq`, `message` or `request` are typed automatically; otherwise pass `type:`.

## Claude skill

Copy `skill/SKILL.md` to `~/.claude/skills/fiverr-lint/SKILL.md`, then run `/fiverr-lint` in Claude Code and paste your text.

## Browser playground

https://waseemnasir2k26.github.io/fiverr-copy-lint/ (or open `docs/index.html`). One file, `rules.json` inlined, no network requests.

## For you if

You sell on Fiverr and want to check a gig or a message before it goes out, or you keep gig copy in a repo and want a CI check.

## Limits

- English rules only.
- Some false positives: `Zoom` in a camera gig, `crypto` in a crypto gig. Use `--fail-on never` to report without failing.
- Length, stuffing and caps heuristics are tuned guesses, not Fiverr thresholds (apart from the 80-character title cap).
- A score of 0 only means none of these rules matched.
- The tool is offline. It never logs in to Fiverr or automates anything on the platform.

## Develop

```bash
pip install -e ".[test]"
python -m pytest -q
python tools/gen_rules.py --check && python tools/build_playground.py --check
```

To change a rule, edit `tools/gen_rules.py`, then run `python tools/gen_rules.py` and `python tools/build_playground.py`. A CI workflow is provided in [`ci/github-actions-ci.yml`](ci/github-actions-ci.yml); copy it to `.github/workflows/ci.yml` to enable it (needs a token with the `workflow` scope).

Related: [fiverr-gig-optimizer](https://github.com/waseemnasir2k26/fiverr-gig-optimizer) audits a whole gig (score, tags, package ladder, fee maths).

## Built by SkynetLabs

MIT licensed.

Need this wired into your business? SkynetLabs builds voice agents, n8n back offices and sites that convert → https://skynetjoe.com
