"""Test Story 2.1: export_graph nhận scope + endpoint GET /api/graph.

- scope='public' bỏ node internal + mọi edge chạm node internal (AD-11, đóng defer 1.7).
- scope='all' (mặc định) giữ toàn bộ đồ thị.
- Endpoint trả 200 + shape {nodes, edges}; audience=customer suy scope=public.
"""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from api.main import create_app
from kb.factory import get_repository

CORPUS = Path(__file__).resolve().parents[2] / "data" / "sample" / "corpus.json"


def _repo():
    return get_repository(str(CORPUS))


def test_export_graph_all_includes_internal() -> None:
    g = _repo().export_graph()  # mặc định scope='all'
    ids = {n["id"] for n in g["nodes"]}
    assert "QD-INT/Điều 2" in ids  # node internal có mặt ở chế độ 'all'


def test_export_graph_public_excludes_internal() -> None:
    g = _repo().export_graph(scope="public")
    ids = {n["id"] for n in g["nodes"]}
    assert "QD-INT/Điều 2" not in ids  # node internal bị lọc (AD-11)
    assert all(n["visibility"] == "public" for n in g["nodes"])


def test_export_graph_public_drops_edges_touching_internal() -> None:
    g = _repo().export_graph(scope="public")
    ids = {n["id"] for n in g["nodes"]}
    # Mọi edge còn lại chỉ nối các node còn hiển thị (không rò internal qua cạnh)
    for e in g["edges"]:
        assert e["from"] in ids and e["to"] in ids


def test_graph_endpoint_shape() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.get("/api/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data and "edges" in data
        assert len(data["nodes"]) >= 1 and len(data["edges"]) >= 1


def test_graph_endpoint_customer_hides_internal() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.get("/api/graph", params={"audience": "customer"})
        assert resp.status_code == 200
        ids = {n["id"] for n in resp.json()["nodes"]}
        assert "QD-INT/Điều 2" not in ids


def test_graph_endpoint_employee_shows_internal() -> None:
    app = create_app(str(CORPUS))
    with TestClient(app) as client:
        resp = client.get("/api/graph", params={"audience": "employee"})
        assert resp.status_code == 200
        ids = {n["id"] for n in resp.json()["nodes"]}
        assert "QD-INT/Điều 2" in ids
