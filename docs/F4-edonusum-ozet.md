# F4 — e-Dönüşüm (Mock/Sandbox) Özeti — v1.34.0

**Tarih:** 2026-09-11
**Kapsam:** Giden e-Fatura/e-Arşiv/e-İrsaliye + gelen kutuları + entegratör ayarları (K1)
**Test:** `test_f4_edonusum.py` → 22/22 ✅ · Tam regresyon → 424/424 ✅

---

## 1. Ne yapıldı

Faz 4'te zaten kısmi olarak bulunan e-Dönüşüm altyapısı (giden `e_belge`, gelen `gelen_belge`,
`edonusum.py`, `entegrator.py`) GM emrindeki eksiklerle tamamlandı ve **Mock/Sandbox** olarak kapatıldı.
Gerçek GİB/İzibiz bağlantısı **YOK**; mimari gerçek entegratöre hazır şekilde soyutlandı.

### 1.1 Giden e-Belge (otomatik tip + durum makinesi)

- Satış faturası **onaylanınca** otomatik `e_belge` **Taslak** üretilir (`fatura.py`).
  - Alıcı `cari_kart.e_fatura_mukellefi = 1` → **e-Fatura (EF)**
  - `0` → **e-Arşiv (EA)** — kullanıcı tipi **elle seçemez**.
- Satış/Alış irsaliyesi onaylanınca otomatik **e-İrsaliye (EI)** Taslak üretilir (`irsaliye.py`).
  - **Transfer** irsaliyesinden e-İrsaliye **üretilmez** (cari/KDV yoktur).
- Durum makinesi: `Taslak → Gönderildi → Onaylandı / Reddedildi / İptal` (CHECK ile sabit).
- **Reddedilen** belge tekrar gönderilebilir; `Gönderildi/Onaylandı` iptal edilemez.
- Aynı fatura/irsaliye için **çifte e-belge** üretimi engelli (durum != 'İptal' kontrolü).

### 1.2 Gönderim + Mock Entegratör

- Tek entegratör katmanı: `entegrator.py` (`MockEntegrator`). Gerçek sağlayıcı sınıfları
  (EDM/İzibiz/QNB) aynı arayüze bağlanacak şekilde tasarlandı; API anahtarı olmadan Mock'a düşer.
- **Test modu (1):** mock GİB deterministik → her gönderim anında `Gönderildi → Onaylandı`.
- **Test modu (0):** gönderim `Gönderildi`'de kalır; `durum-sorgula` hash bazlı gerçekçi yanıt verir
  (~%10 Reddedildi); `mock-yanit` ile elle Onaylandı/Reddedildi uygulanabilir.
- Ham e-belge **UBL-TR benzeri XML** olarak `ek_dosya`'da saklanır (K16; yeni tablo yok).

### 1.3 Gelen Kutusu

- `GET /e-fatura/gelen` ve `GET /e-irsaliye/gelen` — tedarikçiden gelen belgeler.
- `POST /e-fatura/gelen/cek` mock entegratörden çeker (dedup `belge_no` üzerinden).
- Durum: `Okunmadi → Kabul / Red / Itiraz`.
- **Tek tıkla dönüştür:** e-Fatura → **Alış Faturası** Taslak; e-İrsaliye → **Alış İrsaliyesi** Taslak.
  - Onay kullanıcıda; otomatik onay **YOK**.
  - Kalemler stok kartıyla **kod → ad** eşleşir; eşleşmeyen kalem **manuel satır**
    (`stok_id NULL` + `aciklama`).
  - Tedarikçi VKN ile cari karttan bulunur (bulunamazsa uyarı; otomatik cari açılmaz).
  - **Çifte dönüşüm engelli** (`donusum_fatura_id`/`donusum_irsaliye_id` + kontrol).

### 1.4 Ayarlar

- `GET/POST /ayarlar/edonusum` — entegratör seçimi (Mock/EDM/İzibiz/QNB), API anahtarı (password),
  test modu checkbox.
- `entegrator_ayar` tablosu: **K1 — `sirket_id` PRIMARY KEY** (şirket başına tek satır).
- Eski meta tabanlı `/ayarlar/entegrator` ve `/edonusum` + `/gelen` rotaları **geriye dönük** korunur.

### 1.5 GM Rotaları

```
GET  /e-fatura                     giden e-Fatura/e-Arşiv listesi
POST /e-fatura/:id/gonder          mock gönder (test modu 1 → anında Onaylandı)
POST /e-fatura/:id/iptal           İptal (Taslak/Reddedildi)
GET  /e-irsaliye                   giden e-İrsaliye listesi
POST /e-irsaliye/:id/gonder
GET  /e-fatura/gelen               gelen kutusu (e-Fatura)
POST /e-fatura/gelen/:id/kabul     durum Kabul
POST /e-fatura/gelen/:id/red       durum Red
POST /e-fatura/gelen/:id/donustur  Alış Faturası Taslağı
GET  /e-irsaliye/gelen
POST /e-irsaliye/gelen/:id/donustur Alış İrsaliyesi Taslağı
GET  /ayarlar/edonusum             entegratör seçimi (K1)
POST /ayarlar/edonusum/kaydet
```

### 1.6 Altın Kural: Mali Etki ÜRETMEZ

e-Dönüşüm **yalnızca belgeleştirme** katmanıdır. Cari hareket + yevmiye F1'de (fatura/irsaliye
onayında) oluşur; e-belge üretimi/gönderimi **hiçbir mali kayıt** eklemez (test 18 ile doğrulanır).

---

## 2. Yapılmayanlar (GM "Yapmama" listesi)

- Gerçek GİB/İzibiz API bağlantısı **yok** (mock/sandbox).
- F1/F2/F3 mantığı değişmedi (mali etki, KDV-net kuralı, typeahead).
- Ayrı entegratör kodu **yok** — tek `entegrator.py`.
- Gelen kutusunda otomatik fatura **onayı yok** — sadece Taslak.
- Çifte dönüşüm engelli (UNIQUE `belge_no` + `donusum_*` kontrolü).

---

## 3. Değişen dosyalar

| Dosya | Değişiklik |
|---|---|
| `db.py` | `entegrator_ayar` tablosu (K1: sirket_id PK); yetim e-belge temizliği + `trg_fatura_sil_ebelge` / `trg_irsaliye_sil_ebelge` trigger'ları (üst belge silinince türev otomatik silinir) |
| `entegrator.py` | `MockEntegrator(test_modu=...)`; deterministik durum sorgusu |
| `edonusum.py` | `_aktif_sirket`, K1'li `_entegrator`, `_gonder`, Alış irsaliye desteği, manuel kalem, GM rotaları |
| `fatura.py` | Satış onayında otomatik e-belge taslağı (try/except ile onayı bloke etmez) |
| `irsaliye.py` | Satış/Alış onayında otomatik e-İrsaliye taslağı |
| `config.py` | `SURUM = "1.34.0"`, `SURUM_TARIHI = "2026-09-11"` |
| `templates/e_fatura/liste.html` | giden e-Fatura/e-Arşiv listesi (YENİ) |
| `templates/e_fatura/gelen.html` | gelen e-Fatura kutusu (YENİ) |
| `templates/e_irsaliye/liste.html` | giden e-İrsaliye listesi (YENİ) |
| `templates/e_irsaliye/gelen.html` | gelen e-İrsaliye kutusu (YENİ) |
| `templates/ayarlar/edonusum.html` | entegratör ayar formu (YENİ) |
| `templates/base.html` | yan menü: e-Fatura/e-Arşiv, e-İrsaliye, e-Dönüşüm Gelen |
| `templates/ayarlar/index.html` | Ayarlar kartı → `/ayarlar/edonusum` |
| `test_f4_edonusum.py` | 22 kontrol (YENİ) |

---

## 4. Test sonuçları

- `python3 test_f4_edonusum.py` → **22/22** ✅
- Tam regresyon (18 paket) → **424/424** ✅ (F3 30/30, F2 34/34, F1 25/25, POS 41/41 dahil)
- `PRAGMA foreign_key_check` → boş ✅
- F4TEST kalıntısı → yok ✅
