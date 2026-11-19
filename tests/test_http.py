from fastapi.testclient import TestClient

from sieve.http_server import app

client = TestClient(app)


def test_health() -> None:
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_index_and_query() -> None:
    response = client.post("/index", json={"repo": "sample_repo_large"})
    assert response.status_code == 200
    assert response.json()["files"] == 18
    response = client.post("/query", json={
        "task": "Fix KeyError in check_auth when token is missing",
        "repo": "sample_repo_large", "budget": 600,
    })
    assert response.status_code == 200
    assert response.json()["layers"]["total"] <= 600


def test_compress_endpoint() -> None:
    text = "\n".join(f"INFO line {i}" for i in range(2000))
    text += "\nERROR boom in checkout"
    response = client.post("/compress", json={"text": text, "budget": 200})
    assert response.status_code == 200
    body = response.json()
    assert "ERROR boom" in body["text"]
    assert body["tokens_after"] <= 200


def test_read_traversal_is_rejected() -> None:
    client.post("/index", json={"repo": "sample_repo_large"})
    response = client.post("/read", json={
        "file": "../../outside.py", "repo": "sample_repo_large",
    })
    assert response.status_code == 404
