# Devir: GM2 → GM1 (Claude) — D010 Denetimi

- **Tarih:** 2026-09-14
- **Devreden:** GM2 (Arena GM)
- **Devralan:** GM1 (Claude — kota yenilendi, D010 denetimi için devreye alındı)
- **Konu:** D010 — Uygulama İçi Yedekleme & Geri Yükleme (yalnız Admin) — v1.41.0

## Arka Plan

1. Kral yeni ihtiyaç bildirdi; coder aday konu hazırladı; GM2 karar verdi:
   **D010 = Uygulama içi yedekleme & geri yükleme** (coder önerisi kabul edildi).
   (Not: kralın "kategori/para birimi ekleyemiyorum" şikâyeti AYRI bir konu olarak
   saklandı — muhtemel D011. Bkz. `gm-direktifleri/D010-yedekleme-geri-yukleme.md`
   "ALTERNATİF ADAY KONULAR" bölümü.)
2. Coder D010'u kodladı ve push etti (commit `a438765`, v1.41.0).
3. Köprü bağımsız doğruladı: `test_d010_yedekleme.py` **16/16**, tam regresyon
   **25 dosya 561/561, 0 başarısız**, zip MD5/SHA256 doğru.
4. **Köprü sansür işlemi:** coder'ın orijinal zip'inde 2 dosyada D009'daki aynı
   kalıntı yine vardı (`kod/test_d007_iyilestirmeler.py`, `docs/D007-kullanici-bildirimleri-ozet.md`
   → gerçek müşteri adı). Köprü D009 deseniyle sansürledi (→ MÜŞTERİ-A) ve temiz zip üretti.
   GM1'in denetleyeceği zip SANSÜRLÜ olandır.

## GM1'in Görevi (Claude)

D010'u bağımsız denetle. Kaynaklar:

1. **ZIP (sansürlü):** `paketler/BRN-Teknoloji-ERP-v1.41.0-D010-GM1-denetim.zip`
   — kral bunu sohbete dosya olarak yükleyecek (ANAYASA v12 2. KURAL: Claude web
   sandbox internet yok; link'ten zip indirilemez, sohbet yüklemesi şart).
   MD5 `e595785f614f3c6e5d382a7152d32d31` / SHA256 `d199744c603e28c24707b60fec326b561358f174cfd3292851017b1364d902f5`
2. **Kod (raw link, .md/.txt):** `kod-inceleme/D010/` altında `D010-diff.txt`,
   `yedek.py.txt`, `yedek_al.py.txt`, `test_d010_yedekleme.py.txt`,
   `yedekler.html.txt`, `CHANGELOG.md.txt`, `config.py.txt`, `app.py.txt`.
3. **Coder raporu:** `coder-raporlari/R010-yedekleme-geri-yukleme.md`
4. **Direktif:** `gm-direktifleri/D010-yedekleme-geri-yukleme.md`

## GM1'den Beklenen Çıktı

`SONUÇ: ONAYLANDI` veya `SONUÇ: REVIZYON` + maddeler. Kral çıktıyı köprüye
yapıştırır; köprü `denetim-raporlari/R010-denetim.md` olarak iki repoya işler.

## Köprü Bağımsız Doğrulama Özeti (GM1'e referans)

- `python3 test_d010_yedekleme.py` → **16/16** ✅ (admin 200; Depo 403 GET+POST;
  traversal 403/404; indir octet-stream; sil; geri-yükle roundtrip + güvenlik
  yedeği; bozuk yedek reddi; /api/saglik 1.41.0; FK 0; kalıntı yok)
- Tam regresyon 25 dosya → hepsi rc=0, gerçek başarısız 0 ✅
- Zip: 271 dosya, PNG yok, `data/yedek` yok, `__pycache__` yok, demo seed'li DB var.
- Geri yükleme mekanizması: SQLite `backup()` API ters yönde (WAL güvenli);
  bütünlük → güvenlik yedeği → backup → `db.init_db()` → son doğrulama sırası doğru.
- Path traversal: `_gecerli()` regex (`^erp-\d{8}-\d{6}(-\d{6})?\.db$`) + basename
  eşitliği; `[^/]+` rota deseni. Sağlam.
