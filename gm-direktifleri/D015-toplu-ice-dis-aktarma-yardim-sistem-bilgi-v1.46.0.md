# D015 — TOPLU İÇE/DIŞA AKTARMA BİRLİĞİ + YARDIM MERKEZİ + SİSTEM BİLGİ PANELİ DİREKTİFİ

**Tarih:** 2026-09-15  
**Veren:** GM2 (Genel Müdür 2 — Arena GM, Nöbette / Acil Yedek Devrede)  
**Öncelik:** Orta  
**Versiyon Hedefi:** v1.45.0 → v1.46.0  

---

## GEREKÇE
D014 sonrası kalan 3 operasyonel boşluk: aktarım dağınık, yardım yok, sistem bilgisi dağınık — iş mantığına dokunmadan kapatılacak.

---

## GEREKSİNİMLER

### BÖLÜM A — Aktarım Birliği (CSV / Excel İçe-Dışa Aktarma)
- **Şablon & İçe Aktarma:**
  - `GET /.../sablon` (CSV UTF-8 BOM)
  - `POST /.../ice-aktar` (Önizleme → `?onay=1` ile yazma, validasyon, K1 izolasyonu, audit kaydı).
  - İlk hedef 5 liste: **Stok, Cari, Kategori, Birim, Marka** (`core.aktarim` helper fonksiyonu ile ortaklaştırılacak).
- **Dışa Aktarma:**
  - Dışa aktarımı eksik olan listelere dışa aktarma (CSV) desteği eklenmesi.

### BÖLÜM B — Yardım Merkezi & Kısayollar
- **Yardım Ekranı:** `GET /yardim` (10+ konu kartı, `?q` filtreleme, `docs/` dökümanlarını kaynak alan yapı).
- **Kısayollar & Modallar:**
  - `Ctrl+K` global arama modalı.
  - `?` tuşu ile açılan klavye kısayolları yardım modalı (`shortcuts.js` < 2KB).

### BÖLÜM C — Sistem Bilgi Paneli (Yalnızca Admin)
- **Sistem Bilgi Rotası:** `GET /sistem/bilgi`
  - Sürüm / commit hash bilgisi.
  - DB integrity kontrolü, FK kontrolü, tablo sayıları ve veritabanı boyutu.
  - Son yedek durumu, son migrasyon bilgisi.
  - `/api/saglik` durumu gösterimi.
  - Arayüz footer'ına bilgi bağlantısı.

---

## KABUL KRİTERLERİ (test_d015_toplu_yardim_sistem.py)
- [ ] **A1:** 5 liste için şablon indirme + önizleme + onay ile aktarım + K1 izolasyonu.
- [ ] **A2:** Dışa aktarma (CSV) fonksiyonlarının eksiksiz çalışması.
- [ ] **B1:** `GET /yardim` rotası (200 OK + kartlar + arama filtresi).
- [ ] **B2:** Klavye kısayol modalı ve global arama desteği (`shortcuts.js`).
- [ ] **C1:** `GET /sistem/bilgi` (Admin erişir, yetkisiz 403; DB integrity, FK, sürüm doğrulaması).
- [ ] **K1 & FK:** Şirket izolasyonu tam korunur, `PRAGMA foreign_key_check = 0`, test kalıntısı = 0.
- [ ] **Regresyon:** 29 eski dosya + yeni `test_d015_toplu_yardim_sistem.py` = **30 dosya**, 0 başarısız (hedef ~643+ kontrol).

---

## İSTENEN KANITLAR & TESLİM
- ZIP (kod + demo seed'li DB + testler) + MD5/SHA256
- `test_d015_toplu_yardim_sistem.py` test çıktısı
- Tam regresyon çıktısı (30 dosya, tam sayı)
- Değişen/yeni dosya listesi + `kanitlar/v1.46.0/`
