# Fiverr Copy Lint: find out why your Fiverr message was blocked

[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)
![Dependencies: none](https://img.shields.io/badge/dependencies-none-brightgreen.svg)

**A free, offline linter for Fiverr gig titles, descriptions, FAQs and buyer messages.** It flags the words and patterns that get messages blocked or gigs sent back (emails, phone numbers, WhatsApp, "pay me", review requests, stuffed titles), gives each one a reason and a safe rewrite, and scores the text 0-100. CLI, GitHub Action and Claude skill. Python standard library only.

> **Not affiliated with, endorsed by or connected to Fiverr.** Fiverr does not publish its filter. These rules are community-observed (field tests plus common policy themes), not an official list. A clean result is not a guarantee Fiverr will accept your text, and a finding is not proof it will be blocked. Never use this to move a buyer off the platform; the rewrites keep the conversation inside Fiverr.

## Quickstart (60 seconds)

```bash
pip install git+https://github.com/waseemnasir2k26/fiverr-copy-lint

# lint a message you are about to send
echo "Hi! You can pay me via PayPal or WhatsApp +92 300 1234567" | fiverr-copy-lint check - --type message

# get a rewritten version (fixed text on stdout, report on stderr)
echo "Email me at sam@gmail.com" | fiverr-copy-lint check - --fix

# browse the rules, or ask why one exists
fiverr-copy-lint rules
fiverr-copy-lint explain OP-006
```

No install? `git clone` the repo and run `python -m fiverr_copy_lint check yourfile.txt`. Python 3.10+, nothing else.

## Real output

This is the actual output of `fiverr-copy-lint check - --type message --fix` on the sample text below (the report goes to stderr, the rewritten text to stdout):

```text
Hi! You can pay me via PayPal, or add me on WhatsApp +92 300 1234567. Email me at sam@gmail.com
```

```text
<stdin> (message) - risk 88/100 [HIGH] - 4 error, 1 warn, 0 info
  1:13  warn  PAY-005  'pay me'  [12-18]
        found: "pay me"
        why:   Confirmed live: the word 'pay' in a seller message triggered the block.
        try:   Say 'my fee'.
  1:24  error PAY-001  Outside payment service  [23-29]
        found: "PayPal"
        why:   Naming an outside payment service is blocked: all payments must go through Fiverr.
        try:   Remove it; the buyer pays through Fiverr checkout.
  1:35  error OP-006   WhatsApp  [34-52]
        found: "add me on WhatsApp"
        why:   WhatsApp is the single most-blocked destination for moving a buyer off the platform.
        try:   Remove it; offer to continue in the Fiverr inbox.
  1:54  error OP-004   Phone number  [53-68]
        found: "+92 300 1234567"
        why:   Phone numbers (9 to 15 digits, any common formatting) are blocked as off-platform contact details.
        try:   Remove the number.
  1:71  error OP-001   Email address  [70-95]
        found: "Email me at sam@gmail.com"
        why:   Sharing an email address is the most common trigger for the 'keep conversations on Fiverr' block.
        try:   Remove the address and invite the buyer to continue in the Fiverr inbox.
```

```text
Hi! You can order through Fiverr, or Let's keep everything in Fiverr's inbox so you're protected
```

`--fix` is a starting point, not a finished message. It swaps risky spans for safe wording; read the result and tidy the grammar. A scripted terminal recording of the same flow is in [`docs/demo.cast`](docs/demo.cast) (play it with `asciinema play docs/demo.cast`; the text is real CLI output, only the typing speed is synthetic).

## Why was my Fiverr message blocked?

The most common reasons sellers report, and what this linter checks:

| What you wrote                                                              | Why it gets caught         | Rule                       |
| --------------------------------------------------------------------------- | -------------------------- | -------------------------- |
| An email address, even as `name (at) site (dot) com` or `g m a i l`         | Contact details            | `OP-001` `OP-002` `OP-003` |
| A phone number, or digits spelled out ("zero three zero zero...")           | Contact details            | `OP-004` `OP-005`          |
| WhatsApp, Telegram, Skype, Discord, WeChat, Zoom                            | Moving the chat off Fiverr | `OP-006` to `OP-011`       |
| "Call me", "DM me", "contact me", "my website", an external link or @handle | Off-platform invitation    | `OP-012` to `OP-018`       |
| PayPal, Venmo, bank transfer, crypto, "pay me directly", "tip me outside"   | Payment outside Fiverr     | `PAY-001` to `PAY-006`     |
| "Leave me a 5 star review", a bonus for a review                            | Review manipulation        | `REV-001` to `REV-004`     |

## Features

| Feature              | Details                                                                                                                                                                                                                              |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| 46 rules in 5 groups | Off-platform contact (18), payment (6), review manipulation (4), gig SEO hygiene (11), buyer-request spam (7). All in one versioned [`rules.json`](fiverr_copy_lint/rules.json).                                                     |
| 5 text types         | `title`, `description`, `faq`, `message`, `request`. Each rule says which types it applies to.                                                                                                                                       |
| Evasion-aware        | Spaced letters (`w.h.a.t.s.a.p.p`), leetspeak (`payp4l`), full-width and look-alike characters, zero-width characters, `(at)`/`(dot)` emails, spelled-out digits. Offsets still point at your original text.                         |
| Risk score           | 0-100 (error 20, warn 8, info 2, capped) with `low` / `medium` / `high` bands.                                                                                                                                                       |
| `--fix`              | Rewrites 27 of the 46 rules automatically. The rest (review incentives, guarantee claims, title length, keyword stuffing) need a human rewrite and say how.                                                                          |
| Output formats       | `text`, `json`, `sarif` (2.1.0, for GitHub code scanning) and `md`.                                                                                                                                                                  |
| Exit codes           | `0` clean, `1` findings at or above `--fail-on` (default `error`), `2` usage or file error.                                                                                                                                          |
| GitHub Action        | [`action.yml`](action.yml): lint copy files in CI, optional SARIF upload.                                                                                                                                                            |
| Claude skill         | [`skill/SKILL.md`](skill/SKILL.md): a `/fiverr-lint` skill that wraps the CLI.                                                                                                                                                       |
| Browser playground   | [`docs/index.html`](docs/index.html), a single file that runs the same `rules.json` in JavaScript. Nothing is uploaded.                                                                                                              |
| Tested               | 221 pytest cases: a positive and negative fixture for every rule, evasion cases, score monotonicity, `--fix` round trips, SARIF shape, and a check that the JS playground matches the Python engine. Run locally on Windows with Python 3.11; a 3-OS GitHub Actions workflow is provided in [`ci/github-actions-ci.yml`](ci/github-actions-ci.yml). |

### Gig SEO hygiene, in short

Title over 80 characters, one keyword repeated 3+ times, ALL CAPS, emoji spam, missing "I will" convention, description under 120 words, keyword dumps, "guaranteed #1 ranking" style claims, banned superlatives, and "official Google partner" style impersonation. See the full list in [`docs/rules.md`](docs/rules.md) (auto-generated from `rules.json`).

## Use it as a GitHub Action

Keep your gig copy in a repo and lint it on every change:

```yaml
- uses: actions/checkout@v4
- uses: waseemnasir2k26/fiverr-copy-lint@v1.0.0
  with:
    path: gig/title.txt gig/description.txt
    fail-on: error
    sarif-output: results.sarif # optional
```

File names that contain `title`, `description`, `faq`, `message` or `request` are typed automatically; otherwise pass `type:`.

## Use it as a Claude skill

Copy `skill/SKILL.md` to `~/.claude/skills/fiverr-lint/SKILL.md`. Then in Claude Code: `/fiverr-lint` and paste your text.

## Browser playground

Try it at **https://waseemnasir2k26.github.io/fiverr-copy-lint/** or open `docs/index.html` locally. It is one file with `rules.json` inlined, and it makes no network requests.

## How the score works

`score = min(100, 20 x errors + 8 x warnings + 2 x infos)`. Overlapping matches keep only the strongest one. Bands: 0-19 low, 20-49 medium, 50+ high. Adding a risky phrase never lowers the score (tested).

## FAQ

**Why was my Fiverr message blocked?**
Usually because it contained contact details or payment words: an email, a phone number, WhatsApp/Telegram/Skype/Discord, "pay", "PayPal", an external link. Run the message through `fiverr-copy-lint check` to see which phrase matched and what to write instead.

**Does Fiverr publish a list of blocked words?**
No. This tool uses a community-observed list seeded from one seller's live tests (for example `email`, `pay`/`payment` and `Discord` tripped the filter in a normal discovery message) plus common policy themes. Treat it as a pre-flight check, not a verdict.

**Can I trick the filter with `pa.y` or `g m a i l`?**
Don't. Those are flagged on purpose: disguised spellings look worse than the plain word, and moving buyers off Fiverr can get an account restricted. Rewrite the sentence instead.

**Is my text uploaded anywhere?**
No. The CLI is offline, has no dependencies and makes no network calls. The playground is a static page with no requests either.

**Does a score of 0 mean Fiverr will accept it?**
No. It means none of these rules matched.

**False positives?**
Yes, some. Examples: `Zoom` in a video gig that means camera zoom, or `crypto` in a crypto gig. Rules say when they can misfire. Use `--fail-on never` to report without failing, and open an issue with the text that was wrongly flagged.

**How do I add or change a rule?**
Edit `tools/gen_rules.py` (the source of `rules.json`), then run `python tools/gen_rules.py`, `python tools/build_playground.py` and `fiverr-copy-lint rules --format md > docs/rules.md`. Tests fail if any generated file is stale.

## Limitations

- Rules are English-only.
- The JS playground reports offsets in UTF-16 units, the CLI in Python code points (identical for text without emoji).
- Heuristics (length, stuffing, caps) are tuned guesses, not Fiverr thresholds, apart from the 80-character title cap.
- It does not log in to Fiverr, scrape it or automate anything on the platform.

## Development

A GitHub Actions workflow (Linux, Windows, macOS, Python 3.10 and 3.12, plus a self-test of the Action) is in [`ci/github-actions-ci.yml`](ci/github-actions-ci.yml). Copy it to `.github/workflows/ci.yml` to enable it; pushing workflow files needs a token with the `workflow` scope, which the release tooling did not have, so it is not enabled yet.

```bash
pip install -e ".[test]"
python -m pytest -q
python tools/gen_rules.py --check && python tools/build_playground.py --check
```

## More from SkynetLabs

- [fiverr-gig-optimizer](https://github.com/waseemnasir2k26/fiverr-gig-optimizer) - audit a whole gig (score, tags, package ladder, fee maths). It includes a small message lint; this repo is the dedicated, deeper rule engine.
- [upwork-job-radar](https://github.com/waseemnasir2k26/upwork-job-radar) - score new Upwork jobs against your own rubric via the official API. Read and alert only.
- [n8n-workflows](https://github.com/waseemnasir2k26/n8n-workflows) - production n8n workflows you can import and run.

## Want a gig that passes review and converts?

**[Done-for-you gig rewrite](https://www.fiverr.com/agencies/skynetjoellc)** - title, description, FAQ and packages written to pass review and read well to buyers.

## Work with SkynetLabs

Built by [Waseem Nasir](https://www.skynetjoe.com/?utm_source=github&utm_medium=readme&utm_campaign=fiverr-copy-lint) at SkynetLabs — n8n + AI automation for small businesses.

- Hire on Fiverr: https://www.fiverr.com/agencies/skynetjoellc
- Hire on Upwork: https://www.upwork.com/freelancers/muhammadwaseemnasir
- Book a free call: https://calendly.com/skynetlabs/schedule-a-free-consultation
