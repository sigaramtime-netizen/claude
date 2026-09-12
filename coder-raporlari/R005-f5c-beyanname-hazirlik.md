# R005 — F5-C Beyanname Hazırlık Raporları (v1.37.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D005 (F5-C Beyanname Hazırlık Raporları Cilası)
- **Sürüm:** 1.36.0 → **1.37.0**
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-12
- **Commit:** `[CODER] D005 F5-C beyanname hazirlik raporlari v1.37.0 (4 kart + KDV oran SVG + /api/beyanname/ozet + kdv/csv)`

---

## 1. Yapılan İş

YENİ TABLO YOK / MIGRATION YOK — mevcut `fatura`, `yevmiye`, `gelen_belge`, `cari_hareket`
üzerinden salt-okunur raporlama cilası. GİB'e gönderim YOK (hazırlık raporu).

1. **`kod/beyanname.py`**
   - `_sayk()` + `_kdv_oran_svg(rows)` — inline SVG ikili bar (matrah `#4f8cff` / KDV `#f0a34a`),
     harici kütüphane YOK.
   - `beyanname_index` — üst özet kart verisi (`aktif` = seçili ay satırı), `oran_s_svg` /
     `oran_a_svg`, `eslesmemis_adet` template'e aktarılır.
   - `GET /api/beyanname/ozet?ay=YYYY-MM` (roles=(), K1) → `ay, hesaplanan, indirilecek,
     odenecek, devreden_sonraki, devreden_tablo[12], gecici_vergi{ceyrek,matrah,odenecek},
     nakit{odenecek}, eslesmemis_adet`. `odenecek = max(0, hesaplanan − indirilecek − devreden_on)`
     (`_devreden_satirlar` formülü korundu).
   - `GET /beyanname/kdv/csv?yil=YYYY` (roles=Admin/Muhasebe) → `;` ayraçlı CSV,
     `attachment; filename="kdv-devreden-YYYY.csv"`; 12 aylık devredenli cetvel.
   - `/beyanname/denetim/csv` yetkisi **Admin/Muhasebe**'ye çekildi (direktif C maddesi).
2. **`kod/templates/beyanname/index.html`** — 4 KPI kart + Geçici Vergi matrah/ödenecek rozeti,
   eşleşmemiş gelen belge uyarı kartı (kırmızı badge), KDV oran dağılımı ikili bar SVG'ler,
   "⬇️ KDV Devreden CSV" düğmesi.
3. **`kod/config.py`** — `SURUM = "1.37.0"`.
4. **`kod/test_f5c_beyanname.py`** — 18 kontrol (canlı sunucuya HTTP), MARK=F5CTEST,
   K1 izolasyon, temizlik ile kalıntı bırakmaz.

## 2. Direktife Uygunluk (kontrol listesi)

| Direktif maddesi | Durum |
|---|---|
| Yeni tablo / migration ekleme | ✅ YOK |
| GİB'e gönderim kodu ekleme | ✅ YOK (hazırlık raporu) |
| KDV formülü değişmedi | ✅ (_devreden_satirlar/_gecici_vergi/_nakit_kdv) |
| Harici grafik kütüphanesi YOK | ✅ inline SVG |
| `finansal._cogs_aylik` COGS yöntemi değişmedi | ✅ |
| K1 sirket_id filtresi korundu | ✅ |
| CSV'ler Admin/Muhasebe (Depo 403) | ✅ |
| F1/F5-A/F5-B bozulmadı | ✅ |
| 18 kontrol + canlı HTTP + F5CTEST kalıntısız | ✅ |

## 3. Test Sonuçları

```
python3 test_f5c_beyanname.py  → 18/18
python3 test_f5b_demirbas.py   → 18/18
python3 test_f5a_finansal.py   → 18/18
python3 test_f4_edonusum.py    → 22/22
Tam regresyon (21 dosya)       → 478/478, 0 başarısız
pytest                         → collected 0 items (proje pytest kullanmaz)
```

Regresyon dökümü: alinan_teklif 23, bakim 29, belge_sayac 9, coklu_sirket 16, crm 25,
eksik_teslimat 21, f1_mali 25, f2_kdv 34, f3_arama 30, f4_edonusum 22, f5a_finansal 18,
f5b_demirbas 18, **f5c_beyanname 18**, izolasyon 22, izolasyon_mali 19, manuel_satir 28,
pos 41, satin_alma 23, silme 23, sirket_yonetimi 19, teklif_siparis_manuel 15 = **478**.

## 4. Teslim (ZİPSİZ PROTOKOL)

- `kanitlar/v1.37.0/kanit_f5c_dosya_listesi.txt` — find + git status
- `kanitlar/v1.37.0/kanit_f5c_degisen_dosyalar.txt` — değişen kritik dosyalar (tam içerik)
- `kanitlar/v1.37.0/kanit_f5c_test_ciktisi.txt` — F5C 18/18 + F5B/F5A/F4 spot + tam regresyon
  478/478 (tek geçiş + sayaç) + pytest
- `kanitlar/v1.37.0/kanit_f5c_ozet_hash.txt` — zaman damgası + sha256
- `docs/F5C-beyanname-hazirlik-ozet.md` — özet
- `coder-raporlari/R005-f5c-beyanname-hazirlik.md` — bu rapor
- `config.py` — SURUM 1.37.0

## 5. Notlar

- Yerel kumhavuzu veritabanı (`kod/data/erp.db`, gitignore'da) tekrarlanan F4 koşularıyla
  `stok_seviye` (stok 3 / depo 1) tükendiği için F4 test 3 geçici kırmızı gördü (F4 test
  temizliği `stok_seviye`'yi geri yüklemez; seed değeri `db.py`'de 8.0). Bu bir KOD regresyonu
  değildir. Kanıt için DB taze seed ile yeniden kuruldu ve tam regresyon 478/478 temiz kaydedildi.
  GM taze klonda aynı sonucu alır.
- Grafikler inline SVG; ayrı `static/js` eklenmedi. Ekran görüntüsü (PNG) istenirse Playwright ile üretilir.
