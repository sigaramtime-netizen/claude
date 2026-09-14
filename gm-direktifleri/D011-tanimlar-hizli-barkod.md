# D011 — Tanım Verileri (Kategori & Para Birimi) + Hızlı Barkod Girişi

> **Durum:** ONAYLANDI (GM1, 2026-09-14) — kodlamaya hazır.
> Kapsam bölme kararı (Seçenek 3): **D011 = A + C**. D012 = B+D, D013 = E ayrı paket.
> **Sürüm hedefi:** v1.41.0 → **v1.42.0**
> **ÖNCELİK:** Yüksek

---

## GEREKÇE
Kullanıcının canlı kullanım şikâyeti: stok formunda kategori ve para birimi
eklenemiyor ("ekleyemiyorum"); irsaliye/fatura/teklifte hızlı barkod girişi yok.
D007'de marka için çözülen "＋ ekle" deseni bu alanlarda eksik.

## KAPSAM — D011-A: Kategori & Para Birimi Tanımları

Marka deseni (`kod/stok.py` `/api/marka/ekle`, satır ~468) **birebir** kopyalanır:

1. **`/api/kategori/ekle`** (POST, inline, `STOK_WRITE` yetkisi):
   - `ad` trim; boşsa 400 JSON.
   - Büyük/küçük harf duyarsız eşleşme (`lower(ad)`); varsa mevcut `id` dön (**idempotent**).
   - Yoksa `INSERT kategori(ad, aktif=1, sirket_id)` → `audit("kategori", id, "olustur", ...)` → id dön.
   - JSON yanıt; sayfa yenilenmez.
2. **`/api/para-birimi/ekle`** (POST, inline) — aynı desen, yeni **`para_birimi` tablosu**
   (kod, ad, aktif, sirket_id). İdempotent (aynı kod/ad → mevcut id).
3. **Stok formu** (`kod/templates/stok/form.html`):
   - Kategori select'ine **`＋ Kategori`** butonu; para birimi select'ine **`＋ Döviz`** butonu.
   - Davranış (D007 `＋ Marka` birebir): prompt → `fetch POST` → select'e ekle + seç, **sayfa yenilenmez**.
4. **Ayarlar → "Tanımlar" alt-ekranı** (Marka gibi): kategori + para birimi listesi +
   **pasifleştir** (silme YOK — K32 deseni; kullanılan kayıt silinemez, yalnız pasifleştirilir).
   - Pasifleştirilen kayıt yeni belgelerde seçilemez; mevcut kayıtlar bozulmaz.
5. **K1 izolasyonu:** `sirket_id` (kategori tablosunda sirket_id mevcut; marka deseniyle aynı).

## KAPSAM — D011-C: Hızlı Barkod Girişi

- POS'taki `barkod_bul()` + "Enter'da ekle" desenini **irsaliye / fatura / teklif**
  formlarına ekle: ayrı, küçük bir barkod input'u (tek-satır-ekle; sepet mantığına benzer).
- Mevcut typeahead'e **DOKUNMA** — bu ona ek bir hızlı-yol.
- Okutma/yazma + Enter → barkod bulunur → satır otomatik eklenir (bulunamazsa uyarı).

## KAPSAM DIŞI (GM1 kararı)
- **Birim** (adet/kg/metre) ve **cari grup** seçicileri bu pakette YOK.
- Satır bazlı KDV (B) → D012; çoklu döviz gösterimi (D) → D012; tahsilat/ödeme (E) → D013.

## KABUL KRİTERLERİ
- [ ] Kategori inline eklenir + seçilir (sayfa yenilenmez); idempotent (aynı ad → mevcut id).
- [ ] Para birimi inline eklenir + seçilir; idempotent.
- [ ] Ayarlar/Tanımlar: liste + pasifleştir; kullanılan kayıt pasifleştirilir, silinmez.
- [ ] K1: kategori/para birimi şirket izolasyonlu.
- [ ] Barkod input: yaz/okut + Enter → satır eklenir.
- [ ] Yeni tablo: yalnızca `para_birimi` (+ gerekirse migration). İş mantığı (K1–K32, belge
      zincirleri, mali etki) DEĞİŞMEZ.
- [ ] Yeni `test_d011_tanimlar_barkod.py`; tam regresyon (25 dosya) yeşil.
- [ ] Teslim: ZIP (sansürlü, PNG'siz, demo seed'li DB) + MD5/SHA256.

## İSTENEN KANITLAR
- `test_d011_tanimlar_barkod.py` çıktısı (ekle+idempotent, pasifleştir, K1, barkod Enter-ekle).
- Tam regresyon çıktısı (25 dosya).
- Değişen dosya listesi (diff).
- ZIP + MD5/SHA256.

## TEKNİK NOTLAR
- **Para birimi modeli:** `para_birimi` ayrı tablo (kod, ad, aktif, sirket_id) kurulur;
  mevcut `PARA_BIRIMLERI` konfig listesi DB'den beslenir hale getirilir (tohum: TRY/USD/EUR/GBP
  korunur; `doviz_kur.para_birimi` ile uyumlu). Eski TEXT kolon davranışı geriye dönük korunur.
- **Kategori:** tablo hazır (id, ust_id, ad, aktif, created_at, sirket_id); ilk sürüm düz
  (üst kategori yok) — `ust_id` NULL.
- **Audit:** ekleme + pasifleştirme `audit()` ile kayıtlanır.
- **CSRF:** tüm POST'lar mevcut hibrit korumadan geçer (D009).
