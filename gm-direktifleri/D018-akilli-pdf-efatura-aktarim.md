# D018 — AKILLI PDF / E-FATURA OKUYUCU & OTOMATİK CARİ, STOK VE FATURA ENTEGRASYONU

**Tarih:** 2026-09-15  
**Veren:** KÖPRÜ (Kullanıcı Talebi & e-Fatura Örneği Doğrultusunda)  
**Öncelik:** Çok Yüksek / Otomasyon  
**Versiyon Hedefi:** v1.48.0 → v1.49.0  

---

## 1. GEREKÇE & HEDEF
Kullanıcının sisteme manuel fatura, cari ve stok girmesini sıfıra indirmek; tedarikçilerden gelen resmi e-Fatura / PDF belgelerini sisteme yüklediği anda:
1. Cariyi otomatik algılayıp açmak veya eşleştirmek.
2. Faturadaki tüm stokları otomatik algılayıp sisteme stok kartı olarak açmak veya eşleştirmek.
3. Faturanın başlığını (Tedarikçi Fatura No, Tarih, Vade, Para Birimi, Döviz Kuru) ve tüm kalemlerini küsüratlarıyla (`51.900103 USD`) faturaya otomatik doldurmak.

---

## 2. DETAYLI GEREKSİNİMLER

### BÖLÜM A — Backend: Akıllı PDF / e-Fatura Ayrıştırıcı (Parser Engine)
- `core/efatura_parser.py` (veya `kod/efatura_parser.py`):
  - Standart GİB e-Fatura ve PDF metinlerini ayrıştıracak regex/string mantığı:
    - **Cari Bilgileri:** Satıcı Ünvanı, VKN/TCKN, Vergi Dairesi, Adres, Telefon, E-Posta, IBAN.
    - **Fatura Başlığı:** Fatura No (`HER2026000012603`), Tarih (`03-09-2026`), Para Birimi (`USD`), Kur (`48.4500`), Vade (`30 Gün`).
    - **Kalem Tablosu:** Sıra No, Ürün Adı / Açıklama, Miktar, Birim, Birim Fiyat (6 hane küsürat), KDV Oranı, Satır Tutarı.
    - **Toplamlar:** Mal Hizmet Tutarı, KDV Tutarı, Genel Toplam (Döviz ve TL karşılıkları).
  - Güvenli dosya yükleme (`.pdf` ve `.xml` kabul edilir, max 5MB).

### BÖLÜM B — Rotalar & API
1. **`POST /api/fatura/pdf-cozumle`:**
   - PDF dosyasını alır, çözümler ve JSON olarak cari, fatura başlık ve kalem verilerini döner.
2. **`POST /api/fatura/hizli-aktar`:**
   - Çözümlenen veriyi alır:
     - Cari yoksa VKN ile `cari` tablosuna otomatik yeni tedarikçi kartı açar (varsa mevcut `cari_id`'yi alır).
     - Stoklar yoksa ürün adından temiz stok kodu üreterek `stok` tablosuna otomatik stok kartı açar (Alış fiyatı dövizli ve 6 haneli yazılır).
     - Fatura formuna verileri doldurur veya doğrudan taslak alış faturası oluşturup detay ekranına yönlendirir.

### BÖLÜM C — Arayüz (UI) Entegrasyonu
- **Fatura Formu (`/fatura/yeni?tip=Alis`):**
  - Üst kısma belirgin **"📥 e-Fatura / PDF Yükle (Otomatik Doldur)"** butonu.
  - Dosya seçildiği anda arka planda çözümlenir, cari otomatik seçilir, döviz/kur otomatik ayarlanır, tüm kalemler satır satır grid'e basılır!
- **Cari Listesi (`/cari/liste`):**
  - "Yeni Cari" yanına **"📥 Faturadan Cari Ekle"** butonu (faturadaki satıcıyı tek tıkla cariye kaydeder).
- **Stok Listesi (`/stok/liste`):**
  - "Yeni Stok" yanına **"📥 Faturadan Stokları İçe Aktar"** butonu (faturadaki ürünleri tek tıkla stok listesine döker).

---

## 3. KABUL KRİTERLERİ & TEST
- [ ] Gönderilen `herzEFATURA.pdf` dosyası yüklendiğinde `HERZ ELEKTRONİK SAN. TİC. LTD. ŞTİ.` (VKN: `8600135998`) cari olarak eksiksiz tanınıyor.
- [ ] 5 adet stok kalemi (`TTEC NVR`, `TTEC IPBP`, `CAT6 BOX CABLE` vb.) isimleri, miktarları ve küsüratlı döviz fiyatlarıyla (`51.900103`) doğru ayrıştırılıyor.
- [ ] Fatura başlığındaki `HER2026000012603` belge numarası ve `48.45` kuru faturaya tam oturuyor.
- [ ] `test_d018_efatura_otomasyon.py` test suite'i yazılıyor ve 0 hata ile geçiyor.
- [ ] Tam regresyon (31 test dosyası + yeni test) 0 hata ile yeşil kalıyor.

---

## 4. İSTENEN KANITLAR & TESLİM
- `kod/efatura_parser.py` ve ilgili rotalar.
- `test_d018_efatura_otomasyon.py` test çıktısı.
- Tam regresyon çıktısı (32 dosya, 0 başarısız).
- Sansürlü teslim ZIP (`D018-v1.49.0.zip`) + MD5/SHA256 kanıtları.
