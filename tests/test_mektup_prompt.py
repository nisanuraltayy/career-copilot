"""Motivasyon mektubu prompt boyut koruması (kök-neden düzeltmesi).

Aşırı büyük CV analizi geldiğinde prompt'un güvenli boyutta kaldığını ve
akıllı kırpmanın çalıştığını doğrular.
"""

from types import SimpleNamespace
from unittest.mock import MagicMock

from app.core.config import settings
from app.services import mektup_service
from app.services.mektup_service import _kirp_liste, _kirp_metin


def test_kirp_liste_azami_uygular():
    assert _kirp_liste([1, 2, 3, 4], 2) == ["1", "2"]


def test_kirp_liste_liste_degilse_bos():
    assert _kirp_liste("liste-degil", 5) == []
    assert _kirp_liste(None, 5) == []


def test_kirp_metin_uzunsa_kirpar():
    assert _kirp_metin("abcdefgh", 3) == "abc…"
    assert _kirp_metin("kisa", 10) == "kisa"
    assert _kirp_metin(None, 10) == ""


def _yakala_prompt(monkeypatch, cv, ilan) -> str:
    monkeypatch.setattr(mektup_service, "cv_getir", lambda db, cid, uid: cv)
    monkeypatch.setattr(mektup_service, "ilan_getir", lambda db, iid, uid: ilan)
    yakalanan = {}

    def sahte_metin_uret(prompt):
        yakalanan["prompt"] = prompt
        return "Sayin Yetkili, ..."

    monkeypatch.setattr(mektup_service.gemini, "metin_uret", sahte_metin_uret)
    mektup_service.mektup_uret(MagicMock(), user_id=1, cv_id=1, is_ilani_id=2)
    return yakalanan["prompt"]


def test_buyuk_analiz_prompt_guvenli_boyutta(monkeypatch):
    # Patolojik olarak büyük analiz: 500 beceri, 100 x 1000 karakter deneyim.
    cv = SimpleNamespace(
        id=1,
        analiz={
            "beceriler": [f"skill{i}" for i in range(500)],
            "deneyimler": ["x" * 1000 for _ in range(100)],
            "egitim": "y" * 5000,
        },
    )
    ilan = SimpleNamespace(
        id=2,
        pozisyon_adi="Backend Developer",
        sirket_adi="ACME",
        analiz={"gerekli_beceriler": [f"req{i}" for i in range(300)]},
    )

    prompt = _yakala_prompt(monkeypatch, cv, ilan)

    # Prompt güvenli tavanın altında kalmalı.
    assert len(prompt) <= settings.max_prompt_chars
    # Beceriler 40'a kırpıldı: skill0 var, skill45 yok.
    assert "skill0" in prompt
    assert "skill45" not in prompt
    # Eğitim kırpıldı (5000 -> <=500 + kırpma işareti).
    assert "y" * 5000 not in prompt


def test_normal_analiz_kirpilmaz(monkeypatch):
    cv = SimpleNamespace(
        id=3,
        analiz={"beceriler": ["Python", "FastAPI"], "deneyimler": ["Backend Dev"], "egitim": "Lisans"},
    )
    ilan = SimpleNamespace(
        id=4, pozisyon_adi="Backend", sirket_adi=None,
        analiz={"gerekli_beceriler": ["Python"]},
    )
    prompt = _yakala_prompt(monkeypatch, cv, ilan)
    assert "Python" in prompt
    assert "Backend Dev" in prompt
    assert "ilgili şirket" in prompt  # sirket_adi None -> fallback
