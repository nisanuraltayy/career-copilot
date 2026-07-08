# Career Copilot

İş arayanlar için yapay zeka destekli bir kariyer asistanı. Yüklenen CV'yi analiz edip becerilere ayırır, iş ilanlarıyla uyumunu yüzdelik olarak hesaplar, en uygun ilanları önerir ve seçilen ilana özel motivasyon mektubu yazar.

Bu depo projenin **backend** (API) tarafını içerir. Frontend ayrı bir depoda: [career-copilot-frontend](https://github.com/nisanuraltayy/career-copilot-frontend).

## Ne İşe Yarar?

Career Copilot dört temel işi yapar:

1. **CV Analizi** — Yüklenen PDF CV'yi Gemini ile analiz eder; becerileri, deneyimleri ve eğitimi yapılandırılmış bir formata ayırır.
2. **Uyum Analizi** — Bir CV ile bir iş ilanı arasındaki uyumu hesaplar. Hibrit yaklaşım kullanır: V1 kelime eşleştirme (deterministik) + V2 LLM tabanlı anlamsal analiz.
3. **İş Önerileri** — Bir CV'ye en uygun iş ilanlarını, anlamsal benzerliğe göre sıralayarak önerir. pgvector ile vektör benzerliği (cosine distance) üzerinden çalışır.
4. **Motivasyon Mektubu** — Seçilen CV ve ilana özel, kişiselleştirilmiş bir motivasyon mektubu üretir.

## Teknoloji Yığını

- **FastAPI** — Web framework (Python)
- **PostgreSQL + pgvector** — Veritabanı ve vektör benzerlik araması
- **Google Gemini** — LLM (analiz, mektup üretimi) ve embedding (gemini-embedding-001, 3072 boyut)
- **SQLAlchemy** — ORM
- **Docker** — pgvector'lü PostgreSQL'i lokal çalıştırmak için

## Mimari

Proje modüler bir yapıda organize edilmiştir. Sorumluluklar ayrılmıştır (separation of concerns):

```
career-copilot/
├── main.py                  # FastAPI uygulaması, router kayıtları, CORS
├── database.py              # SQLAlchemy modelleri, DB bağlantısı
├── routers/
│   ├── cv.py                # CV yükleme ve analiz endpoint'leri
│   ├── ilan.py              # İş ilanı ekleme ve analiz endpoint'leri
│   ├── uyum.py              # Uyum analizi endpoint'leri
│   ├── mektup.py            # Motivasyon mektubu endpoint'leri
│   └── oneri.py             # İş önerisi endpoint'i (pgvector)
└── services/
    └── gemini_service.py    # Gemini API çağrıları (analiz, mektup, embedding)
```

### Veritabanı Modelleri

Dört tablo:

- `cv_kayitlari` — CV analizleri (+ embedding vektörü)
- `is_ilanlari` — İş ilanı analizleri (+ embedding vektörü)
- `uyum_analizleri` — V1 ve V2 uyum sonuçları
- `motivasyon_mektuplari` — Üretilen mektuplar

CV ve ilan tablolarında `Vector(3072)` tipinde bir `embedding` kolonu vardır. Bu kolon nullable'dır: embedding üretimi başarısız olsa bile (örneğin Gemini API geçici olarak yanıt vermezse) kayıt yine de saklanabilir (graceful degradation).

### Embedding ve Öneri Akışı

Bir CV veya ilan eklendiğinde:

1. Gemini metni analiz eder (JSON).
2. Analiz JSON'undan temiz bir metin oluşturulur.
3. Bu metin `gemini-embedding-001` ile 3072 boyutlu vektöre çevrilir.
4. Vektör, kaydın `embedding` kolonuna yazılır.

Embedding neden ham metinden değil, analiz JSON'undan üretilir? İki sebep: (1) `gemini-embedding-001`'in girdi limiti 2048 token — uzun CV'ler bunu aşabilir; (2) analiz JSON'u gürültüsüz ve öz, CV ile ilan aynı formatta karşılaştırılır.

Öneri hesaplaması pgvector'ün cosine distance operatörü (`<=>`) ile **veritabanı katmanında** yapılır. Tüm vektörler Python'a çekilip döngüyle karşılaştırılmaz; bu yaklaşım ölçeklenebilir.

## Kurulum (Lokal)

### Gereksinimler

- Python 3.11+
- Docker
- Google Gemini API anahtarı

### Adımlar

1. Depoyu klonlayın:
   ```bash
   git clone https://github.com/nisanuraltayy/career-copilot.git
   cd career-copilot
   ```

2. Sanal ortam oluşturun ve bağımlılıkları kurun:
   ```bash
   python -m venv venv
   venv\Scripts\activate        # Windows
   # source venv/bin/activate   # macOS/Linux
   pip install -r requirements.txt
   ```

3. `.env` dosyası oluşturun:
   ```
   DATABASE_URL=postgresql://raguser:ragpass123@localhost:5432/careerdb
   GEMINI_API_KEY=buraya_kendi_anahtariniz
   ```

4. pgvector'lü PostgreSQL'i Docker ile başlatın:
   ```bash
   docker run -d --name rag-postgres \
     -e POSTGRES_USER=raguser \
     -e POSTGRES_PASSWORD=ragpass123 \
     -e POSTGRES_DB=careerdb \
     -p 5432:5432 \
     pgvector/pgvector:pg16
   ```

5. Veritabanında pgvector extension'ını etkinleştirin:
   ```bash
   docker exec -it rag-postgres psql -U raguser -d careerdb -c "CREATE EXTENSION IF NOT EXISTS vector;"
   ```

6. Uygulamayı başlatın (tablolar otomatik oluşur):
   ```bash
   uvicorn main:app --reload
   ```

API `http://127.0.0.1:8000` adresinde çalışır. İnteraktif dokümantasyon: `http://127.0.0.1:8000/docs`.

## Endpoint'ler

| Metod | Yol | Açıklama |
|-------|-----|----------|
| GET | `/` | Ana sayfa (sağlık mesajı) |
| GET | `/saglik` | Sağlık kontrolü |
| POST | `/cv-yukle` | PDF CV yükle ve analiz et |
| GET | `/cv-gecmis` | Yüklenen CV'leri listele |
| POST | `/is-ilani-analiz` | İş ilanı ekle ve analiz et |
| GET | `/is-ilanlari` | Eklenen ilanları listele |
| POST | `/uyum-analizi` | CV-ilan uyumunu hesapla (V1 + V2) |
| GET | `/uyum-analizi-gecmis` | Geçmiş uyum analizleri |
| POST | `/motivasyon-mektubu` | Motivasyon mektubu üret |
| GET | `/motivasyon-mektubu-gecmis` | Geçmiş mektuplar |
| GET | `/is-onerileri/{cv_id}` | Bir CV'ye en uygun ilanları öner (pgvector) |

## Öne Çıkan Teknik Kararlar

- **Hibrit uyum analizi:** V1 (deterministik kelime eşleştirme) her zaman çalışır; V2 (LLM anlamsal analiz) patlarsa V1 yine sonuç döner (graceful degradation).
- **pgvector vektör araması:** Benzerlik hesabı uygulama katmanında değil, veritabanında yapılır.
- **Modüler router yapısı:** Her özellik kendi router dosyasında, `main.py` sade tutulur.
- **CORS whitelist:** Wildcard (`*`) yerine yalnızca frontend origin'lerine izin verilir.
- **Idempotent tablo oluşturma:** `Base.metadata.create_all` ile tablolar varsa dokunulmaz.

---

*Bu proje, junior backend developer yolunda geliştirilen bir öğrenme ve portfolyo projesidir.*
