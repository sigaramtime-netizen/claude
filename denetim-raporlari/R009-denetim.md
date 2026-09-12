# R009 DENETİM RAPORU — D009 (Güvenlik & Sağlamlık Sertleştirme)

- **Denetleyen:** GM2 (Arena GM) — nöbet devraldı (GM1 Claude'un günlük hakkı dolmuştu)
- **Tarih:** 2026-09-12
- **İlgili görev:** D009 — SQL enjeksiyonu, oturum, dosya yükleme, CSRF, kaba kuvvet, yetki matrisi
- **Sürüm:** v1.40.0

---

## SONUÇ: ONAYLANDI ✅

**Karar:** D009 MÜHÜR — v1.40.0 kabul edildi.

### Kanıt dayanağı (denetimde kullanılan doğrulamalar)

1. **KÖPRÜ bağımsız test çalıştırması (Arena danışman, tarafsız):**
   - `test_d009_guvenlik.py` → **18/18** (canlı HTTP sunucusunda)
   - Tam regresyon → **24 dosya, 545/545, 0 başarısız** (her dosya tek tek)
2. **SQL enjeksiyon:** tüm değerler parametrik (`?`); f-string yalnızca sabit tablo/kolon adı
   ve `PRAGMA table_info` — ham birleştirme YOK.
3. **CSRF (Hibrit, GM1 mikro-kararıyla):** `core.py` içinde `csrf_gecerli()` —
   token varsa eşleşme, Origin/Referer varsa host eşleşme (cross-site → 403),
   ikisi yoksa legacy dokunulmaz (regresyon korunur).
4. **Oturum:** `secrets.token_urlsafe(32)` (kriptografik) + 12 saat hareketsizlik süresi +
   `/cikis` sunucu tarafı silme.
5. **Kaba kuvvet:** `kullanici` tablosuna `basarisiz_giris_sayisi` + `kilit_bitis`
   (idempotent migrasyon); 5 hatalı → 15 dk kilit.
6. **Dosya yükleme:** uzantı beyaz listesi + sunucu tarafı 15 MB + traversal temizliği
   (mevcuttu, testle kanıtlandı).
7. **Yetki matrisi:** tüm `/api/*` giriş ister; anonim yalnız `/giris` + `/saglik` (statik JSON).
8. **Zip bütünlüğü:** MD5/SHA256 doğrulandı; KÖPRÜ zip'te 2 dosyada sansürsüz gerçek müşteri
   adı yakaladı → sansürleyip yeniden paketledi (kişi adı → `MÜŞTERİ-A`), public'te sızıntı YOK.
9. **K1 (şirket izolasyonu) + rol/yetki davranışı:** değişmedi (izolasyon testleri yeşil).

> Not: GM2 kararı metin olarak kral üzerinden iletildi; ayrıntılı madde-madde gerekçe
> GM2'den gelirse bu rapora eklenir.

---

**Sonraki adım:** Proje v1.40.0. Sıradaki iş D010 (GM2 veya GM1 planlayacak).
