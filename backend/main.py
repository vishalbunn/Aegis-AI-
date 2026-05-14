"""
Aegis AI v5 — main pipeline.

Two debate modes:
  - parallel:   Pro and Con run independently (v4 behavior)
  - sequential: Pro and Con run for N rounds, each sees opponent's last (v5)

Two pipeline entry points:
  - full_pipeline:  used by the web UI. Runs every agent.
  - eval_pipeline:  used by the eval harness. Skips display-only agents.

Production features:
  - Per-IP rate limiting on /analyze
  - /admin dashboard for observability
  - Cost & cache stats exposed
"""
import sys
import os
import asyncio
import time

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from pydantic import BaseModel
from typing import Optional, List, Literal

from agents.debate_agents  import pro_agent, con_agent
from agents.judge_agents   import critic_agent, final_agent, consensus_agent, scoring_agent
from agents.bias_agent     import bias_agent
from agents.safety_agent   import safety_agent
from agents.uncertainty_agent import uncertainty_agent
from agents.orchestrator   import orchestrator
from agents.baseline_agent import baseline_agent
from agents.model          import cost_tracker

from database   import init_db, save_decision, get_all_decisions, get_decision_by_id, get_all_raw
from logger     import log_request, get_logs
from similarity import find_similar, detect_changed
from cache      import llm_cache
from rate_limiter import rate_limiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        init_db()
        print("Aegis AI v5.0 - DB initialized")
    except Exception as e:
        print("DB init skipped:", str(e))
    yield


app = FastAPI(title="Aegis AI", version="5.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")
app.mount("/static", StaticFiles(directory=frontend_path), name="static")

DOMAIN_PROMPTS = {
    "healthcare": "Focus on medical feasibility, patient safety, evidence-based outcomes, and ethics.",
    "business":   "Focus on ROI, market viability, competitive landscape, and financial risk.",
    "career":     "Focus on long-term growth, skill development, financial stability, and work-life balance.",
    "tech":       "Focus on technical feasibility, scalability, maintainability, and ecosystem maturity.",
    "general":    "",
}


class Query(BaseModel):
    text: str
    domain: str = "general"
    context: Optional[str] = None
    run_baseline: bool = True
    debate_mode: Literal["parallel", "sequential"] = "sequential"
    debate_rounds: int = 2


async def run(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)


# ─── DEBATE LOOPS ────────────────────────────────────────────────────

async def run_parallel_debate(query: str, use_tools: bool, domain_hint: str) -> dict:
    pro_text, con_text = await asyncio.gather(
        run(pro_agent, query, use_tools, domain_hint, "", "", 1),
        run(con_agent, query, use_tools, domain_hint, "", "", 1),
    )
    return {
        "pro_rounds":  [pro_text],
        "con_rounds":  [con_text],
        "pro_final":   pro_text,
        "con_final":   con_text,
        "rounds_run":  1,
        "mode":        "parallel",
    }


async def run_sequential_debate(query: str, use_tools: bool, domain_hint: str, rounds: int) -> dict:
    pro_rounds: List[str] = []
    con_rounds: List[str] = []

    pro_r1, con_r1 = await asyncio.gather(
        run(pro_agent, query, use_tools, domain_hint, "", "", 1),
        run(con_agent, query, use_tools, domain_hint, "", "", 1),
    )
    pro_rounds.append(pro_r1)
    con_rounds.append(con_r1)

    for r in range(2, rounds + 1):
        pro_next, con_next = await asyncio.gather(
            run(pro_agent, query, False, domain_hint, con_rounds[-1], pro_rounds[-1], r),
            run(con_agent, query, False, domain_hint, pro_rounds[-1], con_rounds[-1], r),
        )
        pro_rounds.append(pro_next)
        con_rounds.append(con_next)

    return {
        "pro_rounds":  pro_rounds,
        "con_rounds":  con_rounds,
        "pro_final":   pro_rounds[-1],
        "con_final":   con_rounds[-1],
        "rounds_run":  rounds,
        "mode":        "sequential",
    }


# ─── FULL PIPELINE (UI) ──────────────────────────────────────────────

async def full_pipeline(
    query: str,
    domain: str = "general",
    context: str = "",
    run_baseline_flag: bool = True,
    debate_mode: str = "sequential",
    debate_rounds: int = 2,
) -> dict:
    t0 = time.time()
    domain_hint = DOMAIN_PROMPTS.get(domain, "")
    full_query = f"{context}\n\nCurrent query: {query}".strip() if context else query

    safety = await run(safety_agent, full_query)
    if not safety.get("safe", True):
        return {"blocked": True, "safety": safety,
                "final": {"verdict": "blocked", "reasoning": safety.get("reason", "")}}

    routing, uncertainty, similar_raw = await asyncio.gather(
        run(orchestrator, full_query),
        run(uncertainty_agent, full_query),
        asyncio.to_thread(get_all_raw),
    )
    similar = find_similar(query, similar_raw)
    memory_note = detect_changed(query, similar)
    use_tools = routing.get("run_tools", False)

    baseline_coro = run(baseline_agent, query) if run_baseline_flag else asyncio.sleep(0)
    if debate_mode == "sequential":
        debate_coro = run_sequential_debate(full_query, use_tools, domain_hint, debate_rounds)
    else:
        debate_coro = run_parallel_debate(full_query, use_tools, domain_hint)

    debate, baseline_result = await asyncio.gather(debate_coro, baseline_coro)
    pro_final = debate["pro_final"]
    con_final = debate["con_final"]

    critique = await run(critic_agent, pro_final, con_final, query)
    final_r = await run(final_agent, full_query, pro_final, con_final, critique)

    bias, scores, consensus = await asyncio.gather(
        run(bias_agent, pro_final, con_final, query),
        run(scoring_agent, query, final_r, pro_final, con_final),
        run(consensus_agent, query, pro_final, con_final, critique, final_r, 1),
    )

    latency = round((time.time() - t0) * 1000, 1)

    response = {
        "query":         query,
        "safety":        safety,
        "orchestration": routing,
        "uncertainty":   uncertainty,
        "debate":        debate,
        "critique":      critique,
        "final":         final_r,
        "bias":          bias,
        "scores":        scores,
        "consensus":     consensus,
        "memory_note":   memory_note,
        "similar":       similar,
        "latency_ms":    latency,
        "version":       "5.0",
    }
    if run_baseline_flag and isinstance(baseline_result, dict):
        response["baseline"] = baseline_result

    try:
        save_decision(response)
    except Exception:
        pass

    return response


# ─── EVAL PIPELINE ───────────────────────────────────────────────────

async def eval_pipeline(
    query: str,
    domain: str = "general",
    debate_mode: str = "sequential",
    debate_rounds: int = 2,
) -> dict:
    t0 = time.time()
    domain_hint = DOMAIN_PROMPTS.get(domain, "")

    safety = await run(safety_agent, query)
    if not safety.get("safe", True):
        return {"blocked": True, "safety": safety,
                "final": {"verdict": "blocked", "reasoning": safety.get("reason", "")}}

    routing = await run(orchestrator, query)
    use_tools = routing.get("run_tools", False)

    if debate_mode == "sequential":
        debate = await run_sequential_debate(query, use_tools, domain_hint, debate_rounds)
    else:
        debate = await run_parallel_debate(query, use_tools, domain_hint)

    pro_final = debate["pro_final"]
    con_final = debate["con_final"]

    critique = await run(critic_agent, pro_final, con_final, query)
    final_r  = await run(final_agent, query, pro_final, con_final, critique)

    return {
        "query":      query,
        "debate":     debate,
        "critique":   critique,
        "final":      final_r,
        "latency_ms": round((time.time() - t0) * 1000, 1),
        "version":    "5.0",
    }


# ─── ROUTES ──────────────────────────────────────────────────────────

@app.get("/")
def home():
    return FileResponse(os.path.join(frontend_path, "index.html"))


@app.post("/analyze")
async def analyze(q: Query, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    allowed, retry_after = rate_limiter.check(client_ip)
    if not allowed:
        return JSONResponse(
            status_code=429,
            content={
                "error": "rate_limited",
                "message": f"Too many requests. Try again in {retry_after}s.",
                "retry_after": retry_after,
            },
            headers={"Retry-After": str(retry_after)},
        )

    return await full_pipeline(
        q.text, q.domain, q.context or "", q.run_baseline,
        q.debate_mode, q.debate_rounds,
    )


@app.get("/history")
async def history(limit: int = 100):
    try:
        return get_all_decisions(limit)
    except Exception as e:
        raise HTTPException(500, str(e))


@app.get("/history/{decision_id}")
async def history_item(decision_id: int):
    item = get_decision_by_id(decision_id)
    if not item:
        raise HTTPException(404, "Not found")
    return item


@app.get("/logs")
async def logs(limit: int = 50):
    return get_logs(limit)


# ─── ADMIN / OBSERVABILITY ───────────────────────────────────────────

@app.get("/admin")
async def admin_dashboard():
    """Live observability dashboard."""
    return FileResponse(os.path.join(frontend_path, "admin.html"))


@app.get("/admin/stats")
async def admin_stats():
    """Public read-only observability endpoint. Aggregated stats only —
    no individual queries, no PII."""
    return {
        "version":      "5.0",
        "cache":        llm_cache.stats(),
        "rate_limiter": rate_limiter.stats(),
        "cost":         cost_tracker.stats(),
    }


@app.get("/admin/health")
async def admin_health():
    return {"status": "ok", "version": "5.0"}