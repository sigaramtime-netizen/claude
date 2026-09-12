# F6 — Son Cila (Bildirim API + Yetki CSV + Yazdırma + Şube Özeti) · Faz Özeti (v1.38.0)

Tarih: 2026-09-12 · Paket: F6 (D006) · Kapsam: Faz 1–5 sonrası kalan son eksikler —
bildirim API, yetki matrisi CSV, ortak yazdırma şablonu, şube özet API ve sağlık API.

Kural (GM onaylı):
- **YENİ TABLO YOK / MIGRATION YOK**; harici PDF kütüphanesi **YOK** (sade HTML print).
- K1: bildirimler + şube özeti `sirket_id` ile süzülür; `izole_sube` korunur.
- `/yetkiler/csv` yalnız Admin (Depo 403); `/api/bildirimler`, `/api/sube/ozet`,
  `/api/saglik`, `/x/<id>/yazdir` giriş yapmış herkes (K1/şube izolasyonu korunur).

---

## 1) Veri Modeli Özeti

Değişiklik yok. Salt-okunur cila mevcut tablolar üzerinden:

| Kaynak | Kullanım |
|---|---|
| `bildirimler` | `/api/bildirimler` (tip/okundu filtre, K1, limit 50) |
| `fatura` / `irsaliye` / `siparis` | ortak yazdırma + şube özet sayıları |
| `sube` + `kasa` | `/api/sube/ozet` (kasa_bakiye = o şubedeki kasaların toplamı) |
| `core.ROUTES` | yetki CSV (DB'ye dokunmaz) |

### İş kuralları
1. Yazdırma: `yazdir_belge(r, kalemler, no_key, tip_label)` 3 belgeyi ortak şablona
   normalize eder; başka şubeye ait belge 403 (`sube_koruma`).
2. `/api/saglik` → `{durum, surum, tarih, db, sirket_id}` (mevcut `/saglik` korunur).

---

## 2) Ekran Listesi (etkilenen)

| Rota | Etki |
|---|---|
| `GET /api/bildirimler` | JSON bildirim listesi (tip/okundu filtre) |
| `GET /yetkiler/csv` | `;` ayraçlı yetki matrisi (yalnız Admin) |
| `GET /fatura\|irsaliye\|siparis/<id>/yazdir` | ortak `yazdir/belge.html` (@media print) |
| `GET /api/sube/ozet` | şube → fatura_adet, irsaliye_adet, kasa_bakiye |
| `GET /api/saglik` | sağlık durumu |
| `GET /sube` | belge rozetleri sütunu |

---

## 3) Örnek Test Senaryosu (e2e — `test_f6_cila.py`, 18 kontrol)

1. `/api/bildirimler` 6 alan (id,tip,baslik,mesaj,okundu,tarih) + tip/okundu filtreleri + K1.
2. `/yetkiler/csv` 255 satır + rol sütunu; yalnız Admin (Depo 403).
3. Yazdırma: fatura/irsaliye/sipariş ortak şablon; K1 başka şirket 302, şube 403.
4. `/api/sube/ozet` 2 şube, K1 + izole_sube.
5. `/api/saglik` `surum=1.38.0`, `db=ok`.
6. F5-C/F5-B/F4/F1 regresyonları korunur; FK0; F6TEST kalıntısı yok.

**Sonuç:** `test_f6_cila.py` **18/18**; tam regresyon (22 dosya) **496/496, 0 başarısız**.

---

## 4) Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `core.py` | `yazdir_belge()` ortak yardımcı |
| `app.py` | `_json()`; `/api/bildirimler`, `/yetkiler/csv`, `/api/sube/ozet`, `/api/saglik` |
| `fatura.py` / `irsaliye.py` / `siparis.py` | `yazdir` rotaları ortak şablona |
| `sube.py` | `/sube` listesine belge adetleri |
| `templates/yazdir/belge.html` | YENİ — ortak yazdırma şablonu |
| `templates/yetkiler.html` | CSV düğmesi |
| `templates/sube/liste.html` | belge rozetleri |
| `config.py` | `SURUM = "1.38.0"` |
| `test_f6_cila.py` | YENİ — 18 kontrol |

---

## 5) Kanıtlar

- Test: `test_f6_cila.py` (18/18) + regresyon (496/496).
- Sürüm: `config.py SURUM = "1.38.0"`.
