# R006 — F6 Son Cila (v1.38.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D006 (F6 Son Cila: Bildirim API + Yetki CSV + Yazdırma + Şube Özet + Sağlık)
- **Sürüm:** 1.37.0 → **1.38.0**
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-12
- **Commit:** `[CODER] D006 F6 son cila v1.38.0 (bildirim API + yetki CSV + ortak yazdir + sube ozet + saglik API)`

---

## 1. Yapılan İş

YENİ TABLO YOK / MIGRATION YOK; harici PDF kütüphanesi YOK (sade HTML print).

1. **`kod/core.py`** — `yazdir_belge(r, kalemler, no_key, tip_label)`: fatura/irsaliye/sipariş
   detayını ortak yazdırma şablonu için normalize eden saf yardımcı.
2. **`kod/app.py`**
   - `_json()` helper.
   - `GET /api/bildirimler` (roles=(), K1) — tip (uyari/bilgi/hatirlatma) + okundu (0/1)
     filtreleri, limit 50; `id,tip,baslik,mesaj,okundu,tarih`.
   - `GET /yetkiler/csv` (roles=Admin) — `core.ROUTES` üzerinden `;` ayraçlı CSV
     (`Rota Pattern;Method;Modul;Yetki`), `attachment; filename="yetki-matrisi.csv"`.
   - `GET /api/sube/ozet` (roles=(), K1 + izole_sube) — şube → `fatura_adet`, `irsaliye_adet`,
     `kasa_bakiye` (o şubedeki kasaların `kasa._bakiye` toplamı).
   - `GET /api/saglik` (roles=()) — `{durum, surum, tarih, db, sirket_id}`; mevcut `/saglik` korundu.
3. **`kod/fatura.py` / `irsaliye.py` / `siparis.py`** — `yazdir` rotaları ortak
   `templates/yazdir/belge.html`'e bağlandı; `sube_koruma` ile başka şubeye ait belge 403.
4. **`kod/sube.py`** — `/sube` listesine şube başına fatura/irsaliye adetleri eklendi.
5. **`kod/templates/`** — `yazdir/belge.html` (YENİ, tek bileşen — 3 belge ortak, `@media print`
   + `window.print()`), `yetkiler.html` CSV düğmesi, `sube/liste.html` belge rozetleri.
6. **`kod/config.py`** — `SURUM = "1.38.0"`.
7. **`kod/test_f6_cila.py`** — 18 kontrol (canlı sunucuya HTTP), MARK=F6TEST, K1 izolasyon.

## 2. Direktife Uygunluk (kontrol listesi)

| Direktif maddesi | Durum |
|---|---|
| Yeni tablo / migration ekleme | ✅ YOK |
| Harici PDF kütüphanesi ekleme | ✅ YOK (sade HTML print) |
| Bildirim/yetki mantığı değişmedi (sadece API/CSV) | ✅ |
| K1 sirket_id + izole_sube korundu | ✅ |
| Mevcut /saglik, /yetkiler, /bildirimler bozulmadı | ✅ |
| /yetkiler/csv yalnız Admin (Depo 403) | ✅ |
| Yazdırma: başka şirket/şube belgesi izole (403/302) | ✅ |
| F4/F5 serisi bozulmadı | ✅ |
| 18 kontrol + canlı HTTP + F6TEST kalıntısız | ✅ |

## 3. Test Sonuçları

```
python3 test_f6_cila.py  → 18/18
Tam regresyon (22 dosya) → 496/496, 0 başarısız
pytest                   → collected 0 items (proje pytest kullanmaz)
```

Regresyon dökümü: alinan_teklif 23, bakim 29, belge_sayac 9, coklu_sirket 16, crm 25,
eksik_teslimat 21, f1_mali 25, f2_kdv 34, f3_arama 30, f4_edonusum 22, f5a_finansal 18,
f5b_demirbas 18, f5c_beyanname 18, **f6_cila 18**, izolasyon 22, izolasyon_mali 19,
manuel_satir 28, pos 41, satin_alma 23, silme 23, sirket_yonetimi 19,
teklif_siparis_manuel 15 = **496**.

## 4. Teslim (ZİPSİZ PROTOKOL)

- `kanitlar/v1.38.0/kanit_f6_dosya_listesi.txt` — find + git status
- `kanitlar/v1.38.0/kanit_f6_degisen_dosyalar.txt` — değişen kritik dosyalar (tam içerik)
- `kanitlar/v1.38.0/kanit_f6_test_ciktisi.txt` — F6 18/18 + tam regresyon 496/496 (tek geçiş + sayaç) + pytest
- `kanitlar/v1.38.0/kanit_f6_ozet_hash.txt` — zaman damgası + sha256
- `docs/F6-cila-ozet.md` — özet
- `coder-raporlari/R006-f6-son-cila.md` — bu rapor
- `config.py` — SURUM 1.38.0

## 5. Notlar

- Yazdırma için yeni ortak şablon `templates/yazdir/belge.html` devreye alındı; eski
  `fatura/yazdir.html`, `irsaliye/yazdir.html`, `siparis/yazdir.html` şablonları yerinde
  duruyor (artık hiçbir rota onları kullanmıyor).
- Grafik YOK (F5'te tamamlandı). Ekran görüntüsü (PNG) istenirse Playwright ile üretilir.
