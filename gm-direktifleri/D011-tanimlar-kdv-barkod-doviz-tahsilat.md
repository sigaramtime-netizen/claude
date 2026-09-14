# D011 — Tanım Verileri Yönetimi + Satır Bazlı KDV + Hızlı Barkod + Çoklu Döviz + Cari Tahsilat/Ödeme

> **Durum:** GM1 (Claude) direktifi + **KAPSAM BÖLME KARARI** — 2026-09-14, **Seçenek 3 (3 paket, tematik)** + **KRAL revizyonu:**
> - **D011 = A + C** (Kategori & Cari Grup tanımları + hızlı barkod) — düşük risk, hızlı
> - **D012 = B + D + Para Birimi/Birim tablo geçişi** (satır KDV + çoklu döviz + sabit liste→tablo) — aynı kalem/toplam yüzeyi, birlikte test
> - **D013 = E** (cari tahsilat/ödeme ekranı) — bağımsız
> Sıralama: **D011 → D012 → D013**; her biri kendi zip + testleriyle ayrı ayrı GM1'e gelir,
> GM1 her birini bağımsız çalıştırıp doğrular.
> Coder'a iletilecek D011 paketi: `gm-direktifleri/D011-tanimlar-hizli-barkod.md`
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

## D011-A: Kategori & Cari Grup Tanımları

- Marka'daki desenin birebir aynısı: `/api/kategori/ekle`, `/api/cari_grup/ekle`
  (POST, inline).
- Ayrıca Ayarlar altında (Marka gibi) bir "Tanımlar" alt-ekranı: liste + **pasifleştir**
  (silme DEĞİL — K32 deseniyle tutarlı; kullanılan bir kategori/cari grup silinemez,
  yalnız pasifleştirilir).
- ⚠️ **KRAL revizyonu:** Para Birimi bu paketten çıkarıldı → **D012** (sabit liste → tablo
  geçişi, çoklu dövizle birlikte). Cari Grup eklendi (tablo hazır + `/cari/gruplar` ekranı
  mevcut; yalnızca inline "＋ Grup" butonu eksik).

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

## DANIŞMA NOKTASI (CEVAPLANDI — 2026-09-14)

GM1 → köprü sorusu: D011-D/E büyük; tek paket mi, ikiye mi bölünsün?
→ Köprü 3 seçenek sundu; GM1 **Seçenek 3'ü seçti** (3 paket, tematik). KRAL revizyonu:
Para Birimi D011-A'dan D012'ye taşındı (sabit liste → tablo geçişi pahalı); Cari Grup
D011-A'ya eklendi (tablo hazır). Birim de D012'de Para Birimi ile birlikte tabloya taşınır.
