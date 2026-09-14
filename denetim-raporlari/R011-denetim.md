# R011 — D011 Denetim Raporu: Tanım Verileri (Kategori & Cari Grup) + Hızlı Barkod (v1.42.0)

- **Görev:** D011 — Tanım Verileri (Kategori & Cari Grup inline ekleme) + Hızlı Barkod Girişi
- **Sürüm:** v1.41.0 → **v1.42.0**
- **Denetleyen:** GM1 (Claude)
- **Tarih:** 2026-09-14
- **Coder commit:** `c97202b` (kod: `bcd964a`)

---

## SONUÇ: ONAYLANDI ✅ — MÜHÜR v1.42.0

---

## GM1 gerekçeleri

1. **Kategori + Cari Grup inline ekleme çalışıyor, K32 desenine uygun (silme değil
   pasifleştirme).** `/api/kategori/ekle`, `/api/cari_grup/ekle` rotaları kodda bulundu;
   `/ayarlar/tanimlar` ekranından pasifleştirme yapılıyor; pasif kayıt formlarda seçilemiyor
   (test madde 10-13).
2. **Hızlı barkod girişi 3 formda da (irsaliye/fatura/teklif) gerçekten var**, aynı
   `id="barkod-hizli"` deseniyle — kodda tek tek kontrol edildi (test madde 15-19).
3. **K1 şirket izolasyonu korunmuş:** aynı isimli kategori farklı şirketlerde ayrı kayıt
   üretiyor (test madde 20).
4. **Testler bizzat çalıştırıldı — iki kez, temiz kopyalarla:**
   - İlk çalıştırmada `test_coklu_sirket.py`'de bir bütünlük hatası ve
     `test_d010_yedekleme.py`'de bir çökme görüldü; ancak bunlar **taze, hiç dokunulmamış
     bir zip kopyasında tekrarlanınca ikisi de temiz geçti** — sorun D011 kodunda değil,
     GM1'in kendi ardışık test çalıştırma/sunucu yönetimindeydi. (Şeffaflık notu;
     coder'a haksız regresyon suçlaması yöneltilmedi.)
   - Nihai temiz sonuç: **582/582** — R011 iddiasıyla birebir.
5. **İş mantığına dokunulmamış** — mevcut tüm modüllerin (F1-F6, D007-D010, B1-B3, POS,
   CRM, Bakım) testleri sıfır hatayla geçti.

---

## GM1 ek notu (sıradaki paket)

D012 (satır bazlı KDV + çoklu döviz + Para Birimi/Birim'in tabloya taşınması) direktifi
önceki turda netleştirildi — **coder D012'ye geçebilir.**

---

## Köprü kaydı

- Köprü bağımsız doğrulaması: `test_d011_tanimlar_barkod.py` 21/21; tam regresyon 26 dosya
  0 başarısız — GM1'in 582/582 sonucuyla uyumlu.
- **Sansür bu pakette coder tarafından yapıldı** (D009/D010'daki tekrarlayan kusur giderildi):
  teslim zip'inde gerçek kişi adı → MÜŞTERİ-A / D007-MUSTERIA (köprü D009 deseniyle
  diff-birebir doğruladı; sansürlü test_d007 31/31 geçer). Public'e giden R011 + zip-hash
  metinlerinde kalan 2 ad kalıntısı köprü tarafından "gerçek kişi adı" ifadesine çevrildi.
- Public GM1 paketi: `paketler/BRN-Teknoloji-ERP-v1.42.0-D011-GM1-denetim.zip`
  (MD5 `1624062a26ac9a5ba7791709072f18ab`) + `kod-inceleme/D011/` (12 dosya) raw 200.
