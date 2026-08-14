"""LLM client: routing, prompt caching, token accounting and the run budget (§7).

Two rules this module exists to enforce:

- **A run cannot exceed its budget.** ``RunBudget`` is checked *before* each call
  and refuses once the projected spend would cross the cap. The failure mode being
  guarded against is a loop over ~1,500 clauses, not any single call, so the cap is
  per-run and the check happens up front rather than after the money is gone.
- **Every call is attributed.** Tokens and cost are logged per job, so "extraction
  cost X" is a measurement rather than an estimate.

Keys come from the environment (§11). Nothing here reads a file that could be
committed.
"""

from __future__ import annotations

import os
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_PATH = Path(__file__).resolve().parents[2] / "config" / "models.yaml"


class BudgetExceeded(RuntimeError):
    """Raised instead of making a call that would breach the run budget."""


@dataclass
class Usage:
    job: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cache_write_tokens: int = 0
    cache_read_tokens: int = 0
    seconds: float = 0.0

    @property
    def total_tokens(self) -> int:
        return (
            self.input_tokens
            + self.output_tokens
            + self.cache_write_tokens
            + self.cache_read_tokens
        )


@dataclass
class RunBudget:
    """Per-run spend guard. Costs are in INR via the fx rate in models.yaml."""

    cap_inr: float
    warn_inr: float
    max_calls: int
    spent_inr: float = 0.0
    calls: int = 0
    usages: list[Usage] = field(default_factory=list)
    _warned: bool = False

    def check(self, projected_inr: float = 0.0) -> None:
        if self.calls >= self.max_calls:
            raise BudgetExceeded(
                f"call cap reached ({self.max_calls} calls). "
                f"Spent ~Rs {self.spent_inr:.2f}. Raise budget.max_calls to continue."
            )
        if self.spent_inr + projected_inr > self.cap_inr:
            raise BudgetExceeded(
                f"run budget of Rs {self.cap_inr:.2f} would be exceeded "
                f"(spent Rs {self.spent_inr:.2f} over {self.calls} calls). "
                f"Raise budget.per_run_inr in config/models.yaml to continue."
            )

    def record(self, usage: Usage, cost_inr: float) -> None:
        self.usages.append(usage)
        self.spent_inr += cost_inr
        self.calls += 1
        if not self._warned and self.spent_inr >= self.warn_inr:
            self._warned = True
            print(
                f"[budget] Rs {self.spent_inr:.2f} of Rs {self.cap_inr:.2f} spent "
                f"after {self.calls} calls."
            )

    def report(self) -> str:
        by_job: dict[str, list[Usage]] = {}
        for u in self.usages:
            by_job.setdefault(u.job, []).append(u)
        lines = [
            f"LLM spend: Rs {self.spent_inr:.2f} of Rs {self.cap_inr:.2f} "
            f"over {self.calls} calls"
        ]
        for job, us in sorted(by_job.items()):
            lines.append(
                f"  {job:<22} {len(us):>4} calls  "
                f"in={sum(u.input_tokens for u in us):>8}  "
                f"out={sum(u.output_tokens for u in us):>7}  "
                f"cache_r={sum(u.cache_read_tokens for u in us):>8}  "
                f"{sum(u.seconds for u in us):>6.1f}s"
            )
        return "\n".join(lines)


def load_config(path: Path | str = CONFIG_PATH) -> dict[str, Any]:
    with open(path) as fh:
        return yaml.safe_load(fh)


class LLM:
    """Thin Anthropic wrapper that routes by job name and enforces the budget."""

    def __init__(self, config: dict | None = None, budget: RunBudget | None = None):
        self.config = config or load_config()
        b = self.config["budget"]
        self.budget = budget or RunBudget(
            cap_inr=float(b["per_run_inr"]),
            warn_inr=float(b["warn_at_inr"]),
            max_calls=int(b["max_calls"]),
        )
        self._client = None

    # -- pricing ---------------------------------------------------------

    def _price(self, model: str) -> dict:
        pricing = self.config["pricing"]
        if model not in pricing:
            raise KeyError(f"No pricing for '{model}' in config/models.yaml.")
        return pricing[model]

    def cost_inr(self, model: str, usage: Usage) -> float:
        p = self._price(model)
        fx = float(self.config["fx"]["usd_to_inr"])
        usd = (
            usage.input_tokens * p["input"]
            + usage.output_tokens * p["output"]
            + usage.cache_write_tokens * p.get("cache_write", p["input"])
            + usage.cache_read_tokens * p.get("cache_read", p["input"])
        ) / 1_000_000
        return usd * fx

    def estimate_inr(self, model: str, in_tokens: int, out_tokens: int) -> float:
        """Pre-call projection, used to refuse before spending rather than after."""
        return self.cost_inr(
            model, Usage(job="_estimate", model=model, input_tokens=in_tokens,
                         output_tokens=out_tokens)
        )

    # -- client ----------------------------------------------------------

    @property
    def client(self):
        if self._client is None:
            import anthropic

            key = os.environ.get("ANTHROPIC_API_KEY")
            if not key:
                raise RuntimeError(
                    "ANTHROPIC_API_KEY is not set. Module A reads keys from the "
                    "environment only (BuildSpec §11)."
                )
            self._client = anthropic.Anthropic(api_key=key)
        return self._client

    def route(self, job: str) -> dict:
        routing = self.config["routing"]
        if job not in routing:
            raise KeyError(f"No routing for job '{job}' in config/models.yaml.")
        return routing[job]

    # -- the call --------------------------------------------------------

    def call(
        self,
        job: str,
        *,
        system: str,
        user: str,
        tools: list | None = None,
        tool_choice: dict | None = None,
        model: str | None = None,
        max_tokens: int | None = None,
        cache_system: bool = True,
    ):
        """Make one routed, budgeted call. Returns (message, usage).

        ``system`` is sent as a cacheable prefix: it is the static half (schema,
        instructions, taxonomy) and is identical across every clause in a run, so
        caching turns ~1,500 repeats into one write and 1,499 cheap reads.
        """
        route = self.route(job)
        model = model or route["model"]
        max_tokens = max_tokens or int(route.get("max_tokens", 2000))

        # Rough projection: 4 chars/token, plus the full output allowance.
        projected = self.estimate_inr(model, (len(system) + len(user)) // 4, max_tokens)
        self.budget.check(projected)

        system_blocks = [{"type": "text", "text": system}]
        if cache_system:
            system_blocks[0]["cache_control"] = {"type": "ephemeral"}

        kwargs: dict[str, Any] = {
            "model": model,
            "max_tokens": max_tokens,
            "system": system_blocks,
            "messages": [{"role": "user", "content": user}],
        }
        if tools:
            kwargs["tools"] = tools
        if tool_choice:
            kwargs["tool_choice"] = tool_choice

        started = time.monotonic()
        message = self.client.messages.create(**kwargs)
        elapsed = time.monotonic() - started

        u = message.usage
        usage = Usage(
            job=job,
            model=model,
            input_tokens=getattr(u, "input_tokens", 0) or 0,
            output_tokens=getattr(u, "output_tokens", 0) or 0,
            cache_write_tokens=getattr(u, "cache_creation_input_tokens", 0) or 0,
            cache_read_tokens=getattr(u, "cache_read_input_tokens", 0) or 0,
            seconds=elapsed,
        )
        self.budget.record(usage, self.cost_inr(model, usage))
        return message, usage
