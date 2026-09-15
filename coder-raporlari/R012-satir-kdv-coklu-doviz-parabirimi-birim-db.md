# R012 — Satır Bazlı KDV + Çoklu Döviz + Para Birimi & Birim DB Tablo (v1.43.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D012 — Satır Bazlı KDV + Çoklu Döviz + Para Birimi/Birim DB Tablo Geçişi
- **Sürüm:** 1.42.0 → **1.43.0**
- **Durum:** KODLANDI ✅ — GM denetimi bekleniyor
- **Tarih:** 2026-09-14
- **Direktif:** `gm-direktifleri/D012-satir-kdv-coklu-doviz-parabirimi-birim-db-v1.43.0.md` (GM2 acil yedek ONAYLADI; kapsam **B + D + X**)

---

## 1. Yapılan İş

### B — Satır bazlı KDV (4 belge kalem tablosu)
1. **`kod/db.py`** → `fatura_kalem`, `irsaliye_kalem`, `teklif_kalem`, `siparis_kalem`
   tablolarına `kdv_dahil INTEGER` kolonu (NULL = belge genelini izler; 0 = açıkça hariç;
   1 = açıkça dahil) + `_migrate()` içine kalem-loop'u (mevcut DB'lere ALTER).
2. **`kod/static/js/form-satir.js`** → satır `<select name=k_kdv_dahil>` (`Belge`/`Hariç`/`Dahil`),
   `satirDahil(tr)`: açık 1/0 override, boşsa belge geneli; `makeRow()` select üretir; satır
   verisi yüklenirken `kdv_dahil` uygulanır; global KDV mod değişiminde açık override'lı
   satırlar atlanır.
3. **4 belge form thead'i** `KDV %` → `KDV % / Mod`; **4 modül backend**
   (`fatura.py`, `irsaliye.py`, `teklif.py`, `siparis.py`): `_satirlar_from_form` `k_kdv_dahil`
   okur (1/dahil/on→1, 0/haric→0, boş→None); `line_dahil` ise `core.kdv_ayikla()` ile net'e
   çevrilir; kalem INSERT + edit satır dict `kdv_dahil` taşır. Aynı belgede karışık KDV mümkün.

### D — Çoklu döviz gösterimi + Para Birimi filtresi
4. **Belge detayları** (`fatura/irsaliye/teklif/siparis` `detay.html`): döviz + TL karşılığı
   yan yana — `Belge dövizi: USD · Kur: 1 USD = 34.20 TL · TL karşılığı ≈ …` (irsaliye zaten vardı).
5. **`kod/cari.py:cari_ekstre`** → `pb` query filtresi (Tümü/TRY/USD/EUR/GBP; tarih/devir/toplam
   hepsi filtreye uyar) + `pb_totals` döviz bazlı alt toplam kartı (net TL + ≈ döviz, ortalama kur).
6. **`kod/kartoteks.py:_cari_rows`** → `pb` parametresi (satır + devir + belge tipi birlikte);
   `kartoteks_cari` route `pb` okur + `pb_totals` rozetleri; `kartoteks/cari.html` +
   `cari/ekstre.html` → Para Birimi select'i.
7. Belge kaydedilirken kur sabitlenir (mevcut davranış korundu); cari hareketler daima TL
   karşılığı tutar (K2 bozulmaz — `cari.hareket_ekle` aynen).

### X — Para Birimi & Birim DB tabloya geçiş
8. **`kod/db.py`** → `para_birimi(kod, ad, aktif, sirket_id)` + `birim(ad, aktif, sirket_id)`
   tabloları (`UNIQUE(sirket_id, kod/ad)` = K1 izolasyon); `PARA_BIRIMI_SEED` (TRY/USD/EUR/GBP
   + adları) + `BIRIM_SEED` (11 değer 1:1) + `seed_para_birimi()`/`seed_birim()` (idempotent,
   `seed()` başında çağrılır); `para_birimleri()`/`birimleri()` (aktif filtreli, tablo boşsa
   config sabit listesine düşer; conn verilmezse kendi açıp kapatır).
9. **`kod/stok.py`** → `POST /api/birim/ekle` (alan `ad`) + `POST /api/para-birimi/ekle`
   (alanlar `kod`/`ad`); D011 deseni: boşsa 400, `lower()` + `sirket_id` idempotent, audit, K1;
   rolleri `STOK_WRITE`. Stok formu `#birim-select`/`#pb-select` + `＋ Birim`/`＋ Döviz`
   (prompt → fetch POST → select'e ekle + seç).
10. **`kod/ayarlar.py`** → `/ayarlar/tanimlar` para birimi + birim listelerini (kullanım
    sayısıyla) yükler; `POST /ayarlar/tanimlar/para-birimi/<id>/durum` +
    `/birim/<id>/durum` (Admin; silme YOK — K32; **TRY pasifleştirilemez**). Şablon
    `ayarlar/tanimlar.html` iki yeni kart eklendi.
11. Tüm tüketiciler DB'den okur: fatura/irsaliye/teklif/sipariş `birimler`/`para_birimleri`,
    kasa/banka/çek-senet/döviz/alinan-teklif/satın-alma para birimi dropdown + validasyonları
    (`db.para_birimleri()`), `doviz.py` rapor + kur ekleme. `config.PARA_BIRIMLERI` artık
    yalnızca tohum kaynağı.

### Sürüm & dokümantasyon
12. **`kod/config.py`** `SURUM="1.43.0"` (+`SURUM_TARIHI="2026-09-14"`); **`kod/CHANGELOG.md`**
    v1.43.0 girdisi; **`DURUM.md`** D012 → KODLANDI; **`regresyon_runner.py`** başlık 1.43.0.
13. **`test_d012_kdv_doviz_master.py` (YENİ)** — 21 kontrol; eski testlerdeki sürüm sabitleri
    1.43.0'a güncellendi (`test_d010_yedekleme.py`, `test_d011_tanimlar_barkod.py`, `test_f6_cila.py`).

## 2. Kabul kriterleri kontrolü

| Kriter | Durum |
|---|---|
| Aynı belgede karışık KDV (satır dahil + hariç) | ✅ (test 2-3) |
| Boş override → belge geneli uygulanır (NULL saklanır) | ✅ (test 4) |
| Tohum: para_birimi 4 (TRY/USD/EUR/GBP) + birim 11 | ✅ (test 5) |
| Inline `＋ Birim`/`＋ Döviz` idempotent + sirket_id=1 | ✅ (test 6-9) |
| Yetki: STOK_WRITE dışı 403 | ✅ (test 10) |
| Pasifleştir (silme YOK) + pasif formda seçilemez | ✅ (test 11-13) |
| TRY pasifleştirilemez | ✅ (test 14) |
| K1 izolasyonu (birim + para birimi) | ✅ (test 15) |
| USD fatura detayında döviz + TL görünür | ✅ (test 16) |
| Cari hareket TL karşılığı (K2) + para_birimi=USD | ✅ (test 17) |
| Ekstre Para Birimi filtresi (TRY gizlenir) | ✅ (test 18) |
| Ekstre + kartoteks döviz alt toplamları | ✅ (test 19-20) |
| `PRAGMA foreign_key_check = 0` + kalıntı yok | ✅ (test 21) |
| `SURUM="1.43.0"` | ✅ `config.py` |
| `test_d012_kdv_doviz_master.py` ≥ 12 kontrol | ✅ 21 kontrol |
| Tam regresyon 27 dosya / 0 başarısız | ✅ 603 kontrol |

## 3. Test Sonuçları

```
python3 test_d012_kdv_doviz_master.py  → 21/21 ✅
Tam regresyon (27 dosya)              → 603 kontrol, 0 başarısız ✅
PRAGMA foreign_key_check              → 0
Taze DB seed (idempotent)             → para_birimi=4, birim=11, fk=0
```

## 4. Değişen / eklenen dosyalar

- `kod/db.py` — `para_birimi` + `birim` tabloları, tohumlar, helper'lar; kalem `kdv_dahil` migrasyonu
- `kod/config.py` — `SURUM`/`SURUM_TARIHI` 1.43.0
- `kod/stok.py` — `/api/birim/ekle` + `/api/para-birimi/ekle`; form render DB listeleri
- `kod/cari.py` — `cari_ekstre` pb filtresi + döviz alt toplamları; render DB listeleri
- `kod/kartoteks.py` — `_cari_rows(pb=)` + `kartoteks_cari` pb + alt toplamlar
- `kod/fatura.py`, `kod/irsaliye.py`, `kod/teklif.py`, `kod/siparis.py` — satır KDV + DB listeleri
- `kod/doviz.py`, `kod/kasa.py`, `kod/banka.py`, `kod/cek_senet.py`, `kod/alinan_teklif.py`, `kod/satin_alma.py` — DB para birimi/birim
- `kod/static/js/form-satir.js` — satır KDV select + hesap
- `kod/templates/...` — tanimlar (para birimi + birim kartları), cari/ekstre, kartoteks/cari, 4 belge detay+form
- `kod/regresyon_runner.py`, `kod/CHANGELOG.md`, `DURUM.md`
- `test_d012_kdv_doviz_master.py` (YENİ) + 3 eski test sürüm sabiti
- `paketle_d012.py` (YENİ), `coder-raporlari/R012-...md` (YENİ)

## 5. Nasıl çalıştırılır

```bash
cd kod
python3 app.py                             # http://127.0.0.1:8080
python3 test_d012_kdv_doviz_master.py      # yeni test (21)
python3 regresyon_runner.py                # tam regresyon (27 dosya)
python3 ../paketle_d012.py                 # sansürlü teslim ZIP
```

## 6. Notlar / bilinen sorunlar

- **Kapsam dışı (GM2 talimatı):** D013 tahsilat/ödeme ekranı (E) DOKUNULMADI.
- **Semantik karar (B):** "Satır KDV Dahil" yalnızca **giriş** brüt→net dönüşümünü değiştirir;
  KDV toplamı her satırda `net × oran/100` üzerinden hesaplanır. Böylece aynı net değer
  dahil/hariç girilse de belge toplamı aynı çıkar (F2 "DB her zaman NET" kuralı korunur;
  `test_f2_kdv` 34/34 yeşil). Direktif "aynı belgede karışık KDV mümkün; toplamlar doğru"
  kabul kriteri bu semantikle sağlanır.
- **TRY koruması:** TRY temel para birimidir; tanımlarda pasifleştir butonu disabled + backend
  flash ile reddeder.
- **Silme yok:** K32 gereği para birimi/birim silinmez; pasifleştirme + aktifleştirme var.
- **Sansür:** teslim ZIP'i sansürlü üretildi — `kod/test_d007_iyilestirmeler.py` +
  `docs/D007-kullanici-bildirimleri-ozet.md` içindeki gerçek kişi adı `MÜŞTERİ-A` →
  `MÜŞTERİ-A` / `D007-MUSTERIA` (KÖPRÜ deseniyle birebir, case-sensitive). Özel repoda kaynak
  ad aynen durur.
- **`PRAGMA foreign_key_check=0`** ve demo DB'de D012TEST/F2TEST kalıntısı yok (test kendi temizliğini yapar).
