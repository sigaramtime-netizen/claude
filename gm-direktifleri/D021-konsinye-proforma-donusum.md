# D021 — KONSİNYE AİLESİ + PROFORMA + SATIŞ DÖNÜŞÜM + KREDİ KARTI TAHSİLATI (F2, F3, F4)

**Tarih:** 2026-09-16  
**Veren:** KÖPRÜ (Analiz 07 Sıralı Çalışma Planı, D021 kartı & İstemci Talebi doğrultusunda)  
**Öncelik:** Yüksek / Ticari Akış Bütünlüğü  
**Versiyon Hedefi:** v1.51.0 → v1.52.0

---

## 1. GEREKÇE & KÖK NEDEN ÖZETİ
Analist taraması (04/B.1): (F2) konsinye/emsali akış hiç yok — Wolvox'ta konsinye
irsaliye + konsinye fatura + iade varyantları 4 tip; (F3) proforma fiş tipi yok;
(F4) satış tarafı dönüşüm **buton katmanı** eksik — rotaların kendisi hazır:
`/siparis/yeni?kaynak_teklif`, `/irsaliye/yeni?kaynak_siparis`,
`/fatura/yeni?kaynak_irsaliye` v1.51.0'da çalışıyor (K8/K11), sipariş detayında
aksiyon butonları yok ve teklif, siparişe dönüştükten sonra kapanmıyor
(`teklif.durum`'da "Siparişe Dönüştü" yok).
Ayrıca **istemci özel talebi**: fatura ve irsaliye ödemesi/tahsilatı yaparken ödeme
yöntemleri arasına açık ve net bir şekilde **"Kredi Kartı"** seçeneği eklenmelidir.

Tasarım dayanağı: D020'nın **sayaçsız agregat** deseni (iade kalanı = `kaynak −
SUM(iadeler)`, İptal/Reddedildi hariç) konsinye bakiyesine birebir uyarlanır.
Konsinyede **depo stoku hareket etmez**; mal fiziksel olarak carideyken defterde
ana deponun malı kalır — stok olayı yalnız **faturalamada** gerçekleşir.

---

## 2. DETAYLI GEREKSİNİMLER

### BÖLÜM 1: Konsinye ailesi (F2)
1. `irsaliye.tip` CHECK → `('Satis','Alis','Transfer','SatisIade','AlisIade','Konsinye','KonsinyeIade')`;
   `fatura.tip` CHECK → `('Satis','Alis','SatisIade','AlisIade','Konsinye','KonsinyeIade')`.
   Migrasyon: mevcut `_check_rebuild` deseni (D019/D020) + **eski DB kanıtı**.
2. `TIP_ON_EK`: `irsaliye.py` → `"Konsinye": "IKO"`, `"KonsinyeIade": "IKOI"`;
   `fatura.py` → `"Konsinye": "FKO"`, `"KonsinyeIade": "FKOI"`.
3. **Konsinye bakiyesi = sayaçsız agregat** (cari × stok × varyant):
   `bakiye = Σ IKO (Onaylı miktar) − Σ FKO (Onaylı miktar) − Σ IKOI (Onaylı miktar)`
   (İptal/Reddedildi hariç). KonsinyeIade **fatura** bakiyeye girmez (mal ana depona döner).
   Konsinye fatura kalemi girdisi ≤ anlık bakiye; IKOI girdisi ≤ anlık bakiye —
   UI'da canlı "Konsinye Bakiyesi: X" paneli + sunucuda flash+redirect bloke.
4. **Stok kuralı (kesin):** IKO ve IKOI irsaliyede stok hareketi **YOK** (cari 0, yevmiye 0).
   FKO (konsinye fatura) onayında: stok **−** (belgenin deposundan, normal satış
   faturası gibi) + cari alacak + KDV yevmiye (satış faturası aynısı).
   FKOI (iade konsinye fatura) onayında: D020 SatisIade yönleri aynısı
   (cari alacak +, stok +, yevmiye tersi) + `kaynak_fatura_id` → FKO bağlantısı.
   Tüm kayıtlar belgenin kendi (modül, kayıt) kimliğiyle → D020 red fişi/iade
   kapsama mantığıyla çakışmaz (çift sayım testte kanıtlanacak).
5. Akış girişleri:
   - İrsaliye formu `tip=Konsinye` seçeneği (cari zorunlu, depo seçimi stok için
     değil — bakiye paneli cariye göre).
   - IKO detayında "💰 Fatura Oluştur" → `/fatura/yeni?kaynak_irsaliye=<id>&tip=Konsinye`
     (kalemler kopyalanır, miktar ≤ bakiye).
   - FKO detayında "↩ İade" → D020 iade akışı (`KonsinyeIade` tipiyle).
6. **Konsinye stoğu ekranı** `/cari/konsinye`: cari × ürün tablosu (gönderilen,
   faturalanan, iade gelen, **bakiye**) + cari filtresi + Yazdır + CSV
   (D019 CSV standardı). Cari detayında "Konsinye Bakiyesi" kartı.
7. Konsinye belgelerinde D019 çift döviz kolonu + `no_etiket`
   (`KONSİNYE İRSALİYESİ`, `KONSİNYE FATURASI`, iade varyantları) geçerli.

### BÖLÜM 2: Proforma (F3)
8. `fatura.proforma INTEGER NOT NULL DEFAULT 0` kolonu (migrasyon + backfill 0).
9. Giriş: fatura listesinde "🧾 Proforma" → `/fatura/yeni?proforma=1` (tip Satis,
   formda "PROFORMA" rozeti, cari + kalemler normal).
10. No serisi: `PF-YYYY-NNN` (no üretiminde proforma için `on_ek="PF"`; `fatura_no`
    UNIQUE korunur).
11. Onay akışı: Proforma `Taslak → Onaylandı` olabilir; onayda `_cari_uygula`,
    stok ve yevmiye **YALNIZ proforma'da atlanır** (query kanıtı: cari_hareket /
    stok_hareket / yevmiye COUNT = 0).
12. Yazdırma: başlık `PROFORMA FATURA`; alt bilgide "Proforma belge e-fatura sayılmaz."
13. "🔄 Faturaya Dönüştür" → `/fatura/yeni?kaynak_proforma=<id>` (kalemler kopyalanır,
    normal fatura taslağı, `kaynak_proforma_id` bağlanır — kolon yeni).
14. Proforma: iade kaynağı **olamaz** (IADE_KAYNAK değişmez), ekstre/raporda
    görünürlüğü yok (cari hareketi olmadığından doğal), silme/düzenleme normal
    taslak kurallarıyla.

### BÖLÜM 3: Satış dönüşüm buton katmanı (F4)
15. **Sipariş detayında** (yalnız `Onaylandı` + kalan > 0 iken görünür):
    - "🚚 İrsaliye Oluştur" → `/irsaliye/yeni?kaynak_siparis=<sid>`
    - "🧾 İlgili İrsaliyeler" tablosu: no, tarih, durum, **Fatura durumu**
      (Faturalandı / Kısmi / Faturasız — D017 kolonu) + Faturasız/Kısmi olanlar için
      "Fatura Oluştur" linki → `/fatura/yeni?kaynak_irsaliye=<iid>`
16. **Teklif kapanışı:** sipariş `?kaynak_teklif` ile ONAYLANIŞTA teklif.durum →
    `"Siparişe Dönüştü"` (CHECK'e eklenir, migrasyon); sipariş İptal edilirse teklif
    `Onaylandı`'ya döner (yeniden kullanılabilir). `teklif_kalem`/`teklif`'e
    `kaynak_siparis` gerekmez — siparis.kaynak_teklif_id mevcut.
    Teklif detayında "Siparişe Dönüştü: <no>" rozeti + link.
17. Sipariş detayında "Kaynak Teklif: <no>" rozeti (varsa).

### BÖLÜM 4: Kredi Kartı ile Tahsilat / Ödeme (İstemci Özel Talebi)
18. Fatura ve İrsaliye tahsilat/ödeme modallarında ve hızlı ödeme ekranlarında ödeme türü
    seçeneklerine **"Kredi Kartı"** seçeneği eklenecektir (`Nakit`, `Banka / Havale`, `Kredi Kartı`).
19. Kredi kartı ile tahsilat seçildiğinde:
    - Cari hareketinde `islem_turu = 'Kredi Karti'` (veya `aciklama` alanında Kredi Kartı Tahsilatı)
      olarak işaretlenecektir.
    - Eğer POS modülü bağlı ise ilgili POS hesabı seçilebilecek; bağlı değilse doğrudan banka/kredi kartı
      hesabına borç/alacak kaydı düşecektir.
    - Ekranda ve makbuzda yöntem olarak net bir şekilde **"Kredi Kartı"** yazacaktır.

---

## 3. KABUL KRİTERLERİ & TEST
- [ ] `test_d021_konsinye_proforma_donushum.py` (min. 15 kontrol):
  - 4 konsinye tipi oluşturulur; no serileri `IKO/FKO/IKOI/FKOI-2026-001` UNIQUE.
  - IKO onayı: stok 0, cari 0, yevmiye 0 (COUNT kanıtı); bakiye +.
  - FKO onayı: bakiye −, stok −, cari alacak +, KDV yevmiye; bakiye aşımı bloke (UI+DB).
  - IKOI: bakiye −, stok/cari 0.
  - FKOI: SatisIade yönleri (cari alacak +, stok +) + bakiyeye etki 0.
  - FKO'nun red fişi: stok geri, cari ters, **bakiye otomatik +** (agregat, sayaç yok).
  - Konsinye stoğu ekranı: gönderilen − faturalanan − iade = bakiye (SQL ile birebir); CSV 200.
  - Proforma: onayda yan etki 0 (3 COUNT sorgusu), yazdırda PROFORMA başlığı, "Faturaya Dönüştür" → taslak + bağ.
  - Proforma iade kaynağı yapılamaz (403/flash).
  - Sipariş detay: butonlar yalnız Onaylı+kalan>0'da; İrsaliye → Fatura (kısmi) zinciri; fatura durumu kolonu senkron.
  - Teklif: sipariş onayında "Siparişe Dönüştü" (kilit: düzenleme engelli), sipariş iptalinde "Onaylandı"ya dönüş.
  - Kredi Kartı Ödemesi: Faturadan "Kredi Kartı" seçeneği ile tahsilat yapılır; cari hareketinde ve ödeme durumunda "Kredi Kartı" olarak işlenir ve kalan düşer.
  - USD konsinye: pb devralma + çift kolon.
  - Migrasyon: v1.51.0 şeması → v1.52 (CHECK'ler + proforma + teklif durum; veri + FK + idempotent).
- [ ] Tam regresyon: 34 mevcut + 1 yeni = **35 test dosyası, 0 hata**.

---

## 4. İSTENEN TESLİM
- `kanitlar/v1.52.0/` altında: test çıktısı, tam regresyon, diff, **eski DB
  migrasyon kanıtı**, hash dosyası.
- Sansürlü teslim ZIP (`D021-v1.52.0.zip`) + MD5/SHA256 kanıtları.
- `CHANGELOG.md` v1.52.0 + `config.SURUM`/`SURUM_TARIHI`.
- Rapor: `coder-raporlari/R021-konsinye-proforma-donushum.md` (R019 formatında).
