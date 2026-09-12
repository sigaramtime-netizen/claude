# F5-B Demirbaş & Amortisman Raporlama — v1.36.0

**Görev:** D004 (F5-B) · **Durum:** KODLANDI ✅
**Tarih:** 2026-09-11 · **Önceki:** D003/F5-A v1.35.0

---

## 1. Ne Yapıldı

Demirbaş modülü çalışıyordu (kategori + kart + zimmet + aylık amortisman + GM 770/257),
ama raporlama zayıftı. Bu pakette **yeni tablo YOK** — mevcut 4 tablo üzerine raporlama cilası:

| # | Alt Modül | Durum |
|---|-----------|-------|
| 1 | Amortisman Plan Önizleme (gelecek 12 ay — üretilmiş gerçek / üretilmemiş tahmini) | ✅ |
| 2 | Kategori Bazlı Özet Kartları (4 KPI + kategori→maliyet/birikmiş/net tablosu) | ✅ |
| 3 | Durum Rozetleri (🟢 Aktif / 🟡 Tamamlandı / 🔴 Satıldı·Hurda) + birikmiş çizgi grafik (inline SVG) | ✅ |
| 4 | API Özet Ucu `GET /api/demirbas/ozet` | ✅ |
| 5 | CSV Cetvel `GET /demirbas/amortisman/csv?yil=YYYY` | ✅ |

## 2. Veri Modeli

YENİ TABLO YOK, migration YOK. Mevcut tablolar korunur:
`demirbas_kategori`, `demirbas`, `demirbas_amortisman` (UNIQUE(demirbas_id, donem)),
`demirbas_zimmet`. Amortisman formülü değişmedi: aylık = (maliyet − hurda) / (ömür × 12).

## 3. Backend — `demirbas.py`

- `_amortisman_plan(conn, d, ay=12)` — gelecek 12 ay plan (üretilmiş=gerçek, sonrası=tahmini;
  kalan bakiye bitince durur).
- `_kategori_ozet(conn, sid)` — kategori → adet/maliyet/birikmiş/net (K1 süzgeçli).
- `_line_svg(...)` — inline SVG çizgi grafik (mor `#8b5cf6`), `_bar_svg`/`_hbar_svg` deseninde.
- `demirbas_index` — 4 KPI (Toplam Maliyet, Birikmiş, Net, Aktif Adet) + kategori özet +
  satır başına durum rozeti.
- `demirbas_detay` — plan tablosu + birikmiş çizgi grafiği.
- `GET /api/demirbas/ozet` (roles=(), K1) — `toplam_maliyet, toplam_birikmis, toplam_net,
  aktif_adet, kategori_ozet[], yaklasan_bitis[]` (0–3 ay içinde bitecekler).
- `GET /demirbas/amortisman/csv?yil=YYYY` (roles=Admin/Muhasebe) — BOM + `;` ayraçlı CSV,
  `Content-Disposition: attachment; filename="amortisman-YYYY.csv"`;
  sütunlar: Demirbas Kod, Demirbas Ad, Kategori, Donem, Tutar, Birikmis, Net Deger, Durum.

## 4. Frontend — `templates/demirbas/`

- `index.html`: 4 KPI + kategori özet tablosu + durum rozetleri + "⬇️ CSV Cetvel" düğmesi.
- `detay.html`: "Birikmiş Amortisman Grafiği" (SVG) + "Amortisman Planı (gelecek 12 ay)" tablosu
  (üretilmiş/tahmini rozetli). Mevcut amortisman tablosu ve zimmet takibi korundu.

## 5. Test Kanıtı

```
python3 test_f5b_demirbas.py  → 18/18 (canlı sunucuya HTTP, F5BTEST kalıntısız)
python3 test_f5a_finansal.py  → 18/18 (F5-A bozulmadı)
python3 test_f4_edonusum.py   → 22/22 (F4 bozulmadı)
Tam regresyon (20 dosya)      → 460/460, 0 başarısız
pytest                        → collected 0 items (proje pytest kullanmaz — dürüst gösterim)
```

## 6. Sürüm

- `kod/config.py`: `SURUM = "1.36.0"`, `SURUM_TARIHI = "2026-09-11"`
