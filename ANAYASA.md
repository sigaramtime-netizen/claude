# 📜 ANAYASA v9 (SON) — BRN Teknoloji ERP Çalışma Sistemi

> Tek geçerli kaynak bu dosyadır. v8'den tek fark: **Claude'a İÇERİK NASIL GİDER** kuralı netleşti.

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
| `claude` | 🌍 PUBLIC | GM1 paneli: direktif/rapor/denetim/docs/kanıt — hepsi SANSÜRLÜ METİN |

**Senkron:** Otomatik değil; KÖPRÜ yapar. Public her zaman private'ın SANSÜRLÜ YANSIMASIDIR.

## 3) ⭐ CLAUDE'A İÇERİK NASIL GİDER (EN ÖNEMLİ KURAL)

**KURAL: Claude'a ASLA ZIP ve RESİM (PNG) GÖNDERİLMEZ. Her şey METİN olur.**

Neden:
- Claude web, GitHub'daki **zip'i (binary) indirip açamıyor** → görmezden geliyor/eksik görüyor.
- Claude web, **resim (PNG) okuyamıyor**.
- Zip/uzun dosya **kotayı erken bitiriyor**.

Çözüm (kalıcı):
- Claude'un ihtiyacı olan HER ŞEY public repoda **ayrı .md/.txt dosyası** olarak durur.
- Claude bunları **raw link** ile okur (tek seferde küçük metin, kota dostu):
  `https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/<YOL>`
- Kod incelemesi gerekiyorsa, ilgili dosya(lar) **metin olarak** public'e konur (`.py` içeriği
  `.txt`/`.md` içine). Kod public'e çıkmadan önce SANSÜRLENİR (gerçek isim → MÜŞTERİ-A).
- Ekran görüntüsü istenen kanıtlarda: PNG YERİNE coder **metin kanıt** verir
  (test çıktısı, HTTP durum listesi, dosya listesi). Görsel kanıt gerekirse köprü
  ekranı "şu sayfa 200 döndü, şu alanlar mevcut" diye METNE çevirir.

## 4) GÜNLÜK DÖNGÜ

```
1. Kral → Claude'a "şu görevi direktif yaz / şu raporu denetle"
2. Claude → public repoyu RAW LİNK ile okur → kararını metin yazar
3. Kral → kararı BU pencereye yapıştırır
4. KÖPRÜ → private repoya işler + sansürlü METİN kopyayı public'e koyar + DURUM günceller
5. Kral → Coder'a "devam et" → Coder kodlar, private'a rapor+kanıt (metin) push'lar
6. KÖPRÜ → yeni rapor/kanıt/kodun sansürlü METİN hallerini public'e koyar + denetim paketi hazırlar
7. 1. adıma dön
```

## 5) PUBLIC'E GİREN / GİRMEYEN

- ✅ GİRER (metin): direktifler, raporlar, denetimler, paket md'leri, DURUM/ROL/ANAYASA/BRİFİNG,
  `docs/` (tüm faz özetleri), test ÇIKTILARI, regresyon logları, dosya listeleri,
  gerektiğinde SANSÜRLÜ kod metni.
- ❌ GİRMEZ: ZIP, PNG/resim, `data/*.db`, ham `kod/*.py` (sansürsüz), gerçek müşteri adı/belge no/tutar.

**SANSÜR:** gerçek isim → `MÜŞTERİ-A/B`, marka → `MARKA-A/B/C`, belge no → `BELGE-NNN`,
gerçek tutar → demo tutarlar.

## 6) VARDIYA (Claude hakkı bitince)

- Kullanıcı ARENA GM2'ye yazar → GM2 GitHub'daki son durumu okuyup kaldığı yerden sürdürür.
- Claude geri gelince iş Claude'a döner. İş kaybı olmaz.

## 7) KÖPRÜ NE YAPAR / YAPMAZ

- ✅ YAPAR: kararları işlemek, sansür + senkron, metin paket hazırlamak, raw link vermek,
  coder iddialarını TARAFSIZ doğrulamak (testleri kendi çalıştırıp kanıt üretmek).
- ❌ YAPMAZ: direktif/denetim KARARI vermek (GM1'in), kod yazmak (coder'ın).

## 8) MEVCUT DURUM

- Proje v1.39.0. D001–D007 ONAYLANDI.
- **D008: 1.tur REVİZYON** (köprü zip hatası → 5 doküman Claude'a ulaşmadı; dokümanlar
  aslında mevcut). 2.tur: dokümanlar public'te METİN olarak, GM1 okuyacak.
