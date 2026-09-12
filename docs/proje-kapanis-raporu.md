# Brn Teknoloji ERP — PROJE KAPANIŞ RAPORU

**Elektronikçi İşletme Yönetim Sistemi · 22 modül / 6 faz · TAMAMLANDI ✅**

> **Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Durum:** Faz 1–6 tamamlandı, tüm fazlar
> kullanıcı onayı aldı. Bu doküman, sistemin ne yaptığını ve ne yapmadığını tek bakışta gösteren
> nihai kapanış raporudur.

---

## 1) Modül durumu (22 modül — tamamı ✅)

| # | Modül | Faz | Durum |
|---|---|---|---|
| 1.1 | Notlar | 3 | ✅ |
| 1.2 | Servis Takip | 3 | ✅ |
| 1.3 | Cari | 1 | ✅ |
| 1.4 | Kasa | 1 | ✅ |
| 1.5 | Stok / Stok2 | 1 | ✅ |
| 1.6 | Fatura | 2 | ✅ |
| 1.7 | Çek/Senet | 2 | ✅ |
| 1.8 | İrsaliye | 2 | ✅ |
| 1.9 | Teklif | 2 | ✅ |
| 1.10 | Sipariş | 2 | ✅ |
| 1.11 | Döviz Takip | 2 | ✅ |
| 1.12 | Şube / Depo | 1 | ✅ |
| 1.13 | e-Fatura / e-Arşiv / e-İrsaliye | 4 | ✅ (entegratör mock) |
| 1.14 | e-Fatura / e-İrsaliye Gelen Kutusu | 4 | ✅ |
| 1.15 | Banka | 1 | ✅ |
| 1.16 | Seri No-Garanti | 3 | ✅ |
| 1.17 | Kartoteks | 5 | ✅ |
| 1.18 | Transfer | 5 | ✅ |
| 1.19 | Finansal Analiz | 5 | ✅ |
| 1.20 | Genel Muhasebe | 5 | ✅ |
| 1.21 | Beyanname | 5 | ✅ |
| 1.22 | Demirbaş | 5 | ✅ |

**Çapraz altyapı:** rol bazlı yetkilendirme ✅ · bildirim/uyarı ✅ · SMS/e-posta mock noktası ✅ ·
şube izolasyonu (K1) ✅ · dashboard ✅ · audit log ✅ · ek dosya (K16) ✅ · responsive koyu tema ✅ ·
yazdır/PDF şablonları ✅ · Excel/CSV dışa aktarma ✅ · **sistem yönetimi (Ayarlar: kullanıcı/firma/
bildirim/entegratör) ✅ (Faz 6.1)**.

## 2) Faz özetleri

| Faz | İçerik | Kapanış belgesi |
|---|---|---|
| **1 — Çekirdek** | Cari, Stok/Stok2, Kasa, Banka, Depo/Şube + WSGI çekirdeği, rol/oturum, audit, bildirim, tema | `faz1-tamamlandi.md` |
| **2 — Satış Döngüsü** | Teklif → Sipariş → İrsaliye → Fatura → Çek/Senet → Döviz Takip (K8–K18) | 6 modül özeti |
| **3 — Servis & Garanti** | Servis Takip, Seri No-Garanti, Notlar (K19–K22) | `faz3-servis-garanti-ozet.md` |
| **4 — e-Dönüşüm** | e-Fatura/e-Arşiv/e-İrsaliye + Gelen Kutuları (K23–K25) | `faz4-edonusum-ozet.md` |
| **5 — Mali & Analitik** | Genel Muhasebe, Kartoteks, Transfer, Finansal Analiz, Beyanname, Demirbaş (K26–K30) | `faz5-tamamlandi.md` |
| **6 — Cila** | Şube izolasyonu açılışı, bildirim sistemi, dashboard, mobil/PDF, rol matrisi (K31) + Sistem Yönetimi/Ayarlar (K32) | `faz6-ozet.md` |
| **6.1 — Sistem Yönetimi** | Kullanıcı/firma/bildirim/entegratör yönetimi + PBKDF2 şifre güvenliği (K32) | `faz6.1-sistem-yonetimi-ozet.md` |

## 3) Nihai mimari kurallar (K1–K32, tek listede)

`docs/mimari-kurallar.md` — bağlayıcı sözleşme:

| K | Kural (özet) |
|---|---|
| K1 | Şube `sube_id` ön-hazırlığı → Faz 6'da izolasyon açıldı (cari kartlar ortak) |
| K2 | Borç/Alacak: `bakiye = Σborç − Σalacak`; müşteri (+), tedarikçi (−) |
| K3 | `ilgili_modul` / `ilgili_kayit_id` deseni tüm hareket tablolarında |
| K4 | Kartoteks tek `stok_hareket` kaynağı, salt-okunur |
| K5 | Fiyat kuralı rezervi (ayrı `fiyat_kural` tablosu açılmadı) |
| K6 | Çifte veri girişi yok (otomatik karşılık kayıt) |
| K7 | Barkod hızlı sorgulama |
| K8 | Belge zinciri doğrudan FK (teklif→sipariş→irsaliye→fatura) |
| K9 | İskonto önceliği (kural → stok → cari → 0) |
| K10 | Dönüşüm yalnız "Onaylandı" kaynaktan |
| K11 | Depo bazlı rezervasyon/düşüm + kısmi teslim |
| K12 | Tekliften çoklu sipariş |
| K13 | Belge no `{ÖNEK}-{YYYY}-{NNN}` |
| K14 | Faturasız irsaliye takibi |
| K15 | Kısmi ödenmiş belge iptal engeli |
| K16 | Genel ek dosya (jpg/png/PDF, çoklu) |
| K17 | Çek/Senet durum matrisi + vade takvimi + uyarı |
| K18 | Döviz: TL temel, güncel kur, karışık para birimi ayrı netlenir, kur farkı KDV'li |
| K19 | Servis akışı (7 durum) |
| K20 | Seri No-Garanti süre türetimi + bildirim |
| K21 | Notlar & hatırlatma → bildirim |
| K22 | Servis → Fatura (mali etki fatura onayında) |
| K23 | Giden e-belge (tür otomatik, GİB durum takibi, mock entegratör) |
| K24 | Gelen kutusu → Taslak Alış belgesi (mali etki onayda) |
| K25 | Gönderildi/Onaylandı e-belgeli kaynağın iptali engellenir |
| K26 | GM otomatik yevmiye (Fatura/Kasa/Banka/Çek-Senet/Demirbaş; ara hesaplar 101/121/103/321) |
| K27 | Transfer tek modülde konsolide görünüm |
| K28 | Finansal Analiz türetilmiş analitikler + COGS + bütçe |
| K29 | Beyanname salt-okunur vergi hazırlık raporları (zarar kuralı) |
| K30 | Demirbaş sabit kıymet + normal amortisman (770/257) + zimmet |
| K31 | Faz 6: şube izolasyonu açılışı + bildirim sağlayıcı soyutlaması |
| K32 | Faz 6.1: Sistem Yönetimi (Ayarlar) — kullanıcı/firma/bildirim/entegratör tek merkezde (Admin); silme yerine pasifleştirme; şifreler PBKDF2 |

## 4) Sayısal envanter

| Ölçüt | Değer |
|---|---|
| Modül / faz | **22 modül · 6 faz** |
| Kayıtlı rota | **166** |
| Veri tablosu | **52** |
| Yevmiye fişi | **28** (24 mali + 4 Demirbaş amortisman) |
| Mizan | **dengeli 833.375,26 ₺** |
| Şube | 2 (Batman Merkez · Diyarbakır) |
| Demo kullanıcı | 5 (`admin`, `muhasebe`, `satis`, `servis`, `depo` — şifre `1234`; `depo` Batman şubesine izole) |
| Teknoloji | Python 3 (stdlib) + SQLite + Jinja2 + öz WSGI çekirdeği; Excel dışa aktarım için `openpyxl` |

**Modül başına rota:** Genel 9 · Cari 9 · Stok/Stok2 19 · Kasa 6 · Banka 6 · Depo/Şube 5 ·
Teklif 6 · Sipariş 6 · İrsaliye 6 · Fatura 6 · Çek/Senet 7 · Döviz 6 · Servis 8 · Garanti 4 ·
Notlar 3 · e-Dönüşüm 13 · Kartoteks 7 · Transfer 1 · Genel Muhasebe 10 · Finansal Analiz 5 ·
Beyanname 3 · Demirbaş 9 · Ek dosya 3 · Sistem Yönetimi (Ayarlar) 9.

## 5) Entegrasyon zinciri (şartname Bölüm 2)

**Teklif → Sipariş → İrsaliye → Fatura → e-Fatura/e-Arşiv → Cari/Kasa/Banka → Genel Muhasebe**
tek belge zinciridir. **Fatura / Kasa / Banka / Çek-Senet / Demirbaş amortismanı** her zaman yevmiye
karşılığı üretir (manuel çifte giriş yok). **Servis → Stok düşümü → Fatura → Garanti** otomatiktir.
**Kartoteks** tüm modüllerden beslenen salt-okunur geçmiştir. **Döviz** cinsi kayıtlarda güncel kur
otomatik, kur farkı izlenir.

## 6) Bilinen sınırlamalar / açık noktalar (tek listede)

### ✅ Çözülen açık maddeler (Faz 6.1 — artık sınırlama değil)

Ayrıntılı paket (veri modeli + rota + ekran + canlı test kanıtları):
**`docs/faz6.1-sistem-yonetimi-ozet.md`**.

- **Şifre değiştirme / kullanıcı yönetimi** — eklendi ve canlıda test edildi:
  - Kullanıcı ekleme · rol değiştirme · **aktif/pasif** (sert silme yok, audit korunur) ·
    şifre sıfırlama (Admin) — `Ayarlar → Kullanıcılar`.
  - Her kullanıcı **kendi şifresini** değiştirebilir (üst çubuk 🔑 → `/profil/sifre`).
  - Şifreler **PBKDF2-HMAC-SHA256** ile saklanır (eski salted SHA-256 hash'leri girişte
    otomatik yükseltilir); düz metin hiçbir yerde tutulmaz.
  - `firma` düzenleme ekranı (`Ayarlar → Firma`) + bildirim kanalı ve entegratör ayarları
    tek merkezde (`Ayarlar`) toplandı.

### Vergi & Beyanname
1. **Muhtasar kapsam dışı** — bordro/stopaj veri kaynağı olmadığından boş şablon + açıklama; kaynak
   eklenince otomatik dolar.
2. **Geçici Vergi "tahmini"** — matrah COGS dahil tahmini brüt kârdır (GM kümülatif kârı değil);
   kesin matrah dönem kapanışında netleşir (ekranda rozetli).
3. **Zarar devri** — yıl içi kümülatif matrahtan otomatik düşer; **yıllar arası devir dönem
   kapanışında** netleşir (negatif vergi asla üretilmez).
4. **Nakit esaslı KDV** — cari bazlı basitleştirilmiş oranlama (çek/senet hariç); kesin
   fatura-bazlı eşleştirme için mali müşavir onayı.
5. **Kur farkı faturası KDV fallback** — kaynak fatura kalemlerinden tek KDV oranı; tek oranlı
   değilse **%20** varsayılır.
6. **`HZM-GLN-ESLESME` fallback kartı** — eşleştirilmemiş gelen belge kalemlerinin KDV/hesap
   belirsizliği; Beyanname'de ayrı liste olarak işaretlenir, mali müşavirce netleştirilir.
7. **Sabit %20 hizmet KDV** — `HZM-SRV-ISCLK` gibi hizmet kartları; farklı oran için kart başına
   ayrı KDV oranı girilmesi yeterlidir.

### Demirbaş
8. **Kıst (ay kesri) amortisman uygulanmaz** — ilk amortisman alış ayından tam ay başlar; ilk yıl
   kıst hesabı mali müşavirle netleştirilmelidir.
9. **Çıkış mahsubu manuel** — Satıldı/Hurda'da net defter değeri mahsubu (257 ↔ 689) elle GM fişiyle
   yapılır.
10. **Maliyet KDV hariç** bedeldir (KDV indirilebilir).

### e-Dönüşüm & döviz
11. **Entegratör mock (sandbox)** — gerçek sağlayıcıya geçiş `meta` ayarlarıyla, kod değişmeden.
12. **GİB otomatik doğrulama yok** — `e_fatura_mukellefi` elle güncellenir (uyarı + not).
13. **Döviz** — desteklenen TRY/USD/EUR/GBP; kur TCMB `today.xml`'den çekilir.

### Altyapı / Faz 6
14. **SMS/e-posta sağlayıcısı mock** — kanal varsayılan **kapalı** (dış çağrı yapılmaz); gerçek
    sağlayıcı `bildirim_saglayici.py`'ye yeni bir `Saglayici` sınıfıyla eklenir.
15. **Cari kartlar şube izolasyonu dışında** — merkezi müşteri havuzu (K1'in kapsamıydı); gerekirse
    ileride `cari_kart.sube_id` eklenebilir.
16. **Bildirim taramaları cron'suz** — sayfa ziyaretiyle (dashboard) tetiklenir.
17. **PDF = yazdırılabilir HTML** — tarayıcıyla "PDF'e kaydet"; sunucu-tarafı PDF dosyası üretimi yok.
18. **ÖTV/tevkifat** — alanlar şartnamedeki gibi hazır seçenek olarak durur; aktif hesaplama yok.
19. **Yedekleme** — SQLite dosyası (`data/erp.db`) tek doğruluk kaynağıdır; **`yedek_al.py`**
    aracı tarih damgalı, tutarlı anlık görüntü alır (canlı yazma sırasında güvenli; SQLite
    `.backup()` API'si) ve eskileri otomatik budar. **Her yedek alındıktan sonra
    `PRAGMA integrity_check` sonucu gerçekten okunup değerlendirilir:** `ok` değilse uyarı
    verir ve çıkış kodu 3 döner (bozuk yedek sessizce "OK" sayılmaz). Haftalık cron rutini
    önerilir (bkz. betiğin başındaki örnek); yedeği harici diske / buluta kopyalamak
    operasyonel sorumluluktur.
20. **Fiyat kuralı (K5)** — ayrı tablo açılmadı; iskonto önceliği mevcut alanlarla çalışır.
21. **Mobil** — masaüstü + tablet önceliği tamam; telefon ince ayarı (600px) yapıldı.

## 7) Çalıştırma & erişim

```bash
cd erp
python3 app.py   # → http://localhost:8080
```

İlk açılışta örnek veriler otomatik yüklenir. Yedek almak için: `python3 yedek_al.py` (bkz. Bölüm 6,
madde 19). Demo kullanıcılar (şifre: `1234`):

| Kullanıcı | Rol | Şube |
|---|---|---|
| `admin` | Yönetici | tüm şubeler |
| `muhasebe` | Muhasebe | tüm şubeler |
| `satis` | Satış | tüm şubeler |
| `servis` | Servis Teknisyeni | tüm şubeler |
| `depo` | Depo | **Batman Merkez Şube** (izolasyon örneği) |

## 8) Onay geçmişi

| Faz | Durum |
|---|---|
| Faz 1 — Çekirdek | ✅ tam onay |
| Faz 2 — Satış Döngüsü | ✅ tam onay |
| Faz 3 — Servis & Garanti | ✅ tam onay |
| Faz 4 — e-Dönüşüm | ✅ tam onay |
| Faz 5 — Mali & Analitik | ✅ tam onay |
| Faz 6 — Cila | ✅ tam onay |

**Proje resmi olarak tamamlanmıştır.** 🎉
