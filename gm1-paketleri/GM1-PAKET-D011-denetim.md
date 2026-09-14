# GM1-PAKET — D011 Denetim Paketi (Claude için)

> **Denetleyen:** GM1 (Claude) — D011 bağımsız denetim
> **Konu:** D011 — Tanım Verileri (Kategori & Cari Grup) + Hızlı Barkod Girişi
> **Sürüm:** v1.41.0 → **v1.42.0**
> **Coder commit:** `c97202b` (kod: `bcd964a`)
> **Tarih:** 2026-09-14
> **Direktif:** `gm-direktifleri/D011-tanimlar-hizli-barkod.md` (GM1 onaylı; kapsam A+C)

---

## 1. Nasıl denetleyeceksin (ANAYASA v12)

- **ZIP → sohbete dosya yüklemesi:** Claude web sandbox internet YOK; zip'i link'ten
  indiremezsin. Kral zip'i sohbete dosya olarak yükleyecek. Zip'i açıp kodları oku ve
  GEREKİRSE kendi ortamında testleri çalıştır.
- **.md / .txt → raw link:** raw.githubusercontent.com üzerinden metin olarak okunur.
- Karar formatı: `SONUÇ: ONAYLANDI` veya `SONUÇ: REVIZYON` + gerekçe maddeleri.
  REVIZYON ise madde madde ne düzeltilecek yaz.

## 2. Kaynaklar

### ZIP (sansürlü — kral yükleyecek)
`paketler/BRN-Teknoloji-ERP-v1.42.0-D011-GM1-denetim.zip`
- MD5: `1624062a26ac9a5ba7791709072f18ab`
- SHA256: `463a6327dd731a7c2736e4017da5c076bf9ae9d800f1b28b16fef983aae32afe`
- İçerik: 274 dosya, PNG yok, `data/yedek` yok, demo seed'li DB var (66 tablo, FK=0).

### Kod (raw link, metin — `kod-inceleme/D011/`)
- `kod-inceleme/D011/D011-diff.txt` — D010→D011 tam diff (1076 satır)
- `kod-inceleme/D011/D011-degisen-dosyalar.txt` — değişen dosya listesi
- `kod-inceleme/D011/stok.py.txt` — `/api/kategori/ekle`
- `kod-inceleme/D011/cari.py.txt` — `/api/cari_grup/ekle` + aktif filtre
- `kod-inceleme/D011/ayarlar.py.txt` — `/ayarlar/tanimlar` + durum toggle
- `kod-inceleme/D011/teklif.py.txt` — barkod action
- `kod-inceleme/D011/tanimlar.html.txt` — yeni Tanımlar şablonu
- `kod-inceleme/D011/test_d011_tanimlar_barkod.py.txt` — yeni test (21 kontrol)
- `kod-inceleme/D011/D011-test-ciktisi.txt` — test_d011 çıktısı
- `kod-inceleme/D011/D011-tam-regresyon.txt` — tam regresyon (26 dosya/582/0)
- `kod-inceleme/D011/config.py.txt` — SURUM 1.42.0

### Süreç belgeleri (raw link)
- Direktif: `gm-direktifleri/D011-tanimlar-hizli-barkod.md`
- Coder raporu: `coder-raporlari/R011-tanimlar-hizli-barkod.md`

## 3. Denetim kontrol listesi (kabul kriterleri)

- [ ] `POST /api/kategori/ekle` — boş ad 400; `lower(ad)`+`sirket_id` **idempotent**; `INSERT kategori(ad, aktif=1, sirket_id)` + audit
- [ ] `POST /api/cari_grup/ekle` — aynı desen; **`tip='Bölge'` varsayılan** + audit
- [ ] Yetki: kategori `STOK_WRITE`, grup `WRITE_ROLES`; `POST /ayarlar/tanimlar*` yalnız Admin (403 diğerleri)
- [ ] Form butonları: `stok/form.html` `＋ Kategori` + `cari/form.html` `＋ Grup` (D007 `＋ Marka` deseni, sayfa yenilenmez)
- [ ] Ayarlar→Tanımlar: kategori + cari grup listesi + **pasifleştir/aktifleştir**; **silme YOK (K32)**
- [ ] Pasif kayıt yeni belgelerde seçilemez (`_kategoriler` + `db_tmp_gruplar(aktif=True)`); mevcut kayıtlar bozulmaz
- [ ] K1 şirket izolasyonu (kategori + cari grup)
- [ ] Hızlı barkod: fatura/irsaliye/teklif formunda `barkod_sec` input; Enter→`action=barkod`→satır; bulunamazsa uyarı; `teklif.py`'ye barkod action EKLENDİ; typeahead'e dokunulmadı
- [ ] **Yeni tablo / migration YOK**
- [ ] `test_d011_tanimlar_barkod.py` + tam regresyon (26 dosya) yeşil
- [ ] ZIP (sansürlü, PNG'siz, demo seed'li DB) + MD5/SHA256

## 4. Köprü bağımsız doğrulaması (GM1 referansı)

- `test_d011_tanimlar_barkod.py` → **21/21** ✅
- Tam regresyon 26 dosya → **582 kontrol, 0 başarısız** ✅
- Zip MD5/SHA256 birebir ✅; 274 dosya; PNG/`data/yedek`/`__pycache__` yok; demo DB temiz (FK=0) ✅
- **Sansür bu pakette coder tarafından yapıldı** (D010'da kayda geçen tekrarlayan kusur giderildi):
  `kod/test_d007_iyilestirmeler.py` + `docs/D007-kullanici-bildirimleri-ozet.md` içindeki
  gerçek kişi adı → `MÜŞTERİ-A` / `D007-MUSTERIA`; **KÖPRÜ'nün D009 sansürüyle diff-birebir
  doğrulandı**; sansürlü `test_d007` 31/31 geçer.

## 5. Bilinen sapma

Yok. Kapsam GM1'in onayladığı direktife göre **A (Kategori + Cari Grup) + C (hızlı barkod)**
ile sınırlı; para birimi/birim ve satır bazlı KDV/çoklu döviz/tahsilat **D012/D013'e** ertelendi,
bu pakette DOKUNULMADI.
