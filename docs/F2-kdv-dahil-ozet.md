# F2 — KDV Dahil / Hariç Fiyat Girişi · Faz Özeti (v1.32.0)

Tarih: 2026-09-11 · Paket: F (mali etki doğruluğu) · Kapsam: belge başlığına tek toggle
**"Fiyat Girişi: KDV Hariç / KDV Dahil"**; dahil girilen tutar geriye ayrıştırılır,
**DB'de her zaman NET tutulur** (mizan/kar-zarar bozulmaz).

---

## 1) Veri Modeli Özeti

- Yeni sütun: `teklif.kdv_dahil`, `siparis.kdv_dahil`, `irsaliye.kdv_dahil`, `fatura.kdv_dahil`
  → `INTEGER NOT NULL DEFAULT 0` (0 = KDV hariç giriş). İdempotent migration (`db._migrate`).
- Fiyatlar (`*_kalem.birim_fiyat`, `tutar`) **eskisi gibi NET** tutulur — hiçbir mizan/kar-zarar
  hesabı değişmez.

### Altın kural (yuvarlama)
```
net        = round(brüt / (1 + kdv/100), 2)      # core.kdv_ayikla
kdv_tutarı = round(net * kdv / 100, 2)            # core.kdv_hesapla (brüt-net farkı DEĞİL)
genel      = net + kdv_tutarı
```
Örnek: %20, 120 TL dahil → net 100.00, KDV 20.00. %18, 115 TL dahil → net 97.46, KDV 17.54,
genel 115.00 (kuruş kaybı yok).

---

## 2) Ortak Yardımcı (tek kaynak — `core.py`)

| Fonksiyon | Görev |
|---|---|
| `kdv_ayikla(brut, oran)` | brüt → net (2 ondalık) |
| `kdv_hesapla(net, oran)` | net → KDV tutarı |
| `kdv_dahil_fiyat(net, oran)` | net → brüt (gösterim için) |

Hiçbir modül kendi formülünü yazmaz — 5 modül de `core.kdv_ayikla`'yı çağırır.

---

## 3) Etkilenen Modüller / Ekranlar

| Modül | Backend | Frontend |
|---|---|---|
| Teklif | `_satirlar_from_form(req, kdv_dahil)` net'e çevirir; `kdv_dahil` kaydedilir | `teklif/form.html` toggle |
| Sipariş | aynı | `siparis/form.html` toggle |
| İrsaliye | aynı (Transfer hariç toggle gösterilir) | `irsaliye/form.html` toggle |
| Fatura | aynı | `fatura/form.html` toggle |
| POS | `_sepet_from_form(req, kdv_dahil)` | `pos/satis.html` toggle + JS |

- Ortak satır JS (`static/js/form-satir.js`): toggle değişince tüm satır fiyatları anında
  net↔brüt çevrilir; toplamlar **her zaman net üzerinden** hesaplanır.
- Düzenlemede belge kendi `kdv_dahil` modunda açılır; satır verisi NET gelir, JS brüt gösterir.
- Fatura formu açıklaması dinamik: kaynaklı faturada "mali etki irsaliyede oluştu, fatura
  belgeleştirir"; irsaliyesiz/POS'ta "mali etki fatura onayında oluşur".

---

## 4) Örnek Test Senaryosu (e2e — `test_f2_kdv.py`, 34 kontrol)

1. `kdv_ayikla` doğrulukları (120/20, 118/18, 110/10 → 100).
2. `kdv_hesapla` doğrulukları (100/20 → 20, 97.46/18 → 17.54).
3. Fatura KDV **dahil** 120 → kalem net 100, genel 120, `kdv_dahil=1`.
4. Fatura KDV **hariç** 100 → kalem net 100 (dahil ile birebir aynı).
5. **Mizan etkisi eşitliği:** dahil ve hariç faturaların yevmiye fişi birebir aynı
   (`120 borç / 600 alacak 100 / 391 alacak 20`).
6. İrsaliye KDV dahil → net 100; onayda F1 mali etkisi doğru (cari 120 + fiş 120/600/391).
7. Sipariş KDV dahil → net 100.
8. Teklif KDV dahil → net 100.
9. POS KDV dahil → fatura kalem net 100, genel 120.
10. Düzenlemede toggle korunur (checkbox checked) + satır verisi NET.
11. KDV %0 → dahil/hariç fark etmez.
12. Yuvarlama: 115 brüt %18 → net 97.46 + KDV 17.54 = 115.00 (kuruş kaybı yok).
13. Bütünlük: FK temiz, yetim yevmiye yok, test kalıntısı yok.

**Sonuç:** `test_f2_kdv.py` **34/34**; tam regresyon 16 paket / **372 kontrol / 0 başarısız**
(F1 25 + eski 313 + F2 34).

---

## 5) Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `core.py` | `kdv_ayikla`, `kdv_hesapla`, `kdv_dahil_fiyat` |
| `db.py` | 4 tabloya `kdv_dahil` (+ migration) |
| `fatura.py`, `irsaliye.py`, `teklif.py`, `siparis.py` | `_satirlar_from_form(kdv_dahil)`, INSERT/UPDATE, render |
| `pos.py` | `_sepet_from_form(kdv_dahil)`, rota |
| `templates/{fatura,irsaliye,teklif,siparis}/form.html` | toggle + dinamik açıklama |
| `templates/pos/satis.html` | toggle + JS dönüşüm |
| `static/js/form-satir.js` | KDV modu + fiyat dönüşümü |
| `test_f2_kdv.py` | YENİ — 34 kontrol |
| `docs/F2-kdv-dahil-ozet.md` | bu doküman |

---

## 6) Kanıtlar

- Test: `test_f2_kdv.py` (34/34) + tam regresyon (372/372).
- Ekran görüntüleri: `docs/ekran-goruntuleri/yeni-tema/f2-*.png`.
- Sürüm: `config.py SURUM = "1.32.0"`.
