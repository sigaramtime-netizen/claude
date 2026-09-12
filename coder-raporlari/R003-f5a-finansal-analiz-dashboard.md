# R003 — F5-A Finansal Analiz & Dashboard (v1.35.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D003 (F5-A Finansal Analiz & Dashboard Cilası)
- **Sürüm:** 1.34.0 → **1.35.0**
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-11
- **Commit:** `[CODER] D003 F5-A finansal analiz dashboard v1.35.0 (butce_hedef + /api/finansal/ozet + 6 kart + inline SVG)`

---

## 1. Yapılan İş

1. **`kod/db.py`** — `_migrate()` içine idempotent `butce_hedef` tablosu eklendi
   (`IF NOT EXISTS`, `UNIQUE(sirket_id, yil, ay)`, K1 FK `REFERENCES sirket(id)`).
   Başka yeni tablo eklenmedi; eski `butce` tablosu ve seed'i korundu.
2. **`kod/finansal.py`**
   - Bütçe CRUD'u `butce_hedef` üzerine taşındı: `GET /finansal/butce`,
     `POST /finansal/butce/kaydet` (upsert), `POST /finansal/butce/<id>/sil`.
   - `GET /api/finansal/ozet?donem=aylik|haftalik` eklendi (satis, alis, kar,
     tahsilat, tediye, banka_bakiye, nakit_akis[30 gün], en_cok_satan, en_karli,
     en_cok_ciro_cari, donem_karsilastirma, butce).
   - Kâr = **fatura kalem tutar − (stok.alis_fiyat × miktar)** (satış fiyatı DEĞİL).
   - Nakit akışı: kasa + banka, transfer/açılış hariç; son 30 gün günlük net.
   - Yetki: `FINANSAL_GOR = ("Admin", "Muhasebe")`; `/finansal*` ve `/api/finansal/ozet`
     yalnız bu roller (Depo → 403).
3. **`kod/app.py`** — dashboard `/` route'u `finansal.py` yardımcılarıyla beslendi:
   `bu_ay_kar`, `banka_toplam`, `butce` (hedef + sapma) + dönem seçici anahtarları.
4. **`kod/templates/dashboard.html`** — üstte "Finansal Özet" bloğu: 6 kart
   (Bugün Satış, Bu Ay Satış [bütçe sapma rozeti], Bu Ay Kâr, Kasa Toplam,
   Banka Toplam, Açık Servis) + Bu Ay/Geçen Ay/Geçen Yıl bağlantıları.
   Mevcut KPI kartları korundu.
5. **`kod/templates/finansal/butce.html`** — hedef formu + yıl tablosu
   (hedef_satis/hedef_kar, gerçekleşen, sapma %) + silme.
6. **`kod/templates/finansal/index.html`** — analiz ekranı korundu; bütçe karşılaştırma
   kartı eklendi (hedef/gerçekleşen satış & kâr + sapma rozeti).
7. **`kod/config.py`** — `SURUM = "1.35.0"`, `SURUM_TARIHI = "2026-09-11"`.
8. **`kod/test_f5a_finansal.py`** — 18 kontrol (canlı sunucuya HTTP), MARK=F5ATEST,
   K1 izolasyon, temizlik ile kalıntı bırakmaz.

## 2. Direktife Uygunluk (kontrol listesi)

| Direktif maddesi | Durum |
|---|---|
| Yeni tablo yalnız `butce_hedef` | ✅ |
| Migration idempotent (`IF NOT EXISTS`) | ✅ |
| K1: her sorgu `sirket_id` süzgeci | ✅ |
| Seed yok, boş başlar | ✅ |
| Bütçe kaydı mali tabloya dokunmaz | ✅ (test 16: cari/yevmiye artmadı) |
| Kâr = kalem tutar − alis_fiyat×miktar | ✅ (test 7: 1000−700=300) |
| Bütçe otomatik üretilmez (manuel) | ✅ |
| Harici bağımlılık YOK (Chart.js CDN dahil) | ✅ inline SVG |
| Finansal Analiz yalnız Yönetici+Muhasebe | ✅ (test 15: Depo 403) |
| F1/F2/F3/F4 bozulmaz | ✅ (F4 22/22, F1/F2/F3 yeşil, typeahead /api/ara) |
| 18 kontrol + canlı HTTP + F5ATEST kalıntısız | ✅ |

## 3. Test Sonuçları

```
python3 test_f5a_finansal.py   → 18/18
python3 test_f4_edonusum.py    → 22/22
Tam regresyon (19 test dosyası) → 442/442, 0 başarısız
pytest                          → collected 0 items (proje pytest kullanmaz — dürüst gösterim)
```

Regresyon dökümü: alinan_teklif 23, bakim 29, belge_sayac 9, coklu_sirket 16, crm 25,
eksik_teslimat 21, f1_mali 25, f2_kdv 34, f3_arama 30, f4_edonusum 22, **f5a_finansal 18**,
izolasyon 22, izolasyon_mali 19, manuel_satir 28, pos 41, satin_alma 23, silme 23,
sirket_yonetimi 19, teklif_siparis_manuel 15 = **442**.

## 4. Teslim (ZİPSİZ PROTOKOL)

- `kanitlar/v1.35.0/kanit_f5a_dosya_listesi.txt` — find + git status
- `kanitlar/v1.35.0/kanit_f5a_degisen_dosyalar.txt` — değişen kritik dosyalar (tam içerik)
- `kanitlar/v1.35.0/kanit_f5a_test_ciktisi.txt` — F5A 18/18 + F4 22/22 + tam regresyon 442/442 + pytest
- `kanitlar/v1.35.0/kanit_f5a_ozet_hash.txt` — zaman damgası + sha256
- `docs/F5A-finansal-analiz-ozet.md` — özet
- `coder-raporlari/R003-f5a-finansal-analiz-dashboard.md` — bu rapor
- `config.py` — SURUM 1.35.0

## 5. Notlar

- Direktifteki `finansal/analiz.html` adı projede `templates/finansal/index.html`'e karşılık
  gelir; analiz ekranı korunup bütçe karşılaştırma kartı eklendi (ayrı dosya açılmadı).
- Grafikler sunucu tarafı inline SVG üretilir; `static/js/finansal.js` gerekmedi.
- Ekran görüntüsü (PNG) isterseniz ayrıca üretilir (Playwright opsiyonel).
