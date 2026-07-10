"""V1 deterministik uyum skoru — çekirdek iş mantığı testleri."""

import pytest

from app.services.uyum_service import uyum_v1_hesapla


def test_tam_uyum_yuzde_100():
    sonuc = uyum_v1_hesapla(
        cv_beceriler=["Python", "FastAPI"],
        gerekli_beceriler=["python", "fastapi"],
        tercih_edilen=[],
    )
    assert sonuc["gerekli_uyum_yuzdesi"] == 100
    # tercih yok -> tercih 0, ağırlıklı: 100*0.7 + 0*0.3 = 70
    assert sonuc["uyum_yuzdesi"] == 70
    assert sonuc["eksik_gerekli_beceriler"] == []


def test_case_ve_bosluk_normalize_edilir():
    sonuc = uyum_v1_hesapla(
        cv_beceriler=["  PyThoN  "],
        gerekli_beceriler=["python"],
        tercih_edilen=[],
    )
    assert sonuc["eslesen_gerekli_beceriler"] == ["python"]
    assert sonuc["gerekli_uyum_yuzdesi"] == 100


def test_kismi_uyum_ve_eksikler():
    sonuc = uyum_v1_hesapla(
        cv_beceriler=["python"],
        gerekli_beceriler=["python", "docker"],
        tercih_edilen=["kubernetes"],
    )
    assert sonuc["gerekli_uyum_yuzdesi"] == 50
    assert sonuc["eksik_gerekli_beceriler"] == ["docker"]
    assert sonuc["tercih_uyum_yuzdesi"] == 0


def test_agirlikli_ortalama_70_30():
    # gerekli %100, tercih %0 -> 70 ; gerekli %0, tercih %100 -> 30
    s1 = uyum_v1_hesapla(["a"], ["a"], ["b"])
    assert s1["uyum_yuzdesi"] == 70
    s2 = uyum_v1_hesapla(["b"], ["a"], ["b"])
    assert s2["uyum_yuzdesi"] == 30


def test_bos_gerekli_bolme_hatasi_yok():
    sonuc = uyum_v1_hesapla(cv_beceriler=["python"], gerekli_beceriler=[], tercih_edilen=[])
    assert sonuc["gerekli_uyum_yuzdesi"] == 0
    assert sonuc["uyum_yuzdesi"] == 0
    # gerekli/tercih olmayan tüm CV becerileri ekstra sayılır
    assert sonuc["ekstra_beceriler"] == ["python"]


def test_ekstra_beceriler_dogru_ayrilir():
    sonuc = uyum_v1_hesapla(
        cv_beceriler=["python", "git", "excel"],
        gerekli_beceriler=["python"],
        tercih_edilen=["git"],
    )
    assert sonuc["ekstra_beceriler"] == ["excel"]


def test_bos_string_beceriler_gormezden_gelinir():
    sonuc = uyum_v1_hesapla(cv_beceriler=["", "  "], gerekli_beceriler=["python"], tercih_edilen=[])
    assert sonuc["gerekli_uyum_yuzdesi"] == 0


@pytest.mark.parametrize(
    "cv,gerekli,beklenen",
    [
        (["a", "b"], ["a", "b", "c", "d"], 50),
        (["a", "b", "c"], ["a", "b", "c"], 100),
        ([], ["a"], 0),
    ],
)
def test_gerekli_uyum_parametrik(cv, gerekli, beklenen):
    assert uyum_v1_hesapla(cv, gerekli, [])["gerekli_uyum_yuzdesi"] == beklenen
