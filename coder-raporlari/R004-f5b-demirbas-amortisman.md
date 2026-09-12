# R004 — F5-B Demirbaş & Amortisman Raporlama (v1.36.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D004 (F5-B Demirbaş & Amortisman Raporlama Cilası)
- **Sürüm:** 1.35.0 → **1.36.0**
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-11
- **Commit:** `[CODER] D004 F5-B demirbas amortisman raporlama v1.36.0 (plan + kategori özet + /api/demirbas/ozet + CSV + SVG)`

---

## 1. Yapılan İş

YENİ TABLO YOK / MIGRATION YOK — yalnızca mevcut 4 tablo üzerine raporlama cilası.

1. **`kod/demirbas.py`**
   - `_amortisman_plan(conn, d, ay=12)` — gelecek 12 ay plan (üretilmiş=gerçek,
     üretilmemiş=tahmini; kalan bakiye bitince durur).
   - `_kategori_ozet(conn, sid)` — kategori → adet/maliyet/birikmiş/net (K1).
   - `_line_svg(...)` — inline SVG çizgi grafik (mor `#8b5cf6`), harici kütüphane YOK.
   - `demirbas_index` — 4 KPI (Toplam Maliyet / Birikmiş / Net / Aktif Adet) +
     kategori özet tablosu + satır başına durum rozeti
     (🟢 Aktif `b-ok` / 🟡 Tamamlandı `b-warn` / 🔴 Satıldı·Hurda `b-danger`).
   - `demirbas_detay` — plan tablosu + birikmiş çizgi grafiği (mevcut amortisman
     tablosu ve zimmet takibi korundu).
   - `GET /api/demirbas/ozet` (roles=(), K1) — `toplam_maliyet, toplam_birikmis,
     toplam_net, aktif_adet, kategori_ozet[], yaklasan_bitis[]` (0–3 ay kalanlar).
   - `GET /demirbas/amortisman/csv?yil=YYYY` (roles=Admin/Muhasebe) — BOM + `;` ayraçlı
     CSV, `attachment; filename="amortisman-YYYY.csv"`.
2. **`kod/templates/demirbas/index.html`** — 4 KPI + kategori özet + rozet + CSV düğmesi.
3. **`kod/templates/demirbas/detay.html`** — plan tablosu + SVG grafik.
4. **`kod/config.py`** — `SURUM = "1.36.0"`.
5. **`kod/test_f5b_demirbas.py`** — 18 kontrol (canlı sunucuya HTTP), MARK=F5BTEST,
   K1 izolasyon, temizlik ile kalıntı bırakmaz.

## 2. Direktife Uygunluk (kontrol listesi)

| Direktif maddesi | Durum |
|---|---|
| Yeni tablo ekleme (migration yok) | ✅ |
| `demirbas_amortisman` UNIQUE'si + K1 korundu | ✅ |
| Amortisman formülü değişmedi (taban/(ömür×12)) | ✅ |
| Harici grafik kütüphanesi YOK (inline SVG) | ✅ |
| `_amortisman_uret` idempotent kaldı | ✅ |
| `demirbas_zimmet` değişmedi | ✅ |
| CSV yalnız Admin/Muhasebe (Depo 403) | ✅ |
| F1/F5-A bozulmadı | ✅ (cari_hareket artmadı; /finansal 200) |
| 18 kontrol + canlı HTTP + F5BTEST kalıntısız | ✅ |

## 3. Test Sonuçları

```
python3 test_f5b_demirbas.py  → 18/18
python3 test_f5a_finansal.py  → 18/18
python3 test_f4_edonusum.py   → 22/22
Tam regresyon (20 dosya)      → 460/460, 0 başarısız
pytest                        → collected 0 items (proje pytest kullanmaz)
```

Regresyon dökümü: alinan_teklif 23, bakim 29, belge_sayac 9, coklu_sirket 16, crm 25,
eksik_teslimat 21, f1_mali 25, f2_kdv 34, f3_arama 30, f4_edonusum 22, f5a_finansal 18,
**f5b_demirbas 18**, izolasyon 22, izolasyon_mali 19, manuel_satir 28, pos 41,
satin_alma 23, silme 23, sirket_yonetimi 19, teklif_siparis_manuel 15 = **460**.

## 4. Teslim (ZİPSİZ PROTOKOL)

- `kanitlar/v1.36.0/kanit_f5b_dosya_listesi.txt` — find + git status
- `kanitlar/v1.36.0/kanit_f5b_degisen_dosyalar.txt` — değişen kritik dosyalar (tam içerik)
- `kanitlar/v1.36.0/kanit_f5b_test_ciktisi.txt` — F5B 18/18 + F5A 18/18 + F4 22/22 +
  tam regresyon 460/460 + pytest
- `kanitlar/v1.36.0/kanit_f5b_ozet_hash.txt` — zaman damgası + sha256
- `docs/F5B-demirbas-amortisman-ozet.md` — özet
- `coder-raporlari/R004-f5b-demirbas-amortisman.md` — bu rapor
- `config.py` — SURUM 1.36.0

## 5. Notlar

- Yerel kumhavuzu veritabanı (`kod/data/erp.db`, gitignore'da) tekrarlanan F4 test
  koşularıyla `stok_seviye` (stok 3 / depo 1) 8→0 tükendiği için F4 test 3 geçici olarak
  kırmızı gördü. Bu bir KOD regresyonu değildir; seed değeri `db.py`'de 8 olarak durur.
  Kanıt için DB taze seed ile yeniden kuruldu (`rm data/erp.db` + yeniden başlat) ve
  tam regresyon 460/460 temiz kaydedildi. GM taze klonda aynı sonucu alır.
- Grafikler inline SVG; ayrı `static/js` eklenmedi.
- Ekran görüntüsü (PNG) istenirse Playwright ile ayrıca üretilir.
