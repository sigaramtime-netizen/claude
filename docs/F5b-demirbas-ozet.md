# F5-B — Demirbaş & Amortisman Raporlama · Faz Özeti (v1.36.0)

Tarih: 2026-09-11 · Paket: F5-B (D004) · Kapsam: Demirbaş modülünün raporlama cilası —
amortisman plan önizleme, kategori özet kartları, durum rozetleri + birikmiş grafik,
API özet ucu ve CSV cetvel.

Kural (GM onaylı):
- **YENİ TABLO YOK, migration YOK** — mevcut 4 tablo üzerinden salt-okunur cila.
- Amortisman formülü değişmedi: aylık = (maliyet − hurda) / (ömür × 12).

---

## 1) Veri Modeli Özeti

Değişiklik yok. Mevcut tablolar korunur:

| Tablo | Not |
|---|---|
| `demirbas_kategori` | kategori |
| `demirbas` | kart (kod/ad/maliyet/hurda/ömür/başlangıç) |
| `demirbas_amortisman` | `UNIQUE(demirbas_id, donem)` — üretilmiş aylık kayıtlar |
| `demirbas_zimmet` | zimmet/teslim takibi |

### İş kuralları
1. Plan: ilk 12 ay; `demirbas_amortisman`'da var olan aylar **gerçek**, sonrası **tahmini**
   (kalan bakiye bitince durur).
2. `/api/demirbas/ozet` (roles=(), K1) → `toplam_maliyet, toplam_birikmis, toplam_net,
   aktif_adet, kategori_ozet[], yaklasan_bitis[]` (0–3 ay içinde bitecekler).
3. CSV: BOM + `;` ayraçlı, sütunlar `Demirbas Kod; Ad; Kategori; Donem; Tutar; Birikmis;
   Net Deger; Durum`.

---

## 2) Ekran Listesi (etkilenen)

| Rota | Etki |
|---|---|
| `GET /demirbas` | 4 KPI + kategori özet tablosu + durum rozetleri + CSV düğmesi |
| `GET /demirbas/<id>` | amortisman planı (12 ay) + birikmiş çizgi grafiği |
| `GET /api/demirbas/ozet` | JSON özet (K1) |
| `GET /demirbas/amortisman/csv?yil=YYYY` | CSV cetvel (Admin/Muhasebe) |

---

## 3) Örnek Test Senaryosu (e2e — `test_f5b_demirbas.py`, 18 kontrol)

1. Amortisman planı: üretilmiş aylar gerçek değer, sonrası tahmini (formül tutarlı).
2. Kategori özeti: maliyet/birikmiş/net toplamları demirbas tablosuyla eşleşir.
3. Durum rozetleri (Aktif/Tamamlandı/Satıldı·Hurda) doğru türetilir.
4. `/api/demirbas/ozet` gerekli alanları döner + K1 izolasyonu.
5. CSV: başlık satırı + 12 aylık içerik, `attachment` header.
6. Regresyon: F5-A 18/18 + F4 22/22 bozulmadı.
7. Bütünlük: FK temiz, F5BTEST kalıntısı yok.

**Sonuç:** `test_f5b_demirbas.py` **18/18**; tam regresyon (20 dosya) **460/460, 0 başarısız**.

---

## 4) Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `demirbas.py` | `_amortisman_plan`, `_kategori_ozet`, `_line_svg`; index/detay verileri; `/api/demirbas/ozet`; CSV |
| `templates/demirbas/index.html` | 4 KPI + kategori özet + durum rozetleri + CSV düğmesi |
| `templates/demirbas/detay.html` | plan tablosu + birikmiş grafik |
| `config.py` | `SURUM = "1.36.0"` |
| `test_f5b_demirbas.py` | YENİ — 18 kontrol |

---

## 5) Kanıtlar

- Grafik: inline SVG çizgi (`_line_svg`, mor `#8b5cf6`) — harici kütüphane YOK.
- Test: `test_f5b_demirbas.py` (18/18) + regresyon (460/460).
- Sürüm: `config.py SURUM = "1.36.0"`.
