# D022 — FİŞ TİPİ MOTORU + GERÇEK MAHSUP FİŞİ (M1, T1)

**Tarih:** 2026-09-16  
**Veren:** KÖPRÜ (Analiz 07 Sıralı Çalışma Planı, D022 kartı doğrultusunda)  
**Öncelik:** Yüksek / Muhasebe Çekirdeği  
**Versiyon Hedefi:** v1.52.0 → v1.53.0

---

## 1. GEREKÇE & KÖK NEDEN ÖZETİ
Analist taraması (04/B.1, D019-D021 sonrası yeniden doğrulandı): `yevmiye`
tablosunda **`fis_tipi` kolonu YOK** — fiş tipi bugün zımni: açılış/kapanış
`aciklama LIKE 'Dönem ... Fişi %'` string eşleşmesiyle, tahsilat/tediye
`kaynak_modul` + makbuz no'su (THS-/ODM-) ile, red/kısmi `kaynak_sahne` ile
ayrışıyor. Tip bazlı filtre, rapor ve kontrol imkânsız. (T1) Alacak↔borç
**mahsup fişi hiç yok** — `tediye` yalnız tek taraflı ödeme girişi.

Mevcut altyapı (korunacak): `/muhasebe/yeni` (dengeli muhtelif),
`/muhasebe/acilis` + `/kapanis` (idempotent), `muhasebe.fis_uret`
((modul,id,sahne) dedup'lu otomatik fiş), THS/ODM makbuz akışı
(`cari_odeme.py`), mizan/defter/hesaplar. Bu direktif mevcut davranışı
**değiştirmeden** tipleri adlandırır + mahsup fişini ekler.

---

## 2. DETAYLI GEREKSİNİMLER

### BÖLÜM 1: Fiş tipi motoru (M1)
1. `yevmiye.fis_tipi TEXT NOT NULL DEFAULT 'Muhtelif' CHECK (fis_tipi IN
   ('Açılış','Tahsilat','Tediye','Mahsup','Kapanış','Muhtelif','Red','Otomatik'))`
   (ALTER ADD COLUMN — CHECK tablo rebuild'i gerektirmez; eski DB kanıtı yine
   zorunlu).
2. **Geriye dönük etiketleme** (migrasyonda, idempotent):
   - `aciklama LIKE 'Dönem Açılış Fişi %'` → `'Açılış'`
   - `aciklama LIKE 'Dönem Kapanış Fişi %'` → `'Kapanış'`
   - `kaynak_sahne = 'red'` → `'Red'`
   - `kaynak_modul IN ('Fatura','Irsaliye','CekSenet')` → `'Otomatik'`
   - `kaynak_modul IN ('Kasa','Banka')` ve ilgili `kasa_hareket`/`banka_hareket`
     `belge_no` `'THS-'` ile → `'Tahsilat'`; `'ODM-'` ile → `'Tediye'`
   - kalan her şey → `'Muhtelif'`
3. **Tip etiketi üretimi** (yeni fişlerde, migrasyondan bağımsız tek kaynak):
   `muhasebe.py`'e `fiş_tipi_bul(modul, sahn, harekette_belge_no)` helper'ı —
   tüm INSERT noktaları (`/muhasebe/yeni`, `acilis_fisi`, `kapanis_fisi`,
   `fis_uret`, D019 red fişi, D020/D021 iade/konsinye yevmiyeleri) bu
   helper'dan değer alır; manuel `/muhasebe/yeni` → `'Muhtelif'`.
4. **Yevmiye listesi:** `fis_tipi` filtre dropdown'u + satırda tip rozeti
   (Otomatik=muted, Tahsilat=ok, Tediye=warn, Red=danger, Mahsup=info,
   Açılış/Kapanış=primary, Muhtelif=varsayılan). Mevcut `kaynak` filtresi
   korunur.
5. **Ters fiş:** `POST /muhasebe/<id>/ters` (MUH_WRITE) — yalnız
   `Muhtelif / Mahsup / Tahsilat / Tediye` tiplerine (Otomatik/Red/Açılış/
   Kapanış'ta flash + redirect: "otomatik fişleri kaynak belgenin red fişiyle
   tersine çevirin"). Fiş: satırların borç↔alacak takası, aynı `fis_tipi`,
   `kaynak_modul='Muhasebe'`, `kaynak_id=<orijinal>`, `kaynak_sahne='ters'`,
   yeni FIS no'su; Mahsup tiplerinde cari hareketleri de aynen takas edilir
   (D019 storno deseni). Tersinin tersi bloke (sahne='ters' fişe ters yok).
   Audit: `yevmiye-ters`.
6. **Kopyala:** `POST /muhasebe/<id>/kopyala` (MUH_WRITE) — tüm tiplerden;
   yeni `'Muhtelif'` fiş, satırlar aynen, tarih = bugün, `aciklama="Kopya:
   <orijinal fis_no>"`, yeni FIS no'su. Orijinale dokunulmaz.
7. Fiş detayında: tip rozeti, (Mahsup'ta) mahsup kartı, `Ters Fiş` / `Kopyala`
   butonları (yetki: MUH_WRITE; kural dışı tipte buton gizli + flash).

### BÖLÜM 2: Gerçek mahsup fişi (T1)
8. `GET/POST /muhasebe/mahsup` (MUH_WRITE). Form: **alacaklı cari**
   (borç bakiyesi > 0 olan cari listesi), **borçlu cari** (alacak bakiyesi > 0
   — bize borçlu değil, bizim borçlusu), **tutar**, tarih, açıklama.
9. Doğrulamalar (UI + sunucu, ikisi de):
   - iki cari aynı olamaz;
   - tutar ≤ min(alacaklının borç bakiyesi, borçlunun alacak bakiyesi);
   - cari sirket_id izole kullanıcıya ait olmalı (çapraz şirket enjeksiyon
     koruması — `/muhasebe/yeni` deseni).
10. Fiş üretimi: `fis_no = MHS-YYYY-NNN` (`sonraki_belge_no`, yevmiye tablosu,
    "MHS" ön eki), `fis_tipi='Mahsup'`, `kaynak_modul='Muhasebe'`,
    `durum='Onaylandı'`. Satırlar: `120 ALICILAR` alacak=tutar /
    `320 SATICILAR` borç=tutar (dengeli). Audit: `mahsup`.
11. Cari hareketleri: alacaklıya `alacak=+tutar`, borçluya `borc=+tutar`
    (`belge_tipi='Mahsup'`, `belge_no=MHS-...`, `ilgili_modul='Mahsup'`,
    `ilgili_kayit_id=yevmiye_id`, K18 kolonları TRY).
12. Ekstre entegrasyonu: `cari.py` ekstre `belge_url` haritasına
    `_no.startswith("MHS-")` → `/muhasebe/<ilgili_kayit_id>` eklenir;
    her iki carinin ekstresinde fiş görünür (çapraz referans).
13. Mahsup fişinin tersi Bölüm 5'teki genel ters fişle çalışır (cari bakiyeleri
    aynen geri getirir — test kanıtı).

---

## 3. KABUL KRİTERLERİ & TEST
- [ ] `test_d022_fis_motoru_mahsup.py` (min. 14 kontrol):
  - Migrasyon: v1.52 şeması (fis_tipisiz) → kolon + etiketler doğru
    (açılış→'Açılış', THS yevmiyesi→'Tahsilat', fatura yevmiyesi→'Otomatik',
    red→'Red', manuel→'Muhtelif'); idempotent; veri + FK + sayı korunumu.
  - Liste: tip filtresi her tipten doğru satırları döndürür; rozetler basılır.
  - Yeni manuel fiş `'Muhtelif'`; açılış/kapanış butonları çalışır ve etiketli.
  - Mevcut tahsilat akışı (THS) değişmedi: makbuz + cari + yevmiye aynı;
    yevmiye artık `'Tahsilat'` etiketli (regresyon kanıtı).
  - Mahsup: A (100 borç bakiye) + B (60 alacak bakiye) → 50 → A: 50, B: 10
    (bakiye SQL'i); MHS-2026-001 UNIQUE; yevmiye dengeli (Σborc=Σalacak).
  - Mahsup limiti: 51 giriş bloke (UI+DB); aynı cari bloke.
  - Çapraz referans: A ve B ekstresinde MHS- satırı + tıklanabilir link.
  - Mahsup tersi: bakiyeler 100/60'a aynen döner; orijinal detayda "Ters: ..."
    linki; tersinin tersi bloke.
  - Kopyala: yeni FIS, satırlar birebir, "Kopya:" açıklaması, tarih bugün.
  - Otomatik fişe ters engeli: flash + redirect, yevmiye sayısı değişmez.
  - İzolasyon: şirket dışı cari mahsup formunda görünmez/accept edilmez.
  - Yetki: MUH_WRITE'siz kullanıcı 403 (mahsup, ters, kopyala).
  - USD caride mahsup: K18 kolonları (pb TRY, kur 1) + ekstre çift kolon gösterimi bozulmamış.
- [ ] Tam regresyon: 35 mevcut + 1 yeni = **36 test dosyası, 0 hata**.

---

## 4. İSTENEN TESLİM
- `kanitlar/v1.53.0/` altında: test çıktısı, tam regresyon, diff, **eski DB
  migrasyon kanıtı** (etiket dağılımı sorgusu dahil), hash dosyası.
- Sansürlü teslim ZIP (`D022-v1.53.0.zip`) + MD5/SHA256 kanıtları.
- `CHANGELOG.md` v1.53.0 + `config.SURUM`/`SURUM_TARIHI`.
- Rapor: `coder-raporlari/R022-fis-tipi-motoru-mahsup.md` (R019 formatında).
