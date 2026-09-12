# Faz 1 — Çekirdek: Stok / Stok2 Modülü (Özet & Onay)

> Proje komutundaki "her fazın sonunda veri modeli özeti + ekran listesi + örnek test
> senaryosu üret ve onay iste" kuralı gereği hazırlanmıştır. Faz 1'in 2. modülü.

---

## 1) Bu fazda ne yapıldı?

- **Stok (ana modül):** ürün kartı, seri/lot takibi, kritik stok + otomatik uyarı,
  manuel stok hareketi, stok sayımı ve sayım farkı işleme, kartoteks görünümü.
- **Stok2 (ikincil/detay modülü):** çoklu depo dağılımı, depolar arası transfer,
  depo bazlı min/max kuralları, ürün–tedarikçi eşleştirme, toplu fiyat/iskonto güncelleme.
- Tüm isterler **çalışan web uygulaması** olarak teslim edildi (LIVE PREVIEW: `admin / 1234`).

---

## 2) Veri Modeli (yeni tablolar)

| Tablo | Amaç | Kritik Alanlar |
|---|---|---|
| `kategori` | Ürün kategorileri (hiyerarşik) | ust_id, ad |
| `marka` | Marka tanımları | ad |
| `depo` | Çoklu depo (Stok2) | kod, ad, tip (Ana/Mağaza/Servis) |
| `stok_kart` | Ürün kartı | kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler |
| `stok_varyant` | Varyantlar (renk/model/kapasite) | stok_id, varyant_kodu, ad, ozellikler, alis/satis_fiyat, kritik_stok |
| `stok_seviye` | Depo bazlı stok miktarı + min/max | stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok |
| `stok_hareket` | **TEK kronolojik hareket tablosu** (Kartoteks kaynağı) | stok_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, belge_no, seri_nolar, **ilgili_modul, ilgili_kayit_id** |
| `stok_seri` | Seri no / IMEI kayıtları | stok_id, seri_no, durum, depo_id, giris/cikis_tarihi, ilgili_modul/kayit_id |
| `stok_sayim` + `stok_sayim_kalem` | Sayım başlığı + kalemleri | durum (Taslak/Tamamlandi), sistem_miktar, sayilan_miktar |
| `stok_tedarikci` | Ürün–tedarikçi eşleştirme | stok_id, cari_id, tedarikci_kod, alis_fiyat, oncelik |
| `depo_transfer` + `depo_transfer_kalem` | Depolar arası transfer | kaynak/hedef depo, durum, miktar |

**Verilen 4 kritere uyum:**

1. **`fiyat_kural` rezervi:** `stok_kart` üzerinde ileride eklenecek kural tablosuyla
   (`stok_id`, `cari_id`/`cari_grup_id`, `baslangic_tarih`, `bitis_tarih`, `tip`, `deger`, `oncelik`)
   çakışacak bir alan yoktur; kural tablosu **ayrı** tutulacak (şimdilik açılmadı).
2. **Entegrasyon deseni:** `stok_hareket.ilgili_modul` / `ilgili_kayit_id`, `cari_hareket`
   ile aynı deseni taşır — Faz 2'de Fatura/İrsaliye/Sipariş hareketleri buraya referansla otomatik yazacak.
3. **Kartoteks hazırlığı:** Tüm stok hareketleri (giriş/çıkış/transfer/sayım farkı) tek
   `stok_hareket` tablosunda; Kartoteks (Bölüm 1.17) buradan **salt-okunur** beslenecek.
4. **Stok ↔ Stok2 ayrımı:** Stok = kart + sayım + kritik; Stok2 = çoklu depo + transfer +
   min/max + tedarikçi eşleştirme + toplu fiyat/iskonto. Komut Bölüm 1.5'e birebir uyumlu.

---

## 3) API Uçları (route listesi)

| Metod | Yol | Yetki* | İşlev |
|---|---|---|---|
| GET | `/stok` | giriş | Filtreli stok listesi (arama, kategori, depo, kritik) |
| GET/POST | `/stok/yeni` | A·M·D | Yeni stok kartı |
| GET | `/stok/{id}` | giriş | Kart detayı (Genel/Varyant/Hareket/Seri/Tedarikçi/Not/Log sekmeleri) |
| GET/POST | `/stok/{id}/duzenle` | A·M·D | Kart düzenleme |
| POST | `/stok/{id}/minmax` | A·M·D | Depo bazlı min/max atama |
| POST | `/stok/{id}/not` | giriş | İlişkisel not |
| GET | `/stok/hareketler` | giriş | Kronolojik hareket geçmişi (kartoteks) |
| GET/POST | `/stok/hareket/yeni` | A·M·D | Manuel giriş/çıkış (seri no destekli) |
| GET/POST | `/stok/sayim` | A·M·D | Sayım listesi + yeni sayım |
| GET/POST | `/stok/sayim/{id}` | A·M·D | Sayım detayı + kalem ekleme |
| POST | `/stok/sayim/{id}/tamamla` | A·M·D | Sayımı tamamla (fark → hareket) |
| GET/POST | `/stok/transferler` | A·M·D | Transfer listesi + yeni transfer |
| GET/POST | `/stok/transferler/{id}` | A·M·D | Transfer detayı + kalem ekleme |
| POST | `/stok/transferler/{id}/tamamla` | A·M·D | Transferi tamamla (çift yönlü hareket) |
| GET/POST | `/stok/toplu` | A·M | Toplu fiyat/iskonto güncelleme |
| GET/POST | `/stok/depolar` | A·M·D | Depo listesi + yeni depo |

\* A=Admin, M=Muhasebe, D=Depo. Okuma uçları tüm rollerde; yazma uçları belirtilen rollerde.

---

## 4) Ekran Listesi

1. **Stok Listesi** — arama/kategori/depo/kritik filtreleri, KDV, alış/satış, toplam stok,
   seri/varyant rozetleri, "Kritik altı / Stok yok / Normal" durumları.
2. **Yeni/Düzenle Stok Kartı** — tanım (SKU, barkod, marka, kategori, teknik özellikler),
   fiyat & vergi (KDV, ÖTV, iskonto), seri-lot ve varyant anahtarları.
3. **Stok Kartı Detayı** — 7 sekmeli: Genel (depo dağılımı + min/max), Varyantlar,
   Hareketler, Seri No, Tedarikçiler, Notlar, Geçmiş (audit).
4. **Hareket Geçmişi** — tüm depoların kronolojik akışı; kaynak modül rozeti.
5. **Hareket Ekle** — giriş/çıkış yönü, işlem tipi, miktar, maliyet, seri no girişi.
6. **Sayımlar + Sayım Detayı** — sistem vs sayılan miktar, fark kolonu, tamamlama.
7. **Transferler + Transfer Detayı** — kaynak→hedef, yetersiz stok kontrolü, tamamlama.
8. **Toplu Güncelleme** — kategori/marka/seçili/tümü × ayarla/artır/azalt.
9. **Depolar** — depo listesi + stok özetleri + yeni depo.

---

## 5) Örnek Test Senaryosu

1. `admin / 1234` ile giriş yap → Stok → Yeni Ürün.
2. **Kart:** "MARKA-B 50\" Crystal TV", kategori Televizyon, marka MARKA-B, alış 22.000 ₺,
   satış 27.999 ₺, KDV %20, kritik stok 3, **Seri No takibi açık** → Kaydet.
3. **Serili giriş:** Hareket Ekle → ürünü seç, depo "Ana Depo", yön Giriş, işlem
   "Stok Girişi (Alış)", miktar 5, seri no `50C0001,…,50C0005` → stok 5, seriler "Stokta".
4. **Çıkış:** aynı ürüne yön Çıkış, "Satış Çıkışı", miktar 2, seri `50C0001, 50C0002` →
   stok 3; seçilen seriler "Satıldı" olur.
5. **Kritik uyarı:** miktarı 2'ye düşüren çıkış yap (stok 1 < kritik 3) → Dashboard'da
   "Kritik stok seviyesi" bildirimi belirir.
6. **Sayım:** Sayım → Ana Depo → ürünü seç, sayılan miktarı sistemden farklı gir
   → Tamamla → "Sayım Farkı" hareketi oluşur, stok güncellenir.
7. **Transfer:** Transfer → Ana → Mağaza, ürün + miktar → Tamamla → çift yönlü hareket
   ve depo bakiyeleri güncellenir (yetersiz stokta tamamlama engellenir).
8. **Toplu güncelleme:** Toplu Güncelle → kategori "Televizyon" → satış fiyatı %5 artır
   → kategori altındaki tüm ürünlerin satış fiyatı güncellenir.
9. **Yetki:** `depo / 1234` yeni kart açabilir; `satis / 1234` açamaz (403),
   Toplu Güncelleme'yi yalnızca Muhasebe/Admin görür.
10. **Kartoteks izi:** Stok → Hareket Geçmişi → her hareketin `ilgili_modul`
    (Alış/Satış/Transfer/Sayım/Servis) kaynağı görünür.

---

## 6) Sonraki Adım (onay bekleniyor)

Faz 1'in kalan modülleri: **Kasa → Banka → Depo/Şube** (şube yönetimi). Onay verirsen
**Kasa** modülüyle devam ederim.

---

## 7) Ek — Onay sonrası kapatılan 3 eksik

1. **Varyant barkodu:** `stok_varyant` tablosuna `barkod` alanı eklendi (şemada zaten
   mevcuttu; seed dolduruldu, Varyantlar sekmesinde gösteriliyor). Her varyant ayrı
   barkod taşır: `TEL-14-LG-009-W → 8691234500103`, `TEL-14-LG-009-I → 8691234500110`.
2. **Kartoteks dışa aktarma:** "Stok → Hareket Geçmişi" ekranına **⬇ Excel (.xlsx)** ve
   **🖨 PDF/Yazdır** butonları eklendi. Excel gerçek `.xlsx` (openpyxl) üretir; CSV
   (UTF-8 BOM, noktalı virgül) yedek format; PDF, yazdırılabilir rapor görünümüyle
   ("Yazdır → PDF olarak kaydet") alınır. Dışa aktarma aktif filtreleri korur.
3. **Barkod hızlı sorgulama:** Stok Listesi'ne "🔍 Barkod" kutusu eklendi. Barkod okutulunca
   doğrudan ürün kartına; varyant barkoduysa kartın Varyantlar sekmesine atlar.
   `barkod_bul()` yardımcısı `stok.py` içinde tanımlıdır ve **Faz 2'de Fatura/İrsaliye/Sipariş
   satır girişinde barkod okutunca satırın otomatik gelmesi için bu yardımcı kullanılacaktır**
   (kod içi not düşüldü).
