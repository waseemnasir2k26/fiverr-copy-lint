# Changelog

All notable changes to this project are documented here. Format follows [Keep a Changelog](https://keepachangelog.com/).

## [1.0.0] - 2026-10-12

### Added

- `fiverr-copy-lint check` for titles, descriptions, FAQs, buyer messages and buyer-request replies, with `text`, `json`, `sarif` and `md` output.
- `--fix` to rewrite risky spans with safe alternatives, `--in-place` to write them back to the file.
- `fiverr-copy-lint rules` and `fiverr-copy-lint explain <rule-id>`.
- 46 rules in one versioned `rules.json` across off-platform contact, payment, review manipulation, gig SEO hygiene and buyer-request spam.
- Evasion handling: spaced-out letters, leetspeak, full-width and look-alike characters, zero-width characters, `(at)`/`(dot)` emails, digits spelled as words.
- 0-100 risk score with `low` / `medium` / `high` bands.
- Composite GitHub Action (`action.yml`) with optional SARIF output.
- `/fiverr-lint` Claude skill (`skill/SKILL.md`).
- Single-file browser playground (`docs/index.html`) that runs the same `rules.json` in JavaScript.
- Auto-generated rule catalogue (`docs/rules.md`).
- Test suite (221 cases). A 3-OS GitHub Actions workflow ships as `ci/github-actions-ci.yml` (copy to `.github/workflows/` to enable).
