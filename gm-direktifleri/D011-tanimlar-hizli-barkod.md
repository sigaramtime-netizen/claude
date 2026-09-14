# D011 — Tanım Verileri (Kategori & Cari Grup) + Hızlı Barkod Girişi

> **Durum:** ONAYLANDI (GM1, 2026-09-14) — **KRAL revizyonu:** Para Birimi D011'den çıkarıldı
> (sabit liste → tablo geçişi pahalı; D012'ye taşındı). Cari Grup D011-A'ya eklendi
> (tablo hazır + `/cari/gruplar` ekranı var → yalnızca inline "＋ Grup" butonu eksik).
> **Kapsam:** D011 = **A (Kategori + Cari Grup)** + **C (hızlı barkod)**.
> **Sürüm hedefi:** v1.41.0 → **v1.42.0**
> **ÖNCELİK:** Yüksek

---

## GEREKÇE
Kullanıcının canlı kullanım şikâyeti: stok formunda kategori eklenemiyor; cari formunda
grup eklenemiyor; irsaliye/fatura/teklifte hızlı barkod girişi yok. D007'de marka için
çözülen "＋ ekle" deseni bu alanlarda eksik.

## KAPSAM — D011-A: Kategori & Cari Grup Tanımları

Marka deseni (`kod/stok.py` `/api/marka/ekle`, satır ~468) **birebir** kopyalanır:

1. **`/api/kategori/ekle`** (POST, inline, `STOK_WRITE` yetkisi):
   - `ad` trim; boşsa 400 JSON.
   - Büyük/küçük harf duyarsız eşleşme (`lower(ad)`); varsa mevcut `id` dön (**idempotent**).
   - Yoksa `INSERT kategori(ad, aktif=1, sirket_id)` → `audit("kategori", id, "olustur", ...)` → id dön.
   - JSON yanıt; sayfa yenilenmez.
2. **`/api/cari_grup/ekle`** (POST, inline) — aynı desen; `cari_grup` tablosu hazır
   (id, ad, tip, aciklama, aktif, sirket_id). `ad` trim + idempotent; `tip` varsayılan
   **`'Bölge'`**; `INSERT cari_grup(ad, tip, aktif=1, sirket_id)` → audit → id dön.
3. **Formlara buton:**
   - `kod/templates/stok/form.html`: kategori select'ine **`＋ Kategori`** butonu.
   - `kod/templates/cari/form.html`: grup_id select'ine **`＋ Grup`** butonu.
   - Davranış (D007 `＋ Marka` birebir): prompt → `fetch POST` → select'e ekle + seç, **sayfa yenilenmez**.
4. **Ayarlar → "Tanımlar" alt-ekranı** (Marka gibi): kategori + cari grup listesi +
   **pasifleştir** (silme YOK — K32 deseni; kullanılan kayıt silinemez, yalnız pasifleştirilir).
   - Pasifleştirilen kayıt yeni belgelerde seçilemez; mevcut kayıtlar bozulmaz.
5. **K1 izolasyonu:** `sirket_id` (kategori ve cari_grup tablolarında sirket_id mevcut;
   marka deseniyle aynı).

## KAPSAM — D011-C: Hızlı Barkod Girişi

- POS'taki `barkod_bul()` + "Enter'da ekle" desenini **irsaliye / fatura / teklif**
  formlarına ekle: ayrı, küçük bir barkod input'u (tek-satır-ekle; sepet mantığına benzer).
- Mevcut typeahead'e **DOKUNMA** — bu ona ek bir hızlı-yol.
- Okutma/yazma + Enter → barkod bulunur → satır otomatik eklenir (bulunamazsa uyarı).

## KAPSAM DIŞI (GM1 + KRAL kararı)
- **Para Birimi** ve **Birim** (sabit liste → DB tablo + inline ekleme) → **D012**'ye
  taşındı (çoklu dövizle aynı mekanik dönüşüm).
- Satır bazlı KDV (B) → D012; çoklu döviz gösterimi (D) → D012; tahsilat/ödeme (E) → D013.

## KABUL KRİTERLERİ
- [ ] Kategori inline eklenir + seçilir (sayfa yenilenmez); idempotent (aynı ad → mevcut id).
- [ ] Cari grup inline eklenir + seçilir; idempotent; tip='Bölge'.
- [ ] Ayarlar/Tanımlar: liste + pasifleştir; kullanılan kayıt pasifleştirilir, silinmez.
- [ ] K1: kategori/cari grup şirket izolasyonlu.
- [ ] Barkod input: yaz/okut + Enter → satır eklenir.
- [ ] Yeni tablo YOK (kategori + cari_grup mevcut). İş mantığı (K1–K32, belge zincirleri,
      mali etki) DEĞİŞMEZ.
- [ ] Yeni `test_d011_tanimlar_barkod.py`; tam regresyon (25 dosya) yeşil.
- [ ] Teslim: ZIP (sansürlü, PNG'siz, demo seed'li DB) + MD5/SHA256.

## İSTENEN KANITLAR
- `test_d011_tanimlar_barkod.py` çıktısı (kategori+cari_grup ekle+idempotent, pasifleştir,
  K1 izolasyonu, barkod Enter-ekle).
- Tam regresyon çıktısı (25 dosya).
- Değişen dosya listesi (diff).
- ZIP + MD5/SHA256.

## TEKNİK NOTLAR
- **Kategori:** tablo hazır (id, ust_id, ad, aktif, created_at, sirket_id); ilk sürüm düz
  (üst kategori yok) — `ust_id` NULL.
- **Cari grup:** tablo hazır + `/cari/gruplar` yönetim ekranı mevcut (dokunma); yalnızca
  inline `/api/cari_grup/ekle` ucu + cari formu "＋ Grup" butonu eklenir. `tip` varsayılan
  'Bölge' (yönetim ekranından Segment vb. tipler yine eklenebilir).
- **Audit:** ekleme + pasifleştirme `audit()` ile kayıtlanır.
- **CSRF:** tüm POST'lar mevcut hibrit korumadan geçer (D009).
