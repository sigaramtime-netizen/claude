# D008 — Belgeleme Tamamlama (CHANGELOG + Faz Özetleri) + Bakım Sözleşmesi Cihaz Seçici Düzeltmesi

- **Görev ID:** D008
- **Durum:** BEKLEMEDE (Coder bekleniyor)
- **Öncelik:** Orta
- **Kaynak:** GM1 (Claude) — D007 denetimindeki takip notlarından türetildi
- **Tarih:** 2026-09-12

---

## GEREKSİNİMLER

1. **CHANGELOG.md'yi** v1.33.0'dan (mevcut son kayıt) v1.39.0'a kadar geriye dönük tamamla.
   Her sürüm için ayrı başlık (`## v1.3X.0 — <tarih>`) altında, önceki girdilerle aynı formatta
   (Eklenen/Değişen/Düzeltilen bölümleri):
   - v1.34.0 — F4: e-Dönüşüm Mock/Sandbox
   - v1.35.0 — F5-A: Finansal Analiz & Dashboard (bütçe + SVG kartları)
   - v1.36.0 — F5-B: Demirbaş & Amortisman Raporlama
   - v1.37.0 — F5-C: Beyanname Hazırlık (KDV devreden + geçici vergi + nakit esaslı)
   - v1.38.0 — F6: Son Cila (bildirim API, yetki CSV, ortak yazdırma, şube özeti)
   - v1.39.0 — D007: Kullanıcı Bildirimleri İyileştirmeleri (10 madde)
   - Not: F4 için zaten `docs/F4-edonusum-ozet.md` var; CHANGELOG'a yalnızca eksik girdiyi ekle, mükerrer yazma.

2. **Eksik faz özet dokümanlarını**, önceki fazlarla (`docs/F1-mali-etki-ozet.md`,
   `docs/F2-kdv-dahil-ozet.md`, `docs/F3-arama-ozet.md` gibi) aynı şablonla oluştur:
   - `docs/F5a-finansal-analiz-ozet.md`
   - `docs/F5b-demirbas-ozet.md`
   - `docs/F5c-beyanname-ozet.md`
   - `docs/F6-cila-ozet.md`
   - `docs/D007-kullanici-bildirimleri-ozet.md`
   - Her biri: veri modeli özeti (varsa yeni tablo/alan), ekran listesi, örnek test senaryosu,
     doğrulama kanıtı (ilgili test sonuçları) — bölüm başlıkları önceki F1/F2/F3 `*-ozet.md`
     dosyalarındaki 4 bölümlü yapıyla birebir aynı olsun.

3. **`templates/bakim/detay.html`** içindeki cihaz ekleme formunda düz sayısal
   `<input name="stok_id">` alanını, sistemin geri kalanında kullanılan ortak typeahead
   bileşenine (F3 deseni, `/api/ara?tip=stok`) çevir — kullanıcı stok kodunu/adını yazarak
   arayabilsin, ham ID girmesin.

## KABUL KRİTERLERİ

- [ ] CHANGELOG.md'de v1.34.0'dan v1.39.0'a kadar 6 ayrı sürüm başlığı var, hiçbiri boş değil,
      tarihler `config.SURUM_TARIHI` geçmişiyle tutarlı.
- [ ] 5 yeni `docs/*-ozet.md` dosyası eklendi, her biri önceki fazlarla aynı 4 bölümlü yapıda
      (mevcut dosyalardan biriyle yan yana karşılaştırıldığında yapısal fark yok).
- [ ] `templates/bakim/detay.html`'de artık `<select>`/typeahead ile stok seçiliyor;
      düz `<input type="number" name="stok_id">` kalmadı.
- [ ] Bu 3 değişiklik hiçbir iş mantığını değiştirmiyor — yalnızca dokümantasyon + bir formun
      arayüzü. Tam regresyon (23 test dosyası) hâlâ 526/526. Yeni test dosyası gerekmiyor,
      ama `test_d007_iyilestirmeler.py`'nin 17-18 numaralı typeahead-genelleme kontrolleri
      artık `bakim/detay.html`'i de kapsayacak şekilde güncellenip tekrar koşturulmalı.

## İSTENEN KANITLAR

- [ ] Güncellenmiş CHANGELOG.md ve 5 yeni `docs/*-ozet.md` dosyasının tam içeriği (zip içinde).
- [ ] `templates/bakim/detay.html`'in değişen kısmının diff'i veya tam içeriği.
- [ ] Tam regresyon çıktısı (23 dosya, 526/526 + varsa güncellenen typeahead kontrolü).
- [ ] Zip + MD5/SHA256 (önceki paketlerdeki gibi).

## TEKNİK NOTLAR

- Bu paket saf belgeleme + tek form düzeltmesi; veri modeli/migration değişikliği YOK,
  K1/K8/K13 gibi mimari kurallara dokunmuyor.
- Faz özet dokümanlarını yazarken **gerçek kod davranışını** (test dosyalarındaki senaryoları)
  kaynak al — GM1 brifingindeki genel açıklamaları değil.
