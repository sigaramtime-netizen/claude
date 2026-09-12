# D003 — F5-A Finansal Analiz & Dashboard Cilası (v1.34.0 → v1.35.0)

- **Görev ID:** D003
- **Başlık:** F5-A — Finansal Analiz Dashboard (satış/kâr-zarar/nakit akışı/bütçe/en çok satan)
- **Durum:** BEKLEMEDE → KODLANIYOR (Coder bekleniyor)
- **Öncelik:** Yüksek (Yönetim her gün bakacak ekran)
- **Önceki:** D002 ONAYLANDI — F4 v1.34.0 e-Dönüşüm Mock 22/22 + 424/424

---

## 1. Amaç

Yönetici her sabah tek ekranda şunu görmeli:
- Bu ay ne sattım / geçen ay / geçen yıl karşılaştırması
- Kâr-zarar (satış - maliyet) ve marj
- Nakit akışı (kasa+banka giriş/çıkış)
- Bütçe hedefi vs gerçekleşen (aylık hedef gir, sapma gör)
- En çok satan / en kârlı ürün ve en çok ciro yapan cari

Şu an `finansal.py` ve `Analiz` ekranı var ama dağınık, bütçe yok, karşılaştırma yok, grafikler statik.

## 2. Kapsam (5 alt modül)

| # | Alt Modül | Ne Olacak |
|---|-----------|-----------|
| 1 | **Satış Özeti Kartları** | Bugün / Bu Hafta / Bu Ay / Bu Yıl satış, alış, tahsilat, tediye, açık servis sayısı — tek satır kartlar (dashboard üstü) |
| 2 | **Dönemsel Karşılaştırma Grafiği** | Aylık satış vs alış vs kâr (bar chart), bu ay vs geçen ay vs geçen yıl (3'lü karşılaştırma) |
| 3 | **Nakit Akışı** | Günlük kasa+banka net akışı (son 30 gün çizgi grafik) + kasa/banka bakiyeleri |
| 4 | **Bütçe** | `butce_hedef` tablosu (ay, hedef_satis, hedef_kar). Yönetici hedef girer, dashboard gerçekleşen vs sapma % gösterir |
| 5 | **En Çok Analizleri** | En çok satan 10 ürün (miktar/tutar), en kârlı 10 ürün (tutar-maliyet), en çok ciro yapan 10 cari |

## 3. Veri Modeli (YENİ 1 TABLO)

```sql
CREATE TABLE butce_hedef (
  id INTEGER PRIMARY KEY,
  sirket_id INTEGER NOT NULL,
  yil INTEGER NOT NULL,
  ay INTEGER NOT NULL, -- 1-12
  hedef_satis REAL DEFAULT 0,
  hedef_kar REAL DEFAULT 0,
  olusturan INTEGER,
  olusturma_tarihi TEXT DEFAULT (datetime('now','localtime')),
  FOREIGN KEY(sirket_id) REFERENCES sirket(id),
  UNIQUE(sirket_id, yil, ay)
);
```

- Migration: `db.py` → `_migrate()` içinde `IF NOT EXISTS` ile ekle (idempotent)
- K1: her sorgu `sirket_id` ile süzülür
- Seed gerekmez, boş başlar

## 4. Teknik Uygulama

**A) Backend — `finansal.py` ve `app.py` (dashboard)**

- `finansal.py`: `butce_hedef` CRUD rotaları:
  - `GET /finansal/butce` → liste + form (yıl/ay/hedef)
  - `POST /finansal/butce/kaydet` → insert/update
  - `POST /finansal/butce/:id/sil` → sil
  - `GET /api/finansal/ozet?donem=aylik|haftalik` → JSON (dashboard grafikleri için)
    - `satis`, `alis`, `kar`, `tahsilat`, `tediye`, `nakit_akis` (son 30 gün dizi)
    - Kar hesabı: `fatura kalem tutar - (stok.alis_fiyat * miktar)` — mevcut `faturaToplam` mantığıyla aynı
    - Nakit akışı: `kasa_hareket + banka_hareket` net
- `app.py` dashboard (`/`): üst kartlar + dönem seçici (Bu Ay / Geçen Ay / Geçen Yıl) + bütçe sapma rozeti
- `core.py`: `para_format`, `yuzde_hesap` helper (varsa kullan, yoksa ekle — kopyala-yapıştır yapma)

**B) Frontend — `templates/finansal/` ve `templates/dashboard.html`**

- Dashboard üstü: 6 kart (Bugün Satış, Bu Ay Satış, Bu Ay Kâr, Kasa Toplam, Banka Toplam, Açık Servis) — mevcut kartları koru, sadece veriyi `finansal.py`den çek
- Orta: Bar chart (Chart.js CDN veya inline SVG — harici bağımlılık YOK, mevcut `static/js` kullan) — Aylık satış/alış/kâr (son 12 ay)
- Alt-sol: Nakit akışı çizgi grafik (son 30 gün)
- Alt-sağ: En çok satan / en kârlı / en çok ciro tablo (top 10, tıklayınca stok/cari detaya gider)
- `finansal/butce.html`: Tablo (yıl/ay/hedef_satis/hedef_kar/gerceklesen/sapma%) + form (yıl, ay, hedef gir) — sapma % = `(gercek - hedef)/hedef*100`
- `finansal/analiz.html`: Mevcut analiz ekranını koru, sadece bütçe karşılaştırmasını ekle

**C) Grafik Kütüphanesi**

- Harici framework YOK. Mevcut `static/` içinde Chart.js yoksa **inline SVG bar/line** ile yap (F3'teki gibi) veya CDN'siz mini chart. `node_modules` ekleme.

**D) Yetkilendirme**

- Finansal Analiz sadece `Yonetici` ve `Muhasebe` rolü görebilir (mevcut `roles` kontrolü ile)

## 5. Yapmaman Gerekenler

- F1/F2/F3/F4 mantığını bozma (mali etki, KDV, typeahead, e-Dönüşüm)
- Yeni harici bağımlılık ekleme (Chart.js CDN bile ekleme, inline SVG yap)
- `butce_hedef` dışında yeni tablo ekleme
- Bütçe hedefini otomatik üretme — kullanıcı manuel girer
- Kâr hesabında stok maliyeti yerine satış fiyatını kullanma — mutlaka `alis_fiyat` kullan

## 6. Test Senaryosu — `test_f5a_finansal.py` (YENİ, ZORUNLU)

`test_f5a_finansal.py` oluştur, en az 18 kontrol, canlı sunucuya HTTP (mevcut testler gibi):

1.  `test_butce_olustur`: bütçe hedefi 2026-09 için 100000 satış / 20000 kâr kaydet → DB'de var mı?
2.  `test_butce_guncelle`: aynı ay hedefi güncelle → yeni değer mi?
3.  `test_butce_k1`: Şirket B'de A bütçesi görünmez (K1)
4.  `test_butce_sil`: sil → DB'den gitti mi?
5.  `test_api_ozet_aylik`: `/api/finansal/ozet?donem=aylik` → satis/alis/kar döner mi?
6.  `test_api_ozet_haftalik`: haftalık özet
7.  `test_kar_hesabi`: satış 1000 (alis 700) + %20 KDV → kar 300 mü? (fatura oluştur + kontrol)
8.  `test_nakit_akis`: kasa hareketi ekle → nakit_akis dizisinde görünüyor mu?
9.  `test_dashboard_kartlar`: `GET /` → HTML'de 6 kart var mı? (Bugün Satış vb.)
10. `test_dashboard_butce_sapma`: hedef 100k, gerçekleşen 120k → sapma +20% görünüyor mu?
11. `test_en_cok_satan`: en çok satan ürün API'si → en az 1 ürün, miktar doğru mu?
12. `test_en_karli`: en kârlı ürün → kar = satış - maliyet doğru mu?
13. `test_en_cok_ciro_cari`: en çok ciro yapan cari → doğru sıralı mı?
14. `test_donem_karsilastirma`: bu ay vs geçen ay → iki dönem verisi dönüyor mu?
15. `test_yetki`: depo kullanıcısı `/finansal/butce` → 403 mü?
16. `test_f1_korundu`: bütçe kaydı mali etki üretmez (cari/yevmiye artmadı)
17. `test_f4_korundu`: e-Fatura hala çalışıyor (+ typeahead)
18. `test_fk_kalinti`: FK check [] + F5A kalıntısı yok

Her test `sirket_id` izole, temizlik ile bitir, `MARK = "F5ATEST"` ile kalıntı bırakma.

## 7. Teslim — ZİPSİZ PROTOKOL (AYNI)

**7.1 Dosya Listesi:**
```bash
find . -type f | sort
```

**7.2 Değişen Dosyalar (cat ile dök):**
- `db.py` (butce_hedef migration)
- `finansal.py` (butce CRUD + /api/finansal/ozet)
- `app.py` veya `dashboard.py` (dashboard kart verisi)
- `templates/finansal/butce.html` (YENİ)
- `templates/finansal/analiz.html` veya `dashboard.html` (grafik kartları)
- `static/js/finansal.js` (varsa, grafik render)
- `test_f5a_finansal.py` (TAMAMI)
- `config.py` (SURUM = "1.35.0")

**7.3 Test Kanıtı:**
```bash
python3 test_f5a_finansal.py  # 18/18 olmalı
python3 test_f4_edonusum.py   # 22/22 hala yeşil?
# Tam regresyon:
for f in test_*.py; do echo "== $f =="; python3 $f; done
# Toplam: 424 + 18 = 442 olmalı, 0 başarısız
```

**7.4 Ekran Kanıtı (varsa):**
- `/` dashboard: 6 kart + dönem karşılaştırma bar chart + nakit akışı çizgisi
- `/finansal/butce`: hedef girme formu + sapma % tablosu
- `/finansal/analiz`: en çok satan / en kârlı / en çok ciro tabloları

**7.5 Sürüm:**
- `config.py`: `SURUM = "1.35.0"`, `SURUM_TARIHI = "2026-09-11"`
- `docs/F5A-finansal-analiz-ozet.md` oluştur (özet, F4 gibi)

## 8. Uygulama Sırası

1.  `db.py` migration (butce_hedef)
2.  `finansal.py` → butce CRUD + /api/finansal/ozet
3.  `templates/finansal/butce.html` → form + tablo + sapma %
4.  Dashboard kartlarını `finansal.py` verisiyle besle
5.  Grafikler (bar + line) → inline SVG
6.  En çok analizleri (top 10 sorguları)
7.  Yetki kontrolü
8.  `test_f5a_finansal.py` yaz, tek tek koş
9.  Tam regresyon (442/442)
10. TXT kanıtlarını topla, `kanitlar/v1.35.0/` altına koy, rapor yaz

**KURAL:** Tam regresyon yeşil olmadan teslim etme. Bütçe kaydı mali tabloya dokunmamalı.

---

## 9. Başla

Şimdi `db.py` migration ile başla, sonra `finansal.py` butce CRUD'u yaz.
Her adımda ne yaptığını logla, TXT kanıtlarını hazırla.

GM onayı için `coder-raporlari/R003-...md` + `kanitlar/v1.35.0/` ile `git push` at.
