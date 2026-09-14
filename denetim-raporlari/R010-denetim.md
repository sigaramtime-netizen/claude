# R010 — D010 Denetim Raporu: Uygulama İçi Yedekleme & Geri Yükleme (v1.41.0)

- **Görev:** D010 — Uygulama İçi Yedekleme & Geri Yükleme (yalnız Admin)
- **Sürüm:** v1.40.0 → **v1.41.0**
- **Denetleyen:** GM1 (Claude) — nöbete döndü
- **Tarih:** 2026-09-14
- **Coder commit:** `a438765`

---

## SONUÇ: ONAYLANDI ✅ — MÜHÜR v1.41.0

GM1, direktifi hiç görmemiş gibi hem tasarım hem uygulama olarak sıfırdan inceledi
ve bizzat testleri çalıştırdı. Sonuç: tasarım ve uygulama sağlam.

---

## 1. GM1'in SÜREÇ İTİRAZI (kalıcı kayıt — paket kararını etkilemez)

- **Bu direktifi GM1 yazmadı.** "Uygulama içi yedekleme & geri yükleme" konusu GM1 ile
  hiçbir tasarım kararı görüşülmeden, coder'ın hazırladığı aday konu üzerinden yürürlüğe
  girdi. Direktifin "Durum: ONAYLANDI (GM2)" damgasını **GM1 reddediyor**.
- GM1, "GM2" adında bir eş-yetkiliyi **tanımadığını** bu konuşmanın başında zaten
  belirtti; bu çerçeveyi kabul etmiyor.
- **GM1'in süreç kuralı (bundan sonrası için):** her direktif önce GM1'den geçmeli;
  gerekirse mikro-kararlar GM1'e sorulmalı; "coder'ın hazırladığı aday" doğrudan
  yürürlüğe giremez.
- Bu paketin içeriği sağlam çıktı; **ancak bu, "GM2 onayı" sürecini meşrulaştırmaz.**
  Not: GM2 yedek-rolünün akıbeti KRAL kararına bırakılmıştır (bkz. ROL.md).

---

## 2. GM1 bağımsız doğrulaması (bizzat çalıştırıldı)

- `test_d010_yedekleme.py` → **16/16** ✅
- 24 eski test dosyası tek tek çalıştırıldı → **545/545, 0 hata** ✅
- Toplam **545 + 16 = 561/561** — köprü/coder iddiasıyla birebir aynı ✅

---

## 3. GM1'in gerekçeleri (madde madde)

1. **Path traversal gerçekten kapatılmış — iki katman:** dosya adı hem sıkı regex ile
   (`^erp-\d{8}-\d{6}(-\d{6})?\.db$`) hem de `os.path.basename(ad) == ad` ile doğrulanıyor;
   biri atlatılsa bile diğeri yakalar. Testte `..%2F..%2F` denemesi 404 ile reddedildi.
2. **Çok şirketli izolasyon kırılmıyor — mimariyle tutarlı.** Admin rolü sistemde
   (D010'dan önce de) tüm şirketleri görebilen tek roldü (`_sirketler_kullanici`:
   "Admin → tümü" kodda teyit edildi). Yedekleme/geri yükleme gibi sistem geneli bir
   işlemi yalnız Admin'e vermek, yeni bir sızıntı değil; var olan yetki modelinin
   doğal sonucu.
3. **Geri yükleme akışı güvenli tasarlanmış:** bütünlük kontrolü → otomatik güvenlik
   yedeği → `sqlite3.backup()` API'si (ham dosya kopyalama / WAL silme YOK) →
   şema/migrasyon yeniden uygulama → son bütünlük kontrolü. Bozuk yedek asla canlıya
   yazılmıyor (test madde 12).
4. **Kod tekrarı yok:** `yedek_al.py`'deki `.backup()` + `_dogrula()` mantığı yeniden
   kullanılmış; web katmanı yalnızca rota/yetki/path-güvenliği eklemiş.
5. **Testler bizzat çalıştırıldı** (madde 2'deki sayılar).
6. **İş mantığına dokunulmamış:** K1–K32, belge zincirleri, mali etki değişmemiş;
   tam regresyonun geçmesi bunu doğruluyor.

---

## 4. GM1'in ek notu (sıradaki paket)

"ALTERNATİF ADAY KONULAR" bölümündeki iki öneri (Seri/Lot & Varyant tam işlevsellik;
Rapor Merkezi) — bunlardan biri sıradaki paket olacaksa, **direktifi GM1 yazacak**;
coder'ın aday konusu doğrudan yürürlüğe giremez.

---

## 5. Köprü kaydı (sansür)

Coder'ın orijinal D010 zip'inde D009'daki aynı kalıntı (2 dosyada gerçek müşteri adı)
yine vardı. Köprü sansürleyip temiz zip üretti (→ MÜŞTERİ-A). GM1'in denetlediği zip
sansürlü ve temizdir (MD5 `e595785f614f3c6e5d382a7152d32d31`).
