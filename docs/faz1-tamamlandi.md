# Faz 1 — ÇEKİRDEK: TAMAMLANDI ✅

> Proje komutundaki uygulama planının **Faz 1'i (Çekirdek)** eksiksiz tamamlandı.
> Bu dosya, Faz 2'ye geçiş için Faz 1'in tamamlanma özetidir.

---

## Teslim edilen modüller

| # | Modül | İçerik | Durum |
|---|---|---|---|
| 1 | **Cari** | Kart, ekstre, yaşlandırma (30/60/90), kredi limiti, gruplar, notlar, audit | ✅ |
| 2 | **Stok** | Ürün kartı, seri/lot, kritik stok + uyarı, hareket, sayım, varyant (barkodlu) | ✅ |
| 3 | **Stok2** | Çoklu depo, transfer, min/max, tedarikçi eşleştirme, toplu fiyat/iskonto | ✅ |
| 4 | **Kasa** | Çoklu kasa, giriş/çıkış, fiş, günlük rapor, **cari bağlantısı** | ✅ |
| 5 | **Banka** | Hesaplar, havale/EFT, ekstre, CSV içe aktarma, **cari bağlantısı** | ✅ |
| 6 | **Depo/Şube** | Şube tanımı, depo/kullanıcı-şube bağlama, şube bazlı görünürlük + rapor | ✅ |

**Ayrıca kurulan çekirdek altyapı:** kendi WSGI sunucusu, oturum + rol denetimi
(Admin/Muhasebe/Satis/Servis/Depo), audit log, bildirim sistemi, responsive koyu tema,
Türkçe arayüz, SQLite + migrasyon, seed (örnek) veriler.

## Entegrasyon kuralları (komut Bölüm 2'ye uyum)

> Tüm kurallar artık **`docs/mimari-kurallar.md`** dosyasında toplu ve bağlayıcıdır
> (K1–K7). Özellikle **K1 — Şube (`sube_id`) ön-hazırlık kuralı**: `kasa` ve `banka_hesap`
> tablolarına nullable `sube_id` Faz 1 sonunda eklendi; Faz 2+ belge tabloları
> (`teklif`, `siparis`, `irsaliye`, `fatura`, `cek_senet`, …) baştan `sube_id` ile açılacak.
> Böylece Faz 6'da şema migrasyonu + veri backfill'i gerekmeyecek.

1. **`ilgili_modul` / `ilgili_kayit_id`** deseni cari_hareket, stok_hareket, kasa_hareket ve
   banka_hareket'te tutarlı — Faz 2'de Fatura/İrsaliye/Sipariş bu referanslarla otomatik hareket üretecek.
2. **Kartoteks hazırlığı:** tüm stok hareketleri tek `stok_hareket` tablosunda; Excel/CSV dışa
   aktarma + PDF rapor hazır.
3. **Çifte veri girişi yok:** Kasa/Banka hareketinde cari seçilince `cari_hareket` otomatik oluşur.
4. **Fiyat kuralı rezervi:** cari/stok/tarih bazlı fiyat kuralları için alan adları çakışmaz;
   ayrı `fiyat_kural` tablosu Faz 2'de açılacak.
5. **Barkod:** `barkod_bul()` yardımcısı Faz 2'de Fatura/İrsaliye satır girişinde kullanılacak.
6. **Muhasebe konvansiyonu:** `bakiye = Σborç − Σalacak` (evrensel çift taraflı); müşteri pozitif,
   tedarikçi negatif bakiye — Genel Muhasebe (Faz 5) bu konvansiyonla otomatik yevmiye üretecek.

## Rota özeti

Toplam **50 kayıtlı rota**: Cari 9, Stok/Stok2 17, Kasa 5, Banka 5, Şube 5, genel 9.

## Test edilen kritik senaryolar

- Cari: yaşlandırma FIFO, kredi limiti uyarısı, tahsilat/borç yönü, tedarikçi negatif bakiye.
- Stok: seri no giriş/çıkış yaşam döngüsü, sayım farkı → hareket, transfer çift yönlü, kritik stok bildirimi.
- Kasa/Banka: cari bağlantılı tahsilat/ödeme, kasa↔banka transfer (karşı taraf otomatik,
  yetersiz bakiyede tam red), CSV içe aktarma.
- Şube: şube bazlı stok görünürlüğü, kullanıcı–şube ataması, yetki (Admin-only yönetim).
- Yetki matrisi tüm modüllerde test edildi (okuma tüm roller / yazma role özel).

## Sonraki adım

**Faz 2 — Satış Döngüsü:** Teklif → Sipariş → İrsaliye → Fatura → Çek/Senet → Döviz Takip.
Bu fazda "Teklif → Sipariş → İrsaliye → Fatura" belge zinciri, otomatik stok düşümü,
cari hareket üretimi ve e-Fatura (Faz 4) entegrasyon noktaları kurulacak.
