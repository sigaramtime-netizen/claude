# Manuel (Serbest Metin) Satır Ekleme — Uygulama Özeti

> Tarih: 2026-09-08 · Kapsam: İrsaliye + Fatura · Durum: **Tamamlandı, uçtan uca test edildi**
> Bu özet, Faz 6.1 (Sistem Yönetimi) onayı ve `yedek_al.py` düzeltmesinden **bağımsız** ayrı bir istektir.
>
> **GÜNCELLEME (2026-09-08):** Formlardaki satır girişi, bu dokümanın yazıldığı "manuel çubuğu"
> düzeninden **satır içi yazma + canlı arama** akışına (K34) geçirildi. Aşağıdaki **davranış ve
> yevmiye kuralları (K33) değişmedi**; yalnız *kullanıcının manuel satırı nasıl girdiği* değişti:
> artık ayrı çubuk yok, ürün hücresine yazıp stokla eşleşmeyen metin otomatik manuel olur.
> Güncel akış için bkz. `docs/satir-ekleme-akisi-ozet.md`.

---

## 1. Ne istendi?

Fatura ve irsaliyeye, stoğa bağlı olmayan **serbest metin** satır ekleyebilme:
açıklaması, miktarı, fiyatı, KDV'si ve iskontosu tamamen elle girilen; stoğa dokunmayan satırlar.

## 2. Veri modeli değişikliği

| Tablo | Değişiklik |
|---|---|
| `fatura_kalem.stok_id` | `NOT NULL` → **nullable** (`NULL` = manuel satır) |
| `irsaliye_kalem.stok_id` | `NOT NULL` → **nullable** (`NULL` = manuel satır) |
| `…_kalem.aciklama` | Manuel satırın serbest metni bu alanda saklanır (stoklu satırda `NULL`) |

SQLite'ta mevcut kolonda `NOT NULL` kaldırılamadığı için, `cek_senet` deseniyle **veri
korunarak tablo yeniden kurma** migrasyonu kullanıldı. Mevcut satırlar (5 fatura + 4 irsaliye
kalemi) kayıpsız taşındı — `PRAGMA table_info` ile `stok_id notnull=0` doğrulandı.

**Stoklu satırların davranışı aynen korundu:** barkod, K9 iskonto önceliği, stok düşümü, K11
teslim kontrolü — hepsi yalnız `stok_id` dolu satırlarda çalışır.

## 3. Davranış kuralları

| Kural | Uygulama |
|---|---|
| Stoğa dokunmaz | `stok_hareket` üretilmez, `stok_seviye`/`rezerve` değişmez; irsaliye depo bazlı düşüm yalnız `stok_id` dolu satırda |
| Toplama dahil | Ara toplam / iskonto / KDV / genel toplam içinde hesaplanır |
| K9 geçerli DEĞİL | İskonto kullanıcının girdiği değerdir; stok/cari iskonto oranı manuel satıra **otomatik uygulanmaz** |
| Transfer'de yasak | Transfer irsaliyesinde manuel satır eklenemez (formda çubuk gizli + sunucu tarafı red) |
| Fatura yevmiyesi | Tek fiş korunur; hesap eşlemesi: **Satış → 600** (manuel dahil) · **Alış → stoklu 153 / manuel 770** (kullanıcı seçimi: seçenek a) |
| KDV | Satış 391 (hesaplanan), Alış 191 (indirilecek) — değişmedi |
| Karşı cari | Satış 120 borç / Alış 320 alacak — değişmedi |
| İrsaliye → Fatura | Manuel satır, irsaliyeden fatura üretiminde de taşınır (LEFT JOIN + `manuel` rozeti) |
| Sipariş → İrsaliye | Manuel satır sipariş teslim kontrolüne ve `teslim_edilen` güncellemesine girmez |

## 4. Uçtan uca test sonuçları — **28/28 ✅** (+ 6 ek kontrol)

`test_manuel_satir.py` (workspace'te) — sunucu 8080'de çalışırken tekrarlanabilir.

**TEST A — Satış faturası (stok + manuel):** toplamlar 1200/240/1440 ✓ · 600 tek satır alacak
1200 ✓ · 120 borç 1440 / 391 alacak 240 ✓ · fiş dengeli ✓ · iptal sonrası yevmiye+cari temiz ✓

**TEST B — Alış faturası (stok + manuel):** 153=500 (stoklu) ✓ · **770=100 (manuel)** ✓ ·
191=120 ✓ · fiş dengeli 720/720 ✓

**TEST C — İrsaliye (stok + manuel):** stok_hareket yalnız stoklu satırda (1 kayıt, −2) ✓ ·
stok_seviye yalnız stoklu miktar kadar düştü ✓ · iptal seviyeyi geri aldı ✓

**TEST D — İrsaliye → Fatura:** manuel ad + rozet formda göründü ✓ · fatura kalemine taşındı ✓ ·
iptal stoğu geri aldı ✓

**Ek kontroller:** Transfer formunda manuel çubuğu gizli ✓ · Transfer+manuel kayıt reddedildi ✓ ·
K9 iskontosu manuel satıra uygulanmadı (cari/stok %5 iken manuel iskonto 0) ✓ · regresyon 7
ana sayfa 200 ✓ · mizan dengeli (833.375,26 ₺) ✓ · yetim kayıt yok ✓

## 5. Bilinen sınırlama (not)

Manuel satırlar stok hareketi üretmediği için **Kartoteks** (stok hareket listesi) ekranında
görünmez. Bu, tasarımın doğal sonucudur; manuel satırlar yalnız belge (irsaliye/fatura) ve
muhasebe fişinde izlenir.

## 6. Bu istek sırasında tespit edilip düzeltilen bağımsız hata

- **`fatura.doviz_kur NOT NULL` hatası:** TRY para biriminde fatura/irsaliye kaydederken
  `doviz_kur=None` yazılıyordu → `500 Internal Server Error`. TRY için kur artık `1.0` yazılıyor
  (fatura formu kayıt akışı düzeltildi). Bu hata, manuel satır testini de kilitlemişti.

## 7. Etkilenen dosyalar

- `db.py` — kalem tablolarında `stok_id` nullable + veri korumalı migrasyon
- `fatura.py`, `irsaliye.py` — `_satirlar_from_form`, `_satir_gorunum`, `_…_detay`, `ekle_manuel`
  action, `gecerli` filtresi, kalem INSERT (`aciklama`)
- `irsaliye.py` — `_stok_kontrol_ve_uygula` + `_siparis_teslim_kontrol` manuel satırları atlar;
  Transfer'de manuel yasak
- `muhasebe.py` — `_fatura_satirlar`: Alış matrahı stoklu→153 / manuel→770 olarak bölünür
- `templates/fatura/form.html`, `templates/irsaliye/form.html` — manuel satır çubuğu + rozet +
  `k_manuel_ad` gizli alanı; detay/yazdır şablonlarında "manuel" rozeti, stok kodu gösterilmez
- `test_manuel_satir.py` — tekrarlanabilir uçtan uca test betiği (yeni)
