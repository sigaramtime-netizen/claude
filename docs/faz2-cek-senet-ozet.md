# Faz 2 · Çek/Senet Modülü — Özet (onay için)

> Modül: **Çek / Senet** — Faz 2 Satış Döngüsü'nün **5. halkası** (Teklif → Sipariş → İrsaliye
> → Fatura → **Çek/Senet** → Döviz Takip).
> Bu özetle birlikte, kullanıcının son turda istediği iki kalıcı karar da kodlandı ve burada
> raporlanıyor: **K15 (kısmi ödenmiş belge iptali engeli)** ve **K16 (genel ek dosya altyapısı)**.
> Şartlı onayda istenen iki eksik de bu revizyonda tamamlandı: **(a) `Tahsile Verildi` +
> `Karşılıksız` durumları** (Karşılıksız → önceki tahsilat cari hareketi geri alınır) ve
> **(b) vade takvimi + yaklaşan vade uyarısı** (K17).

---

## 1. Veri modeli

**`cek_senet`** (tek başlık tablosu; çek/senet satırlı bir belge değildir — her çek/senet bir kayıttır)

| Alan | Açıklama |
|---|---|
| `no` | Çek/senet numarası (bankadan gelen gerçek numara — K13 sayaç kullanılmaz) |
| `tip` | `Alinan` (müşteriden aldık, tahsil edeceğiz) / `Verilen` (tedarikçiye verdik, ödeyeceğiz) |
| `tur` | `Cek` / `Senet` |
| `cari_id`, `sube_id` | Cari + şube (K1 gereği nullable `sube_id`) |
| `banka`, `sube_ad` | Banka adı + banka şubesi |
| `tutar`, `keside_tarihi`, `vade` | Tutar, keşide tarihi, vade |
| `durum` | `Bekliyor` → `Tahsile Verildi` → `Tahsil Edildi` / `Karşılıksız`; `Ödendi` / `Ciro` / `İptal` (CHECK: 7 durum — K17) |
| `created_by`, `created_at`, `updated_at` | İzleme |

**`ek_dosya`** (K16 — genel attachment; Çek/Senet baştan bu tabloyu kullanır)

| Alan | Açıklama |
|---|---|
| `ilgili_modul`, `ilgili_kayit_id` | `CekSenet` + id (Notlar deseniyle birebir) |
| `dosya_adi`, `dosya_yolu`, `dosya_tipi`, `boyut` | jpg/png/pdf; 15 MB limit; diskte saklanır |
| `yukleyen_kullanici`, `tarih` | Kim, ne zaman |

---

## 2. Rotalar (6 yeni)

| Rota | Amaç | Yetki |
|---|---|---|
| `GET /cek_senet` | Liste + filtreler (tip/tür/durum/arama) + portföy özeti | herkes |
| `GET/POST /cek_senet/yeni` | Yeni çek/senet | Admin/Muhasebe |
| `GET /cek_senet/{id}` | Detay (durum işlemleri + **Ekler** + audit) | herkes |
| `GET/POST /cek_senet/{id}/duzenle` | Düzenle (yalnız Bekliyor) | Admin/Muhasebe |
| `POST /cek_senet/{id}/durum` | Durum geçişi (izin matrisi + cari hareket + Karşılıksız geri alma + K15 engeli) | Admin/Muhasebe |
| `GET /cek_senet/{id}/yazdir` | Yazdırılabilir görünüm | herkes |
| `GET /cek_senet/vade` | **Vade takvimi** — geciken / bugün / yaklaşan / ileriki dilimleri | herkes |

Ek olarak bu turda gelen **altyapı rotaları**:

| Rota | Amaç |
|---|---|
| `POST /ek/yukle`, `GET /ek/{id}`, `POST /ek/{id}/sil` | K16 — genel attachment |
| `POST /kasa/hareket/{id}/iptal`, `POST /banka/hareket/{id}/iptal` | K15 — bağlı hareketi çözme |

**Fiili toplam rota sayısı: 86** (önceki 74 + 12).

---

## 3. Ekranlar (5 yeni şablon)

1. `cek_senet/liste.html` — portföy kartları (Alınacak/Ödenecek), tip/tür/durum sekmeleri, arama.
2. `cek_senet/form.html` — tip değiştirince cari listesi otomatik yenilenir; tutar/vade/banka.
3. `cek_senet/detay.html` — durum işlemleri + bilgiler + **Ekler bölümü** + audit.
4. `cek_senet/yazdir.html` — yazdırılabilir kart.
5. `cek_senet/vade.html` — **vade takvimi** (4 dilim: geciken / bugün / yaklaşan / ileriki).
6. `ekler_bolum.html` — paylaşılan "Ekler" parçası (Fatura/İrsaliye/Çek-Senet'te ortak).

---

## 4. Davranış / kurallar

- **K2/K6:** `Alinan` çek/senet **Tahsil Edildi** → müşteriye ALACAK; `Verilen` çek/senet
  **Ödendi** → tedarikçiye BORÇ. Cari hareket **tek işlemle** yazılır
  (`ilgili_modul='CekSenet'`, `ilgili_kayit_id=id`).
- **Durum matrisi (K17):** `Bekliyor → Tahsile Verildi/Tahsil Edildi/Ödendi/Ciro/İptal`;
  `Tahsile Verildi → Tahsil Edildi/Karşılıksız/İptal`; `Tahsil Edildi → Karşılıksız/İptal`;
  `Karşılıksız → Tahsil Edildi/Ciro/İptal`. Ciro/Tahsil/Karşılıksız yalnız **Alınan**, Ödendi
  yalnız **Verilen** için anlamlı (tip kısıtı zorlanır).
- **Karşılıksız geri alma:** `Tahsil Edildi` iken `Karşılıksız` yapılırsa o çek/senetin daha önce
  yazdığı Tahsilat cari hareketi **silinir** (çek tahsil edilmemiş sayılır); `Karşılıksız →
  Tahsil Edildi` alacağı yeniden yazar.
- **Vade takvimi + uyarı:** `/cek_senet/vade` ekranı; bildirim taraması (Teklif deseni) vadesi
  **geçen** → `uyari`, vadesine **≤3 gün** kalan → `bilgi` üretir (okunmamışsa tekrar üretmez).
- **İptal geri alma:** Tahsil/Ödendi'den iptal → çek/senetin kendi cari hareketi silinir (net sıfır).
- **K15:** iptal, kendisine bağlı Kasa/Banka hareketi varsa **engellenir**.
- **K16:** fiziksel çek/senet görüntüsü "Ekler" bölümünden yüklenir (jpg/png/pdf, çoklu).

---

## 5. K15 — Kısmi ödenmiş belge iptali (karar + uygulama)

**Karar (kalıcı ilke):** Kullanıcının önerdiği iki seçenek birlikte uygulandı — (a) bağlı
tahsilat varsa **iptali engelle** + (b) fatura kartında **ödeme durumu bandı**. Çek/Senet'e
aynı mekanizma kuruldu. Bu ilke `docs/mimari-kurallar.md` K15'e işlendi.

Akış (test edildi):
1. Fatura onayı → müşteriye borç (cari hareket `ilgili_modul='Fatura'`).
2. Kasa'dan 10.000 ₺ tahsilat, **"Bağlı Fatura"** seçilerek faturaya bağlanır
   (`kasa_hareket.ilgili_modul='Fatura'`).
3. Fatura kartında **Ödeme Durumu** bandı: "Tahsil edilen: 10.000,00 ₺ · Kalan: 11.598,80 ₺".
4. Fatura iptali denenir → **engellenir** ("önce ilgili hareketi iptal edin").
5. Kasa hareketi iptal edilir (cari karşılığı da geri alınır).
6. Fatura iptali artık serbesttir → kendi cari hareketi silinir, **net sıfır**.

---

## 6. K16 — Genel ek dosya altyapısı (karar + uygulama)

- Tek `ek_dosya` tablosu; `notlar` deseniyle birebir; jpg/png + PDF; 15 MB; çoklu dosya.
- `core.Request`'e **multipart/form-data** desteği eklendi (stdlib, `cgi`'siz).
- Rotalar: yükle/liste/indir/sil. Yetki: yükle-sil Admin/Muhasebe/Satış; indir herkes.
- **Çek/Senet baştan dahil**; **İrsaliye + Fatura** detaylarına geriye dönük "Ekler" bölümü
  eklendi (mevcut kod yeniden yazılmadı — detay işleyicilerine 4 satır eklendi).

---

## 7. Örnek test senaryoları (hepsi bu turda çalıştırıldı ✅)

1. **Çek oluştur** — `TEST-CEK-001` (Alınan, 5.000 ₺) → liste/detayda görünür. ✅
2. **Tahsil** — "Tahsil Edildi" → cari harekette müşteriye ALACAK 5.000 ₺ (CekSenet bağlantılı). ✅
3. **Çek iptal** — Tahsil'den iptal → alacak hareketi silinir (bakiye net sıfır). ✅
4. **Fatura onay + kısmi tahsil** — 21.598,80 ₺ fatura, Kasa'dan 10.000 ₺ bağlı tahsilat. ✅
5. **Ödeme bandı** — detayda "Tahsil edilen 10.000,00 ₺ · Kalan 11.598,80 ₺". ✅
6. **K15 engel** — bağlı tahsilat varken fatura iptali engellendi (durum Onaylandı kaldı). ✅
7. **Kasa hareket iptali** — tahsilat + cari karşılığı silindi. ✅
8. **Engel sonrası iptal** — fatura iptali artık başarılı; kendi cari hareketi silindi. ✅
9. **Attachment yükleme** — multipart ile PNG → `ek_dosya` satırı + diskte dosya. ✅
10. **Attachment indirme** — `/ek/{id}` 200 + `image/png`. ✅
11. **İrsaliye/Fatura/Çek detayda "Ekler" bölümü** görünür. ✅
12. **Temiz seed** — test sonrası fatura=2, cek_senet=3, cari_hareket=17, ek_dosya=0, kasa_hareket=9. ✅
13. **Tahsile Verildi → Tahsil → Karşılıksız zinciri** — `TEST-CEK-999`: Bekliyor→Tahsile Verildi→
    Tahsil Edildi (ALACAK 5.000 ₺ yazıldı) → Karşılıksız (alacak geri alındı, hareket 0). ✅
14. **Karşılıksız → sonradan Tahsil** — alacak yeniden yazıldı; ardından İptal → net sıfır. ✅
15. **Geçersiz geçişler engellenir** — `Bekliyor→Karşılıksız` (Alınan) ve `Verilen→Karşılıksız`
    reddedildi; durum değişmedi. ✅
16. **Vade takvimi ekranı** — 4 dilim görünür; geciken (SNT-002), yaklaşan (SNT-001), ileriki
    (CEK-001/002) doğru gruplandı. ✅
17. **Vade bildirimi** — SNT-002 → "vadesi geçti" (uyari), SNT-001 → "vadesi yaklaşıyor" (bilgi);
    dashboard'da bildirimler oluştu (mükerrer üretim yok). ✅
18. **Yeni seed** — 5 kayıt: CEK-001 (Bekliyor), SNT-001 (Tahsile Verildi), CEK-002 (Verilen,
    Bekliyor), CEK-003 (Karşılıksız), SNT-002 (vadesi geçmiş, Bekliyor). ✅

---

## 8. Sonraki adım

- **Döviz Takip** (Faz 2'nin son halkası) — çek/senet + fatura + kasa/banka `para_birimi` ve
  `doviz_kur` alanları hazır.
- Çek/Senet için ileride: cari kartoteks'e çek/senet ekstresi bağlama (altyapı hazır).
