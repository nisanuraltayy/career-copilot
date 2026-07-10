"""Embedding için metin kurma fonksiyonları (pure, defensive)."""

from app.services.cv_service import cv_analizden_embedding_metni
from app.services.ilan_service import ilan_analizden_embedding_metni


def test_cv_metni_tum_alanlar():
    metin = cv_analizden_embedding_metni(
        {"beceriler": ["Python", "SQL"], "deneyimler": ["Backend Dev"], "egitim": "Bilgisayar Müh."}
    )
    assert "Beceriler: Python, SQL" in metin
    assert "Deneyimler: Backend Dev" in metin
    assert "Egitim: Bilgisayar Müh." in metin


def test_cv_metni_bos_analiz_cokmez():
    assert cv_analizden_embedding_metni({}) == ""


def test_cv_metni_beklenmedik_tip_cokmez():
    # beceriler string gelirse (liste değil) -> atlanır, hata fırlatmaz
    metin = cv_analizden_embedding_metni({"beceriler": "yanlis-tip", "egitim": "Lisans"})
    assert "Beceriler" not in metin
    assert "Egitim: Lisans" in metin


def test_ilan_metni_tum_alanlar():
    metin = ilan_analizden_embedding_metni(
        {
            "pozisyon_adi": "Backend Developer",
            "gerekli_beceriler": ["Python"],
            "tercih_edilen_beceriler": ["Docker"],
            "deneyim_yili": "2-3 yil",
        }
    )
    assert "Pozisyon: Backend Developer" in metin
    assert "Gerekli beceriler: Python" in metin
    assert "Tercih edilen beceriler: Docker" in metin
    assert "Deneyim: 2-3 yil" in metin


def test_ilan_metni_bos_cokmez():
    assert ilan_analizden_embedding_metni({}) == ""
