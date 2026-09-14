# D012 — Satır Bazlı KDV + Çoklu Döviz + Para Birimi & Birim DB Tablo Geçişi

> **Durum:** ONAYLANDI — **GM2 (acil yedek, devrede)** kesin direktifi, 2026-09-14.
> GM1 kotası doldu; GM2 KRAL kuralı gereği acil yedek olarak görevde.
> Kapsam GM1+KRAL kararından değiştirilmedi, yalnızca netleştirildi.
> **Sürüm hedefi:** v1.42.0 → **v1.43.0**

---

## SONUÇ — 3 açık karar (GM2)

| # | Soru | GM2 Kararı |
|---|------|-----------|
| 1 | GBP dahil mi? | **EVET — dahil.** `PARA_BIRIMLERI = [TRY,USD,EUR,GBP]` aynen DB `para_birimi` tablosuna 4 kayıt tohum. Sistemde zaten var, tutarlılık için çıkarılmaz. |
| 2 | BIRIMLER DB'ye aynen mi? | **EVET — 1:1 aynen 11 değer:** `["Adet","Kutu","Paket","Çift","Takım","Metre","m²","Kg","Lt","Top","Rulo"]` — sıra/`m²` korunur, idempotent seed. |
| 3 | v1.43.0 onayı? | **ONAYLANDI.** `config.SURUM = "1.43.0"` |

---

## KAPSAM — B + D + X (GM1+KRAL kararı değiştirilmedi, yalnızca netleştirildi)

### (B) Satır Bazlı KDV Dahil/Hariç
- 4 kalem tablosuna `kdv_dahil` kolonu; formda satır `<select>`; net'e `kdv_ayikla` ile çevrim.
- Kapsam: irsaliye, fatura, teklif, sipariş kalem satırları.

### (D) Çoklu Döviz Eşzamanlı Gösterim
- Örn. `100 USD ≈ 3.420 ₺` yan yana gösterim.
- Cari ekstre/kartoteks **Para Birimi filtresi** (Tümü/TRY/USD/EUR/GBP) + döviz bazlı alt toplamlar.

### (X) Para Birimi & Birim: config → DB
- `para_birimi` / `birim` config sabit listesinden **DB tabloya** taşınır (uygulama içi sözlük/cache
  ile beslenir) + inline **`＋ Döviz`** / **`＋ Birim`** (D011 deseni: idempotent, K1 sirket_id, audit).
- Ayarlar→Tanımlar: para birimi + birim listesi + pasifleştir (K32: silme yok).

---

## KABUL KRİTERLERİ (GM2)

- **B1-2:** aynı belgede karışık KDV (bir satır dahil, diğeri hariç) girilebilir; toplamlar doğru.
- **D1-2:** döviz belgede hem döviz hem TL karşılığı görünür; cari ekstre döviz filtresi doğru alt toplam verir.
- **X1-4:** para birimi + birim inline eklenebilir, idempotent, pasifleştirilebilir, kullanımdaysa silinemez; K1 izolasyonlu.
- **K1:** şirket izolasyonu korunur. **FK0:** `PRAGMA foreign_key_check = 0`.
- **Sürüm:** 1.43.0.
- Toplam `test_d012_kdv_doviz_master.py` **en az 12 kontrol**.

## KANIT + TESLİM

- Diff + `test_d012_kdv_doviz_master.py` çıktısı.
- Tam regresyon + `PRAGMA foreign_key_check = 0`.
- ZIP (sansürlü, demo seed'li DB, `__pycache__` hariç) + MD5/SHA256 — ANAYASA v12.

---

## KÖPRÜ NOTLARI (düzeltme/netleştirme — GM2 kararını DEĞİŞTİRMEZ)

1. **Regresyon sayısı düzeltmesi:** GM2 metni "24+1 dosya 557/557" diyor; bu sayı eski
   (D009/D010 dönemi) ve güncel değil. **Güncel baseline: 26 test dosyası / 582 kontrol**
   (D011 v1.42.0 sonrası). D012'de `test_d012_kdv_doviz_master.py` eklenince **27 dosya**
   olur; kabul ölçüsü: 27 dosya, 0 başarısız (582 + yeni D012 kontrolü).
2. **(X) netleştirme:** KRAL kararı "DB tablo"dur; GM2'nin "para_birimi / birim global
   sözlük" ifadesi, DB tabloların uygulama içinde sözlük/cache olarak yüklenmesi olarak
   anlaşılmalıdır — coder DB tablo (kod/ad, aktif, sirket_id) kuracak, mevcut sabit
   listeleri tohum olarak alacaktır.
3. **Doğrulandı (köprü):** `BIRIMLER` 11 değeri birebir doğru (`stok.py:20`);
   `kdv_ayikla()` `core.py:633`'te mevcut; `PARA_BIRIMLERI=[TRY,USD,EUR,GBP]`
   (`config.py:23`); `TCMB_KODLARI=(USD,EUR,GBP)`.
