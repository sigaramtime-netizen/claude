# Mimari Kurallar (tüm fazlar için bağlayıcı)

> Bu dosya, fazlar boyunca tutarlılığı garanti eden **mimari sözleşmeyi** tutar.
> Her yeni modül (Faz 2+) bu kurallara uyar; aksine karar alınırsa burada güncellenir.

---

## K1 — Şube (`sube_id`) ön-hazırlık kuralı  ⭐

Amaç: Faz 6'da iş "yalnızca izolasyon mantığını açmak" olsun; **şema migrasyonu + veri
backfill'i gerektirmesin.**

- **Tanım/ana tabloları `sube_id` (nullable, FK→sube) taşır:** `sube`, `depo`, `kasa`,
  `banka_hesap`, `kullanici`. (Depo ve kullanıcı Faz 1'de, kasa ve banka_hesap Faz 1
  sonunda eklendi; UI/filtre/izolasyon mantığı YOK — sadece kolon durur.)
- **Faz 2+ belge tabloları BAŞTAN nullable `sube_id` ile açılır:** `teklif`, `siparis`,
  `irsaliye`, `fatura`, `fatura_kalem`, `cek_senet`, ve Faz 4-5'teki `beyanname`,
  `demirbas` vb. — istisnasız.
- **Hareket/günlük tabloları ayrı `sube_id` taşımaz;** şubeyi üst ana tablodan veya belge
  kaynağından **miras alır**:
  - `stok_hareket.depo_id → depo.sube_id`
  - `kasa_hareket.kasa_id → kasa.sube_id`
  - `banka_hareket.banka_hesap_id → banka_hesap.sube_id`
  - `cari_hareket` → `ilgili_modul`/`ilgili_kayit_id` üzerinden kaynak belgeye (Faz 2
    belgeleri `sube_id` taşıyacağı için cari hareketinin şubesi belgeden çözülür).
- **Cari kartı şube-taşıyıcı değildir:** müşteri/tedarikçi şubeler arası ortak varlıktır;
  bir cari birden çok şubeden hareket görebilir. Şube ayrımı cari'de değil, hareketin
  kaynak belgesindedir.

> Not: `banka_hesap.sube` = bankanın şubesinin ADI (metin); `banka_hesap.sube_id` =
> işletmenin şubesi (FK). İkisi farklı şeylerdir.

---

## K2 — Borç/Alacak konvansiyonu (çift taraflı muhasebe)

`bakiye = Σborç − Σalacak` — yön, cari tipine göre **ters çevrilmez**.

| Olay | Cari hareketi | Sonuç |
|---|---|---|
| Müşteriye Satış Faturası | BORÇ | müşteri bize borçlanır (bakiye +) |
| Müşteriden Tahsilat | ALACAK | borç azalır |
| Tedarikçiden Alış Faturası | ALACAK | ona borçlanırız (bakiye −) |
| Tedarikçiye Ödeme | BORÇ | borcumuz azalır |

İşaret (pozitif/negatif) "kim kime borçlu"yu söyler. Genel Muhasebe (Faz 5) bu
konvansiyonla otomatik yevmiye üretir.

---

## K3 — `ilgili_modul` / `ilgili_kayit_id` deseni

Tüm hareket tabloları (`cari_hareket`, `stok_hareket`, `kasa_hareket`, `banka_hareket`)
kaynak belgeyi bu iki alanla işaretler. Modüller arası otomatik hareket üretiminde
(örn. fatura → stok düşümü + cari hareket) bu referans zorunludur. Örnek değerler:
`Kasa`, `Banka`, `Transfer`, `Alis`, `Satis`, `Servis`, `Sayim`.

---

## K4 — Kartoteks tek kaynak

Tüm stok hareketleri tek `stok_hareket` tablosunda toplanır; Kartoteks (Bölüm 1.17)
buradan **salt-okunur** beslenir, ayrı veri girişi yapılmaz. Excel (.xlsx), CSV ve
yazdırılabilir rapor çıktısı hazırdır.

---

## K5 — Fiyat kuralı rezervi

Cari/stok/tarih bazlı dinamik fiyat/iskonto kuralları için ayrı `fiyat_kural` tablosu
kullanılacak: `stok_id`, `cari_id`/`cari_grup_id` (nullable), `baslangic_tarih`,
`bitis_tarih`, `tip` (yüzde/sabit), `deger`, `oncelik`. Mevcut `stok_kart` alan adları
bu yapıyla çakışmayacak şekilde kuruludur.

---

## K6 — Çifte veri girişi yok

Kasa/Banka hareketinde cari seçildiğinde `cari_hareket` **tek işlemle otomatik** oluşur
(ilgili_modul='Kasa'/'Banka'). Aynı kural Faz 2 belgeleri için de geçerlidir: fatura
kesilince stok + cari + kasa/banka + (Faz 5'te) yevmiye otomatik üretilir.

---

## K7 — Barkod hızlı sorgulama

`stok.barkod_bul()` yardımcısı, Faz 2'de Fatura/İrsaliye/Sipariş satır girişinde barkod
okutulduğunda satırı otomatik getirmek için kullanılacaktır.

---

## K8 — Belge zinciri geri izlenebilirliği (doğrudan FK)  ⭐

Amaç: "Bir faturadan geriye hangi teklifle başlamıştı" sorusuna JOIN ile cevap verebilmek
(Faz 5 Finansal Analiz raporları buna dayanır). **Belge başlıkları birbirine doğrudan FK**
ile bağlanır; K3'teki `ilgili_modul`/`ilgili_kayit_id` deseni **yalnız hareket
tablolarında** (`cari_hareket`, `stok_hareket`, `kasa_hareket`, `banka_hareket`) kalır,
belge başlıklarında KULLANILMAZ.

| Alt belge | FK | Üst belge | Açıklama |
|---|---|---|---|
| `siparis.kaynak_teklif_id` | → `teklif.id` | nullable | sipariş tekliften de sıfırdan da açılabilir |
| `irsaliye.kaynak_siparis_id` | → `siparis.id` | nullable | irsaliye siparişten de açılabilir |
| `fatura.kaynak_irsaliye_id` | → `irsaliye.id` | nullable | fatura irsaliyeden de açılabilir |

- Zincir yönü tektir: `fatura → irsaliye → siparis → teklif` (en fazla 3 hop).
- **Bire-çok:** bir üst belgeden birden çok alt belge üretilebilir (örn. tek tekliften
  birden çok sipariş); her alt belge tek bir üst belgeye işaret eder.
- Faz 5 raporları (teklif→fatura dönüşüm oranı, belge bazlı kârlılık) bu FK'larla JOIN edilir.

---

## K9 — İskonto önceliği (varsayılan öneri)

Bir satıra iskonto **varsayılanı** verilirken öncelik sırası — Teklif/Sipariş/İrsaliye/
Fatura'da **ortak**:

1. `fiyat_kural` (K5) — tablo açıldığında EN ÜSTE girer (o zamana kadar sırada yoktur).
2. `stok_kart.iskonto_orani` — stoka özel iskonto (0'dan büyükse kazanır).
3. `cari_kart.iskonto_orani` — cariye özel iskonto.
4. `0` — hiçbiri yoksa.

- Öncelik yalnızca **"varsayılan öneri"yi** belirler; satır iskonto değeri sonradan elle
  değiştirilebilir (belgeye özel değer).
- Teklif modülündeki eski "yalnız cari iskontosu" davranışı bu kuralla güncellendi
  (stok özel > cari > 0).

---

## K10 — Belge dönüşümü yalnız "Onaylandı" kaynaktan  ⭐

Belgeler arası dönüşüm yalnızca kaynak belge **Onaylandı** durumundayken yapılır:

- Teklif (Onaylandı) → Sipariş
- Sipariş (Onaylandı) → İrsaliye
- İrsaliye (Onaylandı) → Fatura

"Taslak / Gönderildi / Bekliyor" ve terminal durumlar ("Reddedildi", "Süresi Doldu",
"İptal") dönüşümü **engeller**. Kural hem UI'da (dönüştürme butonu yalnız Onaylandı'da
görünür) hem de sunucu tarafında (UI bypass'a karşı) uygulanır.

Sipariş özelinde durum akışı: **Bekliyor → Onaylandı → (İrsaliye ile) Kısmi → Tamamlandı**
+ terminal **İptal**. Onay (`Bekliyor → Onaylandı`) yetki bazlıdır (Admin/Muhasebe);
müşteri siparişi onaylanırken stok rezervasyonu yapılır, iptalde rezervasyon serbest
bırakılır. `Kısmi`/`Tamamlandı` durumları İrsaliye modülü (sonraki adım) tarafından
`teslim_edilen` üzerinden otomatik türetilecektir.

---

## K11 — Teslimat durumu türetme kuralı (İrsaliye'ye devir)

Rezervasyon ve stok düşümü **her zaman siparişte seçilen `depo_id` bazında** yapılır
(asla "tüm depoların toplamı" değil). Aynı kural İrsaliye'de de geçerli: mal çıkışı
yalnızca belgedeki depodan düşülür, böylece "rezerve var ama o depoda yok" çelişkisi oluşmaz.

- `siparis_kalem.teslim_edilen` **satır bazındadır** (her satır kendi teslim miktarını tutar).
- Sipariş başlığındaki `durum` ise **tüm satırların teslim oranından** türetilir:
  1. Her satırda `teslim_edilen >= miktar` → **Tamamlandı**
  2. Değilse ve herhangi bir satırda `teslim_edilen > 0` → **Kısmi**
  3. Hiçbir satırda teslimat yoksa → **Onaylandı** (henüz sevk edilmemiş)
- Örnek: satır A tam teslim, satır B yarım teslim → başlık **Kısmi** (satır A "tam",
  satır B "yarım" görünür).

---

## K12 — Tekliften çoklu sipariş (bilinçli tasarım kararı)

K8 gereği **bir tekliften birden fazla sipariş üretilebilir** (bire-çok); kısmi kısmi
siparişe dönüştürme meşru bir iş akışıdır ve **engellenmez**. Yanlışlıkla çift tıklamayı
görünür kılmak için:

- Teklif detayında "Bu tekliften oluşturulan siparişler (N)" listesi gösterilir.
- Sipariş formu (tekliften açılıyorsa) "daha önce N sipariş oluşturuldu" bilgisini
  bilgilendirme bandında gösterir.
- Bu gösterim yalnızca bilgilendirme amaçlıdır; dönüşümü kısıtlamaz.

---

## K13 — Belge numaralandırma (yıl bazlı sıfırlanan sayaç)  ⭐

Tüm belgeler `{ÖNEK}-{YYYY}-{NNN}` biçimindedir: Teklif `TKF`, Müşteri Siparişi `SIP`,
Satın Alma Siparişi `SAP`, Satış İrsaliyesi `IRS`, Alış İrsaliyesi `IRA`, Transfer
İrsaliyesi `IRT`, Satış Faturası `SF`, Alış Faturası `AF` (Fatura Faz 2'de açılacak).

- `NNN` **o yıl + ön ek için 1'den başlayan** sıralı sayaçtır; **yıl değişince sıfırlanır**
  (2027'de `TKF-2027-001`, `IRS-2027-001`).
- Sebep: İrsaliye/Fatura **resmi belgelerdir**; Türkiye'de sıra numarası yıl içinde
  sıralıdır ve yıl başında yeniden başlar (e-Fatura/e-İrsaliye'de GİB'e bildirilecek
  numara aynı kuralı izler). Yıl, numaranın **parçasıdır** (yalnızca görsel ön ek değil).
- Sayaç `db.sonraki_belge_no` ile hesaplanır: `{ÖNEK}-{YIL}-%` kayıtlarının en büyük
  `NNN`'si + 1. Sıra boşluğu bırakmaz; belge silinmediği (yalnız İptal) için çakışmaz.

---

## K14 — Faturasız irsaliye takibi (Fatura modülü gereksinimi)  ⭐

İrsaliye **cari hareket üretmez** (mali etki Fatura'da — K2/K6). Bu yüzden sevk edilip
**faturası kesilmemiş** irsaliyelerin gözden kaçmaması sistemin sorumluluğundadır. Fatura
modülü kurulurken şunlar **şarttır**:

1. **"Faturalanmamış" filtresi/görünümü:** İrsaliye listesinde "Faturalanmamış" (onaylı,
   henüz faturaya dönüşmemiş) sekmesi veya filtresi; bu irsaliyeler görsel olarak işaretlenir
   (rozet/bant). Kural: `irsaliye.durum='Onaylandı'` ve `fatura` tablosunda
   `kaynak_irsaliye_id` olarak geçmeyen (veya kaynak fatura İptal olan) kayıtlar.
2. **Dashboard bildirimi:** "Faturasız sevk edilmiş irsaliye" sayısı dashboard'da KPI olarak
   gösterilir ve (varsa) hatırlatma bildirimi üretilir.
3. **Fatura → irsaliye bağlantısında görünürlük:** Fatura, `kaynak_irsaliye_id` üzerinden
   üretildiğinde irsaliye detayında "faturalandı" bilgisi ve fatura linki gösterilir
   (ayrı bir durum kolonu açmaya gerek yok — `fatura` tablosundan türetilir).

---

## K15 — Kısmi ödenmiş belge iptali engeli (bağlı tahsilat/ödeme)  ⭐

Fatura onayı cari hareketi (Satış→borç, Alış→alacak) `ilgili_modul='Fatura'` ile yazar.
Kasa/Banka'dan yapılan tahsilat/ödeme ise **ayrı** bir cari hareket üretir. Fatura iptali
yalnızca kendi cari hareketini silerse, ona bağlı tahsilat "sahipsiz alacak" olarak kalır.
Kalıcı ilke (Fatura **ve** Çek/Senet için geçerli):

1. **Bağlama:** Kasa/Banka tahsilat/ödeme hareketi, opsiyonel **"Bağlı Fatura"** seçimiyle
   bir faturaya bağlanır (`kasa_hareket`/`banka_hareket` üzerinde `ilgili_modul='Fatura'`,
   `ilgili_kayit_id=<fatura_id>`).
2. **Engel:** Onaylı bir fatura, kendisine bağlı Kasa/Banka hareketi varken **iptal edilemez**
   ("bu faturaya bağlı tahsilat var, önce onu düzeltin"). Kasa/Banka hareket iptali
   (`/kasa/hareket/{id}/iptal`, `/banka/hareket/{id}/iptal`) cari karşılığını da geri alır.
3. **Görünürlük:** Fatura kartında "Ödeme Durumu" bandı: bağlı hareketlerden tahsil/ödeme
   toplamı ve kalan tutar gösterilir (Satış'ta tahsilat−ödeme, Alış'ta ödeme−tahsilat).
4. **Çek/Senet:** aynı mekanizma — çek/senet iptali, kendisine bağlı Kasa/Banka hareketi
   varsa engellenir. (Çek/senetin kendi cari hareketi `ilgili_modul='CekSenet'` ile
   iptalde otomatik geri alınır.)

---

## K16 — Genel ek dosya (attachment) altyapısı  ⭐

Tek genel `ek_dosya` tablosu bütün modüllere hizmet eder; `notlar`'ın ilişkisel deseniyle
(`ilgili_tablo`/`ilgili_id`) birebir aynıdır:

- Alanlar: `ilgili_modul`, `ilgili_kayit_id`, `dosya_adi`, `dosya_yolu`, `dosya_tipi`,
  `boyut`, `yukleyen_kullanici`, `tarih`.
- Formatlar: **jpg / jpeg / png + PDF**; tek dosya limiti **15 MB**; bir kayda **birden fazla** dosya.
- Rotalar: `POST /ek/yukle` (multipart/form-data), `GET /ek/{id}` (görüntüle/indir),
  `POST /ek/{id}/sil`.
- Yetki: yükleme/silme **Admin / Muhasebe / Satış**; indirme tüm oturum açmış kullanıcılar.
- Kullanım: **Çek/Senet** (baştan; fiziksel çek/senet görüntüsü) → geriye dönük **İrsaliye**
  ve **Fatura** detayında "Ekler" bölümü → ileride Teklif/Sipariş/Cari/Servis'e aynı tablodan açılır.
- `ilgili_modul` değerleri: `Fatura`, `Irsaliye`, `CekSenet` (hazır); `Teklif`, `Siparis`,
  `Cari`, `Servis` (rezerve).
- Multipart desteği `core.Request` içine eklendi (stdlib; Python 3.13'te `cgi` kaldırıldığı
  için elle ayrıştırılır).

---

## K17 — Çek/Senet durum matrisi + vade takibi  ⭐

`cek_senet.durum` yaşam döngüsü (CHECK ile sabitlenir):
`Bekliyor → Tahsile Verildi → Tahsil Edildi → Karşılıksız` (Alınan);
`Bekliyor → Ödendi` (Verilen); `Ciro` ve `İptal` ara/terminal durumlar.

1. **Geçişler** (`bekliyor`):
   - `Bekliyor` → `Tahsile Verildi`, `Tahsil Edildi`, `Ödendi`, `Ciro`, `İptal`
   - `Tahsile Verildi` → `Tahsil Edildi`, `Karşılıksız`, `İptal`
   - `Tahsil Edildi` → `Karşılıksız`, `İptal`
   - `Karşılıksız` → `Tahsil Edildi` (sonradan tahsil), `Ciro`, `İptal`
   - `Ödendi` → `İptal`; `Ciro` → `İptal`; `İptal` → (terminal)
2. **Tip kısıtı:** `Tahsile Verildi`/`Tahsil Edildi`/`Karşılıksız`/`Ciro` yalnız **Alınan**;
   `Ödendi` yalnız **Verilen** çek/senet içindir.
3. **Cari zamanlaması (Faz 5 revize):** cari hareket artık çek/senet **alındığında/verildiğinde**
   (kayıt oluşturma) yazılır — Alınan → müşteri **ALACAK** (borcu kapanır), Verilen → tedarikçi
   **BORÇ** (borcu kapanır). `Tahsil Edildi`/`Ödendi` ek cari hareket **üretmez** (ara hesaptan
   kasaya geçiş bilanço-içi harekettir). `Karşılıksız` ve `İptal` alınıştaki cari hareketi geri alır;
   `Karşılıksız → Tahsil Edildi` alacağı yeniden yazar. (Yevmiye eşlemesi K26 md.4 ile senkron.)
4. **Vade takvimi + uyarı:** `/cek_senet/vade` ekranı portföydeki (`Bekliyor`/`Tahsile Verildi`)
   kayıtları dilimlere ayırır: **vadesi geçen**, **bugün**, **yaklaşan (≤7 gün)**, **ileriki**.
   Bildirim taraması (Teklif geçerlilik deseni — `_cek_vade_tarama`): vadesi **geçen** → `uyari`,
   vadesine **≤3 gün** kalan → `bilgi`; okunmamış aynı bildirim varsa tekrar üretilmez.

---

## K18 — Döviz Takip: para birimi + kur farkı konvansiyonu  ⭐

Temel para birimi **TL (TRY)**. Döviz Takip modülü (1.11) şu kurallarla çalışır:

1. **Tutar konvansiyonu:** `cari_hareket.borc/alacak` **daima TL karşılığı** saklanır (K2 bakiye
   hesabı TL cinsinden kalır). `para_birimi` + `doviz_kur` yalnızca izleme için yazılır.
   TL karşılığı = döviz tutarı × `doviz_kur` (TRY için kur = 1, `doviz_kur` NULL).
2. **Kur tablosu:** `doviz_kur(para_birimi, kur, tarih, kaynak)` — `kaynak` = `Manuel` / `TCMB`.
   `db.guncel_kur(conn, pb)` o tarihe kadarki son kuru döndürür (TRY → 1.0). Desteklenen birimler:
   **TRY, USD, EUR, GBP** (`config.PARA_BIRIMLERI`).
3. **TCMB entegrasyon noktası:** `POST /doviz/tcmb` TCMB `today.xml` servisini çekip USD/EUR/GBP'yi
   günceller; ağ yoksa zarifçe "manuel giriş kullanın" uyarısı verir (otomatik/manuel — 1.11).
4. **Döviz belgeleri:** Fatura, Çek/Senet, Kasa/Banka hareketi `para_birimi` + `doviz_kur` taşır;
   formda döviz seçilince kur otomatik doldurulur (elle değiştirilebilir). Döviz belgesinden üretilen
   cari hareket **tutar × kur** TL karşılığı yazılır.
5. **Kur farkı (WolvoxCloud özelliği):** döviz faturası, farklı kurdan yapılan bağlı (K15)
   tahsilat/ödemelerle kapatılırsa realize kur farkı = Σ tutar × (tahsilat kuru − fatura kuru).
   `/doviz/kur-farki` ekranı bunu hesaplar. **Kur farkı faturası KDV'ye tabidir:** `matrah` =
   |fark|, KDV oranı **kaynak faturanın kalemlerindeki oran** (tek oranlı değilse/boşsa %20);
   `genel_toplam = matrah + KDV`; cari hareket KDV dahil `genel_toplam` üzerinden işlenir.
6. **Kur farkı faturası kesim kapısı:** yalnız fatura **tamamen kapatıldığında** (kalan döviz = 0)
   kesilebilir; her kaynak fatura için **tek** kur farkı faturası üretilir (mükerrer engel).
   Parçalı/farklı kurlu tahsilatların farkı kümülatif hesaplanıp tek faturada kapatılır — erken
   (kalan > 0) ve mükerrer kesim sunucu tarafında engellenir.
7. **Karışık para birimi bakiyesi:** Kasa/Banka bakiyesi **para birimine göre ayrı** netlenir ve
   gösterilir (örn. "10.000 TL + 500 USD"); TL karşılık toplamı her hareketin kayıt kurundan
   (tutar × `doviz_kur`) hesaplanır. Farklı para birimleri asla tek sayıya toplanmaz. Yetersiz
   bakiye kontrolü ilgili para biriminde yapılır (örn. USD çıkış USD bakiyesine bakılır).
8. **Çoklu para birimi raporu:** `/doviz` ekranı her birim için güncel kur, döviz fatura/çek-senet
   adedi + TL karşılığı ve cari döviz pozisyonunu (TL neti) gösterir.

---

## K19 — Servis Takip entegrasyon kuralı  ⭐ (Faz 3, revize)

`servis_kayit` + `servis_parca` tabloları; yaşam döngüsü şöyle işler:

1. **Durum akışı (CHECK):** `Alındı → Teşhis Edildi → Onay Bekliyor → Tamir Ediliyor →`
   `Tamamlandı → Teslim Edildi`; ara terminal `İade`. Yazma rolleri **Admin/Servis/Muhasebe**;
   okuma tüm giriş yapmış roller (Faz 1 deseni).
2. **Parça fiyatı:** `servis_parca.tutar = miktar × birim_fiyat` (elde girilir; stok kartı
   satış fiyatı otomatik basılmaz).
3. **Seri no bağlantısı:** `servis_kayit.seri_no` ile `stok_seri.seri_no` eşleşirse detayda
   garanti bilgisi + bu serinin geçmiş servis kayıtları gösterilir (1.2 ↔ 1.16 entegrasyonu).
4. **Audit sırası:** tüm modüllerde olduğu gibi `audit()` **commit + close sonrası** çağrılır
   (`audit` ayrı bağlantı açar; açık transaction varken çağrılırsa "database is locked" olur).

> ⚠️ **Finansal etki mimarisi K22'de tanımlıdır** (İrsaliye→Fatura deseniyle aynı): servis
> doğrudan `cari_hareket` YAZMAZ; "Teslim Edildi" parça stoğunu düşer + **Taslak Satış Faturası**
> üretir; cari hareket bu fatura **onaylanınca** doğar (K2/K6).

---

## K20 — Seri No-Garanti kuralı  ⭐ (Faz 3)

1. **Garanti süresi ürün kartında:** `stok_kart.garanti_suresi_ay INTEGER NOT NULL DEFAULT 24`.
2. **Garanti tarihleri seri üzerinde:** `stok_seri.garanti_baslangic` / `garanti_bitis` (TEXT).
   Satılan serilere garanti tarihi elle girilir veya "başlangıç + süre(ay)"dan otomatik türetilir.
3. **Durum türetimi:** `bitis < bugün → Doldu`; `0..30 gün → Yaklaşıyor`; `>30 → Aktif`;
   tarih yok → `Yok`. Stokta duran (satılmamış) serilerde garanti henüz başlamaz.
4. **Bildirim taraması:** dashboard'da `_garanti_tarama()` (Teklif/Çek-Senet deseni):
   süresi **dolan** → `uyari`, **≤30 gün** kalan → `bilgi`; okunmamış aynı bildirim varsa
   tekrar üretilmez (`ilgili_tablo='stok_seri'`).

---

## K21 — Notlar & hatırlatma kuralı  ⭐ (Faz 3)

1. `notlar` tek tablo: `ilgili_tablo`/`ilgili_id` ile herhangi bir modüle (cari, servis, fatura…)
   ilişkilendirilebilir; boşsa serbest hızlı not.
2. **Etiketleme:** metin içinde boşlukla ayrılmış `#etiket` kelimeleri etiket sayılır
   (`etiketler` kolonunda saklanır, listede filtre/badge olarak gösterilir).
3. **Hatırlatma:** `hatirlatma` tarihi girilirse, `_hatirlatma_tarama()` (dashboard) vadesi
   geleni `hatirlatildi=1` yapıp bildirime çevirir (tekrarsız).
4. Okuma tüm roller; yazma Admin/Servis/Muhasebe (silme dâhil).

---

## K22 — Servis → Fatura zinciri (finansal etki mimarisi)  ⭐ (Faz 3 revizyonu)

Servis geliri, diğer tüm satış gelirleri gibi **yalnız Fatura üzerinden** cariye yansır
(proje komutundaki "tamamlanan servis → Fatura modülünde işçilik+parça faturası taslağı"
— Odoo'daki "anında fatura taslağı" mantığı).

1. **Teslim Edildi** (yalnız bir kez): durum geçişi sırasında
   - **Stok düşümü:** her parça kendi `servis_parca.depo_id`'sinden (varsayılan: Servis
     Yedek Parça deposu) `stok._hareket_olustur(..., 'Servis Tüketimi', -adet)` ile düşülür (K11).
   - **Taslak Satış Faturası:** faturalanacak tutar > 0 ise (`fatura.kaynak_servis_id` → servis.id,
     K8 deseni) **Taslak** olarak üretilir. Cari hareket yazılmaz.
   - Garanti kapsamında / ücretsiz ise tutar 0 → fatura üretilmez.
2. **Fatura kalemleri:** parça satırları kendi stok kartından (KDV oranı stok kartından,
   iskonto K9 önceliğiyle); **işçilik** ayrı bir "hizmet" stok kartıyla (`stok_kart.tip='Hizmet'`,
   seed kodu `HZM-SRV-ISCLK`) faturaya girer. `ara_toplam/kdv_toplam/genel_toplam` mevcut
   formülle hesaplanır.
3. **Mali etki:** fatura **onaylandığında** mevcut K2/K6 akışıyla `cari_hareket` (Satış → BORÇ,
   KDV dahil `genel_toplam`) doğar; **iptalde geri alınır** (K15 deseni).
4. **Faturala butonu:** "Tamamlandı" veya "Teslim Edildi" ama faturasız kalan servisler
   (K14 "faturasız irsaliye" deseni) detaydan `POST /servis/{id}/faturala` ile taslak faturaya
   dönüştürülür; listede "Faturasız" rozeti görünür.
5. **Teslim geri alma engeli:** `Teslim Edildi`'den geri dönüş, servisin aktif faturası veya
   parça kaydı varsa **engellenir** (önce fatura iptal edilmeli — K15 benzeri).
6. **e-Fatura hazırlığı (Faz 4):** servis geliri bir `fatura` kaydına sahip olduğundan
   e-Fatura/e-Arşiv hattına sorunsuz girer; doğrudan `cari_hareket` kalıntısı yoktur.

## K23 — Giden e-Belge kuralı (e-Fatura / e-Arşiv / e-İrsaliye)  ⭐ (Faz 4)

Onaylı satış faturası/irsaliyesi, e-Dönüşüm modülünde e-belgeye dönüştürülür.

1. **Tür otomatik belirlenir:** `cari_kart.e_fatura_mukellefi` = 1 → **e-Fatura**, 0 → **e-Arşiv**
   (fatura kaynaklı). İrsaliye kaynaklı belgelerde tür daima **e-İrsaliye**'dir.
   > ⚠️ `e_fatura_mukellefi` şimdilik **elle** güncellenen statik bir bayraktır (GİB mükellefiyet
   > sorgu servisi henüz bağlı değil); kart düzenleme ekranında bu uyarı gösterilir. Gerçek
   > entegratör bağlandığında bu alan **GİB mükellefiyet sorgu servisiyle otomatik doğrulanacaktır**
   > (yanlış bayrak → mükellefe e-Arşiv / mükellef olmayana e-Fatura kesme riski).
2. **Belge no:** K13 deseni `{ÖN EK}-{YYYY}-{NNN}`; ön ekler `EF` (e-Fatura), `EA` (e-Arşiv),
   `EI` (e-İrsaliye) — `db.sonraki_belge_no` ile üretilir.
3. **Durum takibi (GİB):** `Taslak → Gönderildi → Onaylandı / Reddedildi` (+ `İptal`),
   `e_belge.durum` CHECK ile kısıtlı; `ettn` (ETN) ve `hata_mesaji` tutulur. Gönderim yalnız
   Taslak/Reddedildi durumundan, sorgulama yalnız Gönderildi durumundan yapılır.
4. **Entegratör soyut katmanı:** `Entegrator` arayüzü (`saglik/gonder/durum_sorgula/gelen_kutusu`);
   şimdilik `MockEntegrator` (sandbox) aktiftir. Gerçek API anahtarı geldiğinde **kod değişmeden**
   yalnız meta ayarları (`entegrator_saglayici`, `entegrator_api_anahtari`, `entegrator_test_modu`)
   güncellenir. Mock'ta GİB yanıtı `mock-yanit` (yalnız Admin) ile simüle edilir.
5. **e-belge mali etki ÜRETMEZ:** e-belge kaydı bir "gönderim paketidir"; cari/stok etkisi daima
   kaynak fatura/irsaliye onay akışında doğar (K2/K6). e-belge iptali/reddi kaynağı etkilemez.
6. **Ham çıktı:** UBL-TR benzeri XML, K16 `ek_dosya`'ya `ilgili_modul='EDonusum'` ile yazılır
   (`dosya_tipi='xml'`). Yeni tablo açılmaz.

## K24 — Gelen Kutusu → Alış belgesi dönüştürme kuralı  ⭐ (Faz 4)

1. **Çekme:** `POST /gelen/yenile` entegratörün `gelen_kutusu()`'nu çağırır; gelen XML
   `gelen_belge` + `ek_dosya`'ya (`ilgili_modul='GelenBelge'`) yazılır. **Dedup:** `belge_no`
   UNIQUE — aynı belge tekrar çekilmez.
2. **Okuma:** XML kalemleri (ürün/KDV/matrah) parse edilir; her kalem `stok_kart.kod` ile, yoksa
   `ad` LIKE ile eşleştirilir. Eşleşmeyen kalem `HZM-GLN-ESLESME` fallback stok kartına (aktif,
   tip 'Hizmet'; yoksa otomatik açılır) bağlanır. **Dönüştürme engellenmez**; eşleşmeyen kalemler
   flash mesajında listelenir ve kullanıcı kalemi sonradan doğru stok kartına düzeltebilir.
3. **Dönüştürme (`donustur`):** `tutar > 0` ise **Taslak** Alış Faturası (e-Fatura) veya Alış
   İrsaliyesi (e-İrsaliye) üretilir; `gelen_belge.donusum_fatura_id / donusum_irsaliye_id` FK ile
   bağlanır (K8 kaynak FK deseni), durum **Kabul**'e alınır.
4. **Mali etki YOK:** dönüştürme `cari_hareket`/`stok_hareket` YAZMAZ; etki üretilen belge kendi
   modülünde **onaylandığında** doğar (K2/K6 deseni). `Red`/`Itiraz` durumundaki belge dönüştürülemez.
5. **Belge no:** dönüştürmede `AF` (Alış Faturası) / `IRA` (Alış İrsaliyesi) ön eki K13 deseniyle.
6. **Durum seti:** `Okunmadi → Kabul / Red / Itiraz` (`gelen_belge.durum` CHECK).

## K25 — Kaynak belge iptali ↔ e-belge koruması  ⭐ (Faz 4, şartlı onay düzeltmesi)

GİB'e bildirilmiş bir belge, sistemde sanki hiç var olmamış gibi iptal edilemez (yasal zorunluluk).

1. **Engel:** `fatura`/`irsaliye` **iptal edilirken**, kendisine bağlı (`kaynak_fatura_id` /
   `kaynak_irsaliye_id`) **`Gönderildi` veya `Onaylandı`** durumunda bir `e_belge` varsa iptal
   **engellenir** (K15 deseni): "önce e-belge tarafında resmi iptal/düzeltme sürecini tamamlayın".
2. **İzin:** Yalnızca `Taslak` veya `Reddedildi` durumundaki e-belgeler varken iptale izin verilir.
3. **Öksüz temizliği:** Kaynak belge iptal edildiğinde, ona bağlı `Taslak`/`Reddedildi` e-belgeler
   otomatik `İptal`'e alınır (`hata_mesaji='Kaynak fatura/irsaliye iptal edildi'`) — öksüz taslak kalmaz.
4. **Not:** e-belgenin kendi resmi iptal/düzeltme akışı (GİB "iptal e-belgesi"), gerçek entegratör
   bağlandığında `e_belge.durum` CHECK'indeki `İptal` durumuyla eklenecektir.

## K26 — Genel Muhasebe: otomatik yevmiye üretimi  ⭐ (Faz 5)

1. **Çift kayıt zorunlu:** Fatura/Kasa/Banka/Çek-Senet mali etki doğuran her hareket, onaylandığı anda
   **yevmiye fişi** üretir (`yevmiye` + `yevmiye_kalem`); manuel çift veri girişi YOK. İptal edilen
   hareketin fişi de otomatik **geri alınır** (net sıfır — K2/K6/K15 deseni). Cari hareket + yevmiye
   **aynı bağlantı + tek `commit`** ile yazılır; fiş üretimi hata verirse transaction geri alınır →
   sahipsiz cari kaydı oluşmaz (eksik hesap kodunda `RuntimeError` fırlatılır, sessiz atlama YOK).
2. **K8 kaynak izi:** `yevmiye.kaynak_modul + kaynak_id (+ kaynak_sahne)` — dedup bu anahtarla yapılır
   (`fis_uret` idempotent). Çek/Senet sahne bazlı **çok fiş** üretir (`giris`/`tahsil`/`odeme`);
   diğer kaynaklar tek fiş (sahne NULL). Kaynaktan üretilen fiş elle durum değiştirilemez.
3. **Eşleme (Tekdüzen):**
   - Satış Faturası → 120 borç (genel) / 600 alacak (matrah) + 391 alacak (KDV)
   - Alış Faturası → 153 borç (matrah) + 191 borç (KDV) / 320 alacak (genel)
   - Kasa/Banka giriş → 100/102 borç / **cari karşı hesabı** alacak; çıkış → ters; açılış → 500.
     Cari karşı hesabı **tipine göre**: Müşteri → **120 ALICILAR**, Tedarikçi → **320 SATICILAR**
     (HerIkisi → yön bazlı: tahsilat→120, ödeme→320); cari yoksa 679 (gelir) / 632 (gider).
   - Kasa↔Banka transfer → 100↔102 (tek fiş; karşı hareket `ilgili_modul='Transfer' + ilgili_kayit_id`
     doluysa atlanır → çift kayıt olmaz).
4. **Çek/Senet ara hesapları (doğru Tekdüzen eşlemesi):** fiziksel çek eldeyken **Kasa/Banka'ya YAZILMAZ**:
   - `giris` (Alındı/Verildi): Alınan → **101/121 borç / 120 alacak**; Verilen → **320 borç / 103/321 alacak**
   - `tahsil` (Alınan Tahsil Edildi): **100 borç / 101 veya 121 alacak** (nakit ancak tahsilde girer)
   - `odeme` (Verilen Ödendi): **103/321 borç / 100 alacak**
   - `Tahsile Verildi` fiş üretmez (çek hâlâ portföyde); `Karşılıksız`/`İptal` tüm fişleri + cariyi
     geri alır (net sıfır); `Ciro` otomatik fiş üretmez (karşı taraf bilgisi modelde yok → manuel fiş
     önerilir). Hesap eşlemesi: 101 Alınan Çekler, 121 Alacak Senetleri, 103 Verilen Çekler ve Ödeme
     Emirleri, 321 Borç Senetleri.
5. **K1 — şube:** `yevmiye.sube_id` nullable taşınır; fiş kaynağının şubesinden doldurulur
   (Fatura/Çek-Senet kendi `sube_id`'si; Kasa/Banka kasa/banka hesabının şubesi). Mizan şube bazlı
   filtrelenebilir (`/muhasebe/mizan?sube_id=`). `sube_backfill` eski fişleri geri doldurur.
6. **TL esasi:** dövizli belgelerde tutarlar `tutar × doviz_kur` ile TL'ye çevrilir (K18).
7. **Dönem işlemleri:** Açılış Fişi (kasa/banka/cari bakiyeleri → fark 500 Sermaye) ve Kapanış Fişi
   (gelir/gider → 590/591) yıl bazlı idempotent üretilir. Mizan/büyük defter yalnız **Onaylandı**
   fişleri kapsar.
8. **Retroaktif:** `/muhasebe/toplu-uret` (ve açılışta `seed_muhasebe`) eksik fişleri + çek/senet
   cari karşılıklarını geriye dönük üretir; tekrar çalıştırılsa bile çift kayıt oluşmaz.

## K27 — Transfer: tek modülde konsolide görünüm + kasalar arası  ⭐ (Faz 5)

1. **Tek modül (1.18):** Depolar arası · kasalar arası · kasa ↔ banka · şubeler arası transferler
   `/transfer` ekranında tek kronolojik görünümde toplanır (transfer geçmişi).
2. **Yeni veri modeli YOK (K4/K6):** ikinci doğruluk kaynağı açılmaz; kayıtlar kendi modüllerinden
   yönetilir ve konsolide görünüm salt-okunurdur:
   - Depo transferi → `depo_transfer` (+kalem) — **Taslak → Tamamlandı onay akışı** (Stok2).
   - Kasa ↔ Banka → `kasa_hareket`/`banka_hareket` çifti — **anında**, yetersiz bakiyede tam red.
   - Kasa → Kasa → `kasa_hareket` çifti: `Kasa Transferi (Çıkış)` (kaynak, CIKIS) +
     `Kasa Transferi (Giriş)` (hedef, GIRIS), `ilgili_modul='Transfer'` + `ilgili_kayit_id` bağıyla.
3. **GM etkisi:** kasa ↔ banka tek fiş (K26); **kasa → kasa fiş ÜRETMEZ** (100 hesabı içi net sıfır —
   fiş oluşursa Kasa bakiyesi mükerrer sayılır). Çıkış/giriş kayıtları GM'de çift sayılmaz.
4. **Şubeler arası:** kaynak ve hedef varlığın `sube_id`'si farklıysa "Şubeler Arası" işaretlenir
   (depo/kasa/banka `sube_id` taşır — K1).
5. **İptal:** transfer hareketleri tek başına iptal edilemez; ayrı bir "tam transfer iptali" rotası
   da yoktur — transfer bir kez kaydedildikten sonra kalıcıdır ve yalnızca ters yönde yeni bir
   transferle düzeltilir (kasa→kasa ve kasa↔banka için aynı davranış; iki bacağı da engellidir).
   Depo transferleri kendi Taslak→Tamamlandı akışında yönetilir.

## K28 — Finansal Analiz: türetilmiş analitikler + tek yeni tablo (bütçe)  ⭐ (Faz 5)

1. **Salt-okunur analitikler (K4/K6):** satış/kâr-zarar/nakit akışı/ürün/tahsilat/servis grafikleri
   kaynak tablolardan **canlı türetilir** — ayrı veri girişi ve ayrı toplam tablosu yoktur.
2. **Kaynak eşlemesi:** satış → `fatura` (Onaylandı, `ara_toplam × doviz_kur`); kâr-zarar → **iki
   satır**: (a) GM Gelir/Gider hesap bakiyeleri (net, dönem kapanışına kadar geçici) ve (b)
   **tahmini brüt kâr (COGS dahil)** = fatura kalemi cirosu − (adet × güncel `stok_kart.alis_fiyat`);
   nakit akışı → `kasa_hareket`+`banka_hareket` (**transfer ve açılış bakiyesi hariç** — mükerrer
   sayım yok); ürün → `fatura_kalem`; tahsilat → `cari_hareket` (bakiye = Σborç − Σalacak);
   servis → `servis_kayit`+`servis_parca`.
3. **Tek yeni tablo `butce`:** Odoo bütçe mantığı (yıl+ay+tip Gelir/Gider+hedef tutar); analitiklerle
   değil, yalnızca bütçe hedefiyle ilgilidir. Yazma Admin/Muhasebe; okuma tüm roller.
4. **Para birimi:** tüm seriler TL karşılık hesaplanır; dövizli fatura kalemlerinde birim fiyat
   fatura kuruyla TL'ye çevrilir (karma para birimi hatası önlenir).
5. **"En kârlı" tahminidir:** tarihsel maliyet yok; güncel `stok_kart.alis_fiyat` kullanılır ve
   ekranda bu varsayım açıkça belirtilir.

## K29 — Beyanname: salt-okunur vergi hazırlık raporları  ⭐ (Faz 5)

1. **Salt-okunur (K4/K6), GİB gönderimi yok:** `/beyanname` + `/beyanname/denetim` +
   `/beyanname/denetim/csv` yalnızca okur; mali müşavire aktarılabilir çıktı üretir (ekran +
   yazdırma + CSV). Yeni veri modeli yoktur.
2. **Kaynak eşlemesi:** KDV tahakkuk → `fatura`+`fatura_kalem` (onaylı, KDV × `doviz_kur`);
   nakit esaslı → cari bazında tahsilat/ödeme oranı (`cari_hareket` **çek/senet hariç** — henüz
   nakde dönüşmemiş); Geçici Vergi → **Tahmini Brüt Kâr (COGS dahil)** — K28 ile ORTAK kaynak
   (`_cogs_aylik`: fatura_kalem cirosu − adet × güncel alış; yılbaşından kümülatif; × %25 − önceki
   dönem mahsubu). GM net kârı SMM'siz olduğu için matrah olarak KULLANILMAZ; denetim raporu →
   `fatura` + `yevmiye` 391/191 çapraz doğrulama.
3. **Muhtasar:** stopaj/bordro veri modeli olmadığından boş şablon + açıklama; kaynak eklenince
   otomatik dolar (şimdilik kapsam dışı).
4. **Faz 4'ten taşınan açık noktalar:** eşleştirilmemiş `gelen_belge` (`donusum_fatura_id` boş)
   "müşavire ayrı liste" olarak işaretlenir; kur farkı/sabit %20 KDV fallback sonuçları KDV oran
   dağılımında görünür kılınır.
5. **Geçici vergi oranı %25** sabit alınır; matrah = tahmini brüt kâr (COGS dahil) — TAHMİNİDİR,
   kesin matrah dönem kapanışında netleşir (ekranda "tahmini" rozetiyle belirtilir). **Zarar kuralı:**
   vergiye tabi matrah 0'ın altına inemez (max(0, matrah)); asla negatif vergi üretilmez; zarar yıl
   içi kümülatif matrahtan otomatik düşer, yıllar arası devir dönem kapanışında netleşir. KDV
   devreden hesabı saf fonksiyondur (`_devreden_satirlar`) ve İndirilecek > Hesaplanan ay
   senaryosuyla kümülatif doğrulanır.

## K30 — Demirbaş: sabit kıymet + normal amortisman + zimmet  ⭐ (Faz 5)

1. **Yeni veri modeli (meşru):** Demirbaş daha önce hiçbir yerde tutulmadığından 4 tablo açılır
   (K4/K6'nın "ikinci doğruluk kaynağı açma" kuralı ihlal edilmez): `demirbas_kategori`,
   `demirbas`, `demirbas_amortisman`, `demirbas_zimmet`.
2. **Amortisman = normal (eşit paylı, VUK):** aylık pay = (maliyet − hurda) ÷ (ömür × 12). Ömür:
   kategori varsayılanı + kart bazlı düzeltme (`omur_yil` NULL = kategori). Maliyet KDV hariçtir;
   kıst (ay kesri) uygulanmaz, ilk tam ay alış ayıdır.
3. **GM entegrasyonu (K26):** her aylık amortisman 770 (borç) / 257 (alacak) fişi üretir —
   `kaynak_modul='Demirbas'`, `kaynak_id=demirbas.id`, `kaynak_sahne=donem` (idempotent; aynı dönem
   iki kez yazılmaz). Silme fişleri de geri alır.
4. **Tetik:** elle "Amortisman Üret" (POST) + aylık otomatik (Admin/Muhasebe `/demirbas`'ı açınca
   eksik aylar üretilir — cron yok, kapanış akışı). Üretim yalnızca **Aktif** kartlar içindir.
5. **Zimmet:** kartta güncel (`zimmetli_kullanici_id` + `sube_id`, K1) + `demirbas_zimmet` geçmişi
   (Teslim/Devir/İade). Çıkış (Satıldı/Hurda) amortismanı durdurur; net değer mahsubu manueldir.
6. **Tutarlılık kilidi:** amortisman üretilmiş kartta maliyet/ömür/alış tarihi/kategori
   değiştirilemez (GM fişleriyle çelişmemesi için).

## K31 — Faz 6 Cila: şube izolasyonu + bildirim sağlayıcı  ⭐ (Faz 6, son)

1. **Şube izolasyonu (K1 açılışı):** `core.izole_sube(req)` Admin olmayan ve şubeye atanmış
   kullanıcının `sube_id`'sini; `core.sube_koruma(req, kayit_sube)` erişim hakkını döndürür.
   Şubeli kullanıcı yalnız kendi şubesini görür/yazar; oluşturduğu kayıtlar kendi şubesine yazılır;
   başka şubenin kaydına erişim **403**. Uygulanan: Kasa, Banka, Teklif, Sipariş, İrsaliye, Fatura,
   Çek/Senet (+vade), Servis, Demirbaş (+amortisman), GM (yevmiye/mizan/defter), Stok depoları.
   **Cari kartlar bilinçli ortak** (merkez havuz); hareketler üst belgenin şubesini miras alır.
2. **Bildirim sağlayıcı:** soyut `bildirim_saglayici.Saglayici` + `MockSaglayici` (entegratör
   deseni); kanal `meta('bildirim.kanal')` = kapali/sms/eposta; gönderimler `bildirim_gonderim`
   günlüğüne yazılır. `core.notify(..., hedef=, kanal=)` dış gönderimi tetikler. Servis
   `Tamamlandı` → "cihazınız hazır" bildirimi (GSM öncelikli, sonra e-posta).
3. **Cari vade uyarısı:** `_cari_vade_tarama()` ödenmemiş/vadesi geçen cari bakiyesi için uyarı
   üretir (idempotent: okunmamış bildirim varken tekrar üretmez). Diğer taramalarla aynı desen.
4. **Tutarlılık:** yeni tablo yalnız `bildirim_gonderim` (günlük) — K4/K6 korunur; antet bilgisi
   `firma` tablosundan türetilir; rota/rol matrisi `/yetkiler` + `docs/yetki-matrisi.md`'de.

## K32 — Faz 6.1: Sistem Yönetimi (Ayarlar)  ⭐ (Faz 6.1)

1. **Tek merkez:** Kullanıcı yönetimi, firma bilgileri, bildirim kanalı ve e-belge entegratör
   ayarları **`/ayarlar`** altında toplanır (yalnız Admin). Eski yollar (`/bildirimler/ayarlar`,
   `/edonusum/ayarlar`) yeni ekranlara yönlendirir.
2. **Silme yok, pasifleştirme var:** Kullanıcı silinmez; `aktif=0` yapılır (audit geçmişi korunur).
   Kendini pasifleştirme ve son aktif yöneticiyi pasifleştirme engellenir.
3. **Şifre güvenliği:** Şifreler PBKDF2-HMAC-SHA256 (tuzlu, 600k yineleme) ile saklanır; düz metin
   asla (audit detayına bile yazılmaz). Eski salted SHA-256 hash'leri girişte otomatik yükseltilir.
   Yeni/sıfırlanan şifre **en az 8 karakter + en az bir rakam**; şifre değişimi diğer oturumları geçersiz kılar.
4. **Şifre değiştirme (kendi hesabı) tüm rollere açık** (`/profil/sifre`, üst çubuk 🔑);
   Admin başka kullanıcının şifresini sıfırlayabilir (kendi rolünü değiştiremez).
5. **Firma düzenlemesi** `firma` tablosunu günceller ve `core.firma()` önbelleğini temizler
   (antet/PDF anında yansır).

## K33 — Manuel (serbest metin) satır: stoğa bağlı olmayan belge satırı  ⭐ (Faz 6.1 sonrası)

Fatura ve irsaliyeye, stoğa bağlı olmayan **serbest metin** satır eklenebilir. Bu, K4/K6'daki
"her satır bir stok kartına bağlı" varsayımından **bilinçli bir sapmadır**; stoklu satırlar
bozulmadan **yanına ek seçenek** olarak kurulur.

1. **İşaretleme:** `fatura_kalem.stok_id` / `irsaliye_kalem.stok_id` **nullable** — `NULL` = manuel
   satır; dolu = mevcut davranış (barkod, K9 iskonto, stok düşümü, K11) aynen çalışır. Serbest
   metin `…_kalem.aciklama` alanında saklanır (stoklu satırda NULL).
2. **Manuel satır alanları:** açıklama/ad, miktar, birim fiyat, KDV oranı, iskonto oranı — hepsi
   elle girilir; stok kartından hiçbir şey otomatik gelmez.
3. **Stoğa kesinlikle dokunmaz:** `stok_hareket` üretilmez, `stok_seviye`/`rezerve` değişmez;
   irsaliye depo bazlı düşüm, rezervasyon serbest bırakma ve sipariş `teslim_edilen` güncellemesi
   yalnız `stok_id` dolu satırlarda yapılır (`irsaliye._stok_kontrol_ve_uygula`,
   `_siparis_teslim_kontrol` manuel satırları atlar).
4. **Toplamlar:** ara toplam / iskonto / KDV / genel toplam hesabına dahildir.
5. **K9 geçerli DEĞİL:** manuel satırda iskonto, kullanıcının doğrudan girdiği değerdir; stok/cari
   iskonto oranı otomatik uygulanmaz.
6. **Transfer'de yasak:** Transfer irsaliyesinde manuel satır eklenemez (formda çubuk gizli +
   sunucu tarafı red; Transfer cari taşımadığı için anlamı da yoktur).
7. **Yevmiye (K26 genişlemesi):** Fatura onayında hâlâ **tek fiş** üretilir. Hesap eşlemesi:
   **Satış → 600** (manuel satırlar dahil) · **Alış → stoklu satırlar 153, manuel satırlar 770**
   (Genel Yönetim Giderleri); KDV yine 391 (Satış) / 191 (Alış); karşı cari 120/320. Fiş dengeli kalır.
8. **Sınırlama (bilinçli):** manuel satır stok hareketi üretmediği için **Kartoteks**'te (K4)
   görünmez; yalnız belge ve muhasebe fişinde izlenir.


## K34 — Satır ekleme akışı: satır içi yazma + canlı arama  ⭐ (2026-09-08)

Fatura ve irsaliye formlarında satır ekleme, WolvoxCloud/Akınsoft deseniyle yeniden kuruldu:
"önce seç, sonra ekle" yerine **kalemler tablosundaki `+` boş satır açar; kullanıcı satırın
içine yazarak doldurur.** Stoklu/manuel ayrımını kullanıcı seçmez — sistem **metin eşleşmesine
göre kendisi karar verir.**

1. **`+` = sınırsız boş satır:** her tıklama yeni boş satır açar; sınır yok. Form gönderilirken
   boş satırlar atılır.
2. **Ürün hücresi canlı arama:** yazarken `GET /api/stok/ara?q=` ile stok kartlarında **Stok Adı
   ve Stok Kodu** (ayrıca barkod) aranır; 170 ms debounce; Enter ilk öneriyi seçer; ↑/↓ + Enter
   ile seçim; Esc kapatır. Öneri listesinde kod + ad + fiyat + kalan stok görünür.
3. **Otomatik karar (stoklu / manuel):**
   - Listeden stok **seçilirse** (tık/Enter) → stoklu satır: barkod/KDV/satış fiyatı otomatik,
     K9 iskonto önceliği ve stok düşümü normal çalışır (K33 öncesi davranış).
   - Yazılan metin **hiçbir stokla eşleşmiyorsa** (tam kod/barkod/ad dahil) → satır otomatik
     **manuel** (`stok_id NULL`, K33): metin `aciklama` olur, fiyat/KDV elle girilir.
   - **Stable guard:** bir satır çözümlendikten sonra (`settled`) tekrar çözümlenmez — böylece
     tam kod + Enter ile seçilen stok, kullanıcı başka hücreye geçince yanlışlıkla manuele
     dönmez. Yalnız yeni yazım (`input`) satırı yeniden çözüme açar.
4. **Cari de yazarak aranır:** sabit dropdown yok; `GET /api/cari/ara?q=&tip=` ile unvan/kod
   üzerinden canlı arama; tip filtresi belge tipine (Satış/Alış) uyar. Seçim cari id + etiket +
   cari iskonto oranını uygular.
5. **Kısıtlar:** Transfer irsaliyesinde manuel yasak (K33.6) — `data-manuel-yasak="1"`, cari
   alanı gizli, tip değişimi formu otomatik gönderir.
6. **Uygulama noktaları:** `api.py` (`/api/stok/ara`, `/api/cari/ara`), `static/js/form-satir.js`
   (ortak motor), `fatura.py`/`irsaliye.py` (`_cari_secim`), iki `form.html` şablonu. Form
   sözleşmesi: `data-belge`, `data-tip`, `data-manuel-yasak`, `#cari-ara/#cari-id/#cari-list`,
   `#kalemler-body`, `#satirlar-data` (JSON), `#satir-ekle`, `#satir-bos`,
   `#t-ara/#t-isk/#t-kdv/#t-genel`.
7. **Test:** `test_form_satir.js` (16), `test_form_satir2.js` (6), `test_form_satir3.js`
   (uçtan uca kayıt) jsdom ile geçti; `test_manuel_satir.py` regresyonu 28/28 korundu.

## K35 — Belge kalemi birim + görünen ad; hareket/cari görünümleri; sürüm takibi  ⭐ (2026-09-08)

K34 (satır içi yazma) üzerine kurulan tamamlayıcı kurallar:

1. **Birim (kalem bazlı):** `fatura_kalem.birim` / `irsaliye_kalem.birim` (nullable). Stoklu satırda
   stok kartındaki birim otomatik gelir; manuel satırda kullanıcı açılır listeden seçer
   (Adet, Kutu, Paket, Çift, Takım, Metre, m², Kg, Lt, Top, Rulo — `stok.BIRIMLER`).
   Dolu değilse görünümde `stok_kart.birim` → `Adet` düşer.
2. **Görünen ad (`goruntu_adi`):** kalem başına, boşsa **stok kartındaki gerçek ad** gösterilir;
   doldurulursa **yalnız o belgede** (detay + yazdır) bu ad görünür. Stok kartı, Kartoteks ve
   Genel Muhasebe her zaman gerçek stok adını kullanır — override yalnız belge görünümünü etkiler.
3. **Cari ekstre filtreleri (Kartoteks → Cari):** Özet/Detaylı görünüm (detay: fatura/irsaliye
   kalemleri açılır, `gorunen_ad` ile), fiyat göster/gizle, KDV dahil/hariç (fatura hareketinde
   `kdv_toplam` düşülerek gösterilir — `cari_hareket`'e dokunulmaz, yalnız görünüm). PDF/Excel/CSV
   ham ledger'dan üretilir (K4 korunur).
4. **Stok hareketinde "kiminle":** hareketin bağlı olduğu belge (Fatura/İrsaliye) üzerinden cari
   çözülür (`stok.hareket_cari`) — ayrı veri kaynağı açılmaz. Manuel giriş/transferde boş.
5. **Alış Geçmişi (`/stok/alis-gecmisi`):** `Stok Girişi (Alış)` + `İrsaliye Girişi` hareketleri;
   firma, adet, birim fiyat, KDV dahil/hariç kıyaslama (`stok.hareket_kdv_orani`: belge kalemi →
   stok kartı). Arama ürün/kod/barkod/firma/belge no üzerinden.
6. **Stok kartında son 3 alış / son 3 satış:** stok detayında, cari ile birlikte (fiyat kıyaslama).
7. **Sürüm takibi:** `CHANGELOG.md` + `config.SURUM`/`SURUM_TARIHI` (her sayfanın alt bilgisi).
   Her geliştirme partisinde sürüm artırılır.
