# D006 — F6 Son Cila: Bildirim Merkezi + Yetki Matrisi + Yazdırma/PDF + Şube Özet (v1.37.0 → v1.38.0)

- **Görev ID:** D006
- **Başlık:** F6 — Son Cila (bildirim API, yetki CSV, fatura/irsaliye yazdırma, şube özet kartları)
- **Durum:** BEKLEMEDE → KODLANIYOR (Coder bekleniyor)
- **Öncelik:** Kritik — Canlıya çıkış öncesi son mühür
- **Önceki:** D005 ONAYLANDI — F5-C v1.37.0 Beyanname 18/18 + 478/478 (F5 serisi KAPANDI ✅)

---

## 1. Amaç

Faz 1-5 bitti (Çekirdek → Satış → Servis → e-Dönüşüm → Mali/Analitik). Faz 6 (Cila) kod’da var ama **cilasız**:
- Bildirim merkezi sadece HTML — API yok, tip filtre test edilmiyor
- Yetki matrisi (`/yetkiler`) sadece HTML — CSV yok, mali müşavir/Denetçi indiremiyor
- Fatura/İrsaliye/Sipariş yazdırma var ama **ayrı PDF/print route** yok (tek tıkla yazdır)
- Şube özeti sadece dashboard’da dağınık — `/sube` veya `/api/sube/ozet` gibi toplu özet yok
- “Sistem sağlıklı mı?” için `/saglik` var ama detaylı `/api/saglik` (sürüm + DB + test) yok

Bu paket **yeni tablo YOK** — mevcut `bildirimler`, `kullanici`, `sirket`, `sube`, `fatura`, `irsaliye`, `siparis` üzerine cila. **Canlıya hazır** son paket.

## 2. Kapsam (5 alt modül)

| # | Alt Modül | Ne Olacak |
|---|-----------|-----------|
| 1 | **Bildirim API** | `GET /api/bildirimler?tip=uyari&okundu=0` → JSON: `id, tip, baslik, mesaj, okundu, tarih` (K1: `sirket_id`). Mevcut `/bildirimler` korunur. |
| 2 | **Yetki Matrisi CSV** | `GET /yetkiler/csv` → CSV: `Rota Pattern, Method, Modul, Yetki` (Admin sadece, Depo 403). Mevcut `/yetkiler` HTML korunur. |
| 3 | **Yazdırma / PDF Route** | `GET /fatura/<id>/yazdir`, `GET /irsaliye/<id>/yazdir`, `GET /siparis/<id>/yazdir` → sade HTML ( `@media print`, logo + tablo + toplam ) — `window.print()` ile. Ayrı template `yazdir.html` bileşenli (3 belge ortak). |
| 4 | **Şube Özet Kartları + API** | `GET /api/sube/ozet` → JSON: `subeler[{id, kod, ad, fatura_adet, irsaliye_adet, kasa_bakiye}]` (K1: `sirket_id` + `izole_sube` filtresi). `/sube` listesi üstünde küçük özet rozeti (fatura/irsaliye adet). |
| 5 | **Sağlık API Detay** | `GET /api/saglik` → JSON: `{"durum":"ok","surum":"1.38.0","tarih":"2026-09-12","db":"ok","sirket_id":1}` (mevcut `/saglik` korunur, yeni `/api/saglik` eklenir). |

## 3. Veri Modeli

**YENİ TABLO YOK.** Migration YOK.

- `bildirimler` zaten `sirket_id` K1 taşıyor — API K1 ile süz.
- `kullanici`, `sirket`, `sube` zaten var — yetki CSV `core.ROUTES` listesinden üretilir (DB’ye dokunmaz).
- Yazdırma: `fatura`/`irsaliye`/`siparis` + `*_kalem` zaten var — sadece okur.
- Şube özet: `sube` + `fatura`/`irsaliye`/`kasa_hareket` (bakiye `kasa._bakiye` gibi).

## 4. Teknik Uygulama

**A) Backend**

- `app.py`:
  - `GET /api/bildirimler` (`roles=()`): `tip` (uyari/bilgi/hatirlatma) + `okundu` (0/1) query ile filtre, `limit 50`, `sirket_id` zorunlu.
  - `GET /yetkiler/csv` (`roles=("Admin",)`): `core.ROUTES` üzerinden CSV (`;` ayraç), `Content-Disposition: attachment; filename="yetki-matrisi.csv"`, `text/csv`.
  - `GET /api/sube/ozet` (`roles=()`): her şube için `fatura`/`irsaliye` adet (o şubenin `sube_id`’si ile), `kasa` bakiye (şubedeki kasalar toplamı). `izole_sube(req)` varsa yalnız o şube.
  - `GET /api/saglik` (`roles=()`): `surum` = `config.SURUM`, `db` = `try: db.get_conn() → ok else hata`, `tarih` = bugün iso.
  - Yazdırma: 3 route `fatura_yazdir`, `irsaliye_yazdir`, `siparis_yazdir` → ortak helper `_yazdir_verisi(conn, tip, id, sid)` ile `render_template("yazdir/belge.html", belge={tip,no,tarih,cari,kalemler,toplam})`. Sade HTML, `@media print` CSS, logo `FIRMA_ADI`.
- `core.py`: `ROUTES` zaten global — CSV için import et, değişiklik yok.

**B) Frontend — `templates/`**

- `templates/yazdir/belge.html` (YENİ, tek bileşen — 3 belge ortak):
  ```html
  <h1>{{ belge.tip }} — {{ belge.no }}</h1>
  <div>{{ belge.tarih }} · {{ belge.cari }}</div>
  <table>kalemler (sıra, stok_kod, ad, miktar, birim_fiyat, tutar)</table>
  <div>Genel Toplam: {{ toplam|para }}</div>
  <button onclick="window.print()">Yazdır</button>
  ```
  Sade, inline style (harici YOK, önizlemede de görünür).

- `templates/sube/index.html` (veya mevcut `/sube` listesi): üst küçük özet rozetleri (fatura/irsaliye adet) — mevcut tablo korunur.

- `templates/yetkiler.html` korunur — sadece CSV düğmesi `→ /yetkiler/csv` ekle.

**C) Yetkilendirme**

- `/api/bildirimler`, `/api/sube/ozet`, `/api/saglik`, `/fatura/<id>/yazdir` vb.: `roles=()` (giriş yapmış herkes, ama K1/şube izolasyonu korunur).
- `/yetkiler/csv`: `Admin` sadece (Depo/Muhasebe → 403).
- Yazdırma: belgenin `sirket_id` ve `sube_id` izolasyonu `sube_koruma` ile doğrulanır — başka şirket/şubeye ait belge 403.

**D) Grafik / Stil**

- Grafik YOK (F5’te yapıldı). Yazdırma sade HTML + inline print CSS — harici kütüphane YOK.

## 5. Yapmaman Gerekenler

- Yeni tablo / migration ekleme
- Harici PDF kütüphanesi (wkhtmltopdf, reportlab vb.) ekleme — sade HTML print yeterli
- Bildirim/yetki mantığını değiştirme (var olan korunur, sadece API/CSV eklenir)
- K1 `sirket_id` ve `izole_sube` filtresini kaldırma
- Mevcut `/saglik`, `/yetkiler`, `/bildirimler` HTML’lerini bozma

## 6. Test Senaryosu — `test_f6_cila.py` (YENİ, ZORUNLU)

`test_f6_cila.py` oluştur, en az 18 kontrol, canlı sunucuya HTTP (F5 gibi):

1.  `test_bildirim_api`: `GET /api/bildirimler` → list, en az 1 bildirim, `tip` alanı var mı?
2.  `test_bildirim_api_filtre`: `GET /api/bildirimler?tip=uyari` → yalnız `uyari` tipinde mi?
3.  `test_bildirim_api_k1`: Şirket B'de A bildirimi görünmez (A’da oluşturulan `MARK` bildirim B’de yok)
4.  `test_yetki_html`: `GET /yetkiler` → 200, HTML’de `Rota` ve `Yetki` başlıkları var mı?
5.  `test_yetki_csv`: `GET /yetkiler/csv` → 200, `text/csv`, başlık `Rota Pattern;Method` içeriyor mu?, en az 5 satır
6.  `test_yetki_csv_yetki`: Depo rolü `/yetkiler/csv` → 403
7.  `test_yazdir_fatura`: `GET /fatura/<id>/yazdir` (onaylı fatura) → 200, HTML’de fatura_no ve `Yazdır` düğmesi var mı?
8.  `test_yazdir_irsaliye`: `GET /irsaliye/<id>/yazdir` → 200, irsaliye_no var mı?
9.  `test_yazdir_siparis`: `GET /siparis/<id>/yazdir` → 200, siparis_no var mı?
10. `test_yazdir_k1`: Şirket B'de A faturası `/yazdir` → 403 veya 302 (izole)
11. `test_sube_api`: `GET /api/sube/ozet` → `subeler` listesi, en az 1 şube, `fatura_adet` alanı var mı?
12. `test_sube_api_k1`: Şirket B'de yalnız B şubeleri (A şubesi yok)
13. `test_saglik`: `GET /saglik` → `{"durum":"ok"}` korunuyor mu? (200)
14. `test_api_saglik`: `GET /api/saglik` → JSON `durum:surum:db` var mı? `surum` = "1.38.0" mi?
15. `test_f5c_korundu`: `/beyanname` ve `/api/beyanname/ozet` hala 200?
16. `test_f5b_f5a_korundu`: `/demirbas`, `/finansal/butce` hala 200?
17. `test_f4_korundu`: `/edonusum` ve `/api/ara` hala 200?
18. `test_fk_kalinti`: `PRAGMA foreign_key_check` 0 + MARK kalıntısı yok (bildirim/sirket/fatura)

Her test K1 izole, `MARK = "F6TEST"` ile kalıntı bırakma. Bildirim testinde `bildirimler` tablosuna `MARK` başlıklı kayıt aç, sonra `api/bildirimler`’de göründüğünü doğrula, sonra sil.

## 7. Teslim — ZİPSİZ PROTOKOL (AYNI)

**7.1 Dosya Listesi:**
```bash
find . -type f | sort
```

**7.2 Değişen Dosyalar (cat ile dök):**
- `app.py` (yazdırma + /api/bildirimler + /api/sube/ozet + /api/saglik + /yetkiler/csv)
- `templates/yazdir/belge.html` (YENİ, 3 belge ortak)
- `templates/sube/index.html` veya `templates/sube.html` (özet rozet)
- `templates/yetkiler.html` (CSV düğmesi)
- `test_f6_cila.py` (TAMAMI)
- `config.py` (SURUM = "1.38.0")

**7.3 Test Kanıtı:**
```bash
python3 test_f6_cila.py  # 18/18 olmalı
python3 test_f5c_beyanname.py  # 18/18 hala yeşil?
# Tam regresyon:
for f in test_*.py; do echo "== $f =="; python3 $f; done
# Toplam: 478 + 18 = 496 olmalı, 0 başarısız
```

**7.4 Ekran Kanıtı (opsiyonel):**
- `/yetkiler` ve `/yetkiler/csv` indirme
- `/api/bildirimler?tip=uyari` JSON
- `/fatura/1/yazdir` print HTML
- `/api/sube/ozet` JSON
- `/api/saglik` JSON

**7.5 Sürüm:**
- `config.py`: `SURUM = "1.38.0"`, `SURUM_TARIHI = "2026-09-11"`
- `docs/F6-cila-ozet.md` oluştur (özet, F5 gibi)

## 8. Uygulama Sırası

1.  `app.py` → `/api/bildirimler` + `/yetkiler/csv` + 3 `yazdir` + `/api/sube/ozet` + `/api/saglik`
2.  `templates/yazdir/belge.html` → tek bileşen
3.  `templates/yetkiler.html` → CSV düğmesi; `templates/sube/*` → özet rozet
4.  Yetki testleri (Depo 403)
5.  `test_f6_cila.py` yaz, tek tek koş
6.  Tam regresyon 496/496
7.  TXT kanıtlarını topla, `kanitlar/v1.38.0/` altına koy, rapor yaz

**KURAL:** Tam regresyon yeşil olmadan teslim etme. Yeni tablo ekleme. Harici PDF kütüphanesi YOK.

---

## 9. Başla

Şimdi `app.py` ile başla (`/api/bildirimler`).
Her adımda ne yaptığını logla, TXT kanıtlarını hazırla.

GM onayı için `coder-raporlari/R006-...md` + `kanitlar/v1.38.0/` ile `git push` at.
