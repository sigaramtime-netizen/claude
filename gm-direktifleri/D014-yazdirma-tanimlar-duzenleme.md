# D014 — KAPSAMLI YAZDIRMA / ÇIKTI TAMAMLAMA + TANIM VERİLERİ DÜZENLEME DİREKTİFİ

**Tarih:** 2026-09-15  
**Veren:** GM1 (Genel Müdür 1 — Claude)  
**Öncelik:** Yüksek  
**Versiyon Hedefi:** v1.44.0 → v1.45.0  

---

## GEREKÇE
A paketinden sonra eklenen 10+ modülün (B1-B3, POS, Bakım, CRM, Servis, Demirbaş, Transfer, Cari Tahsilat/Ödeme) hiçbirinde yazdırma/çıktı yok — yalnızca orijinal 4 belge (teklif/sipariş/irsaliye/fatura) + kasa fişi + kartoteks raporları + çek/senet kapsanmış. Ayrıca D011/D012'de eklenen tanım verilerinde (Kategori/Para Birimi/Birim/Cari Grup/Marka) yalnızca Ekle var, Düzenle hiç yok ve Marka'da Pasifleştir de eksik — kullanıcı bir yazım hatasını düzeltemiyor.

---

## BÖLÜM A — YAZDIRMA / ÇIKTI TAMAMLAMA

### A1 — Karşı tarafa fiziksel teslim edilen belgeler (yeni, küçük şablonlar)
1. **Cari Tahsilat/Ödeme Makbuzu:** Tarih, cari, tutar (+ TL karşılığı döviz ise), ödeme şekli kırılımı (Nakit/Kart/Havale/Çek), işlemi yapan kullanıcı, imza alanı.
2. **Servis Kaydı Fişi:** Hem müşteri teslim/teslim-alma fişi hem teknisyene iş emri olarak kullanılabilir tek şablon (`teknisyen_id`, `ariza`, `aksesuar`, `garanti_kapsami`, `iscilik_ucreti` alanları).
3. **Bakım Sözleşmesi:** Sözleşme metni + kapsanan cihaz listesi.
4. **Banka Hareket Fişi:** `kasa/fis.html` ile birebir aynı desen.

### A2 — Dahili raporlar + arşiv çıktıları (mevcut `core.yazdir_belge()` yeniden kullanılır — kalemli olanlarda)
5. **CRM Raporu (`/crm/rapor`):** Mevcut ekrana yazdır butonu (yönetici/iş ortağı özeti).
6. **Depo Transferi:** `yazdir_belge()`'nin hafif varyantı (fiyat/KDV sütunu yok, yalnızca ürün+miktar+kaynak/hedef depo — sevk fişi mantığı).
7. **Demirbaş Listesi:** Mevcut CSV'nin (`/demirbas/amortisman/csv`) yanına düzgün biçimli PDF/yazdır (muhasebeciye verilebilir, amortisman durumu dahil).
8. **Satın Alma Talebi, Alınan Teklif:** `yazdir_belge()` yeniden kullanılır (kalemli, aynı şekil).
9. **Teklif:** Mevcut `yazdir_belge()` ortak mekanizmasına taşınır (şu an tek başına eski ayrı şablonunu kullanıyor, F6'daki konsolidasyonla tutarsız — küçük temizlik).

### A3 — Rapor ekranlarına yazdır butonu (ekran zaten var)
10. **Eksik Teslimat Raporu**, **Satın Alma Raporu**.

**Kapsam dışı (gerekçeli):**
- **POS satışı:** Zaten Onaylı Satış Faturası üretiyor, `fatura/yazdir` yeterli; POS ekranına yalnızca kısayol linki eklenir.
- **Tekil CRM aktivite kaydı:** Somut ihtiyaç yok.

---

## BÖLÜM B — TANIM VERİLERİ: DÜZENLEME + MARKA PASİFLEŞTİRME

1. **5 Tanım Tipi:** Kategori, Para Birimi, Birim, Cari Grup, Marka — beşi için de `/ayarlar/tanimlar/<tip>/<id>/duzenle` rotası (isim/kod düzeltme) + `/ayarlar/tanimlar` ekranında "Düzenle" butonu.
2. **Marka Pasifleştirme:** Marka'ya pasifleştirme eklenir — diğer dördüyle aynı seviyeye getirilir.
3. **Koruma Kuralı:** Görünen ad (`ad` alanı) her zaman düzenlenebilir; tanımlayıcı alanlar (`kod`/`tip`) kullanımdaysa değiştirilemez (K1/K13 tutarlılığı korunur).

---

## KABUL KRİTERLERİ

- [ ] A1'deki 4 belge türü: her biri kendi `/<modül>/<id>/yazdir` rotası + Wolvox teması (`#1e4e79`, A paketiyle birebir).
- [ ] A2'deki kalemli olanlar (6, 8) `yazdir_belge()` kullanır — yeni şablon yazılmaz, yalnızca `tip_label` ile ayrıştırılır. Teklif (9) da bu mekanizmaya taşınır.
- [ ] A2/A3'teki rapor ekranlarına "Yazdır" butonu + print-CSS.
- [ ] B'deki 5 tanım tipinde artık Ekle + Düzenle + Pasifleştir üçlüsü eksiksiz.
- [ ] Marka artık pasifleştirilebiliyor.
- [ ] Kullanımdaki bir tanım kaydının adı düzenlenebiliyor; kod/tip değişikliği kullanımdaysa engelleniyor (test: kullanılan bir para biriminin kodu değiştirilmeye çalışılınca reddedilir).
- [ ] Her belge detay sayfasına (varsa) bir "Yazdır" butonu eklenir.
- [ ] Hiçbir mali/iş mantığı değişmiyor — yalnızca görüntüleme + tanım-veri CRUD tamamlama katmanı.
- [ ] Tam regresyon (28 eski dosya + D014) tam yeşil.
- [ ] K1 şirket izolasyonu korunuyor.

---

## İSTENEN KANITLAR & TESLİM
- ZIP + MD5/SHA256 (doğrudan sohbete yükleme).
- `test_d014_yazdirma_tanimlar.py` (en az: 10 yazdırma rotasının her biri 200 + doğru veri; tanım düzenleme (5 tip) başarı + kullanımdaki alan koruması; Marka pasifleştirme; K1 izolasyonu; FK/kalıntı temizliği).
- Tam regresyon çıktısı, tam sayı (29 dosya, 0 başarısız).
- Değişen/yeni dosya listesi.

---

## TEKNİK NOTLAR
Coder isterse ikiye bölüp ayrı zip'te teslim edebilir (`D014-A` / `D014-B`), ama tek pakette de kabul edilir — büyüklüğüne göre karar coder'da, danışmasına gerek yok (ikisi de düşük riskli, iş mantığına dokunmuyor).
