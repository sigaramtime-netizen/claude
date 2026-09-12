# Faz 2 — Satış Döngüsü: Teklif Modülü (Özet & Onay)

> Proje komutundaki "her fazın sonunda veri modeli özeti + ekran listesi + örnek test
> senaryosu üret ve onay iste" kuralı gereği hazırlanmıştır. Faz 2'nin 1. modülü.
> Belge zinciri: **Teklif → Sipariş → İrsaliye → Fatura** (bu, zincirin ilk halkası).

Ayrıca bu turda firma unvanı **"Brn Teknoloji"** olarak güncellendi (seed + şablonlar +
rapor başlıkları + logo "B" + e-posta adresleri).

---

## 1) Bu fazda ne yapıldı?

- **Teklif modülü** uçtan uca çalışır şekilde teslim edildi (LIVE PREVIEW: `admin / 1234`).
- Müşteri fiyat teklifi hazırlama (çok satırlı kalem girişi), durum akışı, geçerlilik
  tarihi + otomatik hatırlatma/süre dolumu, yazdırılabilir PDF teklif görünümü.
- Belge zincirinin ilk halkası: onaylanan teklif, Sipariş modülünde (bir sonraki adım)
  tek tıkla siparişe dönüştürülecek — kalem yapısı buna hazır.

## 2) Veri Modeli (yeni tablolar)

| Tablo | Amaç | Kritik Alanlar |
|---|---|---|
| `teklif` | Teklif başlığı | teklif_no, cari_id, **sube_id** (K1), tarih, gecerlilik_tarihi, durum, para_birimi, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama |
| `teklif_kalem` | Teklif satırları | teklif_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar |

**İş mantığı:**

- Durumlar: `Taslak → Gönderildi → Onaylandı / Reddedildi / Süresi Doldu`.
- `tutar` = satır neti (miktar × birim_fiyat × (1 − iskonto/100)); KDV satırın kdv_orani
  ile hesaplanır. ara_toplam = Σ net; kdv_toplam = Σ (net × kdv/100); genel = ara + kdv.
- **Otomatik hatırlatma:** dashboard ziyaretinde — geçerliliği dolan "Gönderildi/Taslak"
  teklif → "Süresi Doldu" + uyarı bildirimi; geçerliliğine ≤3 gün kalan "Gönderildi"
  teklif → "yaklaşıyor" bildirimi (tekrarsız).
- Kalem girişinde varsayılanlar: birim fiyat = stok satış fiyatı, KDV = stok KDV,
  iskonto = cari iskonto oranı (yeni satır eklerken otomatik dolar, elle düzeltilebilir).

## 3) API Uçları (route listesi)

| Metod | Yol | Yetki* | İşlev |
|---|---|---|---|
| GET | `/teklif` | giriş | Teklif listesi (durum sekmeleri + arama) |
| GET/POST | `/teklif/yeni` | A·M·S | Yeni teklif (satır ekle/kaydet) |
| GET | `/teklif/{id}` | giriş | Detay: kalemler, toplamlar, durum işlemleri, audit |
| GET/POST | `/teklif/{id}/duzenle` | A·M·S | Düzenleme |
| POST | `/teklif/{id}/durum` | A·M·S | Durum geçişi (Gönder/Onayla/Reddet) |
| GET | `/teklif/{id}/yazdir` | giriş | Yazdırılabilir teklif (PDF'e kaydedilebilir) |

\* A=Admin, M=Muhasebe, S=Satış. Okuma tüm rollerde; yazma A/M/S.

## 4) Ekran Listesi

1. **Teklifler** — durum sekmeleri (sayılı), arama, genel toplam ve durum rozetleri.
2. **Yeni/Düzenle Teklif** — cari + tarih + geçerlilik + çok satırlı kalem tablosu
   ("Satır Ekle" sunucu taraflı), canlı toplam özeti, satır silme.
3. **Teklif Detayı** — kalemler, toplamlar, durum işlemleri (Gönder → Onayla/Reddet),
   "Sipariş'e dönüştür" notu, audit geçmişi.
4. **Yazdır/PDF** — antetli teklif görünümü ("FİYAT TEKLİFİ", Brn Teknoloji).
5. **Dashboard** — "Bekleyen Teklifler" KPI + geçerlilik bildirimleri.

## 5) Örnek Test Senaryosu

1. `admin / 1234` → Satış Döngüsü → Teklif: 3 örnek teklif listelenir.
2. **Yeni teklif:** cari "Batman Çarşı Elektronik", geçerlilik +14 gün → ürün seç
   "MARKA-B 43\" TV" → Satır Ekle → miktar 2 → ikinci satır "MARKA-A 9kg" miktar 1,
   iskonto 5 → Kaydet. Doğrulama: TV satırı 35.998 ₺, MARKA-A satırı 17.574,05 ₺,
   KDV 10.714,41 ₺, genel toplam 64.286,46 ₺ (hesap doğrulandı).
3. **Durum:** Taslak → "Gönder" → "Onayla". Liste sekmesinde sayılar güncellenir.
4. **Düzenle:** miktarı değiştir → toplamlar yeniden hesaplanır.
5. **Yazdır:** "Yazdır / PDF" → antetli teklif açılır, yazdırılabilir.
6. **Geçerlilik otomasyonu:** geçerliliği dün olan bir "Gönderildi" teklifi dashboard
   ziyaretinde "Süresi Doldu"ya çevrilir + uyarı bildirimi; geçerliliğine 2 gün kalan
   teklif için "yaklaşıyor" bildirimi üretilir (test edildi).
7. **Yetki:** `satis` teklif yazabilir (200); `depo` görür ama yazamaz (403); anonim → giriş.

## 6) Sonraki Adım (onay bekleniyor)

Faz 2'nin 2. adımı: **Sipariş** (müşteri siparişi + satın alma siparişi, onay akışı,
stok rezervasyonu, **onaylanan tekliften tek tıkla sipariş oluşturma**). Onay verirseniz
Sipariş modülüyle devam ederim.
