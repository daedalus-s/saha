from pathlib import Path

from fastapi.testclient import TestClient

from app.extract.clean import clean_html
from app.extract.llm_extract import heuristic_extract


FIXTURE = Path(__file__).parent / "fixtures" / "sample_page.html"


def test_clean_html_keeps_verses():
    html = FIXTURE.read_text(encoding="utf-8")
    text = clean_html(html, url="https://example.org/gayatri")
    assert "भूर्भुवः" in text
    assert "cookie" not in text.lower() or "भूर्भुवः" in text


def test_heuristic_extract_finds_devanagari_verses():
    html = FIXTURE.read_text(encoding="utf-8")
    text = clean_html(html)
    result = heuristic_extract(text, query="Gayatri Mantra")
    assert result["found"]
    assert result["verses"]
    assert result["script"] == "devanagari"
    assert any("सवितुर्वरेण्यं" in v for v in result["verses"])


def test_privacy_and_terms_pages():
    from app.main import app

    client = TestClient(app)
    privacy = client.get("/privacy")
    terms = client.get("/terms")
    assert privacy.status_code == 200
    assert "Privacy Policy" in privacy.text
    assert terms.status_code == 200
    assert "Terms of Use" in terms.text


def test_health_open():
    from app.main import app

    client = TestClient(app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_search_requires_app_key():
    from app.main import app

    client = TestClient(app)
    response = client.post("/search", json={"query": "Gayatri"})
    assert response.status_code == 401


def test_search_with_app_key():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/search",
        json={"query": "Gayatri Mantra"},
        headers={"X-App-Key": "dev-app-key"},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["hits"]


def test_transliterate_endpoint():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/transliterate",
        json={
            "verses": ["राम"],
            "source_script": "devanagari",
            "target_script": "iast",
        },
        headers={"X-App-Key": "dev-app-key"},
    )
    assert response.status_code == 200
    verses = response.json()["verses"]
    assert verses
    assert verses[0]


def test_extract_mock_page():
    from app.main import app

    client = TestClient(app)
    response = client.post(
        "/extract",
        json={"url": "https://example.org/vignanam/hanuman-chalisa-devanagari"},
        headers={"X-App-Key": "dev-app-key"},
    )
    assert response.status_code == 200
    version = response.json()["version"]
    assert version["script"] == "devanagari"
    assert version["verses"]
