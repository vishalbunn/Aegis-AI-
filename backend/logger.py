import json
import os
import time
from datetime import datetime

LOG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs.json")

def _load():
    if not os.path.exists(LOG_FILE):
        return []
    with open(LOG_FILE, "r") as f:
        return json.load(f)

def _save(data):
    with open(LOG_FILE, "w") as f:
        json.dump(data, f, indent=2, default=str)

def log_request(query: str, result: dict, latency_ms: float, model: str = "llama-3.1-8b-instant"):
    logs = _load()
    entry = {
        "id": len(logs) + 1,
        "timestamp": datetime.now().isoformat(),
        "query": query,
        "model": model,
        "latency_ms": round(latency_ms, 2),
        "agents_output": {
            "pro": result.get("pro", "")[:300],
            "con": result.get("con", "")[:300],
            "critique": result.get("critique", "")[:300],
            "final": result.get("final", "")[:300],
        },
        "scores": result.get("scores", {}),
        "uncertainty": result.get("uncertainty", {}),
        "bias": result.get("bias", {}),
        "rounds": result.get("rounds", 1),
        "domain": result.get("domain", "general"),
    }
    logs.append(entry)
    _save(logs)
    return entry

def get_logs(limit: int = 50):
    logs = _load()
    return sorted(logs, key=lambda x: x["timestamp"], reverse=True)[:limit]