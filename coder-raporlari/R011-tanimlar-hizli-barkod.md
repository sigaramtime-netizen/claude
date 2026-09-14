# R011 — Tanım Verileri (Kategori & Cari Grup) + Hızlı Barkod (v1.42.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D011 — Tanım Verileri (Kategori & Cari Grup) + Hızlı Barkod Girişi
- **Sürüm:** 1.41.0 → **1.42.0**
- **Durum:** KODLANDI ✅ — GM denetimi bekleniyor
- **Tarih:** 2026-09-14
- **Direktif:** `gm-direktifleri/D011-tanimlar-hizli-barkod.md` (GM1 ONAYLADI; GM2 kapsam: **A + C yalnızca**)

---

## 1. Yapılan İş

### A — Tanım Verileri (Kategori & Cari Grup)
1. **`kod/stok.py`** → `POST /api/kategori/ekle` (Ajax, `STOK_WRITE`): Marka deseni birebir —
   `ad` trim, boşsa 400 JSON; `lower(ad)` + `sirket_id` izolasyonlu **idempotent** eşleşme
   (aynı ad → mevcut `id` döner); yoksa `INSERT kategori(ad, aktif=1, sirket_id)` + `audit("kategori",...,"olustur")`.
2. **`kod/cari.py`** → `POST /api/cari_grup/ekle` (Ajax, `WRITE_ROLES`): aynı desen;
   `tip` varsayılan `'Bölge'`; `INSERT cari_grup(ad, tip, aktif=1, sirket_id)` + audit.
3. **`kod/cari.py`** → `_gruplar(..., aktif=False)` parametresi eklendi; cari **liste + form**
   dropdown'ları `db_tmp_gruplar(req, aktif=True)` ile aktif filtreli (pasif grup yeni kayıtta
   seçilemez; mevcut kayıtlar bozulmaz).
4. **Form butonları (D007 `＋ Marka` deseni birebir, sayfa yenilenmez):**
   - `kod/templates/stok/form.html` → `kategori_id` select'ine `＋ Kategori` (id=`kategori-select`).
   - `kod/templates/cari/form.html` → `grup_id` select'ine `＋ Grup` (id=`grup-select`).
   - prompt → `fetch POST` → gelen `{id, ad}` option olarak eklenir + seçilir; hata varsa `d.hata` alert.

### Ayarlar → Tanımlar (pasifleştir, silme YOK — K32)
5. **`kod/ayarlar.py`** → `GET /ayarlar/tanimlar` (roles=Admin): kategori + cari grup listesi
   (kullanım sayısıyla, `sirket_id` izolasyonlu) + `POST /ayarlar/tanimlar/kategori/<id>/durum`
   ve `.../cari-grup/<id>/durum` (aktif⇄pasif toggle + audit). **Silme rotası yok.**
6. **`kod/templates/ayarlar/tanimlar.html` (YENİ)** + Ayarlar hub'ına "🗂️ Tanımlar" kartı.

### C — Hızlı Barkod Girişi (irsaliye/fatura/teklif)
7. `kod/fatura.py` + `kod/irsaliye.py` → `action=="barkod"` backend **zaten vardı** (alan `barkod_sec`);
   eksik olan yalnızca frontend input'uydu.
8. **`kod/teklif.py`** → `action=="barkod"` **eklendi** (stok.barkod_bul → satır ekle, bulunamazsa flash).
9. Üç form şablonunda (`fatura/form.html`, `irsaliye/form.html`, `teklif/form.html`) araç çubuğuna
   `barkod_sec` input (`id="barkod-hizli"`) + `＋ Barkod` butonu; **Enter** → gizli `action=barkod`
   alanı ekleyip formu gönderir (POS "Enter'da ekle" deseni). Mevcut typeahead'e **dokunulmadı**.

### Sürüm & dokümantasyon
10. **`kod/config.py`** `SURUM = "1.42.0"`; **`kod/CHANGELOG.md`** v1.42.0 girdisi.
11. **`test_d011_tanimlar_barkod.py` (YENİ)** — 21 kontrol.

## 2. Kabul kriterleri kontrolü

| Kriter | Durum |
|---|---|
| Kategori/cari grup inline ekleme (Ajax, sayfa yenilenmez) | ✅ (test 2, 6) |
| İdempotent (aynı ad → aynı id) + boş ad 400 | ✅ (test 3-4, 7-8) |
| Cari grup `tip='Bölge'` varsayılan | ✅ (test 6) |
| Yetki: `STOK_WRITE` (kategori) / `WRITE_ROLES` (grup); Admin dışı tanımlar 403 | ✅ (test 5, 14) |
| Ayarlar→Tanımlar liste + pasifleştir; **silme YOK** | ✅ (test 9-11) |
| Pasif kayıt yeni belgelerde seçilemez, mevcut bozulmaz | ✅ (test 12-13) |
| K1 şirket izolasyonu (kategori + cari grup) | ✅ (test 20) |
| Hızlı barkod Enter→satır (fatura/teklif/irsaliye) + bulunamazsa uyarı | ✅ (test 15-18) |
| Barkod input 3 formda var, typeahead'e dokunulmadı | ✅ (test 19) |
| **Yeni tablo / migration YOK** | ✅ (yalnız rota + JS + şablon) |
| `test_d011_tanimlar_barkod.py` + tam regresyon yeşil | ✅ 21/21 + 26 dosya/582/0 |

## 3. Test Sonuçları

```
python3 test_d011_tanimlar_barkod.py  → 21/21 ✅
Tam regresyon (26 dosya)             → 582 kontrol, 0 başarısız ✅
PRAGMA foreign_key_check             → 0
```

## 4. Değişen / eklenen dosyalar

- `kod/stok.py` — `/api/kategori/ekle`
- `kod/cari.py` — `/api/cari_grup/ekle` + `_gruplar(aktif=)` + aktif filtreli dropdown'lar
- `kod/teklif.py` — `action=="barkod"` eklendi
- `kod/ayarlar.py` — `/ayarlar/tanimlar` + durum toggle rotaları
- `kod/templates/ayarlar/tanimlar.html` (YENİ)
- `kod/templates/ayarlar/index.html` — Tanımlar kartı
- `kod/templates/stok/form.html`, `kod/templates/cari/form.html` — `＋ Kategori` / `＋ Grup`
- `kod/templates/fatura/form.html`, `kod/templates/irsaliye/form.html`, `kod/templates/teklif/form.html` — hızlı barkod input
- `kod/config.py`, `kod/CHANGELOG.md`
- `test_d011_tanimlar_barkod.py` (YENİ), `test_d010_yedekleme.py` (sürüm 1.42.0), `test_f6_cila.py` (sürüm 1.42.0)

## 5. Nasıl çalıştırılır

```bash
cd kod
python3 app.py                        # http://127.0.0.1:8080
python3 test_d011_tanimlar_barkod.py  # yeni test
python3 regresyon_runner.py           # tam regresyon
```

## 6. Notlar / bilinen sorunlar

- **Kapsam dışı (GM2 talimatı, D012/D013'e ertelendi — DOKUNULMADI):** para birimi/birim
  tablo geçişi, satır bazlı KDV, çoklu döviz gösterimi, tahsilat/ödeme ekranı.
- **Silme yok:** K32 gereği kullanılan tanım kaydı silinmez; pasifleştirme + aktifleştirme var.
- Pasif kayıtlar mevcut belgelerde görünmeye devam eder (bilinçli: tarihsel bütünlük).
- **Sansür:** teslim ZIP'i sansürlü üretildi — D009/D010'da KÖPRÜ'nün yakaladığı aynı kalıntı
  (gerçek kişi adı ; `kod/test_d007_iyilestirmeler.py` + `docs/D007-kullanici-bildirimleri-ozet.md`)
  paketleme sırasında `MÜŞTERİ-A` / `D007-MUSTERIA` olarak sansürlendi (KÖPRÜ deseniyle birebir
  diff-doğrulandı; sansürlü test_d007 31/31 geçer). Özel repoda kaynak ad aynen durur.
