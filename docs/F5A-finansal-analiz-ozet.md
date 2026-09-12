# F5-A Finansal Analiz & Dashboard — v1.35.0

**Görev:** D003 (F5-A) · **Durum:** KODLANDI ✅
**Tarih:** 2026-09-11 · **Önceki:** D002/F4 v1.34.0

---

## 1. Ne Yapıldı

Yönetici/Muhasebe'nin her sabah bakacağı tek ekran: satış özeti, dönemsel karşılaştırma,
nakit akışı, bütçe hedefi vs gerçekleşen ve en çok analizleri.

| # | Alt Modül | Durum |
|---|-----------|-------|
| 1 | Satış Özeti Kartları (dashboard üstü 6 kart) | ✅ |
| 2 | Dönemsel Karşılaştırma (aylık satış/alış/kâr — inline SVG bar) | ✅ |
| 3 | Nakit Akışı (son 30 gün kasa+banka net, inline SVG) | ✅ |
| 4 | Bütçe (`butce_hedef` CRUD + sapma %) | ✅ |
| 5 | En Çok Analizleri (satan/kârlı ürün top 10, ciro cari top 10) | ✅ |

## 2. Veri Modeli — YENİ TEK TABLO

```sql
CREATE TABLE IF NOT EXISTS butce_hedef (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  sirket_id INTEGER NOT NULL REFERENCES sirket(id),
  yil INTEGER NOT NULL,
  ay INTEGER NOT NULL,          -- 1-12
  hedef_satis REAL NOT NULL DEFAULT 0,
  hedef_kar   REAL NOT NULL DEFAULT 0,
  olusturan INTEGER,
  olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now','localtime')),
  UNIQUE(sirket_id, yil, ay)    -- K1: şirket + yıl + ay başına tek satır
);
```

- Migration `db.py → _migrate()` içinde `IF NOT EXISTS` (idempotent). Seed yok, boş başlar.
- Eski `butce` (Gelir/Gider) tablosuna dokunulmadı; bütçe CRUD'u `butce_hedef` üzerine taşındı.

## 3. Backend

- `finansal.py`:
  - `GET  /finansal/butce` — liste + form (yıl/ay/hedef_satis/hedef_kar)
  - `POST /finansal/butce/kaydet` — insert/update (`ON CONFLICT ... DO UPDATE`)
  - `POST /finansal/butce/<id>/sil` — sil
  - `GET  /api/finansal/ozet?donem=aylik|haftalik` — JSON: `satis, alis, kar, tahsilat,
    tediye, banka_bakiye, nakit_akis[30gün], en_cok_satan, en_karli,
    en_cok_ciro_cari, donem_karsilastirma{bua/gecen/gecen_yil}, butce{hedef, gercek, sapma}`
  - Kâr hesabı: **fatura kalem tutar (TL) − (stok.alis_fiyat × miktar)** — satış fiyatı DEĞİL.
- `app.py` (`/` dashboard): `finansal.py` yardımcılarından `bu_ay_kar`, `banka_toplam`,
  `butce` (hedef + sapma) verisi çekilir; dönem seçici bağlantıları eklenir.
- Yetkilendirme: `FINANSAL_GOR = ("Admin", "Muhasebe")` — `/finansal*` ve `/api/finansal/ozet`
  yalnız bu iki rol; diğerleri 403 (Admin her zaman geçer).

## 4. Frontend (inline SVG — harici bağımlılık YOK)

- `templates/dashboard.html`: 6 kart (Bugün Satış, Bu Ay Satış [bütçe sapma rozeti],
  Bu Ay Kâr, Kasa Toplam, Banka Toplam, Açık Servis) + dönem bağlantıları.
- `templates/finansal/index.html` (analiz ekranı — korundu): bütçe karşılaştırma kartı eklendi
  (hedef/gerçekleşen satış & kâr + sapma rozeti).
- `templates/finansal/butce.html`: hedef formu + yıl tablosu (hedef/gerçekleşen/sapma %).
  Sapma = `(gerçek − hedef) / hedef × 100`.
- Grafikler sunucu tarafı üretilen inline SVG (`_bar_svg`, `_bar2_svg`); `static/js/finansal.js`
  gerekmedi (JS yok).

## 5. Test Kanıtı

- `python3 test_f5a_finansal.py` → **18/18** (direktifin 18 senaryosu, canlı sunucuya HTTP)
- `python3 test_f4_edonusum.py` → **22/22** (F4 bozulmadı)
- Tam regresyon (19 dosya) → **442/442, 0 başarısız**
- Kural doğrulandı: bütçe kaydı mali etki üretmez (cari_hareket/yevmiye artmadı);
  F5ATEST ile kalıntı yok; `PRAGMA foreign_key_check` = [].

## 6. Sürüm

- `kod/config.py`: `SURUM = "1.35.0"`, `SURUM_TARIHI = "2026-09-11"`
