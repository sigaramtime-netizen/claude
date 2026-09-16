# D019 — DÖVİZLİ GÖSTERİM, EKSTRE RAPORLAMA & E-FATURA AKTARIM CİLASI (H1-H9 KESİN ÇÖZÜMÜ)

**Tarih:** 2026-09-16  
**Veren:** KÖPRÜ (Analist 05 Hata Raporu Doğrultusunda)  
**Öncelik:** Çok Yüksek / Mimari Düzeltme & Gösterim Katmanı  
**Versiyon Hedefi:** v1.49.0 → v1.50.0  

---

## 1. GEREKÇE & KÖK NEDEN ÖZETİ
Analist raporunda (05_HATA_RAPORU) çok net ortaya konduğu üzere:
> **Para birimi verisi veritabanında saklanıyor, ancak GÖSTERİM ve HESAPLAMA katmanı (şablonlar, `para` filtresi, bakiye toplamları) birimden habersiz.** `para` filtresi her sayıya körü körüne `₺` ekliyor; ekstre ve fatura detayında TRY ile USD'yi çevirmeden topluyor. Otomatik faturada `None` basılan yerler var ve ekstre yazdırma/CSV eksik.

Bu direktif, **H1'den H9'a kadar olan 9 hatayı** tek bir mimari pakette kökünden çözecektir.

---

## 2. DETAYLI GEREKSİNİMLER (H1 – H9 ÇÖZÜMLERİ)

### BÖLÜM 1: Gösterim Katmanı & Çift Dövizli Fatura/İrsaliye (H4, H5, H9)
1. **`para` Filtresi Para Birimi Desteği (`core.py`):**
   - `|para(birim)` parametresi alacak:
     - `TRY` → `100,00 ₺`
     - `USD` → `100,00 $` (veya `100,00 USD`)
     - `EUR` → `100,00 €`
     - `GBP` → `100,00 £`
   - Belge para birimi USD olan bir yerde asla `₺` basılmayacak!
2. **Fatura ve İrsaliyede Yan Yana Çift Kolon (H5):**
   - Belge para birimi `TRY` dışında ise (`USD/EUR/GBP`):
     - Kalem tablosunda: `[Birim Fiyat (Döviz)] | [Birim Fiyat (TL)]` ve `[Tutar (Döviz)] | [Tutar (TL)]` yan yana sütunlar olacak. (`TL = Döviz × Belge Kuru`).
     - Fatura/İrsaliye yazdırmada (`yazdir/belge.html`) da bu çift kolonlu düzen geçerli olacak.
   - `TRY` belgelerinde mevcut tek kolonlu sade yapı korunacak.
3. **Fatura Detayında "Kalan" Hesaplaması (H9):**
   - Belge USD ise ödemeler döviz bazında toplanacak (`kalan = genel_toplam - odenen_doviz`).
   - TRY ile ödeme yapıldıysa, ödeme tarihindeki kurla USD'ye çevrilip düşülecek.
   - Gösterim: *"Ödenen: 500,00 $ (≈ 24.225,00 ₺) · Kalan: 185,40 $ (≈ 8.982,63 ₺)"* formatında olacak.

### BÖLÜM 2: Cari Ekstre Bakiye & Döviz Toplamları Düzeltmesi (H7, H6)
1. **Ekstre Bakiye Hesabı (H7):**
   - Filtre "Tümü" iken farklı para birimlerindeki hareketler düz toplanmayacak! Her hareket kendi tarihindeki kurla TL karşılığına çevrilerek bakiye sütununa (`Bakiye TL`) yansıtılacak.
   - Döviz Alt Toplamları kartında: `USD: 822,48 USD ≈ 39.849,31 ₺ (Kur: 48,45)` şeklinde hem kendi birimi hem TL karşılığı doğru etiketle basılacak (USD'ye ₺ eklenmeyecek).
2. **Cari Ekstre Yazdırma & CSV Dışa Aktarma (H6):**
   - `/cari/<id>/ekstre/yazdir` rotası eklenecek (Wolvox temalı PDF/yazdırma).
   - `/cari/<id>/ekstre?fmt=csv` ile ekstre hareketleri CSV olarak indirilebilecek.
   - Ekstre sayfasına `🖨 Yazdır` ve `⬇ CSV İndir` butonları eklenecek.

### BÖLÜM 3: Otomatik e-Fatura / PDF Aktarım Cilası (H1, H2, H3)
1. **Cari Kod ve İl/İlçe Otomasyonu (H1):**
   - `efatura.py`: Yeni cari açarken `kod=None` yazılmayacak; `CARI-` önekli veya VKN'den türetilmiş tekil kod üretilecek.
   - `efatura_parser.py`: Adres metninden "İLÇE / İL" bilgisi ayrıştırılarak `cari_kart.il` ve `ilce` alanlarına yazılacak.
2. **"None" Metinlerinin Temizlenmesi (H2):**
   - Fatura kalemlerinde ve form doldururken hiçbir alanda ekrana `"NONE"` / `"None"` basılmayacak; `None` olan değerler `""` (boş string) olarak normalleştirilecek.
3. **Yazdırmada Fatura No ve Tedarikçi Belge No (H3):**
   - `yazdir/belge.html`: Başlıkta belirgin `FATURA NO: {{ fatura_no }}` basılacak.
   - Alış faturası ise hemen altında `Tedarikçi Belge No: {{ belge_no }}` basılacak.

### BÖLÜM 4: Onaylı Alış Faturasında İptal / Red Fişi (H8)
- Onaylı fatura direkt silinmez veya bozulmaz (muhasebe kuralı).
- Onaylı fatura detayına **"🔁 Red / İptal Fişi Oluştur"** butonu eklenecek (Admin/Muhasebe).
- Tıklandığında cari bakiye, stok ve yevmiye ters kayıtla sıfırlanacak, fatura durumu `Reddedildi` yapılacak ve audit log tutulacak.

---

## 3. KABUL KRİTERLERİ & TEST
- [ ] `test_d019_cift_doviz_gosterim.py` test dosyası yazılacak:
  - USD faturada `|para` filtresi `$` basıyor, `₺` basmıyor.
  - Fatura ve irsaliyede USD ve TL sütunları yan yana görünüyor.
  - Ekstrede döviz bakiye hesabı TL bazlı kur çevrimiyle doğru çalışıyor.
  - Cari ekstre `/yazdir` ve `?fmt=csv` 200 OK veriyor.
  - Otomatik faturada cari kod "None" değil, il/ilçe dolu.
  - Ekranda ve yazdır çıktısında hiçbir "None" metni yok.
  - Fatura yazdırmada `FATURA NO` ve `Tedarikçi Belge No` görünüyor.
  - Red fişi oluşturulunca stok ve cari hareketleri tersine dönüyor.
- [ ] Tam regresyon: 32 eski test + yeni test = **33 test dosyası 0 hata ile geçecek.**

---

## 4. İSTENEN TESLİM
- `kanitlar/v1.50.0/` altında tam regresyon çıktısı.
- Sansürlü teslim ZIP (`D019-v1.50.0.zip`) + MD5/SHA256 kanıtları.
