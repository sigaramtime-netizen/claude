# R013 — Cari Tahsilat / Ödeme Ekranı (v1.44.0) — Coder Raporu

**Tarih:** 2026-09-15 · **Direktif:** `gm-direktifleri/D013-cari-tahsilat-odeme.md`
(GM1 kesin, 2026-09-15) · **Sürüm:** v1.43.0 → v1.44.0

## Yapılanlar

**Yeni modül `kod/cari_odeme.py`:**
- `GET/POST /cari/<id>/tahsilat` (roller: Admin·Muhasebe·Satis) +
  `GET/POST /cari/<id>/odeme` (roller: Admin·Muhasebe) — tek `_sunum` + tek çekirdek
  `tahsilat_odeme_olustur()` (POS `pos_satis_olustur` deseni: conn açık gelir, COMMIT çağıranın işi).
- Ödeme satırları POS `p_tip/p_tutar/p_vade` deseninin aynısı + `p_no/p_banka` (çek/senet).
- Nakit → `kasa_hareket_olustur` (`ilgili_modul=CariTahsilat/CariOdeme`, direktif birebir);
  Havale/Kart → `banka_hareket_olustur`; Kart'ta terminal komisyonu düşülmüş NET bankaya,
  cariye BRÜT (POS ile birebir); komisyon açıklamada izlenir.
- Çek/Senet → yeni `cek_senet.cek_olustur()` çekirdeği; tahsilatta tip zorunlu `Alinan`,
  ödemede zorunlu `Verilen` (formda tur seçilir: Cek/Senet; vade zorunlu, no boşsa otomatik).
- Cari + fiş: her satırda `cari.hareket_ekle` (belge_tipi Tahsilat/Ödeme, TL karşılığı K18,
  `ilgili_modul=Kasa/Banka` → K15 iptal tutarlılığı) + `fis_uret` / `cek_senkron` (K26).
  Yeni muhasebe kodu YOK.
- Belge no K13 sayaç: `THS-YYYY-NNN` / `ODM-YYYY-NNN` (`sonraki_belge_no` + sirket bazlı).
- Döviz D012 deseni: TRY→kur None; form kuru yoksa `guncel_kur` (kur sabitlenir).
- Kısmi serbest; avans = toplam − max(açık,0) > 0 ise flash + arayüz uyarısı
  ("Bakiyeyi X ₺ aşıyorsunuz — avans olarak işlenecek"), engelleme yok.
- K1: cari/kasa/banka/terminal aktif şirketten doğrulanır (çapraz → 403); şube izolasyonu
  kasa/banka.py deseniyle (izole şube dışı hesap → 403). Ödeme-nakit çıkışında kasa
  bakiye kontrolü (kasa.py deseni, ilgili para biriminde).
- `audit()` kendi bağlantısını açtığı için çekirdekte BİRİKTİRİLİR, commit SONRASI
  yazılır (kasa.py deseni; aksi hâlde `database is locked` — ilk koşuda yakalandı).

**`kod/cek_senet.py`:** `cek_olustur(conn, req, ...)` çekirdeği eklendi (INSERT + `cek_senkron`,
davranış birebir); `_form_post` insert dalı bu çekirdeğe taşındı → kod tekrarı yok.

**Şablon `kod/templates/cari/tahsilat_odeme.html` (ortak):** bakiye/toplam/kalan KPI'ları,
pb+kur (TL karşılığı canlı), kasa/banka/terminal select'leri, dinamik satırlar
(çek/senet alanları koşullu), JS avans uyarısı, "Çek/Senet … olarak işlenir" notu.

**Butonlar:** `cari/detay.html` + `cari/ekstre.html` + `kartoteks/cari.html` page-actions'a
💰 Tahsilat / 💸 Ödeme eklendi.

**Sürüm:** `config.py` 1.44.0 (2026-09-15); test sürüm sabitleri + regresyon başlığı güncellendi;
`CHANGELOG.md` v1.44.0; `DURUM.md` D012→ONAYLANDI (GM1 mühür), D013→KODLANDI.

## Testler

- `kod/test_d013_cari_tahsilat_odeme.py` — **14/14 ✅**
  (form+butonlar 1-2; karışık tahsilat + fiş hesapları + kısmi 3-5; karışık ödeme 6;
  çek/senet iki yön 7-8; döviz 9; avans 10; yetki 403 11; K1 12; vade 13; FK+kalıntı 14).
- Tam regresyon — **28 dosya, 617 kontrol (603+14), 0 başarısız ✅**.
- `PRAGMA foreign_key_check=0`; D013TEST kalıntısı yok.

## Debug Notları

1. İlk koşuda tüm POST'lar 500 + `database is locked`: sebep çekirdek içindeki doğrudan
   `audit()` çağrısı (audit ayrı bağlantı açar; açık yazma txn'i ile kilitlenir). Çözüm:
   auditleri biriktirip commit sonrası yazmak (kasa.py deseni).
2. Aynı dosyaya paralel `edit_file` çağrıları birbirini ezdi (last-write-wins) — audit
   düzeltmesinin bir kısmı + test düzeltmeleri kayboldu, sıralı yeniden uygulandı ve
   `grep` ile doğrulandı. Sonraki işlerde aynı dosyaya sıralı edit disiplini.
