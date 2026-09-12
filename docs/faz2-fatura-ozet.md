# Faz 2 — Fatura Modülü Özeti (onay bekliyor)

> Belge zinciri: **Teklif → Sipariş → İrsaliye → Fatura** · Fatura, zincirin 4. ve **mali etkinin
> oluştuğu** halkasıdır. İrsaliye onayında üretilmeyen cari hareket (borç/alacak) burada işlenir.

---

## 1) Bu modülde uygulanan mimari kurallar

| Kural | Karar | Uygulama |
|---|---|---|
| **K2/K6 — Cari hareket (mali etki)** | Satış faturası → müşteri **BORÇ** (bakiye +); Alış faturası → tedarikçi **ALACAK** (bakiye −). Tek işlemle, manuel ikinci kayıt yok. | Onayda `cari.hareket_ekle(...)` çağrılır (`belge_tipi='Satış Faturası'/'Alış Faturası'`). Dashboard "Bugünkü Satış" KPI'sı bu hareketlerden otomatik beslenir. |
| **K8 — Belge zinciri** | `fatura.kaynak_irsaliye_id → irsaliye.id` (nullable). | Onaylı irsaliyeden tek tıkla üretim; irsaliye detayında fatura linki. |
| **K10 — Durum kuralı** | Yalnız **Onaylandı** irsaliyeden fatura; **Transfer** irsaliyeden hiçbir zaman. | `_irsaliye_kontrol()` UI + sunucu tarafı çift kontrol. |
| **K13 — Numaralandırma** | `SF` (Satış) / `AF` (Alış) → `{ÖNEK}-{YYYY}-{NNN}`. | `db.sonraki_belge_no()`. |
| **K14 — Faturasız irsaliye takibi** | Sevk edilip faturası kesilmeyen irsaliyeler görünür olmalı. | İrsaliye listesinde "⚠️ Faturalanmamış" sekmesi + satırda "Faturala" butonu/rozeti; irsaliye detayında "Faturalandı"/"Faturasız" bandı; dashboard KPI "Faturasız Sevk İrsaliyeleri". |

**Stok etkisi yok:** mal çıkış/girişi İrsaliye'de tamamlandı; fatura `stok_hareket`/`stok_seviye`'ye
dokunmaz. **İptal:** onaylı faturanın cari hareketi silinir (fatura tek kaynaktır — K6), net mali
etki sıfırlanır.

---

## 2) Veri modeli

### `fatura` (belge başlığı)
| Alan | Tip | Not |
|---|---|---|
| `id`, `fatura_no` | PK, UNIQUE | `SF`/`AF`-`YYYY`-`NNN` (K13) |
| `tip` | TEXT | `Satis` / `Alis` |
| `cari_id` | FK → cari_kart | Satis→müşteri, Alis→tedarikçi |
| `sube_id` | FK → sube (nullable) | **K1** — baştan nullable |
| `kaynak_irsaliye_id` | FK → irsaliye (nullable) | **K8** |
| `tarih`, `vade` | TEXT | vade = ödeme vadesi (opsiyonel) |
| `durum` | TEXT | `Taslak / Onaylandı / İptal` |
| `para_birimi`, `doviz_kur` | | Döviz Takip modülü için hazır |
| `ara/iskonto/kdv/genel_toplam` | REAL | Teklif/Sipariş/İrsaliye ile aynı formül |
| `aciklama` | | |

### `fatura_kalem`
`stok_id`, `varyant_id`, `miktar`, `birim_fiyat`, `iskonto_orani`, `kdv_orani`,
`tutar` (satır neti, KDV hariç), `aciklama`.

### Cari etkisi (onayda)
- **Satis:** `cari_hareket` → belge_tipi `Satış Faturası`, **borç = genel_toplam**.
- **Alis:** `cari_hareket` → belge_tipi `Alış Faturası`, **alacak = genel_toplam**.
- `vade` cari hareketin vadesine taşınır; `ilgili_modul='Fatura'`, `ilgili_kayit_id=fatura.id`.
- **İptal:** bu iki alanla eşleşen cari hareket silinir.

---

## 3) Rotalar (6 yeni · toplam 74)

| Rota | Metod | Yetki | Açıklama |
|---|---|---|---|
| `/fatura` | GET | giriş | Liste + tip/durum/arama filtresi, durum özetleri |
| `/fatura/yeni` | GET/POST | Admin·Muhasebe·Satis | Yeni; `?kaynak_irsaliye=ID` ile onaylı irsaliyeden ön doldurma |
| `/fatura/{id}` | GET | giriş | Detay + durum işlemleri + audit + kaynak irsaliye linki |
| `/fatura/{id}/duzenle` | GET/POST | Admin·Muhasebe·Satis | Yalnız **Taslak** faturalar |
| `/fatura/{id}/durum` | POST | **Admin·Muhasebe** | Onayla (cari hareket) / İptal (geri al) |
| `/fatura/{id}/yazdir` | GET | giriş | Antetli yazdır/PDF (Satış/Alış başlıklı) |

Satır ekleme/silme sunucu taraflı; barkod okutunca satır otomatik gelir (K7); iskonto varsayılanı K9
önceliğiyle önerilir.

---

## 4) Ekranlar

1. **Fatura listesi** — tip/durum sekmeleri, arama, no/tarih/vade/toplam rozetleri, Yazdır.
2. **Fatura formu** — tip, cari (türe göre filtrelenir), tarih + vade, kalem tablosu (barkod + K9), canlı toplamlar; irsaliyeden geliyorsa "Kaynak irsaliye" bandı.
3. **Fatura detayı** — kalemler, durum işlemleri (Taslak→Onaylandı/İptal), kaynak irsaliye bağlantısı, audit geçmişi.
4. **Yazdır/PDF** — antetli "SATIŞ FATURASI" / "ALIŞ FATURASI" (vade alanıyla).
5. **İrsaliye tarafı (K14)** — liste "Faturalanmamış" sekmesi + "Faturala" butonu; detayda "Faturalandı"/"Faturasız" bandı.
6. **Dashboard** — yeni KPI'lar "Faturasız Sevk İrsaliyeleri" ve "Taslak Faturalar"; Faz 2 rozeti güncellendi.

---

## 5) Örnek test senaryosu (çalıştırıldı, geçti)

**Hazırlık:** `admin/1234` girişi; temiz seed (2 fatura: `BELGE-NNN`, `BELGE-NNN`).

| # | Adım | Beklenen | Sonuç |
|---|---|---|---|
| 1 | `GET /fatura` | 200; 2 seed fatura (Satış + Alış) | ✅ |
| 2 | `GET /fatura/1/yazdir`, `/2/yazdir` | "SATIŞ FATURASI" / "ALIŞ FATURASI" | ✅ |
| 3 | **K10:** `?kaynak_irsaliye=4`(Taslak) / `=5`(Transfer) | 302 → irsaliye detayı (engel) | ✅ |
| 4 | `?kaynak_irsaliye=3` (onaylı, faturasız) | 200, ön dolu "Kaynak irsaliye · BELGE-NNN" | ✅ |
| 5 | `POST /fatura/yeni` (irsaliye 3) | 302 → `BELGE-NNN` (Taslak), vade taşınır | ✅ |
| 6 | **Onayla (cari hareket)** | `cari_hareket`: borç 21.598,80 (Satış Faturası), vade 2026-10-07; faturasız sayısı 1→0 | ✅ |
| 7 | **İptal (geri al)** | fatura cari hareketi silinir; faturasız sayısı 0→1 | ✅ |
| 8 | Çifte onay engeli | Onaylı fatura tekrar onaylanamaz; cari hareket tek kalır | ✅ |
| 9 | Yetki | `satis`: liste/yeni 200, onay 403 · anon: 302 | ✅ |
| 10 | **K14:** `/irsaliye?faturasiz=1` | yalnız `BELGE-NNN`; detayda "Faturasız" + "Şimdi faturala" | ✅ |
| 11 | **K14:** `/irsaliye/1` (faturalı) | "Faturalandı" + fatura linki | ✅ |
| 12 | Dashboard | "Faturasız Sevk İrsaliyeleri" + "Taslak Faturalar" KPI'ları görünür | ✅ |
| 13 | **K13:** seri numaralama | `BELGE-NNN` sıralı üretilir | ✅ |

> Ayrıca İrsaliye'ye eklenen **aşırı teslimat koruması** (sipariş kalanını aşan / siparişte
> olmayan ürün girişi reddedilir; aynı siparişten açılmış taslak irsaliyelerin bekleyen miktarı
> düşülür) uçtan uca test edildi (bkz. `faz2-irsaliye-ozet.md` test 16).

---

## 6) Sıradaki adım (onayınıza bağlı)

**Çek / Senet** (zincirin 5. halkası): müşteriden alınan / tedarikçiye verilen çek-senet kaydı,
vade + tahsil/öde takibi, cari hareket bağlantısı (tahsil edilince alacak kapanır), portföy/
bordro listeleri.
