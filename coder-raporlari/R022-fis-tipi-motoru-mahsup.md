# R022 — Fiş Tipi Motoru + Gerçek Mahsup Fişi (v1.53.0) — Coder Raporu

**Tarih:** 2026-09-18 · **Direktif:** `gm-direktifleri/D022-fis-motoru-mahsup.md`
(KÖPRÜ, M1/T1) · **Sürüm:** v1.52.0 → v1.53.0

## Şema (`db.py`)

- `yevmiye.fis_tipi TEXT NOT NULL DEFAULT 'Muhtelif' CHECK (fis_tipi IN
  ('Açılış','Tahsilat','Tediye','Mahsup','Kapanış','Muhtelif','Red','Otomatik'))`
  — ALTER ADD COLUMN (rebuild gerekmez) + `idx_yevmiye_fis_tipi`.
- `_migrate_d022(conn)`: kolon ekleme + **geriye dönük etiketleme** (yalnız
  hâlâ 'Muhtelif' olanlar → yeni tipler korunur, idempotent): açılış/kapanış
  `aciklama LIKE` deseni, `kaynak_sahne='red'` → Red, `kaynak_modul IN
  ('Fatura','Irsaliye','CekSenet')` → Otomatik, kasa/banka `belge_no`
  THS- → Tahsilat / ODM- → Tediye (EXISTS alt sorgusu). Testten doğrudan
  çağrılabilir.

## Fiş tipi motoru (M1) — `muhasebe.py`

- **Tek kaynak:** `fis_tipi_bul(modul, sahne=None, belge_no="", ozel=None)`.
  `ozel` verilirse doğrulanır (açılış/kapanış/mahsup/muhtelif/kopya);
  verilmezse kural: red → Red; belge modülleri → Otomatik; kasa/banka
  THS-/ODM- → Tahsilat/Tediye; kalan → Muhtelif.
- INSERT noktaları: `/muhasebe/yeni` (Muhtelif), `acilis_fisi` (Açılış),
  `kapanis_fisi` (Kapanış), `fis_uret` (modül+sahne+belge_no), D019 fatura/
  irsaliye red fişleri (`("Fatura"/"Irsaliye", "red")`), ters/kopya rotaları.
- Liste: `?tip=` filtresi + 9 sütunlu tablo (Tip rozeti renk haritası).
- **Ters fiş** `POST /muhasebe/<id>/ters`: yalnız `TERS_IZINLI =
  (Muhtelif, Mahsup, Tahsilat, Tediye)`; satır takası + aynı tip +
  `kaynak_modul='Muhasebe', kaynak_id=<orijinal>, kaynak_sahne='ters'`;
  Mahsup'ta cari hareketleri `hareket_ekle` ile takas (belge_no orijinalin
  fis_no'su → ekstrede orijinal fişe bağlı kalır) → bakiyeler aynen döner.
  Tersinin tersi ve otomatik/red/açılış/kapanışta flash+redirect.
  Audit: `yevmiye-ters`.
- **Kopyala** `POST /muhasebe/<id>/kopyala`: her tipten → yeni Muhtelif fiş,
  satırlar birebir, tarih bugün, `Kopya: <fis_no>`. Audit: `kopyala`.
- Detay: tip rozeti, "Ters:"/"Ters edilen fiş" linkleri, Mahsup cari kartı,
  Ters/Kopyala butonları (kural dışı tipte gizli).

## Gerçek mahsup fişi (T1) — `muhasebe.py` + `templates/muhasebe/mahsup.html`

- `GET/POST /muhasebe/mahsup` (MUH_WRITE): alacaklı = borç bakiyeli cariler,
  borçlu = alacak bakiyeli cariler (dropdown'da canlı bakiye).
- Doğrulama (sunucu): aynı cari yasak; tutar ≤ min(bakiyeA, −bakiyeB);
  `cari_kart` + `sirket_id` kontrolü (çapraz şirket enjeksiyon koruması).
  UI: `data-bakiye` ile JS ipucu + `max` sınırı.
- Fiş: `MHS-YYYY-NNN` (`sonraki_belge_no`), tip Mahsup, 320 borç / 120
  alacak; cari hareketleri `(Mahsup, yevmiye_id)` kimliğiyle, K18 TRY/kur 1.
- Ekstre: `cari.py` belge_url haritasına `MHS-` → `/muhasebe/<yevmiye_id>`.

## Düzeltme — kapanış fişi dengesizliği

`kapanis_fisi` kapatma satırını hesap tipine göre sabit tarafta yazıyordu;
iade/red sonrası **ters bakiyeli** hesapta (gelir borç, gider alacak)
negatif satır üretip fişi dengesizleştiriyordu (mizan farkı 4.622,90 ₺).
Artık kapatma bakiyenin **ters tarafına mutlak değer** yazar; fark
590 (alacak, kâr) / 591 (borç, zarar) doğru tarafta. Test 3'e açılış+kapanış
denge ve negatif-satır-yok kanıtı eklendi; canlı mizan farkı 0,00 ₺.

## Test & kanıt

- `test_d022_fis_motoru_mahsup.py`: **14/14** (migrasyon+etiket dağılımı,
  liste filtresi/rozet, manuel+açılış/kapanış, THS/ODM regresyonu, mahsup
  bakiyeleri/UNIQUE/denge, limit+aynı cari, çapraz ekstre, ters+dönüş+
  tersin-tersi, kopyala, otomatik ters engeli, izolasyon, yetki 403×4,
  USD mahsup, FK/kalıntı).
- Tam regresyon: **36 dosya / 723 kontrol / 0 hata** (709 + 14 tam tutarlı).
- Migrasyon kanıtı 3 katmanlı: (1) test içi `_migrate_d022` (fis_tipisiz
  9 fişli temp DB; 6 kural + idempotence + sayı korunumu), (2) canlı kanıt
  `kanitlar/v1.53.0/D022-migrasyon-kaniti.txt` (**etiket dağılımı sorgusu
  dahil**), (3) taze CREATE.
- Teslim: `teslim/D022-v1.53.0.zip` (sansürlü, PNG'siz, demo DB dahil) + MD5/SHA256.

## Notlar

- Kodlama sırasında yakalananlar: ters/kopya/mahsup INSERT'lerinde
  placeholder sayısı (10 değer/9 kolon → 3 rotada düzeltildi); `_hesap_bakiye`
  negatif bakiye dengesizliği (yukarıdaki düzeltme); mahsup formu JS `max`
  (testte `data-bakiye` ile doğrulanır, değer istemci tarafında hesaplanır).
- Canlı DB etiket dağılımı beklendiği gibi: `{Muhtelif: 23, Otomatik: 13}` —
  demo kasa/banka hareketleri THS/ODM öneki taşımadığından Muhtelif kalır
  (kural dışı etiketleme yok; THS/ODM akışı test 4'te kanıtlandı).
- GM kuralı gereği doğrudan commit & push yapıldı; bu rapor + ZIP GM kontrolüne sunuldu.
