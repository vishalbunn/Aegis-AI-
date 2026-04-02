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

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"]
)

# ✅ Fix: frontend path
frontend_path = os.path.join(os.path.dirname(__file__), "../frontend")

app.mount(
    "/static",
    StaticFiles(directory=frontend_path),
    name="static"
)

DOMAIN_PROMPTS = {
    "healthcare": "Focus on medical feasibility, patient safety, evidence-based outcomes, and ethics.",
    "business":   "Focus on ROI, market viability, competitive landscape, and financial risk.",
    "career":     "Focus on long-term growth, skill development, financial stability, and work-life balance.",
    "tech":       "Focus on technical feasibility, scalability, maintainability, and ecosystem maturity.",
    "general":    "",
}

# ✅ Fix: safe startup (prevents Vercel crash)
@app.on_event("startup")
async def startup():
    try:
        init_db()
        print("🚀 Aegis AI v4.1 — DB initialized")
    except Exception as e:
        print("⚠️ DB init skipped (Vercel environment):", str(e))

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

# ================= PIPELINE =================
async def full_pipeline(query: str, domain: str = "general",
                        context: str = "", run_baseline_flag: bool = True) -> dict:
    t0 = time.time()
    domain_hint = DOMAIN_PROMPTS.get(domain, "")
    full_query = f"{context}\n\nCurrent query: {query}".strip() if context else query

    # Safety
    safety = await run(safety_agent, full_query)
    if not safety.get("safe", True):
        return {"blocked": True, "final": safety.get("reason", "Query blocked.")}

    routing, uncertainty, similar_raw = await asyncio.gather(
        run(orchestrator, full_query),
        run(uncertainty_agent, full_query),
        asyncio.to_thread(get_all_raw),
    )

    similar = find_similar(query, similar_raw)
    memory_note = detect_changed(query, similar)

    use_tools = routing.get("run_tools", False)

    baseline_coro = run(baseline_agent, query) if run_baseline_flag else asyncio.sleep(0)

    pros, cons, baseline_result = await asyncio.gather(
        run(pro_agent, full_query, use_tools, domain_hint),
        run(con_agent, full_query, use_tools, domain_hint),
        baseline_coro,
    )

    critique = await run(critic_agent, pros, cons, query)
    final_r = await run(final_agent, full_query, pros, cons, critique)

    scores = await run(scoring_agent, query, final_r, pros, cons)

    latency = round((time.time() - t0) * 1000, 1)

    return {
        "query": query,
        "pro": pros,
        "con": cons,
        "critique": critique,
        "final": final_r,
        "scores": scores,
        "latency_ms": latency,
    }

# ================= ROUTES =================

# ✅ Serve frontend
@app.get("/")
def home():
    return FileResponse(os.path.join(frontend_path, "index.html"))

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

@app.get("/logs")
async def logs(limit: int = 50):
    return get_logs(limit)
