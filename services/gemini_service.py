import os
import json
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()
_client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))


def gemini_json_uret(prompt: str, model: str = "gemini-flash-latest") -> dict:
    """Gemini'ye prompt gonder, JSON cevap al, Python dict olarak don.
    Markdown fence (```json ... ```) varsa otomatik temizler.
    JSON parse edilemezse ValueError firlatir.
    """
    yanit = _client.models.generate_content(model=model, contents=prompt)
    cevap_metni = yanit.text.strip()
    if cevap_metni.startswith("```json"):
        cevap_metni = cevap_metni.removeprefix("```json").removesuffix("```").strip()
    elif cevap_metni.startswith("```"):
        cevap_metni = cevap_metni.removeprefix("```").removesuffix("```").strip()
    return json.loads(cevap_metni)


def gemini_metin_uret(prompt: str, model: str = "gemini-flash-latest") -> str:
    """Gemini'ye prompt gonder, duz metin cevap al, string olarak don."""
    yanit = _client.models.generate_content(model=model, contents=prompt)
    return yanit.text.strip()


def gemini_embedding_uret(metin: str, gorev_tipi: str = "RETRIEVAL_DOCUMENT") -> list[float] | None:
    """Verilen metni gemini-embedding-001 ile 3072 boyutlu vektore cevirir.

    gorev_tipi:
        RETRIEVAL_DOCUMENT -> saklanan belgeler icin (CV, ilan)
        RETRIEVAL_QUERY    -> arama sorgusu icin
    output_dimensionality=3072 acikca yaziliyor: DB kolonumuz Vector(3072),
    kod ile schema arasindaki kontrat gorunur olsun diye.

    Basarisiz olursa None doner (graceful degradation). Cagiran taraf
    embedding'siz de kaydedebilir, cunku embedding kolonu nullable.
    """
    try:
        yanit = _client.models.embed_content(
            model="gemini-embedding-001",
            contents=metin,
            config=types.EmbedContentConfig(
                task_type=gorev_tipi,
                output_dimensionality=3072,
            ),
        )
        return yanit.embeddings[0].values
    except Exception as hata:
        print(f"[embedding hatasi] {hata}")
        return None