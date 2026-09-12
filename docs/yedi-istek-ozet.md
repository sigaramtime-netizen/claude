# Yedi İstek Paketi — Uygulama Özeti (v1.23.0)

> Tarih: 2026-09-08 · Durum: **Tamamlandı, uçtan uca test edildi**
> Kural: `mimari-kurallar.md` **K35** · Sürüm: `CHANGELOG.md` v1.23.0

Kullanıcının onayladığı satır ekleme akışının (K34) üzerine gelen yedi istek birlikte uygulandı.

---

## 1) Alış irsaliyesi → cari borç görünmüyor (değerlendirme + netleştirme)

- **Tasarım gereği (hata değil):** K2/K6 — irsaliye mali hareket üretmez; borç/alacak faturayla doğar.
- **K14 doğrulandı:** "Faturasız" filtresi/rozeti **alış irsaliyelerini de kapsıyor**
  (canlı test: oluşturulan alış irsaliyesi `?faturasiz=1` listesinde göründü, sonra temizlendi).
- **Netleştirme eklendi:** irsaliye detayındaki "Faturasız" kartı artık tip bilinçli:
  *Alış* → "İrsaliye cari borç üretmez — tedarikçiye borç, Alış Faturası onaylanınca doğar";
  *Satış* → "müşteri alacağı Satış Faturası onaylanınca doğar".

## 2) Stok kartına birim tipi

- `stok_kart.birim` zaten vardı; `BIRIMLER` genişletildi: **Adet, Kutu, Paket, Çift, Takım, Metre, m², Kg, Lt, Top, Rulo**.
- Belge kalemlerine `birim` kolonu eklendi; **manuel satır girişinde birim açılır listesi**.
- Stoklu satırda birim stok kartından otomatik gelir; detay + yazdırda miktarın yanında gösterilir.

## 3) Cari Hareketler / Ekstre genişletme (mevcut ekranın üzerine — yeni kaynak yok)

`/kartoteks/cari` (Kartoteks → Cari) üzerine:
- **Görünüm:** Özet (konu başlığı) ↔ **Detaylı** (fatura/irsaliye kalemleri satır içinde açılır).
- **Fiyat göster/gizle** toggle.
- **KDV dahil/hariç** toggle (fatura hareketinde `kdv_toplam` düşülerek; `cari_hareket` değişmez).
- Tarih aralığı + belge tipi filtreleri (mevcut) korundu; **PDF/Excel/CSV zaten var** (doğrulandı).

## 4) Versiyon takibi

- `CHANGELOG.md` (Keep a Changelog formatı) + `config.SURUM="1.23.0"` / `SURUM_TARIHI`.
- Her sayfanın **alt bilgisinde sürüm etiketi** (`v1.23.0 (2026-09-08)`).

## 5) Stok Hareketleri genişletme

- `/stok/hareketler`: her satırda **"Cari / Tedarikçi"** sütunu (belge üzerinden çözülür, K4).
- Yeni **`/stok/alis-gecmisi`** ekranı: stok alışlarında **hangi firmadan, kaç adet, ne fiyata**
  (KDV dahil/hariç kıyaslama toggle'ı); arama ürün/kod/barkod/firma/belge no üzerinden çalışır.

## 6) Stok kartında "son 3 alış / son 3 satış"

- Stok detayına iki kart eklendi: son 3 alış (tarih, tedarikçi, adet, birim maliyet) ve
  son 3 satış (tarih, müşteri, adet, birim fiyat) — yeni alış girerken fiyat kıyaslaması için.

## 7) Belgede görünen ürün adı override (`goruntu_adi`)

- `fatura_kalem.goruntu_adi` / `irsaliye_kalem.goruntu_adi` (nullable).
- Stoklu satırda "Görünen ad" alanı: **boşsa stok adı**, doldurulursa **yalnız o belgede** o ad
  gösterilir (detay + yazdır). Stok kartı/Kartoteks/Genel Muhasebe gerçek stok adını kullanır.

---

## Ek: yarış durumu düzeltmesi (onaylanan teknik not)

Canlı arama isteklerine **sıra numarası** eklendi: yalnız en son gönderilen isteğin yanıtı
uygulanır, eski yanıtlar yok sayılır (`form-satir.js`; `test_form_satir4.js` ile doğrulandı).

## Test sonuçları

| Test | Kapsam | Sonuç |
|---|---|---|
| `test_form_satir.js` | satır içi yazma + autocomplete + manuel fallback + toplamlar | 16/16 ✅ |
| `test_form_satir2.js` | Transfer manuel yasağı + K9 iskonto önceliği | 6/6 ✅ |
| `test_form_satir3.js` | UI'da kurulan satırların gerçek kaydı (uçtan uca) | ✅ |
| `test_form_satir4.js` | yarış durumu (eski yanıt yok sayılır) | 3/3 ✅ |
| `test_form_satir5.js` | birim + görünen ad override (uçtan uca) | 7/7 ✅ |
| `test_manuel_satir.py` | K33 manuel satır regresyonu | 28/28 ✅ |
| Canlı doğrulama | K14 alış, alış geçmişi (firma/KDV), son 3, cari ekstre filtreleri, Transfer formu | ✅ |

Son kontrol: DB bütünlüğü `ok`, mizan dengeli, test verisi temizlendi.

## Etkilenen dosyalar

- `db.py` — kalem tablolarına `birim` + `goruntu_adi` migrasyonu
- `stok.py` — `BIRIMLER`, `hareket_cari`, `hareket_kdv_orani`, `/stok/alis-gecmisi`,
  hareketlerde cari, stok detayı son 3 alış/satış
- `kartoteks.py` — cari ekstre filtreleri (özet/detay, fiyat, KDV) + stok ledger "kiminle"
- `fatura.py`, `irsaliye.py` — kalem birim/goruntu_adi oku-yaz; detay sorgularında `gorunen_ad`/`birim_goster`
- `static/js/form-satir.js` — birim seçimi, görünen ad alanı, yarış durumu koruması
- `templates/fatura/form.html`, `templates/irsaliye/form.html` — Birim sütunu
- `templates/{fatura,irsaliye}/{detay,yazdir}.html` — `gorunen_ad` + birim gösterimi
- `templates/kartoteks/cari.html` — yeni filtre çubuğu + detaylı görünüm
- `templates/stok/{hareketler,alis_gecmisi,detay}.html` — cari sütunu, alış geçmişi, son 3
- `templates/irsaliye/detay.html` — tip bilinçli "Faturasız" ipucu
- `templates/base.html`, `config.py`, `core.py`, `CHANGELOG.md` — sürüm takibi
