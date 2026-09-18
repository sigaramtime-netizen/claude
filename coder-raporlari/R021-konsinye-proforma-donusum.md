# R021 — Konsinye Ailesi + Proforma + Satış Dönüşüm + Kredi Kartı (v1.52.0) — Coder Raporu

**Tarih:** 2026-09-17 · **Direktif:** `gm-direktifleri/D021-konsinye-proforma-donusum.md`
(KÖPRÜ, F2/F3/F4 + istemci Bölüm 4) · **Sürüm:** v1.51.0 → v1.52.0

## Şema (`db.py`)

- `fatura.tip` → `+ 'Konsinye','KonsinyeIade'`;
  `irsaliye.tip` → `+ 'Konsinye','KonsinyeIade'`;
  `teklif.durum` → `+ 'Siparişe Dönüştü'`.
- Yeni kolonlar: `fatura.proforma` (backfill 0), `fatura.kaynak_proforma_id`.
- Migrasyon: `_migrate_d021(conn)` (testten doğrudan çağrılabilir);
  3 bağımsız `_check_rebuild` + 2 kolon ALTER'ı, idempotent.
  Taze kurulum CREATE'leri güncel.

## Konsinye (F2) — `fatura.py`, `irsaliye.py`, `muhasebe.py`, `cari.py`

- Seriler: `IKO/IKOI/FKO/FKOI-YYYY-NNN` (`TIP_ON_EK`, UNIQUE korunur).
- IKO/IKOI onayında stok/cari/yevmiye SIFIR (durum rotasında atlanır;
  `_stok`/`_cari_uygula_irsaliye` savunma korumalı). FKO onayında stok −
  (belge deposu) + cari borç (müşteri) + Satis KDV aynası; FKOI D020
  SatisIade yönleriyle ama bakiyeye etki 0.
- Bakiye: `cari._konsinye_bakiye` sayaçsız agregat (cari × stok × varyant,
  yalnız Onaylı). FKO/IKOI girdisi ≤ bakiye: form satır rozeti + flash bloke
  + onay-anı bekçisi (Taslak sayılmadığından onayda yeniden denetlenir).
- FKO red/iptalinde ters kayıtlar; bakiye agregat olduğundan otomatik geri
  döner. Red fişleri savunmalıdır (hareket yoksa yalnız durum değişir).
- `/cari/konsinye`: gönderilen/faturalanan/iade/bakiye + cari filtresi +
  stok araması + sıfır-gizleme + Yazdır + D019 CSV (BOM/`;`/TR sayı).
  Cari detayında "Konsinye Bakiyesi" kartı.
- IKO detayında "💰 Fatura Oluştur" → FKO dönüşümü (kalem kopyalama +
  bakiye kontrolü); FKO'dan D020 iade akışı (`KonsinyeIade`).
  Yazdırmada `KONSİNYE FATURASI/İRSALİYESİ` no_etiketleri + çift döviz kolonu.

## Proforma (F3) — `fatura.py`, `core.py` + 5 şablon

- `PF-YYYY-NNN` serisi; onayda `_cari_uygula`/stok/yevmiye atlanır
  (3 COUNT = 0, test kanıtlı), e-belge üretilmez, Ödeme kartı gizlenir.
- "🔄 Faturaya Dönüştür" → `?kaynak_proforma` kalem kopyalı normal taslak;
  detayda kaynak/dönüşüm kartları. Proforma iade kaynağı olamaz (UI + DB).
- PROFORMA şeridi (form/detay/yazdır) + footer "Proforma belge e-fatura
  sayılmaz." Taslak kuralları (düzenle/sil) normal faturayla aynı.

## Satış dönüşüm (F4) — `siparis.py`, `teklif.py` + 4 şablon

- Sipariş detayında "🚚 İrsaliye Oluştur" (yalnız Onaylandı/Kısmi).
  Kısmi teslimatta ikinci irsaliye serbest (`_siparis_kontrol` + teslim
  kontrolü korunur).
- İrsaliyeler tablosunda Fatura durumu rozeti (Faturalandı/Kısmi/Faturasız)
  + Fatura Oluştur linkleri; fatura linkleri durum rozetli.
- Teklif kapanışı (madde 16): kaynak sipariş ONAYLANINCA teklif otomatik
  "Siparişe Dönüştü" (kilit: düzenleme/silme engelli). Sipariş iptalinde
  başka aktif sipariş yoksa teklif "Onaylandı"ya döner (yeniden
  kullanılabilir). Kısmi kısmi birden fazla sipariş serbest
  (`_teklif_kaynak_kontrol` Dönüştü'yü kabul eder). Detayda rozet +
  "Dönüştü Olarak İşaretle" (manuel, sipariş-beslemeli).

## Kredi Kartı (Bölüm 4) — `cari_odeme.py` + 3 şablon

- Ödeme türü net "Kredi Kartı". POS terminali opsiyonel: bağlıysa
  komisyonlu NET, değilse komisyonsuz BRÜT bankaya.
- Fatura Ödeme kartında tek-tık "💳 Kredi Kartı ile Tahsil Et/Öde" →
  `?fatura=` prefill (Kart satırı + güncel kalan); işlem faturaya bağlanır
  (kalan düşer, bağlı-hareket kilidi çalışır; çek/senet bağlanmaz).
- Cari hareket açıklaması "… — Kredi Kartı …" içerir; makbuzda şekil net
  "Kredi Kartı" (terminalsiz tespiti etikete göre, komisyon-notuna değil).

## Test & kanıt

- `test_d021_konsinye_proforma_donushum.py`: **16/16** (IKO/IKOI sıfır etki,
  FKO aynası, FKOI, aşım blokları, FKO red, konsinye ekranı, proforma,
  proforma kilidi, sipariş zinciri, teklif kapanışı, 2× KK, USD konsinye,
  migrasyon, FK/kalıntı).
- Tam regresyon: **35 dosya / 709 kontrol / 0 hata** (693 + 16 tam tutarlı).
- Migrasyon kanıtı 3 katmanlı: (1) test içi `_migrate_d021` (tırnaklı eski
  DDL + idempotence), (2) canlı kanıt `kanitlar/v1.52.0/`, (3) taze CREATE.
- Teslim: `teslim/D021-v1.52.0.zip` (sansürlü, PNG'siz, demo DB dahil) + MD5/SHA256.

## Notlar

- Direktif Bölüm 1/4'teki "cari alacak" ifadesi yazım hatasıdır; "satış
  faturası aynısı" hükmü uygulanmıştır (FKO: müşteri BORÇlanır).
- Kodlama sırasında yakalananlar: `req.query` liste-değer tuzağı (`req.q`
  kullanıldı); kasa/banka yönü `islem_tipi`'ndedir (`yon` kolonu yok);
  ikinci sipariş/teklif kilit etkileşimi (onay-anı kilit + iptal-dönüş);
  KK temizliğinde yevmiye sırası (hareket silinmeden önce id'ler toplanır).
- Eski testlerdeki sabit sürüm beklentileri 1.52.0'a güncellendi
  (test_d010/d015/f6 — sürüm artışı rutini).
- GM kuralı gereği doğrudan commit & push yapıldı; bu rapor + ZIP GM kontrolüne sunuldu.
