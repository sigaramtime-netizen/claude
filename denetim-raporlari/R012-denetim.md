# R012 DENETİM RAPORU — ONAYLANDI (v1.43.0 MÜHÜR)

**Tarih:** 2026-09-15  
**Denetmen:** GM1 (Genel Müdür 1 — Claude)  
**Görev:** D012 — Satır Bazlı KDV + Çoklu Döviz + Para Birimi & Birim DB Tablo Geçişi  
**Önceki Sürüm:** v1.42.0 (D011 MÜHÜRLÜ)  
**Yeni Sürüm:** v1.43.0  
**Sonuç:** **SONUÇ: ONAYLANDI** (v1.43.0 MÜHÜR)

---

## 1. GM1 DENETİM GEREKÇELERİ (BİREBİR ALINTI)

1. **Satır bazlı KDV (B) doğru çalışıyor:** `irsaliye.py`'de `_satirlar_from_form`: her satırın kendi `k_kdv_dahil[]` değeri var, boşsa belge geneli varsayılana düşüyor. Testte (madde 2-4) karışık bir belgede (100 dahil + 100 hariç) toplamların doğru çıktığını (`ara=200, kdv=40, genel=240`) gördüm.
2. **Çoklu döviz (D) eşzamanlı gösterim gerçek:** `irsaliye/detay.html`'de *"Belge dövizi: USD · Kur: 1 USD = X TL · TL karşılığı ≈ ..."* satırını kodda buldum. Cari ekstrede `pb` (para birimi) filtre select'i + döviz alt toplamları mevcut.
3. **Para Birimi & Birim artık gerçek DB tabloları (X):** `sqlite_master`'da `para_birimi` ve `birim` tablolarını doğrudan sorguladım — var. `/api/birim/ekle`, `/api/para-birimi/ekle` inline rotaları çalışıyor. Güzel bir ek koruma da gördüm: TRY pasifleştirilemiyor (madde 14) — bunu direktifte istemedim ama mantıklı bir savunma, temel para birimi kilitli kalmalı.
4. **K1 izolasyonu ve K32 deseni (silme yerine pasifleştirme) korunmuş:** hem birim/para birimi hem kategori/cari grup için.
5. **Testler iki kez, temiz DB ile, bizzat çalıştırıldı:** `test_d012_kdv_doviz_master.py` → 21/21. 26 eski dosyayı 3 partide (12+12+3, her partide temiz DB kopyası) çalıştırdım, hepsi 0 hatayla geçti. Toplam 603/603 — hem R012'nin iddiasıyla hem kendi hesabımla birebir örtüşüyor.
6. **FK/bütünlük temiz, test kalıntısı yok.**

---

## 2. KÖPRÜ NOTU

D012 ile kullanıcının orijinal 9 maddelik şikayet listesi (D011+D012) tamamen başarıyla kapatılmıştır.  
GM1 tarafından bir sonraki görev olarak **D013 — Cari Tahsilat / Ödeme Ekranı** kesin direktifi verilmiştir.

Sürüm **v1.43.0** resmen mühürlenmiştir.
