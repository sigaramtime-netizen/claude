# R007 — Kullanıcı Bildirimleri & UX/İş Mantığı İyileştirmeleri (v1.39.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D007 (10 maddelik kullanıcı bildirimi; 1 kritik + 3 yüksek)
- **Sürüm:** 1.38.0 → **1.39.0**
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-12
- **Commit:** `7aa85cd [CODER] D007 Kullanıcı Bildirimleri & İyileştirmeler v1.39.0`

---

## 1. Yapılan İş (madde madde)

| # | Madde | Çözüm |
|---|-------|-------|
| 1 | KDV dahil/hariç açılır liste | `fatura/irsaliye/siparis/teklif/pos` formlarında checkbox → `<select name="kdv_dahil">` (0=Hariç, 1=Dahil); PY parse `in ("1","dahil","on")` geriye dönük uyumlu; `form-satir.js` + `pos/satis.html` JS `value==='1'` okuyor |
| 2 | **KRİTİK** Stok marka/model inline ekleme | `POST /api/marka/ekle` (Ajax, JSON, `sirket_id=db.sirket_id`, büyük/küçük harf duyarsız idempotent) + stok formunda `＋ Marka` butonu (`prompt` → fetch → `<option>` ekle + seç, reload YOK) + Model input alanı |
| 3 | Stok kart 8 ek alan | migrasyon: `stok_kart` + `tevkifat_orani REAL DEFAULT 0`, `istisna_kodu`, `grubu`, `ana_grup`, `alt_grup`, `ozel_kod1/2/3`, `model` (idempotent `pragma_table_info`); form "Ek Bilgiler" kartı, detay tablosu, `stok.py` INSERT/UPDATE |
| 4 | Typeahead TTEC filtre bug | `api.py _stok_ara` ORDER BY sadeleştirildi (kod önek sırası), `seri_lot_takibi`/`varyant_takibi` alanları eklendi; seed'e `TV-40-TTEC-010` + `marka TTEC` eklendi; e2e doğrulandı (`T`→geniş, `TTEC`→1) |
| 5 | İrsaliye döviz USD/EUR/GBP | `irsaliye` + `doviz_kur REAL DEFAULT 1` (migrasyon); formda Döviz select + Kur input (TRY→kur=1 kilit); `_cari_uygula_irsaliye` borç/alacak TL karşılığı (K18), `muhasebe._irsaliye_satirlar` kur çevrimi; detay/yazdırda `USD ≈ TL` notu |
| 6 | Eksi stok izni | `irsaliye._stok_kontrol_ve_uygula` kontrol bloğu → `hatalar` boş, `[UYARI]` log; seviye eksiye iner, iptalde geri döner. Fatura stok'a zaten dokunmuyor (kontrol yok) |
| 7 | Cari kartoteks typeahead | `kartoteks/cari.html` select → typeahead (`data-tip=cari` + `ta:select` auto-submit) |
| 8 | MÜŞTERİ-A 2 irsaliye (alış+satış) bug | `_cari_rows`/`cari_ekstre` tüm belge tiplerini aldığı doğrulandı; `HerIkisi` cari ile e2e test (borç 1000 + alacak 500 → 2 satır + bakiye 500) |
| 9 | Detay sayfalarında Sil butonu | `fatura/irsaliye/siparis/teklif` detayda `🗑 Sil` (confirm, Taslak koşullu) mevcut — doğrulandı |
| 10 | Tüm select'lerde manuel arama | `kasa/banka/cek_senet` cari, `garanti/stok hareket/sayım/transfer` stok select'leri → typeahead; `grep 'select name=cari_id|stok_id'` = 0 |

## 2. Direktife Uygunluk (kontrol listesi)

| Direktif maddesi | Durum |
|---|---|
| Yeni tablo YOK; yalnız stok_kart +8 alan + irsaliye.doviz_kur | ✅ |
| Migrasyon idempotent (PRAGMA), geriye dönük uyumlu | ✅ |
| Yeni FK/UNIQUE yok | ✅ |
| Harici kütüphane yok | ✅ |
| Kritik madde 2 (stok marka inline) önce | ✅ |
| `/api/ara` limit 20 korundu | ✅ |
| K1 `sirket_id` + şube izolasyonu asla kaldırılmadı | ✅ |
| F6/F5/F4/F1 regresyonları korundu | ✅ |
| Her madde madde madde test edildi | ✅ |
| `test_d007_iyilestirmeler.py` (≥22 kontrol) | ✅ 30 kontrol |

## 3. Test Sonuçları

```
python3 test_d007_iyilestirmeler.py  → 30/30 başarılı
Tam regresyon (23 dosya)            → 526/526, 0 başarısız
pytest                              → no tests ran (proje pytest kullanmaz — dürüst gösterim)
PRAGMA foreign_key_check            → 0 satır
D007TEST kalıntısı                  → 0
```

Regresyon dökümü: alinan_teklif 23, bakim 29, belge_sayac 9, coklu_sirket 16, crm 25,
**d007 30**, eksik_teslimat 21, f1_mali 25, f2_kdv 34, f3_arama 30, f4_edonusum 22,
f5a 18, f5b 18, f5c 18, f6 18, izolasyon 22, izolasyon_mali 19, manuel_satir 28,
pos 41, satin_alma 23, silme 23, sirket_yonetimi 19, teklif_siparis_manuel 15 = **526**.

Not: `test_f2_kdv.py` (10.1/10.3) ve `test_f6_cila.py` (14) D007 değişikliklerine
uyarlandı — kdv checkbox→select (madde 1) ve `SURUM=1.39.0` beklenen davranış değişikliği.

## 4. Teslim (ZİPSİZ PROTOKOL)

- `kanitlar/v1.39.0/kanit_d007_dosya_listesi.txt` — git status + diff stat
- `kanitlar/v1.39.0/kanit_d007_degisen_dosyalar.txt` — değişen kritik dosyalar (tam içerik)
- `kanitlar/v1.39.0/D007-test-ciktisi.txt` — D007 30/30 (tek geçiş)
- `kanitlar/v1.39.0/D007-tam-regresyon.txt` — 23 dosya tam regresyon 526/526
- `kanitlar/v1.39.0/pytest-gosterim.txt` — pytest "no tests ran" dürüst gösterim
- `kanitlar/v1.39.0/kanit_d007_ozet_hash.txt` — zaman damgası + sha256
- `coder-raporlari/R007-kullanici-bildirimleri-iyilestirmeler.md` — bu rapor
- `config.py` — SURUM 1.39.0

## 5. Notlar

- `marka` tablosu canlı DB'de `sirket_id + UNIQUE(sirket_id, ad)` içeriyor (çoklu şirket
  migrasyonundan); inline ekleme bu şemaya uygun `sirket_id` ile yazar.
- Madde 8 için backend sorguları zaten doğruydu; e2e test (HerIkisi cari) ile teyit edildi,
  kod değişikliği gerekmedi.
- Madde 9 (detay Sil) zaten mevcuttu; buton koşulları doğrulandı.
- PNG ekran görüntüsü istenirse Playwright ile üretilir (opsiyonel).
