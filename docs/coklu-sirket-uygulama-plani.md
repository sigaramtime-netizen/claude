# İstek 3 — Çoklu Şirket: Somut Uygulama Planı (Seçenek A)

> Durum: **ADIM 1 ✅ + ADIM 2 ✅ + ADIM 3 ✅ + ADIM 4 ✅ + ADIM 5 ✅** (Adım 6: test+sürüm kaldı).
>
> ⚠️ Ara durum uyarısı artık **kaldırıldı** — Adım 3 tamamlandı: 22 modül `WHERE sirket_id=?`
> filtreli ve insert'ler aktif şirketi damgalıyor; Cari/Fatura/Stok için "A şirketinde oluşan kayıt
> B şirketinde görünmüyor" kanıtı `test_izolasyon_e2e.py` **22/22** ile sağlandı.

## 0. Kilitleşmiş kararlar (kullanıcı onaylı — değişmez)

1. **Mimari A:** Tek veritabanı + her iş tablosunda `sirket_id` kolonu.
2. **Geçiş:** Oturum bazlı — aktif şirket `sessionler` tablosunda tutulur, üst bardan değiştirilir.
3. **Kullanıcı–Şirket:** **N-N** — `kullanici_sirket` ara tablosu; bir kullanıcı birden çok şirkette,
   bir şirkette birden çok kullanıcı.

---

## 1. Veri modeli değişiklikleri (DDL)

### 1.1 Yeni tablolar

```sql
-- Şirket: firma tablosunun çoklu-şirket karşılığı
CREATE TABLE IF NOT EXISTS sirket (
  id            INTEGER PRIMARY KEY AUTOINCREMENT,
  kod           TEXT NOT NULL UNIQUE,
  unvan         TEXT NOT NULL,
  kisa_ad       TEXT,
  vergi_dairesi TEXT,
  vergi_no      TEXT,
  adres         TEXT,
  telefon       TEXT,
  email         TEXT,
  logo          TEXT,
  aktif         INTEGER NOT NULL DEFAULT 1,
  created_at    TEXT DEFAULT (datetime('now','localtime'))
);

-- Kullanıcı-Şirket N-N üyelik
CREATE TABLE IF NOT EXISTS kullanici_sirket (
  kullanici_id INTEGER NOT NULL REFERENCES kullanici(id),
  sirket_id    INTEGER NOT NULL REFERENCES sirket(id),
  PRIMARY KEY (kullanici_id, sirket_id)
);
```

### 1.2 Var olan tablolara eklemeler

```sql
ALTER TABLE sube      ADD COLUMN sirket_id INTEGER NOT NULL DEFAULT 1 REFERENCES sirket(id);
ALTER TABLE sessionler ADD COLUMN sirket_id INTEGER;   -- aktif şirket (oturum bazlı, nullable=ilk girişte set)
```

### 1.3 `sirket_id` damgalanacak tablolar (kapsamlı liste)

- **Master data:** `cari_grup`, `cari_kart`, `kategori`, `marka`, `depo`, `kasa`, `banka_hesap`,
  `hesap`, `demirbas_kategori`, `stok_kart`, `stok_varyant`, `stok_tedarikci`, `doviz_kur`.
- **İşlem/başlık:** `cari_hareket`, `stok_hareket`, `stok_seviye`, `stok_seri`, `stok_sayim`,
  `stok_sayim_kalem`, `depo_transfer`, `depo_transfer_kalem`, `kasa_hareket`, `banka_hareket`,
  `teklif`, `teklif_kalem`, `siparis`, `siparis_kalem`, `irsaliye`, `irsaliye_kalem`,
  `fatura`, `fatura_kalem`, `cek_senet`, `servis_kayit`, `servis_parca`, `e_belge`,
  `gelen_belge`, `yevmiye`, `yevmiye_kalem`, `butce`, `demirbas`, `demirbas_amortisman`,
  `demirbas_zimmet`.
- **Polimorfik / yardımcı:** `notlar`, `ek_dosya`, `bildirimler`, `audit_log`.

> **Kalem tablolarına `sirket_id` denormalize edilir** ve değer başlık kaydından kopyalanır.
> Gerekçe: silme/rapor/stok sorguları kalemlere doğrudan bakar; tek kolon filtre, her sorguda
> başlık JOIN'i zorunluluğunu kaldırır. (Mikro karar **B** — aşağıda.)

### 1.4 `firma` tablosunun akıbeti

`firma` tek-satırlık şirket kimliğidir (unvan, vergi dairesi, vergi no, adres…). Çoklu şirkette
bu model çalışmaz; **`firma` içeriği `sirket.id=1`'e taşınır ve `firma` tablosu kaldırılır.**
`core.firma_yenile()` artık **aktif sirketten** okur (footer/başlık/logo). `config.FIRMA_ADI`
yalnızca ilk açılışta `sirket` seed'i için kullanılır. (Mikro karar **D**.)

---

## 2. Migrasyon adımları (idempotent `db._migrate` içinde)

1. `sirket` + `kullanici_sirket` tablolarını oluştur.
2. `sirket` seed: `firma` satırından `id=1, kod='BRN', unvan=…` (yoksa `config.FIRMA_ADI`).
3. Bölüm 1.3'teki **her** tabloya `ALTER TABLE ADD COLUMN sirket_id INTEGER NOT NULL DEFAULT 1`
   (kolon zaten varsa atla — mevcut `_migrate` deseniyle aynı).
4. `sube.sirket_id` backfill = 1.
5. `kullanici_sirket` backfill: tüm mevcut kullanıcılar için `(id, 1)` satırı.
6. `firma` → `sirket` kopyala; `firma` tablosunu bırak (DROP) veya boş bırak.
7. `meta.sema_versiyonu` artır.

> **Kritik:** Adım 3 `DEFAULT 1` ile çalıştığı için mevcut tüm demo/gerçek veriler otomatik
> **1 numaralı şirkete** bağlanır — tek şirket modundaki davranış birebir korunur.

---

## 3. Oturum & geçiş (oturum bazlı)

- `sessionler.sirket_id` = aktif şirket.
- `core.load_session` `req.user`'a ekler:
  - `sirket_id` (aktif), `sirket_ad`,
  - `sirketler`: kullanıcının yetkili olduğu şirket listesi (Admin → tümü; diğer → `kullanici_sirket`).
- Girişte: `sirket_id` boşsa ilk yetkili şirkete set edilir.
- `POST /sirket/gec` → `sessionler.sirket_id` günceller. **Güvenlik:** hedef şirket kullanıcının
  üyelik listesinde olmalı (Admin hariç).

---

## 4. Kapsam (izolasyon) katmanı — mevcut K1 şube deseninin birebir aynısı

`core.py`'de zaten var olan şube deseni şirkete genellenir:

```python
def izole_sirket(req):        # aktif sirket_id (herkes; Admin dahil tek aktif şirket)
    return req.user["sirket_id"] if req.user else None

def sirket_koruma(req, kayit_sirket_id):  # detay/düzenle/silme rotalarında 403 kapısı
    return kayit_sirket_id == izole_sirket(req)
```

- **Liste sorguları:** `WHERE sirket_id = ?` (aktif şirket).
- **Insert/update:** `sirket_id` = aktif şirket, otomatik yazılır.
- **Admin:** tek aktif şirketle çalışır (çapraz-şirket görünümü yok) → veri sızıntısı riski sıfır.
  Çapraz şirket konsolidasyonu (gerekiyorsa) ayrı bir rapor ekranı olarak sonraya.
- **K1 şube izolasyonu alt katman olarak korunur:** `sube` artık şirkete bağlı; kullanıcının
  `sube_id`'si kendi şirketi içinde anlamlı. `sube_koruma` aynen kalır, üstüne `sirket_koruma` biner.

---

## 5. Belge zinciri & çapraz referanslar (şirket dışına sızma engeli)

- Zincir taşımaları (Teklif→Sipariş→İrsaliye→Fatura) **kaynak seçim sorgularına** `sirket_id` filtresi alır.
- Kaynak doğrulama fonksiyonlarına (`_teklif_kaynak_kontrol`, irsaliye/fatura kaynak kontrolleri)
  **kaynak ile aktif şirketin eşleşmesi** koşulu eklenir (mevcut `sube_koruma` çağrılarının yanına).
- `ilgili_modul` + `ilgili_kayit_id` tarzı bağlar (cari hareket ↔ belge, kasa/banka ↔ çek, yevmiye ↔ kaynak)
  şirket filtresiyle birlikte yazılır/okunur.

---

## 6. Belge numara üretimi (K13) — şirket başına bağımsız sayaç

`db.sonraki_belge_no(conn, tablo, kolon, on_ek, yil)` imzasına `sirket_id` eklenir:

```python
def sonraki_belge_no(conn, tablo, kolon, on_ek, yil, sirket_id):
    ... WHERE {kolon} LIKE ? AND sirket_id = ? ...
```

Böylece iki şirketin `BELGE-NNN`, `BELGE-NNN` numaraları birbirine karışmaz/çakışmaz.
(Ön ek şirket kodundan türetilebilir — mikro karar **C** kapsamı.)

### 6.1 **DB kısıtlaması (zorunlu, mikro karar C'den bağımsız): global UNIQUE → composite UNIQUE** ✅ UYGULANDI

K13'ten beri `teklif.teklif_no`, `fatura.fatura_no`, `siparis.siparis_no` vb. kolonlar şemada
**global `TEXT UNIQUE`** olarak kurulmuştu. Yalnızca sayaç `sirket_id` ile filtrelemek yeterli değildir:
B şirketi `BELGE-NNN` üretmeye çalıştığında A şirketi bu değeri kullanmışsa **alttaki UNIQUE kısıtı
SQLite hatası verir**, iki şirket aynı anda çalışamaz hale gelir.

**Çözüm (migrasyonla):** şirket kapsamındaki tüm UNIQUE kolonlar `UNIQUE(sirket_id, <kolon>)`
bileşik kısıtına dönüştürülür. SQLite kolon-seviye UNIQUE'i `ALTER` ile kaldıramadığı için ilgili
tablolar resmi **12-adım prosedürüyle yeniden kurulur** (`_yeni` tablo → kopyala → `DROP` eski →
`RENAME`). Kritik detay: eski ad `RENAME` edilirse çocuk tabloların FK'ları `_eski` adına yeniden
yazılır ve bozulur; bu yüzden sıra **DROP + RENAME**'dir (çocuk FK'ları asıl adı işaret etmeye devam eder).

Kapsanan kolonlar (şirket başına benzersiz olması gereken **tüm** alanlar — yalnızca belge no değil,
aynı çarpışma master-data kodlarında da var):

| Tablo | Kolon | Tablo | Kolon |
|---|---|---|---|
| teklif | teklif_no | cari_kart | kod |
| siparis | siparis_no | stok_kart | kod |
| irsaliye | irsaliye_no | demirbas | kod |
| fatura | fatura_no | depo | kod |
| e_belge | belge_no | kasa | kod |
| gelen_belge | belge_no | banka_hesap | kod |
| yevmiye | fis_no | hesap | kod |
| servis_kayit | servis_no | sube | kod |
| — | — | marka | ad |

Global kalanlar (kullanıcı hesapları ortak): `kullanici.kullanici_adi`; kayıt-içi bileşikler
(`stok_seviye(stok_id,varyant_id,depo_id)` vb.) ebeveynleri şirket kapsamına girdiği için değişmez.

---

## 7. UI değişiklikleri

- **Üst bar:** aktif şirket seçici (dropdown) — yalnız kullanıcının yetkili şirketlerini listeler.
- **`/ayarlar/sirketler`** (Admin): şirket CRUD (liste + yeni + düzenle + pasifleştirme — K32: sert silme yok).
- **`/ayarlar/kullanicilar`**: kullanıcı formuna şirket üyelikleri (N-N checkbox seti) eklenir.
- **`/ayarlar/firma`**: aktif şirketin bilgilerini düzenler → artık `sirket` tablosuna yazar.
- **Footer:** aktif şirket adı + sürüm.

---

## 8. Raporlar & muhasebe

- Mizan, kartoteks, finansal analiz, beyanname, stok raporları: tüm toplam sorgularına `sirket_id` filtresi.
- **Mizan aktif şirket için dengelenir** (borç=alacak şirket başına tutar).
- Hesap planı (`hesap`) `sirket_id` taşır: her şirket kendi planını yönetir (ileride şablondan kopyalama).

### 8.1 ⚠️ Yeni şirket → otomatik Hesap Planı seed'i (Adım 5'te zorunlu)

`hesap.kod` composite UNIQUE'e girdiği için (doğru karar) **her şirketin kendi 27 hesaplık Tekdüzen
Hesap Planı kopyası** olması gerekir. `/ayarlar/sirketler`'de yeni şirket oluşturulduğunda
`db.sirket_seed(conn, yeni_id)` çağrılacak ve şunları **yeni şirketin `sirket_id`'siyle** kopyalayacak:

1. **Hesap planı** (27 kayıt, `HESAP_PLANI` şablonundan) — yoksa fatura/kasa/banka onay kancaları
   `hesap_id` bulamaz ve Genel Muhasebe yeni şirkette hiç çalışmaz.
2. **Demirbaş kategorileri** (`demirbas_kategori`) — demirbaş kaydı kategori referansı bekler.
3. (Değerlendirme) **Varsayılan depo** — stok/sipariş formları boş depo listesiyle açılmasın diye.

> Bu not Adım 5'e gelince hatırlatıcıdır; Adım 2 kapsamında değildir.

---

## 9. Audit / bildirim / ek dosya / notlar

- Dördü de `sirket_id` taşır; yazarken aktif şirket damgalanır.
- `audit_log`: silinen şirketin izleri bile `sirket_id` ile kalır (geçmiş korunur).
- Bildirim taramaları kullanıcı bazlıdır; şirket geçişi bildirimleri etkilemez (kullanıcıya özeldir).

---

## 10. Seed / demo

- Mevcut tüm demo veriler **sirket_id=1**'de kalır.
- Opsiyonel: boş bir "2. Şirket" + örnek kullanıcı (demo geçişini göstermek için).
- Demo şifre `1234` yalnız seed'de (mevcut kural aynen).

---

## 11. Yuvarlanma (rollout) sırası — her adım testli

| Adım | İçerik | Risk |
|---|---|---|
| 1 | DDL + `_migrate` + backfill (tek şirket modu davranışı değişmez) | Düşük |
| 2 | `core`: `izole_sirket` + `sirket_koruma` + oturum `sirket_id` | Orta |
| 3 | Modül modül sorgu filtreleri (22 modül) | Yüksek hacim |
| 4 | Numara üretimi + zincir/kaynak kontrolleri | Orta |
| 5 | UI (seçici + ayarlar + kullanıcı N-N) | Orta |
| 6 | Test paketi + sürüm + CHANGELOG | — |

---

## 12. Test planı

Yeni `test_coklu_sirket.py`:
1. İki şirket kur; **A şirketi verisi B'de görünmez** (liste + detay + rapor).
2. Belge numaraları şirket başına bağımsız (aynı yıl iki `BELGE-NNN`).
3. Zincir taşıma (teklif→sipariş→irsaliye→fatura) şirket dışına sızamaz (kaynak doğrulama 403/uyarı).
4. Kullanıcı yalnız üyelik listesindeki şirketlere geçebilir; Admin tümüne.
5. Cari/Stok silme (`referans_var`) şirket sınırında doğru çalışır (başka şirketin referansı engellemez).
6. Mevcut tüm testler (manuel satır, silme kuralları) **sirket_id=1 bağlamında yeşil kalır** (regresyon).

---

## 13. Mikro kararlar — **KESİNLEŞTİ** (kullanıcı onayı)

- **A — Admin kapsamı:** ✅ **Evet** — Admin de tek aktif şirketle çalışır; çapraz görünüm yok
  (veri sızıntısı riski sıfır). Çapraz şirket konsolidasyonu ileride ayrı, açıkça etiketlenmiş bir
  rapor ekranı olarak.
- **B — Kalem tablolarında `sirket_id`:** ✅ **Evet** — denormalize; başlıktan kopyalanır.
- **C — Belge no ön eki:** ✅ **Hayır** — ön ek değişmez (`BELGE-NNN` formatı korunur); yalnızca
  sayaç şirket başına ayrışır. Teknik çakışma §6.1'deki **composite UNIQUE** ile çözülür.
- **D — `firma` tablosu:** ✅ **Evet** — `sirket`'e geçilir; `sirket.id=1` firma verisini taşır,
  `core.firma_yenile()` aktif şirketten okur, `firma` tablosu kaldırılır (Adım 2'de).

## 14. Durum — Adım 1 ✅ + Adım 2 ✅ (tamamlandı)

`db._migrate_coklu_sirket()` ile (idempotent, `DEFAULT 1` backfill):

- `sirket` + `kullanici_sirket` tabloları kuruldu; `firma` → `sirket.id=1` taşındı (firma tablosu şimdilik duruyor, Adım 2'de kaldırılacak).
- Tüm kullanıcılar `(id, 1)` ile 1. şirkete üye yapıldı (N-N backfill).
- `sessionler.sirket_id` eklendi (oturum bazlı geçiş taşıyıcısı, nullable).
- **17 tablo** composite `UNIQUE(sirket_id, kolon)`'a rebuild edildi; diğer **~30 tabloya** `sirket_id` kolonu eklendi.
- `meta.sema_versiyonu` → **2**.

Doğrulama: `integrity_check → ok`, `foreign_key_check → temiz`, composite UNIQUE davranışı
(aynı no + aynı şirket engel / farklı şirket serbest) DB seviyesinde test edildi; regresyon
(silme 23/23, manuel satır 28/28, teklif/sipariş 15/15) temiz, mizan dengeli.

### Adım 2 ✅ — core katmanı (oturum wiring + firma kaldırma + geçiş rotası)

- `core.load_session`: oturuma `sirket_id` + `sirket_ad` + `sirketler` (N-N üyelik; Admin → tümü)
  eklendi; geçersiz/boş `sirket_id` ilk yetkili şirkete düşürülür.
- `core.izole_sirket(req)` + `core.sirket_koruma(req, kid)` (mevcut K1 `izole_sube`/`sube_koruma`
  deseninin şirket karşılığı).
- `core.firma()` → aktif `sirket`'ten okur (şirket başına önbellek); `firma_yenile()` cache temizler.
- `app.giris`: oturum oluşturulurken `sirket_id` ilk yetkili şirkete atanır.
- `firma` tablosu **kaldırıldı** (migrasyon `DROP TABLE IF EXISTS firma`; veri `sirket.id=1`'de).
- `ayarlar_firma` artık aktif şirketin `sirket` satırını düzenler.
- `edonusum._firma` → `sirket`'ten okur (e-belge kendi `sirket_id`'sini kullanır).
- Yeni modül `sirket.py`: `POST /sirket/gec` (N-N üyelik doğrulamalı; yetkisiz şirkete geçiş engelli).
- `base.html` üst bar: 2+ şirkette oturum bazlı şirket seçici (dropdown).

Doğrulama: `test_coklu_sirket.py` **16/16** (Adım 1 + 2 değişmezleri); regresyon silme 23/23,
manuel satır 28/28, teklif/sipariş 15/15; e-belge `_firma` OK; `integrity_check → ok`, mizan dengeli.

**Sıradaki:** Adım 3 (22 modül sorgu filtreleri — `WHERE sirket_id=?` + insert/update damgası) →
Adım 4 (numara üretimi `sonraki_belge_no` + zincir/kaynak kontrolleri) → Adım 5 (UI: `/ayarlar/sirketler`
CRUD + kullanıcı N-N + §8.1 şirket seed'i) → Adım 6 (test + sürüm).

### Adım 3 ✅ — 22 modül sorgu/insert filtreleri + izolasyon kanıtı

- **Tüm modüller** `sirket_id` filtreli/damgalı: cari, stok, notlar, fatura, teklif, siparis,
  irsaliye, sube, kasa, banka, cek_senet, servis, garanti, transfer, doviz, finansal, beyanname,
  demirbas, kartoteks, muhasebe, edonusum + `app.py` (dashboard/tarama/bildirim), `core.notify`,
  `api.py` canlı arama, `ekler.py` (ek dosya).
- Yardımcılar `sid=None` parametreli: `db.sirket_id(req)`, `db.sonraki_belge_no(..., sirket_id)`,
  `db.guncel_kur(..., sid)`, `kasa._kasalar/_bakiye/_bakiye_doviz`, `banka._hesaplar`,
  `cek_senet._detay`, `transfer.*`, `finansal.*`, `beyanname.*`, `demirbas._amortisman_uret`,
  `kartoteks._cari_rows/_stok_rows`, `muhasebe.*`, `edonusum.*`, `doviz.*`,
  `stok.hareket_cari/hareket_kdv_orani`.
- **Çapraz şirket hedef-ID koruması** (POST kaydetme yolları): fatura (kaynak irsaliye + cari/stok),
  teklif/sipariş/irsaliye (cari/depo/stok), kasa (kasa/cari/banka_hesap), banka (banka_hesap/cari/kasa).
- Belge zinciri kaynak kontrolleri `sirket_id`'li (`_teklif_kaynak_kontrol`, `_siparis_kontrol`,
  `_irsaliye_kontrol`).

Kanıt: **`test_izolasyon_e2e.py` 22/22** — "A şirketinde oluşan cari/stok/fatura B şirketinde
görünmüyor" (liste + JSON API + doğrudan detay erişimi) + ters yön. Regresyon silme 23/23,
manuel satır 28/28, teklif/sipariş 15/15 temiz; `integrity_check → ok`, mizan dengeli.

### Adım 4 ✅ — Belge no + zincir/kaynak kontrolleri

- `db.sonraki_belge_no(..., sirket_id)` — sayaç şirket başına ayrışır; fatura/teklif/siparis/
  irsaliye/servis/demirbas/muhasebe/edonusum/doviz çağrıları `sirket_id`'li.
- Zincir kaynak sorguları `WHERE id=? AND sirket_id=?` (teklif→sipariş→irsaliye→fatura).

### Adım 5 ✅ — UI: şirket CRUD + kullanıcı N-N + şirket seed'i

- `db.sirket_seed(conn, yeni_id)` (idempotent): **27 hesap Tekdüzen** + **5 demirbaş kategorisi** +
  **varsayılan depo (ANA)** — plan §8.1 zorunluluğu.
- `ayarlar.py`: `/ayarlar/sirketler` (liste+yeni), `/ayarlar/sirket/(id)/guncelle`,
  `/ayarlar/sirket/(id)/durum` (pasifleştirme; **en az bir aktif şirket korunur**).
- Kullanıcı N-N üyeliği: `/ayarlar/kullanicilar` yeni kullanıcı formuna şirket checkbox seti;
  `/ayarlar/kullanici/(id)/sirketler` üyelik güncelleme; Admin "tüm şirketler" görünümü.
- `templates/ayarlar/sirketler.html` (yeni), `kullanicilar.html` (üyelik sütunu + checkbox),
  `index.html` (Şirketler kartı), `base.html` footer aktif şirket adı, `style.css` `.chk-inline`.

Kanıt: **`test_sirket_yonetimi.py` 19/19** (şirket oluştur → 27/5/1 seed → admin geçiş →
düzenleme → üyeliksiz geçiş engeli → üyelik sonrası geçiş → pasifleştirme guard + round-trip).

**Sıradaki:** Adım 6 — test paketi toplu koşu + `config.SURUM` bump + CHANGELOG + kullanıcı onayı.
