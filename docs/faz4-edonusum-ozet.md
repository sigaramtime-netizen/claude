# Faz 4 — e-Dönüşüm (özet + test kanıtları)

**Tarih:** 2026-09-07 · **Firma:** Brn Teknoloji · **Kapsam:** e-Fatura/e-Arşiv/e-İrsaliye (1.13), Gelen Kutuları (1.14)

> Bu doküman Faz 4 sonu onay paketidir: veri modeli özeti, ekran listesi ve örnek test senaryosu
> (test kanıtlarıyla). Proje komutu gereği faz sonunda onay istenir.

---

## 1) Veri Modeli Özeti

### 1.1 `e_belge` (yeni — giden)
| Kolon | Tip | Açıklama |
|---|---|---|
| id | INTEGER PK | |
| belge_no | TEXT UNIQUE | `{EF/EA/EI}-{YYYY}-{NNN}` (K13 yıl bazlı sayaç) |
| tur | TEXT CHECK | `EFatura, EArsiv, EIrsaliye` — alıcı mükellefiyetine göre otomatik |
| kaynak_fatura_id | FK → fatura | K8 kaynak FK deseni (fatura kaynaklıysa) |
| kaynak_irsaliye_id | FK → irsaliye | K8 kaynak FK deseni (irsaliye kaynaklıysa) |
| cari_id | FK → cari_kart | alıcı |
| alici_vkn / alici_unvan | TEXT | XML/ETTN için alıcı kimlik bilgisi |
| senaryo | TEXT | varsayılan `Temel` |
| ettn | TEXT | GİB ETN (gönderim sonrası) |
| durum | TEXT CHECK | `Taslak, Gönderildi, Onaylandı, Reddedildi, İptal` |
| hata_mesaji | TEXT | red nedeni |
| gonderim_tarihi | TEXT | |
| created_by / created_at / updated_at | | audit alanları |

### 1.2 `gelen_belge` (yeni — gelen)
| Kolon | Tip | Açıklama |
|---|---|---|
| id | INTEGER PK | |
| belge_no | TEXT UNIQUE | dedup anahtarı |
| tur | TEXT CHECK | `EFatura, EIrsaliye` |
| gonderen_vkn / gonderen_unvan | TEXT | tedarikçi |
| alici_vkn | TEXT | firmanın VKN'si |
| belge_tarih | TEXT | |
| tutar / kdv | REAL | XML'den okunan genel toplam / KDV |
| para_birimi | TEXT | varsayılan TRY |
| durum | TEXT CHECK | `Okunmadi, Kabul, Red, Itiraz` |
| donusum_fatura_id | FK → fatura | K8: dönüştürülen Alış Faturası |
| donusum_irsaliye_id | FK → irsaliye | K8: dönüştürülen Alış İrsaliyesi |
| aciklama | TEXT | |
| created_by / created_at / updated_at | | audit alanları |

### 1.3 Mevcut tablolara eklenen
| Tablo | Değişiklik | Açıklama |
|---|---|---|
| cari_kart | `e_fatura_mukellefi INTEGER NOT NULL DEFAULT 0` | giden tür otomatik: 1=e-Fatura, 0=e-Arşiv. ⚠️ Şimdilik **elle** güncellenir (kart düzenlemede uyarı gösterilir); gerçek entegratörde GİB sorgu servisiyle otomatik doğrulanacak. |
| ek_dosya | (yeni kayıtlar) | `ilgili_modul='EDonusum'` (giden) / `'GelenBelge'`, `dosya_tipi='xml'` — ham UBL-TR benzeri çıktı (K16, yeni tablo YOK) |

> **K25 (şartlı onay düzeltmesi):** Kaynak fatura/irsaliye iptali, kendisine bağlı **Gönderildi/Onaylandı**
> durumundaki e-belge varken **engellenir** (K15 deseni). Taslak/Reddedildi e-belgeler iptali engellemez;
> kaynak iptal edilirse bu e-belgeler otomatik `İptal`'e alınır.

### 1.4 Meta ayarları (entegratör)
`entegrator_saglayici` (Mock), `entegrator_api_anahtari` (boş), `entegrator_test_modu` (1).
Gerçek anahtar geldiğinde kod değişmeden bu üç değer güncellenir.

---

## 2) Ekran Listesi

| # | Ekran | Rota | Yetki | Durum |
|---|---|---|---|---|
| 1 | Giden e-Belge Listesi | `GET /edonusum` | Admin/Muhasebe/Depo (görüntüleme) | ✅ |
| 2 | Yeni e-Belge (kaynak seç + otomatik tür) | `GET /edonusum/yeni` | Admin/Muhasebe | ✅ |
| 3 | e-Belge Oluştur | `POST /edonusum/olustur` | Admin/Muhasebe | ✅ |
| 4 | e-Belge Detay (kalem + XML + entegratör işlemleri) | `GET /edonusum/{id}` | görüntüleme | ✅ |
| 5 | GİB'e Gönder | `POST /edonusum/{id}/gonder` | Admin/Muhasebe | ✅ |
| 6 | GİB Yanıtını Sorgula | `POST /edonusum/{id}/durum-sorgula` | Admin/Muhasebe | ✅ |
| 7 | Mock GİB Yanıtı (sandbox) | `POST /edonusum/{id}/mock-yanit` | Admin | ✅ |
| 8 | Entegratör Ayarları | `GET/POST /edonusum/ayarlar` | Admin | ✅ |
| 9 | Gelen Kutusu Listesi | `GET /gelen` | görüntüleme | ✅ |
| 10 | Gelen Kutusunu Yenile | `POST /gelen/yenile` | Admin/Muhasebe | ✅ |
| 11 | Gelen Belge Detay (XML + stok eşleşmesi) | `GET /gelen/{id}` | görüntüleme | ✅ |
| 12 | Gelen Belge → Alış belgesine Dönüştür | `POST /gelen/{id}/donustur` | Admin/Muhasebe | ✅ |
| 13 | Gelen Belge Durum Değiştir | `POST /gelen/{id}/durum` | Admin/Muhasebe | ✅ |

**NAV güncellemesi:** Faz 4 menüsünde e-Fatura/e-Arşiv → `/edonusum`, e-İrsaliye → `/edonusum?tur=EIrsaliye`,
Gelen Kutuları → `/gelen` aktif (hazir=True).

---

## 3) Örnek Test Senaryosu (uçtan uca)

> Senarist: muhasebe (admin). Ortam: sandbox MockEntegrator.

| # | Adım | Beklenen Sonuç | Kanıt |
|---|---|---|---|
| 1 | `/edonusum/yeni` — onaylı `BELGE-NNN` (mükellef müşteri) için "Oluştur" | `BELGE-NNN` kaydı, tür **e-Fatura**, durum Taslak | ✅ |
| 2 | Detaydan "GİB'e Gönder" | durum **Gönderildi**, `ettn` üretilir | ✅ |
| 3 | "GİB Yanıtını Sorgula" (mock) | durum **Onaylandı** | ✅ |
| 4 | e-İrsaliye: `BELGE-NNN` için oluştur | `BELGE-NNN`, tür **e-İrsaliye** | ✅ |
| 5 | Mock yanıt = "Reddedildi" + neden | durum **Reddedildi**, `hata_mesaji` dolar | ✅ |
| 6 | `/gelen/yenile` (2 kez) | toplam 2 belge — **dedup** (belge_no UNIQUE) | ✅ |
| 7 | `GLN-BELGE-NNN1` → "Alış Faturasına Dönüştür" | **Taslak** `BELGE-NNN` (matrah 15.240 + KDV 3.048 = 18.288), kalemler `CM-9KG-ARC-004` + `PAR-DRM-VST-007` ile eşleşti, gelen durumu **Kabul** | ✅ |
| 8 | `GLN-BELGE-NNN1` → önce Itiraz'a al, sonra dönüştür | **Itiraz iken dönüştürme engellendi**; Okunmadi'ye çekince **Taslak** `BELGE-002` oluştu, durum **Kabul** | ✅ |
| 9 | `cari_hareket` sayısı dönüştürme sonrası | **değişmedi** (dönüştürme mali etki YAZMAZ — onayda doğar, K2/K6) | ✅ |
| 10 | Depo kullanıcısı `/edonusum/yeni` | **403** (yazma yetkisi yok) | ✅ |
| 11 | `BELGE-NNN` (e-belgesi `BELGE-NNN` **Onaylandı**) iptali | **engellendi** — fatura Onaylandı kalır, "resmi iptal/düzeltme" uyarısı | ✅ |
| 12 | `BELGE-001` (e-belgesi `BELGE-NNN` **Gönderildi**) iptali | **engellendi** — irsaliye Onaylandı kalır | ✅ |
| 13 | Taslak e-belgeli faturada iptal | **izin verildi**; cari hareket geri alındı; Taslak e-belge otomatik **İptal** oldu | ✅ |
| 14 | Gelen kalem hiçbir stok kartıyla eşleşmezse | dönüştürme **engellenmez**; kalem `HZM-GLN-ESLESME` fallback kartına bağlanır, flash mesajında listelenir | ✅ |

**Regresyon:** 32 ana sayfa (cari, stok, depo, kasa, banka, şube, teklif, sipariş, irsaliye, fatura,
çek/senet, döviz, servis, garanti, notlar + e-dönüşüm) 200 döndü.

---

## 4) Faz 5 öncesi gözden geçirilecekler (kullanıcı kararları)

- Hizmet kartı `HZM-SRV-ISCLK` KDV oranı sabit %20; farklı KDV oranlı hizmet türleri için kart çoğaltılabilir.
- Kur farkı faturasında karma KDV oranlı faturalardaki "tek oranlı değilse %20" fallback davranışı.
- KDV oranı fallback'lerinin Beyanname doğruluğuna etkisi.

---

## 5) Onay İsteği

Faz 4 — e-Dönüşüm (e-Fatura/e-Arşiv/e-İrsaliye + Gelen Kutuları) kapsamı yukarıda özetlenmiş ve
test kanıtlarıyla sunulmuştur. Onayınız sonrası **Faz 5 — Beyanname & Muhasebe** fazına geçilir.
