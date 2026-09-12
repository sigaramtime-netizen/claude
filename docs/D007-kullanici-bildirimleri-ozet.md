# D007 — Kullanıcı Bildirimleri & UX/İş Mantığı İyileştirmeleri (10 madde) · Faz Özeti (v1.39.0)

Tarih: 2026-09-12 · Paket: D007 · Kapsam: Kralın canlı testindeki 10 maddelik geri bildirim
listesi — 1 kritik (stok marka inline ekleme) + 3 yüksek (typeahead filtre, cari ekstre 2
irsaliye bug, eksi stok) + 6 UX/veri modeli iyileştirmesi.

Kural (GM onaylı):
- Yeni tablo **YOK**; yalnız `stok_kart` +8 alan + `irsaliye.doviz_kur` (idempotent
  `PRAGMA table_info` migrasyon, geriye dönük uyumlu). Yeni FK/UNIQUE yok; harici kütüphane yok.
- `/api/ara` limit 20 korunur; K1 `sirket_id` + şube izolasyonu asla kaldırılmaz.

---

## 1) Veri Modeli Özeti

| Tablo | Değişiklik |
|---|---|
| `stok_kart` | + `tevkifat_orani REAL DEFAULT 0`, `istisna_kodu`, `grubu`, `ana_grup`, `alt_grup`, `ozel_kod1`, `ozel_kod2`, `ozel_kod3`, `model` (idempotent migrasyon) |
| `irsaliye` | + `doviz_kur REAL DEFAULT 1` (`para_birimi` zaten vardı) |

### İş kuralları (madde → davranış)
1. KDV modu: `<select name="kdv_dahil">` 0/1; PY parse `in ("1","dahil","on")` (F2 net-kuralı korunur).
2. Marka inline: `POST /api/marka/ekle` — boş ad 400; aynı ad idempotent (mevcut id döner); `sirket_id` ile yazar.
3. 8 ek alan + model form/liste/detay + INSERT/UPDATE'te korunur.
4. `_stok_ara`: tam kod → kod öneki → ad içeren sıralaması (`TTEC`→1, `T`→geniş).
5. İrsaliye döviz: cari hareket borç/alacak **TL karşılığı** (`genel_toplam × kur`), `para_birimi`+`doviz_kur` izlemede; yevmiye TL dengeli.
6. Eksi stok: irsaliye stok kontrolü `[UYARI]` log basar, onayı **bloke etmez**; seviye eksiye iner, iptalde geri döner.
7. Kartoteks cari: typeahead + `ta:select` auto-submit.
8. Cari ekstre/kartoteks: alış + satış irsaliyesi **iki ayrı satır**, toplam borç/alacak doğru.
9. Detay sayfaları: fatura/irsaliye/sipariş/teklif `🗑 Sil` (Taslak koşullu, confirm).
10. Tüm cari/stok `select`'leri typeahead (`grep 'select name=cari_id|stok_id'` = 0).

---

## 2) Ekran Listesi (etkilenen)

| Rota | Etki |
|---|---|
| `POST /api/marka/ekle` | YENİ — marka inline ekleme (Ajax/JSON) |
| `GET/POST /stok/yeni` · `/stok/<id>/duzenle` | +Model +8 ek alan + `＋ Marka` butonu |
| `GET /stok/<id>` | detayda ek bilgiler tablosu |
| `/fatura\|irsaliye\|siparis\|teklif/yeni` + POS | KDV dahil/hariç `<select>` |
| `/irsaliye/yeni` | döviz select + kur input |
| `GET /kartoteks/cari` · `/kartoteks/stok` | typeahead seçici |
| kasa/banka/çek-senet/garanti/stok hareket/sayım/transfer | typeahead (madde 10) |

---

## 3) Örnek Test Senaryosu (e2e — `test_d007_iyilestirmeler.py`, 30 kontrol)

1. KDV select: `kdv_dahil=1` + bf 118 (KDV %18) → DB'ye net 100 (fatura + irsaliye).
2. Marka inline: `POST /api/marka/ekle` → 200 + id; boş ad 400; aynı ad idempotent.
3. Stok 8 alan + model: kaydet → oku → güncelle → değerler korunur.
4. Typeahead: `q=TTEC` → tam 1 kayıt; `q=T` → >1 kayıt.
5. İrsaliye USD: 100 USD × kur 30 → cari 3000 TL + yevmiye borç=alacak=3000.
6. Eksi stok: seviye 8 → satış 10 onay başarılı → seviye -2 → iptal → 8.
7. Kartoteks typeahead: `MÜŞTERİ-A` filtre → 1 kayıt.
8. MÜŞTERİ-A (HerIkisi): satış 1000 (borç) + alış 500 (alacak) → 2 satır + bakiye 500.
9. Detay Sil butonu: 4 belge detayında `/sil` formu.
10. Typeahead genelleme: `select name=cari_id|stok_id` kalıntısı 0.
11. Regresyon: F6/F5c/F5b/F1 endpoint'leri 200; K1 başka şirkette D007 verisi yok.
12. Bütünlük: `PRAGMA foreign_key_check` = 0; D007TEST kalıntısı yok.

**Sonuç:** `test_d007_iyilestirmeler.py` **30/30**; tam regresyon (23 dosya)
**526/526, 0 başarısız** (hedef ~518 aşıldı).

---

## 4) Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `db.py` | migrasyon (stok_kart +8 alan + model, irsaliye.doviz_kur); seed'e TTEC ürün+marka |
| `api.py` | `_stok_ara` ORDER BY + `seri_lot_takibi`/`varyant_takibi` alanları |
| `stok.py` | `POST /api/marka/ekle`; 8 alan + model parse/INSERT/UPDATE |
| `irsaliye.py` | döviz parse + INSERT/UPDATE; `_cari_uygula_irsaliye` TL çevrim; eksi stok kontrolü |
| `muhasebe.py` | `_irsaliye_satirlar` döviz kur çevrimi |
| `fatura.py` / `siparis.py` / `teklif.py` / `pos.py` | `kdv_dahil` parse |
| `static/js/form-satir.js` + `pos/satis.html` | kdv select okuma + para sembolü |
| 10+ şablon (fatura/irsaliye/siparis/teklif/pos/kartoteks/kasa/banka/cek_senet/garanti/stok) | KDV select + typeahead dönüşümleri |
| `config.py` | `SURUM = "1.39.0"` |
| `test_d007_iyilestirmeler.py` | YENİ — 30 kontrol |

---

## 5) Kanıtlar

- Test: `test_d007_iyilestirmeler.py` (30/30) + regresyon (526/526).
- `PRAGMA foreign_key_check` boş; D007TEST kalıntısı yok.
- Sürüm: `config.py SURUM = "1.39.0"`.
