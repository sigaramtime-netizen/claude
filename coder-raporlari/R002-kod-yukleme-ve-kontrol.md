# R002 — Coder Raporu: v1.34.0 Kod + Kanıt Yükleme

- **Rapor ID:** R002
- **İlgili direktif:** D002
- **Durum:** TAMAMLANDI  (seçenekler: TAMAMLANDI / KISMI / HATA)

---

## Yapılan iş

`/home/user/erp` içindeki **Brn Teknoloji ERP v1.34.0** projesinin tamamı repo'nun
`kod/` klasörüne yüklendi. F4 (e-Dönüşüm Mock/Sandbox) paketinin kanıtları
`kanitlar/v1.34.0/` klasörüne konuldu.

- Sürüm: **v1.34.0** (`kod/config.py` → `SURUM = "1.34.0"`, `SURUM_TARIHI = "2026-09-11"`)
- Mimari: Python 3 (yalnızca stdlib: wsgiref + sqlite3) — harici framework/bağımlılık YOK
- Veritabanı: SQLite, 65 tablo (`kod/data/erp.db` ilk açılışta `db.init_db()` ile otomatik üretilir)
- Test: 18 paket, **424/424 GEÇTİ** (F4 22/22 dahil)

## Değişen / eklenen dosyalar

- `kod/` — projenin tamamı (61 `.py`, 133 `.html` şablon, `static/`, `docs/`, 18 test)
- `kanitlar/v1.34.0/` — F4 kanıtları:
  - `kanit_f4_dosya_listesi.txt` (525 dosya listesi)
  - `kanit_f4_degisen_dosyalar.txt` (değişen dosyaların tam dökümü, 2180 satır)
  - `kanit_f4_test_ciktisi.txt` (F4 22/22 + pytest dürüst notu)
  - `kanit_f4_regresyon.log` (18 paket satır satır, 424/424)
  - `f4-*.png` (6 ekran görüntüsü)
  - `PROJE-DOKUMANTASYONU-v1.34.0.txt` (tam proje dokümantasyonu)
- `kanitlar/v1.33.0-arsiv/` — önceki F3 kanıtları (kod/ kökünden taşındı)
- `coder-raporlari/R002-kod-yukleme-ve-kontrol.md` — bu rapor
- `.gitignore` — `kod/data/*.db`, `kod/uploads/`, `kod/yedek/` vb. hariç

## Nasıl çalıştırılır

```bash
cd kod
python3 app.py                          # → http://localhost:8080  (admin / 1234)
python3 test_f4_edonusum.py             # → 22/22 olmalı
for t in test_*.py; do python3 $t; done # → toplam 424/424 olmalı
```

> Not: `kod/data/erp.db` bilerek yüklenmedi (binary; ilk `python3 app.py`
> çalıştırmasında seed verisiyle otomatik üretilir). `kod/uploads/` (ham XML'ler)
> çalışma zamanı üretimi olduğundan hariç tutuldu.

## Kanıtlar

- `kanitlar/v1.34.0/kanit_f4_test_ciktisi.txt` — F4 testi 22/22 çıktısı
- `kanitlar/v1.34.0/kanit_f4_regresyon.log` — tam regresyon 424/424
- `kanitlar/v1.34.0/kanit_f4_degisen_dosyalar.txt` — tüm kritik değişikliklerin içeriği
- `kanitlar/v1.34.0/f4-*.png` — giden/gelen listeler, ayarlar, belge detayı

## Notlar / bilinen sorunlar

- Proje **pytest kullanmaz**; testler düz Python scriptleridir (`python3 test_x.py`).
  `python3 -m pytest` → "collected 0 items" (dürüst not kanıt TXT'lerinde mevcuttur).
- e-Dönüşüm **Mock/Sandbox**'tır; gerçek GİB/İzibiz bağlantısı yoktur (GM emri gereği).
- GM denetim kontrol listesi (D002) adımları `kod/` içinde aynen çalışır durumdadır.
