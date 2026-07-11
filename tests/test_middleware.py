"""Request-ID ve güvenlik başlığı middleware'leri."""


def test_request_id_header_eklenir(client):
    r = client.get("/saglik")
    assert r.status_code == 200
    assert r.headers.get("X-Request-ID")  # boş olmayan bir kimlik


def test_gelen_request_id_korunur(client):
    r = client.get("/saglik", headers={"X-Request-ID": "test-rid-123"})
    assert r.headers.get("X-Request-ID") == "test-rid-123"


def test_guvenlik_basliklari(client):
    r = client.get("/saglik")
    assert r.headers.get("X-Content-Type-Options") == "nosniff"
    assert r.headers.get("X-Frame-Options") == "DENY"


def test_rate_limitli_endpoint_acikken_500_donmez(client, monkeypatch):
    """Regresyon: rate limiting AÇIKKEN, Pydantic model döndüren rate-limitli
    bir endpoint 500 vermemeli (slowapi header-injection tuzağı)."""
    from types import SimpleNamespace

    from app.core.rate_limit import limiter
    from app.services import user_service

    monkeypatch.setattr(
        user_service, "kayit_ol",
        lambda db, email, parola: SimpleNamespace(id=1, email=email),
    )
    limiter.enabled = True
    try:
        r = client.post(
            "/auth/register", json={"email": "x@y.com", "parola": "parola12345"}
        )
        assert r.status_code == 201, r.text  # 500 DEĞİL
        assert r.json()["access_token"]
    finally:
        limiter.enabled = False
