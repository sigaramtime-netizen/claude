# R010 — Uygulama İçi Yedekleme & Geri Yükleme (v1.41.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D010 — Uygulama İçi Yedekleme & Geri Yükleme (yalnız Admin)
- **Sürüm:** 1.40.0 → **1.41.0**
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-14
- **Direktif:** `gm-direktifleri/D010-yedekleme-geri-yukleme.md` (GM2 onayı: "D010 kodla")

---

## 1. Yapılan İş

1. **`kod/yedek.py` (YENİ web modülü)** — `/ayarlar/yedek*` rotaları (tümü `roles=("Admin",)`):
   - `GET /ayarlar/yedekler` — `data/yedek/` altındaki yedekleri listeler (ad, boyut, bütünlük, tablo).
   - `POST /ayarlar/yedek/al` — SQLite `.backup()` + `PRAGMA integrity_check`; bozuk yedek diske bırakılmaz.
   - `GET /ayarlar/yedek/indir/<dosya>` — octet-stream indirme.
   - `POST /ayarlar/yedek/<dosya>/sil` ve `.../geri-yukle`.
   - **Path traversal:** dosya adı yalnızca `erp-YYYYMMDD-HHMMSS(-ffffff).db` deseninde kabul
     (`_gecerli` regex); geçersiz ad 403, kodlanmış `../` 404.
   - **Geri yükleme sırası:** bütünlük doğrula → otomatik güvenlik yedeği → **backup API ile
     ters yönde geri yükle** (WAL güvenli) → `db.init_db()` (eski yedekse eksik kolonları ekle)
     → son bütünlük doğrulaması.
2. **`kod/yedek_al.py` refactor** — `yedek_al(hedef, sakla)` fonksiyonu çıkarıldı (CLI + web
   ortak kullanır); `main()` buna bağlandı.
3. **Bugfix (D010'un ortaya çıkardığı):** yedek dosya adı saniye çözünürlüklüydü
   (`erp-YYYYMMDD-HHMMSS.db`); aynı saniyede alınan iki yedek (örn. geri yükleme sırasındaki
   güvenlik yedeği) **birbirini eziyordu** → dosya adına mikrosaniye eklendi. Ayrıca CLI
   `main()` içinde hedef dizin `stat` sıralaması düzeltildi.
4. **`kod/templates/ayarlar/yedekler.html` (YENİ)** + Ayarlar hub'ına "💾 Yedekleme" kartı.
5. **`kod/config.py`** `SURUM = "1.41.0"`; **`kod/CHANGELOG.md`** v1.41.0 girdisi.
6. **`test_d010_yedekleme.py` (YENİ)** — 16 kontrol.

## 2. Kabul kriterleri kontrolü

| Kriter | Durum |
|---|---|
| `POST /ayarlar/yedek/al` → yeni `erp-*.db` + integrity ok | ✅ (test 3) |
| Liste/indir/sil çalışır; Admin dışı 403 | ✅ (test 4-5: Depo 403) |
| Path traversal reddi (indir + geri-yükle) | ✅ (test 6-7: 403/404) |
| Geri yükleme öncesi güvenlik yedeği; bozuk dosya geri yüklenmez | ✅ (test 10-12) |
| Yeni tablo / migration YOK; iş mantığı değişmedi | ✅ (yalnız rota + yardımcılar) |
| `test_d010_yedekleme.py` + tam regresyon yeşil | ✅ 16/16 + 561/561 |
| ZIP (sansürlü, PNG'siz, demo seed'li DB) | ✅ |

## 3. Test Sonuçları

```
python3 test_d010_yedekleme.py  → 16/16 ✅
Tam regresyon (25 dosya)       → 561/561, 0 başarısız ✅
PRAGMA foreign_key_check       → 0
```

Döküm: alinan_teklif 23, bakim 29, belge_sayac 9, coklu_sirket 16, crm 25, d007 31,
d009 18, **d010 16**, eksik_teslimat 21, f1 25, f2 34, f3 30, f4 22, f5a 18, f5b 18, f5c 18,
f6 18, izolasyon 22, izolasyon_mali 19, manuel_satir 28, pos 41, satin_alma 23, silme 23,
sirket_yonetimi 19, teklif_siparis_manuel 15 = **561**.

## 4. Geliştirme sırasında yakalanan ve düzeltilen hatalar

1. **Aynı saniyede çakışan yedek adı:** `%H%M%S` damgası iki yedeği aynı adla yazıyordu;
   geri yükleme sırasındaki güvenlik yedeği, geri yüklenecek yedeğin ÜZERİNE yazıyordu
   → mikrosaniye eklendi (`erp-YYYYMMDD-HHMMSS-ffffff.db`).
2. **İlk geri yükleme denemesi `shutil.copyfile` + elle `-wal/-shm` silme** kullanıyordu;
   bu, WAL kipindeki canlı DB'yi bozup sunucuda kalıcı `sqlite3.OperationalError: disk I/O
   error` yarattı → SQLite'ın `backup()` API'si ters yönde kullanılarak düzeltildi
   (CLI'ın yedek alma tarafında zaten kullanılan resmi mekanizma).
3. CLI `main()`: refactor sonrası hedef dizin oluşturulmadan `os.stat(hedef)` çağrılıyordu
   → sıralama düzeltildi.

## 5. Teslim (ZIP — ANAYASA v11 kuralı)

- `teslim/D010-v1.41.0.zip` — kaynak kod + şablonlar + statik + 25 test + **demo seed'li DB**
  (`data/erp.db`: 5 kullanıcı, 12 stok, FK 0). `data/yedek/` (çalışma zamanı yedekleri),
  `uploads/`, `__pycache__`, `ekran-goruntuleri/` (PNG) zip'e GİRMEZ.
- MD5 + SHA256: `kanitlar/v1.41.0/D010-zip-hash.txt`
- Kanıt: `kanitlar/v1.41.0/D010-tam-regresyon.txt`, `D010-test-ciktisi.txt`

## 6. Notlar

- Yeni tablo/migration YOK; K1/şirket izolasyonu ve rol davranışı değişmedi
  (`test_coklu_sirket` 16/16, `test_izolasyon_e2e` 22/22, `test_izolasyon_mali_e2e` 19/19).
- Yedekler tüm şirketlerin verisini içerdiğinden rotalar bilinçli olarak **yalnız Admin**.
- `.gitignore`'a `kod/data/yedek/` eklendi (yedekler repoya girmesin).
