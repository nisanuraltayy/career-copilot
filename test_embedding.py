from services.gemini_service import gemini_embedding_uret

vektor = gemini_embedding_uret("Python backend developer, FastAPI ve PostgreSQL deneyimi")

if vektor is None:
    print("HATA: embedding None dondu (API cagrisinda sorun var)")
else:
    print(f"Embedding uzunlugu: {len(vektor)}")
    print(f"Ilk 5 deger: {vektor[:5]}")
    print(f"3072 mi? {'EVET' if len(vektor) == 3072 else 'HAYIR: ' + str(len(vektor))}")