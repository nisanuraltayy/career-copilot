import os
import json
from google import genai
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