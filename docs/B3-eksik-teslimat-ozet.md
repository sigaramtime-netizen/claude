# B3 — Eksik Teslimatlar + Satın Alma Raporu · Faz Özeti (v1.27.4)

Tarih: 2026-09-11 · Paket: B — Satın Alma Yönetimi · Kapsam: B3 (kapanış)

---

## 1) Veri Modeli Özeti

B3 yeni tablo getirmez — tamamı **türetilmiş** veridir.

### Kullanılan mevcut alanlar
- `siparis_kalem`: `miktar`, `teslim_edilen`, **`kalan_iptal` (yeni kolon)**, `birim_fiyat`
- `siparis`: `tip='Alis'`, `teslim_tarihi`, `doviz_kur`, `cari_id` (tedarikçi), `sube_id`
- `satin_alma_talebi`, `alinan_teklif`, `irsaliye`, `fatura` (rapor özeti için)

### Yeni tek kolon
| Kolon | Tip | Açıklama |
|---|---|---|
| `siparis_kalem.kalan_iptal` | REAL NOT NULL DEFAULT 0 | Kısmi teslimatın bilinçli kapatılması (migrasyon ile eklendi) |

### Türetim kuralları
- **Kalan** = `miktar − teslim_edilen − kalan_iptal` (eksik teslimat tanımı: kalan > 0).
- **Eksik tutar (TRY)** = kalan × birim_fiyat × doviz_kur.
- **Gecikme günü** = bugün − teslim_tarihi (pozitifse).
- **Sipariş durumu** `_siparis_durum_turet`: tüm satırlarda `teslim_edilen + kalan_iptal ≥ miktar` ise `Tamamlandı`, kısmen ise `Kısmi`. Alış irsaliyesinin kalan hesabı da `kalan_iptal`'i düşer (fazla teslimat engellenir).
- **Kapatma yetkisi:** `Admin · Muhasebe · Depo`; kapatma/geri alma audit + bildirim izlenir.

---

## 2) Ekran Listesi

| Rota | Yöntem | Yetki | Açıklama |
|---|---|---|---|
| `/satin-alma/eksik-teslimatlar` | GET | herkes | Eksik liste; tedarikçi + "sadece gecikmiş" filtresi; KPI özet |
| `/satin-alma/eksik-teslimatlar/<kalem_id>/kapat` | POST | KAPAT | `hedef=kapat` (miktar opsiyonel; boşsa tüm kalan) / `hedef=geri_al` |
| `/satin-alma/rapor` | GET | herkes | Dönem + tedarikçi filtreli özet + Alış siparişi dökümü + eksik dökümü |
| Dashboard | — | — | "Eksik Teslimat" KPI kartı (kalem + TRY tutar) |

**NAV:** "Eksik Teslimatlar" + "Satın Alma Raporu" aktif → **"Satın Alma Yönetimi" grubu B1+B2+B3 ile tamamlandı**.

---

## 3) Örnek Test Senaryosu (e2e — `test_eksik_teslimat.py`, 21 kontrol)

1. Alış siparişi (SAP) oluşturulur (Bekliyor) + onaylanır.
2. Kısmi Alış irsaliyesi (2/5) onaylanır → `teslim_edilen=2`, sipariş `Kısmi`.
3. Eksik listede sipariş görünür; kalan 3, eksik tutar 300,00 ₺.
4. Gecikme rozeti (teslim tarihi dün → 1 gün).
5. Kalan kapat → `kalan_iptal=3`, sipariş `Tamamlandı`, eksikten düşer.
6. Geri al → `kalan_iptal=0`, sipariş `Kısmi`, eksikte tekrar.
7. Kısmi kapat (1/3) → kalan 2.
8. Aşırı kapat engeli (99 > kalan).
9. Tedarikçi filtresi.
10. Rapor render (özet + döküm).
11. Şirket izolasyonu.
12. USD teklif detayı `|kur` filtresiyle render (B2 regresyonu).

---

## 4) Doğrulama Kanıtı

- B3 e2e: **21/21** · Regresyon 10 paket: **197/197** → toplam **218/218**.
- `PRAGMA foreign_key_check` = boş · `integrity_check` = ok · yetim `stok_hareket` = 0.
- Ekran görüntüleri (benzersiz zaman damgalı): eksik liste, rapor, dashboard.
