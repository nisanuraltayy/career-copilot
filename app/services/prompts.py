"""LLM prompt şablonları.

Prompt'lar iş mantığından ayrı tutulur: değiştirmek/versiyonlamak,
gözden geçirmek kolaylaşır.
"""


def cv_analiz_prompt(cv_metni: str) -> str:
    return f"""Asagida bir ozgecmis (CV) metni var. Bu CV'den asagidaki bilgileri JSON formatinda cikar:
- beceriler (liste): teknik beceriler, diller, frameworkler, araclar
- deneyimler (liste): pozisyon ve sirket isimleri
- egitim (string): en yuksek egitim seviyesi ve alani

Sadece JSON dondur, baska aciklama ekleme.

CV METNI:
{cv_metni}
"""


def ilan_analiz_prompt(ilan_metni: str) -> str:
    return f"""Asagida bir is ilani metni var. Bu ilandan asagidaki bilgileri JSON formatinda cikar:
- pozisyon_adi (string): orn. "Backend Developer"
- sirket_adi (string ya da null): belirtilmemisse null
- deneyim_yili (string ya da null): orn. "2-3 yil", "junior", "5+ yil". Belirtilmemisse null
- gerekli_beceriler (liste): mutlaka aranan beceriler (must-have)
- tercih_edilen_beceriler (liste): nice-to-have, plus olan beceriler

Sadece JSON dondur, baska aciklama ekleme.

IS ILANI METNI:
{ilan_metni}
"""


def uyum_semantik_prompt(
    cv_beceriler: list, gerekli_beceriler: list, tercih_edilen: list
) -> str:
    return f"""Bir CV ile bir is ilani arasinda semantik uyum analizi yap.

CV BECERILERI:
{cv_beceriler}

IS ILANI GEREKLI BECERILER:
{gerekli_beceriler}

IS ILANI TERCIH EDILEN BECERILER:
{tercih_edilen}

Gorevin:
1. Semantik eslesmeleri bul. Ornek: 'REST API' ile 'REST API tasarimi' aynidir; 'SQL' ile 'PostgreSQL' yakindir.
2. 0-100 arasi bir uyum yuzdesi ver. Sadece kelime degil anlam bazli degerlendir.
3. 2-3 cumlelik bir ozet yaz: kullanici neden bu pozisyona uyumlu/uyumsuz?

Sadece JSON dondur, baska aciklama ekleme. Su formatta:
{{
  "uyum_yuzdesi": <0-100 arasi sayi>,
  "guclu_yonler": ["...", "..."],
  "eksik_yonler": ["...", "..."],
  "ozet": "..."
}}
"""


def motivasyon_mektubu_prompt(
    beceriler: list, deneyimler: list, egitim: str, pozisyon: str,
    sirket: str, gerekli_beceriler: list,
) -> str:
    return f"""Asagidaki bilgilerle profesyonel ve samimi bir motivasyon mektubu yaz.

ADAY BILGILERI:
- Beceriler: {beceriler}
- Deneyimler: {deneyimler}
- Egitim: {egitim}

BASVURULAN POZISYON:
- Pozisyon: {pozisyon}
- Sirket: {sirket}
- Aranan beceriler: {gerekli_beceriler}

KURALLAR:
- Turkce yaz.
- 200-300 kelime arasi olsun.
- "Sayin Yetkili," ile basla.
- 3-4 paragraf.
- Adayin guclu yonlerini one cikar, ama yalan/abartma yapma.
- "Saygilarimla, [Ad Soyad]" ile bitir.
- Sadece mektup metnini dondur, baska aciklama ekleme.
"""
