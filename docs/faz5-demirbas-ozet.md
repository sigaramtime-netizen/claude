# Demirbaş (1.22) — Onay Paketi

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Faz 5 · modül 6/6 (son)**

## Tasarım kararı (kullanıcı kararları + K kuralları)

Demirbaş daha önce hiçbir yerde tutulmadığından **4 yeni tablo** açılır — K4/K6'nın "ikinci
doğruluk kaynağı açma" kuralı ihlal edilmez (mevcut veri çoğaltılmaz). Kullanıcı kararları:

1. **Ömür/oran tanımı:** kategori varsayılanı + **kart bazlı düzeltme** (`omur_yil` NULL = kategori).
2. **Yöntem:** **normal amortisman** (eşit paylı, VUK). Aylık pay = (maliyet − hurda) ÷ (ömür × 12).
3. **Tetik:** **elle "Amortisman Üret"** (POST, seçilen aya kadar) + **aylık otomatik** (Admin/Muhasebe
   `/demirbas`'ı açtığında eksik aylar üretilir — kapanış akışı; cron yok).

| Kural | Uygulama |
|---|---|
| **K26** (otomatik yevmiye) | her aylık amortisman GM fişi üretir: **770 borç / 257 alacak**; `kaynak_modul='Demirbas'`, `kaynak_id=demirbas.id`, `kaynak_sahne=donem` (idempotent — aynı dönem iki kez yazılmaz) |
| **K1** (şube) | `demirbas.sube_id` + `demirbas_zimmet.sube_id` baştan eklendi |
| Zimmet | kartta güncel (`zimmetli_kullanici_id` + `sube_id`) + `demirbas_zimmet` geçmişi (Teslim/Devir/İade) |
| Tutarlılık kilidi | amortisman üretilmiş kartta maliyet/ömür/alış tarihi/kategori değiştirilemez (GM fişleriyle çelişmemesi için) |

## Veri modeli özeti (4 yeni tablo — 47 → 51)

| Tablo | Alanlar (özet) | Amaç |
|---|---|---|
| `demirbas_kategori` | ad, omur_yil, aciklama | varsayılan ömür/oran (Bilgisayar 4y, Mobilya 10y, Makine 10y, Taşıt 5y, Diğer 5y) |
| `demirbas` | kod, ad, kategori_id, alis_tarihi, maliyet, hurda_degeri, omur_yil (NULL=kategori), **sube_id**, **zimmetli_kullanici_id**, durum, aciklama | sabit kıymet kartı |
| `demirbas_amortisman` | demirbas_id, donem (YYYY-MM), tutar, birikmis, net_deger — `UNIQUE(demirbas_id, donem)` | dönem bazlı amortisman tablosu |
| `demirbas_zimmet` | demirbas_id, kullanici_id, sube_id, islem, tarih, aciklama | zimmet geçmişi |

## Ekran listesi

| # | Ekran | Rota | Yetki |
|---|---|---|---|
| 1 | Demirbaş listesi + KPI (maliyet/birikmiş/net/zimmetli) + yeni kart + kategori + Amortisman Üret | `GET /demirbas` | görüntüleme: tüm roller · yazma: Admin/Muhasebe |
| 2 | Demirbaş detayı: amortisman tablosu + zimmet geçmişi + düzenleme + durum/silme | `GET /demirbas/{id}` | tüm roller |
| 3 | Kart ekle / güncelle / zimmet / durum / sil / amortisman üret / kategori ekle | POST (7 rota) | Admin/Muhasebe |

## Örnek test senaryosu (canlı HTTP + DB doğrulaması)

| # | Adım | Beklenen | Kanıt |
|---|---|---|---|
| 1 | `GET /demirbas` (admin) | 200; KPI maliyet 89.000,00 / birikmiş 2.241,66 / net 86.758,34; 3 kart | ✅ |
| 2 | Aylık otomatik amortisman | Admin açtığında eksik aylar üretildi (4 satır + 4 GM fişi) | ✅ |
| 3 | Sayısal doğruluk | DBR-001 Ağu+Eyl 937,50×2 (birikmiş 1.875,00 / net 43.125,00) · DBR-002 Eyl 233,33 · DBR-003 Eyl 133,33 | ✅ DB eşleşti |
| 4 | GM entegrasyonu | 4 fiş 770 borç / 257 alacak; `kaynak_modul='Demirbas'`; mizan dengeli | ✅ |
| 5 | İdempotentlik | "Amortisman Üret" tekrar → yeni satır yok | ✅ |
| 6 | Detay + zimmet | `GET /demirbas/1`: amortisman tablosu + zimmet geçmişi (Teslim rozeti, kişi + şube) | ✅ |
| 7 | Kart ekle → otomatik ilk ay | yeni kart 12.000, 4y → Eylül 250,00 otomatik üretildi | ✅ |
| 8 | Güncelleme kilidi | amortismanlı kartta maliyet 99.999 denemesi reddedildi (12.000 kaldı) | ✅ |
| 9 | Zimmet Teslim/İade | Teslim → kişi atanır; İade → boşa alınır; geçmiş 2 satır | ✅ |
| 10 | Durum + Sil | Satıldı → amortisman durur; Sil → kart + amortisman + fişler geri alınır | ✅ |
| 11 | Yetki | depo: görüntüleme serbest, yazma formu gizli, POST 403; muhasebe: tam | ✅ |
| 12 | Regresyon | 30 sayfa 200; mizan dengeli 833.375,26; 28 yevmiye (24 + 4 Demirbaş) | ✅ |

## Notlar / kapsam kararları

- **Maliyet KDV hariç** bedeldir (KDV indirilebilir olduğundan amortismana tabi değere girmez).
- **Kıst (ay kesri) amortisman uygulanmaz:** ilk amortisman alış ayından tam ay başlar; ilk yıl kıst
  hesabı gerekiyorsa mali müşavirce düzeltilir (ekranda belirtilir).
- **Çıkış (Satıldı/Hurda):** amortismanı durdurur; net defter değerinin mahsubu (257 ↔ 689) manuel
  GM fişiyle yapılır (düşük sıklık, tek seferlik işlem — bu sürümde otomatikleştirilmedi).
- **GM net kârına etki:** amortisman gerçek bir gider olduğundan Finansal Analiz'in "GM net kâr
  (geçici)" satırı 136.878,00 → **134.636,34** (−2.241,66 amortisman) olur; "Tahmini Brüt Kâr
  (COGS dahil)" satırı fatura bazlı olduğundan **etkilenmez** (−39.622,00). Beyanname Geçici Vergi
  matrahı COGS bazlı olduğu için değişmez.
- **Oranlar VUK listesine göre seed'lendi** (Bilgisayar %25/4y, Mobilya %10/10y, Makine %10/10y,
  Taşıt %20/5y, Diğer %20/5y); kategori/ömür serbestçe düzenlenebilir (oran = 100 ÷ ömür).
