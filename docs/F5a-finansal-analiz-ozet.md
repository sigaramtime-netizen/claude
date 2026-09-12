# F5-A — Finansal Analiz & Dashboard (Bütçe + SVG Kartları) · Faz Özeti (v1.35.0)

Tarih: 2026-09-11 · Paket: F5-A (D003) · Kapsam: Yönetici/Muhasebe'ye tek bakışta satış özeti,
dönemsel karşılaştırma, nakit akışı, bütçe hedefi vs gerçekleşen ve en çok analizleri.

Kural (GM onaylı):
- Kâr hesabı **fatura kalem tutarı (TL) − (stok alış fiyatı × miktar)** üzerinden yapılır
  (satış fiyatı DEĞİL — maliyet bazlı kâr).
- Bütçe kaydı **mali etki üretmez** (cari_hareket/yevmiye'ye satır yazmaz).
- Yetki: `FINANSAL_GOR = ("Admin", "Muhasebe")` — diğer roller 403.

---

## 1) Veri Modeli Özeti

Yeni **tek tablo** (idempotent, `IF NOT EXISTS`):

| Tablo | Değişiklik |
|---|---|
| `butce_hedef` | YENİ — `id, sirket_id FK, yil, ay, hedef_satis, hedef_kar, olusturan, olusturma_tarihi`; `UNIQUE(sirket_id, yil, ay)` (K1: şirket + yıl + ay başına tek satır). |

- Eski `butce` (Gelir/Gider) tablosuna dokunulmadı; bütçe CRUD'u `butce_hedef` üzerine taşındı.
- Başka migration/FK değişikliği yok. Seed yok, boş başlar.

### İş kuralları
1. Bütçe kaydet = `ON CONFLICT(sirket_id,yil,ay) DO UPDATE` (upsert).
2. Sapma = `(gerçek − hedef) / hedef × 100` (hedef 0 ise sapma gösterilmez).
3. `GET /api/finansal/ozet?donem=aylik|haftalik` JSON döner: `satis, alis, kar, tahsilat,
   tediye, banka_bakiye, nakit_akis[30 gün], en_cok_satan, en_karli, en_cok_ciro_cari,
   donem_karsilastirma, butce{hedef, gercek, sapma}`.

---

## 2) Ekran Listesi (etkilenen)

| Rota | Etki |
|---|---|
| `GET /finansal/butce` | Bütçe hedef listesi + form (yıl/ay/hedef_satis/hedef_kar) |
| `POST /finansal/butce/kaydet` | insert/update (upsert) |
| `POST /finansal/butce/<id>/sil` | hedef sil |
| `GET /api/finansal/ozet` | JSON özet (Admin/Muhasebe) |
| `/` (dashboard) | 6 kart (Bugün Satış, Bu Ay Satış [bütçe sapma rozeti], Bu Ay Kâr, Kasa, Banka, Açık Servis) |
| `/finansal` | analiz ekranı — bütçe karşılaştırma kartı eklendi |

---

## 3) Örnek Test Senaryosu (e2e — `test_f5a_finansal.py`, 18 kontrol)

1. `butce_hedef` tablosu var; UNIQUE(sirket_id, yil, ay) uygulanıyor.
2. Bütçe kaydı → satır oluşur; aynı ay tekrar → UPDATE (mükerrer satır yok).
3. Bütçe kaydı **mali etki üretmez** (cari_hareket + yevmiye artmadı).
4. `/api/finansal/ozet` → gerekli alanlar + sapma hesabı doğru.
5. Dashboard satış özeti + kâr (maliyet bazlı) doğru.
6. Yetki: Muhasebe dışı rol `/finansal*` 403.
7. Bütünlük: FK temiz, F5ATEST kalıntısı yok.

**Sonuç:** `test_f5a_finansal.py` **18/18**; tam regresyon (19 dosya) **442/442, 0 başarısız**
(F4 22/22 dahil — bozulmadı).

---

## 4) Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `finansal.py` | `/finansal/butce*` rotaları + `/api/finansal/ozet`; kâr/özet yardımcıları |
| `db.py` | `butce_hedef` tablosu (migrasyon, idempotent) |
| `app.py` | dashboard veri beslemesi (bu_ay_kar, banka_toplam, butce sapma) |
| `templates/dashboard.html` | 6 kart + dönem bağlantıları |
| `templates/finansal/index.html` | bütçe karşılaştırma kartı (hedef/gerçekleşen + sapma) |
| `templates/finansal/butce.html` | hedef formu + yıl tablosu |
| `config.py` | `SURUM = "1.35.0"` |
| `test_f5a_finansal.py` | YENİ — 18 kontrol |

---

## 5) Kanıtlar

- Grafikler sunucu tarafı inline SVG (`_bar_svg`, `_bar2_svg`) — harici JS/kütüphane YOK.
- Test: `test_f5a_finansal.py` (18/18) + regresyon (442/442).
- Sürüm: `config.py SURUM = "1.35.0"`.
