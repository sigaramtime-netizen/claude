# D012 — TASLAK DİREKTİF (SUPERSEDED)

> ⚠️ Bu taslak, GM2'nin kesin direktifiyle yer değiştirdi:
> `gm-direktifleri/D012-satir-kdv-coklu-doviz-parabirimi-birim-db-v1.43.0.md`
> (2026-09-14, GM2 acil yedek devrede). Bu dosya yalnızca tarihsel kayıt olarak durur.
> Kaynak kapsam: `gm-direktifleri/D011-tanimlar-kdv-barkod-doviz-tahsilat.md` (B ve D
> bölümleri) + KRAL revizyonu (Para Birimi & Birim tablo geçişi).
> **Sürüm hedefi (öneri):** v1.42.0 → **v1.43.0**

---

## BAŞLIK: D012 — Satır Bazlı KDV + Çoklu Döviz + Para Birimi & Birim Tablo Geçişi

## ÖNCELİK: Yüksek

## KAPSAM

### D012-B — Satır Bazlı KDV Dahil/Hariç
- Her kalem satırına opsiyonel `kdv_dahil` override; **boşsa** belge geneli varsayılan uygulanır.
- Kapsam: **irsaliye, fatura, teklif, sipariş** kalem satırları.
- Gerekçe: karışık KDV muamelesi tek belgede mümkün olmalı.

### D012-D — Çoklu Döviz (eşzamanlı gösterim)
- Belge para birimi (TRY/USD/EUR[/GBP]) seçimi mevcut; belge kaydedilirken **kur sabitlenir**
  (mevcut K2 deseni).
- Ekranda hem döviz hem TL karşılığı **yan yana** gösterilir (yalnız arka planda değil).
- Cari ekstre: para birimi filtresi (Tümü/TRY/USD/EUR[/GBP]) + her döviz cinsinden ayrı alt toplam.

### D012-X — Para Birimi & Birim Tablo Geçişi (KRAL revizyonu)
- `PARA_BIRIMLERI` (sabit liste) ve `BIRIMLER` (sabit liste) → **DB tablo**
  (kod/ad, aktif, sirket_id).
- D011 inline deseni birebir: stok formunda **`＋ Döviz`** ve **`＋ Birim`** butonları
  → prompt → `fetch POST /api/para-birimi/ekle` + `/api/birim/ekle` → select'e ekle + seç
  (sayfa yenilenmez), **idempotent** (aynı ad/kod → mevcut id).
- Ayarlar→Tanımlar: para birimi + birim listesi + pasifleştir (K32: silme yok).
- Tohum: mevcut değerler korunur (TRY/USD/EUR[/GBP]; Adet/kg/metre vb.).
- `doviz_kur.para_birimi` ile uyum; TCMB kur çekme entegrasyonu bozulmaz.

## KABUL KRİTERLERİ
- Aynı belgede bir satır KDV dahil, diğeri hariç girilebilir; toplamlar doğru.
- USD faturada hem USD hem TL tutar görünür; cari ekstre döviz filtresi doğru alt toplam verir.
- Para birimi + birim inline eklenebilir, idempotent, pasifleştirilebilir, kullanımdaysa silinemez.
- K1 şirket izolasyonu (para_birimi + birim).
- TCMB kur çekme ve mevcut K2 konvansiyonu bozulmaz.
- Yeni test `test_d012_*`; tam regresyon (26 dosya) yeşil.
- İş mantığı (K1–K32, belge zincirleri, mali etki) korunur.
- Teslim: ZIP (sansürlü, PNG'siz, demo seed'li DB) + MD5/SHA256 + diff + test çıktısı.

## İSTENEN KANITLAR
- `test_d012_*` çıktısı (satır KDV karışık, çift döviz gösterim, ekstre filtresi, inline
  para birimi/birim + idempotent + pasifleştir, K1).
- Tam regresyon çıktısı (26 dosya).
- Değişen dosya listesi (diff) + ZIP + MD5/SHA256.

## GM2'YE AÇIK KARARLAR (cevaplanmalı)
1. **GBP dahil mi?** (sistemde var; GM1 ilk metninde yalnız TRY/USD/EUR dedi) — tutarlılık için
   dahil önerilir.
2. **Birim tohum değerleri:** mevcut `BIRIMLER` listesi DB'ye aynen tohum olarak alınsın mı?
3. **Sürüm:** v1.43.0 onayı.
