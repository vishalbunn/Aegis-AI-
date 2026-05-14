"""
Model client for Aegis AI v5.

Two-tier setup (canonical):
  - DEBATER: Llama-3.1-8B-instant (Pro, Con, Safety, Uncertainty)
  - JUDGE:   Llama-3.3-70B-versatile (Critic, Final, Consensus, Scoring, Bias)

Single-tier setup (current — token-budget mode):
  Both debater and judge use Llama-3.1-8B-instant.

Production features:
  - LRU cache (1hr TTL) — same prompt returns cached result
  - Cost / token tracking
  - Strict mode for eval (raise on failure)
"""
import os
import threading
from pathlib import Path
from openai import OpenAI
from dotenv import load_dotenv

# Walk up to find .env regardless of cwd.
_HERE = Path(__file__).resolve()
for parent in [_HERE.parent, _HERE.parent.parent, _HERE.parent.parent.parent]:
    candidate = parent / ".env"
    if candidate.exists():
        load_dotenv(dotenv_path=candidate)
        break
else:
    load_dotenv()

# Models. Override in .env to switch.
DEBATER_MODEL = os.getenv("AEGIS_DEBATER_MODEL", "llama-3.1-8b-instant")
JUDGE_MODEL   = os.getenv("AEGIS_JUDGE_MODEL",   "llama-3.1-8b-instant")

STRICT_MODE = os.getenv("AEGIS_STRICT", "0") == "1"
CACHE_ENABLED = os.getenv("AEGIS_CACHE", "1") == "1"

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
if not GROQ_API_KEY:
    raise RuntimeError(
        "GROQ_API_KEY not found. Make sure .env exists in the project root and contains:\n"
        "GROQ_API_KEY=gsk_your_key_here"
    )

client = OpenAI(
    base_url="https://api.groq.com/openai/v1",
    api_key=GROQ_API_KEY,
)


class ModelCallError(RuntimeError):
    """Raised in strict mode when an LLM call fails."""


# ─── Cost tracking ───────────────────────────────────────────────────
# Groq pricing reference (per million tokens, on-demand tier):
#   llama-3.1-8b-instant:     input $0.05  / output $0.08
#   llama-3.3-70b-versatile:  input $0.59  / output $0.79
PRICING = {
    "llama-3.1-8b-instant":    {"in_per_m": 0.05,  "out_per_m": 0.08},
    "llama-3.3-70b-versatile": {"in_per_m": 0.59,  "out_per_m": 0.79},
}


class CostTracker:
    def __init__(self):
        self._lock = threading.Lock()
        self._calls = 0
        self._failures = 0
        self._input_tokens = 0
        self._output_tokens = 0
        self._cost_usd = 0.0
        self._by_model: dict = {}

    def record(self, model: str, in_tok: int, out_tok: int) -> None:
        price = PRICING.get(model, {"in_per_m": 0, "out_per_m": 0})
        cost = (in_tok / 1_000_000) * price["in_per_m"] + (out_tok / 1_000_000) * price["out_per_m"]
        with self._lock:
            self._calls += 1
            self._input_tokens += in_tok
            self._output_tokens += out_tok
            self._cost_usd += cost
            m = self._by_model.setdefault(model, {"calls": 0, "in_tokens": 0, "out_tokens": 0, "cost_usd": 0.0})
            m["calls"] += 1
            m["in_tokens"] += in_tok
            m["out_tokens"] += out_tok
            m["cost_usd"] += cost

    def record_failure(self):
        with self._lock:
            self._failures += 1

    def stats(self) -> dict:
        with self._lock:
            return {
                "total_calls": self._calls,
                "failures": self._failures,
                "input_tokens": self._input_tokens,
                "output_tokens": self._output_tokens,
                "total_cost_usd": round(self._cost_usd, 4),
                "by_model": {
                    k: {**v, "cost_usd": round(v["cost_usd"], 4)} for k, v in self._by_model.items()
                },
            }


cost_tracker = CostTracker()


# ─── Cache import (deferred to avoid circular) ───────────────────────
def _get_cache():
    try:
        from cache import llm_cache
        return llm_cache
    except ImportError:
        return None


# ─── Core call ───────────────────────────────────────────────────────

def _call(model: str, prompt: str, temperature: float = 0.7, max_tokens: int = 1024) -> str:
    # 1. Check cache (only at low-ish temperature — high temp wants fresh sampling)
    cache = _get_cache() if CACHE_ENABLED and temperature <= 0.5 else None
    if cache is not None:
        cached = cache.get(model, prompt, temperature)
        if cached is not None:
            return cached

    # 2. Make the API call
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=temperature,
            max_tokens=max_tokens,
        )
        text = resp.choices[0].message.content or ""

        # Record cost / token usage
        usage = getattr(resp, "usage", None)
        if usage:
            cost_tracker.record(
                model,
                getattr(usage, "prompt_tokens", 0),
                getattr(usage, "completion_tokens", 0),
            )

        if not text.strip():
            cost_tracker.record_failure()
            if STRICT_MODE:
                raise ModelCallError(f"Empty response from {model}")
            return f"Model Error: empty response from {model}"

        # Store in cache for future calls (only stable / low-temp responses)
        if cache is not None:
            cache.set(model, prompt, temperature, text)

        return text

    except Exception as e:
        cost_tracker.record_failure()
        if STRICT_MODE:
            raise ModelCallError(f"{model}: {e}") from e
        return f"Model Error: {e}"


def call_debater(prompt: str, temperature: float = 0.7) -> str:
    return _call(DEBATER_MODEL, prompt, temperature=temperature)


def call_judge(prompt: str, temperature: float = 0.3) -> str:
    return _call(JUDGE_MODEL, prompt, temperature=temperature)


def call_model(prompt: str) -> str:
    """Back-compat shim — old code calls call_model()."""
    return call_debater(prompt)