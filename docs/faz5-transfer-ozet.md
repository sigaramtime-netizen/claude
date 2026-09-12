# Faz 5 — Transfer (1.18) — özet + test kanıtları

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Faz 5 / Modül 3/6** · **Durum:** tamamlandı ✅

> Faz 5 (Mali/Analitik) 3. modülü. Sıra: Genel Muhasebe ✅ → Kartoteks ✅ → **Transfer ✅** →
> Finansal Analiz → Beyanname → Demirbaş.

---

## Tasarım kararı (baştan netleştirilen)

**Yeni veri modeli AÇILMADI — konsolide salt-okunur görünüm (K4/K6 deseni).** Gerekçe:
1. K6 "çifte veri girişi yok" — ayrı bir `transfer` tablosu, zaten `depo_transfer` /
   `kasa_hareket` / `banka_hareket` içinde yaşayan kayıtların ikinci doğruluk kaynağı olur;
   GM'de yakaladığımız "transfer çift sayımı" sınıfından hataları yeniden üretme riski taşır.
2. Mevcut akışların kendi doğrulaması var: depo transferi **Taslak→Tamamlandı onay akışı**,
   kasa↔banka **anında + yetersiz bakiyede tam red**. "Onay mekanizması" şartı böyle karşılanıyor.

**Eksik olan "kasalar arası" parçası bu modülde tamamlandı:** kasa→kasa transferi (önceden yoktu)
`kasa.py`'ye eklendi — böylece 1.18'in üç türü de (depolar arası, kasalar arası, kasa↔banka)
tek modülde görünür hale geldi.

---

## 1) Veri Modeli Özeti

**Yeni tablo YOK.** Konsolide görünümün kaynakları:

| Tür | Kaynak tablo | Durum / onay |
|---|---|---|
| Depolar Arası | `depo_transfer` + `depo_transfer_kalem` | Taslak → Tamamlandı (Stok2 onayı) |
| Kasa ↔ Banka | `kasa_hareket`/`banka_hareket` çifti (`ilgili_modul='Transfer'`) | Anında (bakiye kontrollü) |
| Kasalar Arası | `kasa_hareket` çifti: `Kasa Transferi (Çıkış)` + `(Giriş)` | Anında (bakiye kontrollü) |

- Kasa→Kasa: kaynak kasa `Kasa Transferi (Çıkış)` (CIKIS), hedef kasa `Kasa Transferi (Giriş)`
  (GIRIS), `ilgili_kayit_id` bağıyla eşleşir; **GM'de fiş üretmez** (100 hesabı içi net sıfır).
- "Şubeler Arası": kaynak/hedef varlığın `sube_id`'si farklıysa işaretlenir (K1).

---

## 2) Ekran Listesi

| # | Ekran | Rota | Yetki |
|---|---|---|---|
| 1 | Transfer konsolide liste (geçmiş + KPI + filtre) | `GET /transfer` | tüm roller |
| 2 | Kasa→Kasa transfer girişi | `POST /kasa/hareket` (tip: Kasa → Kasa) | Admin/Muhasebe/Satış |

Mevcut giriş/onay ekranlarına link: depo transferi → `/stok/transferler`, kasa/banka → `/kasa`+`/banka`.
Filtreler: tür (Depo/Kasalar Arası/Kasa ↔ Banka), şube, tarih aralığı.

---

## 3) Örnek Test Senaryosu (canlı HTTP)

| # | Adım | Beklenen | Kanıt |
|---|---|---|---|
| 1 | `GET /transfer` (seed) | 200; mevcut kasa→banka (TR-001 30.000) satırı + KPI | ✅ |
| 2 | Kasa→Kasa POST | çıkış (kasa1) + giriş (kasa2) kaydı, `ilgili_kayit_id` bağı | ✅ |
| 3 | Kasa bakiye etkisi | kasa1 −1.000, kasa2 +1.000 | ✅ |
| 4 | GM net sıfır | fiş sayısı değişmedi (0 yeni) | ✅ |
| 5 | Konsolide görünüm | "Kasalar Arası" satırı + 1.000 tutar | ✅ |
| 6 | Transfer tek başına iptal | reddedildi, kayıt korundu | ✅ |
| 7 | Depo transferi (Taslak) | "Depolar Arası" + "Onay Bekliyor" + "1 kalem" | ✅ |
| 8 | Tür filtresi | `tip=Depo` kasa satırını gizler; `tip=Kasa ↔ Banka` gösterir | ✅ |
| 9 | Regresyon | 14 sayfa 200; GM mizan dengeli (831.133,60) | ✅ |

---

## 4) Notlar

- Seed'de tek şube (Batman Merkez) olduğundan "Şubeler Arası" rozeti şu an görünmez;
  ikinci şube eklenince otomatik çalışır (kaynak/hedef `sube_id` karşılaştırması).
- Kasa→Kasa transferi GM'de kasıtlı olarak fiş üretmez — 100 hesabı içinde net sıfırdır;
  kasa↔banka transferleri ise K26 gereği tek fişle izlenir.
- Test sırasında oluşturulan kasa→kasa ve depo transferi kayıtları temizlendi; seed pristine.

---

## 5) Şartlı onay teyitleri (kullanıcının 2 sorusu — 2026-09-08)

### T1 — Kasa→Kasa'da yetersiz bakiye → atomiklik ✅

Kasa→Kasa transferi, **diğer tüm çıkış yönlü hareketlerle aynı** "yetersiz bakiye" kontrolünden
geçer: `Kasa Transferi (Çıkış)` tipi `CIKIS` listesindedir ve kontrol (kaynak kasanın TRY
bakiyesi < tutar ise) iki bacağın yazıldığı bloktan **önce** çalışır; yetersiz bakiyede istek
**hiçbir INSERT yapılmadan** reddedilir. İki bacak tek `commit`'te yazıldığı için "yarım kayıt"
oluşamaz; ayrıca hedef kasa varlığı da çıkış yazılmadan önce doğrulanır (geçersiz hedefte yine
sıfır kayıt).

**Canlı test:** kaynak kasa1 bakiye 30.500 iken 999.999 TL'lik transfer POST'u →
kasa_hareket satır sayısı **değişmedi (9→9)**, `Kasa Transferi*` tipli satır **0**, flash
"…yetersiz (TRY)" göründü. Geçersiz `hedef_kasa_id=99999` POST'unda da satır değişimi **0**.

### T2 — Tam transfer iptali (çift bacaklı) davranışı ✅

Transfer **bir kez kaydedildikten sonra kalıcıdır**; bütünü (iki bacak birlikte) geri alan ayrı
bir rota **yoktur** — düzeltme ancak ters yönde yeni bir transfer girilerek yapılır. Bu bilinçli
bir tasarım kararıdır ve üç türde de tutarlıdır:

- Kasa→Kasa: çıkış bacağı da giriş bacağı da tek başına iptal edilemez (ikisi de
  `TRANSFER_TIPLERI` içinde → "tek başına iptal edilemez" flash'ı, kayıt korunur).
- Kasa↔Banka: kasa bacağı **ve** banka bacağı tek başına iptal edilemez (aynı kural,
  `banka_hareket_iptal` da transfer tiplerini bloklar).

**Canlı test:** 100 TL kasa1→kasa2 transferi sonrası her iki bacağa ayrı ayrı `iptal` POST'u
reddedildi (kayıtlar korundu); `/kasa/transfer/{id}/iptal` gibi bir rota yok (404). Kasa↔Banka
seed bacaklarına (kasa id=4, banka id=3) iptal POST'ları da reddedildi. Test kayıtları
temizlendi; kasa bakiyeleri 30.500 / 6.200, 24 yevmiye, mizan dengeli 831.133,60.
