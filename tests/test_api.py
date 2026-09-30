"""
API Integration Tests for Flask Server Endpoints
"""

import json
import shutil
import tempfile
import pytest

from rag_generator.core.factory import RAGFactory
from rag_generator.app import create_web_app


@pytest.fixture
def client():
    tmp_dir = tempfile.mkdtemp()
    factory = RAGFactory(storage_root=tmp_dir)

    # Seed one test app
    factory.create_app(
        name="Test API App",
        description="Testing endpoints",
        raw_texts=[{
            "title": "api_test.txt",
            "content": "The API gateway rate limit is 10,000 requests per minute with Redis token bucket algorithm."
        }]
    )

    app = create_web_app(factory=factory)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client

    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_api_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.get_json()
    assert data["status"] == "healthy"
    assert "supported_formats" in data


def test_api_list_apps(client):
    res = client.get("/api/apps")
    assert res.status_code == 200
    apps = res.get_json()
    assert len(apps) >= 1
    assert "app_id" in apps[0]


def test_api_query_app(client):
    apps_res = client.get("/api/apps")
    app_id = apps_res.get_json()[0]["app_id"]

    query_res = client.post(
        f"/api/apps/{app_id}/query",
        json={"question": "What is the API gateway rate limit?", "top_k": 3}
    )
    assert query_res.status_code == 200
    answer = query_res.get_json()
    assert "10,000" in answer["answer"]
    assert answer["confidence"] in ("High", "Medium")
    assert len(answer["citations"]) >= 1


def test_api_create_app(client):
    create_res = client.post(
        "/api/apps",
        json={
            "name": "Runtime Created App",
            "description": "Created via API",
            "raw_texts": [{"title": "note.txt", "content": "Special project codename is Project Chimera."}]
        }
    )
    assert create_res.status_code == 201
    data = create_res.get_json()
    new_app_id = data["application"]["app_id"]

    # Verify query on newly created app
    q_res = client.post(
        f"/api/apps/{new_app_id}/query",
        json={"question": "What is the special project codename?"}
    )
    assert q_res.status_code == 200
    assert "Project Chimera" in q_res.get_json()["answer"]
