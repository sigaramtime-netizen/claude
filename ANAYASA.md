# 📜 ANAYASA v7 (SON) — BRN Teknoloji ERP Çalışma Sistemi

> Tek geçerli kaynak bu dosyadır. v6'nın "public repo yok" maddesi iptal: artık iki repo var.

---

## 1) ROLLER

| Rol | Sahip | Görev |
|---|---|---|
| **GM1 (beyin)** | **CLAUDE (web)** | Direktif yazar, coder'ı denetler, ONAYLANDI/REVİZYON kararı verir |
| **GM2 (yedek)** | **ARENA GM** (gm@arena) | Claude yokken GM1'in işini yapar |
| **Coder** | **ARENA CODER** (coder@arena) | Kodu yazar, test eder, rapor+kanıt yükler |
| **KÖPRÜ + Danışman** | **ARENA (bu pencere)** | Claude'un çıktısını repolara işler; dokümanları public panele SANSÜRLÜ kopyalar |

## 2) İKİ REPO

| Repo | Görünürlük | İçerik |
|---|---|---|
| `BRN-Teknoloji-ERP` | 🔒 PRIVATE | **kod/**, kanıtların HAM hali, her şeyin aslı (kaynak) |
| `BRN-GM1-KONTROL` | 🌍 PUBLIC | Claude'un OKUMASI için: direktifler, raporlar, denetimler, DURUM/ROL/ANAYASA — hepsi SANSÜRLÜ |

### PUBLIC'e giren / girmeyen
- ✅ GİRER: `gm-direktifleri/`, `coder-raporlari/`, `denetim-raporlari/`, `gm1-paketleri/`,
  `DURUM.md`, `ROL.md`, `ANAYASA.md`, test ÇIKTILARI (sonuç listeleri), dosya listeleri.
- ❌ GİRMEZ: `kod/` (kaynak kod), `data/erp.db`, EKRAN GÖRÜNTÜLERİ (PNG),
  `kanit_*_degisen_dosyalar.txt` (kod dökümü), **gerçek müşteri adı / belge no / tutar**.

### SANSÜR KURALI (KÖPRÜ otomatik uygular)
- Gerçek müşteri adı → `MÜŞTERİ-A`, `MÜŞTERİ-B`...
- Gerçek belge no (IRS/IRA-2026-xxx) → `BELGE-001`...
- Gerçek tutarlar → demo tutarlar (1.000,00 / 500,00 gibi).
- Kaynak kod parçaları → "bkz: private repo" notu.

## 3) GÜNLÜK DÖNGÜ

```
1. Kral → Claude'a "şu görevi direktif yaz / şu raporu denetle"
2. Claude → metin üretir
3. Kral → metni BU pencereye yapıştırır
4. Ben (KÖPRÜ) → PRIVATE repoya işlerim; SANSÜRLÜ kopyasını PUBLIC repoya koyarım
5. Kral → Coder'a "devam et" → Coder kodlar, PRIVATE repoya rapor+kanıt push'lar
6. Ben → yeni raporun sansürlü kopyasını + denetim paketini PUBLIC repoya koyarım
7. Kral → Claude'a PUBLIC link verir → Claude okur, karar verir → 3. adıma dön
```

## 4) CLAUDE İÇERİĞİ NASIL OKUR

- PUBLIC repo + **raw.githubusercontent.com** linkleri. Public olduğu için Claude
  (web erişimi olan sürümü) linki okuyabilir.
- Okuyamazsa yedek yol: dosyayı GitHub'dan indir → Claude'a yükle.

## 5) BEN NE YAPARIM / YAPMAM

- ✅ YAPARIM: Claude çıktısını private repoya işlemek, sansürleyip public repoya
  kopyalamak, DURUM.md güncellemek, denetim paketleri hazırlamak, link vermek.
- ❌ YAPMAM: kendi başıma direktif/denetim kararı (GM1'in işi), kod yazmak (coder'ın işi).

## 6) MEVCUT DURUM

- Proje v1.39.0 — kod private repoda. D001–D006 ONAYLANDI. **D007 KODLANDI → GM1 (Claude) onayı bekliyor.**
- İlk köprü görevi: D007 denetim paketini public repoya koyup Claude'a link vermek.
