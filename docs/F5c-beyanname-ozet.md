# F5-C — Beyanname Hazırlık Raporları (KDV Devreden + Geçici Vergi + Nakit Esaslı) · Faz Özeti (v1.37.0)

Tarih: 2026-09-12 · Paket: F5-C (D005) · Kapsam: Beyanname modülünün raporlama cilası —
özet kartlar, KDV oran dağılım grafiği, API özet ucu, KDV devreden CSV ve eşleşmemiş
gelen belge vurgusu.

Kural (GM onaylı):
- **YENİ TABLO YOK / MIGRATION YOK** — mevcut `fatura`, `yevmiye`, `gelen_belge`,
  `cari_hareket` üzerinden salt-okunur rapor.
- GİB'e gönderim **YOK** (hazırlık raporu).
- KDV formülleri değişmedi: `_devreden_satirlar`, `_gecici_vergi` (COGS matrahı, %25), `_nakit_kdv`.

---

## 1) Veri Modeli Özeti

Değişiklik yok. Kullanılan mevcut kaynaklar:

| Kaynak | Kullanım |
|---|---|
| `fatura` + `fatura_kalem` | hesaplanan/indirilecek KDV (satış/alış) |
| `yevmiye` / `yevmiye_kalem` | KDV hesap (191/391) bazlı tutarlar |
| `gelen_belge` | eşleşmemiş gelen belge adedi (kırmızı badge) |
| `cari_hareket` | nakit esaslı KDV |

### İş kuralları
1. `odenecek = max(0, hesaplanan − indirilecek − devreden_on)`.
2. `/api/beyanname/ozet?ay=YYYY-MM` → `ay, hesaplanan, indirilecek, odenecek,
   devreden_sonraki, devreden_tablo[12], gecici_vergi{ceyrek,matrah,odenecek},
   nakit{odenecek}, eslesmemis_adet`.
3. CSV başlığı: `Ay; Hesaplanan KDV; Indirilecek KDV; Devreden (Onceki); Odenecek;
   Devreden (Sonraki)` — 12 satır.

---

## 2) Ekran Listesi (etkilenen)

| Rota | Etki |
|---|---|
| `GET /beyanname` | 4 KPI kart + Geçici Vergi rozeti + eşleşmemiş uyarı kartı + oran dağılım grafikleri |
| `GET /api/beyanname/ozet` | JSON özet (K1) |
| `GET /beyanname/kdv/csv?yil=YYYY` | 12 aylık devreden cetveli (Admin/Muhasebe) |
| `GET /beyanname/denetim/csv` | yetki Admin/Muhasebe'ye çekildi |

---

## 3) Örnek Test Senaryosu (e2e — `test_f5c_beyanname.py`, 18 kontrol)

1. Özet kartlar: hesaplanan/indirilecek/ödenecek/devreden tutarları fatura verisiyle eşleşir.
2. `odenecek` devreden düşülmüş (max(0, …)) doğru.
3. KDV oran dağılımı: satış + alış matrah/KDV ikili bar SVG üretilir.
4. `/api/beyanname/ozet` gerekli alanlar + K1 izolasyonu.
5. KDV devreden CSV: 12 satır + `;` ayraçlı + `attachment`.
6. Eşleşmemiş gelen belge adedi doğru (kırmızı badge).
7. Regresyon: F5-B 18/18 + F5-A 18/18 + F4 22/22 bozulmadı.
8. Bütünlük: FK temiz, F5CTEST kalıntısı yok.

**Sonuç:** `test_f5c_beyanname.py` **18/18**; tam regresyon (21 dosya) **478/478, 0 başarısız**.

---

## 4) Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `beyanname.py` | `_kdv_oran_svg` (ikili bar), özet kart verisi, `/api/beyanname/ozet`, `/beyanname/kdv/csv`, denetim yetkisi |
| `templates/beyanname/index.html` | 4 KPI + geçici vergi rozeti + eşleşmemiş uyarı + oran grafikleri + CSV düğmesi |
| `config.py` | `SURUM = "1.37.0"` |
| `test_f5c_beyanname.py` | YENİ — 18 kontrol |

---

## 5) Kanıtlar

- Grafik: inline SVG ikili bar (matrah `#4f8cff` / KDV `#f0a34a`) — harici kütüphane YOK.
- Test: `test_f5c_beyanname.py` (18/18) + regresyon (478/478).
- Sürüm: `config.py SURUM = "1.37.0"`.
