# D007 — Kullanıcı Geri Bildirimleri & UX/İş Mantığı İyileştirmeleri (v1.39.0)

**Öncelik:** Yüksek — 10 madde, 1 kritik (stok marka/model), 3 yüksek (typeahead filtre, cari ekstre 2 irsaliye bug, eksi stok)  
**Tarih:** 2026-09-12  
**Kaynak:** Final kabul sonrası kralın canlı testi — 10 maddelik liste (aşağıda verbatim)  
**Kapsam:** Yeni tablo **VAR (kontrollü)** — `stok_kart` genişlemesi (migrasyon, geriye dönük uyumlu, default NULL/0) + mevcut tablolarda ek kolonlar. Harici kütüphane yok.  
**Sürüm:** **v1.39.0** (`kod/config.py SURUM = "1.39.0"`)

> GM notu acemi arenası: Kral 10 maddeyi tek seferde yolladı, hepsi haklı. Kritik olanı (stok marka) hemen düzelt, gerisini tek D007'de topla ama testi madde madde yap. Akınsoft referansını ezberle, Wolvox kopyası yok. Her madde için **önce mevcut kodu oku, sonra en az değişimi yap**.

---

## Verbatim Kullanıcı Listesi (değiştirme yok)

1. irsaliye fatura teklif gibi fiyat girilen yerlerde kdv dahil kdv hariç seçeneği kdv nin yanına açılır liste olsun
2. yeni Stok eklemede marka model yazan yere ekleme yapamıyorum (bu ciddi sorun bunun için düzenleme yap)
3. stok ekleme de tevkifat oranı , istisna kodu , Grubu , ana grup , alt grup , özel kod 1 , özel kod 2 , özel kod 3
4. irsaliyede alış irsaliyesinde ürün eklediğimde stokta olan ürünü menuel olarak ürün ismini yazmak istediğimde sadece tek karakterde arama yapıyor mesela ürün TTEC tir T yazdığımda bütün liste açılıyor TTEC yazdığımda ürünü filtrelemiyor kontrol et ve stok eklenen diğer bölümlede kontrol et fatura teklif gibi yerlerde.
5. irsaliyede alış ve satışında sadece tl işlemler var diğer döviz işlemlerinide ekle usd euro gibi, fiyat usd de ekle o fişin içeriğinde usd ve tl aynı anda olsun irsaliye fatura teklifi istersem usd olarak kaydolsun istersem tl olarak kaydolsun akınsoftun sisteminden örnek alabilirsin.
6. irsaliye fatura da stok eklerkende elimizde stok yoksa eklemeye devam etsin eksi bakiyeye düşsün.
7. cari kartodeks te cari seçte liste açılıyor menuel arama yapılabilsin.
8. bir cariye 2 irsaliye ekledim biri alış biri satış irsaliyesi cari ektreden baktığımda ve cari kartoteks ten listenin içeriği gözükmüyor sadece tek satırda satış irsaliyesi gözüküyor ve toplamlarda yanlış cari ismi MÜŞTERİ-A.
9. irsaliye fatura teklif gibi bölümlerde sil tuşuda olsun ama irsaliye veya fatura teklifinin içini açtığımızda silme olsun.
10. uygulamada tanımlı verileri stok ve cari tedarikçi gibi seçme olan bütün bölümlede menuel aramda yapılabilsin uzun listeden çekmek zor oluyor.

---

## A. Hedef & Kapsam Haritası

| # | Başlık | Tip | Dokunan Dosyalar | Risk |
|---|--------|-----|------------------|------|
| 1 | KDV dahil/hariç açılır liste | UX | `fatura/form.html`, `irsaliye/form.html`, `siparis/form.html`, `teklif/form.html`, `pos/satis.html` + `form-satir.js` + ilgili `*.py` (`kdv_dahil` parse) | Düşük |
| 2 | Stok marka/model inline ekleme | **Kritik Bug** | `stok/form.html`, `stok.py`, `marka` tablosu, `base.html` modali | Yüksek |
| 3 | Stok ek alanlar (tevkifat vb.) | Data Model | `db.py` migrasyon, `stok_kart` 8 yeni kolon, `stok/form.html`, `stok.py`, `stok/liste.html`, `stok/detay.html` | Orta |
| 4 | Typeahead filtre bug (TTEC) | Bug | `api.py _stok_ara`, `static/js/typeahead.js`, `static/js/form-satir.js` | Yüksek |
| 5 | İrsaliye döviz (USD/EUR/GBP) TL+orijinal | Feature | `irsaliye.py`, `db.py` (doviz_kur kolon zaten var), `irsaliye/form.html`, `irsaliye/detay.html`, `muhasebe` (TL çeviri) | Yüksek |
| 6 | Eksi stok izni | İş Mantığı | `irsaliye.py _stok_kontrol_ve_uygula`, `fatura.py` stok kontrol, `stok.py` ayar, `core` ayar flag | Orta |
| 7 | Cari kartoteks typeahead | UX | `kartoteks/cari.html`, `kartoteks.py` | Düşük |
| 8 | Cari ekstre/kartoteks 2 irsaliye bug (MÜŞTERİ-A) | **Bug** | `cari.py cari_ekstre`, `kartoteks.py _cari_rows`, `cari_hareket` sorgusu | Yüksek |
| 9 | Detay içinde Sil butonu | UX | `fatura/detay.html`, `irsaliye/detay.html`, `teklif/detay.html`, `siparis/detay.html` | Düşük |
| 10 | Tüm seçimlerde manuel arama (typeahead genelleme) | UX | Tüm `select` → typeahead dönüşümü: `bakim/form.html`, `servis/form.html`, `crm/form.html`, `kartoteks/*`, `pos/*`, `satin_alma/*` | Orta |

---

## B. Teknik Tasarım (Madde Madde)

### 1) KDV dahil/hariç → Açılır liste (Kdv'nin yanında)

**Mevcut:** `input type=checkbox name=kdv_dahil` → checked= dahil.

**İstenen:** KDV oranı input'unun **hemen sağında** `<select name="kdv_dahil">` → `0 = Hariç`, `1 = Dahil`. Placeholder: `KDV Hariç / KDV Dahil`.

**PY değişimi:**
- `kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1","dahil","on") else 0` — geriye dönük uyumlu (checkbox da 1 gönderir, select de 1).
- Template'te `checked` → `selected` mantığı: `<option value="0" {{ 'selected' if not kdv_dahil }}>` / `<option value="1"...>`

**Etkilenen şablonlar (5):**
- `fatura/form.html` (satır bazında değil, **başlık bazında** — sayfa başında Para Birimi / KDV modu yan yana)
- `irsaliye/form.html`
- `sipariş/form.html` (`siparis/form.html`)
- `teklif/form.html`
- `pos/satis.html` (küçük, POS sepet başlığı)

**JS:** `form-satir.js` satır eklemede `kdv_dahil` flag'ini header'daki select'ten okumaya devam edecek (zaten `document.querySelector('[name=kdv_dahil]')`).

**Test:** Dahil seç + birim fiyat 118 gir (KDV %18) → DB'ye net 100 düşer, genel 118 kalır. Hariç seç aynı net 100 → aynı sonuç (F2 kuralı).

---

### 2) Stok marka/model inline ekleme (KRİTİK)

**Mevcut:** `stok/form.html` → `<select name=marka_id>` sadece mevcut markalar. Yeni marka eklemek için `/ayarlar/markalar`a gitmek gerekiyor. Kullanıcı ekleyemiyor.

**İstenen:** Marka select'inin yanında **+** düğmesi → modal / prompt → `POST /stok/marka/ekle` (Ajax) → marka tablosuna `INSERT` (sirket_id ile) → select'e ekle + seçili yap. Sayfa reload yok.

**Tasarım:**
- `db.py` `marka` tablosu zaten var: `id, ad, sirket_id`. Değişmez.
- Yeni route: `POST /api/marka/ekle` veya `POST /stok/marka/ekle` (`roles=(Admin,Muhasebe,Depo)`) — body `ad` → trim → boş değilse insert → `{id, ad}` JSON dön.
- `stok/form.html` → select yanına `<button type=button class="btn sm" id="marka-ekle">+ Marka Ekle</button>` + küçük `<input id="marka-yeni-ad" placeholder="Yeni marka">` veya `prompt()`. En basit: `prompt`.
- JS: `fetch('/api/marka/ekle', {method:'POST', body: new URLSearchParams({ad})})` → dönen id'yi `<option>` olarak ekle.
- Aynı desen **kategori** için de ekle (bonus, kullanıcı isterse — kategori de kapalı olabilir).

**K1:** `sirket_id = db.sirket_id(req)` ile insert.

**Test:** Stok yeni sayfasında marka yoksa `TTEC` yaz → + → Kaydet → Stok kaydet → detayda `marka_ad = TTEC` görünür.

---

### 3) Stok kart ek alanlar (8 alan)

**İstenen alanlar:**

| Alan | Tip | DB Kolon | Form Input |
|------|-----|----------|------------|
| Tevkifat oranı | REAL % | `tevkifat_orani REAL DEFAULT 0` | number 0-100 |
| İstisna kodu | TEXT | `istisna_kodu TEXT` | text |
| Grubu | TEXT | `grubu TEXT` | text |
| Ana grup | TEXT | `ana_grup TEXT` | text |
| Alt grup | TEXT | `alt_grup TEXT` | text |
| Özel kod 1 | TEXT | `ozel_kod1 TEXT` | text |
| Özel kod 2 | TEXT | `ozel_kod2 TEXT` | text |
| Özel kod 3 | TEXT | `ozel_kod3 TEXT` | text |

**Migrasyon (`db.py`):**
- `ALTER TABLE stok_kart ADD COLUMN ...` 8 kez `if col not in cols` kontrolü (idempotent, `init_db` içinde).
- Mevcut kartlarda default: `0` / `NULL` — raporlar etkilenmez.
- `sirket_id` filtresi yok, global kolon.

**Form (`stok/form.html`):** Yeni card `Ek Bilgiler` → 2 satır grid (4+4). Placeholder ve help text ekle.

**Liste (`stok/liste.html`):** İstemeden kalabalık yapma — detayda göster, listede sadece `grubu` badge olarak (opsiyonel).

**Detay (`stok/detay.html`):** Yeni satır.

**PY (`stok.py`):** `v = { "tevkifat_orani": _f(req.form.get("tevkifat_orani")), "istisna_kodu": ..., }` → INSERT/UPDATE.

**Test:** Yeni stok `grubu=Elektronik, tevkifat=50, ozel_kod1=BRN-1` ile kaydet → detayda görünür → düzenle → değerler korunur → FK0.

---

### 4) Typeahead filtre bug — T yazınca hepsi, TTEC yazınca filtrelemiyor

**Mevcut şikayet:** Alış irsaliyesinde manuel stok arama tek harfte hepsi geliyor (doğru), ama `TTEC` yazınca filtre daralmıyor (yanlış). Diğer belgelerde de aynı.

**Kök neden adayları:**
- `api.py _stok_ara`: `like = f"%{q}%"` → `WHERE s.ad LIKE ? OR s.kod LIKE ?` → `%TTEC%` doğru filtrelemeli. Ancak `ORDER BY CASE WHEN lower(kod)=lower(?) THEN 0` kısmında `q` tam kod değilse alt sıralara atıyor ama filtre zaten `like`. Sorun yok gibi.
- **Gerçek şüpheli:** `typeahead.js` `input` event debounce 200ms + `fetchList(qtext)` sadece `qtext = input.value.trim()` ile çağrılıyor. Ancak `irsaliye/form.html` **manuel stok ekleme** için **ayrı bir `form-satir.js` stok arama** var (`fetch('/api/ara?tip=stok&q='...)`) — o kısım `typeahead.js` değil, eski inline arama. O kodda `q` 1 karakterde mi limit var? `form-satir.js:245 fetch('/api/ara?tip=stok&q=' + ...)` — limit yok ama `minChars` kontrolü olabilir.
- Ayrıca `irsaliye/form.html` satır tablosunda **manuel satır** için `k_manuel_ad` free text, ama stok seçimi için ayrı `k_stok_id` hidden + typeahead kullanılıyor. Alış irsaliyesinde tedarikçi filtresi `cari_tip=Alis` ile stok araması karışıyor olabilir.

**Yapılacak:**
- `api.py` loglama: `T`, `TT`, `TTE`, `TTEC` için curl testi — beklenen: `T` → ~3 kayıt (TTEC, TEL-...), `TTEC` → 1 kayıt (TTEC). Eğer API doğru dönüyorsa bug frontend'de.
- `typeahead.js` → `input` handler'da `if (!qtext) { close(); return; }` → 1 harfte bile fetch yapıyor (doğru). `fetchList` 200ms debounce doğru. Sorun: `focus` event'te `fetchList('')` → ilk 20'yi getiriyor, sonra yazınca `T` ile fetch ediyor ama **önceki `items` render'da `like` ile filtrelenmiyor, direkt API sonucu render**. API doğruysa 1 harfte çok kayıt gelmesi normal (Akınsoft da öyle — ilk harfte geniş liste). Ama `TTEC` yazınca API 1 kayıt dönmeli, dönmüyorsa API bug.
- **Fix:** `_stok_ara` sorgusunu sadeleştir ve test et: `ad LIKE ? OR kod LIKE ? OR barkod LIKE ?` + `LIMIT 20` yeterli. `ORDER BY` karmaşasını kaldır veya `lower(q) = lower(kod)` optimizasyonunu ayrı tut.
- **Ek kontrol:** `form-satir.js` içindeki **manuel stok arama** (eski satır ekleme input'u) tamamen kaldırılacak — tek kaynak `typeahead.js` kalacak (F3 kuralı). İrsaliyedeki satır ekleme artık **typeahead ile stok seç** → `k_stok_id` hidden.

**Test senaryosu (ayrıntılı):**
1. `curl "/api/ara?tip=stok&q=T"` → liste >1
2. `curl "/api/ara?tip=stok&q=TTEC"` → tam 1 (TTEC) — değilse FAIL
3. UI: `/irsaliye/yeni` → stok satırında `T` yaz → liste açılıyor → `TTEC` yaz → liste **daralıyor** sadece TTEC kalmalı — video/screenshot
4. Aynı testi `/fatura/yeni`, `/teklif/yeni`, `/siparis/yeni`, `/pos/satis` hepsinde tekrarla.

---

### 5) İrsaliye döviz (USD/EUR/GBP) — Akınsoft deseni

**Mevcut:** `irsaliye.py` → `para_birimi="TRY"` sabit, `fatura.py` → `para_birimi` seçilebilir (4 para birimi), `teklif`/`siparis` de seçilebilir. İrsaliye eksik.

**İstenen:** İrsaliye de **para birimi + doviz_kur** seçilebilir olmalı; fiş içeriğinde **hem orijinal döviz hem TL karşılığı** görünmeli; kullanıcı irsaliye/fatura/teklifi **USD olarak da kaydedebilmeli**.

**Akınsoft deseni (özet):**
- Belge başlığında `Para Birimi [TRY/USD/EUR/GBP v]` + yanında `Kur [___]` (TRY ise 1.0 ve readonly, döviz ise `db.guncel_kur()` ile dolu, editlenebilir).
- Satır tutarları **orijinal para biriminde** girilir, DB'ye orijinal yazılır; **TL karşılığı** cari/muhasebe için `kur` ile çevrilir (mizan TL).
- Detay sayfasında `Genel Toplam: 100 USD (≈ 3.000 ₺)` çift gösterim.

**DB:** `irsaliye` tablosunda zaten `para_birimi TEXT DEFAULT 'TRY'` + `doviz_kur REAL DEFAULT 1` yoksa ekle (fatura gibi). Migrasyon `db.py` → `irsaliye` için `PARA_BIRIMLERI` kontrolü.

**PY (`irsaliye.py`):**
- `_form_post` içinde `para_birimi = req.form.get("para_birimi") if in PARA_BIRIMLERI else "TRY"` + `doviz_kur = _f(req.form.get("doviz_kur"), 1.0)` (TRY→1.0, döviz→ `db.guncel_kur()` fallback)
- `cari.hareket_ekle` ve `muhasebe.fis_uret` çağrılarında `para_birimi, doviz_kur` geçir (faturada olduğu gibi `pb/kur`).
- Detay template'te `para_birimi` rozeti + TL çevirisi: `{{ irsaliye.genel_toplam }} {{ irsaliye.para_birimi }} {% if irsaliye.para_birimi != 'TRY' %} (≈ {{ (irsaliye.genel_toplam * irsaliye.doviz_kur)|para }} ₺){% endif %}`

**Form (`irsaliye/form.html`):** Başlığa `Para Birimi` select + `Kur` input (fatura formundan kopyala). `TRY` seçilince kur 1.0 disable.

**Test:**
- Satış irsaliyesi `USD, kur 30, miktar 1, birim 100 USD` → `genel_toplam=120 USD`, cari_hareket `borc=3600 ₺` (120*30) mi yoksa `borc=120 USD` + kur ayrı mı? — **Mevcut fatura mantığı:** cari_hareket `para_birimi` ile yazılır, mizan TL'ye çevirir. Aynı desen irsaliyede de olmalı. Test netleştirilecek.

---

### 6) Eksi stok izni (negatife düşsün)

**Mevcut:** `_stok_kontrol_ve_uygula` → `eldeki < miktar → hatalar.append()` → onay engeli. Kullanıcı "stok yoksa da eklemeye devam etsin" istiyor.

**İstenen:** Onay **engellenmesin**, stok **eksiğe düşebilsin**. Uyarı ver ama bloke etme.

**Seçenekler:**
- **A (tercih):** Ayar tablosu `ayarlar` → `eksi_stok_izin = 1` default. Kontrol: `if not eksi_izin and eldeki < miktar → hata`, `else: # izin varsa hatayı atla, rezerve kontrolünü de gevşet`.
- **B (hızlı):** Direkt engeli kaldır, her zaman eksiğe izin ver (kullanıcı isteği net). GM olarak **B** daha basit — ama ileride geri almak zor.

**Karar:** **B** — doğrudan kaldır, ama log'a `UYARI: stok eksiğe düştü` yaz. `hatalar` listesini boş bırak, `stok._hareket_olustur` eksi miktarı yazsın, `stok_seviye.miktar` negatife insin.

**Dosyalar:** `irsaliye.py _stok_kontrol_ve_uygula` + `fatura.py _stok_kontrol` (varsa) — aynı pattern.

**Test:**
- Stok 3 miktar 8 → satış irsaliyesi miktar 10 → onay **başarılı** → `stok_seviye` 8→ -2 → `stok_hareket` -10 → iptal → -2→8 geri döner.

---

### 7) Cari kartoteks → manuel arama (typeahead)

**Mevcut:** `kartoteks/cari.html` → `<select name=cari_id>` + `<input name=q>` ayrı. Uzun listede scroll zor.

**İstenen:** Select yerine **typeahead** (tek input).

**Tasarım:**
- `kartoteks/cari.html` → `<input type=hidden name=cari_id id=cari-id>` + `<div class="typeahead" data-tip="cari" data-target="cari-id" data-initial="{{ cari.unvan }} ({{ cari.kod }})">`
- `typeahead.js` zaten var → `GET /api/ara?tip=cari&q=...` → seçim → form submit (onchange → `this.form.submit()` yerine JS `pick` event'te `form.submit()`).

**Test:** `MÜŞTERİ-A` yaz → MÜŞTERİ-A filtrelenir → seç → kartoteks gelir.

---

### 8) Cari ekstre/kartoteks 2 irsaliye bug — MÜŞTERİ-A

**Mevcut şikayet:** 1 cariye 1 alış + 1 satış irsaliyesi eklenince ekstrede sadece satış görünüyor, toplam yanlış.

**Olası kök nedenler:**
- `cari.py cari_ekstre` sorgusu `WHERE ilgili_modul='Irsaliye'` ama `tip` filtresi `Satis` ile sınırlı olabilir (Transfer hariç gibi). Kontrol: `SELECT * FROM cari_hareket WHERE cari_id=?` → her iki irsaliye de `Satış İrsaliyesi` ve `Alış İrsaliyesi` olarak iki satır olmalı (borç vs alacak). Eğer sadece biri görünüyorsa `cari_hareket` insert'inde alış için `alacak` yazılmıyor mu?
- `irsaliye.py _cari_uygula_irsaliye` → `if irs["tip"] == "Satis": borc=tutar else: alacak=tutar` — doğru. Transfer hariç. Yani satış borç, alış alacak olmalı — her ikisi de yazılmalı.
- `kartoteks.py _cari_rows` → `WHERE cari_id=? AND sirket_id=?` + `belge_tipi` filtresi var mı? `tipler` listesinde `Satış İrsaliyesi` / `Alış İrsaliyesi` ayrı. Eğer filtre `belge_tipi` boşken tümü gelmeli. Bug: `belge_tipi` parametresi `ilgi_modul` ile karışıyor olabilir.
- Toplam yanlış: `top_b = SUM(borc)`, `top_a = SUM(alacak)` — alış alacak, satış borç. Net `borc - alacak`. Eğer sadece biri geliyorsa toplam tek taraflı.

**Yapılacak:**
- Repro: MÜŞTERİ-A carisine `IRS-... Alış (tedarikçi olarak mı? — ama müşteri carisi alış irsaliyesi alamaz, tip Alis ise cari Tedarikci olmalı. Kullanıcı aynı cariye hem alış hem satış yapmış — cari tipi HerIkisi olmalı). Testte HerIkisi cari kullan.
- `sqlite3 "SELECT id, belge_tipi, borc, alacak FROM cari_hareket WHERE cari_id=(SELECT id FROM cari_kart WHERE unvan LIKE '%MÜŞTERİ-A%') ORDER BY id"`
- `cari_ekstre` template'inde `{% for h in rows %}` filtresi `if h.belge_tipi != 'Alış İrsaliyesi'` gibi bir gizleme var mı kontrol.
- Fix: Sorgu netleştir, her iki tip de dahil. `kartoteks.py _cari_rows` içinde `belge_tipi` filtresi sadece seçiliyse uygula, boşsa tümü.

**Test:** MÜŞTERİ-A'a 1 satış (1000) + 1 alış (500) → `top_b=1000, top_a=500, bakiye=500` → ekstrede 2 satır → kartotekste 2 satır + bakiye 500.

---

### 9) Detay içinde Sil butonu (irsaliye/fatura/teklif/sipariş)

**Mevcut:** Sil sadece listede veya `/sil` POST ile. Detay sayfasında yok (veya küçük link).

**İstenen:** Detay sayfasının üst aksiyonlarında **Sil** (kırmızı) + confirm.

**Tasarım:** `fatura/detay.html`, `irsaliye/detay.html`, `siparis/detay.html`, `teklif/detay.html` → `.page-actions` içine:
```html
{% if row.durum == 'Taslak' %}
<form method="post" action="/fatura/{{ row.id }}/sil" onsubmit="return confirm('Silinsin mi?')">
  <button class="btn danger sm">🗑 Sil</button>
</form>
{% endif %}
```
Mevcut `*_sil` route'ları zaten `Taslak` kontrollü — sadece buton ekle.

---

### 10) Tüm seçimlerde manuel arama (typeahead genelleme)

**Mevcut:** F3'te 11 şablon typeahead'e geçti, ama bazı yerler hâlâ `<select>`: `kartoteks/cari.html`, `kartoteks/stok.html` (stok select), `bakim/form.html` (cihaz?), `servis/form.html` (cari?), `satin_alma/form.html` (tedarikçi? — typeahead var ama kontrol), `cari/liste.html` filtre.

**İstenen:** Uzun listeli her `<select>` typeahead'e dönsün.

**Kapsam (tam liste çıkarılacak):**
- `kartoteks/cari.html` (cari select) → typeahead
- `kartoteks/stok.html` (stok select) → typeahead (data-tip=stok)
- `kartoteks/index.html` barkod zaten var
- `bakim/form.html` cari + cihaz?
- `servis/form.html` cari + stok?
- `crm/form.html` cari zaten typeahead (kontrol)
- `notlar`, `cek_senet` cari seçimi?

**Kural:** `select` içinde `>20` option varsa typeahead şart. `GET /api/ara` zaten 20 limit — UX düzelir.

**Test:** Her sayfada `TTEC` yaz → doğru filtre → seçim → POST başarılı.

---

## C. Veri Modeli (Migrasyon Planı)

### Yeni kolonlar — `stok_kart` (8)

```sql
ALTER TABLE stok_kart ADD COLUMN tevkifat_orani REAL NOT NULL DEFAULT 0;
ALTER TABLE stok_kart ADD COLUMN istisna_kodu TEXT;
ALTER TABLE stok_kart ADD COLUMN grubu TEXT;
ALTER TABLE stok_kart ADD COLUMN ana_grup TEXT;
ALTER TABLE stok_kart ADD COLUMN alt_grup TEXT;
ALTER TABLE stok_kart ADD COLUMN ozel_kod1 TEXT;
ALTER TABLE stok_kart ADD COLUMN ozel_kod2 TEXT;
ALTER TABLE stok_kart ADD COLUMN ozel_kod3 TEXT;
```

Idempotent: `if col not in pragma_table_info` → add.

### İrsaliye döviz (varsa ekle)

```sql
-- kontrol: irsaliye para_birimi var mı?
ALTER TABLE irsaliye ADD COLUMN para_birimi TEXT NOT NULL DEFAULT 'TRY';
ALTER TABLE irsaliye ADD COLUMN doviz_kur REAL NOT NULL DEFAULT 1.0;
ALTER TABLE irsaliye_kalem ADD COLUMN doviz_kur REAL; -- satır bazlı kur (opsiyonel, başlıkla aynı)
```

`fatura` ve `teklif/siparis` zaten var — dokunma.

### Ayar

```sql
-- eksi stok izni (opsiyonel, ama B seçeneğinde gerek yok — doğrudan koddan izin ver)
-- yine de ekle, ileride kapatmak isterse:
INSERT OR IGNORE INTO ayarlar(anahtar, deger, sirket_id) VALUES('eksi_stok_izin','1',1);
```

**FK/UNIQUE:** Yeni kolonlarda yok. Mevcut FK korunur.

---

## D. Kabul Kriterleri (Test Senaryoları) — 22 Kontrol (F6 deseni)

| # | Kontrol | Beklenen |
|---|---------|----------|
| 1 | `test_kdv_select_fatura` → KDV select Hariç/Dahil | POST `kdv_dahil=1` → net 100, `0` → net 100 (F2) + UI select görünür |
| 2 | `test_kdv_select_irsaliye` | aynı |
| 3 | `test_kdv_select_teklif_siparis_pos` | 3 şablon daha select |
| 4 | `test_marka_inline_ekle` → stok form + marka | `POST /api/marka/ekle {ad:TTEC2}` → 200 + stok kaydet → detayda TTEC2 |
| 5 | `test_stok_ek_alanlar_kayit` → 8 alan | insert → select → 8 alan doğru |
| 6 | `test_stok_ek_alanlar_guncelle` | update korunur |
| 7 | `test_api_ara_TTEC` → `/api/ara?tip=stok&q=TTEC` | tam 1 kayıt (TTEC) — T'de >1 |
| 8 | `test_typeahead_irsaliye` → UI | irsaliye yeni → stok input TTEC → liste daralır |
| 9 | `test_irsaliye_doviz_usd` → USD irsaliye | `para_birimi=USD kur=30` → irsaliye oluşur + detayda `USD (≈ TL)` + cari_hareket TL çevrilmiş |
| 10 | `test_irsaliye_doviz_tl_ceviri_muhasebe` | yevmiye TL dengeli |
| 11 | `test_eksi_stok_izin` → miktar 10 stok 8'de satış 10 | onay başarılı, seviye -2, iptal → 8 |
| 12 | `test_eksi_stok_fatura` | aynı faturada |
| 13 | `test_kartoteks_cari_typeahead` → UI | `/kartoteks/cari` typeahead var + MÜŞTERİ-A filtre |
| 14 | `test_cari_ekstre_2_irsaliye` → MÜŞTERİ-A HerIkisi | satış borç + alış alacak 2 satır + top doğru |
| 15 | `test_kartoteks_cari_2_irsaliye` | aynı kartotekste 2 satır |
| 16 | `test_sil_butonu_detay` → 4 detay sayfa | fatura/irsaliye/teklif/siparis detayda Sil formu var + Taslak ise aktif |
| 17 | `test_typeahead_genel_cari` → tüm cari selectler typeahead | grep `select name=cari_id` → 0 (sadece typeahead kaldı) |
| 18 | `test_typeahead_genel_stok` | aynı stok için |
| 19 | `test_f6_korundu` → bildirim/yetki/yazdir/sube/saglik | 200 |
| 20 | `test_f5c_f5b_f1_korundu` | 200 |
| 21 | `test_k1_korundu` → şirket B'de A verisi yok | 0 |
| 22 | `test_fk_kalinti` → FK0 + kalıntı 0 | 0 |

**Regresyon:** 496 → **~518** (yeni kontrollerle). Tüm eski testler + yeni 22.

---

## E. Dosya Değişim Özeti (beklenen)

```
kod/config.py                  SURUM 1.39.0
kod/db.py                      migrasyon (8 kolon + irsaliye doviz)
kod/api.py                     stok arama ORDER BY sadeleştirme (TTEC fix)
kod/stok.py                    8 alan + marka ekle route
kod/irsaliye.py                döviz + eksi stok + kdv select parse
kod/fatura.py                  kdv select parse
kod/siparis.py, teklif.py      kdv select parse
kod/kartoteks.py               cari rows bug + typeahead hazırlık
kod/cari.py                    ekstre bug (if varsa)
kod/core.py                    (gerekirse eksi_stok helper)
kod/static/js/typeahead.js     (gerekirse debounce düzeltme)
kod/static/js/form-satir.js    kdv select okuma
kod/templates/stok/form.html   marka + + 8 alan
kod/templates/fatura/form.html select kdv
kod/templates/irsaliye/form.html select kdv + para birimi + kur
kod/templates/siparis/form.html select
kod/templates/teklif/form.html select
kod/templates/pos/satis.html   select
kod/templates/fatura/detay.html Sil butonu
kod/templates/irsaliye/detay.html Sil
kod/templates/teklif/detay.html Sil
kod/templates/siparis/detay.html Sil
kod/templates/kartoteks/cari.html typeahead
kod/templates/kartoteks/stok.html typeahead (opsiyonel)
kod/templates/yazdir/belge.html doviz gösterim (USD≈TL)
kanitlar/v1.39.0/*              4 dosya
test_d007_iyilestirmeler.py     22 kontrol
```

---

## F. Teslim Şekli

1. Kod → `c9XXXXX [CODER] D007 ... v1.39.0` commit, `kanitlar/v1.39.0/` (test çıktısı + degisen dosyalar + hash)
2. GM bağımsız: `python3 -c db.init_db` (FK0), `app.py` canlı, `python3 test_d007_iyilestirmeler.py 22/22`, `for f in test_*.py → 518/518`
3. `DURUM.md` → KODLANDI → GM ONAYLANDI mühür
4. Bilinen risk: Akınsoft döviz çift gösterim — TL çeviri mizanı bozarsa F1 testi yakalar (borç≠alacak).

---

**Onay:** GM → Coder'a ilet, direktif net. Kritik madde 2 önce.
