"""One positive and one negative fixture per rule, driven by the examples in rules.json."""
import pytest

from fiverr_copy_lint.engine import check, load_catalogue

META, RULES = load_catalogue()
IDS = [r.id for r in RULES]


def ids_found(text, ttype):
    return {f.rule_id for f in check(text, ttype).findings}


@pytest.mark.parametrize("rule", RULES, ids=IDS)
def test_positive_fixture_triggers_rule(rule):
    ex = rule.examples
    assert rule.id in ids_found(ex["bad"], ex["type"]), f"{rule.id} did not fire on its bad fixture"


@pytest.mark.parametrize("rule", RULES, ids=IDS)
def test_negative_fixture_does_not_trigger_rule(rule):
    ex = rule.examples
    assert rule.id not in ids_found(ex["good"], ex["type"]), f"{rule.id} fired on its good fixture"


@pytest.mark.parametrize("rule", RULES, ids=IDS)
def test_rule_is_documented(rule):
    assert rule.rationale and rule.suggestion and rule.name
    assert rule.severity in ("error", "warn", "info")
    assert rule.examples["type"] in rule.applies


def test_catalogue_size_and_groups():
    assert len(RULES) >= 40
    assert {r.group for r in RULES} == {"off-platform", "payment", "review-manipulation", "gig-seo", "buyer-request"}
    assert len(set(IDS)) == len(IDS)


def test_note_is_honest_about_source():
    assert "NOT AN OFFICIAL FIVERR LIST" in META["note"]
