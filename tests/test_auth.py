"""Auth: güvenlik yardımcıları, register/login akışı ve endpoint koruması."""

from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core import security
from app.core.exceptions import AuthError, ConflictError
from app.db.models import User
from app.services import user_service

# --- Birim: parola hash + JWT ---


def test_parola_hash_ve_dogrula():
    h = security.hash_parola("gizli-parola")
    assert h != "gizli-parola"
    assert security.parola_dogrula("gizli-parola", h) is True
    assert security.parola_dogrula("yanlis", h) is False


def test_token_uret_ve_coz_round_trip():
    token = security.token_uret(42)
    assert security.token_coz(token) == 42


def test_token_coz_gecersiz_none():
    assert security.token_coz("bozuk.token.xyz") is None
    assert security.token_coz("") is None


# --- API: register / login ---


def test_register_token_doner(client, monkeypatch):
    monkeypatch.setattr(
        user_service, "kayit_ol",
        lambda db, email, parola: SimpleNamespace(id=7, email=email),
    )
    r = client.post("/auth/register", json={"email": "a@b.com", "parola": "parola12345"})
    assert r.status_code == 201
    assert r.json()["access_token"]
    assert r.json()["token_type"] == "bearer"


def test_register_kisa_parola_422(client):
    r = client.post("/auth/register", json={"email": "a@b.com", "parola": "kisa"})
    assert r.status_code == 422


def test_register_gecersiz_email_422(client):
    r = client.post("/auth/register", json={"email": "gecersiz", "parola": "parola12345"})
    assert r.status_code == 422


def test_register_duplicate_409(client, monkeypatch):
    def patla(db, email, parola):
        raise ConflictError("Bu e-posta zaten kayıtlı.")

    monkeypatch.setattr(user_service, "kayit_ol", patla)
    r = client.post("/auth/register", json={"email": "a@b.com", "parola": "parola12345"})
    assert r.status_code == 409
    assert r.json()["error"]["code"] == "conflict"


def test_login_basarili(client, monkeypatch):
    monkeypatch.setattr(
        user_service, "kimlik_dogrula",
        lambda db, email, parola: SimpleNamespace(id=3, email=email),
    )
    r = client.post("/auth/login", json={"email": "a@b.com", "parola": "parola12345"})
    assert r.status_code == 200
    assert r.json()["access_token"]


def test_login_hatali_401(client, monkeypatch):
    def patla(db, email, parola):
        raise AuthError("E-posta veya parola hatalı.")

    monkeypatch.setattr(user_service, "kimlik_dogrula", patla)
    r = client.post("/auth/login", json={"email": "a@b.com", "parola": "yanlisparola"})
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_me_mevcut_kullaniciyi_doner(client):
    # client fixture'ı get_current_user'ı TEST_USER'a eziyor.
    r = client.get("/auth/me")
    assert r.status_code == 200
    assert r.json()["email"] == "test@example.com"


def test_register_login_refresh_token_dondurur(client, monkeypatch):
    monkeypatch.setattr(
        user_service, "kayit_ol",
        lambda db, email, parola: SimpleNamespace(id=7, email=email),
    )
    r = client.post("/auth/register", json={"email": "a@b.com", "parola": "parola12345"})
    assert r.json()["refresh_token"]  # access + refresh çifti


# --- Refresh token + parola değiştirme ---


def test_refresh_yeni_token_verir(client, monkeypatch):
    monkeypatch.setattr(
        user_service, "kullanici_getir",
        lambda db, uid: SimpleNamespace(id=uid, is_active=True),
    )
    rt = security.refresh_token_uret(5)
    r = client.post("/auth/refresh", json={"refresh_token": rt})
    assert r.status_code == 200
    assert r.json()["access_token"] and r.json()["refresh_token"]


def test_refresh_gecersiz_token_401(client):
    r = client.post("/auth/refresh", json={"refresh_token": "bozuk.token"})
    assert r.status_code == 401


def test_access_ve_refresh_token_ayrisir():
    at = security.token_uret(1)  # access
    rt = security.refresh_token_uret(1)
    # access, refresh yerine kullanılamaz; refresh, access yerine kullanılamaz.
    assert security.token_coz(at, beklenen_tip="refresh") is None
    assert security.token_coz(rt, beklenen_tip="access") is None
    assert security.token_coz(at, beklenen_tip="access") == 1
    assert security.token_coz(rt, beklenen_tip="refresh") == 1


def test_change_password_204(client, monkeypatch):
    monkeypatch.setattr(user_service, "parola_degistir", lambda db, user, eski, yeni: None)
    r = client.post(
        "/auth/change-password",
        json={"eski_parola": "eskiparola", "yeni_parola": "yeniparola123"},
    )
    assert r.status_code == 204


def test_change_password_kisa_parola_422(client):
    r = client.post(
        "/auth/change-password", json={"eski_parola": "x", "yeni_parola": "kisa"}
    )
    assert r.status_code == 422


def test_change_password_tokensiz_401(anon_client):
    r = anon_client.post(
        "/auth/change-password",
        json={"eski_parola": "x", "yeni_parola": "yeniparola123"},
    )
    assert r.status_code == 401


# --- Endpoint koruması (anon_client: get_current_user ezilmemiş) ---


def test_korumali_endpoint_tokensiz_401(anon_client):
    r = anon_client.get("/cv-gecmis")
    assert r.status_code == 401
    assert r.json()["error"]["code"] == "unauthorized"


def test_saglik_public_kalir(anon_client):
    # Sağlık uçları auth gerektirmez.
    assert anon_client.get("/saglik").status_code == 200


# --- Entegrasyon: gerçek DB yazma yolu (in-memory SQLite) ---


@pytest.fixture
def sqlite_db():
    """Sadece users tablosunu içeren in-memory SQLite session (Postgres'siz)."""
    eng = create_engine("sqlite://")
    User.__table__.create(eng)
    with Session(eng) as s:
        yield s


def test_kayit_ve_giris_gercek_db(sqlite_db):
    u = user_service.kayit_ol(sqlite_db, "x@y.com", "parola12345")
    assert u.id is not None
    assert u.hashed_password.startswith("$2b$")  # bcrypt
    assert user_service.kimlik_dogrula(sqlite_db, "x@y.com", "parola12345").id == u.id


def test_duplicate_kayit_conflict_gercek_db(sqlite_db):
    user_service.kayit_ol(sqlite_db, "x@y.com", "parola12345")
    with pytest.raises(ConflictError):
        user_service.kayit_ol(sqlite_db, "x@y.com", "parola12345")


def test_yanlis_parola_autherror_gercek_db(sqlite_db):
    user_service.kayit_ol(sqlite_db, "x@y.com", "parola12345")
    with pytest.raises(AuthError):
        user_service.kimlik_dogrula(sqlite_db, "x@y.com", "yanlis")


def test_parola_degistir_gercek_db(sqlite_db):
    u = user_service.kayit_ol(sqlite_db, "x@y.com", "parola12345")
    user_service.parola_degistir(sqlite_db, u, "parola12345", "yeniparola99")
    # yeni parola geçer, eski geçmez
    assert user_service.kimlik_dogrula(sqlite_db, "x@y.com", "yeniparola99").id == u.id
    with pytest.raises(AuthError):
        user_service.kimlik_dogrula(sqlite_db, "x@y.com", "parola12345")


def test_parola_degistir_yanlis_eski_autherror(sqlite_db):
    u = user_service.kayit_ol(sqlite_db, "x@y.com", "parola12345")
    with pytest.raises(AuthError):
        user_service.parola_degistir(sqlite_db, u, "yanliseskisi", "yeniparola99")
