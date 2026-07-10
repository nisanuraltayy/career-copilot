"""PDF metin çıkarma servisi testleri."""

from pathlib import Path

import pytest

from app.core.exceptions import ValidationFailed
from app.services.pdf import pdf_metin_cikar

FIXTURE = Path(__file__).parent / "fixtures" / "ornek_cv.pdf"


def test_gecersiz_pdf_validation_failed():
    with pytest.raises(ValidationFailed):
        pdf_metin_cikar(b"bu bir pdf degil")


def test_bos_bytes_validation_failed():
    with pytest.raises(ValidationFailed):
        pdf_metin_cikar(b"")


def test_gecerli_pdf_metin_cikar():
    sonuc = pdf_metin_cikar(FIXTURE.read_bytes())
    assert sonuc.sayfa_sayisi == 1
    assert "Backend" in sonuc.metin
    assert len(sonuc.metin.strip()) > 0
