# R007 DENETİM RAPORU — D007 (v1.39.0)

- **Denetleyen:** GM1 (Claude)
- **Tarih:** 2026-09-12
- **İlgili görev:** D007 — Kullanıcı Bildirimleri & İyileştirmeler (10 madde)
- **Yöntem:** Kaynak kod zip'i + demo seed'li DB + testler GM1'e verildi; GM1 testleri
  bağımsız çalıştırıp kodu grep'lerle çapraz doğruladı.

---

## SONUÇ: ONAYLANDI ✅

### Gerekçeler (GM1, aynen)

1. **Testler bağımsız olarak çalıştırıldı, hepsi geçti.** `test_d007_iyilestirmeler.py` → **30/30**.
   Diğer 22 test dosyası da tek tek çalıştırıldı: hepsi 0 hatayla geçti, toplam **526/526**
   — brifingde iddia edilen sayıyla birebir aynı.
2. **10 maddenin her biri kodda doğrulandı** (test çıktısı + grep çapraz kontrol):
   - Madde 1 (KDV dahil/hariç select): fatura/irsaliye/teklif/sipariş/POS'ta mevcut, net tutar doğru.
   - Madde 2 (marka inline ekleme, KRİTİK): `stok.py:468` → `POST /api/marka/ekle` rotası var, testte 200 + id dönüyor.
   - Madde 3 (stok kart ek alanlar): kayıt+güncellemede korunuyor.
   - Madde 4 (typeahead TTEC filtre bugu): `q=TTEC` artık tam 1 kayıt dönüyor.
   - Madde 5 (irsaliye döviz USD→TL): 100 USD × kur 30 = 3.000 TL doğru çevrilmiş, yevmiye dengeli.
   - Madde 6 (eksi stok izni): `irsaliye.py:335`'te açıkça "D007 madde 6" referansı var; stok yetersizken onay bloke etmiyor.
   - Madde 7-10 (kartoteks typeahead, çoklu irsaliye ekstre, Sil butonu, typeahead genelleme): hepsi testte doğrulanmış; `<select name="cari_id/stok_id">` kalıntısı sıfır.
3. **Regresyon riski yok:** F1 (mali etki), F5b/F5c, F6, K1 (şirket izolasyonu) hepsi geçti — D007 hiçbir eski modülü bozmamış.
4. **Bütünlük temiz:** `PRAGMA foreign_key_check` boş, test kalıntısı (`D007TEST`) yok.

### Ek notlar / riskler (D007'yi bloke etmez — takip edilmeli)

- **Belgeleme boşluğu:** `CHANGELOG.md` en son v1.33.0 (F3)'te duruyor; `config.py` 1.39.0 diyor.
  F5-A/F5-B/F5-C/F6/D007 için ayrı "özet.md" dosyaları yok (F1–F4'te vardı). Kod ve testler
  mevcut ve geçiyor; bu iş eksik değil ama **kayıt disiplini** bozulmuş → coder'dan geriye
  dönük CHANGELOG + faz özet dokümanları tamamlanması istenmeli (**D008 adayı**).
- Küçük gözlem: `templates/bakim/detay.html` içinde cihaz eklerken `stok_id` düz sayısal
  `<input>` (select değil). D007 kapsamı dışında; ileride typeahead'e çevrilebilir.

---

**Karar:** D007 MÜHÜR — v1.39.0 kabul edildi. Sıradaki: D008 (belgeleme disiplini).
