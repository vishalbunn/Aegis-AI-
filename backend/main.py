import sys, os, asyncio, time
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional

from agents.pro_agent         import pro_agent
from agents.con_agent         import con_agent
from agents.critic_agent      import critic_agent
from agents.final_agent       import final_agent
from agents.relevance_agent   import relevance_agent
from agents.scoring_agent     import scoring_agent
from agents.uncertainty_agent import uncertainty_agent
from agents.bias_agent        import bias_agent
from agents.consensus_agent   import consensus_agent
from agents.baseline_agent    import baseline_agent
from agents.safety_agent      import safety_agent
from agents.orchestrator      import orchestrator

from database   import init_db, save_decision, get_all_decisions, get_decision_by_id, get_all_raw
from logger     import log_request, get_logs
from similarity import find_similar, detect_changed

app = FastAPI(title="Aegis AI", version="4.1")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])

DOMAIN_PROMPTS = {
    "healthcare": "Focus on medical feasibility, patient safety, evidence-based outcomes, and ethics.",
    "business":   "Focus on ROI, market viability, competitive landscape, and financial risk.",
    "career":     "Focus on long-term growth, skill development, financial stability, and work-life balance.",
    "tech":       "Focus on technical feasibility, scalability, maintainability, and ecosystem maturity.",
    "general":    "",
}

@app.on_event("startup")
async def startup():
    init_db()
    print("🚀 Aegis AI v4.1 — all agents loaded")

class Query(BaseModel):
    text: str
    domain: str = "general"
    context: Optional[str] = None
    run_baseline: bool = True

class CompareQuery(BaseModel):
    text_a: str
    text_b: str
    domain: str = "general"

async def run(func, *args, **kwargs):
    return await asyncio.to_thread(func, *args, **kwargs)

async def full_pipeline(query: str, domain: str = "general",
                        context: str = "", run_baseline_flag: bool = True) -> dict:
    t0 = time.time()
    domain_hint = DOMAIN_PROMPTS.get(domain, "")
    full_query = f"{context}\n\nCurrent query: {query}".strip() if context else query

    # ── 0: Safety gate ──────────────────────────────
    safety = await run(safety_agent, full_query)
    if not safety.get("safe", True):
        return {
            "blocked": True, "safety": safety, "query": query, "domain": domain,
            "pro": "", "con": "", "critique": "", "final": safety.get("reason", "Query blocked."),
            "scores": {}, "uncertainty": {}, "bias": {}, "consensus": {},
            "similar": [], "memory_note": "", "rounds": 0, "search_used": False,
            "complexity": "blocked", "latency_ms": 0, "meta": {"id": None, "created_at": None},
            "orchestration": {}, "comparison": None,
        }

    # ── 1: Routing + uncertainty + history (parallel) ─
    routing, uncertainty, similar_raw = await asyncio.gather(
        run(orchestrator, full_query),
        run(uncertainty_agent, full_query),
        asyncio.to_thread(get_all_raw),
    )
    similar     = find_similar(query, similar_raw)
    memory_note = detect_changed(query, similar)
    use_tools   = routing.get("run_tools", False)
    run_bias    = routing.get("run_bias", True)
    max_rounds  = routing.get("run_consensus_rounds", 2)
    complexity  = routing.get("complexity", "moderate")

    # ── 2: Debate round (pro + con + baseline in parallel) ─
    baseline_coro = run(baseline_agent, query) if run_baseline_flag else asyncio.sleep(0)
    pros, cons, baseline_result = await asyncio.gather(
        run(pro_agent,  full_query, use_tools, domain_hint),
        run(con_agent,  full_query, use_tools, domain_hint),
        baseline_coro,
    )
    if not run_baseline_flag:
        baseline_result = None

    # ── 3: Refine (critic + optional bias) ──────────
    refine_tasks = [run(critic_agent, pros, cons, query)]
    if run_bias:
        refine_tasks.append(run(bias_agent, pros, cons, query))
    refine_results = await asyncio.gather(*refine_tasks)
    critique = refine_results[0]
    bias     = refine_results[1] if run_bias else {
        "pro_bias": "skipped", "con_bias": "skipped",
        "overall_bias": "balanced", "severity": "low", "flags": []
    }

    # ── 4: Final answer ──────────────────────────────
    final_r = await run(final_agent, full_query, pros, cons, critique)
    relevance = await run(relevance_agent, query, final_r)
    if "NO" in relevance.upper():
        final_r = "⚠️ Response went off-topic. Please try rephrasing your query."

    # ── 5: Consensus rounds ──────────────────────────
    consensus_r = None
    rounds_done = 0
    for rnd in range(1, max_rounds + 1):
        prev = consensus_r.get("consensus", final_r) if consensus_r else final_r
        consensus_r = await run(consensus_agent, query, pros, cons, critique, prev, round_num=rnd)
        rounds_done = rnd
        if consensus_r.get("stability", 0) >= 88:
            break

    final_answer = (consensus_r or {}).get("consensus") or final_r

    # ── 6: Scoring ───────────────────────────────────
    scores = await run(scoring_agent, query, final_answer, pros, cons)

    # ── 7: Persist ───────────────────────────────────
    meta = save_decision(
        query=query, pro=pros, con=cons, critique=critique,
        final=final_answer, scores=scores, uncertainty=uncertainty,
        bias=bias, consensus=consensus_r, domain=domain,
    )

    latency = round((time.time() - t0) * 1000, 1)

    # ── 8: Baseline comparison ───────────────────────
    comparison = None
    if baseline_result and isinstance(baseline_result, dict):
        aegis_wc = len((pros + cons + critique + final_answer).split())
        b_wc = baseline_result.get("word_count", 1)
        comparison = {
            "baseline": baseline_result,
            "aegis_word_count": aegis_wc,
            "baseline_word_count": b_wc,
            "aegis_has_bias_check": True,
            "aegis_has_uncertainty": True,
            "aegis_has_scoring": True,
            "aegis_has_multi_agent": True,
            "aegis_agent_count": 9 if run_bias else 7,
            "depth_advantage": round(aegis_wc / max(b_wc, 1), 2),
        }

    result = {
        "query": query, "domain": domain, "blocked": False,
        "safety": safety, "orchestration": routing,
        "pro": pros, "con": cons, "critique": critique, "final": final_answer,
        "scores": scores, "uncertainty": uncertainty, "bias": bias,
        "consensus": consensus_r or {}, "similar": similar,
        "memory_note": memory_note, "rounds": rounds_done,
        "search_used": use_tools, "complexity": complexity,
        "latency_ms": latency,
        "meta": meta,          # ← always a dict with id + created_at
        "comparison": comparison,
    }

    log_request(query, result, latency)
    return result


@app.get("/")
def home():
    return FileResponse(os.path.join(os.path.dirname(__file__), "../frontend/index.html"))

@app.post("/analyze")
async def analyze(q: Query):
    return await full_pipeline(q.text, q.domain, q.context or "", q.run_baseline)

@app.post("/compare")
async def compare(q: CompareQuery):
    a, b = await asyncio.gather(
        full_pipeline(q.text_a, q.domain, run_baseline_flag=False),
        full_pipeline(q.text_b, q.domain, run_baseline_flag=False),
    )
    return {"a": a, "b": b}

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

@app.get("/share/{decision_id}")
async def share_item(decision_id: int):
    item = get_decision_by_id(decision_id)
    if not item:
        raise HTTPException(404, "Not found")
    return item

@app.get("/logs")
async def logs(limit: int = 50):
    return get_logs(limit)

@app.get("/stats")
async def stats():
    all_d = get_all_decisions(1000)
    keys = ["feasibility", "risk", "confidence", "impact", "cost", "overall"]
    avg = {}
    for k in keys:
        vals = [d[k] for d in all_d if d.get(k) is not None]
        avg[k] = round(sum(vals) / len(vals), 1) if vals else None
    domains, complexity_dist = {}, {}
    for d in all_d:
        dom = d.get("domain", "general")
        domains[dom] = domains.get(dom, 0) + 1
        c = (d.get("orchestration") or {}).get("complexity", "unknown")
        complexity_dist[c] = complexity_dist.get(c, 0) + 1
    return {
        "total_decisions": len(all_d),
        "avg_scores": avg,
        "by_domain": domains,
        "by_complexity": complexity_dist,
    }

app.mount("/frontend", StaticFiles(
    directory=os.path.join(os.path.dirname(__file__), "../frontend")), name="frontend")