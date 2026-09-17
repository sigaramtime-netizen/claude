# R020 — İade Ailesi: 4 Fiş Tipi + Kaynak Dönüşümü (v1.51.0) — Coder Raporu

**Tarih:** 2026-09-16 · **Direktif:** `gm-direktifleri/D020-iade-ailesi.md`
(KÖPRÜ, F1) · **Sürüm:** v1.50.0 → v1.51.0

## Şema (`db.py`)

- `fatura.tip` → `('Satis','Alis','SatisIade','AlisIade')`;
  `irsaliye.tip` → `('Satis','Alis','Transfer','SatisIade','AlisIade')`;
  `irsaliye.durum` → `+ 'Reddedildi'`.
- Yeni kolonlar: `fatura.kaynak_fatura_id`, `fatura.depo_id` (iade stok bacağı
  için), `irsaliye.kaynak_irsaliye_id`, `fatura_kalem.kaynak_kalem_id`,
  `irsaliye_kalem.kaynak_kalem_id`.
- Migrasyon: D019 rebuild deseni `_check_rebuild` yardımcısına genellendi
  (tırnaklı/tırnaksız/IF NOT EXISTS + çift-replace koruması); D020 bloğu
  `_migrate_d020(conn)` olarak ayrıldı (testten doğrudan çağrılabilir).
  Fatura + irsaliye rebuild'leri bağımsız ve idempotent; trigger + index ihya
  `_SIRKET_INDEXLER` üzerinden.

## Dönüşüm akışı (`fatura.py`, `irsaliye.py` + 4 şablon)

- `GET /iade-sec` (Onaylı Satış/Alış arama) + `GET/POST /<id>/iade-olustur`.
  Kalemler fiyat/iskonto/KDV aynen kopyalanır; yalnız miktar girilir.
- Kalan: `kaynak − SUM(iade kalemleri)` agregatı — Taslak + Onaylı sayılır,
  İptal/Reddedildi hariç (sayaç yok → red/iptal/silmede otomatik serbest, §19).
- Limit: formda `max` + JS anlık takas + sunucuda flash + redirect (§6).
- pb kaynaktan devralınır (salt okunur); kur `db.guncel_kur` önerisiyle
  düzenlenebilir (D012/D017 deseni, §9).
- İade düzenlenemez (`/duzenle` flash + redirect): normal form
  `kaynak_kalem_id` bağını koruyamaz; düzeltme yolu sil + yeniden dönüşüm (§8).
  Normal formun tip listesi `TIPLER_FORM` ile kilitli (POST enjeksiyonu da
  iade üretemez).

## Onay etkileri

- **İade faturası** (`_stok_uygula_iade`): cari (SatisIade→alacak, AlisIade→
  borç) + `muhasebe.fis_uret(..., 'iade')` aynası (600/391↔120, 320↔191/153/770;
  mevcut hesaplarla, ters taraf) + stok (satış +, alış −, `(Fatura, iade_id)`
  kimliğiyle, form deposuna). İptalde cari/yevmiye silinir + stok telafi
  hareketi yazılır (iz korunur).
- **İade irsaliye:** `_stok_kontrol_ve_uygula` yeni kolları (SatisIade +,
  AlisIade −); cari + yevmiye atlanır (§12; `fis_uret`/`_irsaliye_satirlar`
  savunma korumalı).
- Kaynak detayda kalem satırında "İade Edilen: X / Y" + "Bu Belgenin İadeleri"
  listesi; iade detayda "Kaynak Belge" kartı. Yazdırmada §18 başlıkları +
  "İadesi: SF-…". D019 çift döviz kolonu pb-bazlı olduğundan iadede otomatik.

## Red fişi & kilitler

- Fatura red fişi 4 tipi de kapsar: cari takası tipe göre dallanmak yerine
  kendi toplamlarının takasına genellendi (kaynaklı faturada toplam 0 →
  otomatik atlanır); yevmiye orijinal araması `('','iade')` sahnelerini kapsar.
- İrsaliyeye yeni `POST /red-fisi`: cari takas + yevmiye storno + kendi stok
  tersi + K25 e-belge kilidi (iptal kuralıyla aynı). İade irsaliyede yalnız
  stok bacağı çevrilir.
- **Madde 13:** tüm iade/red stok hareketleri işlem gören belgenin kendi
  `(modül, kayıt)` kimliğiyle yazılır; kaynak stok satırlarına UPDATE/DELETE
  yok (testte önce/sonra SQL kanıtı).
- Yetki §21: oluşturma = modül yazma rolü, onay/red = onay rolü (mevcut
  route rolleri; `satis` kullanıcısıyla 403 kanıtlı).

## Test & kanıt

- `test_d020_iade_ailesi.py`: **13/13** (seriler, 2× onay aynası, yalnız-stok,
  kısmi + bloke, kaynak detay, çift sayım + §19, USD, taslak, kilit, yetki,
  migrasyon, FK/kalıntı).
- Tam regresyon: **34 dosya / 693 kontrol / 0 hata** (680 + 13 tam tutarlı).
- Migrasyon kanıtı 3 katmanlı: (1) test içi `_migrate_d020` çağrısı
  (eski-şekilli temp DB, idempotence dahil), (2) canlı kanıt — v1.50 koduyla
  üretilmiş DB + örnek veri, v1.51 koduyla açıldı: CHECK + kolon + 8/9/4/5
  satır korunumu + FK temiz + trigger/index, (3) taze kurulum CREATE yolu.
  Bkz. `kanitlar/v1.51.0/D020-migrasyon-kaniti.txt`.
- Teslim: `teslim/D020-v1.51.0.zip` (sansürlü, PNG'siz, demo DB dahil) + MD5/SHA256.

## Notlar

- Kodlama sırasında yakalananlar: iade INSERT'lerinde placeholder sayısı
  (17 değer/18 kolon → düzeltildi); test bağlantısında `row_factory` eksikliği.
- Tasarım kararı: iade faturası stok bacağını da üstlenir (direktif §10 kesin);
  aynı fiziksel iade için hem iade faturası hem iade irsaliyesi oluşturulmaması
  gerektiği onay ipucunda belirtilir (çift sayım uyarısı).
- GM kuralı gereği doğrudan commit & push yapıldı; bu rapor + ZIP GM kontrolüne sunuldu.
