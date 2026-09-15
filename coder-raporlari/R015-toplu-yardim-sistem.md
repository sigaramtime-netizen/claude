# R015 — Toplu İçe/Dışa Aktarma + Yardım + Sistem Bilgi (v1.46.0) — Coder Raporu

**Tarih:** 2026-09-15 · **Direktif:** `gm-direktifleri/D015-toplu-ice-dis-aktarma-yardim-sistem-bilgi-v1.46.0.md`
(GM2 kesin, 2026-09-15) · **Sürüm:** v1.45.0 → v1.46.0

## BÖLÜM A — Aktarım Birliği (`kod/aktarim.py`, 15 rota)

- Rotalar: `/stok/...`, `/cari/...` (roller: STOK_WRITE / WRITE_ROLES) +
  `/ayarlar/tanimlar/<kategori|birim|marka>/...` (Admin). Şablon + dışa aktarma
  okuma rollerindedir (liste sayfalarıyla aynı); içe aktarma yazma rolündedir.
- Akış: dosya yükle → `_csv_oku` (utf-8-sig + iso-8859-9 yedeği, `;`/`,` ayraç
  sezme, 5 MB / 2000 satır limiti) → `_dogrula` (başlık birebir, zorunlu alan,
  TR/EN sayı, para-birimi/tip üyeliği, ad→id çözümleme K1'li) → önizleme şablonu
  (50 satır + 50 hata + sayaçlar) → `?onay=1&token` tek kullanımlık yazma.
- `_yaz`: mevcut kod/ad atlanır (yazma anında yeniden kontrol), K1 `sirket_id`,
  tek audit (`ice-aktar`). Stok/cari liste + 3 tanım kartına butonlar eklendi.

## BÖLÜM B — Yardım (`kod/yardim.py` + `static/js/shortcuts.js`)

- `GET /yardim` (12 kart: 8 iş akışı + aktarım + raporlar + tanımlar + yedek;
  `?q` başlık/özet/adım arar; docs dosya adları kaynak gösterilir) + NAV Yardım bölümü.
- `shortcuts.js` **1622 bayt** (< 2KB): Ctrl+K stok+cari `/api/ara` araması
  (2 harf + 200ms debounce, Enter = ilk sonuç), `?` kısayol penceresi (form
  odaklıyken açılmaz), Esc kapatır. Modal CSS + script `base.html`'de.

## BÖLÜM C — Sistem Bilgi (`kod/sistem.py`, Admin)

- `GET /sistem/bilgi`: jinja `SURUM` + `git rev-parse HEAD` (%ci %s, hatada
  "bilinmiyor"), `integrity_check` + FK adedi, tablo/satır listesi + boyut
  (db+wal+shm+journal) + SQLite/user_version, `yedek._liste()` ilk kaydı
  (ad/tarih/bütünlük), `/api/saglik` JS canlı kutusu. Footer'a Admin'e özel link.

## Testler

- `kod/test_d015_toplu_yardim_sistem.py` — **12/12 ✅** (şablon 1, 5 liste
  aktarım 2-4, validasyon 5, atlama 6, K1 7, dışa aktarma 8, yardım 9,
  shortcuts 10, sistem 11, FK/kalıntı 12).
- Tam regresyon — **30 dosya, 645 kontrol (633+12), 0 başarısız ✅**.
- Sürüm sabitleri 1.46.0'a çekildi.

## Debug Notları

1. Stok INSERT'te placeholder fazlalığı (`15 values for 14 columns`) — düzeltildi.
2. Test CSV'lerinde sütun kaymaları (X1/X2/X3, D007 tırnak kaçışı değil ama benzer
   dikkat) — satırlar 11 sütuna sabitlendi; marka hatası yanlış sütundaydı.
3. `requests.text` BOM'u `\ufeff` bırakır (`strip` temizlemez) — assertion
   `replace("\ufeff","")` ile yazıldı; görünmez karakter `repr` ile doğrulandı.
