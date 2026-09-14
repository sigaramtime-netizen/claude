# GM1-PAKET — D010 Denetim Paketi (Claude için)

> **Denetleyen:** GM1 (Claude) — D010 bağımsız denetim
> **Konu:** D010 — Uygulama İçi Yedekleme & Geri Yükleme (yalnız Admin)
> **Sürüm:** v1.40.0 → **v1.41.0**
> **Coder commit:** `a438765`
> **Tarih:** 2026-09-14
> **Nöbet devri:** `devir/D010-gm2-den-gm1.md`

---

## 1. Nasıl denetleyeceksin (ANAYASA v12)

- **ZIP → sohbete dosya yüklemesi:** Claude web sandbox internet YOK; zip'i link'ten
  indiremezsin. Kral zip'i sohbete dosya olarak yükleyecek. Sen zip'i açıp kodları
  oku ve GEREKİRSE kendi ortamında testleri çalıştır.
- **.md / .txt → raw link:** Aşağıdaki linkler raw.githubusercontent.com üzerinden
  metin olarak okunur.
- Karar formatı: `SONUÇ: ONAYLANDI` veya `SONUÇ: REVIZYON` + gerekçe maddeleri.
  REVIZYON ise madde madde ne düzeltilecek yaz.

## 2. Kaynaklar

### ZIP (sansürlü — kral yükleyecek)
`paketler/BRN-Teknoloji-ERP-v1.41.0-D010-GM1-denetim.zip`
- MD5: `e595785f614f3c6e5d382a7152d32d31`
- SHA256: `d199744c603e28c24707b60fec326b561358f174cfd3292851017b1364d902f5`
- İçerik: 271 dosya, PNG yok, `data/yedek` yok, demo seed'li DB var.

### Kod (raw link, metin)
- `kod-inceleme/D010/D010-diff.txt` — D009→D010 tam diff (707 satır)
- `kod-inceleme/D010/yedek.py.txt` — yeni web modülü (169 satır)
- `kod-inceleme/D010/yedek_al.py.txt` — refactor (179 satır)
- `kod-inceleme/D010/test_d010_yedekleme.py.txt` — yeni test (210 satır)
- `kod-inceleme/D010/yedekler.html.txt` — yeni şablon
- `kod-inceleme/D010/CHANGELOG.md.txt`, `config.py.txt`, `app.py.txt`

### Süreç belgeleri (raw link)
- Direktif: `gm-direktifleri/D010-yedekleme-geri-yukleme.md`
- Coder raporu: `coder-raporlari/R010-yedekleme-geri-yukleme.md`

## 3. Denetim kontrol listesi (kabul kriterleri)

- [ ] `POST /ayarlar/yedek/al` → yeni `erp-*.db` + integrity ok
- [ ] Liste / indir / sil çalışır; **Admin dışı her rol 403**
- [ ] `indir` + `geri-yukle` rotalarında **path traversal reddi** (`../` → 400/403)
- [ ] Geri yükleme öncesi **otomatik güvenlik yedeği**; bozuk dosya geri yüklenmez
- [ ] **Yeni tablo / migration YOK**; iş mantığı (K1–K32, belge zincirleri, mali etki) değişmez
- [ ] `test_d010_yedekleme.py` + tam regresyon (25 dosya) yeşil
- [ ] ZIP (sansürlü, PNG'siz, demo seed'li DB) + MD5/SHA256

## 4. Köprü bağımsız doğrulaması (GM1 referansı)

- `test_d010_yedekleme.py` → **16/16** ✅
- Tam regresyon 25 dosya → **561/561, 0 başarısız** ✅
- Zip MD5/SHA256 birebir ✅; 271 dosya; PNG/`data/yedek`/`__pycache__` yok; demo DB temiz ✅
- Geri yükleme: bütünlük → güvenlik yedeği → `backup()` API (WAL güvenli) → `init_db()` → son doğrulama ✅
- Path traversal: regex whitelist + basename eşitliği + `[^/]+` rota deseni ✅

## 5. Bilinen sapma (önemli)

Coder'ın ORİJİNAL zip'inde D009'daki aynı sansür kalıntısı tekrar oluştu
(`kod/test_d007_iyilestirmeler.py` + `docs/D007-kullanici-bildirimleri-ozet.md`
→ gerçek müşteri adı). Köprü SANSÜRLEDİ; sana verilen zip TEMİZ. Bu kalıntı D010
mantığını ETKİLEMEZ (D007 test fişkırtısı) ama coder'ın kaynak dosyalarında
düzeltilmesi gereken tekrarlayan bir kusur olarak kayda geçti.
