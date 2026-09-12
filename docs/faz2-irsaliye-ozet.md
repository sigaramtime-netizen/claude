# Faz 2 — İrsaliye Modülü Özeti (onay bekliyor)

> Belge zinciri: **Teklif → Sipariş → İrsaliye → Fatura** · İrsaliye, zincirin 3. halkasıdır.
> Bu modülle birlikte `docs/mimari-kurallar.md`'ye **K13** (belge numaralandırma) işlendi.

---

## 1) Bu modülde uygulanan mimari kurallar

| Kural | Karar | Uygulama |
|---|---|---|
| **K8 — Belge zinciri** | Belge başlıkları doğrudan FK ile bağlanır. | `irsaliye.kaynak_siparis_id → siparis.id` (nullable). Fatura'da `kaynak_irsaliye_id` aynı desenle gelecek. |
| **K10 — Durum kuralı** | Dönüşüm yalnız **Onaylandı** kaynaktan. | Onaylı siparişten tek tıkla irsaliye; `Tamamlandı`/`Bekliyor`/`İptal` siparişten üretim engellenir (sipariş detayına yönlendirilir). |
| **K11 — Depo bazlı düşüm + teslim türetme** | Stok çıkış/girişi **yalnız belgedeki `depo_id`** bazında; siparişin `teslim_edilen`'i satır bazında artar, başlık durumu tüm satırların teslim oranından türetilir (tümü tam → Tamamlandı, herhangi biri >0 → Kısmi, hiçbiri → Onaylandı). | Onayda tek işlemde: stok hareketi + `stok_seviye` güncelleme + rezervasyon serbest bırakma + `teslim_edilen` artırımı + sipariş durumu türetimi. İptal ters yönlü hareketle geri alır. |
| **K13 — Belge numaralandırma** | `{ÖNEK}-{YYYY}-{NNN}`; yıl değişince NNN 1'den başlar. | `db.sonraki_belge_no()` ile: **IRS** (Satış), **IRA** (Alış), **IRT** (Transfer). |

**Önemli tasarım kararı:** İrsaliye onayı **`cari_hareket` üretmez.** İrsaliye fiziksel sevk
belgesidir; müşteri borcu/tedarikçi alacağı **Fatura** onaylandığında oluşur (K2/K6). İrsaliye
yalnız `stok_hareket` (ilgili_modul='Irsaliye') üretir — ilgili modül bu şekilde test edildi.

---

## 2) Veri modeli

### `irsaliye` (belge başlığı)
| Alan | Tip | Not |
|---|---|---|
| `id`, `irsaliye_no` | PK, UNIQUE | `IRS`/`IRA`/`IRT`-`YYYY`-`NNN` (K13) |
| `tip` | TEXT | `Satis` (müşteriye sevk) / `Alis` (tedarikçiden mal kabul) / `Transfer` (depo→depo) |
| `cari_id` | FK → cari_kart (nullable) | Satis→müşteri, Alis→tedarikçi; Transfer'de boş |
| `sube_id` | FK → sube (nullable) | **K1** — baştan nullable |
| `depo_id` | FK → depo | Kaynak depo (zorunlu) |
| `hedef_depo_id` | FK → depo (nullable) | Yalnız Transfer'de dolu |
| `kaynak_siparis_id` | FK → siparis (nullable) | **K8** — onaylı siparişten üretim |
| `tarih`, `durum` | | `Taslak / Onaylandı / İptal` |
| `para_birimi`, `ara/iskonto/kdv/genel_toplam` | | Teklif/Sipariş ile aynı formül |
| `aciklama` | | |

### `irsaliye_kalem`
`stok_id`, `varyant_id`, `miktar`, `birim_fiyat`, `iskonto_orani`, `kdv_orani`,
`tutar` (satır neti, KDV hariç), `aciklama`.

> Toplam formülü (Teklif/Sipariş ile aynı): satır net = miktar × birim_fiyat × (1 − isk/100);
> KDV = Σ(net × kdv/100); genel = ara + KDV.

### Stok etkisi (onayda)
- **Satis:** kaynak depodan çıkış (`stok_seviye.miktar −`, varsa `rezerve` de düşer), sipariş `teslim_edilen +`.
- **Alis:** kaynak depoya giriş (`stok_seviye.miktar +`).
- **Transfer:** kaynak depodan çıkış + hedef depoya giriş (çift yönlü).
- **İptal (onaylıyken):** yukarıdakilerin tamamı ters yönde geri alınır.

---

## 3) Rotalar (6 yeni · toplam 68)

| Rota | Metod | Yetki | Açıklama |
|---|---|---|---|
| `/irsaliye` | GET | giriş | Liste + tip/durum/arama filtresi, durum özetleri |
| `/irsaliye/yeni` | GET/POST | Admin·Muhasebe·Satis | Yeni; `?kaynak_siparis=ID` ile onaylı siparişten ön doldurma |
| `/irsaliye/{id}` | GET | giriş | Detay + durum işlemleri + audit |
| `/irsaliye/{id}/duzenle` | GET/POST | Admin·Muhasebe·Satis | Yalnız **Taslak** irsaliyeler |
| `/irsaliye/{id}/durum` | POST | **Admin·Muhasebe** | Onayla / İptal (yetki bazlı onay akışı) |
| `/irsaliye/{id}/yazdir` | GET | giriş | Antetli yazdır/PDF (Satış/Alış/Transfer başlıklı) |

Satır ekleme/silme sunucu taraflı; **barkod okutunca satır otomatik gelir** (K7 —
`stok.barkod_bul()`); iskonto varsayılanı K9 önceliğiyle önerilir. Siparişten geliyorsa
"Kaynak sipariş" bandı gösterilir; Transfer'de cari gizlenip `hedef_depo_id` istenir.

---

## 4) Ekranlar

1. **İrsaliye listesi** — tip/durum sekmeleri, arama, no/tarih/toplam rozetleri, Yazdır.
2. **İrsaliye formu** — tip, cari (türe göre filtrelenir), depo(+hedef), tarih, kalem tablosu (barkod + K9 iskonto), canlı toplamlar.
3. **İrsaliye detayı** — kalemler, durum işlemleri (Taslak→Onaylandı, İptal), kaynak sipariş bağlantısı, audit geçmişi.
4. **Yazdır/PDF** — antetli "SATIŞ İRSALİYESİ" / "ALIŞ İRSALİYESİ" / "TRANSFER İRSALİYESİ".
5. **Sipariş detayı** — "Bu siparişten oluşturulan irsaliyeler (N)" listesi + linkler (zincir izlenebilirliği).

---

## 5) Örnek test senaryosu (çalıştırıldı, geçti)

**Hazırlık:** `admin/1234` girişi; temiz seed (2 seed irsaliye).

| # | Adım | Beklenen | Sonuç |
|---|---|---|---|
| 1 | `GET /irsaliye` | 200; `BELGE-001` (Satış), `BELGE-NNN` (Alış) | ✅ |
| 2 | `GET /irsaliye/1/yazdir`, `/2/yazdir` | "SATIŞ İRSALİYESİ" / "ALIŞ İRSALİYESİ" | ✅ |
| 3 | `GET /irsaliye/yeni` | 200 | ✅ |
| 4 | **K10:** `?kaynak_siparis=1`(Tamamlandı) / `=2`(Bekliyor) | 302 → sipariş detayı (üretim engelli) | ✅ |
| 5 | SIP-002 onayla | `rezerve`: BUZ +2, KLM +1 | ✅ |
| 6 | `GET /irsaliye/yeni?kaynak_siparis=2` | Ön dolu: "Kaynak sipariş · BELGE-NNN" | ✅ |
| 7 | `POST /irsaliye/yeni` (BUZ x1) | 302 → `BELGE-NNN` (Taslak) | ✅ |
| 8 | **K11 kısmi teslim:** Onayla | BUZ 8→7, rezerve 2→1, teslim 1/2, SIP-002 **Kısmi** | ✅ |
| 9 | **İptal geri alma** | BUZ 7→8, rezerve 1→2, teslim 0, SIP-002 Onaylandı | ✅ |
| 10 | Transfer ANA→MAG (TV-43 x2) | `BELGE-NNN`; ANA 11→9, MAG 2→4 | ✅ |
| 11 | Alış (standalone, TV-43 x1) | `BELGE-002`; ANA 9→10 | ✅ |
| 12 | Yetki | `satis`: liste/yeni 200, onay 403 · `depo`: yeni 403 · anon: 302 | ✅ |
| 13 | Barkod satır ekleme (8691234500011) | "MARKA-B 43\" Crystal UHD 4K TV" satıra gelir | ✅ |
| 14 | **K13:** teklif üret | `BELGE-NNN`; irsaliye serileri IRS/IRA/IRT sıralı | ✅ |
| 15 | Cari hareket kontrolü | İrsaliye `cari_hareket` üretmez (tasarım gereği); `stok_hareket` üretir | ✅ |
| 16 | **Aşırı teslimat koruması** | Sipariş BUZ=2 iken irsaliyede BUZ=3 → red "sipariş kalanı 2, istenen 3"; siparişte olmayan ürün → red; iki ayrı Taslak irsaliye aynı kalanı paylaşamaz | ✅ |

---

## 6) Sıradaki adım (onayınıza bağlı)

**Fatura** (zincirin 4. halkası): satış/alış faturası, onaylı irsaliyeden tek tıkla üretim
(`kaynak_irsaliye_id` — K8), `SF`/`AF` numaralama (K13), **cari hareket** (borç/alacak) üretimi
(K2/K6 — mali etki burada), `teslim_edilen`/stok'a ek etki üretmez (stok etkisi İrsaliye'de bitti).
Fatura modülünde **K14** uygulanacak: "faturalanmamış irsaliyeler" filtresi + rozet, dashboard
bildirimi, irsaliye detayında "faturalandı" bilgisi.
