# GM1 DENETİM PAKETİ — D013 (v1.44.0)
**Tarih:** 2026-09-15  
**Görev:** D013 — Cari Tahsilat / Ödeme Ekranı (POS Ödemeler Deseni + İki Rota + Yetki)  
**Önceki Sürüm:** v1.43.0 (D012 MÜHÜRLÜ)  
**Yeni Sürüm:** v1.44.0  
**Hazırlayan:** KÖPRÜ (Bağımsız Denetim Doğrulaması)

---

## 1. BAĞIMSIZ DOĞRULAMA ÖZETİ (KÖPRÜ TEST ÇIKTISI)

KÖPRÜ ortamında sıfırdan DB init edilmiş, test sunucusu ayağa kaldırılmış ve tam suite bağımsız çalıştırılmıştır:

1. **Yeni Test Paketi (`test_d013_cari_tahsilat_odeme.py`):**
   - **14 / 14 BAŞARILI** (0 hata, exit=0)
   - Bölüm A (Formlar, Alınan/Verilen notları, kart/ekstre butonları): **GEÇTİ**
   - Bölüm B (Karışık tahsilat: Nakit 3000 + Kart 2000 %2 komisyon, kasa/banka/alacak, yevmiye 100/120 ve 102/120, kısmi kapatma): **GEÇTİ**
   - Bölüm C (Karışık ödeme: Havale 3000 + Nakit 500, borç azaltma, yevmiye 320/102 ve 320/100): **GEÇTİ**
   - Bölüm D (Çek/Senet iki yön: Tahsilatta Alınan / Ödemede Verilen zorunlu, yevmiye): **GEÇTİ**
   - Bölüm E (Döviz USD kur TL çevrim, fazla tahsilat avans uyarısı, Satış rolü ödeme yapamaz 403, K1 şirket izolasyonu 403, vadesiz çek engeli): **GEÇTİ**
   - Bölüm F (FK bütünlüğü = 0, D013TEST kalıntı = 0): **GEÇTİ**

2. **Tam Regresyon Suite (`regresyon_runner.py`):**
   - **28 TEST DOSYASI / 617 KONTROL — 0 BAŞARISIZLIK (exit=0)**
   - Sistemdeki hiçbir modül bozulmamıştır.

3. **Sansür ve Hijyen:**
   - Kod, döküman ve ZIP tamamen sansürlüdür (MÜŞTERİ-A; isim kalıntısı = 0).
   - `.png`, `.pyc`, `__pycache__` temizlenmiştir.

---

## 2. DENETİM ZIP PAKETİ (GM1 İÇİN)

GM1 bağımsız çalıştırma kuralına uygun olarak tüm kod, şablonlar, dökümanlar ve demo DB tek zip içinde sunulmaktadır:

- **Dosya Adı:** `paketler/BRN-Teknoloji-ERP-v1.44.0-D013-GM1-denetim.zip`
- **Boyut:** 916.608 bayt
- **MD5:** `73f8cfad3b27fe011f1e743268a12fd8`
- **SHA256:** `9b804e5a367a80cf4743ef7e093739a47f4669d37c3f78171742b0b7aa9bb9d8`

---

## 3. RAW BAĞLANTILARI (PUBLIC REPO)

- **D013 Direktifi:** [D013 Direktif](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/gm-direktifleri/D013-cari-tahsilat-odeme.md)
- **Coder Raporu (R013):** [R013 Coder Raporu](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/coder-raporlari/R013-cari-tahsilat-odeme.md)
- **Zip Bilgi & Hash:** [D013 Zip Hash](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D013/D013-zip-hash.txt)
- **Tam Regresyon Çıktısı:** [D013 Regresyon](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D013/D013-tam-regresyon.txt)
- **Test Dosyası:** [test_d013_cari_tahsilat_odeme.py](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D013/test_d013_cari_tahsilat_odeme.py)
- **Denetim ZIP İndir:** [BRN-Teknoloji-ERP-v1.44.0-D013-GM1-denetim.zip](https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/paketler/BRN-Teknoloji-ERP-v1.44.0-D013-GM1-denetim.zip)
