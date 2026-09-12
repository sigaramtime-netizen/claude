# D — Bakım Sözleşmesi · Faz Özeti (v1.29.0)

Tarih: 2026-09-11 · Paket: D — Bakım Sözleşmesi · Kapsam: cihaz bazlı periyodik sözleşme +
periyodik fatura + servis iş emri entegrasyonu + otomatik yenileme uyarısı

---

## 1) Veri Modeli Özeti

D paketi 3 yeni tablo getirir; periyodik fatura mevcut modüllerin yardımcılarıyla
(`fatura._toplamlar`, `fatura._cari_uygula`, `muhasebe.fis_uret`) tek noktadan kurulur
(manuel ikinci kayıt yok). Ayrıca `servis_kayit`'a 1 yeni kolon eklenir.

### Yeni tablolar
| Tablo | Amaç | Kritik alanlar |
|---|---|---|
| `bakim_sozlesme` | Sözleşme başlığı | `sozlesme_no` (BKM-YYYY-NNN), `cari_id`, `baslangic`, `bitis`, `periyot` ∈ {Aylik, 3 Aylik, 6 Aylik, Yillik}, `bedel`, `durum` ∈ {Aktif, İptal}, `sirket_id` |
| `bakim_sozlesme_cihaz` | Kapsanan cihazlar | `sozlesme_id`, `stok_id`, `seri_no`, `cihaz_aciklama`, `sirket_id` |
| `bakim_sozlesme_fatura` | Üretilen dönem faturaları | `sozlesme_id`, `fatura_id`, `donem` (UNIQUE `sozlesme_id`+`donem` → mükerrer engeli), `sirket_id` |

### Migration
- `servis_kayit.bakim_sozlesme_id` (nullable; sözleşme kapsamında açılan iş emrini bağlar).

### İş kuralları
1. **Durum türetimi** (`_durum_turet`): saklanan `durum` + süre; bitiş < bugün → `Süresi Doldu`,
   bitiş ≤ bugün+30 → `Yaklaşıyor`, değilse `Aktif`; `İptal` ayrı tutulur.
2. **Periyodik fatura** (`_fatura_uret`): bugünün dönem etiketi (`_donem_etiket`: Ay → `2026-09`,
   3 Aylık → `2026-Q3`, 6 Aylık → `2026-H2`, Yıllık → `2026`) için **Onaylı Satış Faturası**:
   hizmet kalemi `HZM-BKM-SOZL` (seed; KDV oranı + varsayılan iskonto fatura mantığıyla) ×1,
   `fatura._cari_uygula(yon=1)` → cariye BORÇ, `muhasebe.fis_uret("Fatura", fid)` → yevmiye.
   Aynı dönem için ikinci üretim `bakim_sozlesme_fatura(donem)` UNIQUE + ön kontrolle engellenir.
   Stok düşümü yapılmaz (hizmet).
3. **İş emri** (`bakim_is_emri`): sözleşme cihazından `cihaz`/`seri_no` taşınır;
   `garanti_kapsami=1`, `iscilik_ucreti=0` (kapsam dahili ücretsiz), `bakim_sozlesme_id` bağlanır;
   arıza açıklaması zorunludur.
4. **Yenileme** (`bakim_yenile`): yeni sözleşme `baslangic = eski bitis + 1 gün`, aynı cari +
   bedel + periyot; kapsanan cihazlar kopyalanır; eski sözleşmeden bağımsız yeni numara.
5. **K1 izolasyon:** her satır `sirket_id` taşır; tüm sorgular `sirket_id` ile süzülür;
   çapraz şirketten fatura/yenileme/iş emri engellenir.

### Varsayılanlar
- `seed_bakim()` idempotent; `HZM-BKM-SOZL` (Bakım Sözleşmesi Hizmeti, KDV %20) hizmet kartı +
  2 demo sözleşme: `BELGE-NNN` (Aylık, bitiş bugün+15 → **Yaklaşıyor**, cihaz `SN-BKM-1001`
  teşhir TV) · `BELGE-NNN` (Yıllık, bitiş bugün+275 → **Aktif**, cihazlar `SN-BKM-2002`
  çamaşır makinesi + `SN-BKM-2003` buzdolabı).
- Yeni sözleşme numarası `db.sonraki_belge_no` ile `BKM-<yıl>-<sıra>` üretilir.

---

## 2) Ekran Listesi

| Rota | Yöntem | Yetki | Açıklama |
|---|---|---|---|
| `/bakim/sozlesmeler` | GET | herkes | Sözleşme listesi (durum türetimi + cihaz/fatura sayaçları + filtre) |
| `/bakim/sozlesme/yeni` | GET/POST | Admin·Servis·Muhasebe | Yeni sözleşme (cari + dönem + periyot + bedel) |
| `/bakim/sozlesme/<id>` | GET | herkes | Detay: cihaz listesi, dönem faturaları, iş emirleri |
| `/bakim/sozlesme/<id>/duzenle` | GET/POST | Admin·Servis·Muhasebe | Düzenleme |
| `/bakim/sozlesme/<id>/cihaz` | POST | Admin·Servis·Muhasebe | Cihaz ekle |
| `/bakim/sozlesme/cihaz/<id>/sil` | POST | Admin·Servis·Muhasebe | Cihaz çıkar |
| `/bakim/sozlesme/<id>/fatura-uret` | POST | Admin·Muhasebe | Dönem faturası üret (Onaylı SF) |
| `/bakim/sozlesme/<id>/is-emri` | POST | Admin·Servis·Muhasebe | Sözleşme kapsamında servis iş emri aç |
| `/bakim/sozlesme/<id>/yenile` | POST | Admin·Servis·Muhasebe | Tek tıkla yeni döneme yenile |
| `/bakim/sozlesme/<id>/durum` | POST | Admin·Servis·Muhasebe | Aktif ↔ İptal |
| `/bakim/rapor` | GET | herkes | Aktif/yaklaşan/dolan sayıları + toplam dönemlik bedel |

**NAV:** "Servis" menüsü altında "Bakım Sözleşmesi"; dashboard'da KPI kartı
(aktif + yaklaşan + dolan).

---

## 3) Örnek Test Senaryosu (e2e — `test_bakim.py`, 29 kontrol)

1. Sözleşme oluştur (`BKM-YYYY-NNN`, Aktif) + liste render.
2. Doğrulama: bitiş ≤ başlangıç engeli; geçersiz cari engeli.
3. Cihaz ekle (stok + seri no + açıklama) / sil.
4. Periyodik fatura: Onaylı SF (genel = bedel × KDV), cariye BORÇ, yevmiye fişi,
   dönem kaydı; **mükerrer üretim engeli** (flash + sayaç 1).
5. İş emri: `servis_kayit` (Alındı, `garanti_kapsami=1`, seri no taşınır); arızasız engel.
6. Yenileme: yeni sözleşme (başlangıç = bitiş+1 gün, bedel/cari aynı) + cihaz kopyalanır.
7. Durum toggle: Aktif ↔ İptal.
8. Yaklaşan sözleşme rozeti + rapor render.
9. Yetki: Depo → yeni/fatura 403.
10. Şirket izolasyonu: 2. şirket listesi boş; çapraz şirket fatura engeli.
11. Temizlik/bütünlük: FK boş, yetim yevmiye fişi yok, yetim `bakim_sozlesme_fatura` yok,
    yetim `servis_kayit.bakim_sozlesme_id` yok.

---

## 4) Doğrulama Kanıtı

- Test: `test_bakim.py` **29/29** ✅ (tam regresyon: 13 paket / **288** kontrol yeşil, 0 başarısız).
- Ekran görüntüleri (`docs/ekran-goruntuleri/yeni-tema/`): `bakim-sozlesmeler`, `bakim-yeni`,
  `bakim-detay`, `bakim-rapor` (20260911 damgalı).
- Örnek veri (seed'den, tekrarlanabilir): `BELGE-NNN` (Yaklaşıyor, SN-BKM-1001/1002),
  `BELGE-NNN` (Aktif).
- `data/erp.db` **sıfırdan temiz seed** ile üretildi: yetim fiş yok, FK boş, test artığı yok.
