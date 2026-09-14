# D010 — Uygulama İçi Yedekleme & Geri Yükleme (Admin)

> **Durum:** ONAYLANDI — **GM1 (Claude) denetimiyle, 2026-09-14** (bkz. `R010-denetim.md`).
> GM1'in düzeltmesi: bu direktifi GM1 yazmadı; coder'ın aday konusu üzerinden yürürlüğe
> girmişti ve "GM2 onayı" damgası GM1 tarafından reddedilir. GM1 paketi sıfırdan denetleyip
> ONAYLADI; ancak bundan sonraki her direktif önce GM1'den geçmelidir.
> Sürüm: **v1.41.0**.

---

## BAŞLIK: D010 — Uygulama İçi Yedekleme & Geri Yükleme (Admin)

## ÖNCELİK: Yüksek

## GEREKÇE
- D009'da güvenlik katmanı sertleştirildi; felaket kurtarmanın diğer yarısı **yedekleme**.
- `kod/yedek_al.py` zaten var ama yalnızca **komut satırı** aracı — uygulama içinden
  (web arayüzü) yedek alınamıyor, listelenemiyor, indirilemiyor, geri yüklenemiyor.
- Gerçek kullanıcı (Admin) sunucuya SSH/cron erişimi olmadan yedek yönetemiyor.

## GEREKSİNİMLER
1. **Yedek listesi:** `GET /ayarlar/yedekler` (yalnız Admin) — `data/yedek/` içindeki
   `erp-*.db` dosyalarını listeler (ad, boyut, tarih, integrity durumu).
2. **Yedek al:** `POST /ayarlar/yedek/al` (yalnız Admin) — SQLite `.backup()` API'si ile
   tutarlı anlık görüntü `data/yedek/erp-YYYYMMDD-HHMMSS.db`; alındıktan sonra
   `PRAGMA integrity_check` doğrulanır; sonuç flash ile gösterilir.
3. **İndir:** `GET /ayarlar/yedek/indir/<dosya>` (yalnız Admin) — yalnızca `data/yedek/`
   altındaki dosyalar; path traversal koruması (dosya adı whitelist/gerçek yol kontrolü).
4. **Sil:** `POST /ayarlar/yedek/<dosya>/sil` (yalnız Admin) — yalnızca kendi ürettiği
   `erp-*.db` desenindeki dosyalar silinir.
5. **Döndürme (rotasyon):** varsayılan son **30** yedek saklanır, eskileri otomatik budanır
   (yedek_al.py davranışıyla birebir).
6. **Geri yükleme:** `POST /ayarlar/yedek/geri-yukle/<dosya>` (yalnız Admin) —
   geri yüklemeden ÖNCE otomatik güvenlik yedeği alınır; dosya integrity_check'ten
   geçmeden geri yüklenmez; sonuç flash ile gösterilir.

## KABUL KRİTERLERİ
- [ ] `POST /ayarlar/yedek/al` → yeni `erp-*.db` oluşur ve integrity "ok".
- [ ] Liste / indir / sil rotaları çalışır; Admin dışı her rol 403.
- [ ] `indir` ve `geri-yukle` rotalarında path traversal dosya adı reddedilir
      (`../` girişimi 400/403, dosya sistemine dokunulmaz).
- [ ] Geri yükleme öncesi otomatik güvenlik yedeği alınır; bozuk dosya geri yüklenmez.
- [ ] Yeni tablo / migration YOK; iş mantığı (K1-K32, belge zincirleri, mali etki) değişmez.
- [ ] Yeni `test_d010_yedekleme.py` eklendi; tam regresyon (25 dosya) yeşil.
- [ ] Teslim: ZIP (sansürlü, PNG'siz, demo seed'li DB — yedek klasörü hariç) + MD5/SHA256.

## İSTENEN KANITLAR
- [ ] `test_d010_yedekleme.py` — en az: yedek al+integrity, listele, indir, sil,
      Admin dışı 403, path traversal reddi, geri yükleme roundtrip.
- [ ] Tam regresyon çıktısı (25 dosya).
- [ ] ZIP + MD5/SHA256; değişen dosya listesi.

## TEKNİK NOTLAR
- `yedek_al.py` içindeki `sqlite3 .backup()` + integrity_check mantığı yeniden kullanılır
  (kod çoğaltma yerine `yedek_al.py`'ye bir `yedek_al(hedef, adet)` fonksiyonu eklenir,
  web katmanı onu çağırır).
- Yedekler `data/yedek/` altında tutulur; teslim zip'ine GİRMEZ (yalnız demo `data/erp.db` girer).
- Admin yetkisi mevcut `AYAR_WRITE`/`("Admin",)` deseniyle; K1 şirket izolasyonu yedeklerde
  geçerli değildir (yedek tüm şirketlerin verisini içerir — bu yüzden yalnız Admin).
- Sürüm: v1.40.0 → **v1.41.0**.

---

## ALTERNATİF ADAY KONULAR (GM isterse)

1. **Seri/Lot & Varyant tam işlevsellik** — şemada `seri_lot_takibi`/`varyant_takibi`
   bayrakları ve `stok_varyant` altyapısı var ama yönetim ekranı ve stok hareketlerine
   seri/lot girişi tam değil. Daha büyük kapsam, veri modeli dokunuşu riskli.
2. **Rapor Merkezi** — mevcut 18 rapor/csv/yazdır rotasını tek "Raporlar" ekranında
   toplamak + filtreli dönem raporları. Yeni tablo yok, kapsam orta.
