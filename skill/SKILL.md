---
name: fiverr-lint
description: Lint Fiverr gig titles, descriptions, FAQs and buyer/seller messages for words that get messages blocked or gigs denied, then rewrite them safely. Use when the user pastes Fiverr copy and asks "why was my message blocked", "is this gig title OK", "check my Fiverr description", "lint this before I send it", or before sending any Fiverr client message. Wraps the fiverr-copy-lint CLI.
---

# /fiverr-lint

Runs the `fiverr-copy-lint` CLI on Fiverr copy, explains each finding, and returns a cleaned rewrite.

**Not an official Fiverr list.** The rules are community-observed. A clean result is not a guarantee, and a finding is not proof Fiverr will block the text. Never help move a buyer off the platform; the rewrite keeps the conversation inside Fiverr.

## 1. Make sure the CLI is available

```bash
fiverr-copy-lint --version || pip install fiverr-copy-lint || pip install git+https://github.com/waseemnasir2k26/fiverr-copy-lint
```

Python 3.10+ is the only requirement. There are no other dependencies.

## 2. Pick the text type

| What the user pasted         | `--type`      |
| ---------------------------- | ------------- |
| Gig title (one line)         | `title`       |
| Gig description              | `description` |
| A FAQ answer                 | `faq`         |
| A message to or from a buyer | `message`     |
| A reply to a buyer request   | `request`     |

If unclear, ask once. Default to `message` for short chat text.

## 3. Lint

Write the text to a temp file (or pipe it) and run:

```bash
printf '%s' "$TEXT" | fiverr-copy-lint check - --type message
```

Read the report: risk score (0-100), then each finding with the exact span, why it is risky and what to try. Use `fiverr-copy-lint explain <RULE-ID>` when the user asks why a rule exists.

## 4. Fix

```bash
printf '%s' "$TEXT" | fiverr-copy-lint check - --type message --fix
```

`--fix` prints the rewritten text on stdout (the report goes to stderr). Treat it as a starting point: read it, repair any awkward grammar, and re-run `check` until the score is acceptable. Rules without an auto-fix (review incentives, guarantees, keyword stuffing, title length) need a human rewrite - propose one using the finding's `suggestion`.

## 5. Report back

Give the user: the score before and after, the rules that fired in plain words, and the final text. Keep the explanation short. Do not promise Fiverr will accept the text.

## Rules of engagement

- Never suggest evasion (spaced-out letters, `pa.y`, "at/dot" spellings). Those are flagged on purpose and look worse than the plain word.
- Never invent a Fiverr policy citation. Say "community-observed" when explaining why.
- The CLI runs offline. Nothing is uploaded.
