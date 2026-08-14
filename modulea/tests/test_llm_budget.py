"""The run budget (BuildSpec §7). No API calls — that is the point.

The cap has to refuse *before* the request is made, otherwise it is a report of
what was spent rather than a limit on it. These tests assert that by giving the
client no API key at all: if the budget check were happening after the call was
constructed, the missing key would surface first.
"""

from __future__ import annotations

import pytest

from regspine.common.llm import LLM, BudgetExceeded, RunBudget, Usage, load_config


@pytest.fixture(scope="module")
def config() -> dict:
    return load_config()


def test_config_prices_every_routed_model(config):
    """A routed model with no price silently escapes the budget."""
    routed = set()
    for job in config["routing"].values():
        routed.add(job["model"])
        if "escalate_to" in job:
            routed.add(job["escalate_to"])
    assert routed <= set(config["pricing"]), routed - set(config["pricing"])


def test_budget_refuses_before_the_call_is_made(config, monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    llm = LLM(config=config, budget=RunBudget(cap_inr=0.001, warn_inr=0.0, max_calls=100))

    with pytest.raises(BudgetExceeded):
        llm.call("extract_obligations", system="x" * 4000, user="y" * 4000)

    assert llm.budget.calls == 0
    assert llm.budget.spent_inr == 0.0


def test_call_cap_is_independent_of_cost(config):
    """A retry storm can be individually cheap and still be a runaway."""
    budget = RunBudget(cap_inr=1_000_000.0, warn_inr=1.0, max_calls=3)
    budget.calls = 3
    with pytest.raises(BudgetExceeded, match="call cap"):
        budget.check(0.0)


def test_spend_accumulates_and_is_attributed(config):
    llm = LLM(config=config, budget=RunBudget(cap_inr=100.0, warn_inr=99.0, max_calls=10))
    usage = Usage(
        job="extract_obligations",
        model="claude-sonnet-5",
        input_tokens=10_000,
        output_tokens=2_000,
    )
    cost = llm.cost_inr("claude-sonnet-5", usage)
    llm.budget.record(usage, cost)

    # 10k in @ $3/M + 2k out @ $15/M = $0.06 -> ~Rs 5.10 at 85/USD
    assert cost == pytest.approx(5.10, abs=0.2)
    assert llm.budget.calls == 1
    assert "extract_obligations" in llm.budget.report()


def test_cache_reads_are_priced_far_below_fresh_input(config):
    """Prompt caching is the reason a ~1,500-clause run is affordable, so the
    saving has to be real in the accounting too."""
    llm = LLM(config=config)
    fresh = llm.cost_inr(
        "claude-sonnet-5", Usage(job="j", model="claude-sonnet-5", input_tokens=100_000)
    )
    cached = llm.cost_inr(
        "claude-sonnet-5", Usage(job="j", model="claude-sonnet-5", cache_read_tokens=100_000)
    )
    assert cached < fresh / 5


def test_unknown_model_is_an_error_not_a_free_call(config):
    llm = LLM(config=config)
    with pytest.raises(KeyError):
        llm.cost_inr("some-unpriced-model", Usage(job="j", model="some-unpriced-model"))


def test_unknown_job_is_rejected(config):
    llm = LLM(config=config)
    with pytest.raises(KeyError):
        llm.route("no_such_job")
