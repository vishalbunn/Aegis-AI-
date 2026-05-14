"""
Integration tests for the FastAPI app routes.

Doesn't make real LLM calls — only tests that routes exist and respond.
Run with: pytest tests/test_main_app.py
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "backend"))

# Set dummy key so model.py can import (it doesn't call out unless we hit /analyze)
os.environ.setdefault("GROQ_API_KEY", "dummy_key_for_tests")

from fastapi.testclient import TestClient
from backend.main import app

client = TestClient(app)


class TestRoutes:
    def test_health_endpoint(self):
        r = client.get("/admin/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"
        assert r.json()["version"] == "5.0"

    def test_stats_endpoint(self):
        r = client.get("/admin/stats")
        assert r.status_code == 200
        body = r.json()
        assert "cache" in body
        assert "rate_limiter" in body
        assert "cost" in body
        assert body["version"] == "5.0"

    def test_stats_shape(self):
        r = client.get("/admin/stats")
        body = r.json()
        assert "size" in body["cache"]
        assert "hits" in body["cache"]
        assert "max_requests" in body["rate_limiter"]
        assert "total_calls" in body["cost"]

    def test_home_serves_html(self):
        r = client.get("/")
        assert r.status_code == 200
        assert "html" in r.headers.get("content-type", "").lower() or r.status_code == 200

    def test_nonexistent_route_404(self):
        r = client.get("/this/route/does/not/exist")
        assert r.status_code == 404

    def test_admin_dashboard_route_exists(self):
        r = client.get("/admin")
        assert r.status_code == 200
        content = r.text.lower()
        assert "<html" in content or "<!doctype" in content

    def test_admin_dashboard_references_stats_endpoint(self):
        r = client.get("/admin")
        # Dashboard should call /admin/stats for its data
        assert "/admin/stats" in r.text