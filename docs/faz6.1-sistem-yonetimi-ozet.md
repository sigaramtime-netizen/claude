# Faz 6.1 — SİSTEM YÖNETİMİ (AYARLAR): Onay Paketi

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Kapsam:** K32 · **Durum:** onay bekleniyor

Bu paket, kullanıcı talebiyle eklenen **Sistem Yönetimi (Ayarlar)** bölümünün diğer modüllerle
aynı formatta sunumudur: veri modeli, rota listesi, ekran listesi ve **canlı test kanıtları**.

---

## 1) Veri modeli

**Yeni tablo açılmadı** (K4/K6 ilkesi). Mevcut tablolar kullanıldı:

| Tablo | Kullanım | Bu pakette dokunulan |
|---|---|---|
| `kullanici` | Kullanıcılar (ad, rol, `aktif`, `sube_id`, `sifre_hash`) | Ekle / rol / aktif-pasif / şifre |
| `firma` | Firma bilgileri (ünvan, vergi dairesi/no, adres, telefon, e-posta, logo) | Güncelleme ekranı |
| `meta` | `bildirim.kanal`, `entegrator_*` anahtarları | Kanal + entegratör ayarları |
| `sessionler` | Oturumlar | Şifre değişiminde diğer oturumları geçersiz kılma |
| `audit_log` | İşlem geçmişi (kim/ne/ne zaman) | Tüm yönetim işlemleri günlüklenir |

**Şema değişikliği:** yok — `kullanici.aktif` ve `kullanici.sube_id` önceki fazlarda zaten
mevcuttu (K1). **Şifre saklama:** PBKDF2-HMAC-SHA256 (tuzlu, 600.000 yineleme); eski salted
SHA-256 hash'leri girişte otomatik yükseltilir (bkz. test A).

---

## 2) Rota listesi (9 yeni — toplam 157 → 166)

| # | Rota | Metot | Yetki |
|---|---|---|---|
| 1 | `/ayarlar` | GET | Admin |
| 2 | `/ayarlar/kullanicilar` | GET+POST | Admin |
| 3 | `/ayarlar/kullanici/{uid}/rol` | POST | Admin |
| 4 | `/ayarlar/kullanici/{uid}/durum` | POST | Admin |
| 5 | `/ayarlar/kullanici/{uid}/sifre` | POST | Admin |
| 6 | `/ayarlar/firma` | GET+POST | Admin |
| 7 | `/ayarlar/bildirim` | GET+POST | Admin |
| 8 | `/ayarlar/entegrator` | GET+POST | Admin |
| 9 | `/profil/sifre` | GET+POST | **tüm roller** (kendi hesabı) |

> Eski yollar artık yönlendirir: `/bildirimler/ayarlar` → `/ayarlar/bildirim` ·
> `/edonusum/ayarlar` → `/ayarlar/entegrator`.

---

## 3) Ekran listesi

| # | Ekran | Rota | Açıklama |
|---|---|---|---|
| 1 | Ayarlar hub | `/ayarlar` | Kullanıcı/firma/bildirim/entegratör kartları + tanım linkleri |
| 2 | Kullanıcı Yönetimi | `/ayarlar/kullanicilar` | Liste + ekle formu + rol/durum/şifre aksiyonları |
| 3 | Firma Bilgileri | `/ayarlar/firma` | Ünvan, adres, vergi, iletişim, logo |
| 4 | Bildirim Kanalı | `/ayarlar/bildirim` | SMS/e-posta kanalı + gönderim günlüğü |
| 5 | e-Belge Entegratörü | `/ayarlar/entegrator` | Sağlayıcı, API anahtarı, test modu |
| 6 | Şifre Değiştir | `/profil/sifre` | Mevcut + yeni şifre (üst çubuk 🔑) |

---

## 4) Canlı test kanıtları (istenen 4 senaryo + ek kontroller)

Test ortamı: `python3 app.py` (port 8080), `requests` ile HTTP + SQLite doğrulaması.
Tüm testler **redirect takibi kapalı** (`allow_redirects=False`) ile yapıldı.

### Test A — PBKDF2 geçişi: eski kullanıcı `1234` ile giriş yapabiliyor, hash otomatik yükseliyor
1. `muhasebe` kullanıcısının hash'i eski (legacy salted SHA-256) formata alındı
   (migrasyon öncesi durum simülasyonu): `ff285781...:...`
2. `db.dogrula_sifre("1234", legacy)` → **True** (eski format hâlâ doğrulanıyor)
3. `POST /giris` (muhasebe / 1234) → `GET /` → **200** ✅
4. Giriş sonrası hash formatı → **`pbkdf2_sha256`** (otomatik yükseltildi) ✅
5. Yeni formatla tekrar giriş → **200** ✅

### Test B — Pasifleştirme audit geçmişini korur
1. `pasif_test` (Satis) kullanıcısı eklendi; bir **not** oluşturdu → audit kaydı
   `id=102 · kullanici_adi='pasif_test' · tablo='notlar' · islem='olustur'` ✅
2. Admin kullanıcıyı **pasifleştirdi** → `kullanici.aktif = 0`, satır **tabloda duruyor** ✅
3. Pasifleştirme sonrası audit satırı **aynen korunuyor** (`[102]`) ✅
4. Pasif kullanıcı giriş denemesi → **302** (engellendi) ✅

### Test C — Şifre sıfırlama yetkisi: Admin yapar, diğer roller 403
1. `muhasebe` (Admin değil) `POST /ayarlar/kullanici/9/sifre` → **403** ✅
2. `muhasebe` `GET /ayarlar/kullanicilar` → **403** ✅
3. `admin` sıfırlama → **302** (başarılı) ✅
4. Yeni şifreyle giriş → **200** · eski şifreyle giriş → **302** ✅
5. Audit/DB'de düz metin şifre **yok** (dosya taraması) ✅

### Test D — Yeni kullanıcı + şube ataması → K1 izolasyonu çalışıyor
1. `sube_test` (Depo, `sube_id=1` Batman) eklendi → rol/sube doğru yazıldı ✅
2. `sube_test` `/kasa`'da **Diyarbakır Kasa'yı görmüyor**, kendi şube kasasını görüyor ✅
3. `sube_test` `/stok/depolar`'da **Diyarbakır Depo'yu görmüyor** ✅
4. `admin` her ikisini de görüyor ✅
5. `sube_test` Diyarbakır kasasına hareket POST → **403** ✅

### Ek kontroller
- Ayarlar sayfaları: `admin 200 / depo 403` (5 ekran) ✅
- `/profil/sifre`: admin 200 · depo 200 · girişsiz 302 ✅
- Demo kullanıcıların tamamı `1234` ile giriş yapıyor (5/5 → 200) ✅
- 39 sayfalık regresyon → hepsi 200, 500 yok ✅
- Mizan dengeli **833.375,26 ₺** (değişmedi) · rota **166** · tablo **52** ✅
- Test hijyeni: tüm geçici kullanıcı/not/session/audit satırları temizlendi;
  `audit_log` 6 satıra (onaylı Faz 6 durumuna) döndü ✅

---

## 5) Tasarım kararları

1. **Silme yok, pasifleştirme var** — audit geçmişi kopmaz (Test B ile kanıtlı).
2. **Güvenlik korumaları:** kendini pasifleştirme, kendi rolünü değiştirme ve **son aktif
   yöneticiyi** pasifleştirme engellenir.
3. **Şifre politikası:** yeni/sıfırlanan şifre **en az 8 karakter ve en az bir rakam**; şifre
   değişiminde diğer oturumlar geçersiz kılınır; audit'e düz metin şifre yazılmaz.
4. **Tek merkez:** bildirim kanalı ve entegratör ayarları `/ayarlar` altında toplandı; eski
   yollar yönlendirir (yinelenen sayfa yok).
5. **Firma önbelleği:** `core.firma_yenile()` ile antet/PDF anında güncellenir (test edildi).

## 6) Sonuç

K32 (Sistem Yönetimi) kodlandı, uçtan uca test edildi ve tüm istenen senaryolar **canlı kanıtlarla**
doğrulandı. Yeni tablo yok; 9 yeni rota; mali veriye dokunulmadı (mizan sabit).
