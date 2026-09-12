# 📜 ANAYASA v8 (SON) — BRN Teknoloji ERP Çalışma Sistemi

> Tek geçerli kaynak bu dosyadır. İki repo vardır ve SENKRONİZASYONU KÖPRÜ YAPAR.

---

## 1) ROLLER

| Rol | Sahip | Görev |
|---|---|---|
| **GM1 (beyin)** | **CLAUDE (web)** | Direktif yazar, coder'ı denetler, ONAYLANDI/REVİZYON kararı verir |
| **GM2 (yedek GM)** | **ARENA GM** (gm@arena) | Claude'un günlük hakkı bitince işi devralır |
| **Coder** | **ARENA CODER** (coder@arena) | Kodu yazar, test eder, rapor+kanıt yükler |
| **KÖPRÜ + Danışman** | **ARENA (bu pencere)** | Claude'un kararlarını repolara işler, sansürler, senkron tutar |

## 2) İKİ REPO (ve senkronizasyon)

| Repo | Görünürlük | İçerik |
|---|---|---|
| `BRN-Teknoloji-ERP` | 🔒 PRIVATE | **kod/**, ham kanıtlar, her şeyin aslı (kaynak) |
| `claude` | 🌍 PUBLIC | GM1 paneli: direktifler, raporlar, denetimler, docs/, sansürlü kanıtlar, DURUM/ROL/ANAYASA |

**SENKRONİZASYON KURALI:** İki repo **otomatik değil**, KÖPRÜ tarafından senkron tutulur:
- Her Claude kararı → KÖPRÜ önce PRIVATE repoya, sonra SANSÜRLÜ kopyasını PUBLIC repoya işler.
- Coder private repoya push edince → KÖPRÜ rapor/kanıtın sansürlü halini public'e kopyalar.
- Kural: public her zaman private'ın SANSÜRLÜ YANSIMASIDIR (kod + gerçek veri ASLA public'e çıkmaz).

## 3) VARDIYA (Claude hakkı bitince)

- Claude'un günlük hakkı bitti → kullanıcı **ARENA GM2**'ye yazar → GM2, GitHub'daki
  son durumu (DURUM.md + denetim-raporlari + gm1-paketleri) okuyarak kaldığı yerden
  GM işini sürdürür. İş kaybı OLMAZ (her şey repolarda).
- Claude geri gelince iş yine Claude'a döner.

## 4) GÜNLÜK DÖNGÜ

```
1. Kral → Claude'a "şu görevi direktif yaz / şu raporu denetle"
2. Claude → public repoyu raw link ile okur → kararını metin yazar
3. Kral → kararı BU pencereye yapıştırır
4. KÖPRÜ (ben) → private repoya işler + sansürlü kopyayı public'e koyar + DURUM.md günceller
5. Kral → Coder'a "devam et" → Coder kodlar, private repoya rapor+kanıt push'lar
6. KÖPRÜ → yeni raporun sansürlü kopyasını + denetim paketini public'e koyar
7. 1. adıma dön
```

## 5) PUBLIC'E GİREN / GİRMEYEN

- ✅ GİRER: direktifler, raporlar, denetimler, paketler, DURUM/ROL/ANAYASA/BRİFİNG,
  `docs/` (47 doküman), test ÇIKTILARI, regresyon logları, dosya listeleri.
- ❌ GİRMEZ: `kod/` (.py + şablonlar), `data/erp.db`, EKRAN GÖRÜNTÜLERİ (PNG),
  `*_degisen_dosyalar.txt` (kod dökümü), gerçek müşteri adı / belge no / gerçek tutar.

**SANSÜR EŞLEMELERİ:** gerçek isim → `MÜŞTERİ-A/B`, marka → `MARKA-A/B`,
belge no → `BELGE-NNN`, gerçek tutar → demo tutarlar.

## 6) BEN (KÖPRÜ) NE YAPARIM / YAPMAM

- ✅ YAPARIM: Claude kararlarını işlemek, sansür + senkron, DURUM.md güncellemek,
  denetim paketleri + brifing hazırlamak, raw link vermek, tıkanıklık desteği.
- ❌ YAPMAM: kendi başıma direktif/denetim kararı (GM1'in işi), kod yazmak (coder'ın işi).

## 7) MEVCUT DURUM

- Proje v1.39.0. D001–D006 ONAYLANDI. **D007 KODLANDI → GM1 (Claude) onayı bekliyor.**
- Public panelde: GM1-BRIFING.md + 47 docs + sansürlü kanıtlar + D007 paketi hazır.
- Claude'a verilecek ilk link: public `GM1-BRIFING.md` raw linki + D007 paketi.
