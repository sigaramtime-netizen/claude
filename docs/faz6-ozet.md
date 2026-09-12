# Faz 6 — CİLA: Onay Paketi

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Son faz** · Faz 5 tam onay ✅

## Kapsam (şartname 3.6 + kullanıcı kararları)

Rol bazlı yetkilendirme, bildirim sistemi, dashboard, mobil/tablet uyumu, PDF şablonları.
Kullanıcı kararları: **şube izolasyonu açılsın + test edilsin** ✅ · **SMS/e-posta mock
entegrasyon noktası eklensin** ✅. Yeni modül yok; çapraz altyapı doğrulandı + boşluklar kapatıldı.

## Veri modeli özeti (51 → 52 tablo)

| Tablo | Alanlar | Amaç |
|---|---|---|
| `bildirim_gonderim` | bildirim_id, kanal (sms/eposta), hedef, baslik, mesaj, ilgili_tablo/id, durum | SMS/e-posta gönderim günlüğü (mock: 'Gonderildi') |

> Ayar `meta.anahtar='bildirim.kanal'` (kapali/sms/eposta). Başka tablo açılmadı — K4/K6 korunur.

## Ekran listesi (yeni)

| # | Ekran | Rota | Yetki |
|---|---|---|---|
| 1 | Bildirim merkezi (tip filtresi + sayacı) | `GET /bildirimler` | tüm roller |
| 2 | Bildirim ayarları + gönderim günlüğü | `GET/POST /bildirimler/ayarlar` | Admin |
| 3 | Yetki matrisi (rota × rol) | `GET /yetkiler` | Admin |
| 4 | Dashboard: vadesi yaklaşan çek/senet + geciken cari panelleri | `GET /` | tüm roller |

## K1 — Şube izolasyonu (açıldı)

`core.izole_sube(req)` + `core.sube_koruma(req, kayit_sube)` yardımcıları eklendi; **Admin veya
şubesiz (merkez) kullanıcı tüm şubeleri görür, şubeli kullanıcı yalnız kendi şubesini görür.**
Uygulanan modüller: Kasa, Banka, Teklif, Sipariş, İrsaliye, Fatura, Çek/Senet (+vade takvimi),
Servis, Demirbaş (+amortisman üretimi), Genel Muhasebe (yevmiye listesi, mizan, defter),
Stok (depo listesi; stok kartları zaten depo üzerinden izole). **Cari kartlar bilinçli olarak
ortak bırakıldı** (merkezden yönetilir; hareketler üst belgenin şubesini miras alır). Şubeli
kullanıcının oluşturduğu kayıtlar otomatik kendi şubesine yazılır; başka şubenin kaydına erişim
403 döner.

## Bildirim sistemi (tamamlanan)

- **Yeni tetikleyici:** `_cari_vade_tarama()` — ödenmemiş/vadesi geçen cari bakiyesi otomatik
  uyarısı (şartname satır 23; idempotent, okunmamış bildirim varsa tekrar üretmez).
- **Sağlayıcı soyutlaması:** `bildirim_saglayici.py` (soyut `Saglayici` + `MockSaglayici`);
  e-belge entegratörüyle aynı desen — gerçek SMS/e-posta sağlayıcısına geçiş kod değişikliği
  gerektirmez. Gönderimler `bildirim_gonderim`'e günlüklenir.
- **Servis "cihazınız hazır":** servis `Tamamlandı` olduğunda cari'nin GSM (yoksa e-posta)
  hedefiyle bildirim + sağlayıcı gönderimi tetiklenir.
- **Merkez iyileştirmesi:** tip sekmeleri (uyarı/bilgi/hatırlatma) + okunmamış sayacı + nav rozeti.

## Dashboard / mobil / PDF / rol matrisi

- **Dashboard:** vadesi yaklaşan çek/senet (≤7 gün) ve vadesi geçen cari bakiyeleri panelleri;
  proje durumu (Faz 1–5 ✅, Faz 6 devam) ve dinamik şube başlığı.
- **Mobil:** 600px kırılımı — kompakt üst çubuk (rol rozetleri gizlenir), 2 sütun KPI, tam genişlik
  aksiyon butonları; tablolar yatay kaydırmalı (`.tbl-wrap`), kenar menü off-canvas (mevcut).
- **PDF:** teklif/sipariş/irsaliye/fatura yazdır şablonlarına `firma` tablosundan antet (adres,
  telefon, vergi dairesi/no) eklendi; Türkçe kuruş formatı doğrulandı.
- **Rol matrisi:** Admin'e özel `/yetkiler` ekranı (157 rota × rol) + `docs/yetki-matrisi.md`.

## Seed (Faz 6)

İkinci örnek şube **Diyarbakır Şube (SUB-02)** + kendi depo/kasa'sı eklendi; mevcut belgelerin
`sube_id` değerleri ilk şubeye backfill edildi; **`depo` kullanıcısı Batman Merkez Şube'ye
atanarak şubeli kullanıcı örneği oluşturuldu** (demo şifre yine `1234`).

## Örnek test senaryosu (canlı HTTP + DB doğrulaması)

| # | Adım | Beklenen | Kanıt |
|---|---|---|---|
| 1 | İzolasyon — liste | depo (şube 1) `/kasa`, `/stok/depolar`, `/demirbas`, `/teklif`'te Diyarbakır kayıtlarını **göremez**; admin görür | ✅ |
| 2 | İzolasyon — detay | depo, şube-2 demirbaş/teklif detayında **403**; admin 200 | ✅ |
| 3 | İzolasyon — yazma | depo, şube-2 kasasına hareket POST'unda **403** | ✅ |
| 4 | İzolasyon — mizan | depo mizanı varsayılan kendi şubesine kilitli | ✅ |
| 5 | Cari vade uyarısı | 2 cari için "vadesi geçen bakiye" uyarısı (10.000,00 ₺ / 5.500,00 ₺); tekrar tarama mükerrer üretmez | ✅ |
| 6 | SMS mock | kanal=sms → servis `Tamamlandı` → `bildirim_gonderim` kaydı (sms, hedef GSM, 'Gonderildi') + bildirim | ✅ |
| 7 | Bildirim merkezi | `/bildirimler` tip filtre + `/bildirimler/ayarlar` (Admin) | ✅ |
| 8 | Yetki matrisi | admin `/yetkiler` 200; depo 403 | ✅ |
| 9 | Dashboard | vadesi yaklaşan + geciken cari panelleri | ✅ |
| 10 | PDF antet | fatura yazdır sayfasında firma adres/telefon/vergi bilgisi | ✅ |
| 11 | Regresyon | 33 sayfa 200; mizan dengeli **833.375,26**; 28 yevmiye | ✅ |

## Notlar / kapsam kararları

- **Cari kartlar ortak:** çok şubede de aynı müşteri havuzu kullanılır (yaygın ERP kararı);
  cari bazlı şube ayırımı gerekirse sonraki bir sürümde `cari_kart.sube_id` eklenebilir.
- **Sağlayıcı kapalı varsayılan:** gerçek gönderim başlamadan hiçbir dış çağrı yapılmaz; kanal
  Admin tarafından açılır.
- **K1 migrasyonu gerekmedi:** `sube_id` alanları önceki fazlarda baştan eklendiği için yalnızca
  tek şubeli geçmiş verilerin backfill'i yapıldı (şema değişikliği yok).
