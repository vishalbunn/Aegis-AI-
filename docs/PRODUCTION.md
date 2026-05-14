# Production Engineering Notes

This document describes the production-grade infrastructure built on top of
Aegis's research pipeline. The research piece — sequential vs parallel debate —
is documented in the main [README](../README.md). This doc covers the
**operational layer**: how Aegis is built to actually run, not just to demo.

## Architecture

```
Browser (UI)                           Browser (Dashboard)
     |                                        |
     | POST /analyze                          | GET /admin/stats (every 5s)
     v                                        v
+---------------------------------------------------------+
| FastAPI (uvicorn, port 8000)                            |
|  - Rate limiter (per-IP, sliding window)                |
|  - /analyze   -> full pipeline                          |
|  - /admin     -> dashboard HTML                         |
|  - /admin/stats -> JSON: cache, rate-limit, cost        |
|  - /admin/health -> liveness check (Docker healthcheck) |
+---------------------------------------------------------+
     |
     v
+---------------------------------------------------------+
| Agent pipeline                                          |
|  Safety -> Orchestrator -> Debate (parallel|sequential) |
|         -> Critic -> Final -> Bias / Scoring / Consensus|
+---------------------------------------------------------+
     |
     v
+---------------------------------------------------------+
| Model layer (backend/agents/model.py)                   |
|  - LRU cache (1hr TTL, 1000 entries)                    |
|  - Cost tracker (per-model token + USD)                 |
|  - Strict mode (raise on failure, for eval honesty)     |
+---------------------------------------------------------+
     |
     v
   Groq API
```

## Production features

### 1. LRU cache for LLM calls
File: `backend/cache.py`

- Same `(model, prompt, temperature)` returns cached response for 1 hour
- LRU eviction at 1000 entries
- Only caches low-temperature (<=0.5) calls — high-temp calls want fresh sampling
- Thread-safe (uvicorn workers may share process)
- Stats exposed at `/admin/stats`

**Why:** demo traffic frequently re-runs the same example queries. Caching cuts
~80% of API calls without harming response quality on stable prompts.

### 2. Per-IP rate limiting
File: `backend/rate_limiter.py`

- Sliding-window: 10 requests per 10 minutes per IP (configurable)
- In-memory; swap to Redis for multi-worker deployments
- Returns `429 Retry-After: N` with friendly JSON error
- Stats exposed at `/admin/stats`

**Why:** a single user (or bot scraping the demo) can otherwise burn through
the free-tier daily budget in minutes, taking the demo offline.

### 3. Cost & token tracking
File: `backend/agents/model.py` (`CostTracker` class)

- Per-call recording of input tokens, output tokens, USD cost
- Aggregated per-model
- Uses Groq published pricing
- Stats exposed at `/admin/stats`

### 4. Observability dashboard
File: `frontend/admin.html`

- Single-page, auto-refreshing every 5s
- Charts via Chart.js (CDN)
- No build step, no npm dependencies
- Lives at `/admin`

### 5. Docker
Files: `Dockerfile`, `docker-compose.yml`, `.dockerignore`

- Multi-stage build (~200MB final image)
- Non-root user (`aegis`, uid 1000) for security
- Built-in healthcheck on `/admin/health`
- Persistent volume for memory file

```bash
docker-compose up
```

### 6. CI / tests
Files: `tests/`, `.github/workflows/tests.yml`

- 46 unit + integration tests
- Covers metrics, safety regex, benchmark integrity, cache, rate limiter, API routes
- Runs on every push via GitHub Actions
- ~5 seconds runtime

```bash
pytest
```

## Performance

Measured on Groq free tier (Llama-3.1-8B for both debater and judge):

| Scenario | Mode | Avg latency | LLM calls per query |
|---|---|---|---|
| First query (cold cache) | Parallel | 30-60s | 5 |
| First query (cold cache) | Sequential (2 rounds) | 70-120s | 8 |
| Repeat query (warm cache) | Either | <1s | 0 |
| Eval pipeline (no UI agents) | Parallel | 5-15s | 4 |
| Eval pipeline (no UI agents) | Sequential (2 rounds) | 60-90s | 6 |

## Cost analysis

Pricing per 1M tokens (Groq on-demand):

| Model | Input | Output |
|---|---|---|
| `llama-3.1-8b-instant` | $0.05 | $0.08 |
| `llama-3.3-70b-versatile` | $0.59 | $0.79 |

Estimated cost per query (sequential, 2 rounds, all 8B):
- ~5,000 input tokens, ~3,000 output tokens
- = $0.00025 + $0.00024 = **~$0.0005 per query**
- = **~$0.50 per 1000 queries**

A full 30-query benchmark eval (×2 modes) consumes roughly **$0.06**.

## Failure modes observed & how each is handled

| Failure | Symptom | Handling |
|---|---|---|
| API key invalid | 401 Unauthorized | Loud error at startup (`model.py` raises) |
| Daily token cap hit | 429 rate_limit_exceeded | Eval pauses 30s, retries once |
| Cloudflare IP block | 403 Access denied | Manual: switch network or wait |
| Empty model response | Empty string returned | Strict mode raises; lenient returns error string |
| JSON parse failure | Malformed LLM output | Fallback to `{verdict: "conditional", confidence: 50}` |
| Safety over-block (v5.0 bug) | Risky personal decisions blocked | v5.1: prompt teaches risky vs harmful distinction |
| One bad query in eval | One row marked error | Eval continues; report shows partial results honestly |

## Deployment

### Local development
```bash
git clone https://github.com/vishalbunn/Aegis-AI-
cd Aegis-AI-
pip install -r requirements.txt
cp .env.example .env  # add GROQ_API_KEY
uvicorn backend.main:app --reload
```

### Docker (recommended)
```bash
docker-compose up
```

### Vercel (live demo)
The frontend is deployable to Vercel; the FastAPI backend is wrapped via
`api/index.py`. Set `GROQ_API_KEY` in Vercel environment variables.

## Known limitations

1. **Single-model in current eval.** Both debater and judge run Llama-3.1-8B due
   to free-tier daily token limits on the 70B model. The canonical setup
   (8B debater + 70B judge) requires either paid Groq tier or splitting eval
   runs across days.
2. **In-memory cache and rate limiter** don't survive container restarts.
   For multi-instance production deployment, swap to Redis.
3. **Inter-rater labels not yet collected.** The `reference_lean` field on
   the benchmark is the author's expert lean, not multi-rater ground truth.
4. **No structured logging** — using `print()` and FastAPI access logs.
   Production would want JSON-structured logs and a log aggregator.

## Future work

- Cross-model validation (gpt-4o-mini, Claude Haiku) to confirm the
  sequential-debate finding isn't model-specific
- Rounds ablation: rounds=1,2,3,4 to find optimal debate depth
- Inter-rater labels on the benchmark (Cohen's kappa)
- Redis-backed cache & rate limiter for multi-worker deployments
- Structured logging + Prometheus metrics export