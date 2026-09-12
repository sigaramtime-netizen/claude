# Faz 5 — Kartoteks (1.17) — özet + test kanıtları (revize)

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Faz 5 / Modül 2/6** · **Durum:** tamamlandı ✅

> Faz 5 (Mali/Analitik) 2. modülü. Sıra (bkz. `docs/faz5-plan.md`): Genel Muhasebe ✅ → **Kartoteks ✅** →
> Transfer → Finansal Analiz → Beyanname → Demirbaş.

Kullanıcının şartlı onayındaki 2 madde bu revizyonda kapatıldı:
1. ✅ **Dışa aktarma (Excel/CSV) + yazdırılabilir PDF raporu** eklendi (`/kartoteks/cari|stok/export` + `/rapor`).
2. ✅ **Barkod hızlı sorgulama**: `stok.barkod_bul()` ile okutulan barkod doğrudan ilgili ürünün
   kartoteksine atlar (`/kartoteks/stok?barkod=…` → 302 → `?stok_id=`); ad/kod/barkod araması da ekli.

Bonus düzeltme: `core.Response` aynı isimde çift `Content-Type` başlığı üretebiliyordu
(varsayılan `text/html` + verilen başlık yan yana) — bu hem Kartoteks hem **mevcut Stok2 export'unda**
gizli bir kusurdu; aynı isimli başlık artık değiştirilir (tek başlık).

---

## 1) Veri Modeli Özeti

**Yeni tablo YOK** (K4 — tek kaynak). Kartoteks, mevcut iki hareket tablosunun salt-okunur,
kronolojik, koşu bakiyeli dökümüdür:

| Kaynak | Tablo | Koşu bakiyesi |
|---|---|---|
| Cari Kartoteks | `cari_hareket` (K2/K6) | `Σborc − Σalacak` (TL; K18) |
| Stok Kartoteks | `stok_hareket` (K4) | `Σmiktar` depo bazlı / genel |

- `ilgili_modul` + `ilgili_kayit_id` (K3) izinden **kaynağa link** üretilir: Fatura, Çek/Senet,
  İrsaliye, Servis, Transfer (kayit_id doluysa; büyük/küçük harfe duyarsız).
- Ayrı veri girişi **yok**; yazma rotası yok (POST → 404). Tüm roller salt-okunur.

---

## 2) Ekran Listesi

| # | Ekran | Rota | Yetki |
|---|---|---|---|
| 1 | Kartoteks ana sayfa (KPI + yönlendirme) | `GET /kartoteks` | tüm roller |
| 2 | Cari kartoteks (seçim + döküm) | `GET /kartoteks/cari?cari_id=` | tüm roller |
| 3 | Stok kartoteks (seçim + döküm + barkod) | `GET /kartoteks/stok?stok_id=&barkod=` | tüm roller |
| 4 | Cari dışa aktarma (Excel/CSV) | `GET /kartoteks/cari/export?cari_id=&format=` | tüm roller |
| 5 | Stok dışa aktarma (Excel/CSV) | `GET /kartoteks/stok/export?stok_id=&format=` | tüm roller |
| 6 | Cari yazdırılabilir rapor (PDF) | `GET /kartoteks/cari/rapor?cari_id=` | tüm roller |
| 7 | Stok yazdırılabilir rapor (PDF) | `GET /kartoteks/stok/rapor?stok_id=` | tüm roller |

Filtreler: tarih aralığı (`bas`/`bit`), belge tipi (cari) / işlem tipi + depo (stok), ad/kod/barkod arama.
Filtreler dışa aktarmaya ve rapora da taşınır. Önceki dönemden devir satırı koşu bakiyesini doğru başlatır.

---

## 3) Örnek Test Senaryosu (canlı HTTP)

| # | Adım | Beklenen | Kanıt |
|---|---|---|---|
| 1 | `GET /kartoteks` | 200; KPI'lar (cari/stok kart + hareket + toplam stok) | ✅ |
| 2 | `GET /kartoteks/cari` | cari dropdown (8 kart); seçim yoksa yönlendirme | ✅ |
| 3 | `GET /kartoteks/cari?cari_id=1` | başlık + hareketler + koşu bakiye + Net Bakiye | ✅ |
| 4 | Koşu bakiye doğruluğu (cari 1) | DB `Σborc−Σalacak` = 274,80 = ekran | ✅ |
| 5 | `GET /kartoteks/stok?stok_id=1` | mevcut stok + depo dağılımı + koşu miktar | ✅ |
| 6 | Stok koşu miktar = `stok_seviye` (depo 1) | 10,0 = 10,0 | ✅ |
| 7 | Depo filtresi | `depo_id=1` → "Kalan (genel)" etiketi gizlenir | ✅ |
| 8 | Kaynak linkleri | cari→`/fatura/`, `/cek_senet/`; stok→`/irsaliye/` | ✅ |
| 9 | Tarih filtresi devir satırı | `bas=` verildiğinde "Önceki dönemden devir" | ✅ |
| 10 | Salt-okunur | POST `/kartoteks/cari` → 404 (yazma yok) | ✅ |
| 11 | Rol matrisi | 5 rol okuma 200 | ✅ |
| 12 | **Barkod sorgulama** | `barkod=8691234500011` → 302 → `stok_id=1`; bilinmeyen barkod uyarısı | ✅ |
| 13 | **Excel dışa aktarma** | cari/stok → 200, geçerli `.xlsx` (PK imzası), tek `Content-Type` | ✅ |
| 14 | **CSV dışa aktarma** | UTF-8 BOM, `;` ayraçlı, koşu bakiye kolonu | ✅ |
| 15 | Filtreli export | `belge_tipi=Tahsilat` → yalnız tahsilat satırları | ✅ |
| 16 | **PDF/yazdır raporu** | cari + stok rapor sayfaları, "Yazdır / PDF'e Kaydet" | ✅ |
| 17 | Eksik parametre | export idsiz → 302 yönlendirme | ✅ |
| 18 | Regresyon | 13 ana sayfa 200; GM mizan dengeli | ✅ |

---

## 4) Notlar

- Seed'deki eski `stok_hareket` kayıtlarının bir kısmı `ilgili_modul='Alis'/'Satis'` ve
  `ilgili_kayit_id=NULL` taşır (Faz 1/2 tarihsel girişleri) → kaynak etiketi görünür, link üretilmez.
  Canlı akışta (İrsaliye/Servis/Transfer) kayit_id doludur ve link çalışır.
- PDF: uygulama genelindeki desenle tutarlı olarak **yazdır → PDF'e kaydet** (tarayıcı) ile üretilir
  (harici PDF kütüphanesi yoktur); Excel ise gerçek `.xlsx` (openpyxl) dosyasıdır.

