"""تست لایهٔ HTTP (Issue #5 تا #12).

از `TestClient` استفاده می‌کند که بدون سرور واقعی و بدون شبکه کار می‌کند.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.api.main import app

VALID = {
    "description": "آشپزخانه و حمام قدیمی بازسازی کامل، بودجه 500 میلیون تومان",
    "total_area_m2": "80",
    "title": "آپارتمان ونک",
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def _create(client: TestClient, **overrides) -> dict:
    data = {**VALID, **overrides}
    res = client.post("/api/projects", data=data)
    assert res.status_code == 201, res.text
    return res.json()


class TestHealth:
    def test_health_ok(self, client):
        res = client.get("/health")
        assert res.status_code == 200
        assert res.json()["status"] == "ok"


class TestUi:
    def test_index_served(self, client):
        res = client.get("/")
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]

    def test_index_is_rtl_persian(self, client):
        text = client.get("/").text
        assert 'dir="rtl"' in text
        assert 'lang="fa"' in text
        assert "بنّا" in text

    def test_index_has_form_fields(self, client):
        text = client.get("/").text
        for field in ('id="area"', 'id="desc"', 'id="files"'):
            assert field in text


class TestCreateProject:
    def test_returns_full_result(self, client):
        data = _create(client)
        assert data["project_id"]
        assert data["total_area_m2"] > 0
        assert len(data["spaces"]) == 2
        assert len(data["scenarios"]) == 4
        assert data["wbs_items"]
        assert data["selected"] in {s["kind"] for s in data["scenarios"]}

    def test_no_missing_prices(self, client):
        assert _create(client)["missing_price_codes"] == []

    def test_scenario_labels_are_persian(self, client):
        labels = {s["label_fa"] for s in _create(client)["scenarios"]}
        assert labels == {"اقتصادی", "استاندارد", "باکیفیت", "مناسب اجاره"}

    def test_scenarios_have_cost_ranges(self, client):
        for scen in _create(client)["scenarios"]:
            assert scen["cost"]["min_toman"] < scen["cost"]["max_toman"]
            assert scen["duration_days"]["min_toman"] < scen["duration_days"]["max_toman"]

    def test_budget_selects_scenario(self, client):
        data = _create(client, description="آشپزخانه بازسازی کامل، بودجه 150 میلیون تومان")
        assert data["budget_toman"] == 150_000_000
        assert data["selected"] == "rental"

    def test_wbs_items_are_ordered_by_phase(self, client):
        order = ["تخریب", "تأسیسات", "سازه و دیوار", "پوشش کف و دیوار", "کابینت و درب", "رنگ و دکور"]
        phases = [i["phase_label_fa"] for i in _create(client)["wbs_items"]]
        assert phases == sorted(phases, key=order.index)

    def test_wbs_items_have_material(self, client):
        for item in _create(client)["wbs_items"]:
            assert item["material"], f"{item['code']} بدون متریال"

    def test_description_alone_is_enough(self, client):
        """متراژ و رسانه اختیاری‌اند — متن به‌تنهایی باید کار کند."""
        data = _create(client, description="آشپزخانه و حمام بازسازی کامل", total_area_m2="")
        assert data["spaces"]
        assert data["scenarios"]

    def test_brief_url_returned(self, client):
        data = _create(client)
        assert data["brief_url"] == f"/api/projects/{data['project_id']}/brief"


class TestValidationErrors:
    def test_empty_description_rejected(self, client):
        res = client.post("/api/projects", data={"description": "", "total_area_m2": "80"})
        assert res.status_code == 422

    def test_area_below_mvp_range_rejected(self, client):
        res = client.post("/api/projects", data={**VALID, "total_area_m2": "5"})
        assert res.status_code == 400
        assert "۲۰" in res.json()["detail"]

    def test_area_above_mvp_range_rejected(self, client):
        res = client.post("/api/projects", data={**VALID, "total_area_m2": "5000"})
        assert res.status_code == 400
        assert "۱۰۰۰" in res.json()["detail"]

    def test_errors_are_persian(self, client):
        detail = client.post("/api/projects", data={**VALID, "total_area_m2": "5"}).json()["detail"]
        assert not detail.isascii()

    def test_unsupported_file_type_rejected(self, client):
        res = client.post(
            "/api/projects",
            data=VALID,
            files={"files": ("doc.pdf", b"%PDF-1.4", "application/pdf")},
        )
        assert res.status_code == 400
        assert "پشتیبانی" in res.json()["detail"]

    def test_oversized_file_rejected(self, client):
        big = b"x" * (25 * 1024 * 1024 + 1)
        res = client.post(
            "/api/projects",
            data=VALID,
            files={"files": ("huge.jpg", big, "image/jpeg")},
        )
        assert res.status_code == 400
        assert "حجم" in res.json()["detail"]

    def test_valid_image_accepted(self, client):
        res = client.post(
            "/api/projects",
            data=VALID,
            files={"files": ("room.jpg", b"fake-jpeg-bytes", "image/jpeg")},
        )
        assert res.status_code == 201, res.text


class TestRetrieveProject:
    def test_get_project_by_id(self, client):
        created = _create(client)
        res = client.get(f"/api/projects/{created['project_id']}")
        assert res.status_code == 200
        assert res.json()["project_id"] == created["project_id"]

    def test_unknown_project_returns_404(self, client):
        res = client.get("/api/projects/doesnotexist")
        assert res.status_code == 404
        assert not res.json()["detail"].isascii()

    def test_result_is_stable_across_requests(self, client):
        created = _create(client)
        again = client.get(f"/api/projects/{created['project_id']}").json()
        assert again["wbs_items"] == created["wbs_items"]
        assert again["scenarios"] == created["scenarios"]


class TestBriefEndpoint:
    def test_brief_is_html(self, client):
        created = _create(client)
        res = client.get(created["brief_url"])
        assert res.status_code == 200
        assert "text/html" in res.headers["content-type"]

    def test_brief_is_rtl_and_has_title(self, client):
        created = _create(client)
        text = client.get(created["brief_url"]).text
        assert 'dir="rtl"' in text
        assert "آپارتمان ونک" in text

    def test_brief_contains_all_scenarios(self, client):
        created = _create(client)
        text = client.get(created["brief_url"]).text
        for label in ("اقتصادی", "استاندارد", "باکیفیت", "مناسب اجاره"):
            assert label in text

    def test_brief_contains_wbs_items(self, client):
        created = _create(client)
        text = client.get(created["brief_url"]).text
        for item in created["wbs_items"]:
            assert item["title"] in text

    def test_brief_404_for_unknown_project(self, client):
        assert client.get("/api/projects/nope/brief").status_code == 404


class TestOpenApi:
    def test_schema_generated(self, client):
        res = client.get("/openapi.json")
        assert res.status_code == 200
        paths = res.json()["paths"]
        assert "/api/projects" in paths
        assert "/api/projects/{project_id}/brief" in paths
