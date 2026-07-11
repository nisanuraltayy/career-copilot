# Deployment — Career Copilot'u canlıya alma

Bu rehber projeyi **Render** üzerinde ücretsiz katmanla canlıya almayı anlatır.
(Alternatifler için en altta Railway/Fly notları var.)

> **Ben (asistan) neyi yapamam:** cloud platformunda hesap açmak, giriş yapmak
> veya "Deploy" düğmesine basmak — bunlar senin hesabınla senin yapman gereken
> adımlar. Tüm **config ve dosyaları** hazırladım; aşağıdaki adımlar tıklamalık.

---

## Yerel vs. cloud topolojisi (önemli fark)

Lokalde `docker compose` üç servisi tek ağda çalıştırır ve nginx `/api`'yi
`app:8000`'e proxy'ler. Cloud'da servisler **ayrı** yaşar; bu yüzden:

- **Backend** ve **DB** birlikte (Render Blueprint — `render.yaml`).
- **Frontend** ayrı bir **Static Site**; backend'e **public URL + CORS** ile
  konuşur (nginx proxy yerine). Kod bunu zaten destekliyor (`VITE_API_URL`).

```
[Static Site: frontend]  ──HTTPS + CORS──▶  [Web Service: backend]  ──▶  [Postgres+pgvector]
   VITE_API_URL=backend URL                    CORS_ORIGINS=frontend URL
```

---

## 1) Backend + veritabanı (Render Blueprint)

1. [dashboard.render.com](https://dashboard.render.com) → **New → Blueprint**.
2. Backend repo'sunu (`career-copilot`) seç. Render `render.yaml`'i okur:
   Postgres (pgvector) + Docker web service oluşturur.
3. **Apply**. Render soracağı gizli değerler:
   - `GEMINI_API_KEY` → Google Gemini anahtarın.
   - `CORS_ORIGINS` → şimdilik boş bırak; frontend URL'ini adım 2'den sonra gir.
   - `JWT_SECRET` → Render otomatik güçlü değer üretir (elle girme).
4. Deploy bitince backend URL'in olur: `https://career-copilot-api.onrender.com`.
   - Migration'lar (pgvector extension + tablolar) **otomatik** uygulanır.
   - Doğrula: `https://<backend>/saglik` → `{"durum":"iyi",...}`.

> pgvector: Render managed Postgres `CREATE EXTENSION vector`'ü destekler;
> migration bunu ilk açılışta çalıştırır. 3072 boyutta ANN index kurulmaz
> (bkz. README) — küçük/orta veri için sorun değil.

## 2) Frontend (Render Static Site)

1. **New → Static Site** → frontend repo'sunu (`career-copilot-frontend`) seç.
2. Ayarlar:
   - **Build Command:** `npm ci && npm run build`
   - **Publish Directory:** `dist`
   - **Environment Variable:** `VITE_API_URL = https://career-copilot-api.onrender.com`
     (adım 1'deki backend URL'i — build sırasında bundle'a gömülür).
3. **Redirects/Rewrites** sekmesine bir kural ekle (SPA yönlendirmesi için):
   - Source `/*` · Destination `/index.html` · Action **Rewrite**.
4. Deploy bitince frontend URL'in olur: `https://career-copilot-frontend.onrender.com`.

## 3) İki servisi bağla (CORS)

1. Backend servisinin **Environment** ayarlarına dön.
2. `CORS_ORIGINS` = frontend URL'in (örn. `https://career-copilot-frontend.onrender.com`).
3. Backend'i **Manual Deploy → Clear cache & deploy** ile yeniden başlat.
4. Frontend URL'ini aç → kayıt ol → kullan. 🎉

---

## Production kontrol listesi

- [x] `ENVIRONMENT=production` → `/docs` kapalı, güvensiz JWT_SECRET reddedilir
- [x] `JWT_SECRET` güçlü ve gizli (Render üretir)
- [x] `GEMINI_API_KEY` gizli env (repoda değil)
- [x] `CORS_ORIGINS` yalnızca frontend origin'i
- [x] HTTPS (Render otomatik sağlar)
- [x] `DATABASE_URL` normalize edilir (`postgres://` → `postgresql://`)
- [x] `PORT` platformdan okunur (Dockerfile `${PORT:-8000}`)
- [ ] (Öneri) Rate limit için çok-instance'ta Redis storage
- [ ] (Öneri) Hata izleme (Sentry) ve uptime monitoring

## Ortam değişkenleri (özet)

| Değişken | Backend | Değer |
|----------|:------:|-------|
| `DATABASE_URL` | ✓ | Render DB'den otomatik |
| `GEMINI_API_KEY` | ✓ | gizli |
| `JWT_SECRET` | ✓ | Render üretir |
| `ENVIRONMENT` | ✓ | `production` |
| `CORS_ORIGINS` | ✓ | frontend URL'i |
| `VITE_API_URL` | frontend | backend URL'i (build-time) |

---

## Alternatifler (kısa)

- **Railway:** Repo bağla → Postgres eklentisi (pgvector için `pgvector/pgvector`
  imajı) → backend Docker servis + frontend. Servisler arası private networking
  var; env'ler benzer.
- **Fly.io:** `fly launch` (Docker'ı algılar) + `fly postgres create` (pgvector
  için imaj/extension). Backend ve frontend ayrı app'ler; `VITE_API_URL` + CORS.
- **Tek VPS + docker-compose:** Bu repodaki `docker-compose.yml` bir sunucuda
  (DigitalOcean/Hetzner) olduğu gibi çalışır; önüne bir reverse proxy (Caddy/
  Traefik) + TLS koy. En çok kontrol, en çok bakım.
