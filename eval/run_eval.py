"""
Aegis Eval Harness v1 (lean + strict + retry + cloudflare-friendly pacing)

Sets AEGIS_STRICT=1, paces queries to respect Groq free-tier rate limits AND
avoid Cloudflare IP blocking, and retries once on 429 errors.
"""
import os
os.environ["AEGIS_STRICT"] = "1"

import sys
import json
import time
import asyncio
import argparse
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from eval.benchmark import BENCHMARK
from backend.main import eval_pipeline


# ─── METRICS ──────────────────────────────────────────────────────────

def tfidf_distance(a: str, b: str) -> float:
    if not a or not a.strip() or not b or not b.strip():
        return 0.0
    try:
        vec = TfidfVectorizer(stop_words="english", min_df=1).fit_transform([a, b])
        sim = cosine_similarity(vec[0], vec[1])[0][0]
        return float(1 - sim)
    except Exception:
        return 0.0


def argument_diversity(pro_final: str, con_final: str) -> float:
    return tfidf_distance(pro_final, con_final)


def stance_drift(rounds: list) -> float:
    if not rounds or len(rounds) < 2:
        return 0.0
    return tfidf_distance(rounds[0], rounds[-1])


def verdict_match(predicted: str, reference: str) -> bool:
    p = (predicted or "").lower().strip()
    r = (reference or "").lower().strip()
    if r == "conditional":
        return p in {"yes", "no", "conditional"}
    return p == r


# ─── RUN ──────────────────────────────────────────────────────────────

async def run_one(query_obj: dict, mode: str, rounds: int = 2) -> dict:
    t0 = time.time()
    last_err = None

    # Try up to 2 times. On 429, sleep 30s and retry once.
    for attempt in range(2):
        try:
            result = await eval_pipeline(
                query=query_obj["query"],
                domain=query_obj["domain"],
                debate_mode=mode,
                debate_rounds=rounds,
            )
            break
        except Exception as e:
            last_err = str(e)
            if "429" in last_err and attempt == 0:
                print(f"    rate limit hit, sleeping 30s and retrying...", flush=True)
                await asyncio.sleep(30)
                continue
            return {
                "id": query_obj["id"],
                "mode": mode,
                "error": last_err[:300],
                "elapsed": round(time.time() - t0, 2),
            }
    else:
        return {
            "id": query_obj["id"],
            "mode": mode,
            "error": last_err[:300] if last_err else "unknown",
            "elapsed": round(time.time() - t0, 2),
        }

    elapsed = time.time() - t0

    if result.get("blocked"):
        return {"id": query_obj["id"], "mode": mode, "blocked": True, "elapsed": elapsed}

    debate = result.get("debate", {})
    pro_final = debate.get("pro_final", "") or ""
    con_final = debate.get("con_final", "") or ""
    pro_rounds = debate.get("pro_rounds", []) or []
    con_rounds = debate.get("con_rounds", []) or []
    final = result.get("final") or {}
    verdict = (final.get("verdict") or "").lower()
    confidence = final.get("confidence", 0)

    return {
        "id":           query_obj["id"],
        "query":        query_obj["query"],
        "domain":       query_obj["domain"],
        "difficulty":   query_obj["difficulty"],
        "reference":    query_obj["reference_lean"],
        "trap":         query_obj.get("trap"),
        "mode":         mode,
        "rounds":       rounds,
        "elapsed":      round(elapsed, 2),
        "verdict":      verdict,
        "confidence":   confidence,
        "verdict_match": verdict_match(verdict, query_obj["reference_lean"]),
        "diversity":    round(argument_diversity(pro_final, con_final), 4),
        "pro_drift":    round(stance_drift(pro_rounds), 4),
        "con_drift":    round(stance_drift(con_rounds), 4),
    }


async def run_benchmark(mode: str, rounds: int, limit: int = None,
                        fail_threshold: int = 5, sleep_between: float = 8.0) -> list:
    """Stops early if `fail_threshold` consecutive failures occur.
    Sleeps `sleep_between` seconds between queries to respect rate limits AND
    avoid Cloudflare IP-level abuse blocks."""
    queries = BENCHMARK[:limit] if limit else BENCHMARK
    results = []
    consecutive_fails = 0
    for i, q in enumerate(queries, 1):
        print(f"  [{mode:10}] {i}/{len(queries)}  {q['id']:12}  {q['query'][:60]}...", end="", flush=True)
        r = await run_one(q, mode, rounds)
        if r.get("error"):
            consecutive_fails += 1
            print(f"  FAIL: {r['error'][:80]}")
        elif r.get("blocked"):
            consecutive_fails = 0
            print(f"  BLOCKED by safety")
        else:
            consecutive_fails = 0
            print(f"  ok ({r.get('elapsed', '?')}s, verdict={r.get('verdict')})")
        results.append(r)

        if consecutive_fails >= fail_threshold:
            print(f"\n  STOPPING: {fail_threshold} consecutive failures.")
            break

        # Pace ourselves between queries (cloudflare-friendly).
        await asyncio.sleep(sleep_between)
    return results


# ─── AGGREGATION ──────────────────────────────────────────────────────

def aggregate(results: list, mode: str) -> dict:
    rows = [r for r in results if r.get("mode") == mode and "verdict" in r and not r.get("error")]
    if not rows:
        return {"mode": mode, "n": 0}

    n = len(rows)
    avg = lambda key: round(sum(r.get(key, 0) for r in rows) / n, 4)
    pct = lambda key: round(100 * sum(1 for r in rows if r.get(key)) / n, 1)

    traps = [r for r in rows if r.get("trap")]
    trap_resistance = round(100 * sum(1 for r in traps if r["verdict_match"]) / len(traps), 1) if traps else 0

    return {
        "mode":             mode,
        "n":                n,
        "avg_diversity":    avg("diversity"),
        "avg_pro_drift":    avg("pro_drift"),
        "avg_con_drift":    avg("con_drift"),
        "verdict_alignment": pct("verdict_match"),
        "trap_resistance":  trap_resistance,
        "avg_latency_s":    avg("elapsed"),
        "avg_confidence":   avg("confidence"),
    }


def write_markdown(parallel_agg: dict, sequential_agg: dict, all_results: list, path: Path):
    lines = [
        "# Aegis AI v5 - Eval Results",
        f"Generated: {datetime.now().isoformat(timespec='seconds')}",
        f"Benchmark: {len(BENCHMARK)} queries",
        "",
        f"Successful runs: parallel={parallel_agg.get('n', 0)}, sequential={sequential_agg.get('n', 0)}",
        "",
        "## Headline metrics",
        "",
        "| Metric | Parallel (v4) | Sequential (v5) | Delta |",
        "|---|---|---|---|",
    ]

    keys = [
        ("avg_diversity",     "Argument diversity (Pro vs Con)"),
        ("avg_pro_drift",     "Pro-side stance drift R1->Rn"),
        ("avg_con_drift",     "Con-side stance drift R1->Rn"),
        ("verdict_alignment", "Verdict alignment with reference (%)"),
        ("trap_resistance",   "Trap-case resistance (%)"),
        ("avg_latency_s",     "Avg latency (s)"),
        ("avg_confidence",    "Avg confidence"),
    ]
    for key, label in keys:
        p = parallel_agg.get(key, 0)
        s = sequential_agg.get(key, 0)
        if isinstance(p, (int, float)) and isinstance(s, (int, float)):
            delta = round(s - p, 4)
            lines.append(f"| {label} | {p} | {s} | {delta:+} |")
        else:
            lines.append(f"| {label} | {p} | {s} | - |")

    errs = [r for r in all_results if r.get("error") or r.get("blocked")]
    if errs:
        lines += ["", f"## Errors / blocks: {len(errs)}", ""]
        for e in errs[:15]:
            reason = e.get("error") or "blocked"
            lines.append(f"- `{e.get('id')}` [{e.get('mode')}]: {reason[:200]}")

    lines += ["", "## Per-query results", "",
              "| ID | Domain | Diff | Ref | P verdict | S verdict | P-div | S-div | P-conf | S-conf |",
              "|---|---|---|---|---|---|---|---|---|---|"]

    by_id = {}
    for r in all_results:
        if "verdict" in r and not r.get("error"):
            by_id.setdefault(r["id"], {})[r["mode"]] = r

    for q in BENCHMARK:
        p = by_id.get(q["id"], {}).get("parallel", {})
        s = by_id.get(q["id"], {}).get("sequential", {})
        lines.append(
            f"| {q['id']} | {q['domain']} | {q['difficulty']} | {q['reference_lean']} | "
            f"{p.get('verdict', '-')} | {s.get('verdict', '-')} | "
            f"{p.get('diversity', '-')} | {s.get('diversity', '-')} | "
            f"{p.get('confidence', '-')} | {s.get('confidence', '-')} |"
        )

    path.write_text("\n".join(lines), encoding="utf-8")


# ─── MAIN ─────────────────────────────────────────────────────────────

async def main(limit: int = None, rounds: int = 2, sleep_between: float = 8.0):
    n = len(BENCHMARK[:limit] if limit else BENCHMARK)
    print(f"\nAegis Eval (lean + strict + retry) - benchmark ({n} queries x 2 modes)")
    print(f"Pacing: {sleep_between}s between queries, 30s retry on 429.\n")

    print("[1/2] PARALLEL mode")
    parallel = await run_benchmark("parallel", rounds=1, limit=limit, sleep_between=sleep_between)

    print("\n[2/2] SEQUENTIAL mode")
    sequential = await run_benchmark("sequential", rounds=rounds, limit=limit, sleep_between=sleep_between)

    all_results = parallel + sequential

    parallel_agg = aggregate(all_results, "parallel")
    sequential_agg = aggregate(all_results, "sequential")

    out_dir = Path(__file__).resolve().parent
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = out_dir / f"results_{ts}.json"
    md_path   = out_dir / f"results_{ts}.md"

    json_path.write_text(json.dumps({
        "timestamp": ts,
        "parallel_aggregate": parallel_agg,
        "sequential_aggregate": sequential_agg,
        "results": all_results,
    }, indent=2), encoding="utf-8")

    write_markdown(parallel_agg, sequential_agg, all_results, md_path)

    n_par = parallel_agg.get("n", 0)
    n_seq = sequential_agg.get("n", 0)

    print(f"\nResults: {md_path}")
    print(f"Raw:     {json_path}")
    print("\nHeadline:")
    print(f"  Successful runs:  {n_par} parallel / {n_seq} sequential")
    if n_par == 0 and n_seq == 0:
        print("\n  WARNING: zero successful runs.")
        return
    print(f"  Diversity:        {parallel_agg.get('avg_diversity')} -> {sequential_agg.get('avg_diversity')}")
    print(f"  Pro drift:        {parallel_agg.get('avg_pro_drift')} -> {sequential_agg.get('avg_pro_drift')}")
    print(f"  Con drift:        {parallel_agg.get('avg_con_drift')} -> {sequential_agg.get('avg_con_drift')}")
    print(f"  Verdict align:    {parallel_agg.get('verdict_alignment')}% -> {sequential_agg.get('verdict_alignment')}%")
    print(f"  Trap resistance:  {parallel_agg.get('trap_resistance')}% -> {sequential_agg.get('trap_resistance')}%")


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--limit", type=int, default=None, help="Run only first N queries")
    p.add_argument("--rounds", type=int, default=2, help="Sequential debate rounds")
    p.add_argument("--sleep", type=float, default=8.0, help="Seconds between queries (default 8)")
    args = p.parse_args()
    asyncio.run(main(args.limit, args.rounds, args.sleep))