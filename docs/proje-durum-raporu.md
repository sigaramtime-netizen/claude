# Brn Teknoloji ERP — Genel Rapor

**Rapor tarihi:** 07.09.2026
**Kapsam:** Elektronik / beyaz eşya / teknik servis işletmesi için web tabanlı mini-ERP
(Elektronikçi İşletme Yönetim Sistemi)
**Genel durum:** **PROJE TAMAMLANDI ✅** — Faz 1 (Çekirdek) · Faz 2 (Satış Döngüsü) · Faz 3 (Servis & Garanti) · Faz 4 (e-Dönüşüm) · Faz 5 (Mali/Analitik) · Faz 6 (Cila) — tamamı tam onay · **Faz 6.1 (Sistem Yönetimi / Ayarlar) ✅ eklendi**. Kapanış raporu: `docs/proje-kapanis-raporu.md`.

---

## 1) Yönetici Özeti

22 modül / 6 faz olarak planlanan sistemin **tüm fazları tamamlanmıştır**. **Faz 1 (Çekirdek)** —
Cari, Stok/Stok2, Kasa, Banka, Depo/Şube — **Faz 2 (Satış Döngüsü)** — Teklif → Sipariş →
İrsaliye → Fatura → Çek/Senet → Döviz Takip — **Faz 3 (Servis & Garanti)** — Servis Takip,
Seri No-Garanti, Notlar — **Faz 4 (e-Dönüşüm)** — e-Fatura/e-Arşiv/e-İrsaliye + Gelen Kutuları —
**Faz 5 (Mali/Analitik)** — Genel Muhasebe, Kartoteks, Transfer, Finansal Analiz, Beyanname,
Demirbaş — ve **Faz 6 (Cila)** — şube izolasyonu, bildirim sağlayıcısı, dashboard/mobil/PDF ince
ayarı — uçtan uca çalışır durumdadır. Faz 1–5 tam onay almıştır; Faz 6 onay paketi
`docs/faz6-ozet.md` kullanıcı onayına sunulmuştur (bkz. Bölüm 10).

- **Teknoloji:** Python 3 (standart kütüphane) + SQLite + Jinja2 + öz WSGI çekirdeği
  (harici çalışma zamanı bağımlılığı yok; Excel dışa aktarım için `openpyxl`).
- **Kapsam:** 22 modül (Faz 1–5) + genel ek-dosya altyapısı (K16) + Faz 6 cila altyapısı,
  **166 kayıtlı rota**, **52 tablo**, örnek (seed) veri seti (2 şube), 5 demo kullanıcı.
- **Kalite:** Kritik senaryolar gerçek HTTP testleriyle doğrulanmıştır (bakiye konvansiyonu,
  yetki matrisi, belge zinciri, izolasyon, kur farkı, servis teslim entegrasyonu, garanti takibi,
  e-belge üretimi/durum takibi, gelen kutusu dönüştürmesi, dışa aktarım).

---

## 2) Proje Planı ve Modül Durumu (22 modül / 6 faz)

| # | Modül (şartname) | Faz | Durum |
|---|---|---|---|
| 1.1 | Notlar | Faz 3 | ✅ |
| 1.2 | Servis Takip | Faz 3 | ✅ |
| 1.3 | Cari | Faz 1 | ✅ |
| 1.4 | Kasa | Faz 1 | ✅ |
| 1.5 | Stok / Stok2 | Faz 1 | ✅ |
| 1.6 | Fatura | Faz 2 | ✅ |
| 1.7 | Çek/Senet | Faz 2 | ✅ |
| 1.8 | İrsaliye | Faz 2 | ✅ |
| 1.9 | Teklif | Faz 2 | ✅ |
| 1.10 | Sipariş | Faz 2 | ✅ |
| 1.11 | Döviz Takip | Faz 2 | ✅ |
| 1.12 | Şube / Depo | Faz 1 | ✅ |
| 1.13 | e-Fatura / e-Arşiv / e-İrsaliye | Faz 4 | ✅ (entegratör bağlantı noktası mock ile) |
| 1.14 | e-Fatura / e-İrsaliye Gelen Kutusu | Faz 4 | ✅ |
| 1.15 | Banka | Faz 1 | ✅ |
| 1.16 | Seri No-Garanti | Faz 3 | ✅ |
| 1.17 | Kartoteks | Faz 5 | ✅ Salt-okunur kronolojik döküm (cari + stok, koşu bakiyeli) + Excel/CSV dışa aktarma + PDF rapor + barkod sorgulama |
| 1.18 | Transfer | Faz 5 | ✅ Tek modül konsolide görünüm (depo/kasa↔banka/kasalar arası) + şubeler arası işareti |
| 1.19 | Finansal Analiz | Faz 5 | ✅ Türetilmiş grafikler + bütçe (butce) + dönemsel karşılaştırma |
| 1.20 | Genel Muhasebe | Faz 5 | ✅ Otomatik yevmiye (K26) + mizan/defter + açılış/kapanış |
| 1.21 | Beyanname | Faz 5 | ✅ KDV (tahakkuk + nakit esaslı) + Geçici Vergi + Muhtasar (boş şablon) + vergi denetim raporu + CSV |
| 1.22 | Demirbaş | Faz 5 | ✅ Sabit kıymet + normal amortisman (770/257 GM fişi) + zimmet takibi |

**Çapraz altyapı (Faz 6):** rol bazlı yetkilendirme ✅ · bildirim/uyarı ✅ · SMS/e-posta mock
entegrasyon noktası ✅ · şube izolasyonu (K1 açıldı) ✅ ·
dashboard ✅ · audit log ✅ · responsive koyu tema ✅ · PDF/yazdır şablonları ✅ · mobil/tablet
uyumu 🔶 (masaüstü + tablet önceliği tamam).

---

## 3) Teslim Edilen Modüller (detay)

### Faz 1 — Çekirdek

| Modül | Özellikler |
|---|---|
| **Cari** | Kart (müşteri/tedarikçi/her ikisi), ekstre (yürüyen bakiye), FIFO yaşlandırma (30/60/90), kredi limiti + aşım uyarısı, cari grupları, ilişkisel notlar, audit log |
| **Stok** | Ürün kartı (SKU, barkod, marka, kategori, teknik özellikler), seri/lot takibi, kritik stok + otomatik bildirim, stok hareketi, sayım + sayım farkı, varyant sistemi (varyant bazlı barkod) |
| **Stok2** | Çoklu depo dağılımı, depolar arası transfer (çift yönlü), min/max stok, ürün–tedarikçi eşleştirme, toplu fiyat/iskonto güncelleme, Excel/CSV/PDF dışa aktarma, barkod hızlı sorgulama |
| **Kasa** | Çoklu kasa, nakit giriş/çıkış, açılış bakiyesi, yazdırılabilir kasa fişi, günlük rapor, **cari bağlantısı** (tek işlemle tahsilat/ödeme) |
| **Banka** | Hesap tanımları (IBAN), havale/EFT, hesap ekstresi, CSV ekstre içe aktarma, **cari bağlantısı**, kasa↔banka transfer (karşı taraf otomatik) |
| **Depo/Şube** | Şube + depo CRUD, depo–şube / kullanıcı–şube bağlama, şube bazlı raporlama, **şube bazlı veri izolasyonu** (HTTP düzeyinde test edildi) |

### Faz 2 — Satış Döngüsü (belge zinciri)

| Modül | Özellikler |
|---|---|
| **Teklif** | Durum akışı (Taslak→Gönderildi→Onaylandı/Reddedildi/Süresi Doldu), geçerlilik otomasyonu + hatırlatma, K9 iskonto önceliği, yazdır/PDF |
| **Sipariş** | Müşteri + satın alma siparişi, yetki bazlı onay, **stok rezervasyonu** (depo bazlı), onaylı tekliften tek tıkla üretim (K8/K10), yazdır/PDF |
| **İrsaliye** | Satış/alış/transfer, onaylı siparişten tek tıkla üretim, depo bazlı mal çıkış/girişi + kısmi teslim (K11), aşırı teslimat koruması, iptalde geri alma, K13 numaralandırma, yazdır/PDF |
| **Fatura** | Satış/alış faturası, onaylı irsaliyeden tek tıkla üretim, **cari hareket üretimi** (K2/K6) + iptalde geri alma, vade, K13 (SF/AF), **K14 faturasız irsaliye takibi**, **K15 kısmi ödeme iptal engeli + ödeme bandı**, **K16 ek dosya**, yazdır/PDF |
| **Çek/Senet** | Alınan/verilen çek-senet, vade + tahsil/öde, cari hareket (tek işlem, alınışta), **durum matrisi (K17)**, **Karşılıksız → cari geri alma**, **vade takvimi + yaklaşan vade uyarısı**, **GM ara hesap fişi (K26: 101/121/103/321)**, K15 engeli, **K16 fiziksel görüntü**, portföy özeti, yazdır |
| **Döviz Takip** | Kur yönetimi (manuel + **TCMB entegrasyonu**), döviz cinsi fatura/çek-senet/kasa-banka, cari hareketler **TL karşılığı**, **kur farkı izleme + otomatik kur farkı faturası**, çoklu para birimi raporu |

### Faz 3 — Servis & Garanti

| Modül | Özellikler |
|---|---|
| **Servis Takip** | Servis kaydı (cihaz, seri no, arıza, aksesuar, teknisyen), 7 durumlu akış (Alındı→…→Teslim Edildi/İade), yedek parça ekleme (stoktan + depo seçimi), **Teslim = stok düşümü (Servis Tüketimi, depo bazlı) + Taslak Satış Faturası**; **mali etki fatura onayında** (K22 — İrsaliye→Fatura deseniyle aynı, KDV'li), "Faturala" butonu (K14 deseni), teslim geri alma engeli, seri no → garanti/geçmiş eşleşmesi, ilişkisel notlar, audit |
| **Seri No-Garanti** | Satılan serilerin garanti başlangıç/bitiş takibi, ürün bazlı `garanti_suresi_ay` (24 varsayılan), garanti durumu (Aktif/Yaklaşıyor≤30g/Doldu/Yok), **garanti bildirim taraması** (dolan→uyarı, yaklaşan→bilgi), satış + servis geçmişi |
| **Notlar** | Bağımsız hızlı not defteri: etiket (#öncelikli…), tarihli **hatırlatma → otomatik bildirim**, cari/servis/faturaya ilişkisel not |

---

## 4) Mimari Sözleşme (bağlayıcı kurallar — `docs/mimari-kurallar.md`)

| Kural | İçerik |
|---|---|
| **K1 — Şube ön-hazırlığı** | `depo`, `kasa`, `banka_hesap`, `kullanici` nullable `sube_id` taşır; Faz 2+ belge tabloları baştan `sube_id` ile açılır; hareket tabloları şubeyi üst tablodan miras alır. Faz 6'da yalnızca izolasyon açılır; migrasyon gerekmez. |
| **K2 — Borç/Alacak** | `bakiye = Σborç − Σalacak`; müşteri pozitif, tedarikçi negatif. Alış Faturası → Alacak, Ödeme → Borç. |
| **K3 — Belge referansı** | `ilgili_modul` / `ilgili_kayit_id` tüm hareket tablolarında tutarlı. |
| **K4 — Kartoteks** | Tek `stok_hareket` tablosu salt-okunur Kartoteks kaynağı. |
| **K5 — Fiyat kuralı** | Ayrı `fiyat_kural` tablosu (ileride); mevcut alanlarla çakışmaz. |
| **K6 — Çifte veri yok** | Kasa/Banka'da cari seçilince `cari_hareket` tek işlemle otomatik; Faz 2 belgeleri de öyle. |
| **K7 — Barkod** | `stok.barkod_bul()` belge satır girişinde barkod okutunca satırı getirir. |
| **K8 — Belge zinciri** | Doğrudan FK: `siparis.kaynak_teklif_id`, `irsaliye.kaynak_siparis_id`, `fatura.kaynak_irsaliye_id` (nullable). |
| **K9 — İskonto önceliği** | `fiyat_kural` → `stok_kart.iskonto_orani` → `cari_kart.iskonto_orani` → 0. |
| **K10 — Durum kuralı** | Dönüşüm yalnız **Onaylandı** kaynaktan; UI + sunucu çift kontrol. |
| **K11 — Depo bazlı rezervasyon/düşüm** | Rezervasyon/düşüm seçilen `depo_id` bazında; `teslim_edilen` satır bazında; başlık durumu teslim oranından türetilir. |
| **K12 — Tekliften çoklu sipariş** | Bir tekliften çok sipariş serbest; bilgilendirme bantları. |
| **K13 — Belge numaralandırma** | `{ÖNEK}-{YYYY}-{NNN}`; yıl değişince NNN sıfırlanır (TKF, SIP/SAP, IRS/IRA/IRT, SF/AF). |
| **K14 — Faturasız irsaliye takibi** | Sevk edilip faturalanmayan irsaliyeler görünür kalır (filtre + rozet + dashboard KPI). |
| **K15 — Kısmi ödenmiş belge iptali** | Bağlı tahsilat/ödeme varken fatura/çek-senet **iptal edilemez**; önce hareket iptal edilir. |
| **K16 — Genel ek dosya** | Tek `ek_dosya` tablosu (jpg/png + PDF); Çek/Senet, İrsaliye, Fatura'da "Ekler". |
| **K17 — Çek/Senet durum matrisi + vade** | 7 durum; cari hareket alınışta yazılır (Faz 5); `Karşılıksız`/`İptal` geri alır; vade takvimi + yaklaşan vade uyarısı. |
| **K18 — Döviz Takip** | Temel para birimi TL; cari tutarlar daima TL karşılığı. `doviz_kur` (Manuel/TCMB) + `db.guncel_kur()`. **Karışık para birimi bakiyesi para birimine göre ayrı netlenir (asla tek sayıya toplanmaz).** **Kur farkı faturası KDV'ye tabidir** (kaynak faturanın KDV oranı; matrah + KDV = genel). TCMB `today.xml` entegrasyon noktası + çoklu para birimi raporu. |
| **K19–K22 — Servis & Garanti** | Servis akışı (7 durum), teslim = depo bazlı stok düşümü + Taslak Satış Faturası, **mali etki fatura onayında** (K22); garanti süre türetimi; ilişkisel notlar. |
| **K23–K24 — e-Dönüşüm** | Giden tür otomatik (mükellefiyet bayrağı), GİB durum takibi (`Taslak→Gönderildi→Onaylandı/Reddedildi`), soyut entegratör (mock ↔ gerçek meta ile), ham XML `ek_dosya`'ya; gelen kutusu dedup + K8 dönüştürme (Taslak Alış belgesi, mali etki onayda) + eşleşmeyen kalem fallback kartı. |
| **K25 — Kaynak iptal ↔ e-belge** | **Gönderildi/Onaylandı** e-belgesi olan fatura/irsaliye **iptal edilemez** (K15 deseni, yasal koruma); Taslak/Reddedildi e-belge engel değil, iptalde otomatik `İptal`'e alınır. |
| **K26 — Genel Muhasebe** | Fatura/Kasa/Banka/Çek-Senet → otomatik yevmiye (tek işlem + tek commit; net sıfır). **Çek/senet ara hesapları 101/121/103/321** (çek eldeyken Kasa/Banka'ya yazılmaz); cari karşı hesabı tipe göre 120/320; `yevmiye.sube_id` (K1) + şube bazlı mizan; transfer tek kayıt; açılış/kapanış fişi; retroaktif + idempotent. |

---

## 5) Veri Modeli (52 tablo)

| Grup | Tablolar |
|---|---|
| Çekirdek | `kullanici`, `sessionler`, `firma`, `meta`, `audit_log`, `bildirimler` |
| Cari | `cari_grup`, `cari_kart`, `cari_hareket`, `notlar` |
| Stok / Stok2 | `kategori`, `marka`, `stok_kart`, `stok_varyant`, `stok_seviye`, `stok_hareket`, `stok_seri`, `stok_sayim`, `stok_sayim_kalem`, `stok_tedarikci` |
| Depo / Şube | `depo`, `depo_transfer`, `depo_transfer_kalem`, `sube` |
| Kasa / Banka | `kasa`, `kasa_hareket`, `banka_hesap`, `banka_hareket` |
| Faz 2 belgeleri | `teklif`, `teklif_kalem`, `siparis`, `siparis_kalem`, `irsaliye`, `irsaliye_kalem`, `fatura`, `fatura_kalem`, `cek_senet` |
| Faz 3 servis | `servis_kayit`, `servis_parca` |
| Faz 4 e-Dönüşüm | `e_belge`, `gelen_belge` |
| Döviz | `doviz_kur` |
| Genel altyapı | `ek_dosya` |
| Faz 5 — Genel Muhasebe | `hesap`, `yevmiye`, `yevmiye_kalem` |
| Faz 5 — Finansal Analiz | `butce` |
| Faz 5 — Demirbaş | `demirbas_kategori`, `demirbas`, `demirbas_amortisman`, `demirbas_zimmet` |
| Faz 6 — Cila | `bildirim_gonderim` (SMS/e-posta gönderim günlüğü) |

> Faz 5/6 notu: **Kartoteks, Transfer, Finansal Analiz grafikleri ve Beyanname türetilmiş görünümlerdir** —
> yeni tablo açılmaz (mevcut tablolardan hesaplanır); yalnız GM (3) + bütçe (1) + Demirbaş (4) +
> bildirim gönderim günlüğü (1) yeni tablo ekler.

> Faz 3 revizyon kolonları: `fatura.kaynak_servis_id` (K22), `servis_parca.depo_id` (K11),
> `stok_kart.tip` (`Urun`/`Hizmet`).
> Faz 4 kolonları: `cari_kart.e_fatura_mukellefi` (giden tür otomatik), `e_belge.durum` CHECK
> (`Taslak/Gönderildi/Onaylandı/Reddedildi/İptal`), `gelen_belge.durum` CHECK
> (`Okunmadi/Kabul/Red/Itiraz`), `gelen_belge.donusum_fatura_id/donusum_irsaliye_id` (K8).

---

## 6) Rota Özeti (166 kayıtlı rota)

| Modül | Rota | Modül | Rota |
|---|---|---|---|
| Genel (giriş/dashboard/bildirim/yetki) | 9 | Teklif | 6 |
| Cari | 9 | Sipariş | 6 |
| Stok / Stok2 | 19 | İrsaliye | 6 |
| Kasa | 6 | Fatura | 6 |
| Banka | 6 | Çek/Senet | 7 |
| Depo/Şube | 5 | Döviz Takip | 6 |
| Ek dosya (K16) | 3 | Servis Takip | 8 |
| Seri No-Garanti | 4 | Notlar | 3 |
| e-Dönüşüm | 13 | Kartoteks | 7 |
| Genel Muhasebe | 10 | Transfer | 1 |
| Finansal Analiz | 5 | Beyanname | 3 |
| Demirbaş | 9 | Sistem Yönetimi (Ayarlar) | 9 |
| **Toplam** | **166** | | |

Yetki modeli: okuma uçları tüm rollerde; yazma uçları role özel (Cari yazma Admin/Muhasebe/Satış;
Stok yazma Admin/Muhasebe/Depo; Banka yazma Admin/Muhasebe; Şube yönetimi ve **Ayarlar** yalnız Admin;
şifre değiştirme herkesin kendi hesabı için; Döviz kuru/fark yazma Admin/Muhasebe).

---

## 7) Doğrulanan Kritik Senaryolar (gerçek HTTP testleri)

- **Cari:** FIFO yaşlandırma; müşteri pozitif / tedarikçi negatif bakiye; kredi limiti uyarısı;
  yaşlandırma ve dashboard alacağı yalnız müşterileri kapsar.
- **Stok:** seri no yaşam döngüsü (Stokta→Satıldı); sayım farkı → hareket; transfer çift yönlü;
  kritik stok bildirimi; varyant barkodu; barkod → kart/varyant yönlendirme; Excel içerik doğrulaması.
- **Kasa/Banka:** cari bağlantılı tahsilat/ödeme; kasa↔banka transferde karşı taraf otomatik +
  **yetersiz bakiyede tam red** (yarım kayıt oluşmaz); CSV ekstre içe aktarma.
- **Şube izolasyonu:** şubeli kullanıcı yalnız kendi şubesini/deposunu görür; yönetim 403; Admin tam görür.
- **Belge zinciri:** K8 FK'ları, K10 "yalnız Onaylandı" engeli, K11 depo bazlı rezervasyon/düşüm +
  kısmi teslim, K13 numaralandırma HTTP ile doğrulandı. İrsaliye yalnız `stok_hareket` üretir;
  Fatura `cari_hareket` üretir; **aşırı teslimat koruması** ve **K14 faturasız irsaliye** çalışıyor.
- **K15:** faturaya bağlı tahsilat varken fatura iptali engellendi; hareket iptali sonrası serbest —
  net sıfır doğrulandı.
- **K16:** multipart yükleme → `ek_dosya` + disk dosyası; `/ek/{id}` indirme; "Ekler" bölümü.
- **K17:** çek alındığında → ALACAK cari hareketi (tahsil/ödeme ara hesaptan kasaya geçer); iptalde geri
  alma; durum matrisi; vade uyarıları. (Faz 5 revize: cari zamanlaması alınışa çekildi — K26 md.4.)
- **K18:** TCMB'den gerçek kur çekimi (USD 48,4336 / EUR 56,2864 / GBP 65,659); USD fatura
  (BELGE-NNN, 2.400 USD @ 48,44) → cari borç 116.256,00 TL; USD tahsilat @ 48,60 → kur farkı
  **384,00 TL** doğru; kur farkı faturası + mükerrer engel; USD çek-senet tahsili → TL cari alacak;
  Kasa USD / Banka EUR döviz hareketleri → TL karşılık cari hareket.
- **Faz 3 — Servis (revize):** `POST /servis/2/durum → Teslim Edildi` → `stok_hareket`
  "Servis Tüketimi" −1 (depo 3) + `stok_seviye` 10→9; **cari hareket yazılmadı**; **Taslak
  Satış Faturası** üretildi (matrah 690 + KDV 138 = **828,00 TL**, parça + hizmet kalemleri);
  **fatura onayı** → cari borç 828,00 TL; **fatura iptali** → geri alındı; **teslim geri alma
  engeli**; "Faturala" butonu; garanti/ücretsiz servis faturalanmadı; **rol:** depo yazamıyor
  (403), servis yazabiliyor (200).
- **Faz 3 — Garanti:** başlangıç + süre → bitiş otomatik (07.09.2026 + 12 ay = 07.09.2027);
  satılan serilerde Aktif/Yaklaşıyor/Doldu türetimi; seri no ile servis geçmişi çapraz bağlantı.
- **Faz 3 — Notlar:** ilişkisel `servis_kayit|2` ayrıştırması; etiket ve hatırlatma alanları;
  silme ve audit.
- **Faz 4 — Giden e-belge:** mükellef müşteriye onaylı fatura → `BELGE-NNN` (otomatik e-Fatura);
  gönderim → `Gönderildi` + ETN; sorgu (mock) → `Onaylandı`; mock red → `Reddedildi` + `hata_mesaji`;
  e-İrsaliye `BELGE-NNN` (tur sabit); belge no K13 deseni `EF/EA/EI-2026-NNN`.
- **Faz 4 — Gelen kutusu:** yenile 2 kez → dedup (2 belge); e-Fatura → **Taslak** `BELGE-NNN`
  (matrah 15.240 + KDV 3.048 = 18.288) kalemleri stok kartlarıyla eşleşti; e-İrsaliye → **Taslak**
  `BELGE-002`; **Itiraz iken dönüştürme engellendi**; dönüştürme `cari_hareket` YAZMADI
  (onayda mali etki, K2/K6); gelen durumu `Kabul`.
- **Faz 4 — Entegratör:** soyut `Entegrator` arayüzü + `MockEntegrator` (sandbox); meta ayarlarıyla
  gerçek sağlayıcıya kod değişmeden geçiş; ham XML `ek_dosya`'ya (`EDonusum`/`GelenBelge`) yazıldı.
- **Faz 4 — Rol:** Depo `/edonusum/yeni` ve `/edonusum/ayarlar` **403**; Muhasebe yazabiliyor,
  ayarlar yalnız Admin.
- **Faz 4 — K25 iptal koruması:** Onaylandı e-belgeli `BELGE-NNN` ve Gönderildi e-belgeli
  `BELGE-001` iptali **engellendi**; Taslak e-belgeli fatura iptali serbest (cari geri alındı +
  Taslak e-belge otomatik İptal).

---

## 8) Çalıştırma & Demo Erişimi

```bash
cd erp
python3 app.py
# → http://localhost:8080
```

İlk açılışta örnek veriler otomatik yüklenir (seed). Demo kullanıcılar (şifre: `1234`):

| Kullanıcı | Rol | Not |
|---|---|---|
| `admin` | Yönetici | tüm şubeler |
| `muhasebe` | Muhasebe | tüm şubeler |
| `satis` | Satış | tüm şubeler |
| `servis` | Servis Teknisyeni | tüm şubeler |
| `depo` | Depo | **Batman Merkez Şube** (şube izolasyonu örneği) |

---

## 9) Dosya Yapısı

```
erp/
├── app.py            # giriş noktası + auth + dashboard + bildirimler
├── core.py           # WSGI çekirdeği, yönlendirici, oturum, şablon yardımcıları
├── db.py             # şema + migrasyon + seed
├── config.py         # yollar ve ayarlar (PARA_BIRIMLERI)
├── cari.py           # MODÜL: Cari
├── stok.py           # MODÜL: Stok + Stok2
├── kasa.py           # MODÜL: Kasa
├── banka.py          # MODÜL: Banka
├── sube.py           # MODÜL: Depo/Şube
├── teklif.py         # MODÜL: Teklif (Faz 2)
├── siparis.py        # MODÜL: Sipariş (Faz 2)
├── irsaliye.py       # MODÜL: İrsaliye (Faz 2)
├── fatura.py         # MODÜL: Fatura (Faz 2)
├── cek_senet.py      # MODÜL: Çek/Senet (Faz 2)
├── doviz.py          # MODÜL: Döviz Takip (Faz 2)
├── ekler.py          # ALTYAPI: genel ek dosya (K16)
├── servis.py         # MODÜL: Servis Takip (Faz 3)
├── garanti.py        # MODÜL: Seri No-Garanti (Faz 3)
├── notlar.py         # MODÜL: Notlar (Faz 3)
├── entegrator.py     # ALTYAPI: soyut Entegrator + MockEntegrator (Faz 4)
├── edonusum.py       # MODÜL: e-Dönüşüm — giden e-belge + gelen kutusu (Faz 4)
├── muhasebe.py      # MODÜL: Genel Muhasebe (Faz 5)
├── kartoteks.py     # MODÜL: Kartoteks — salt-okunur kronolojik döküm (Faz 5)
├── transfer.py      # MODÜL: Transfer — konsolide transfer görünümü (Faz 5)
├── finansal.py      # MODÜL: Finansal Analiz — grafikler + bütçe + karşılaştırma (Faz 5)
├── beyanname.py     # MODÜL: Beyanname — KDV/Geçici Vergi/Muhtasar + denetim (Faz 5)
├── demirbas.py      # MODÜL: Demirbaş — sabit kıymet + amortisman + zimmet (Faz 5)
├── data/erp.db       # SQLite (otomatik)
├── templates/        # Jinja2 şablonları
├── static/style.css  # tema
└── docs/             # faz özetleri + mimari kurallar + bu rapor
```

---

## 10) Sonraki Adımlar

### A. Faz 2 kapanışı — Döviz Takip şartlı onayının 3 düzeltmesi (TAMAMLANDI ✅)

1. **Karışık para birimi kasa/banka bakiyesi** ✅ — `kasa.py` + `banka.py`'de `_bakiye_doviz()`
   (para birimi bazında) + TL-karşılık `_bakiye()`; liste şablonlarında "X ₺ · Y USD · Z EUR"
   ayrı gösterim + TL karşılık; günlük rapor TL karşılık; yetersiz bakiye kontrolü ilgili para
   biriminde. **Test:** Kasa "30.500,00 ₺ · 100,00 USD" (TL karşılık 35.343,36 ₺); Banka
   "120.000,00 ₺ · 2.400,00 USD · 200,00 EUR" (247.897,28 ₺); USD 600 çıkış USD bakiyesi 500 iken
   **reddedildi**, USD 400 çıkış izin verildi.
2. **Kur farkı faturası KDV** ✅ — matrah + KDV (kaynak faturanın kalem oranı, yoksa %20) = genel;
   cari hareket KDV dahil. **Test:** BELGE-NNN = matrah 384,00 + KDV 76,80 (%20) = **460,80 TL**,
   cari borç 460,80 TL.
3. **Mükerrer engel netleştirme** ✅ — kesim yalnız fatura **tamamen kapatılınca** (kalan = 0);
   kaynak fatura başına tek fatura. **Test:** ikinci kesim engellendi; kısmi tahsilatlı faturada
   "Tam kapanınca kesilir" rozeti + kesim engeli.

### B. Faz 3 — Servis & Garanti (TAMAMLANDI ✅, TAM ONAY)

Servis Takip (1.2), Seri No-Garanti (1.16), Notlar (1.1) tamamlandı; K19–K21 + K22 kuralları
`docs/mimari-kurallar.md`'ye işlendi. Kullanıcının şartlı onay düzeltmesi (Servis teslimi doğrudan
`cari_hareket` yazmaz; stok düşümü + Taslak Satış Faturası, mali etki fatura onayında) uygulandı ve
**tam onay** alındı (`docs/faz3-servis-garanti-ozet.md`).

### C. Faz 4 — e-Dönüşüm (TAMAMLANDI ✅, TAM ONAY)

e-Fatura/e-Arşiv/e-İrsaliye (1.13) + Gelen Kutuları (1.14) tamamlandı ve canlı uygulamada test
edildi (`docs/faz4-edonusum-ozet.md`). K23–K25 kuralları `docs/mimari-kurallar.md`'ye işlendi.
Kullanıcı şartlı onay koşulları (e-belge Gönderildi/Onaylandı ise fatura iptal engeli; mükellefiyet
bayrağı elle güncelleme uyarısı + GİB doğrulama notu; gelen stok eşleşme fallback kartı) kapatıldı
ve **tam onay** alındı.

### D. Faz 5 — Mali & Analitik (TAMAMLANDI ✅, TAM ONAY)

6 modülün tamamı kodlandı, canlı uygulamada test edildi, onay paketleri üretildi ve **kullanıcı
onayı alındı**: Genel Muhasebe ✅ · Kartoteks ✅ · Transfer ✅ · Finansal Analiz ✅ · Beyanname ✅ ·
Demirbaş ✅. Konsolide kapanış özeti: `docs/faz5-tamamlandi.md`. Kurallar K26–K30
`docs/mimari-kurallar.md`'ye işlendi.

### E. Faz 6 — Cila (TAMAMLANDI ✅, TAM ONAY)

Şube izolasyonu açıldı (K1) + test edildi; bildirim sistemi tamamlandı (cari vade uyarısı, tip
filtresi, SMS/e-posta mock sağlayıcı + gönderim günlüğü); dashboard panelleri, mobil/tablet CSS,
PDF antetleri ve rol matrisi ekranı (`/yetkiler`) eklendi. Onay paketi: `docs/faz6-ozet.md`.
**Proje kapanış raporu:** `docs/proje-kapanis-raporu.md`.

