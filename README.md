<div align="center">

# 🎯 Career Copilot

**Yapay zekâ destekli kariyer asistanı — backend API**

CV'yi analiz eder, iş ilanlarıyla uyumunu ölçer, en uygun ilanları önerir ve kişiye özel motivasyon mektubu üretir.

[![CI](https://github.com/nisanuraltayy/career-copilot/actions/workflows/ci.yml/badge.svg)](https://github.com/nisanuraltayy/career-copilot/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.11%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.136-009688)
![Postgres](https://img.shields.io/badge/PostgreSQL-pgvector-336791)
![License](https://img.shields.io/badge/license-MIT-green)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com/deploy?repo=https://github.com/nisanuraltayy/career-copilot)

**🌐 Canlı demo:** [career-copilot-frontend-3ntf.onrender.com](https://career-copilot-frontend-3ntf.onrender.com) · **API:** [career-copilot-api-p5fs.onrender.com](https://career-copilot-api-p5fs.onrender.com/docs)

<sub>Ücretsiz Render katmanında çalışır — 15 dk hareketsizlikte uyur, ilk istek ~50 sn sürebilir. Düğme backend + pgvector'lü Postgres'i kurar (blueprint: `render.yaml`); tam deploy rehberi: [DEPLOYMENT.md](DEPLOYMENT.md).</sub>

</div>

---

## İçindekiler

- [Genel Bakış](#genel-bakış)
- [Özellikler](#özellikler)
- [Teknoloji Yığını](#teknoloji-yığını)
- [Mimari](#mimari)
- [Hızlı Başlangıç (Docker)](#hızlı-başlangıç-docker)
- [Manuel Kurulum](#manuel-kurulum)
- [Veritabanı Migration'ları](#veritabanı-migrationları)
- [Testler](#testler)
- [API Referansı](#api-referansı)
- [Yapılandırma](#yapılandırma)
- [Deployment](#deployment)
- [Öne Çıkan Teknik Kararlar](#öne-çıkan-teknik-kararlar)

---

## Genel Bakış

Career Copilot, iş arayan bir kullanıcının CV'sini yükleyip yapay zekâ ile analiz eden, ardından bu analizi iş ilanlarıyla eşleştirerek somut kariyer içgörüleri üreten bir REST API'dir. Bu depo projenin **backend** tarafını içerir; frontend ayrı bir depodadır: [career-copilot-frontend](https://github.com/nisanuraltayy/career-copilot-frontend).

## Özellikler

| Özellik | Açıklama |
|--------|----------|
| 📄 **CV Analizi** | PDF CV'yi Gemini ile analiz eder; beceri, deneyim ve eğitimi yapılandırılmış JSON'a ayırır. |
| 🎯 **Uyum Analizi** | CV ↔ ilan uyumunu hibrit hesaplar: **V1** deterministik kelime eşleştirme + **V2** LLM semantik analiz. |
| 🔎 **İş Önerileri** | CV'ye en yakın ilanları **pgvector** cosine distance ile veritabanı katmanında sıralar. |
| ✍️ **Motivasyon Mektubu** | Seçilen CV ve ilana özel, kişiselleştirilmiş mektup üretir. |

## Teknoloji Yığını

- **FastAPI** — asenkron web framework
- **PostgreSQL + pgvector** — ilişkisel veri + vektör benzerlik araması
- **SQLAlchemy 2.0** — tip güvenli ORM
- **Alembic** — versiyonlanmış veritabanı migration'ları
- **Google Gemini** — LLM analiz/üretim + `gemini-embedding-001` (3072 boyut) embedding
- **Pydantic v2 / pydantic-settings** — şema doğrulama ve yapılandırma
- **pytest + ruff** — test ve statik analiz
- **Docker / docker-compose** — container'lı çalıştırma

## Mimari

Proje **katmanlı (layered) mimari** ile tasarlanmıştır. Her katmanın tek bir sorumluluğu vardır ve bağımlılıklar tek yönlüdür: `router → service → db`. HTTP detayları iş mantığına, iş mantığı da HTTP'ye sızmaz.

```
app/
├── main.py                 # Uygulama fabrikası (create_app), middleware, router kaydı
├── core/
│   ├── config.py           # Pydantic Settings — tek yapılandırma kaynağı (fail-fast)
│   ├── logging.py          # Yapılandırılmış logging (dev: metin, prod: JSON)
│   └── exceptions.py       # Hata hiyerarşisi + merkezi exception handler'lar
├── db/
│   ├── base.py             # Declarative Base, TimestampMixin (tz-aware)
│   ├── session.py          # Engine, SessionLocal, get_db (pool + pre_ping)
│   └── models.py           # ORM modelleri (ForeignKey, ilişkiler, index'ler)
├── schemas/                # Pydantic request/response modelleri (I/O kontratı)
├── services/               # ── İş mantığı katmanı ──
│   ├── gemini.py           #   Gemini istemci sarmalayıcısı (sağlayıcıdan bağımsız)
│   ├── pdf.py              #   PDF metin çıkarma
│   ├── prompts.py          #   LLM prompt şablonları
│   ├── cv_service.py       #   CV: PDF → analiz → embedding → kayıt
│   ├── ilan_service.py     #   İlan iş mantığı
│   ├── uyum_service.py     #   V1 (pure) + V2 (LLM) uyum hesabı
│   ├── mektup_service.py   #   Mektup üretimi
│   └── oneri_service.py    #   pgvector vektör araması
└── routers/                # İnce HTTP katmanı (validasyon + service çağrısı)

alembic/                    # Migration'lar (create_all yerine)
tests/                      # pytest suite (birim + API, DB/API'ye vurmadan)
```

### Katmanların sorumluluğu

- **Router** — sadece HTTP: girdi doğrulama, servis çağırma, `response_model` ile yanıt. İş kararı vermez.
- **Service** — tüm iş mantığı ve DB erişimi. HTTP'den habersizdir; anlamlı domain hataları (`ResourceNotFound`, `UpstreamServiceError` …) fırlatır.
- **Schema** — API'nin dış kontratı; iç modelden ayrıdır, böylece DB şeması değişse de API stabil kalır.

### İş İlanı / CV ekleme akışı

```
İstek → Router (doğrula) → Service → [Gemini analiz] → [analiz JSON'undan embedding metni]
      → [Gemini embedding] → DB kaydı → response_model → JSON yanıt
```

Embedding **ham metinden değil, analiz JSON'undan** üretilir. İki sebep: (1) `gemini-embedding-001`'in girdi limiti ~2048 token, uzun CV'ler bunu aşar; (2) analiz JSON'u gürültüsüzdür ve CV ile ilan **aynı formatta** karşılaştırılır.

Embedding üretimi başarısız olursa kayıt yine de saklanır (`embedding` kolonu nullable) — **graceful degradation**.

## Hızlı Başlangıç (Docker)

Tek komutla **tam yığın** ayağa kalkar: frontend (nginx) + backend + pgvector'lü PostgreSQL. Migration'lar otomatik uygulanır; frontend `/api`'yi backend'e proxy'ler (CORS gerekmez).

> Frontend ayrı repodadır; iki repo **kardeş klasörlerde** olmalı (`career-copilot/` ve `career-copilot-frontend/`).

```bash
git clone https://github.com/nisanuraltayy/career-copilot.git
cd career-copilot
cp .env.example .env          # GEMINI_API_KEY ve JWT_SECRET doldurun
docker compose up --build
```

- Uygulama (frontend): <http://localhost:5173>
- Backend API: <http://localhost:9000>  · Swagger: <http://localhost:9000/docs>

> **Güçlü JWT_SECRET üret:** `python -c "import secrets; print(secrets.token_urlsafe(48))"`

## Manuel Kurulum

<details>
<summary>Docker olmadan lokal geliştirme</summary>

**Gereksinimler:** Python 3.11+, çalışan bir PostgreSQL (pgvector eklentili), Gemini API anahtarı.

```bash
# 1) Sanal ortam + bağımlılıklar
python -m venv venv
venv\Scripts\activate            # Windows
# source venv/bin/activate       # macOS/Linux
pip install -r requirements-dev.txt

# 2) .env oluştur
cp .env.example .env             # değerleri doldur

# 3) pgvector'lü Postgres (Docker ile tek container)
docker run -d --name rag-postgres \
  -e POSTGRES_USER=raguser -e POSTGRES_PASSWORD=ragpass123 -e POSTGRES_DB=careerdb \
  -p 5432:5432 pgvector/pgvector:pg16

# 4) Şemayı oluştur (migration)
alembic upgrade head

# 5) Çalıştır
uvicorn app.main:app --reload
```

</details>

## Veritabanı Migration'ları

Şema `create_all` ile değil **Alembic** ile yönetilir; her değişiklik versiyonlanır ve geri alınabilir.

```bash
alembic upgrade head                        # en son şemaya getir
alembic downgrade -1                         # bir adım geri al
alembic revision --autogenerate -m "mesaj"   # model değişiminden yeni migration üret
```

> **Not (vektör index'i):** `gemini-embedding-001` 3072 boyut üretir. pgvector'ün ANN index'leri (ivfflat/hnsw) **en fazla 2000 boyut** destekler; bu yüzden 3072'de arama *exact scan* yapar (küçük/orta veri için yeterli). Ölçek gerekince `EMBEDDING_DIM` 1536'ya düşürülüp bir HNSW index migration'ı eklenebilir — kod bu değişime tek noktadan hazırdır (`app/core/config.py`).

## Testler

Testler **gerçek veritabanına veya Gemini API'sine vurmaz** — DB sahte session ile, servisler monkeypatch ile izole edilir. Bu sayede CI'da hızlı ve deterministiktir.

```bash
pytest                 # tüm suite
pytest --cov           # coverage raporu ile
ruff check app tests   # statik analiz
```

**97 test · %88 coverage.** Kapsam: V1 uyum skoru (parametrik), embedding metin kurucular, Gemini JSON temizleme/hata soyutlama, PDF çıkarma, auth (register/login/refresh/parola değiştirme, gerçek SQLite entegrasyon testleri dahil), rate limiting, request-ID middleware, ve tüm endpoint'lerin başarı + hata (401/404/400/422/502/503) yolları.

## API Referansı

🔒 = `Authorization: Bearer <token>` gerektirir. Kaynaklar **kullanıcıya özeldir** (multi-tenant): her kullanıcı yalnızca kendi CV/ilan/analiz/mektuplarını görür.

| Metod | Yol | Açıklama |
|-------|-----|----------|
| GET | `/` | Kök — servis durumu |
| GET | `/saglik` | Liveness (süreç ayakta mı?) |
| GET | `/hazir` | Readiness (DB dahil bağımlılıklar hazır mı?) |
| POST | `/auth/register` | Kayıt ol → access + refresh token |
| POST | `/auth/login` | Giriş yap → access + refresh token |
| POST | `/auth/refresh` | Refresh token ile yeni token çifti al (rotasyon) |
| POST | `/auth/change-password` 🔒 | Parola değiştir (eski parola doğrulanır) |
| GET | `/auth/me` 🔒 | Mevcut kullanıcı |
| POST | `/cv-yukle` 🔒 | PDF CV yükle ve analiz et |
| GET | `/cv-gecmis` 🔒 | Yüklenen CV'leri listele (limit/offset) |
| POST | `/is-ilani-analiz` 🔒 | İş ilanı ekle ve analiz et |
| GET | `/is-ilanlari` 🔒 | Eklenen ilanları listele (limit/offset) |
| POST | `/uyum-analizi` 🔒 | CV–ilan uyumunu hesapla (V1 + V2) |
| GET | `/uyum-analizi-gecmis` 🔒 | Geçmiş uyum analizleri |
| POST | `/motivasyon-mektubu` 🔒 | Motivasyon mektubu üret |
| GET | `/motivasyon-mektubu-gecmis` 🔒 | Geçmiş mektuplar |
| GET | `/is-onerileri/{cv_id}` 🔒 | Bir CV'ye en uygun ilanları öner (pgvector) |

> AI endpoint'leri IP başına **rate limit**'lidir (varsayılan 20/dakika). Her yanıtta korelasyon için `X-Request-ID` başlığı döner.

**Tutarlı hata formatı** — tüm hatalar aynı gövdeyle döner, teknik detay client'a sızmaz:

```json
{ "error": { "code": "not_found", "message": "CV bulunamadı (id=99)." } }
```

## Yapılandırma

Tüm ayarlar `app/core/config.py`'de tek yerde, tip güvenli tanımlanır ve `.env`'den okunur. Öne çıkanlar:

| Değişken | Varsayılan | Açıklama |
|----------|-----------|----------|
| `DATABASE_URL` | — (zorunlu) | PostgreSQL bağlantı adresi |
| `GEMINI_API_KEY` | — (zorunlu) | Google Gemini API anahtarı |
| `ENVIRONMENT` | `development` | `production`'da `/docs` kapanır |
| `JWT_SECRET` | dev default | Token imzalama anahtarı — **production'da zorunlu** (fail-fast) |
| `JWT_EXPIRE_MINUTES` | `60` | Access token ömrü (kısa) |
| `JWT_REFRESH_EXPIRE_MINUTES` | `43200` (30 gün) | Refresh token ömrü |
| `RATE_LIMIT_AI` | `20/minute` | AI endpoint'leri için IP başına limit |
| `LOG_JSON` | `false` | Log agregasyonu için JSON log |
| `CORS_ORIGINS` | localhost:5173 | Virgülle ayrılmış izinli origin'ler |
| `EMBEDDING_DIM` | `3072` | Embedding boyutu (bkz. vektör index notu) |
| `MAX_UPLOAD_BYTES` | `10485760` | Yükleme boyut limiti (10 MB) |

## Deployment

Proje [Render](https://render.com)'da **ücretsiz katmanda** canlıdır (backend + frontend + pgvector'lü Postgres). Kendi kopyanı deploy etmek için:

1. Yukarıdaki **Deploy to Render** düğmesine tıkla → `render.yaml` blueprint'i backend + veritabanını otomatik kurar.
2. Frontend'i ayrı bir **Static Site** olarak deploy et, `VITE_API_URL`'i backend URL'ine ayarla.
3. Backend'in `CORS_ORIGINS`'ini frontend URL'i ile güncelle.

Adım adım detaylar, ortam değişkenleri ve alternatif platformlar (Railway, Fly.io, VPS) için: **[DEPLOYMENT.md](DEPLOYMENT.md)**.

## Öne Çıkan Teknik Kararlar

- **Katmanlı mimari** — router/service/schema/db ayrımı; iş mantığı HTTP'den bağımsız, birim test edilebilir (saf fonksiyonlar).
- **JWT auth + multi-tenancy** — bcrypt parola hash'i, kısa ömürlü access + uzun ömürlü refresh token ayrımı (`type` claim'i ile birbirinin yerine kullanılamaz), token rotasyonu. Her kaynak `user_id`'ye bağlı ve sorgular kullanıcıya göre kapsanır (bir kullanıcı diğerinin verisini göremez). `app/core/security.py`, `app/core/deps.py`.
- **Rate limiting + gözlemlenebilirlik** — AI endpoint'lerinde IP başına limit (slowapi); her istek için `X-Request-ID` korelasyon kimliği loglara ve yanıta işlenir; güvenlik başlıkları.
- **Merkezî hata yönetimi** — servisler domain hatası fırlatır, tek handler HTTP'ye çevirir. Tutarlı `{error: {code, message}}` gövdesi; stack trace asla sızmaz.
- **Geçici hatalara dayanıklılık (retry + model fallback)** — Google yoğun trafikte `503 UNAVAILABLE` / `429` döndürebilir. AI istemcisi bu **geçici** hataları üstel geri çekilme + jitter ile 5 kez yeniden dener; birincil model hâlâ müsait değilse **yedek model zincirine** düşer (`gemini-2.5-flash` → `gemini-2.0-flash` → `gemini-2.5-flash-lite`); ancak tüm zincir tükenirse **HTTP 503** döner. Kalıcı hatalar (4xx, geçersiz yanıt) ise beklemeden **502** olur. Kod haritası: `app/services/gemini.py` (`_generate`, `_retry_ile_cagir`, `_model_zinciri`).
- **Pinlenmiş üretim modeli + bounded çıktı** — Kayan `-latest` alias'ı yerine kararlı GA modeli `gemini-2.5-flash` kullanılır. Serbest metin üretimi (mektup) `max_output_tokens` ve istek timeout'u ile sınırlıdır; böylece en pahalı çağrı bile yük altında öngörülebilir kalır (mektup 503'ünün kök nedeni buydu).
- **Alembic migration'ları** — versiyonlu, geri alınabilir şema; production'da `create_all` yok.
- **Referans bütünlüğü** — `ForeignKey` + `ON DELETE CASCADE` ve indexli FK kolonları.
- **Hibrit uyum analizi** — V1 (deterministik) her zaman çalışır; V2 (LLM) patlarsa V1'e düşer (graceful degradation).
- **DB-katmanında vektör araması** — benzerlik hesabı Python'a çekilmeden pgvector `<=>` ile yapılır; ölçeklenebilir.
- **12-factor config** — ayarlar env'den, fail-fast doğrulama ile; sağlayıcı sarmalayıcısı (Gemini) sayesinde LLM sağlayıcısı tek dosyadan değişir.
- **Gözlemlenebilirlik** — yapılandırılmış logging, `/saglik` (liveness) ve `/hazir` (readiness) probe'ları, Docker `HEALTHCHECK`.
- **Güvenli container** — çok aşamalı (multi-stage) build, root olmayan kullanıcı, ince runtime imajı.
- **Tam yığın Docker** — tek `docker compose up` ile frontend (nginx, `/api` reverse proxy → CORS'suz), backend ve pgvector birlikte ayağa kalkar.

---

<div align="center">
<sub>MIT lisansı · Senior backend pratiklerini sergilemek için geliştirilmiş portfolyo projesi</sub>
</div>
