# 🧠 Aegis AI — Multi-Agent Decision Intelligence System

<div align="center">

![Aegis AI](https://img.shields.io/badge/Aegis_AI-v4.0-black?style=for-the-badge)
![Python](https://img.shields.io/badge/Python-3.10+-blue?style=for-the-badge&logo=python)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green?style=for-the-badge&logo=fastapi)
![Groq](https://img.shields.io/badge/Groq-LLaMA_3.1-orange?style=for-the-badge)
![License](https://img.shields.io/badge/License-MIT-yellow?style=for-the-badge)

**A research-grade deliberative multi-agent AI system for complex decision analysis.**

[Live Demo](https://your-vercel-url.vercel.app) · [Report Bug](https://github.com/YOUR_USERNAME/aegis-ai/issues) · [Request Feature](https://github.com/YOUR_USERNAME/aegis-ai/issues)

</div>

---

## 📌 What is Aegis AI?

Aegis AI is a **deliberative multi-agent system** that goes beyond single-LLM responses. Instead of asking one model to reason about a decision, Aegis orchestrates **9 specialized AI agents** that debate, critique, detect bias, reach consensus, and produce structured verdicts — all backed by real-time web search.

> Unlike standard LLM chatbots, Aegis agents have distinct roles, call external tools, and run multiple reasoning rounds before converging on an answer.

---

## 🏗️ System Architecture

```
User Query
    │
    ▼
┌─────────────────────────────────────────┐
│           SAFETY LAYER                  │  ← Blocks harmful queries
└─────────────────────────────────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│           ORCHESTRATOR                  │  ← Routes by complexity
│   simple(1 round) / moderate / complex  │
└─────────────────────────────────────────┘
    │
    ├──► UNCERTAINTY AGENT  (detects ambiguity)
    ├──► WEB SEARCH TOOL    (real-world data)
    │
    ▼  ROUND 1: DEBATE
┌──────────────┐    ┌──────────────┐
│  PRO AGENT   │    │  CON AGENT   │
│ (advocates)  │    │(adversarial) │
└──────────────┘    └──────────────┘
    │                     │
    ▼  ROUND 2: REFINE
┌──────────────┐    ┌──────────────┐
│  BIAS AGENT  │    │ CRITIC AGENT │
│(bias detect) │    │ (evaluates)  │
└──────────────┘    └──────────────┘
    │
    ▼  ROUND 3: CONVERGE
┌─────────────────────────────────────────┐
│          CONSENSUS AGENT                │  ← Stabilises answer
│         (up to 3 rounds)                │
└─────────────────────────────────────────┘
    │
    ▼
┌──────────────┐    ┌──────────────┐
│ FINAL AGENT  │    │SCORING AGENT │
│  (verdict)   │    │(5 dimensions)│
└──────────────┘    └──────────────┘
    │
    ▼
┌─────────────────────────────────────────┐
│     MEMORY + LOGGER + BASELINE          │
│  JSON storage · logs · LLM comparison   │
└─────────────────────────────────────────┘
```

---

## 🤖 The 9 Agents

| Agent | Role | Type |
|-------|------|------|
| **Safety Agent** | Blocks harmful/unethical queries before any processing | Gate |
| **Orchestrator** | Scores query complexity, routes to correct agent set | Meta |
| **Uncertainty Agent** | Detects ambiguity, generates clarifying questions | Meta |
| **Pro Agent** | Builds strongest case in favor (uses web search) | Reasoning |
| **Con Agent** | Builds strongest case against (uses web search) | Reasoning |
| **Bias Agent** | Detects confirmation bias, anchoring, availability heuristic | Analysis |
| **Critic Agent** | Identifies weaknesses and missing points in both sides | Analysis |
| **Consensus Agent** | Runs 1–3 rounds to stabilize and converge the answer | Synthesis |
| **Final Agent** | Produces the final decision with confidence % | Synthesis |
| **Scoring Agent** | Quantifies feasibility, risk, confidence, impact, cost | Evaluation |
| **Baseline Agent** | Runs single-LLM call for research comparison | Research |

---

## ✨ Features

### 🔬 Research-Grade
- **Multi-round deliberation** — debate → refine → converge (not single-pass)
- **Baseline comparison** — Aegis vs plain LLM, same query, measured depth advantage
- **Structured scoring** — 5 quantitative dimensions per decision
- **Agent influence tracking** — shows which agent drove the final verdict
- **Bias detection** — identifies specific cognitive biases in reasoning
- **Uncertainty quantification** — flags ambiguous queries before analysis

### 🛠️ Production Features
- **Web search integration** — agents fetch real-world data (Tavily / DuckDuckGo fallback)
- **Dynamic orchestration** — simple queries use fewer agents, complex queries use all
- **Safety layer** — hard-blocks harmful queries, soft-checks edge cases
- **Persistent memory** — JSON-based decision storage with similarity matching
- **Full request logging** — latency, model, agent outputs per request
- **Domain modes** — Business, Career, Tech, Healthcare (custom prompts per domain)

### 🎨 Frontend
- Magazine-editorial aesthetic (Awwwards-level UI)
- Compare mode — two decisions side by side
- History tab with search, filter by verdict/domain/complexity
- Share via URL, Export PDF
- Agent influence visualization with animated bars
- Score dashboard with animated background fills

---

## 🚀 Quick Start

### Prerequisites
- Python 3.10+
- [Groq API key](https://console.groq.com) (free)
- [Tavily API key](https://tavily.com) (free, optional — DuckDuckGo fallback built in)

### Installation

```bash
# Clone the repo
git clone https://github.com/YOUR_USERNAME/aegis-ai.git
cd aegis-ai

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp .env.example .env
# Edit .env and add your keys
```

### Environment Variables

```env
GROQ_API_KEY=your_groq_key_here
TAVILY_API_KEY=your_tavily_key_here  # optional
```

### Run

```bash
uvicorn backend.main:app --reload
```

Open [http://localhost:8000](http://localhost:8000)

---

## 📁 Project Structure

```
aegis-ai/
├── backend/
│   ├── main.py                  # FastAPI app, full pipeline orchestration
│   ├── database.py              # JSON memory store
│   ├── logger.py                # Request/response logger
│   ├── similarity.py            # Jaccard similarity for memory matching
│   ├── agents/
│   │   ├── model.py             # Groq LLM client
│   │   ├── safety_agent.py      # Safety gate
│   │   ├── orchestrator.py      # Dynamic routing
│   │   ├── uncertainty_agent.py # Ambiguity detection
│   │   ├── pro_agent.py         # Advocate reasoning
│   │   ├── con_agent.py         # Adversarial reasoning
│   │   ├── bias_agent.py        # Bias detection
│   │   ├── critic_agent.py      # Critical evaluation
│   │   ├── consensus_agent.py   # Multi-round convergence
│   │   ├── final_agent.py       # Final verdict synthesis
│   │   ├── scoring_agent.py     # Quantitative scoring
│   │   └── baseline_agent.py   # Single-LLM baseline
│   └── tools/
│       └── search.py            # Tavily + DuckDuckGo search
├── frontend/
│   └── index.html               # Full SPA frontend
├── requirements.txt
├── .env.example
└── README.md
```

---

## 🔌 API Reference

### `POST /analyze`
Run full multi-agent pipeline on a decision query.

```json
{
  "text": "Should I quit my job and start a startup?",
  "domain": "career",
  "context": "I have 3 years of savings",
  "run_baseline": true
}
```

**Response includes:** `pro`, `con`, `critique`, `final`, `scores`, `bias`, `uncertainty`, `consensus`, `orchestration`, `comparison`, `meta`

### `POST /compare`
Run two decisions in parallel.

```json
{
  "text_a": "Should I buy a car?",
  "text_b": "Should I buy a bike?",
  "domain": "general"
}
```

### `GET /history`
Returns all saved decisions.

### `GET /stats`
Returns aggregate statistics across all decisions.

### `GET /share/{id}`
Returns a specific decision by ID (for shareable links).

---

## 📊 Scoring Dimensions

| Dimension | Description |
|-----------|-------------|
| **Feasibility** | How practical/achievable is this decision? |
| **Risk** | How risky is this decision? (higher = more risk) |
| **Confidence** | How confident is the system in its verdict? |
| **Impact** | What is the potential impact of this decision? |
| **Cost** | How costly is this decision? (higher = more costly) |

---

## 🔬 Why This is Agentic AI

This project demonstrates key properties of agentic AI systems as defined in academic literature:

1. **Autonomy** — agents operate independently with distinct roles and prompts
2. **Tool use** — agents call external APIs (web search) before reasoning
3. **Multi-step planning** — orchestrator decides which agents to invoke and how many rounds
4. **Deliberation** — multiple agents debate and refine before converging
5. **Memory** — decisions are stored, retrieved, and used to inform future analyses
6. **Self-evaluation** — bias agent and relevance agent evaluate and correct other agents
7. **Structured output** — scoring agent produces quantified, explainable metrics

> Compare with: LangChain agents, AutoGen multi-agent, CrewAI — Aegis implements the same architectural patterns from scratch.

---

## 🛣️ Roadmap

- [ ] PostgreSQL persistence (production DB)
- [ ] User authentication + personal history
- [ ] Model switcher (Groq / Gemini / OpenAI)
- [ ] Real-time agent streaming (show thinking live)
- [ ] Experiment mode (vary prompts, compare outputs)
- [ ] Decision timeline chart
- [ ] REST API for third-party integrations
- [ ] Mobile app (React Native)

---

## 🧑‍💻 Tech Stack

| Layer | Technology |
|-------|-----------|
| Backend | FastAPI (Python) |
| LLM | Groq API (LLaMA 3.1 8B Instant) |
| Web Search | Tavily API / DuckDuckGo (fallback) |
| Memory | JSON (upgradeable to PostgreSQL) |
| Frontend | Vanilla HTML/CSS/JS (no framework) |
| Fonts | Bebas Neue, Instrument Serif, Geist Mono |
| Deployment | Vercel / Uvicorn |

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgements

- [Groq](https://groq.com) for fast LLM inference
- [Tavily](https://tavily.com) for web search API
- [FastAPI](https://fastapi.tiangolo.com) for the backend framework

---

<div align="center">
Built with ❤️ as a research project in Multi-Agent AI Systems
</div>
