# D023 — MUHASEBE ÇEKİRDEĞİ: HESAP EŞLEMELERİ + FİŞ HAREKETLERİ + HESAP DURUMU + TEMİNAT ÇEK/SENET (M2, M3, M4, T2)

**Tarih:** 2026-09-18  
**Veren:** KÖPRÜ (Analiz 07 Sıralı Çalışma Planı, D023 kartı doğrultusunda)  
**Öncelik:** Orta / Muhasebe Çekirdeği Derinleştirme  
**Versiyon Hedefi:** v1.53.0 → v1.54.0

---

## 1. GEREKÇE & KÖK NEDEN ÖZETİ
Analist taraması (04/B.2, D022 sonrası yeniden doğrulandı):
(M2) Yevmiye satır hesapları **koddaki sabit stringler** — `_fatura_satirlar`
(`muhasebe.py`): satış `120/600/391`, alış `153+191/320` (manuel → `770`),
iadeler ayna; `_cek_satirlar`, amortisman `770/257`. Tekdüzen planı `hesap`
tablosunda VAR ama eşleme ekrandan değiştirilemiyor; şirket hesabı farklı
kod kullanmak istediğinde kod değişikliği gerekir.
(M3) Fiş **satır** seviyesinde liste ekranı yok (`/muhasebe/defter` tek
hesabın dökümü; tüm fişlerin satırları hesap/tip/tarih filtreli görülemiyor).
(M4) **Hesap Durumu** ekranı yok (çoklu hesap × aylık: açılış + hareket +
kapanış matrisi) — mizan anlık toplam, defter satır dökümü; ikisi de bu
ekran değil.
(T2) Teminat çek/senet hiç yok (`cek_senet`'te teminat kolonu 0 hit).

---

## 2. DETAYLI GEREKSİNİMLER

### BÖLÜM 1: Hesap eşleme tanımları (M2)
1. `hesap_esleme` tablosu: `id, sirket_id, anahtar TEXT, hedef_kod TEXT,
   not_ TEXT, UNIQUE(sirket_id, anahtar)`. Anahtarlar (varsayılanlar = mevcut
   sabitler, davranış değişmez):
   | anahtar | varsayılan |
   |---|---|
   | `satis_alici` | 120 |
   | `satis_hasilat` | 600 |
   | `satis_kdv` | 391 |
   | `alis_satici` | 320 |
   | `alis_kdv` | 191 |
   | `alis_stok` | 153 |
   | `alis_manuel_gider` | 770 |
   | `kasa` | 100 |
   | `banka` | 102 |
   | `cek_alinan` | 101 |
   | `cek_verilen` | 103 |
   | `amortisman_gider` | 770 |
   | `amortisman_birikmis` | 257 |
2. `db.py`'ye `hesap_esleme_get(conn, anahtar, sid)` — eşleme yoksa veya
   hedef kod o şirkette `hesap` tablosunda yoksa **varsayılana düşer**
   (asla hatalı fiş). Şirket kurulumunda (`sirket_seed`) varsayılanlar
   eklenir (idempotent).
3. **Tüm** `_*_satirlar` fonksiyonları (`_fatura_satirlar`, `_kasa_satirlar`,
   `_banka_satirlar`, `_cek_satirlar`, demirbaş amortisman) sabit kod yerine
   `hesap_esleme_get` kullanır. D022 `fis_tipi_bul` deseni korunur.
4. Ekran `/muhasebe/eslemeler` (MUH_WRITE): anahtar × (mevcut kod, hesap adı,
   not) tablosu + kod değişikliği (o şirketin `hesap` tablosundan dropdown) +
   "Varsayılana Döndür" butonu. Her değişiklik audit (`hesap-esleme`).
5. Eşleme değişikliği **geleceğe** etkilidir: mevcut yevmiyeler yeniden
   üretilmez (mevcut fiş dokunulmaz).

### BÖLÜM 2: Fiş hareketleri (satır) listesi (M3)
6. Ekran `/muhasebe/hareketler` (görmek herkese, MUH okuma):
   `yevmiye_kalem` × `yevmiye` × `hesap` JOIN. Kolonlar: Tarih, Fiş No,
   **Fiş Tipi** (D022 rozeti), Hesap Kodu + Ad, Açıklama, Borç, Alacak,
   Kaynak (modül + belge no — tıklanabilir: Fatura→/fatura/<id>, Kasa→
   kasa hareket fişi, Mahsup→/muhasebe/<id> vb.).
7. Filtreler: tarih aralığı, hesap (tek veya kod aralığı, örn. 100-199),
   fiş tipi (D022), cari/belge no metin arama. Alt toplamlar: Σborç, Σalacak
   (filtre kapsamında, dengeli olmalı — uyarı rozeti).
8. Yazdır + CSV (D019 standardı: BOM, `;`, TR sayı). Boş sonuç: "kayıt yok".

### BÖLÜM 3: Hesap Durumu ekranı (M4)
9. Ekran `/muhasebe/hesap-durumu`: çoklu hesap seçimi (checkbox + "tümü") →
   matris: satırlar = seçili hesaplar, kolonlar = yılın ayları (12) + TOPLAM.
   Her hücre: ay borç / ay alacak; satır başı: **açılış bakiyesi**; satır sonu:
   **kapanış bakiyesi** (aktif/pasife göre borç−alacak işareti). Alt satır:
   aylık Σborç / Σalacak / net.
10. Parametre: yıl seçimi + "kümülatif bakiye göster" (varsa mevcut mizan
    bakiye deseniyle tutarlı). Yazdır.
11. Doğrulama: her hesap için `açılış + Σaylar = kapanış` testte SQL ile
    birebir.

### BÖLÜM 4: Teminat çek/senet (T2)
12. `cek_senet`'e kolonlar: `teminat INTEGER NOT NULL DEFAULT 0`,
    `teminat_durum TEXT NOT NULL DEFAULT 'Yok' CHECK (teminat_durum IN
    ('Yok','Aktif','Mahsup Edildi','İade Edildi'))` (migrasyon + backfill).
13. **Teminat = carinin bize verdiği, alacağını güvenceleyen çek/senet**
    (yedek; alacak silinmez). Oluşturma: çek/senet formunda `teminat`
    checkbox + tutar (≤ carinin borç bakiyesi, UI+sunucu) + vade.
    Oluşturma **defter dışıdır**: cari 0, yevmiye 0 (COUNT kanıtı).
14. **Vade işleme:** `/cek-senet/teminat` ekranında vadesi gelen Aktif
    teminatlar listelenir + "Vadeyi İşle" aksiyonu (tekli/toplu):
    - carinin borç bakiyesi ≥ teminat tutarı → **tam mahsup**: cari
      `alacak=+tutar` (alacak düşer) + yevmiye `101 ALINAN ÇEKLER borç /
      120 ALICILAR alacak` (hesap kodları M2 eşlemesinden: `cek_alinan`,
      `satis_alici`) + durum `'Mahsup Edildi'` + audit `teminat-mahsup`.
    - borç < tutar → borç kadar mahsup, kalan `"Kalan X iade edildi"`
      açıklamasıyla durum `'Mahsup Edildi'` (kalan parça fişi yok — açıklama
      + audit yeterli).
    - borç 0 → durum değişmez, uyarı ("borç kalmamış, iade edin").
15. **Erken iade:** Aktif teminat detayında "↩ İade Et" (yetki: çek/senet
    yazma) → durum `'İade Edildi'`, mali etki 0, audit `teminat-iade`.
16. **Teminat bordrosu** `/cek-senet/teminat`: cari × teminat tutarı × vade ×
    durum + filtre (durum, cari) + Yazdır + CSV. Cari detayında "Teminat
    Çek/Senet" kartı (Aktif toplamı).
17. Teminat, normal çek/senet listesinde "Teminat" rozetiyle ayrılır;
    teminat çek **vade gelmeden** tahsilat/ödeme akışına giremez (kilit).

---

## 3. KABUL KRİTERLERİ & TEST
- [ ] `test_d023_muhasebe_cekirdegi.py` (min. 14 kontrol):
  - Eşleme: `satis_hasilat` 600→602 değiştir → yeni satış faturasının yevmiyesi
    602 kullanır; eski fişler değişmez; eşleme ekranı + "varsayılana dön" + audit.
  - Geçersiz kod (şirkette olmayan) → varsayılana düşer, fiş yine dengeli.
  - Kasa/banka/çek/amortisman eşlemeleri de geçerli (4 örnek).
  - Hareketler listesi: hesap aralığı + tip + tarih filtresi SQL ile birebir;
    kaynak linkleri çalışıyor; alt toplam dengeli; CSV 200 + BOM.
  - Hesap Durumu: 12 ay matrisinde `açılış + Σ = kapanış` (3 hesap, SQL kanıtı);
    çoklu seçim + yazdır.
  - Teminat oluşturma: cari 0 + yevmiye 0 (COUNT kanıtı); bakiye aşımı bloke.
  - Vade işleme (tam): cari alacak −tutar, yevmiye 101/120 dengeli, durum + audit.
  - Vade işleme (kısmi): borç < tutar → borç kadar mahsup + açıklama.
  - Vadesi gelen teminatın normal tahsilat akışına girişi kilitli.
  - Erken iade: durum değişir, mali etki 0, audit.
  - Bordro: cari bazlı toplam doğru + CSV; cari detay kartı.
  - Yetki: eşleme/vade-işleme/iade → yazma yetkisi; yetkisiz 403.
  - Şirket izolasyonu: şirket dışı hesap/kod/teminat kabul edilmez.
- [ ] Tam regresyon: 36 mevcut + 1 yeni = **37 test dosyası, 0 hata**.

---

## 4. İSTENEN TESLİM
- `kanitlar/v1.54.0/` altında: test çıktısı, tam regresyon, diff, **eski DB
  migrasyon kanıtı** (teminat kolonları + hesap_esleme seed), hash dosyası.
- Sansürlü teslim ZIP (`D023-v1.54.0.zip`) + MD5/SHA256 kanıtları.
- `CHANGELOG.md` v1.54.0 + `config.SURUM`/`SURUM_TARIHI`.
- Rapor: `coder-raporlari/R023-muhasebe-cekirdegi-teminat.md` (R019 formatında).
