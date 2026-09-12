# GM1 DENETİM GÖREVİ — D008 (Belgeleme Tamamlama + Bakım Cihaz Seçici)

> Sen bu projenin GM1'sin (Claude). Aşağıdaki D008 coder raporunu DENETLE.
> Direktif (D008) ile yapılanı (R008 + kod + test) karşılaştır.
> Çıktını şu formatta ver: **SONUÇ: ONAYLANDI / REVIZYON** + madde madde gerekçe
> (REVİZYON ise coder'ın düzelteceği maddeleri numaralı listele).

==================================================================
1) DİREKTİF (D008)
==================================================================
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

==================================================================
2) CODER RAPORU (R008)
==================================================================
# R008 — Belgeleme Tamamlama + Bakım Cihaz Seçici (v1.39.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D008 (CHANGELOG v1.34→v1.39 geriye dönük + 5 faz özeti + bakim/detay typeahead)
- **Sürüm:** 1.39.0 (değişmedi — saf belgeleme + tek form düzeltmesi)
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-12
- **Commit:** `aa339b1 [CODER] D008 belgeleme tamamlama + bakim cihaz seçici typeahead (v1.39.0)`

---

## 1. Yapılan İş

1. **`kod/CHANGELOG.md`** — v1.34.0'dan v1.39.0'a kadar **6 sürüm başlığı** geriye dönük
   eklendi (Keep a Changelog formatı, Eklenen/Değişen/Testler bölümleri, önceki girdilerle
   aynı desen): v1.34.0 (F4), v1.35.0 (F5-A), v1.36.0 (F5-B), v1.37.0 (F5-C), v1.38.0 (F6),
   v1.39.0 (D007). F4 için `docs/F4-edonusum-ozet.md` zaten var → mükerrer yazılmadı.
2. **5 yeni `docs/*-ozet.md`** (F1/F2 ile aynı 4 bölümlü yapı: Veri Modeli → Ekran Listesi →
   Örnek Test Senaryosu → Değişen Dosyalar + Kanıtlar):
   - `docs/F5a-finansal-analiz-ozet.md` (YENİ)
   - `docs/F5b-demirbas-ozet.md` (YENİ)
   - `docs/F5c-beyanname-ozet.md` (YENİ)
   - `docs/F6-cila-ozet.md` (mevcut dosya, 4 bölümlü F1/F2 şablonuna göre yeniden yazıldı)
   - `docs/D007-kullanici-bildirimleri-ozet.md` (YENİ)
   İçerikler **gerçek kod/test davranışından** derlendi (test dosyalarındaki senaryolar +
   `SURUM` geçmişi).
3. **`kod/templates/bakim/detay.html`** — cihaz ekleme formundaki düz sayısal
   `<input type="number" name="stok_id">` kaldırıldı; ortak F3 typeahead bileşenine çevrildi
   (`<input type="hidden" name="stok_id" id="stok-id">` + `<div class="typeahead"
   data-tip="stok" data-target="stok-id">`). Backend `POST /bakim/sozlesme/<id>/cihaz`
   değişmedi (stok_id hidden input'tan okunur); "Cihaz (stok) veya açıklama girin" kuralı korundu.
4. **`kod/test_d007_iyilestirmeler.py`** — 18 numaralı typeahead-genelleme kontrolü
   `bakim/detay.html`'i kapsayacak şekilde genişletildi + 18b kontrolü eklendi
   (sayısal stok_id inputu yok + data-tip=stok var). Kontrol sayısı 30 → **31**.

## 2. Direktife Uygunluk (kontrol listesi)

| Kabul kriteri | Durum |
|---|---|
| CHANGELOG'da v1.34→v1.39 arası 6 ayrı sürüm başlığı, hiçbiri boş değil | ✅ |
| Tarihler `config.SURUM_TARIHI` geçmişiyle tutarlı (hepsi 2026-09-11; F5-C/F6/D007 12'sinde ama SURUM_TARIHI sabit kaldığı için 09-11 kullanıldı) | ✅ |
| 5 yeni docs/*-ozet.md, önceki F1/F2 ile aynı 4 bölümlü yapıda | ✅ |
| bakim/detay.html'de `<input type="number" name="stok_id">` kalmadı | ✅ |
| İş mantığı değişmedi (saf dokümantasyon + form arayüzü) | ✅ |
| Tam regresyon 23 dosya, 0 başarısız | ✅ 527/527 |
| test_d007 typeahead kontrolleri bakim/detay'ı kapsıyor | ✅ |

## 3. Test Sonuçları

```
python3 test_d007_iyilestirmeler.py  → 31/31 (18/18b güncellendi)
Tam regresyon (23 dosya)            → 527/527, 0 başarısız
pytest                              → no tests ran (proje pytest kullanmaz)
PRAGMA foreign_key_check            → 0 satır
```

Regresyon dökümü: alinan_teklif 23, bakim 29, belge_sayac 9, coklu_sirket 16, crm 25,
**d007 31**, eksik_teslimat 21, f1_mali 25, f2_kdv 34, f3_arama 30, f4_edonusum 22,
f5a 18, f5b 18, f5c 18, f6 18, izolasyon 22, izolasyon_mali 19, manuel_satir 28,
pos 41, satin_alma 23, silme 23, sirket_yonetimi 19, teklif_siparis_manuel 15 = **527**.

## 4. Teslim (ZİPSİZ PROTOKOL — D008 direktifi "zip" dese de kalıcı zipsiz kuralı uygulandı)

- `kanitlar/v1.39.0/D008-tam-regresyon.txt` — 23 dosya, 527/527
- `kanitlar/v1.39.0/D008-test-ciktisi.txt` — test_d007 31/31 (tek geçiş)
- `kanitlar/v1.39.0/D008-degisen-dosyalar.txt` — CHANGELOG + 5 özet + bakim/detay + test_d007 + DURUM (tam içerik)
- `kanitlar/v1.39.0/D008-ozet-hash.txt` — zaman damgası + sha256
- `coder-raporlari/R008-belgeleme-tamamlama.md` — bu rapor

## 5. Notlar

- `docs/F6-cila-ozet.md` zaten mevcuttu ama 6 bölümlü farklı bir şablondaydı; D008'in
  "önceki F1/F2/F3 ile birebir aynı 4 bölümlü yapı" kriteri için yeniden yazıldı.
- Bakım cihaz seçici typeahead'e çevrilirken backend'e dokunulmadı; `test_bakim.py` 29/29
  geçmeye devam etti (regresyon garantisi).

==================================================================
3) BAĞIMSIZ DOĞRULAMA NOTU (KÖPRÜ = Arena danışmanı, TARAFSIZ)
==================================================================
Köprü (Arena) coder'ın iddialarını YERELDE bağımsız çalıştırarak doğruladı:

  - test_d007_iyilestirmeler.py  →  31/31 GEÇTİ (canlı HTTP sunucuda, gerçek e2e)
  - Tam regresyon (23 dosya)     →  527/527, 0 başarısız (her dosya tek tek çalıştırıldı)
  - CHANGELOG.md: v1.34.0..v1.39.0 arası 6 başlık mevcut (tarih 2026-09-11)
  - 5 yeni docs/*-ozet.md mevcut (F5a/F5b/F5c/F6/D007)
  - bakim/detay.html: düz <input type=number name=stok_id> KALDIRILMIŞ;
    <input type=hidden name=stok_id id=stok-id> + typeahead data-tip=stok VAR

NOT: Bu doğrulama karar DEĞİL, sadece tarafsız teknik kanıttır.
Karar (ONAY/REVİZYON) SENİNDİR (GM1).

==================================================================
4) KANIT DOSYALARI (private repoda)
==================================================================
kanitlar/v1.39.0/D008-tam-regresyon.txt   — 23 dosya, 527/527
kanitlar/v1.39.0/D008-test-ciktisi.txt    — test_d007 31/31
kanitlar/v1.39.0/D008-degisen-dosyalar.txt— CHANGELOG + 5 özet + bakim/detay + test_d007 (tam içerik)
kanitlar/v1.39.0/D008-ozet-hash.txt       — sha256

==================================================================
NOT: Kod zip'i (güncel, D008 değişiklikleri dahil) ayrıca verilecek.
==================================================================
