# D009 — MİKRO-KARARLAR (GM1 = Claude, kesin kararlar)

> Coder bu dosyaya göre ilerler. GM1 2026-09-12 tarihinde netleştirdi.

---

## KARAR 1 — Teslim formatı: ZIP (tek ve kesin)

- **"Kalıcı zipsiz kural" diye bir şey YOKTUR.** GM1 böyle bir kuralı hiç onaylamadı;
  bu, köprünün ara dönem yazdığı hatalı bir nottan kaynaklandı ve iptal edildi.
- **KOD / MANTIK / GÜVENLİK değiştiren her paket** (D009 dahil) için: güncel kaynak kod +
  demo seed'li DB + testler **tek ZIP içinde** teslim edilir, **MD5/SHA256** ile.
- Zip **sansürlü** (gerçek isim → MÜŞTERİ-A vb.), **PNG/resim içermez**.
- Format, D007/D008 zip turlarıyla **birebir aynı**.
- Ek TXT kanıt paketi İSTENMEZ (GM1 kendi testini kendisi koşturur; zip yeterli).
- "Metin/raw-link yeterli" yalnızca **saf dokümantasyon** paketleri içindir (istisna).

## KARAR 2 — CSRF tasarımı: HİBRİT (token + Origin/Referer kontrolü)

GM1'in seçimi: **Hibrit**. Uygulama kuralları (aynen):

1. **Token varsa** → token eşleşmeli (gerçek tarayıcı formu → korunur).
2. **Origin/Referer başlığı varsa** → host eşleşmeli (cross-site istek → 403).
3. **İkisi de yoksa** (örn. mevcut testlerin düz `requests` POST'ları) → **dokunulmaz**
   (ret edilmez), böylece 527 mevcut kontrol yeşil kalır.

**Test yükü:**
- Mevcut 271 test POST'una **DOKUNULMAZ** (geriye dönük CSRF token eklenmez) —
  D009'un "mevcut hiçbir test bozulmayacak" maddesinin gereği.
- Yeni `test_d009_guvenlik.py` yalnızca şu iki senaryoyu kapsar:
  - yanlış CSRF token → 403,
  - cross-origin token'sız POST → 403.

**Neden Hibrit:** Direktifin "form'a gizli alan + sunucu tarafı doğrulama" kriterini tam
karşılar (token alanı gerçekten doğrulanır); "Yalnız Origin/Referer" bunu karşılamaz;
"Katı token" ise 271 mevcut testi bozar. Hibrit, güvenlik açığını kapatırken regresyonu korur.

---

## ÖZET (coder için)

- Teslim: **tek ZIP** (sansürlü + demo DB + testler + MD5/SHA256).
- CSRF: **Hibrit** (yukarıdaki 3 kural + 2 yeni test senaryosu).
- Mevcut testlere dokunma; yalnızca `test_d009_guvenlik.py` eklenir.
