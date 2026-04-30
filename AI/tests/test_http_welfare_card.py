from types import SimpleNamespace

from fastapi.testclient import TestClient

from api.http import create_app


def _build_test_config():
    return SimpleNamespace(
        server=SimpleNamespace(debug=False, cors_origins="*"),
        ocr=SimpleNamespace(
            provider="paddleocr",
            device="cpu",
            http_timeout_seconds=45,
            http_max_upload_mb=20,
        ),
    )


def test_health_endpoint_returns_200(monkeypatch):
    monkeypatch.setattr("api.http.get_config", _build_test_config)
    client = TestClient(create_app())

    response = client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert "ocr" in body["services"]


def test_welfare_card_ocr_endpoint_returns_json(monkeypatch):
    monkeypatch.setattr("api.http.get_config", _build_test_config)

    def _fake_extract(image_data: bytes, device: str):
        assert image_data
        assert device == "cpu"
        return {
            "card_company": "KB국민카드",
            "card_number": "1234-5678-9012-3456",
            "expiration_date": "12/30",
            "cvc": "123",
            "confidence": {
                "card_company": 0.95,
                "card_number": 0.92,
                "expiration_date": 0.81,
                "cvc": 0.76,
            },
            "raw_text": ["KB국민카드", "1234 5678 9012 3456", "12/30", "CVC 123"],
        }

    monkeypatch.setattr("api.http._extract_welfare_card_fields", _fake_extract)
    client = TestClient(create_app())

    response = client.post(
        "/api/v1/ocr/welfare-card",
        files={"file": ("welfare-card.jpg", b"fake-image-data", "image/jpeg")},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["card_company"] == "KB국민카드"
    assert body["card_number"] == "1234-5678-9012-3456"
    assert body["expiration_date"] == "12/30"
    assert body["cvc"] == "123"
    assert isinstance(body["raw_text"], list)
    assert "confidence" in body
