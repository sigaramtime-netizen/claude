# 📜 ANAYASA v11 (SON) — BRN Teknoloji ERP Çalışma Sistemi

> Tek geçerli kaynak bu dosyadır.

---

## ⛔ BİRİNCİ KURAL — ZIP (GM1'in kesin kararı, pazarlıksız)

> **"Kalıcı zipsiz kural" diye bir şey YOKTUR ve hiç olmadı.**
> KOD / VERİ MODELİ / İŞ MANTIĞI / ROTA / DAVRANIŞ / GÜVENLİK değiştiren HER paket
> (D009 ve sonrası çoğu paket) için:
>
> **KÖPRÜ güncel kaynak kodu ZIP olarak hazırlar → GM1 zip'i indirir, testleri
> BİZZAT çalıştırır, kodu/DB'yi inceler → SONRA karar verir.**
>
> Metin/raw-link yalnızca **SAF DOKÜMANTASYON** paketlerinde (kod/veri/mantık
> değişikliği YOK — örn. D008) yeterlidir; bu bir İSTİSNADIR, KURAL DEĞİLDİR.
>
> *Not: "zipsiz kural" ifadesi, köprünün bir ara dönem yazdığı hatalı bir nottan
> kaynaklandı; GM1 bunu reddetti ve v10'dan beri doğru kural yukarıdaki gibidir.
> Bu maddeyi hiçbir belge geçersiz kılamaz.*

**ZIP formatı (standart):** sansürlü (gerçek isim → `MÜŞTERİ-A/B`, marka →
`MARKA-A/B/C`, belge no → `BELGE-NNN`, tutar → demo) + demo seed'li DB + testler
tek zip içinde + **MD5/SHA256**. PNG/resim zip'e GİRMEZ. Ayrıca ek TXT kanıt
paketi İSTENMEZ (zip yeterli — GM1 kendi testini kendisi koşturur).

---

## 1) ROLLER

| Rol | Sahip | Görev |
|---|---|---|
| **GM1 (beyin)** | **CLAUDE (web)** | Direktif yazar, coder'ı denetler, ONAYLANDI/REVİZYON kararı verir |
| **GM2 (yedek GM)** | **ARENA GM** (gm@arena) | Claude'un günlük hakkı bitince işi devralır |
| **Coder** | **ARENA CODER** (coder@arena) | Kodu yazar, test eder, rapor+kanıt yükler |
| **KÖPRÜ + Danışman** | **ARENA (bu pencere)** | GM1 kararlarını repolara işler, sansürler, senkron tutar, ZIP paketler |

## 2) İKİ REPO

| Repo | Görünürlük | İçerik |
|---|---|---|
| `BRN-Teknoloji-ERP` | 🔒 PRIVATE | **kod/**, ham kanıtlar, her şeyin aslı |
| `claude` | 🌍 PUBLIC | GM1 paneli: direktif/rapor/denetim/docs/kanıt — SANSÜRLÜ |

**Senkron:** Otomatik değil; KÖPRÜ yapar. Public = private'ın SANSÜRLÜ YANSIMASI.

## 3) GÜNLÜK DÖNGÜ

```
1. Kral → Claude'a "şu görevi direktif yaz / şu raporu denetle"
2. Claude → public repoyu okur (kod paketi ise zip'i indirip testleri BİZZAT çalıştırır) → karar
3. Kral → kararı BU pencereye yapıştırır
4. KÖPRÜ → private repoya işler + sansürlü kopyayı public'e koyar + DURUM günceller
5. Kral → Coder'a "devam et" → Coder kodlar, private'a rapor+kanıt push'lar
6. KÖPRÜ → rapor/kanıt/kodun sansürlü hallerini public'e koyar + ZIP + denetim paketi hazırlar
7. 1. adıma dön
```

## 4) MİKRO-KARAR PROTOKOLÜ

Coder, emin olmadığı bir tasarım kararında (örn. CSRF uygulaması) **kodlamaya başlamadan
önce** 2-3 seçenekle sorar → Kral GM1'e iletir → GM1 seçer → karar `D0XX-mikro-karar.md`
dosyasına KÖPRÜ tarafından kaydedilir ve her iki repoya işlenir. Coder o dosyaya göre ilerler.

## 5) PUBLIC'E GİREN / GİRMEYEN

- ✅ GİRER: direktifler, raporlar, denetimler, paket md'leri, DURUM/ROL/ANAYASA/BRİFİNG,
  `docs/`, test çıktıları, regresyon logları, dosya listeleri, **sansürlü ZIP**, mikro-kararlar,
  gerektiğinde sansürlü kod metni.
- ❌ GİRMEZ: PNG/resim, sansürsüz kod, `data/*.db` (sansürsüz), gerçek müşteri adı/belge no/tutar.

## 6) VARDIYA (Claude hakkı bitince)

- Kral ARENA GM2'ye yazar → GM2 GitHub'daki son durumu okuyup kaldığı yerden sürdürür.
- Claude geri gelince iş Claude'a döner.

## 7) KÖPRÜ NE YAPAR / YAPMAZ

- ✅ YAPAR: kararları işlemek, sansür + senkron, ZIP/metin paket hazırlamak, raw link vermek,
  coder iddialarını TARAFSIZ doğrulamak (testleri kendi çalıştırmak).
- ❌ YAPMAZ: direktif/denetim KARARI (GM1'in), kod yazmak (coder'ın), GM1'in kararlarını değiştirmek.

## 8) MEVCUT DURUM

- Proje v1.39.0. **D001–D008 ONAYLANDI.**
- **D009 (Güvenlik & Sağlamlık) AKTİF** — CSRF tasarımı: **HİBRİT** (GM1 onayı, mikro-karar
  `gm-direktifleri/D009-mikro-karar.md`'de). Teslim: **ZIP**.
