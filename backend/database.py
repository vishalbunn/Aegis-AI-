import json
import os
from datetime import datetime

DB_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory.json")

def _load():
    if not os.path.exists(DB_FILE):
        return []
    with open(DB_FILE, "r") as f:
        return json.load(f)

def _save(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def init_db():
    if not os.path.exists(DB_FILE):
        _save([])
    print(f"✅ JSON memory ready → {DB_FILE}")

def save_decision(query, pro, con, critique, final, scores: dict = None, uncertainty: dict = None, bias: dict = None, consensus: dict = None, domain: str = "general"):
    records = _load()
    new_id = (records[-1]["id"] + 1) if records else 1
    scores = scores or {}
    record = {
        "id":          new_id,
        "query":       query,
        "pro":         pro,
        "con":         con,
        "critique":    critique,
        "final":       final,
        "domain":      domain,
        # flat scores for quick access
        "feasibility": scores.get("feasibility"),
        "risk":        scores.get("risk"),
        "confidence":  scores.get("confidence"),
        "impact":      scores.get("impact"),
        "cost":        scores.get("cost"),
        "overall":     scores.get("overall"),
        # full structured data
        "scores":      scores,
        "uncertainty": uncertainty or {},
        "bias":        bias or {},
        "consensus":   consensus or {},
        "agent_influence": scores.get("agent_influence", {}),
        "created_at":  datetime.now().isoformat(),
    }
    records.append(record)
    _save(records)
    return {"id": new_id, "created_at": record["created_at"]}

def get_all_decisions(limit=100):
    records = _load()
    return sorted(records, key=lambda r: r["created_at"], reverse=True)[:limit]

def get_decision_by_id(decision_id: int):
    for r in _load():
        if r["id"] == decision_id:
            return r
    return None

def get_all_raw():
    """Return all records for similarity matching."""
    return _load()