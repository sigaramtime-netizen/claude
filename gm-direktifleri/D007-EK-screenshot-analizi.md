# D007 EK — Screenshot Analizi (2026-09-12 14:20)

**Amaç:** Kralın yolladığı 4 ekranın D007 maddeleriyle birebir eşleşmesini teyit, eksik detayları kapat.

**Dosyalar:** `irsaliyeler.png`, `cari kartoteks.png`, `Satış irsaliye fatura.png` (Wolvox Yurt İçi Satış Faturası), `stok tanımlaro.png` (Wolvox Stok Tanımları)

---

## 1) irsaliyeler.png — İrsaliye Listesi

**Görülen:**
- Üst filtre: `Tümü / Taslak(1) / Onaylandı(5) / İptal(0) / Faturalanmamış(3)` + `Satış / Alış / Transfer` sekmeler
- Ara input: `İrsaliye no, cari unvan/kod ara…` + Filtrele/Temizle
- Tablo kolonlar: `No | Tip | Cari | Tarih | Kalem | Genel Toplam | Durum | Fatura | [Aç][Yazdır]`
- Satırlar (ör):
  - `BELGE-001 Alış MÜŞTERİ-B 500,00 ₺ Onaylandı → Faturala`
  - `BELGE-003 Satış MÜŞTERİ-A 1.000,00 ₺ Onaylandı → Faturala`
  - `BELGE-002 Alış MÜŞTERİ-A 500,00 Taslak`
- Altta 7 satır, hepsi Onaylandı/Taslak, hepsinde Yazdır var, **Sil yok** (madde 9 doğrulandı).
- Para birimi kolon yok — hep TL (madde 5: döviz eksik doğrulandı).

**D007 eşleşme:**
- ✅ **Madde 5** (döviz): `Genel Toplam` yanında `Para Birimi` rozeti ekle + USD/EUR seçince `≈ TL` çeviri.
- ✅ **Madde 9** (Sil): Liste değil, **detay içinde** Sil — bu listede Sil olmaması doğru (istenen: detayda Sil).
- ✅ **Madde 10** (uzun liste): Cari filtre input'u düz `<input>` — typeahead değil, ama bu liste filtresi için kabul edilebilir. Asıl hedef formlardaki cari/stok seçimi.

**Not:** MÜŞTERİ-A cariye hem Alış (`BELGE-002 Taslak`) hem Satış (`BELGE-003 Onaylandı`) var — tam da madde 8'in repro verisi.

---

## 2) cari kartoteks.png — Cari Kartoteks (MÜŞTERİ-A)

**Görülen:**
- Üst: `Cari Seç` → `<select>` dropdown `CAR-1001 MÜŞTERİ-A` (uzun liste, manuel arama yok — **madde 7/10 kanıtı**)
- Yanında: `Ara (kod/unvan)…` + Listele (ayrı input, ama select'i filtrelemiyor)
- Kart: `CAR-1001 MÜŞTERİ-A` + 3 KPI (Toplam Borç/Alacak/Net Bakiye) — Net Bakiye **1.000,00 ₺ kırmızı**
- Hareket Dökümü: **Sadece 1 satır** `2026-09-12 Satış İrsaliyesi BELGE-003 ürün satış 1.000,00 ₺` + `Toplam(filtered) 1.000`
- **Beklenen:** 2 satır olmalı (BELGE-003 Satış 1.000 Borç + BELGE-002 Alış 500 Alacak) → Net **500 ₺** olmalı. Şu an Alış kaybolmuş.
- Tablo kolonlar: `Tarih | Belge Tipi | Belge No | Açıklama | Kaynak | Vade | Borç | Alacak | Bakiye` — doğru.
- Görünüm/ Fiyat/ KDV toggle'ları var (Özet/Detay, Göster/Gizle, Dahil/Hariç) — mevcut.

**D007 eşleşme:**
- ✅ **Madde 7 & 10**: Üstteki `<select>` → **typeahead**'e dönülecek (GET /api/ara?tip=cari). Bu ekranın en kritik UX düzeltmesi.
- ✅ **Madde 8 (BUG)**: **Kesin repro** — irsaliyeler.png'deki `BELGE-002 (MÜŞTERİ-A, Alış, Taslak)` kartotekste yok, çünkü **Taslak irsaliye henüz cari_hareket yazmıyor** (F1 kuralı: sadece Onaylandı yazar). Ancak `BELGE-002 Taslak` olduğu için görünmemesi **normal**. Fakat kullanıcı diyor ki biri Alış biri Satış ekledi, ekstrede sadece Satış görünüyor. İkinci ekranın altındaki `BELGE-003 Onaylandı 1.000` + `BELGE-002 Taslak` → Taslak olduğu için cari_hareket yok, ekstrede görünmez — kullanıcı Taslak'ı Onaylayınca görünmesi gerek. **Gerçek bug:** Eğer `BELGE-002` Onaylandı olsaydı bile görünmüyor mu? Testte MÜŞTERİ-A için 1 Alış+1 Satış **her ikisi de Onaylandı** yapılmalı ve 2 satır kontrol edilecek. `kartoteks.py _cari_rows` sorgusunda `belge_tipi` filtresi veya `ilgi_modul` lower-case bug'ı olabilir. D007 madde 8'de bu net test edilecek.
- Ayrıca `irsaliyeler.png`de `BELGE-002 Taslak` → Onaylayınca kartotekste çıkmalı. Kullanıcı Taslak'ı gözden kaçırmış olabilir — GM olarak Onaylı haliyle test ettireceğiz.

**Aksiyon (D007 madde 8):**
```sql
SELECT belge_tipi, belge_no, borc, alacak FROM cari_hareket WHERE cari_id= (SELECT id FROM cari_kart WHERE kod='CAR-1001') ORDER BY tarih;
-- Beklenen 2 satır: (Satış İrsaliyesi, BELGE-003, 4200, 0) ve (Alış İrsaliyesi, BELGE-002, 0, 3500) — Onaylandı sonrası
```
- Template'te `{% for h in rows %}` filtresi `if h.belge_tipi == 'Satış ...'` gibi bir koşul varsa kaldır.

---

## 3) Satış irsaliye fatura.png — Wolvox Yurt İçi Satış Faturası (REFERANS)

**Görülen (Wolvox):**
- Üst form: `Cari Kodu/Unvan, Fatura Seri/No, KDV Oranı, Fiyat Tipi, Vade Durumu, Evrak No Girişi` + `Cari/Stok Hareket Ayrıntısı, Fatura Bekli, Fatura İptal` checkbox'lar
- Orta **Hareketler** grid: Kolonlar `Stok Kodu, Stok Adı, Miktar, Birimi, Temel Mik, Fiyat, Birim2 Fiyat, KDV Durumu, KDV HrcFiyat, İnd.Fiyat, Ara Tutar, İnd.Ara Toplam, Hesap, Simge/Ara Kuru, Satış Kuru, Fiyatı, Birim2 Fiyat, KDV Hrc...`
- Satır örnek: `STO0015 ADA GH6 1,000 ADET 1,000 ADET 82.000 82.000 Dahil ... 82.000 ... 5,000 5,500 ...`
- Altta **Genel Toplamlar**: `Toplam 120.000,00 TL, Isk.Toplam 0,00, Ara Toplam 120.000,00` + sağda `Genel Toplam 120.000,00 TL` ve **yanında Döviz karşılığı `2.000,00 $`** kutusu + `Döviz Toplam, KDV Detayları, İskontolar ...`

**Ne isteniyor (madde 5):**
> "irsaliyede alış ve satışında sadece tl işlemler var diğer döviz işlemlerini de ekle usd euro gibi, fiyat usd de ekle o fişin içeriğinde usd ve tl aynı anda olsun irsaliye fatura teklifi istersem usd olarak kaydolsun istersem tl olarak kaydolsun akınsoftun sisteminden örnek alabilirsin."

**Çıkarım:**
- Wolvox gibi **belge bazında Para Birimi seç + Kur** + **satır bazında Birim Fiyat (orijinal para biriminde)** + **alt toplamda çift para gösterimi**.
- Bizde `fatura` zaten döviz var (4 para birimi), `irsaliye` eksik — D007 madde 5 sadece irsaliyeyi kapatıyor. Ancak ekran şunu da gösteriyor: **satır bazında KDV durumu (Dahil/Hariç) ayrı kolonda** — bu da madde 1'in Wolvox referansı.

**D007 eşleşme:**
- ✅ **Madde 1**: KDV Durumu `Dahil/Hariç` — Wolvox'te `Kdv Durumu` kolonu var. Bizde başlık bazında select olacak (satır bazında değil, başlık bazında — daha basit ve F2 ile uyumlu). Wolvox satır bazında tutuyor ama bizde başlık yeter (akınsoft da başlık bazında).
- ✅ **Madde 5**: **Belge Para Birimi + Kur** (fatura/teklif/sipariş zaten var, irsaliye eklenecek) + **Detay/Yazdır'da çift gösterim** `120 USD (≈ 3.600 ₺)` + **Yazdır şablonunda** `yazdir/belge.html` çift kutucuk.

**Ek not (Wolvox'tan alınmayacak):** Wolvox'un 15+ kolonu kopyalanmayacak — WOLVOX taklidi uyarısı korunacak. Biz **sade**: `Miktar | Birim Fiyat (orijinal) | KDV % | Tutar (orijinal) | Tutar (TL)` yeter.

---

## 4) stok tanımlaro.png — Wolvox Stok Tanımları (REFERANS)

**Görülen:**
- Tabs: `Genel Bilgiler | Birim/Barkod | Fiyatlar | İstatistikler | Özel Ayarlar 1 | Özel Ayarlar 2 | Özel Tanımlar | Alternatifler ...`
- Alanlar:
  - `Bilg.Kodu 3247, Stok Adı ARMUT, Stok Kodu STO2682, Barkod Tipi UPC, Barkodu 869...,`
  - `Grubu ▼, Ara Grubu ▼, Alt Grubu ▼, Açıklama`
  - `Özel Kodu 1, Özel Kodu 2, Özel Kodu 3`
  - `Vergi Oranları: KDV Alış % 0, ÖTV %, KDV Satış Prk.% 18, ÖİV %, KDV Satış Tpt.% 18, 85 Nolu KDV Kanununa Tabi`
  - `Tevkifat Oranı 0 / 0, İstisna Kodu [🔍]`
  - `Vade Günü, Döviz Hesabı Kullan $ ▼, Bonus Oranı, Bonus Birim Fiyatı, Pazarlamacı Prim Oranı`
  - Sağ panel: `Ana Stok, Asorti sistemi kullan, Markası [🔍][+], Modeli, Renk, Beden, Ana Stok Kodu`
  - Altta: `Önceki | Sonraki | Ekle | Sil | Düzenle | Kaydet | Vazgeç | Yenile`

**Ne isteniyor (madde 2+3):**
> Madde 2: "marka model yazan yere ekleme yapamıyorum"
> Madde 3: "tevkifat oranı , istisna kodu , Grubu , ana grup , alt grup , özel kod 1 , özel kod 2 , özel kod 3"

**Çıkarım:**
- Wolvox'ta `Markası` yanında `[🔍]` (ara) ve `[+]` (yeni) butonları var — kullanıcı tam bunu istiyor.
- `Modeli` alanı da ayrı (bizde `teknik_ozellikler` içinde, ayrı input yok).
- `Grubu / Ara Grubu / Alt Grubu` 3 seviye (bizde D007'de grubu/ana_grup/alt_grup = 3).
- `Özel Kodu 1-3` birebir.
- `Tevkifat Oranı / İstisna Kodu` birebir.
- `Döviz Hesabı Kullan` + `KDV Alış/Satış` zaten bizde var (kdv_orani, para_birimi).

**D007 eşleşme:**
- ✅ **Madde 2**: Marka `+` butonu + modal (Wolvox'taki `+` gibi) — model için de aynı (model = `teknik_ozellikler` veya yeni `model` kolonu? En azından marka + model input'u ekle).
- ✅ **Madde 3**: 8 kolonun isimleri Wolvox ile birebir eşleşiyor, screenshot kanıtı tamam.

**Fark:** Wolvox'un `Birim/Barkod, Fiyatlar` sekmeleri bizde tek sayfada — D007'de tek card içinde göstereceğiz, sekmeye gerek yok.

---

## Sonuç — D007 Kapsamı Screenshot'larla TEYİT

| Screenshot | D007 Madde | Durum |
|------------|------------|-------|
| `irsaliyeler.png` Sil yok + TL sadece | 5, 9 | ✅ kapsamlı |
| `cari kartoteks.png` select + Tek satır | 7, 8, 10 | ✅ kritik repro hazır |
| `Satış irsaliye fatura.png` Wolvox grid + Genel Toplam $ | 1, 5 | ✅ referans anlaşıldı, sadeleştirilmiş döviz/KDV |
| `stok tanımlaro.png` Grubu/Özel Kod/Tevkifat/Marka+ | 2, 3 | ✅ 8 alan + marka+ birebir |

**Eksik yok — D007 direktifi screenshot'ları zaten kapatıyor.** Ek olarak sadece `Modeli` için `stok_kart.model` kolonu eklenebilir (D007'deki 8'e +1), coder opsiyonel yapabilir.

**Sonraki adım:** Coder D007'yi `v1.39.0` olarak kodlar → GM canlı 22/22 + 518/518 + FK0 + MÜŞTERİ-A repro (2 satır) ile mühürler.
