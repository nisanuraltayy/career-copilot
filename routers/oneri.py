from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db, CVKaydi, IsIlani

router = APIRouter()


@router.get("/is-onerileri/{cv_id}")
def is_onerileri(
    cv_id: int,
    limit: int = 5,
    db: Session = Depends(get_db),
):
    # 1. CV var mi ve embedding'i var mi kontrol et
    cv = db.query(CVKaydi).filter(CVKaydi.id == cv_id).first()
    if cv is None:
        raise HTTPException(status_code=404, detail=f"CV bulunamadi (id={cv_id})")
    if cv.embedding is None:
        raise HTTPException(
            status_code=400,
            detail=f"Bu CV'nin embedding'i yok, oneri hesaplanamaz (id={cv_id})",
        )

    # 2. pgvector cosine distance (<=>) ile en yakin ilanlari DB'de sirala.
    #    Hesap veri katmaninda yapilir, tum vektorler Python'a cekilmez.
    #    Sadece embedding'i olan ilanlar dikkate alinir.
    sonuclar = (
        db.query(
            IsIlani,
            IsIlani.embedding.cosine_distance(cv.embedding).label("uzaklik"),
        )
        .filter(IsIlani.embedding.isnot(None))
        .order_by("uzaklik")
        .limit(limit)
        .all()
    )


    oneriler = []
    for ilan, uzaklik in sonuclar:
        benzerlik = 1 - uzaklik
        oneriler.append({
            "ilan_id": ilan.id,
            "pozisyon_adi": ilan.pozisyon_adi,
            "sirket_adi": ilan.sirket_adi,
            "deneyim_yili": ilan.deneyim_yili,
            "uyum_skoru": round(benzerlik * 100, 1),
            "uzaklik": round(uzaklik, 4),
        })

    return {
        "cv_id": cv_id,
        "cv_dosya_adi": cv.dosya_adi,
        "toplam_oneri": len(oneriler),
        "oneriler": oneriler,
    }