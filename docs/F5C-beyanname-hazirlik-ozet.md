# F5-C Beyanname Hazırlık Raporları — v1.37.0

**Görev:** D005 (F5-C) · **Durum:** KODLANDI ✅
**Tarih:** 2026-09-12 · **Önceki:** D004/F5-B v1.36.0

---

## 1. Ne Yapıldı

Beyanname modülü çalışıyordu (KDV tahakkuk/nakit, Geçici Vergi, Muhtasar, denetim + CSV)
ama cilasızdi. Bu pakette **yeni tablo YOK** — mevcut `fatura`, `yevmiye`, `gelen_belge`,
`cari_hareket` üzerinden salt-okunur raporlama cilası. GİB'e gönderim YOK (hazırlık raporu).

| # | Alt Modül | Durum |
|---|-----------|-------|
| 1 | Özet Kartlar (Hesaplanan/İndirilecek/Ödenecek/Devreden + Geçici Vergi rozeti) | ✅ |
| 2 | KDV Oran Dağılımı Grafik (satış + alış, inline SVG ikili bar — matrah+KDV) | ✅ |
| 3 | API Özet Ucu `GET /api/beyanname/ozet?ay=YYYY-MM` | ✅ |
| 4 | KDV Devreden CSV `GET /beyanname/kdv/csv?yil=YYYY` (12 aylık cetvel) | ✅ |
| 5 | Gelen Eşleşmemiş Vurgu (kırmızı badge) + Denetim koruması | ✅ |

## 2. Veri Modeli

YENİ TABLO YOK / MIGRATION YOK. KDV formülü korundu:
`_devreden_satirlar`, `_gecici_vergi` (COGS matrahı, %25), `_nakit_kdv` — değişmedi.

## 3. Backend — `beyanname.py`

- `_sayk()` + `_kdv_oran_svg(rows)` — inline SVG ikili bar (matrah `#4f8cff` / KDV `#f0a34a`).
- `beyanname_index` — üst özet kart verisi (`aktif` = seçili ay satırı) + `oran_s_svg` /
  `oran_a_svg` + `eslesmemis_adet` template'e aktarılır.
- `GET /api/beyanname/ozet?ay=YYYY-MM` (roles=(), K1) → `ay, hesaplanan, indirilecek,
  odenecek, devreden_sonraki, devreden_tablo[12], gecici_vergi{ceyrek,matrah,odenecek},
  nakit{odenecek}, eslesmemis_adet`. `odenecek = max(0, hesaplanan − indirilecek − devreden_on)`.
- `GET /beyanname/kdv/csv?yil=YYYY` (roles=Admin/Muhasebe) → `;` ayraçlı CSV,
  `attachment; filename="kdv-devreden-YYYY.csv"`; başlık:
  `Ay; Hesaplanan KDV; Indirilecek KDV; Devreden (Onceki); Odenecek; Devreden (Sonraki)`;
  12 satır (`_devreden_satirlar(kdv, yil, 0)`).
- `/beyanname/denetim/csv` yetkisi **Admin/Muhasebe**'ye çekildi (direktif C maddesi).

## 4. Frontend — `templates/beyanname/index.html`

- Üstte 4 KPI kart (Bu Ay Hesaplanan KDV + GM 391, İndirilecek KDV + GM 191,
  Ödenecek KDV (devreden düşülmüş), Devreden KDV sonraki ay) + Geçici Vergi matrah/ödenecek rozeti.
- Eşleşmemiş gelen belge uyarı kartı (kırmızı badge; 0 ise yeşil "temiz").
- KDV Oran Dağılımı kartlarına ikili bar SVG eklendi (tablo korundu).
- "⬇️ KDV Devreden CSV" düğmesi (yalnız Admin/Muhasebe görür).

## 5. Test Kanıtı

```
python3 test_f5c_beyanname.py  → 18/18 (canlı sunucuya HTTP, F5CTEST kalıntısız)
python3 test_f5b_demirbas.py   → 18/18 (F5-B bozulmadı)
python3 test_f5a_finansal.py   → 18/18 (F5-A bozulmadı)
python3 test_f4_edonusum.py    → 22/22 (F4 bozulmadı)
Tam regresyon (21 dosya)       → 478/478, 0 başarısız
pytest                         → collected 0 items (proje pytest kullanmaz — dürüst gösterim)
```

## 6. Sürüm

- `kod/config.py`: `SURUM = "1.37.0"`, `SURUM_TARIHI = "2026-09-11"`
