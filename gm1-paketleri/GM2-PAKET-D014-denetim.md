# GM2 DENETİM PAKETİ — D014 (v1.45.0)
**Tarih:** 2026-09-15  
**Görev:** D014 — Kapsamlı Yazdırma/Çıktı Tamamlama + Tanım Verileri Düzenleme  
**Önceki Sürüm:** v1.44.0 (D013 MÜHÜRLÜ)  
**Yeni Sürüm:** v1.45.0  
**Nöbetçi GM:** GM2 (Arena GM — Acil Yedek Devrede)  
**Hazırlayan:** KÖPRÜ (Bağımsız Denetim Doğrulaması)

---

## 1. BAĞIMSIZ DOĞRULAMA ÖZETİ (KÖPRÜ TEST ÇIKTISI)

KÖPRÜ ortamında sıfırdan DB init edilmiş, test sunucusu ayağa kaldırılmış ve tam suite bağımsız çalıştırılmıştır:

1. **Yeni Test Paketi (`test_d014_yazdirma_tanimlar.py`):**
   - **16 / 16 BAŞARILI** (0 hata, exit=0)
   - Bölüm A1 (4 fiziksel çıktı: Cari Makbuz, Servis Fişi/İş Emri, Bakım Sözleşmesi, Banka Fişi 200 OK + Wolvox teması): **GEÇTİ**
   - Bölüm A2 (Arşiv çıktıları: Depo Transfer sevk, Demirbaş Amortisman, Satın Alma Talep/Teklif, Teklif şablonu konsolidasyonu): **GEÇTİ**
   - Bölüm A3 (Rapor butonları: CRM/Eksik/Rapor Yazdır + POS fatura kısayolu): **GEÇTİ**
   - Bölüm B (5 tanım tipinde Ekle/Düzenle/Pasifleştir, Marka pasifleştirme, kullanılan kod/tip kilit koruması): **GEÇTİ**
   - Bölüm K1 / FK (Şirket izolasyonu + FK=0 bütünlük + kalıntı=0): **GEÇTİ**

2. **Tam Regresyon Suite (`regresyon_runner.py`):**
   - **29 TEST DOSYASI / 633 KONTROL — 0 BAŞARISIZLIK (exit=0)**
   - Sistemdeki hiçbir modül bozulmamıştır.

3. **Sansür ve Hijyen:**
   - Kod, döküman ve ZIP tamamen sansürlüdür (MÜŞTERİ-A; müşteri isim kalıntısı = 0).
   - `.png`, `.pyc`, `__pycache__` temizlenmiştir.

---

## 2. DENETİM ZIP PAKETİ

- **Dosya:** `paketler/BRN-Teknoloji-ERP-v1.45.0-D014-GM1-denetim.zip`
- **Boyut:** 959.221 bayt
- **MD5:** `4c2375c2affbea3d2b596d61900113e5`
- **SHA256:** `64b25c8d3916ad4e5aac500bfd061688193f60c1be84c793625abbf3332d7df8`

---

## 3. RAW BAĞLANTILARI (PUBLIC REPO)

- **D014 Direktifi:** [D014 Direktif](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/gm-direktifleri/D014-yazdirma-tanimlar-duzenleme.md)
- **Devir Notu:** [Devir Brifingi (GM1 -> GM2)](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/devir/D014-gm1-den-gm2.md)
- **Coder Raporu (R014):** [R014 Coder Raporu](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/coder-raporlari/R014-yazdirma-tanimlar-duzenleme.md)
- **Zip Bilgi & Hash:** [D014 Zip Hash](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D014/D014-zip-hash.txt)
- **Tam Regresyon Çıktısı:** [D014 Regresyon](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D014/D014-tam-regresyon.txt)
- **Test Dosyası:** [test_d014_yazdirma_tanimlar.py](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D014/test_d014_yazdirma_tanimlar.py)
- **Değişen Dosyalar:** [D014 Değişen Dosyalar](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D014/D014-degisen-dosyalar.txt)
- **Genel Durum:** [DURUM.md](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/DURUM.md)
