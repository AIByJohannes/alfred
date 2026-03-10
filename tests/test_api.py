from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def test_health_reports_runtime(monkeypatch):
    monkeypatch.delenv("ALFRED_CLI_BIN", raising=False)

    response = client.get("/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["runtime_root"].endswith(".alfred-runtime")
    assert body["prompt_source"] == "prompts/SOUL.md"


def test_root_endpoint_includes_prompt_metadata():
    response = client.get("/")

    assert response.status_code == 200
    body = response.json()
    assert body["prompt_source"] == "prompts/SOUL.md"
    assert body["message"] == "Alfred local workbench is running"
