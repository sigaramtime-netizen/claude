# R023 — Muhasebe Çekirdeği + Teminat Çek/Senet (v1.54.0) — Coder Raporu

**Tarih:** 2026-09-18 · **Direktif:** `gm-direktifleri/D023-muhasebe-cekirdegi-teminat.md`
(KÖPRÜ, M2/M3/M4/T2) · **Sürüm:** v1.53.0 → v1.54.0

## Şema (`db.py`)

- `hesap_esleme(id, sirket_id, anahtar, hedef_kod, not_, UNIQUE(sirket_id, anahtar))`
  — 13 anahtar (satis_alici 120, satis_hasilat 600, satis_kdv 391, alis_satici 320,
  alis_kdv 191, alis_stok 153, alis_manuel_gider 770, kasa 100, banka 102,
  cek_alinan 101, cek_verilen 103, amortisman_gider 770, amortisman_birikmis 257).
  Varsayılanlar v1.53 sabitleriyle birebir → davranış değişmez.
- `cek_senet.teminat INTEGER NOT NULL DEFAULT 0` + `teminat_durum TEXT NOT NULL
  DEFAULT 'Yok' CHECK (…'Yok','Aktif','Mahsup Edildi','İade Edildi')` (taze
  şemada CREATE içinde; eskide ALTER).
- `_migrate_d023(conn)`: tablo + **tüm mevcut şirketlere 13'er varsayılan seed**
  (INSERT OR IGNORE → kullanıcı değişikliği ezilmez) + teminat kolonları
  (backfill 0/'Yok'). Idempotent, testten çağrılabilir.
- `sirket_seed` adım 4: yeni şirkete varsayılan eşlemeler.

## Eşleme motoru (M2)

- **Tek kaynak:** `db.hesap_esleme_get(conn, anahtar, sid)` — eşleme satırı yoksa
  YA DA hedef kod o şirketin `hesap` tablosunda yoksa **varsayılana düşer**
  (asla hatalı/dengesiz fiş). Tablo yoksa (migrasyon öncesi) de varsayılan.
- `_fatura_satirlar` / `_irsaliye_satirlar` (satış 120/600/391, alış 153+191/320,
  manuel 770, iadeler ayna), `_kasa_satirlar` / `_banka_satirlar` (100/102),
  `_cari_hesap` (Müşteri→satis_alici, Tedarikçi→alis_satici, HerIkisi yön
  bazlı), `_cek_ara_kod` (Çek turu→cek_alinan/cek_verilen; **senet 121/321
  sabit** — eşleme kapsamı dışı, davranış korundu), `_cek_satirlar` (tahsil
  100→kasa eşlemesi), amortisman `fis_uret` dalı (770/257) — hepsi
  `hesap_esleme_get`'ten alır. D022 `fis_tipi_bul` deseni korundu.
- Ekran `/muhasebe/eslemeler` (MUH_WRITE): 13 satır × (mevcut kod, hesap adı,
  not) + o şirketin hesap planından dropdown + **Varsayılana Döndür**.
  Geçersiz kod ekrandan kabul edilmez (sunucu doğrulama); her değişiklik
  audit `hesap-esleme` (eski→yeni + işlem). Değişiklik **geleceğe etkilidir**
  (mevcut yevmiyeler yeniden üretilmez — test 2'de eski fiş birebir korunur).

## Fiş hareketleri listesi (M3) — `/muhasebe/hareketler`

- `yevmiye_kalem × yevmiye × hesap` JOIN + kaynak belge no için modül bazlı
  LEFT JOIN'ler (fatura/irsaliye/çek/kasa/banka/demirbaş).
- Kolonlar: Tarih, Fiş No (fiş detay linki), **Fiş Tipi** (D022 rozeti), Hesap
  Kodu+Ad, Açıklama, Borç, Alacak, **Kaynak** (modül etiketi + belge no,
  tıklanabilir: `KAYNAK_URL` haritası — Fatura→/fatura/\<id\>, Kasa→
  /kasa/hareket/\<id\>/fis, Banka→/banka/hareket/\<id\>/fis, Çek/Senet→
  /cek_senet/\<id\>, Demirbaş→/demirbaş/\<id\>, Manüel→/muhasebe/\<id\>).
- Filtreler: tarih aralığı, hesap tek kod **veya aralık** (`100-199` →
  `h.kod>=? AND h.kod<=?`), fiş tipi (D022), cari/belge no metin arama
  (`cari_hareket×cari_kart` EXISTS alt sorgusu — cari adı/kodu/belge no).
- Alt toplam Σborç/Σalacak (filtre kapsamı) + dengesizse **⚠ Dengesiz** rozeti.
- Yazdır (window.print) + CSV (D019 standardı: UTF-8 BOM, `;`, TR sayı, CRLF);
  boş sonuç "Kayıt yok". Şube izolasyonu (izole_sube) korunur.

## Hesap Durumu (M4) — `/muhasebe/hesap-durumu`

- Çoklu hesap seçimi (checkbox + "tümü"; seçim yoksa tümü) × yıl → matris:
  satır başı **açılış** (yıl öncesi Σborç−Σalacak), 12 ay hücresi ay borç /
  ay alacak, TOPLAM kolonu, satır sonu **kapanış** = açılış + Σ(b−a).
- Gösterim aktif/pasif tipine göre: Aktif/Gider doğal borç (B), Pasif/Özkaynak/
  Gelir doğal alacak (A) — `_bk_goster` (TL biçimi, taraf harfi).
- Alt satır: aylık Σborç/Σalacak/net. Parametre: yıl seçimi (−5…+1) +
  **kümülatif bakiye göster** (ay hücresinde ikinci satır; mizan bakiye
  deseni borç−alacak). Yazdır. Test 7: 3 hesapta açılış + Σaylar = kapanış
  SQL ile birebir.

## Teminat çek/senet (T2)

- **Oluşturma:** çek/senet formunda `teminat` checkbox (yalnız Alınan tipinde
  görünür) + cari borç bakiyesi UI ipucu (typeahead seçimine `bakiyeler` JSON
  haritası + submit kontrolü) + sunucu doğrulama: tutar (TL karşılığı) ≤
  carinin borç bakiyesi, aksi halde "aşamaz" flash. `cek_olustur(…,
  teminat=True)` → INSERT `teminat=1, teminat_durum='Aktif'` ve **cek_senkron
  çağrılmaz** → cari 0, yevmiye 0 (test 8 COUNT kanıtı). Verilen tip + teminat
  bloke.
- **Vade işleme** `/cek_senet/teminat/isle` (CEK_WRITE; tekli `id` veya toplu):
  vadesi gelen (`vade<=bugun`) Aktif + Alınan + İptal-dışı teminatlar.
  - Tam (borç ≥ tutar): `muhasebe.teminat_fis_uret` → yevmiye **101 borç /
    120 alacak** (kodlar `cek_alinan` + `satis_alici` eşlemesinden; sahne
    'giris' → sonraki cek_senkron dedup) + cari hareket `Tahsilat` alacak=tutar
    (ilgili_modul CekSenet → ekstrede çek detayı linki).
  - Kısmi (borç < tutar): borç kadar mahsup + çek açıklamasına **"Kalan X
    iade edildi"** (kalan parça fişi yok — fiş açıklamasında da).
  - Borç 0: durum değişmez, "borcu kalmamış, iade edin" uyarısı.
  - Durum → 'Mahsup Edildi'; audit `teminat-mahsup` (tutar/mahsup/kalan/yevmiye
    id). Audit'ler commit sonrası yazılır (kilitlenme önlemi).
- **Erken iade** `POST /cek_senet/<id>/teminat-iade`: yalnız Aktif →
  'İade Edildi', mali etki 0, audit `teminat-iade`.
- **Bordro** `/cek_senet/teminat` (+ dash diğer adı `/cek-senet/teminat`):
  cari × tutar × vade × durum + durum/cari filtresi + Yazdır + CSV (BOM/`;`/TR)
  + durum özet kartları + vadesi gelenlere tekli/toplu "Vadeyi İşle".
- **Kilitler:** `cek_durum` Aktif teminatta tüm durum geçişlerini bloklar
  ("bordrodan işleyin"); `cek_senkron` Aktif teminatta no-op (defter dışı
  kalır, düzenlemede zorla bile fiş/cari üretmez); işlenmiş (Mahsup Edildi)
  teminat düzenlenemez/silinemez (mali iz); vade takvimi + portföy toplamları
  Aktif teminatı dışlar (ayrı "🛡 Teminat (Aktif)" kartı); normal listede
  "🛡 Teminat · durum" rozeti; detayda teminat kartı + İade Et + kilit
  bildirimi; cari detayında "Teminat Çek/Senet (Aktif)" kartı (adet + ₺).

## Test & Teslim

- `test_d023_muhasebe_cekirdegi.py` — **15/15** (kabul kriterlerinin tamamı +
  temizlik): migrasyon kanıtı (13×2 seed, backfill, idempotent, FK), eşleme
  600→602 + eski fiş dokunulmazlığı + audit, varsayılana dön + geçersiz kod
  999 → varsayılana düşüş + fiş dengeli, kasa/banka/çek/amortisman eşlemeleri,
  hareketler CSV≡SQL (aralık+tip+tarih filtresi) + kaynak link + ΣTOPLAM, CSV
  BOM/TR + boş sonuç, hesap durumu SQL kanıtı (100/120/600), teminat defter
  dışı + bloklar, tam mahsup (101/120 + cari + audit), kısmi mahsup (kalan
  notu), akış kilidi + borç-0 uyarısı, erken iade, bordro + CSV + cari kartı,
  yetki 403 + şirket izolasyonu, FK 0 + kalıntı 0 + mizan 0.
- Tam regresyon: **37 dosya / 738 kontrol / 0 başarısız**.
- `kanitlar/v1.54.0/`: test çıktısı, tam regresyon, diff, eski DB migrasyon
  kanıtı (teminat kolonları + hesap_esleme seed), ZIP hash.
- Teslim: `teslim/D023-v1.54.0.zip` (sansürlü; demo seed DB + testler dahil,
  görsel/yedek/upload/pycache hariç) + MD5/SHA256.

## Bilinen notlar

- Vade işleme fişi `fis_tipi='Otomatik'` (kaynak CekSenet — D022 motoru
  tutarlılığı); sahne 'giris' sayesinde işlem sonrası normal tahsil akışı
  (Tahsile Ver → Tahsil Et) sorunsuz devam eder, çift fiş oluşmaz.
- Kısmi mahsup sonrası çek tahsil edilirse tahsil fişi tam tutarla (100/101)
  yazılır — direktif gereği kalan parça için ayrı fiş üretilmez.
- D022 mahsup fişi (MHS, 320/120) bilinçli olarak eşleme dışı bırakıldı
  (D022 sözleşmesi sabit; direktif yalnız `_*_satirlar` ailesini kapsıyor).
