# Faz 2 — Sipariş Modülü Özeti (onay bekliyor)

> Belge zinciri: **Teklif → Sipariş → İrsaliye → Fatura** · Sipariş, zincirin 2. halkasıdır.
> Bir önceki turda netleştirilen 3 mimari karar (K8/K9/K10) bu modülle birlikte
> `docs/mimari-kurallar.md`'ye işlendi ve uygulandı.

---

## 1) Netleştirilen mimari kararlar (bu turda karara bağlandı)

| Kural | Karar | Uygulama |
|---|---|---|
| **K8 — Belge zinciri** | Belge başlıkları **doğrudan FK** ile bağlanır; `ilgili_modul`/`ilgili_kayit_id` yalnız hareket tablolarında kalır. | `siparis.kaynak_teklif_id → teklif.id` (nullable) eklendi. İrsaliye'de `kaynak_siparis_id`, Fatura'da `kaynak_irsaliye_id` aynı desenle gelecek. |
| **K9 — İskonto önceliği** | Varsayılan öneri: `fiyat_kural` (ileride) → **stok özel iskonto** → **cari iskonto** → `0`. | Teklif'in eski "yalnız cari iskontosu" davranışı güncellendi; Sipariş satır girişi aynı sırayı kullanıyor. |
| **K10 — Durum kuralı** | Dönüşüm yalnız **Onaylandı** kaynaktan. | Teklif → Sipariş hem UI'da (buton yalnız Onaylandı'da) hem sunucu tarafında engellenir (Gönderildi/Taslak/Reddedildi/Süresi Doldu → red). |
| **K11 — Depo bazlı rezervasyon/düşüm** | Rezervasyon ve stok düşümü **her zaman siparişte seçilen `depo_id`** bazında (asla depoların toplamı değil). `teslim_edilen` satır bazında; başlık `durum`'u tüm satırların teslim oranından türetilir (tümü tam → Tamamlandı, herhangi biri >0 → Kısmi, hiçbiri → Onaylandı). | Bu turda netleştirildi ve test edildi (bkz. test 16). İrsaliye aynı kuralı kullanacak. |
| **K12 — Tekliften çoklu sipariş** | Bir tekliften birden fazla sipariş üretilebilir (kısmi dönüşüm **bilinçli olarak serbest**). | Yanlışlıkla çift dönüşümü görünür kılmak için teklif detayına "oluşturulan siparişler (N)" listesi ve sipariş formuna "daha önce N sipariş" bilgilendirme bandı eklendi (engelleme yok). |

---

## 2) Veri modeli

### `siparis` (belge başlığı)
| Alan | Tip | Not |
|---|---|---|
| `id`, `siparis_no` | PK, UNIQUE | `SIP-2026-00X` (Müşteri) / `SAP-2026-00X` (Alış) |
| `tip` | TEXT | `Musteri` (müşteriye satış) / `Alis` (tedarikçiye satın alma) |
| `cari_id` | FK → cari_kart | Musteri→müşteri, Alis→tedarikçi (liste tipe göre filtrelenir) |
| `sube_id` | FK → sube (nullable) | **K1** — baştan nullable, Faz 6'da izolasyon açılacak |
| `depo_id` | FK → depo (nullable) | Müşteri siparişinde zorunlu (rezervasyon deposu); Alış'ta opsiyonel |
| `kaynak_teklif_id` | FK → teklif (nullable) | **K8** — onaylanan tekliften tek tıkla üretim |
| `tarih`, `teslim_tarihi` | TEXT | |
| `durum` | TEXT | `Bekliyor / Onaylandı / Kısmi / Tamamlandı / İptal` |
| `para_birimi`, `doviz_kur` | | Döviz Takip modülü için hazır |
| `ara/iskonto/kdv/genel_toplam` | REAL | Teklif ile aynı formül |

### `siparis_kalem`
`stok_id`, `varyant_id`, `miktar`, **`teslim_edilen`** (İrsaliye besleyecek), `birim_fiyat`,
`iskonto_orani`, `kdv_orani`, `tutar` (satır neti, KDV hariç), `aciklama`.

> Toplam formülü (Teklif ile aynı, doğrulandı): satır net = miktar × birim_fiyat × (1 − isk/100);
> KDV = Σ(net × kdv/100); genel = ara + KDV.

### Rezervasyon
Müşteri siparişi **Onaylandı** olunca `stok_seviye.rezerve` artar; İptal'de `MAX(rezerve−miktar,0)`
ile serbest bırakılır. Onay öncesi **eldeki = miktar − rezerve** kontrolü yapılır; yetersizse onay
reddedilir (hiçbir rezervasyon yazılmaz). Rezervasyon Stok modülünün `/stok/{id}` detayında
"Rezerve" sütununda görünür.

**Kontrol ve rezervasyon, siparişte seçilen `depo_id` bazındadır (K11)** — asla tüm depoların
toplamı değil. Doğrulama: TV-43 ürünü ANA'da 12, MAG'de 2 adetken (toplam 14), MAG seçili
siparişte 3 adet istenince onay "eldeki: 2, istenen: 3" ile reddedilir; aynı ürün ANA seçili
siparişte onaylanır. İrsaliye mal düşümünü aynı depodan yapacağı için "rezerve var ama o depoda
yok" çelişkisi doğmaz.

---

## 3) Rotalar (6 yeni · toplam 62)

| Rota | Metod | Yetki | Açıklama |
|---|---|---|---|
| `/siparis` | GET | giriş | Liste + tip/durum/arama filtresi, durum özetleri |
| `/siparis/yeni` | GET/POST | Admin·Muhasebe·Satis | Yeni; `?kaynak_teklif=ID` ile onaylı tekliften ön doldurma |
| `/siparis/{id}` | GET | giriş | Detay + durum işlemleri + audit |
| `/siparis/{id}/duzenle` | GET/POST | Admin·Muhasebe·Satis | Yalnız **Bekliyor** siparişler |
| `/siparis/{id}/durum` | POST | **Admin·Muhasebe** | Onayla / İptal (yetki bazlı onay akışı) |
| `/siparis/{id}/yazdir` | GET | giriş | Antetli yazdır/PDF (Müşteri/Alış başlıklı) |

Satır ekleme/silme sunucu taraflı (Teklif ile aynı desen); tip değişince cari listesi otomatik
yenilenir (Müşteri→müşteriler, Alış→tedarikçiler; satır birim fiyatı da `satış_fiyat`/`alış_fiyat`
olarak önerilir).

---

## 4) Ekranlar

1. **Sipariş listesi** — tip/durum sekmeleri, arama, no/tarih/toplam rozetleri, Yazdır.
2. **Sipariş formu** — tip, cari, depo, tarih/teslim, kalem tablosu (iskonto önceliği K9), canlı toplamlar; tekliften geliyorsa "Kaynak teklif" bandı.
3. **Sipariş detayı** — kalemler + (müşteri siparişinde) Eldeki/Rezerve sütunu, durum işlemleri, kaynak teklif bağlantısı, audit geçmişi.
4. **Yazdır/PDF** — antetli "MÜŞTERİ SİPARİŞİ" / "SATIN ALMA SİPARİŞİ".
5. **Dashboard** — yeni KPI "Onay Bekleyen Siparişler"; Faz 2 rozeti "Teklif + Sipariş hazır".
6. **Teklif detayı** — Onaylandı teklifte "🛒 Siparişe Çevir" butonu (K10).

---

## 5) Örnek test senaryosu (çalıştırıldı, geçti)

**Hazırlık:** `admin/1234` girişi.

| # | Adım | Beklenen | Sonuç |
|---|---|---|---|
| 1 | `GET /siparis` | 200, 3 seed sipariş | ✅ |
| 2 | `GET /siparis/1` (onaylı müşteri) | "Eldeki / Rezerve" + rezervasyon metni | ✅ |
| 3 | `GET /siparis/1/yazdir`, `/3/yazdir` | "MÜŞTERİ SİPARİŞİ" / "SATIN ALMA SİPARİŞİ" | ✅ |
| 4 | `GET /siparis/yeni?kaynak_teklif=3` (Onaylandı) | 200, kalem ön dolu | ✅ |
| 5 | `?kaynak_teklif=1`(Gönderildi) / `=2`(Taslak) / `=99`(yok) | 302 → teklif detayı | ✅ |
| 6 | `POST /siparis/yeni` (teklif 3) | 302 → `BELGE-NNN`, `kaynak_teklif_id=3`, toplam 39.898,86 | ✅ |
| 7 | `POST` ile Gönderildi tekliften oluşturma | 200 + hata "Yalnızca 'Onaylandı'…" (sunucu engeli) | ✅ |
| 8 | Onayla (`durum=Onaylandı`) yeterli stok | 302, `rezerve 0→1` | ✅ |
| 9 | Aynı siparişi tekrar onayla | Red, rezerve değişmez (çifte rezervasyon yok) | ✅ |
| 10 | Onayla — stok yetersiz (100 adet, eldeki 5) | Red, "Stok yetersiz… (eldeki: 5, istenen: 100)", rezerve değişmez | ✅ |
| 11 | İptal (`durum=İptal`) onaylı sipariş | 302, `rezerve 1→0`; İptal sonrası onay reddi | ✅ |
| 12 | İskonto önceliği (K9) | TV-55(stok %5)+cari %8 → %5; TV-43(stok %0)+cari %8 → %8 | ✅ |
| 13 | Teklif'te aynı K9 | %5 / %8 (eski davranış güncellendi) | ✅ |
| 14 | Alış tipi | cari listesi yalnız tedarikçiler; satır fiyatı = alış_fiyat (28.000) | ✅ |
| 15 | Yetki | `satis`: liste/yeni 200, onay 403 · `depo`: yeni 403 · anon: 302 | ✅ |
| 16 | **Depo bazlı rezervasyon (K11)** | TV-43 (ANA 12 / MAG 2): MAG seçili 3 adet → red "eldeki: 2, istenen: 3"; ANA seçili 3 adet → onay, `rezerve` ANA'da 1→4, MAG değişmez | ✅ |
| 17 | **Aynı tekliften çoklu sipariş (K12)** | Teklif 3'ten 2 sipariş üretilebilir; teklif detayı "oluşturulan siparişler (2)" + linkler; sipariş formunda "daha önce 2 sipariş" bandı | ✅ |

---

## 6) Sıradaki adım (onayınıza bağlı)

**İrsaliye** (zincirin 3. halkası): sevk irsaliyesi (satış/alış), onaylı siparişten tek tıkla
üretim, `kaynak_siparis_id` (K8), mal çıkışı/girişi → `stok_hareket` + `stok_seviye` düşümü,
`teslim_edilen` artırımı ve `Kısmi`/`Tamamlandı` durumunun otomatik türetilmesi, rezervasyon
serbest bırakma.
