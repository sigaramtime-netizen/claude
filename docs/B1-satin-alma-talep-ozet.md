# B1 — Satın Alma Talebi · Faz Özeti (v1.27.2)

Tarih: 2026-09-10 · Paket: B — Satın Alma Yönetimi · Kapsam: B1

---

## 1) Veri Modeli Özeti

### `satin_alma_talebi` (talep başlığı)
| Kolon | Tip | Açıklama |
|---|---|---|
| `id` | INTEGER PK | |
| `talep_no` | TEXT | `SAT-{YYYY}-{NNN}` · `UNIQUE(sirket_id, talep_no)` (K13, şirket başına sayaç) |
| `sirket_id` | INTEGER FK | Çoklu şirket damgası (K1) |
| `sube_id` | INTEGER FK | Şube izolasyonu (K1) |
| `depo_id` | INTEGER FK | İsteğe bağlı depo |
| `tedarikci_id` | INTEGER FK | `cari_kart` (Tedarikci/HerIkisi) |
| `kaynak` | TEXT | `Yurt İçi` / `Yurt Dışı` (ithalat hafif alanı) |
| `gerekce` | TEXT | Talep gerekçesi |
| `durum` | TEXT | `Taslak → Onay Bekliyor → Onaylandı / Reddedildi → Siparişe Dönüştü` |
| `talep_eden_id` | INTEGER FK | `kullanici` |
| `onaylayan_id` | INTEGER FK | Onaylayan kullanıcı (onay/red'de dolar) |
| `onay_tarihi` | DATE | |
| `red_nedeni` | TEXT | Red nedenli olmak zorunda |
| `donusen_siparis_id` | INTEGER FK | `siparis.id` — tek seferlik SAP bağı (K8/K10) |
| `created_by`, `created_at`, `updated_at` | | Audit/zaman |

### `satin_alma_talebi_kalem` (talep satırları)
| Kolon | Tip | Açıklama |
|---|---|---|
| `id` | INTEGER PK | |
| `talep_id` | INTEGER FK | Başlığa bağlı, `ON DELETE CASCADE` |
| `stok_id` | INTEGER FK | NULL ise **manuel (serbest metin)** satır |
| `varyant_id`, `miktar`, `birim`, `tahmini_fiyat` | | Satır detayı |
| `oncelik` | TEXT | `Normal` / `Acil` |
| `aciklama` | TEXT | Manuel satır adı |
| `sirket_id` | INTEGER | Denormalize şirket damgası (İstek 3 mikro karar B) |

### Kurallar
- **Yetki:** yazma `Admin · Muhasebe · Satış · Depo`; **onay `Admin · Muhasebe`**.
- Talep **mali etki üretmez**; yalnız iç onay + bildirim + audit.
- Çapraz-şirket koruması: stok/depo/tedarikçi referansları aynı `sirket_id` içinde doğrulanır.
- Silme yalnız `Taslak`; düzenleme yalnız `Taslak` (Faz 6.1 pasifleştirme ilkesiyle uyumlu — onaylı belge yok edilemez).
- SAP üretimi yalnız `Onaylandı` ve `donusen_siparis_id IS NULL` talepten, tek seferlik.
- `talep_no` sayacı şirket başına bağımsız (B şirketi kendi `SAT-{YIL}-001`'ini üretir).

---

## 2) Ekran Listesi (7 rota)

| Rota | Yöntem | Yetki | Açıklama |
|---|---|---|---|
| `/satin-alma/talepler` | GET | herkes | Liste + durum/kaynak/arama filtresi + durum rozetleri + özet sayaçları |
| `/satin-alma/talepler/yeni` | GET/POST | TALEP_WRITE | Yeni talep (stok veya manuel satır, tedarikçi, depo, kaynak) |
| `/satin-alma/talepler/<id>` | GET | herkes | Detay: kalemler, durum, onay/red/gönder butonları (role göre) |
| `/satin-alma/talepler/<id>/duzenle` | GET/POST | TALEP_WRITE | Yalnız Taslak düzenleme |
| `/satin-alma/talepler/<id>/sil` | POST | TALEP_WRITE | Yalnız Taslak silme |
| `/satin-alma/talepler/<id>/durum` | POST | TALEP_WRITE | `gonder / geri_cek / onayla / reddet` geçişleri (onay TALEP_ONAY) |
| `/satin-alma/talepler/<id>/siparise-donustur` | GET/POST | TALEP_WRITE | Onaylı talepten SAP üretimi (tedarikçi seçimi) |

**NAV:** Yeni üst grup "Satın Alma Yönetimi" → Satın Alma Talebi (aktif), Alınan Teklif (B2, pasif),
Alış Siparişi/İrsaliye/Fatura (mevcut Alış yönlerine bağlantı), Eksik Teslimatlar (B3, pasif).

---

## 3) Örnek Test Senaryosu (e2e — `test_satin_alma_talep.py`, 23 kontrol)

1. Kalemsiz talep oluşturulamaz.
2. Talep oluşturulur (`Taslak`, `BELGE-NNN`); kalem + tedarikçi damgalanır.
3. Taslak düzenlenir (miktar 5→6).
4. Onaya gönderilir → `Onay Bekliyor`.
5. Onay yetkisi olmayan `Satis` onaylayamaz.
6. `Admin` onaylar → `Onaylandı`, `onaylayan_id` dolar.
7. SAP üretilir (`Bekliyor`, `Alis`, `BELGE-NNN`); kalem kopyalanır.
8. İkinci dönüştürme engellenir (tek SAP).
9. Onaylanmış talep silinemez; Taslak silinebilir.
10. Nedensiz red engellenir; nedenli red işlenir.
11. Şirket izolasyonu + bağımsız sayaç (B şirketi `BELGE-NNN`).

---

## 4) Doğrulama Kanıtı

- B1 e2e: **23/23** · Regresyon 8 paket: **151/151** → toplam **174/174**.
- `PRAGMA foreign_key_check` = boş · `integrity_check` = ok.
- Ekran görüntüleri (benzersiz zaman damgalı): liste, yeni, detay, dönüştür, dashboard.
