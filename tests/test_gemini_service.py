"""Gemini sarmalayıcısı — JSON temizleme, hata soyutlama (client mocklanır)."""


from unittest.mock import MagicMock

import pytest
from google.genai import errors as genai_errors

from app.core.exceptions import ServiceUnavailableError, UpstreamServiceError
from app.services import gemini


@pytest.fixture(autouse=True)
def _hizli_retry(monkeypatch):
    """Testlerde gerçek beklemeyi kaldır; sleep çağrılarını say."""
    uyku = MagicMock()
    monkeypatch.setattr(gemini.time, "sleep", uyku)
    # backoff'u deterministik ve sıfır yap (jitter'ı sabitle)
    monkeypatch.setattr(gemini.random, "uniform", lambda a, b: 0.0)
    return uyku


def _srv_error(code: int = 503):
    """Gerçek bir SDK ServerError (geçici) üretir."""
    return genai_errors.ServerError(
        code, {"error": {"code": code, "status": "UNAVAILABLE", "message": "busy"}}
    )


def _client_kur(monkeypatch, generate_side_effect):
    """generate_content'i verilen side_effect ile bir sahte client kurar.
    Çağrı sayısını takip eden MagicMock'u döndürür."""
    gen = MagicMock(side_effect=generate_side_effect)

    def sahte_client():
        m = type("M", (), {})()
        m.models = type("Models", (), {})()
        m.models.generate_content = gen
        return m

    monkeypatch.setattr(gemini, "_client", sahte_client)
    return gen


def test_strip_json_fence_json_etiketi():
    assert gemini._strip_json_fence('```json\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_json_fence_duz_fence():
    assert gemini._strip_json_fence('```\n{"a": 1}\n```') == '{"a": 1}'


def test_strip_json_fence_fence_yok():
    assert gemini._strip_json_fence('{"a": 1}') == '{"a": 1}'


def _sahte_yanit(text: str):
    class _Y:
        def __init__(self, t):
            self.text = t
    return _Y(text)


def test_json_uret_basarili(monkeypatch):
    def sahte_client():
        m = type("M", (), {})()
        m.models = type("Models", (), {})()
        m.models.generate_content = lambda model, contents: _sahte_yanit('```json\n{"x": 5}\n```')
        return m

    monkeypatch.setattr(gemini, "_client", sahte_client)
    assert gemini.json_uret("prompt") == {"x": 5}


def test_json_uret_gecersiz_json_upstream_error(monkeypatch):
    def sahte_client():
        m = type("M", (), {})()
        m.models = type("Models", (), {})()
        m.models.generate_content = lambda model, contents: _sahte_yanit("bu json degil")
        return m

    monkeypatch.setattr(gemini, "_client", sahte_client)
    with pytest.raises(UpstreamServiceError):
        gemini.json_uret("prompt")


def test_json_uret_api_hatasi_upstream_error(monkeypatch):
    def sahte_client():
        m = type("M", (), {})()
        m.models = type("Models", (), {})()
        def patla(model, contents):
            raise RuntimeError("API down")
        m.models.generate_content = patla
        return m

    monkeypatch.setattr(gemini, "_client", sahte_client)
    with pytest.raises(UpstreamServiceError):
        gemini.json_uret("prompt")


def test_embedding_bos_metin_none_doner():
    assert gemini.embedding_uret("") is None
    assert gemini.embedding_uret("   ") is None


def test_embedding_api_hatasi_none_doner(monkeypatch):
    def sahte_client():
        m = type("M", (), {})()
        m.models = type("Models", (), {})()
        def patla(model, contents, config):
            raise RuntimeError("embed down")
        m.models.embed_content = patla
        return m

    monkeypatch.setattr(gemini, "_client", sahte_client)
    # graceful degradation: exception değil None
    assert gemini.embedding_uret("metin") is None


# --- Retry / exponential backoff davranışı ---


def test_gecici_hata_sonra_basari(monkeypatch):
    # İlk iki çağrı 503, üçüncü başarılı -> retry sayesinde sonuç döner.
    gen = _client_kur(
        monkeypatch,
        [_srv_error(503), _srv_error(503), _sahte_yanit('{"x": 5}')],
    )
    assert gemini.json_uret("prompt") == {"x": 5}
    assert gen.call_count == 3


def test_gecici_hata_tukenirse_503(monkeypatch, _hizli_retry):
    # Her zaman 503 -> denemeler tükenir -> ServiceUnavailableError.
    gen = _client_kur(monkeypatch, _srv_error(503))
    with pytest.raises(ServiceUnavailableError):
        gemini.json_uret("prompt")
    # max_retries=4 -> 5 deneme, 4 bekleme
    assert gen.call_count == settings_max_retries() + 1
    assert _hizli_retry.call_count == settings_max_retries()


def test_429_rate_limit_gecici(monkeypatch):
    gen = _client_kur(monkeypatch, [genai_errors.ClientError(429, {"error": {"code": 429}}),
                                    _sahte_yanit('{"ok": 1}')])
    assert gemini.json_uret("p") == {"ok": 1}
    assert gen.call_count == 2


def test_kalici_hata_502_retry_yok(monkeypatch, _hizli_retry):
    # 400 kalıcı istemci hatası -> retry YOK, UpstreamServiceError (502).
    gen = _client_kur(monkeypatch, genai_errors.ClientError(400, {"error": {"code": 400}}))
    with pytest.raises(UpstreamServiceError):
        gemini.json_uret("prompt")
    assert gen.call_count == 1
    assert _hizli_retry.call_count == 0


def test_metin_uret_gecici_tukenirse_503(monkeypatch):
    _client_kur(monkeypatch, _srv_error(503))
    with pytest.raises(ServiceUnavailableError):
        gemini.metin_uret("prompt")


def test_embedding_gecici_tukenirse_none(monkeypatch):
    # Embedding opsiyonel: retry yapılır ama sonunda başarısızsa None (patlamaz).
    gen = MagicMock(side_effect=_srv_error(503))

    def sahte_client():
        m = type("M", (), {})()
        m.models = type("Models", (), {})()
        m.models.embed_content = gen
        return m

    monkeypatch.setattr(gemini, "_client", sahte_client)
    assert gemini.embedding_uret("metin") is None
    assert gen.call_count == settings_max_retries() + 1


def settings_max_retries() -> int:
    from app.core.config import settings
    return settings.gemini_max_retries
