# Aegis AI

A multi-agent decision-support system that tests whether **sequential debate**
between LLM agents produces measurably better deliberation than **parallel
monologue** — the standard pattern in most multi-agent demos.

---

## The question

Most "multi-agent" LLM systems run their agents in parallel: a Pro agent and a
Con agent both write arguments without ever seeing each other's reasoning. The
"debate" exists in the user's head when they read the output side-by-side.

The multi-agent debate (MAD) literature [1, 2] suggests this misses most of the
value — that *iterative, adversarial refinement* is what improves reasoning,
not parallel argument generation. But a recent finding [3] also shows that
LLM agents have a strong "funneling effect" toward premature consensus, even on
contentious topics.

**Aegis tests both claims on a benchmark of 30 real-world decisions.**

## Hypotheses

1. **H1 — Diversity:** Sequential debate yields more semantically distinct
   Pro/Con final arguments than parallel debate.
2. **H2 — Drift:** In sequential mode, agents meaningfully update their
   stance between round 1 and round N (rather than restating the same points).
3. **H3 — Alignment:** Sequential debate produces verdicts that align better
   with reasonable expert lean, especially on cases designed to elicit
   cognitive biases (sunk cost, anchoring, social proof, etc.).

## Method

- **Benchmark:** 30 hand-crafted decision queries spanning career, business,
  tech, healthcare, and personal life. 5 of these are "trap" cases that probe
  bias resistance (e.g. "I've already invested $80k in my idea — should I keep
  going?").
- **Conditions:**
  - `parallel` — Pro and Con run once, never see each other (baseline).
  - `sequential` — Pro and Con each run for N rounds; in rounds 2+ each side
    receives the opponent's previous-round argument and is instructed to
    rebut, strengthen, and add new points.
- **Models:** Llama-3.1-8B (debaters) and Llama-3.3-70B (judge), via Groq.
  The weaker-debater + stronger-judge split is standard in the MAD literature.
- **Metrics:**
  - *Argument diversity:* `1 − cos(TF-IDF(pro_final), TF-IDF(con_final))`
  - *Stance drift:* `1 − cos(TF-IDF(round_1), TF-IDF(round_N))` per side
  - *Verdict alignment:* fraction of cases where the verdict matches the
    benchmark `reference_lean`
  - *Trap resistance:* alignment on the 5 bias-trap cases

Results live in `eval/results_<timestamp>.md`.

## Architecture

```
                           ┌─ safety gate (regex + classifier)
User query ────────────────┤
                           ├─ orchestrator (complexity routing)
                           └─ uncertainty check

                                    │
                                    ▼
                       ┌──── DEBATE LOOP ────┐
                       │                     │
       Round 1   Pro ──┤  ── Con (parallel)  │
                       │                     │
       Round 2   Pro ←─┤── sees Con R1 ──────┤── Con sees Pro R1
                       │                     │
                       └──── final round ────┘
                                    │
                                    ▼
                            Critic (Llama 70B)
                                    │
                                    ▼
                       Final verdict + Bias audit + Scoring
                                    │
                                    ▼
                            Consensus stabilizer
```

## Running it

```bash
git clone https://github.com/vishalbunn/Aegis-AI-
cd Aegis-AI-
pip install -r requirements.txt

cp .env.example .env
# Add GROQ_API_KEY (free at console.groq.com)

# Serve the UI
uvicorn backend.main:app --reload

# Run the eval
python -m eval.run_eval --limit 5      # quick smoke test (5 queries)
python -m eval.run_eval                # full benchmark (30 queries × 2 modes)
```

## Results

See `eval/results_<latest>.md` after running the harness. The headline
table reports per-mode metrics and per-query verdicts. Key findings will
be summarized here once the eval has been run.

## What's actually here vs. what's not

**Built and working:**
- Two-mode debate pipeline (parallel + sequential)
- Bias / safety / orchestration / scoring agents — all wired in
- 30-query benchmark with 5 bias-trap cases
- Eval harness that produces JSON + Markdown reports
- Web UI for interactive use

**Not built (honest list):**
- No human-rated ground truth — the `reference_lean` is consensus expert
  lean, not verified outcomes. A real calibration study needs labeled
  outcomes (planned future work).
- Single model family (Llama via Groq). Cross-model robustness untested.
- Memory is JSON + Jaccard similarity. Fine for demos, not production.

## References

1. Du et al. 2023. *Improving Factuality and Reasoning in Language Models
   through Multiagent Debate.* arXiv:2305.14325
2. Liang et al. 2023. *Encouraging Divergent Thinking in LLMs through
   Multi-Agent Debate.* arXiv:2305.19118
3. *The Social Laboratory: A Psychometric Framework for Multi-Agent LLM
   Evaluation.* 2025. arXiv:2510.01295
4. Wang et al. 2025. *Silence is Not Consensus: Disrupting Agreement Bias
   in Multi-Agent LLMs via Catfish Agent for Clinical Decision Making.*
   arXiv:2505.21503

---

Built as a research project on multi-agent deliberation.
MIT License.