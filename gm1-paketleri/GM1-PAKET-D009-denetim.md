# GM1 DENETİM GÖREVİ — D009 (Güvenlik & Sağlamlık Sertleştirme)

> Sen bu projenin GM1'sin (Claude). D009 coder raporunu DENETLE.
> Direktif (D009) + mikro-kararlar ile yapılanı (R009 + kod + test) karşılaştır.
> Çıktını şu formatta ver: **SONUÇ: ONAYLANDI / REVIZYON** + madde madde gerekçe
> (REVİZYON ise coder'ın düzelteceği maddeleri numaralı listele).

---

## 1) DİREKTİF + MİKRO-KARARLAR (özet)

- **D009 direktifi:** `gm-direktifleri/D009-guvenlik-sertlestirme.md` (public panelde)
- **Mikro-karar (GM1 onaylı):** `gm-direktifleri/D009-mikro-karar.md`
  - CSRF = **HİBRİT** (token + Origin/Referer; ikisi yoksa legacy dokunulmaz)
  - Teslim = **ZIP** (sansürlü + demo DB + testler + MD5/SHA256)

## 2) CODER RAPORU (R009) — özet

R009'un iddiaları:
1. **SQL enjeksiyon:** tüm sorgular parametrik; f-string yalnızca sabit tablo/kolon adı; 0 ham sorgu.
2. **Oturum:** `secrets.token_urlsafe(32)` + 12 saat hareketsizlik süresi + `/cikis` sunucu tarafı silme.
3. **Kaba kuvvet:** 5 hatalı → 15 dk kilit (kullanici tablosuna 2 alan, idempotent).
4. **Dosya yükleme:** uzantı beyaz listesi + 15MB sunucu limiti + traversal temizliği (zaten vardı, testlendi).
5. **CSRF:** Hibrit uygulandı (form gizli alanı vardı ama sunucu doğrulaması yoktu → eklendi).
6. **Yetki matrisi:** tüm `/api/*` giriş gerektiriyor; anonim yalnız `/giris` + `/saglik` (statik JSON).
7. **Test:** test_d009 18/18 + tam regresyon 24 dosya 545/545.

## 3) KÖPRÜ BAĞIMSIZ DOĞRULAMASI (Arena — tarafsız teknik kanıt)

Köprü (Arena) coder'ın iddialarını YERELDE bağımsız doğruladı:

- **test_d009_guvenlik.py → 18/18 GEÇTİ** (canlı HTTP sunucuda çalıştırıldı)
- **Tam regresyon → 24 dosya, 545/545, 0 başarısız** (her dosya tek tek çalıştırıldı)
- **SQL taraması:** f-string `execute` yalnızca sabit tablo/kolon adı + `PRAGMA table_info`;
  değerler hep parametre (`?`). Ham birleştirme YOK.
- **CSRF:** `core.py` içinde `csrf_gecerli()` hibrit kontrol + dispatch'e bağlı (POST'ta çağrılıyor).
- **Oturum:** `app.py` `secrets.token_urlsafe(32)`; `core.py` `load_session` 12 saat + `son_erisim`.
- **Kaba kuvvet:** `db.py` `basarisiz_giris_sayisi` + `kilit_bitis` (idempotent); `app.py` `/giris` sayaç.
- **Zip hash:** coder'ın MD5/SHA256'sı zip ile birebir eşleşti (doğrulandı).

> NOT: Bu doğrulama KARAR değildir — yalnızca tarafsız teknik kanıttır.
> Karar (ONAY/REVİZYON) SENİNDİR. GM1 kuralı gereği zip'i indirip testleri SEN de çalıştırmalısın.

## 4) KOD ZIP LİNKİ (güncel kaynak kod, sansürlü)

İndir: https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/paketler/BRN-Teknoloji-ERP-v1.40.0-D009-GM1-denetim.zip

- İçerik: 267 dosya (kod + şablonlar + statik + docs + testler + demo seed'li DB)
- Sansür: gerçek kişi adı → `MÜŞTERİ-A` (markalar demo ticari isim, bırakıldı). PNG YOK.
- DB: demo seed (5 kullanıcı, 12 stok, 1 şirket, gerçek kişi verisi YOK).
- MD5: dfc3b9ac171af81e084a31f79027d03b
- SHA256: e75da953dadd5e68f11eba6bc59fa8d7d36f6c2cf523c1f7f1a41b30ba111103

Çalıştırma: `cd BRN-Teknoloji-ERP-v1.40.0/kod && python3 app.py` → http://localhost:8080 (admin/1234)
Test: `python3 test_d009_guvenlik.py` (18/18 beklenir); tam regresyon: `for t in test_*.py; do python3 $t; done`

## 5) KANIT DOSYALARI (private repoda)

- `kanitlar/v1.40.0/D009-test-ciktisi.txt` — test_d009 18/18
- `kanitlar/v1.40.0/D009-tam-regresyon.txt` — 24 dosya 545/545
- `kanitlar/v1.40.0/D009-degisen-dosyalar.txt` — değişen dosya listesi
- `kanitlar/v1.40.0/D009-zip-hash.txt` — coder'ın hash kaydı
