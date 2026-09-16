# R019 — Dövizli Gösterim, Ekstre & Red Fişi (v1.50.0) — Coder Raporu

**Tarih:** 2026-09-16 · **Direktif:** `gm-direktifleri/D019-doviz-gosterim-ekstre-efatura-cila.md`
(KÖPRÜ, Analist 05 H1-H9) · **Sürüm:** v1.49.0 → v1.50.0

## H4/H5 — `|para(birim)` + çift kolon (`core.py`, şablonlar)

- `PARA_SEMBOL = {"TRY": "₺", "USD": "$", "EUR": "€", "GBP": "£"}`; `_para(v, birim)`
  bilinmeyen birimde `1.000,00 XYZ` yazar (asla yanlış sembol). Mevcut `_fmt_para`
  aynen durur (TL uyumluluğu).
- `fatura/detay.html`, `irsaliye/detay.html`, `yazdir/belge.html`: `cift_doviz`
  bayrağıyla Birim Fiyat/Tutar yanına TL sütunları; TL belgede tek kolon (davranış
  değişmez). Yazdırmada `no_etiket` haritası (`FATURA NO`, `İRSALİYE NO`, …) +
  Alış'ta `Tedarikçi Belge No` (H3).

## H9 — Kalan (`fatura.py`)

- `_odeme_durumu` yeniden yazıldı: kasa/banka tahsilat satırları kendi kuruyla
  belge para birimine çevrilir (`odenen`, `kalan` döviz bazlı), `odenen_tl` /
  `kalan_tl` TL yaklaşık. Şablon: `Ödenen: 500,00 $ (≈ 24.225,00 ₺) · Kalan: 500,00 $`.

## H7/H6 — Ekstre (`cari.py`, `ekstre.html`, `ekstre_yazdir.html`)

- `_ekstre_satirlar` helper (ekran + yazdırma ortak): TL tutar + `borc_doviz` /
  `alacak_doviz` alt detayı (`kur>0` ise, `ROUND(x,2)`). Başlık `Bakiye (TL)`;
  kartoteks altında H6 kartı (`1.000,00 USD ≈ 48.450,00 ₺ (Kur: 48,45)`).
  K18 gereği bakiye matematiği zaten TL-doğruydu; düzeltme gösterim katmanında.
- `GET /cari/<id>/ekstre/yazdir` (Wolvox çıktı, filtreli) + `?fmt=csv`
  (BOM + `;` + TR sayı) + ekranda `🖨 Yazdır` / `⬇ CSV İndir` butonları.

## H1/H2 — Aktarım cilası (`efatura_parser.py`, `efatura.py`, `efatura-doldur.js`)

- Cari açılışında `CARI-{VKN}` tekil kodu (çakışırsa `-2…`, VKN yoksa seri);
  adres→il/ilçe: UBL'de `CitySubdivisionName`/`CityName`, metin yolunda
  `İLÇE / İL` biçimi + 81 il sezgiseli.
- JS `deger()` null-guard (miktar/fiyat/KDV/ad/birim yedekli), ekstrede
  `or ''` (belge_no/açıklama) → ekranda `None` yok.

## H8 — Red fişi (`fatura.py`, `db.py`)

- `POST /fatura/<id>/red-fisi` (yalnız Onaylı + Admin/Muhasebe): cari ters kaydı,
  kalan bakiyeyi sıfırlayan yevmiye storno (`kaynak_sahne='red'`), **yalnızca**
  `ilgili_modul='Fatura'` stok hareketlerinin tersi (irsaliye hareketlerine
  dokunulmaz — çift sayım yok), durum → `Reddedildi`, audit `red-fisi`.
  Bağlı tahsilat/ödeme varsa 302 + uyarı (kilit).
- `fatura.durum` CHECK `Reddedildi` içermiyordu → migrate'te DROP+RENAME rebuild
  (tırnaklı DDL + çift-replace tuzaklarına karşı korumalı) + `trg_fatura_sil_ebelge`
  ve index ihyası. Demo DB'de doğrulandı: 7 fatura + 8 kalem korundu, FK temiz.

## Test & kanıt

- `test_d019_cift_doviz_gosterim.py`: **12/12** (H4/H5/H9/H7/H6/H3/H1/H2/H8 + FK/kalıntı).
- Tam regresyon: **33 dosya / 680 kontrol / 0 hata** (668 + 12 tam tutarlı).
- Kanıtlar: `kanitlar/v1.50.0/` (test çıktısı, regresyon, diff, hash).
- Teslim: `teslim/D019-v1.50.0.zip` (sansürlü, PNG'siz, demo DB dahil) + MD5/SHA256.

## Notlar

- Kodlama sırasında yakalanan gerçek bug: `@route(.../ekstre)` satırı helper
  eklenirken `_ekstre_satirlar` üstüne kaymıştı → ekstre 500 veriyordu; test
  yakaladı, düzeltildi, regresyon yeşil.
- GM kuralı gereği doğrudan commit & push yapıldı; bu rapor + ZIP GM kontrolüne sunuldu.
