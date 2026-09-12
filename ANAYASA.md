# 📜 ANAYASA v10 (SON) — BRN Teknoloji ERP Çalışma Sistemi

> Tek geçerli kaynak bu dosyadır.
> v9'dan farkı: "Claude'a ZIP gönderilmez" kuralı GM1 tarafından reddedildi → v10 doğru kuralı yazar.

---

## 1) ROLLER

| Rol | Sahip | Görev |
|---|---|---|
| **GM1 (beyin)** | **CLAUDE (web)** | Direktif yazar, coder'ı denetler, ONAYLANDI/REVİZYON kararı verir |
| **GM2 (yedek GM)** | **ARENA GM** (gm@arena) | Claude'un günlük hakkı bitince işi devralır |
| **Coder** | **ARENA CODER** (coder@arena) | Kodu yazar, test eder, rapor+kanıt yükler |
| **KÖPRÜ + Danışman** | **ARENA (bu pencere)** | Claude kararlarını repolara işler, sansürler, senkron tutar, paket hazırlar |

## 2) İKİ REPO

| Repo | Görünürlük | İçerik |
|---|---|---|
| `BRN-Teknoloji-ERP` | 🔒 PRIVATE | **kod/**, ham kanıtlar, her şeyin aslı |
| `claude` | 🌍 PUBLIC | GM1 paneli: direktif/rapor/denetim/docs/kanıt — SANSÜRLÜ |

**Senkron:** Otomatik değil; KÖPRÜ yapar. Public = private'ın SANSÜRLÜ YANSIMASI.

## 3) ⭐ CLAUDE'A İÇERİK NASIL GİDER (EN ÖNEMLİ KURAL — GM1 onaylı)

İKİ DURUM:

### A) KOD / VERİ MODELİ / İŞ MANTIĞI / ROTA / DAVRANIŞ DEĞİŞİKLİĞİ OLAN PAKETLER
(D009 ve sonrası çoğu paket bu sınıftadır.)
- KÖPRÜ güncel kaynak kodu **ZIP** hazırlar: PNG/resim YOK, kod+seed SANSÜRLÜ
  (gerçek isim → MÜŞTERİ-A), demo seed'li DB dahil.
- Zip public repoda `paketler/` altına konur; denetim paketi md'sine ZIP LİNKİ eklenir.
- **GM1 zip'i indirir, testleri BİZZAT ÇALIŞTIRIR, kodu/DB'yi inceler, SONRA karar verir.**
- "Rapor doğru yazılmış" yaklaşımıyla ONAY VERİLMEZ — bağımsız doğrulama ŞART.

### B) SAF DOKÜMANTASYON PAKETLERİ
(kod/veri/mantık değişikliği YOK — örn. D008)
- Metin (raw link) okuması YETERLİDİR; zip gerekmez.
- Bu bir **İSTİSNADIR**, kural DEĞİLDİR.

### GENEL KURALLAR (her iki durumda)
- ZIP içine PNG/resim GİRMEZ (görüntü gerekmiyor).
- Public'e çıkan her şey (zip dahil) SANSÜRLÜDÜR.
- KÖPRÜ, GM1'den ÖNCE coder iddialarını TARAFSIZ doğrular (testleri kendi çalıştırır).
  Bu, GM1'in bağımsız çalıştırmasının YERİNİ TUTMAZ — yardımcı kanıttır.
- Raw link formatı: `https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/<YOL>`

## 4) GÜNLÜK DÖNGÜ

```
1. Kral → Claude'a "şu görevi direktif yaz / şu raporu denetle"
2. Claude → public repoyu okur (kod paketi ise zip'i indirir + test çalıştırır) → karar yazar
3. Kral → kararı BU pencereye yapıştırır
4. KÖPRÜ → private repoya işler + sansürlü kopyayı public'e koyar + DURUM günceller
5. Kral → Coder'a "devam et" → Coder kodlar, private'a rapor+kanıt push'lar
6. KÖPRÜ → rapor/kanıt/kodun sansürlü hallerini public'e koyar + zip + denetim paketi hazırlar
7. 1. adıma dön
```

## 5) PUBLIC'E GİREN / GİRMEYEN

- ✅ GİRER: direktifler, raporlar, denetimler, paket md'leri, DURUM/ROL/ANAYASA/BRİFİNG,
  `docs/`, test çıktıları, regresyon logları, dosya listeleri, **sansürlü ZIP** (kod paketleri için),
  gerektiğinde sansürlü kod metni.
- ❌ GİRMEZ: PNG/resim, `data/*.db` (sansürsüz haliyle), sansürsüz kod, gerçek müşteri adı/belge no/tutar.

**SANSÜR:** gerçek isim → `MÜŞTERİ-A/B`, marka → `MARKA-A/B/C`, belge no → `BELGE-NNN`, tutar → demo.

## 6) VARDIYA (Claude hakkı bitince)

- Kullanıcı ARENA GM2'ye yazar → GM2 GitHub'daki son durumu okuyup kaldığı yerden sürdürür.
- Claude geri gelince iş Claude'a döner.

## 7) KÖPRÜ NE YAPAR / YAPMAZ

- ✅ YAPAR: kararları işlemek, sansür + senkron, zip/metin paket hazırlamak, raw link vermek,
  coder iddialarını TARAFSIZ doğrulamak.
- ❌ YAPMAZ: direktif/denetim KARARI (GM1'in), kod yazmak (coder'ın).

## 8) MEVCUT DURUM

- Proje v1.39.0. **D001–D008 ONAYLANDI.** Sıradaki: D009 (GM1 planlayacak).
