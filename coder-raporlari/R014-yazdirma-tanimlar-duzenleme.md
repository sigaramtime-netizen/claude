# R014 — Yazdırma/Çıktı Tamamlama + Tanım Verileri Düzenleme (v1.45.0) — Coder Raporu

**Tarih:** 2026-09-15 · **Direktif:** `gm-direktifleri/D014-yazdirma-tanimlar-duzenleme.md`
(GM1 kesin, 2026-09-15) · **Sürüm:** v1.44.0 → v1.45.0 · **Teslim:** tek paket
(direktif iki seçeneği de coder'a bırakmıştı; tamamı düşük riskli görüntüleme katmanı).

## BÖLÜM A — Yazdırma (10 çıktı)

**A1 — yeni küçük şablonlar (Wolvox `#1e4e79`, A paketi CSS deseni):**
- `cari_odeme.py` → `GET /cari/<id>/makbuz/<belge>` + `templates/cari/makbuz.html`:
  kasa/banka satırları belge_no ile; çek/senet satırları D013 audit detayındaki
  `belge_no` JSON eşleşmesiyle bulunur (şema değişikliği yok); kırılım + toplam +
  dövizde TL karşılığı + işlemi yapan + çift imza. Ekstre THS/ODM satırlarına Makbuz butonu.
- `servis.py` → `GET /servis/<id>/yazdir` + `templates/servis/yazdir.html`
  (detay sorgusu yeniden kullanılır; sube_koruma var; çift imza).
- `bakim.py` → `GET /bakim/sozlesme/<id>/yazdir` + `templates/bakim/yazdir.html`
  (koşullar + cihazlar; detay rotasıyla aynı izolasyon).
- `banka.py` → `GET /banka/hareket/<id>/fis` + `templates/banka/fis.html`
  (`kasa/fis.html` birebir + firma/döviz satırı); banka listesine Fiş butonu.

**A2 — `core.yazdir_belge()` yeniden kullanımı (yeni şablon YOK, yalnızca `tip_label`):**
- `satin_alma.py` → `/talepler/<id>/yazdir` ("Satın Alma Talebi"; tarih=created_at,
  toplamlar tahmini_fiyat×miktar); `alinan_teklif.py` → `/teklifler/<id>/yazdir`
  ("Alınan Teklif"; cari=tedarikçi). İkisinde de sube_koruma var.
- `stok.py` → `/stok/transferler/<id>/yazdir` ("Depo Transfer Sevk Fişi", no=`DT-000000`
  sentetik): `yazdir/belge.html`'e `fiyat_gizli` bayrağı eklendi (fiyat sütunları +
  toplamlar gizlenir; tanımsızken eski davranış korunur → mevcut 3 çağrı etkilenmez).
- `demirbas.py` → `/demirbas/amortisman/yazdir?yil=` (CSV ile aynı sorgu, roller aynı).
- `teklif.py` → ortak mekanizmaya taşındı (`yazdir_belge(t, kalemler, "teklif_no", "Teklif")`
  + şube koruması); `templates/teklif/yazdir.html` silindi (tek referans bu rotaydı).
- CRM Raporu ekranına Yazdır butonu.

**A3:** eksik_liste + satin-alma rapor şablonlarına `window.print()` butonu
(genel `@media print` CSS zaten mevcuttu); POS satış detayına Fatura Yazdır kısayolu.

**Butonlar (kabul #7):** servis/bakım/talep/teklif/transfer detay + banka liste (Fiş) +
ekstre (Makbuz) + demirbaş index + crm/eksik/rapor + POS kısayol. Mali/iş mantığı değişmedi.

## BÖLÜM B — Tanımlar (`ayarlar.py`, Admin)

- `ayarlar_tanimlar/<tip>/<id>/duzenle` (GET+POST, 5 tip) + `tanim_duzenle.html` formu
  + 5 karta Düzenle butonu + Marka kartı + `/marka/<id>/durum` rotası.
- Koruma (`_tanim_kullanim`): `ad` her zaman; para-birimi `kod` 13 tabloda taranır
  (stok/fatura/teklif/sipariş/irsaliye/kasa/banka/hesap/çek/cari/kur/alınan/bakım),
  cari-grup `tip` grup_id ile, `birim.ad` 7 tabloda (metin-anahtar olduğu için
  tanımlayıcı sayıldı — direktif yorumum, testle sabitlendi) taranır; kullanımdaysa
  reddedilir. Kod benzersizlik + kategori üst-kendi/üye kontrolleri dahil.
- Marka pasifliği stok formunda otomatik işler (`stok._markalar` zaten aktif=1 süzüyor).

## Testler

- `kod/test_d014_yazdirma_tanimlar.py` — **16/16 ✅** (A1: 1-4, A2: 5-9, A3: 10,
  B: 11-14, K1: 15, FK/kalıntı: 16).
- Tam regresyon — **29 dosya, 633 kontrol (617+16), 0 başarısız ✅**.
- Sürüm sabitleri (d010/f6 + docstring'ler) 1.45.0'a çekildi; d012 docstring'indeki
  D013 sed hatası (direktif dosya adı v1.44.0 yazılmıştı) v1.43.0'a düzeltildi.

## Debug Notları

1. `servis_kayit/satin_alma_talebi/alinan_teklif.durum` CHECK kısıtları test kurulumunda
   yakalandı (Alındı / Onay Bekliyor / Alındı kullanıldı).
2. Makbuzda kırılım etiketi boş çıktı: dict anahtarı `Sekil` (büyük) yazılmış, şablon
   `sekil` okuyordu → düzeltildi (D013 mantığına dokunulmadı, yalnızca D014 kodu).
3. Jinja `"` kaçışı (`&#34;`) ürün adı karşılaştırmasında hesaba katıldı (test tarafı).
4. `disabled` inputlar POST'a düşmediği için kilitli alanlarda `readonly` kullanıldı
   (sunucu tarafı kilit kontrolü zaten var; çift katman).
