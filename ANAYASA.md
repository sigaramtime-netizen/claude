# 📜 ANAYASA v12 (SON) — BRN Teknoloji ERP Çalışma Sistemi

> Tek geçerli kaynak bu dosyadır.

---

## ⛔ BİRİNCİ KURAL — ZIP (GM1'in kesin kararı, pazarlıksız)

> **"Kalıcı zipsiz kural" diye bir şey YOKTUR ve hiç olmadı.**
> KOD / VERİ MODELİ / İŞ MANTIĞI / ROTA / DAVRANIŞ / GÜVENLİK değiştiren HER paket
> (D009 ve sonrası çoğu paket) için: **ZIP teslim edilir → GM1 testleri BİZZAT çalıştırır.**
> Metin/raw-link yalnızca **SAF DOKÜMANTASYON** paketlerinde yeterlidir (istisna).

**ZIP formatı (standart):** sansürlü (gerçek isim → `MÜŞTERİ-A/B`, marka → `MARKA-A/B/C`,
belge no → `BELGE-NNN`, tutar → demo) + demo seed'li DB + testler tek zip içinde +
**MD5/SHA256**. PNG/resim zip'e GİRMEZ. Ayrı ek TXT kanıt paketi İSTENMEZ.

---

## ⭐ İKİNCİ KURAL — CLAUDE'A DOSYA NASIL ULAŞIR (teknik gerçek, kesin)

> **Claude web'in sandbox'ında İNTERNET YOK.** Bu yüzden:
>
> - **ZIP (binary) → link ile ASLA çekemez** ("[binary data]" yer tutucusu döner).
>   → ZIP, **kullanıcı tarafından Claude sohbetine DOSYA OLARAK YÜKLENİR.**
> - **Metin (.md/.txt) → raw link ile OKUYABİLİR** (fetch eder).
>   → Direktif/rapor/denetim/özet metinleri raw link ile verilir; yükleme gerekmez.
>
> **KÖPRÜ'NÜN STANDART GÖREVİ:** kod paketlerinde sansürlü ZIP'i hazırlar, kullanıcıya
> "bu dosyayı indir → Claude'a sürükle-bırak" der, denetim paketini (md) raw link ile verir.
> Hash doğrulaması için zip'in MD5/SHA256'sı denetim paketinde yazar.

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
| `claude` | 🌍 PUBLIC | GM1 paneli: direktif/rapor/denetim/docs/kanıt/zip — SANSÜRLÜ |

**Senkron:** Otomatik değil; KÖPRÜ yapar. Public = private'ın SANSÜRLÜ YANSIMASI.

## 3) GÜNLÜK DÖNGÜ

```
1. Kral → Claude'a "şu görevi direktif yaz / şu raporu denetle"
2. Claude → metinleri raw link ile okur; kod paketi ise zip'i SOBBETTEKİ DOSYADAN açıp testleri çalıştırır → karar
3. Kral → kararı BU pencereye yapıştırır
4. KÖPRÜ → private repoya işler + sansürlü kopyayı public'e koyar + DURUM günceller
5. Kral → Coder'a "devam et" → Coder kodlar, private'a rapor+kanıt push'lar
6. KÖPRÜ → rapor/kanıt/kodun sansürlü hallerini public'e koyar + ZIP + denetim paketi hazırlar
   → ZIP'i kullanıcıya "indir → Claude'a yükle" diye sunar; md paketini raw link verir
7. 1. adıma dön
```

## 4) MİKRO-KARAR PROTOKOLÜ

Coder, emin olmadığı bir tasarım kararında kodlamaya başlamadan 2-3 seçenekle sorar →
Kral GM1'e iletir → GM1 seçer → karar `D0XX-mikro-karar.md` olarak KÖPRÜ tarafından
kaydedilir ve iki repoya işlenir. Coder o dosyaya göre ilerler.

## 5) PUBLIC'E GİREN / GİRMEYEN

- ✅ GİRER: direktifler, raporlar, denetimler, paket md'leri, DURUM/ROL/ANAYASA/BRİFİNG,
  `docs/`, test çıktıları, regresyon logları, dosya listeleri, **sansürlü ZIP**, mikro-kararlar.
- ❌ GİRMEZ: PNG/resim, sansürsüz kod, `data/*.db` (sansürsüz), gerçek müşteri adı/belge no/tutar.

## 6) VARDIYA (Claude hakkı bitince)

- Kral ARENA GM2'ye yazar → GM2 GitHub'daki son durumu okuyup kaldığı yerden sürdürür.
- Claude geri gelince iş Claude'a döner.

## 7) KÖPRÜ NE YAPAR / YAPMAZ

- ✅ YAPAR: kararları işlemek, sansür + senkron, ZIP/metin paket hazırlamak, raw link vermek,
  coder iddialarını TARAFSIZ doğrulamak (testleri kendi çalıştırmak).
- ❌ YAPMAZ: direktif/denetim KARARI (GM1'in), kod yazmak (coder'ın), GM1 kararlarını değiştirmek.

## 8) MEVCUT DURUM

- Proje v1.40.0 (D009 kodlu). **D001–D008 ONAYLANDI.**
- **D009 (Güvenlik) — GM1 denetimi bekleniyor** (zip kullanıcıya verildi, Claude'a yüklenecek).
