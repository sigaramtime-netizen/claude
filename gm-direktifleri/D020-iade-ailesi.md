# D020 — İADE AİLESİ: 4 YENİ FİŞ TİPİ + KAYNAK BELGE DÖNÜŞÜMÜ (F1)

**Tarih:** 2026-09-16  
**Veren:** KÖPRÜ (Analiz 07 Sıralı Çalışma Planı, D020 kartı doğrultusunda)  
**Öncelik:** Çok Yüksek / Ticari Akış Bütünlüğü  
**Versiyon Hedefi:** v1.50.0 → v1.51.0

---

## 1. GEREKÇE & KÖK NEDEN ÖZETİ
Analist taraması (04/B.1, 07 planı): `fatura.tip` yalnız `{Satis, Alis}`, `irsaliye.tip`
`{Satis, Alis, Transfer}`. **İade belgesi tipi yok** — iadeler bugün negatif turlu normal
fatura ya da manuel yevmiyeyle işleniyor: kaynak belge bağlantısı, kısmi iade takibi ve
denetim izi yok. Wolvox'ta satış/alış için 4 ayrı iade fiş tipi + kaynak belgeden dönüşüm
vardır; bu, ticari akış bütünlüğünün (F1) çekirdeğidir.

Tasarım dayanağı: D019'da kurulmuş **red fişi storno deseni** (cari ters hareket +
yevmiye storno `kaynak_sahne='red'` + kendi (modül, kayıt) stok hareketleri tersi +
audit + kilit) iade akışına uyarlanır. Fark: **iade, kaynak belgenin tersi değil,
kendi kayıtlarını taşıyan YENİ bir belgedir**; her iade kalemi, kopyalandığı kaynak
kaleme `kaynak_kalem_id` ile bağlanır.

---

## 2. DETAYLI GEREKSİNİMLER

### BÖLÜM 1: DB şeması & no serileri
1. `fatura.tip` CHECK → `('Satis','Alis','SatisIade','AlisIade')`;
   `irsaliye.tip` CHECK → `('Satis','Alis','Transfer','SatisIade','AlisIade')`.
   Migrasyon: D019 rebuild pattern (yeni DB + **eski DB kanıtı** zorunlu).
2. `TIP_ON_EK` güncellenir: `fatura.py` → `"SatisIade": "SFIAD"`, `"AlisIade": "AFIAD"`;
   `irsaliye.py` → `"SatisIade": "IRSIAD"`, `"AlisIade": "IRAIAD"`.
   No üretimi mevcut `db.sonraki_belge_no` ile (şirket bazlı, yıl sayaçlı).
3. Yeni kolonlar (migrasyon + boş backfill):
   - `fatura.kaynak_fatura_id INTEGER REFERENCES fatura(id)` — iadenin kaynak faturası
   - `irsaliye.kaynak_irsaliye_id INTEGER REFERENCES irsaliye(id)` — iadenin kaynak irsaliyesi
   - `fatura_kalem.kaynak_kalem_id INTEGER` / `irsaliye_kalem.kaynak_kalem_id INTEGER`
     — iade kaleminin, kopyalandığı kaynak kaleme bağı
   - `irsaliye.durum` CHECK'e `'Reddedildi'` eklenir (iade irsaliyeye de red fişi
     çalışmalı; D019 bunu yalnız faturaya eklemişti).
4. `DURUMLAR` listeleri ve tip rozetleri: iade tipleri listelerde kırmızı/amber rozetle
   ayrılır.

### BÖLÜM 2: İade oluşturma akışı (kaynak belgeden dönüşüm)
5. Giriş noktaları (2 adet):
   - Onaylı fatura/irsaliye **detayında** "↩ İade Faturası Oluştur" / "↩ İade İrsaliyesi
     Oluştur" butonu (yalnız Onaylı belgede görünür).
   - Liste ekranında "↩ Yeni İade" → kaynak belge seçimi (no/cari arama) → dönüşüm.
6. Kaynak seçilince kalemler otomatik kopyalanır: miktar **düzenlenebilir ama
   iade edilebilir kalanı aşamaz** (kısmi iade):
   `kalan = kaynak kalem miktarı − SUM(kaynak_kalem_id = X olan iade kalemleri)`.
   Formda kalem başına "İade edilebilir: X" ipucu; limiti aşan kayıt UI'da ve DB'ye
   yazarken (flash + redirect) bloke edilir.
7. Kaynak belge detayında: "İade Edilen: X / Y" satırı + bağlı iadeler listesi
   (no + tarih + tutar + durum, tıklanabilir).
8. İade durumu normal belge gibi **Taslak → Onaylandı** akışıyla ilerler; tüm yan
   etkiler (cari/stok/yevmiye) YALNIZ onayda oluşur. Taslak iade silinebilir.
9. İadenin para birimi = kaynak belgenin para birimi (değiştirilemez, form okunur).
   Kur: iade tarihindeki TCMB kuru (otomatik) ya da manuel giriş — D012/D017 deseni.

### BÖLÜM 3: Muhasebe & stok yönleri (kesin)
10. **Satış iadesi (SatisIade):** cari `alacak=+tutar` (alacak düşer — D019 red fişi
    Satis yönüyle aynı), stok **+** (ürün depona döner), yevmiye `kaynak_modul='Fatura'`,
    `kaynak_sahne='iade'`, KDV satırları satış faturasının tersi.
11. **Alış iadesi (AlisIade):** cari `borc=+tutar` (tedarikçiye borç düşer), stok **−**,
    yevmiye aynası (KDV alımın tersi).
12. **İade irsaliye:** YALNIZ stok (satış iadesi → +, alış iadesi → −); cari hareket
    0, yevmiye 0 (normal irsaliye deseniyle aynı).
13. Stok hareketleri iadenin **kendi (modül, kayıt)** kimliğiyle yazılır → D019 red
    fişinin ters çevirme kapsamı (kaynak_sahne='red', (modül, kayıt) bazlı) iadenin
    stokunu ancak iade red fişi tetiklediğinde çevirir. **Kaynak belgenin stokuna
    hiçbir iade işlemi doğrudan dokunmaz** (çift sayım yasak — testte SQL kanıtı).
14. K18: tüm tutarlar DAİMA TL karşılığı saklanır + `para_birimi`/`doviz_kur` kolonları
    (fatura/irsaliye/cari deseni aynen).
15. Kontrol miktar bazındadır (kalem kalem); tutar, kur farkından kaynak tutardan
    sapabilir — bu bir hata değildir, formda "kaynak tutar: X / iade tutarı: Y" bilgilendirmesi yeterlidir.

### BÖLÜM 4: Görünüm & yazdırma
16. Fatura/irsaliye listelerinde tip filtresine 4 yeni tip; liste satırında tip kolonu.
17. Detayda "Kaynak Belge" kartı (no + link) ve "Bu Belgenin İadeleri" bölümü.
18. `yazdir/belge.html` → `no_etiket` haritasına: `SATIŞ İADE FATURASI`,
    `ALIŞ İADE FATURASI`, `SATIŞ İADE İRSALİYESİ`, `ALIŞ İADE İRSALİYESİ`;
    başlık bloğuna kaynak satırı: **"İadesi: SF-2026-001"** (varsa).
    D019 çift döviz kolonu iade belgelerinde de geçerlidir.

### BÖLÜM 5: Kilitler & yetki
19. İadeye red fişi: yalnız Onaylı iade; ters kayıt iadenin kendi kayıtlarını çevirir,
    kaynak belgenin "iade edilen" toplamı agregat sorgudan (sayaç yok) otomatik
    düşer → asenkronlaşma imkânsız.
20. İadeye bağlı tahsilat/ödeme (Kasa/Banka) varsa red fişi 302 + uyarıyla kilitlenir
    (D019 kuralı).
21. Yetki: oluşturma = ilgili modülün yazma yetkisi; onay = `FATURA_ONAY`
    (fatura) / mevcut irsaliye onay rolü (irsaliye); yetkisiz istek flash + redirect.

---

## 3. KABUL KRİTERLERİ & TEST
- [ ] `test_d010..d019` tarzında `test_d020_iade_ailesi.py` yazılacak (min. 12 kontrol):
  - 4 tipin her biri oluşturulur; no serileri `SFIAD-2026-001` vb. UNIQUE.
  - Satış iadesi onayı: cari alacak −tutar, stok +miktar, yevmiye satırları (SQL ile miktar eşleşmesi).
  - Alış iadesi onayı: cari borç −tutar, stok −miktar.
  - İade irsaliye: yalnız stok; cari hareket 0, yevmiye 0 (COUNT sorgusu kanıtı).
  - Kısmi iade: 100'lük kaleme 40 → "İade edilebilir: 60"; 2. iadede 61 giriş bloke (UI + DB).
  - Kaynak detayda "İade Edilen: 40/100" + iade linki görünür.
  - **Çift sayım:** iadenin red fişi yalnız iadenin kendi stokunu çevirir; kaynak belgenin stoku değişmez (önce/sonra SQL).
  - USD kaynak faturadan iade: pb devralınır, yazdırmada çift kolon, kaynak satırı basılır.
  - Taslak iade: yan etki 0 (cari/stok/yevmiye COUNT), silinebilir.
  - Kilit: iadeye tahsilat bağlıyken red fişi engellenir.
  - Yetki: onay rolü olmayan kullanıcı 403/flash alır.
  - Migrasyon: v1.50.0 şemalı eski DB → yeni şema (CHECK'ler + kolonlar + veri korunumu + FK temiz).
- [ ] Tam regresyon: 33 mevcut test + 1 yeni = **34 test dosyası, 0 hata**.

---

## 4. İSTENEN TESLİM
- `kanitlar/v1.51.0/` altında: test çıktısı, tam regresyon çıktısı, diff, **eski DB
  migrasyon kanıtı**, hash dosyası.
- Sansürlü teslim ZIP (`D020-v1.51.0.zip`) + MD5/SHA256 kanıtları.
- `CHANGELOG.md` v1.51.0 bölümü + `config.SURUM`/`SURUM_TARIHI` güncellemesi.
- Rapor: `coder-raporlari/R020-iade-ailesi.md` (R019 formatında).
