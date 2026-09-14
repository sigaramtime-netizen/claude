# D011 — Tanım Verileri Yönetimi + Satır Bazlı KDV + Hızlı Barkod + Çoklu Döviz + Cari Tahsilat/Ödeme

> **Durum:** GM1 (Claude) direktifi — 2026-09-14.
> Kapsam bölme kararı (D011 tek paket mi, D011+D012 mi) GM1'in köprü seçeneklerini
> değerlendirmesiyle kesinleşecek (bkz. "Danışma noktası").
> **ÖNCELİK:** Yüksek (çok sayıda gerçek kullanıcı şikâyeti birikmiş)

---

## Kaynak ve kod analizi

Kullanıcının canlı kullanım şikâyetleri + ekran görüntüsü (v1.41.0 build doğrulandı:
`+ Marka` var — D007 — ama `+ Kategori` yok). GM1 kodda kontrol etti:

| # | İddia | Gerçek durum |
|---|-------|--------------|
| 1 | Kategori/Para Birimi ekleme-silme yok | ✅ gerçek boşluk — `/api/marka/ekle` var, kategori/para birimi için yok |
| 2 | KDV dahil/hariç satır bazlı olsun | Kısmen — belge geneli tek toggle (`kdv_dahil` tek değer), satır bazlı değil |
| 3 | Barkod/stok kodu alanı | Kısmen — typeahead barkod da kabul ediyor ("ad/kod/barkod") ama POS'taki hızlı barkod-oku-Enter-ekle yok |
| 4 | Çoklu döviz (TL+USD aynı anda) | Altyapı var (`para_birimi`/`doviz_kur`) ama eş zamanlı çift gösterim + ekstrede döviz ayrıştırma yok |
| 5 | Cari tahsilat/ödeme ekranı yok | Kısmen — Kasa/Banka'da `cari_id` bağlanabiliyor ama tek "Tahsilat Al / Ödeme Yap" ekranı yok; POS ödeme-dağılım mantığı tekrarlanmamış |

---

## D011-A: Kategori & Para Birimi Tanımları

- Marka'daki desenin birebir aynısı: `/api/kategori/ekle`, `/api/para-birimi/ekle`
  (POST, inline).
- Ayrıca Ayarlar altında (Marka gibi) bir "Tanımlar" alt-ekranı: liste + **pasifleştir**
  (silme DEĞİL — K32 deseniyle tutarlı; kullanılan bir kategori/para birimi silinemez,
  yalnız pasifleştirilir).

## D011-B: Satır Bazlı KDV Dahil/Hariç

- Her kalem satırına opsiyonel `kdv_dahil` override; boşsa belge geneli varsayılan uygulanır.
- Kapsam: **irsaliye, fatura, teklif, sipariş** kalem satırları.
- Gerekçe (kullanıcı): "bazı kalemler faturasız/istisna olabilir" — karışık KDV muamelesi
  tek belgede mümkün olmalı.

## D011-C: Hızlı Barkod Girişi

- POS'taki `barkod_bul()` + "Enter'da ekle" desenini irsaliye/fatura/teklif formlarına ekle
  (ayrı, küçük bir barkod input'u; sepet mantığına benzer tek-satır-ekle).
- Mevcut typeahead'e DOKUNMA — bu ona ek bir hızlı-yol.

## D011-D: Çoklu Döviz (eşzamanlı gösterim)

- Belge para birimi seçimi (TRY/USD/EUR) zaten var; eklenecek: belge kaydedilirken **kur
  sabitlenir** (mevcut K2 deseni), ama ekranda hem döviz hem TL karşılığı **yan yana
  gösterilir** (yalnız arka planda değil, arayüzde de).
- Cari ekstre: para birimi filtresi (Tümü/TRY/USD/EUR), her döviz cinsinden ayrı alt toplam.
- **Kapsam sınırı:** yalnızca TRY/USD/EUR (mevcut `TCMB_KODLARI` ile aynı 3 birim).
  ⚠️ Köprü notu: sistemde GBP de var (`PARA_BIRIMLERI=[TRY,USD,EUR,GBP]`, `TCMB_KODLARI=
  (USD,EUR,GBP)`) — GBP dahil/hariç GM1 netleştirmeli.

## D011-E: Cari Tahsilat / Ödeme Ekranı

- Yeni tek ekran: `/cari/<id>/tahsilat` (alacak tahsili) ve `/cari/<id>/odeme` (tedarikçi
  ödemesi) — POS'un ödeme-dağılım desenini (Nakit/Kart/Havale/Çek-Senet, bölünebilir)
  tekrar kullanır.
- Arka planda mevcut `kasa_hareket`/`banka_hareket`/`cek_senet` + cari hareket + yevmiye
  üretimini çağırır — **yeni tablo gerekmez**, yalnızca birleştirici ekran + rota.
- Kredi kartı seçilirse POS'taki terminal/komisyon mantığı yeniden kullanılır.

---

## KABUL KRİTERLERİ (özet)

- **D011-A:** kategori/para birimi inline eklenebilir, pasifleştirilebilir, kullanımdaysa silinemez.
- **D011-B:** aynı belgede bir satır KDV dahil, diğeri hariç girilebilir; toplamlar doğru.
- **D011-C:** barkod input'una okutma/yazma + Enter → satır otomatik eklenir.
- **D011-D:** USD faturada hem USD hem TL tutar görünür; cari ekstre döviz filtresiyle doğru alt toplamlar.
- **D011-E:** tahsilat/ödeme ekranı doğru kasa/banka/çek + cari hareket + yevmiye üretir
  (mevcut fonksiyonlar çağrılır, kod tekrarı yok).
- Tam regresyon (25 dosya) + yeni testler yeşil.
- Zip + MD5/SHA256 (GM1'in bağımsız çalıştırması için).

---

## DANIŞMA NOKTASI (GM1 → köprü)

D011-D ve D011-E kapsam olarak büyük — tek pakette mi (D011), yoksa D011 (A+B+C,
küçük/hızlı) ve D012 (D+E, büyük/döviz+tahsilat) olarak ikiye mi bölünsün?
→ Köprü 2-3 seçenekle dönecek; karar GM1'in.
