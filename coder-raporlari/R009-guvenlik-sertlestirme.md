# R009 — Güvenlik & Sağlamlık Sertleştirme (v1.40.0) — KOD YÜKLEME & KONTROL RAPORU

- **Görev:** D009 — Güvenlik & Sağlamlık Denetimi (SQL enjeksiyon, oturum, dosya yükleme, CSRF, kaba kuvvet, yetki matrisi)
- **Sürüm:** 1.39.0 → **1.40.0**
- **Durum:** KODLANDI ✅ — GM onayı bekleniyor
- **Tarih:** 2026-09-12
- **Commit:** (aşağıda)

---

## 1. Tarama Sonuçları (mevcut durum → karar)

| Madde | Bulgu | Karar |
|---|---|---|
| **SQL enjeksiyon** | Tüm sorgular parametrik (`?` placeholder). f-string'ler yalnızca sabit tablo/kolon adı (whitelist, `_toplu_ayarla`) veya sabit WHERE parçası; `LIKE` değerleri (`like = f"%{q}%"`) daima parametre olarak bağlanıyor. Ham string birleştirme YOK. | Kod değişikliği gerekmedi; grep + test kanıtı. |
| **Oturum** | Token `secrets.token_urlsafe(32)` (kriptografik) ✅; HttpOnly+SameSite ✅; `/cikis` sunucu tarafı siler ✅. **Eksik:** boşta kalma (idle) süresi kontrolü yoktu (`son_erisim` kolonu vardı, kullanılmıyordu). | 12 saat hareketsizlik sonrası sunucu tarafı silme + `son_erisim` güncelleme (5 dk throttle) eklendi. |
| **Kaba kuvvet** | Yok. | `kullanici` tablosuna `basarisiz_giris_sayisi` + `kilit_bitis` (idempotent migrasyon); 5 hatalı → 15 dk kilit; başarılı girişte sıfırlama. |
| **Dosya yükleme** | Zaten sağlam: uzantı beyaz listesi (jpg/png/pdf), sunucu tarafı 15 MB limit, sunucu üretimli dosya adı (traversal yok). | Değişiklik gerekmedi; testle kanıtlandı. |
| **CSRF** | Formlarda `csrf` gizli alanı VAR ama **sunucu tarafında hiç doğrulanmıyordu**. | Hibrit (GM onaylı): (1) token alanı varsa oturum token'ıyla eşleşmeli; (2) Origin/Referer varsa host eşleşmeli (cross-site → 403); (3) ikisi de yoksa (eski test istekleri) dokunulmaz. |
| **Yetki matrisi** | Tüm `/api/*` uçları `roles=()` ile giriş gerektiriyor; anonim yalnız `/giris` + `/saglik` (sağlık probu, statik `{"durum":"ok"}`, hassas veri yok). Kaçak YOK. | Dokümante edildi + test. |

## 2. Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `config.py` | `SURUM = "1.40.0"` |
| `db.py` | SCHEMA + `_migrate`: `kullanici` + `basarisiz_giris_sayisi`, `kilit_bitis` |
| `app.py` | `/giris` kaba kuvvet: kilit kontrolü + sayaç + 5 deneme → 15 dk kilit + başarıda sıfırlama |
| `core.py` | `load_session` 12 saat süre kontrolü + `son_erisim` güncelleme; `csrf_gecerli()` hibrit kontrol + dispatch'e bağlama |
| `test_f6_cila.py` | 14. kontrol `surum == "1.40.0"` (sürüm artışı beklentisi) |
| `test_d009_guvenlik.py` | YENİ — 18 kontrol |

## 3. Test Sonuçları

```
test_d009_guvenlik.py  → 18/18 ✅
Tam regresyon (24 dosya) → 545/545, 0 başarısız ✅
PRAGMA foreign_key_check → 0
```

- 18 kontrol: SQL enjeksiyon (login + arama), oturum (kriptografik token + /cikis + süre),
  kaba kuvvet (5 yanlış → kilit, 6. deneme reddi, kilit kalkınca giriş), CSRF (yanlış token
  403, cross-origin 403, legacy POST çalışır), dosya yükleme (traversal temizliği, .exe reddi,
  15 MB limit, pdf kabul), yetki matrisi (`/api/*` anonim 302, `/saglik` sağlık probu 200),
  FK + kalıntı.
- 271 mevcut test POST'u (23 eski dosya) geriye dönük **dokunulmadı** — GM onaylı hibrit kural
  sayesinde token'sız/Origin'siz istekler aynen çalışıyor (regresyon 527 → 545, hiçbir eski
  kontrol bozulmadı).

## 4. Teslim (ZIP — GM onaylı, D008 kuralına uygun)

- `teslim/D009-v1.40.0.zip` — kaynak kod + şablonlar + statik + testler + **demo seed'li DB**
  (`data/erp.db`: 5 kullanıcı, 12 stok, 1 şirket, FK 0) + `docs/` + kök yönetişim md'leri.
  `__pycache__` ve `uploads/` hariç (sansürlü).
- MD5 + SHA256: `kanitlar/v1.40.0/D009-zip-hash.txt`
- Kanıt (ek bilgi): `kanitlar/v1.40.0/D009-tam-regresyon.txt`, `D009-test-ciktisi.txt`

## 5. Notlar

- Şifre hash'i (PBKDF2-HMAC-SHA256, K32) kapsam dışı — dokunulmadı.
- K1 (şirket izolasyonu), şube izolasyonu ve rol/yetki davranışı değişmedi (`test_izolasyon_e2e`
  22/22, `test_coklu_sirket` 16/16, `test_izolasyon_mali_e2e` 19/19).
- Yeni tablo YOK; yalnızca `kullanici` tablosuna 2 alan (idempotent).
