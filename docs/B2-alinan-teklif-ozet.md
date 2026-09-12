# B2 — Alınan Teklif + Teklif Değerlendirme · Faz Özeti (v1.27.3)

Tarih: 2026-09-10 · Paket: B — Satın Alma Yönetimi · Kapsam: B2

---

## 1) Veri Modeli Özeti

### `alinan_teklif` (başlık)
| Kolon | Tip | Açıklama |
|---|---|---|
| `id` | INTEGER PK | |
| `teklif_no` | TEXT | `ALT-{YYYY}-{NNN}` · `UNIQUE(sirket_id, teklif_no)` (K13, şirket başına sayaç) |
| `talep_id` | INTEGER FK | `satin_alma_talebi` — opsiyonel (bağlı/bağımsız teklif) |
| `tedarikci_id` | INTEGER FK | `cari_kart` (Tedarikci/HerIkisi) — zorunlu |
| `sube_id` | INTEGER FK | Şube izolasyonu (K1) |
| `depo_id` | INTEGER FK | Opsiyonel |
| `tarih`, `gecerlilik_tarihi` | DATE | |
| `teslim_suresi_gun`, `odeme_vadesi_gun` | INTEGER | Değerlendirme kriterleri |
| `para_birimi` | TEXT | `TRY·USD·EUR·GBP` (B2 orta kapsam) |
| `doviz_kur` | REAL | 1 döviz = ? TL; TRY için 1, boşsa `db.guncel_kur` |
| `durum` | TEXT | `Taslak → Alındı → Kazanan / Elendi → Siparişe Dönüştü` |
| `ara/iskonto/kdv/genel_toplam` | REAL | Para birimi cinsinden (TRY karşılığı = genel × kur) |
| `aciklama` | TEXT | |
| `donusen_siparis_id` | INTEGER FK | `siparis.id` — tek seferlik SAP bağı (K8/K10) |
| `created_by`, `created_at`, `updated_at` | | Audit/zaman |
| `sirket_id` | INTEGER | Çoklu şirket damgası |

### `alinan_teklif_kalem` (satırlar)
| Kolon | Tip | Açıklama |
|---|---|---|
| `id` | INTEGER PK | |
| `teklif_id` | INTEGER FK | Başlığa bağlı, `ON DELETE CASCADE` |
| `stok_id` | INTEGER FK | NULL ise **manuel (serbest metin)** satır |
| `varyant_id`, `miktar`, `birim` | | Satır detayı |
| `birim_fiyat` | REAL | Para birimi cinsinden |
| `iskonto_orani`, `kdv_orani` | REAL | K9 konvansiyonu |
| `tutar` | REAL | Satır net tutarı (KDV hariç) |
| `aciklama` | TEXT | Manuel satır adı |
| `sirket_id` | INTEGER | Denormalize şirket damgası |

### Kurallar
- **Yetki:** giriş/düzenleme `Admin · Muhasebe · Satış · Depo`; **kazanan seçme + SAP üretimi `Admin · Muhasebe`**.
- **Tek kazanan:** bir talepte aynı anda tek `Kazanan` olabilir; yeni kazanan eskiyi `Alındı`'ya geri alır.
- **Tek dönüşüm:** bir talep yalnız bir kez SAP'ye dönüşür; tekliften dönüştürülünce talep de `Siparişe Dönüştü` olur ve `donusen_siparis_id` dolar.
- Döviz: kur SAP'ye sabitlenerek taşınır; otomatik kur farkı fişi üretilmez.
- Çapraz-şirket koruması: stok/depo/tedarikçi referansları aynı `sirket_id` içinde doğrulanır.
- Silme/düzenleme yalnız `Taslak`.

---

## 2) Ekran Listesi (8 rota)

| Rota | Yöntem | Yetki | Açıklama |
|---|---|---|---|
| `/satin-alma/teklifler` | GET | herkes | Liste + durum filtreleri + TRY karşılığı sütunu |
| `/satin-alma/teklifler/yeni` (`?talep_id=`) | GET/POST | WRITE | Yeni teklif; talepten ön-doldurma; döviz + kur |
| `/satin-alma/teklifler/<id>` | GET | herkes | Detay (kalemler, toplamlar, TRY karşılığı) |
| `/satin-alma/teklifler/<id>/duzenle` | GET/POST | WRITE | Yalnız Taslak |
| `/satin-alma/teklifler/<id>/sil` | POST | WRITE | Yalnız Taslak |
| `/satin-alma/teklifler/<id>/durum` | POST | WRITE | `alindi / geri_taslak / kazanan / ele` (karar: KARAR) |
| `/satin-alma/teklifler/<id>/siparise-donustur` | GET/POST | KARAR | Kazanan tekliften SAP (kur sabitlenir) |
| `/satin-alma/teklifler/karsilastir` (`?talep_id=`) | GET | herkes | Değerlendirme: TRY'ye göre sıralı karşılaştırma + talep seçici |

**NAV:** "Alınan Teklif" + "Teklif Değerlendirme" aktif; "Eksik Teslimatlar" (B3) pasif.

---

## 3) Örnek Test Senaryosu (e2e — `test_alinan_teklif.py`, 23 kontrol)

1. Kalemsiz teklif oluşturulamaz.
2. Tedarikçisiz teklif oluşturulamaz.
3. Teklif oluşturulur (Taslak, `BELGE-NNN`); toplam 2×10000 %20 KDV → 24000.
4. Taslak düzenlenir (miktar 2→3 → 36000).
5. Alındı geçişi.
6. `Satis` kazanan seçemez (yetki).
7. Tek kazanan kuralı (eski kazanan geri alınır).
8. Kazanan tekliften SAP üretilir (kalem + para birimi + kur taşınır).
9. Bağlı talep de `Siparişe Dönüştü` olur.
10. İkinci dönüşüm engellenir (tek SAP).
11. Ele işaretleme.
12. Silme kuralları (Taslak silinir; Alındı silinemez).
13. Döviz: USD teklif genel 120 (100 + %20); SAP'ye kur 30 sabitlenir.
14. Şirket izolasyonu + bağımsız sayaç (B şirketi `BELGE-NNN`).

---

## 4) Doğrulama Kanıtı

- B2 e2e: **23/23** · Regresyon 9 paket: **174/174** → toplam **197/197**.
- `PRAGMA foreign_key_check` = boş · `integrity_check` = ok.
- Ekran görüntüleri (benzersiz zaman damgalı): liste, yeni form, detay, karşılaştırma, dashboard.
