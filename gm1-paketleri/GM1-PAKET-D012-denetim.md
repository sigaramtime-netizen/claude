# GM1 DENETİM PAKETİ — D012 (v1.43.0)
**Tarih:** 2026-09-15  
**Görev:** D012 — Satır Bazlı KDV + Çoklu Döviz + Para Birimi & Birim DB Tablo Geçişi  
**Önceki Sürüm:** v1.42.0 (D011 MÜHÜRLÜ)  
**Yeni Sürüm:** v1.43.0  
**Hazırlayan:** KÖPRÜ (Bağımsız Denetim Doğrulaması)

---

## 1. BAĞIMSIZ DOĞRULAMA ÖZETİ (KÖPRÜ TEST ÇIKTISI)

KÖPRÜ ortamında sıfırdan DB init edilmiş, test sunucusu ayağa kaldırılmış ve tam suite bağımsız çalıştırılmıştır:

1. **Yeni Test Paketi (`test_d012_kdv_doviz_master.py`):**
   - **21 / 21 BAŞARILI** (0 hata, exit=0)
   - BÖLÜM B (Satır KDV: karışık dahil/hariç hesaplama, satır override, boş default): **GEÇTİ**
   - BÖLÜM X (DB tohum 4 PB + 11 Birim, inline ekleme, pasifleştirme, TRY koruması, K1 şirket izolasyonu): **GEÇTİ**
   - BÖLÜM D (Döviz + TL eşzamanlı gösterim, kur çarpımı K2, ekstre/kartoteks döviz filtresi): **GEÇTİ**
   - BÖLÜM F (FK bütünlüğü = 0, kalıntı = 0): **GEÇTİ**

2. **Tam Regresyon Suite (`regresyon_runner.py`):**
   - **27 TEST DOSYASI / 603 KONTROL — 0 BAŞARISIZLIK (exit=0)**
   - Hiçbir modülde kırılma yok.

3. **Sansür ve Güvenlik:**
   - Kod ve dökümanlar tamamen sansürlenmiştir (Yakup Erbaş / müşteri isim kalıntısı = 0).
   - `.png`, `.pyc`, `__pycache__` temizlenmiştir.

---

## 2. DENETİM ZIP PAKETİ (GM1 İÇİN)

GM1 bağımsız çalıştırma kuralına uygun olarak tüm kod, şablonlar, dökümanlar ve demo DB tek zip içinde paketlenmiştir:

- **Dosya Adı:** `paketler/BRN-Teknoloji-ERP-v1.43.0-D012-GM1-denetim.zip`
- **Boyut:** 873.456 bayt
- **MD5:** `fce71e82265fd5e7ce55bbab83241947`
- **SHA256:** `dfe936ed815726e31f13b1b30d2fac4a4e4372a85db12a00b6cbd2b29cb23f8c`

---

## 3. RAW BAĞLANTILARI (PUBLIC REPO)

- **D012 Direktifi:** [D012 Direktif](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/gm-direktifleri/D012-satir-kdv-coklu-doviz-parabirimi-birim-db-v1.43.0.md)
- **Coder Raporu (R012):** [R012 Coder Raporu](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/coder-raporlari/R012-satir-kdv-coklu-doviz-parabirimi-birim-db.md)
- **Zip Bilgi & Hash:** [D012 Zip Hash](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D012/D012-zip-hash.txt)
- **Değişen Dosyalar:** [D012 Değişen Dosyalar](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D012/D012-degisen-dosyalar.txt)
- **Tam Regresyon Çıktısı:** [D012 Regresyon](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D012/D012-tam-regresyon.txt)
- **Test Dosyası:** [test_d012_kdv_doviz_master.py](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D012/test_d012_kdv_doviz_master.py)
- **Denetim ZIP İndir:** [BRN-Teknoloji-ERP-v1.43.0-D012-GM1-denetim.zip](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/paketler/BRN-Teknoloji-ERP-v1.43.0-D012-GM1-denetim.zip)
