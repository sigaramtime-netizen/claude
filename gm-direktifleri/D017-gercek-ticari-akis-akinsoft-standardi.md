# D017 — GERÇEK TİCARİ AKIŞ & AKINSOFT STANDARDI (KÜSÜRAT 6 HANE, ÇİFT DÖVİZLİ FATURA, ALIŞ FATURA NO, CARİ EKSTRE LİNKLERİ, KALEM AÇIKLAMA, ÖDEMELER MENÜSÜ)

**Tarih:** 2026-09-15  
**Veren:** KÖPRÜ (Kullanıcı Talebi & Akınsoft 401 Video Analizi Doğrultusunda)  
**Öncelik:** Çok Yüksek / Ticari Kullanılabilirlik  
**Versiyon Hedefi:** v1.47.0 → v1.48.0  

---

## 1. GEREKÇE & HEDEF
Kullanıcının 2 haftadır yaşadığı fiili operasyonel tıkanıklıklar ve Akınsoft Wolvox ERP eğitim videoları analizi sonucunda, ticari hayatın gerektirdiği temel akışlar sisteme kazandırılacaktır:
1. `51,900103` gibi 6 basamaklı ithalat/elektronik küsüratlarının girilememesi (HTML `step="0.01"` kilidi).
2. Dövizli alış faturasında verinin USD olarak tutulamaması ve TL karşılıklarının aynı anda satır satır izlenememesi.
3. Alış faturasında tedarikçinin matbu/e-fatura numarasının (`HER2026000012603`) girileceği alanın olmaması.
4. Fatura kalemlerinde stok adının serbestçe düzenlenememesi (müşteriye özel fatura açıklaması yazılamaması).
5. Cari ekstredeki satırların ölü metin olması (belgeye tıklayıp detayına ve düzeltmeye gidilememesi).
6. Ana menüde tek tıkla erişilebilir Ödemeler & Tahsilatlar (Tediye / Makbuz) ekranının bulunmaması.

---

## 2. DETAYLI GEREKSİNİMLER

### MADDE 1: Küsürat & Ondalık Serbestliği (6 Hane Hassasiyet)
- Tüm formlarda (Stok Kartı, Alış/Satış Faturası, İrsaliye, Teklif, Sipariş):
  - Fiyat ve tutar inputlarındaki `step="0.01"` kısıtlamaları kaldırılacak, `step="any"` yapılacak.
  - Veritabanı ve Python matematik işlemlerinde (`ROUND(..., 6)` veya serbest float) virgülden sonra en az **6 hane** (`51.900103`) tam korunacak.

### MADDE 2: Çift Dövizli Fatura Grid'i (USD/EUR + TL Eşzamanlı Matrah)
- Fatura para birimi USD/EUR vb. seçildiğinde:
  - Fatura kalem satırlarında hem döviz değerleri:
    `[Döviz Birim Fiyat] | [Döviz İskonto] | [Döviz KDV Tutarı] | [Döviz Satır Tutarı]`
  - Hem de anlık kurla çarpılmış TL karşılıkları:
    `[TL Birim Fiyat] | [TL KDV] | [TL Tutar]` yan yana görüntülenecek ve hesaplanacak.
  - Fatura genel toplam kutusunda:
    - **Dövizli Toplam:** Ara Toplam (USD), KDV (USD), Genel Toplam (USD)
    - **Fatura Kuru:** `1 USD = 48.45 TL`
    - **TL Karşılığı:** Ara Toplam (TL), KDV (TL), Genel Toplam (TL) alt alta basılacak.

### MADDE 3: Alış Faturasında "Tedarikçi Fatura / Belge No"
- `fatura` tablosuna ve formlarına `belge_no` (Tedarikçi Fatura No / e-Fatura No) alanı eklenecek/etkinleştirilecek.
- Alış faturasında sistemin iç seri numarası (`AF-2026-001`) yanında tedarikçinin kestiği `HER2026000012603` gibi numaralar serbestçe girilebilecek, aranabilecek ve listelerde gösterilecek.

### MADDE 4: Kalemlerde Bağımsız 3'lü Yapı (Stok Kodu + Barkod + Serbest Açıklama)
- Fatura, irsaliye, teklif ve sipariş kalemlerinde:
  - **Stok Kodu** (kilitli/seçilen ürünün kodu)
  - **Barkod** (kilitli/seçilen ürünün barkodu)
  - **Ürün / Kalem Açıklaması:** Formda serbestçe değiştirilebilir `<input type="text">` olacak. Kullanıcı ürün adını faturada değiştirdiğinde (örn: *"TTEC NVR Kamera Montajı Dahil"* yazdığında), ana stok kartındaki orijinal isim bozulmayacak, yalnızca o faturadaki kalem açıklamasına kaydedilecek.
  - Ürün seçilmeden serbest manuel satır eklendiğinde de bu açıklama kaydedilecek.

### MADDE 5: Cari Ekstre & Stok Hareketlerinde Tıklanabilir Belge Linkleri
- **Cari Ekstre (`/cari/<id>/ekstre`):**
  - Ekstre tablosundaki her belge numarası (AF-xxx, SF-xxx, IRA-xxx, CEK-xxx, O-xxx, THS-xxx vb.) **mavi tıklanabilir link** olacak.
  - Tıklandığında doğrudan o belgenin detayına (`/fatura/<id>`, `/irsaliye/<id>`, `/cari/<id>/makbuz/<no>` vb.) gidecek; oradan inceleme ve düzenleme yapılabilecek.
- **Stok Hareketleri Listesi:**
  - Stok adına veya koduna tıklandığında doğrudan Stok Kartı detayına (`/stok/<id>`) gidecek.

### MADDE 6: Üst Menüye "Ödemeler & Tahsilatlar (Tediye / Makbuz)" Butonu
- Üst ana menüye veya Finans Yönetimi menüsünün en başına göz önünde tek tıkla erişilebilir **"💰 Ödeme & Tahsilat (Kasa/Banka/Tediye)"** menüsü eklenecek.
- Bu ekrandan cari seçilerek Nakit / Banka Havale / Kredi Kartı / Çek-Senet parçalı tahsilat veya ödeme anında girilebilecek.

---

## 3. KABUL KRİTERLERİ & TEST
- [ ] Stok kartı ve fatura formlarında `51.900103` gibi 6 basamaklı fiyatlar sıfır hata ile kaydediliyor.
- [ ] Alış faturasında girilen tedarikçi fatura no listelerde ve detayda görünüyor.
- [ ] Dövizli faturada döviz birim fiyat, döviz toplam ve TL karşılıkları eksiksiz hesaplanıyor.
- [ ] Kalem tablosunda stok kodu, barkod ve serbest kalem açıklaması bağımsız çalışıyor.
- [ ] Cari ekstredeki evrak numaralarına tıklanınca ilgili belge açılıyor.
- [ ] Üst menüde Ödeme & Tahsilat bağlantısı faal.
- [ ] Tam regresyon (30 test dosyası + yeni testler) 0 hata ile geçiyor.
- [ ] K1 şirket izolasyonu ve FK bütünlüğü korunuyor.

---

## 4. İSTENEN KANITLAR & TESLİM
- `test_d017_akinsoft_ticari_akis.py` test suite.
- Tam regresyon çıktısı (tüm testler yeşil).
- Sansürlü teslim ZIP (`D017-v1.48.0.zip`) + MD5/SHA256 kanıtları.
