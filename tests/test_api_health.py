"""Sağlık endpoint'leri."""


def test_ana_sayfa(client):
    r = client.get("/")
    assert r.status_code == 200
    body = r.json()
    assert body["durum"] == "calisiyor"
    assert body["ortam"] == "test"


def test_saglik(client):
    r = client.get("/saglik")
    assert r.status_code == 200
    assert r.json()["durum"] == "iyi"


def test_hazir_db_ok(client, fake_db):
    # fake_db.execute() sorunsuz döner -> hazır
    r = client.get("/hazir")
    assert r.status_code == 200
    assert r.json()["durum"] == "hazir"


def test_hazir_db_down_503(client, fake_db):
    fake_db.execute.side_effect = RuntimeError("db down")
    r = client.get("/hazir")
    assert r.status_code == 503
