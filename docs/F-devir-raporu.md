# Brn Teknoloji ERP — Devir / Devamlılık Raporu (v1.31.0)

> Bu rapor, Arena.ai Agent Mode'a **yapıştırılarak** yeni bir oturum başlatmak için hazırlanmıştır.
> Amaç: F1'in kapandığını ve F2/F3'ün ne olduğunu, kod/veri/test durumuyla birlikte eksiksiz aktarmak.

---

## 1) Proje Kimliği

- **Uygulama:** Brn Teknoloji ERP — Flask + SQLite, çok şirketli, tamamen Türkçe UI.
- **Çalışma dizini:** `/home/user/erp` (modüller tek klasörde, `app.py` çoklu rota yüklüyor).
- **Sürüm:** `v1.31.0` (`config.py: SURUM = "1.31.0"`, `SURUM_TARIHI = "2026-09-11"`).
- **Kalıcı kurallar (tüm paketlerde geçerli):**
  1. Benzersiz zaman damgalı kanıt + MD5/SHA256 hash teslimi.
  2. Test/veri/kod üçlüsü: e2e test + temiz seed verisi + kod birlikte doğrulanır.
  3. Tam regresyon zorunlu (mevcut tüm `test_*.py` yeşil olmalı).
  4. Türkçe UI; K1 = şirket izolasyonu (`sirket_id` her satırda, sorgular `sirket_id` ile süzülür).
- **Önceki paketler (kapalı):** A (kasa/banka/stok/cari), B1 (satın alma talebi), B2 (alınan teklif),
  B3 (eksik teslimat), C (POS), D (bakım sözleşmesi), E (CRM aktivite/görev takibi, v1.30.0).

---

## 2) F1 — Mali Etki: "Zincirdeki İlk Belgede Bir Kere" — **KAPANDI** ✅

**Kural (kullanıcı onaylı):**
- **İrsaliyeli akış:** mali etki (cari borç/alacak + yevmiye) **irsaliye onayında** oluşur.
- **Kaynaklı fatura** (`fatura.kaynak_irsaliye_id IS NOT NULL`) onaylandığında **mali etki üretmez** — yalnızca belgeleştirir.
- **İrsaliyesiz akış** (POS, doğrudan fatura — `kaynak_irsaliye_id IS NULL`): mali etki **fatura onayında** doğmaya devam eder (eski davranış, dokunulmadı).

**Fiş deseni (`muhasebe._irsaliye_satirlar`):**
| İrsaliye tipi | Fiş satırları |
|---|---|
| Satış | `120 borç (genel) / 600 alacak (matrah) + 391 alacak (KDV)` |
| Alış — stoklu | `153 borç (matrah) + 191 borç (KDV) / 320 alacak (genel)` |
| Alış — manuel | `770 borç (matrah) + 191 borç (KDV) / 320 alacak (genel)` |
| Transfer | mali etki **yok** (yalnız depo stok transferi) |

**İş kuralları:**
- İrsaliye **onayı**: stok hareketi + `cari.hareket_ekle` (yön=1) + `muhasebe.fis_uret("Irsaliye", iid)`.
- İrsaliye **iptali**: kendisinden üretilmiş ve iptal edilmemiş fatura varsa iptal **engellenir**; yoksa stok + cari (yön=-1) + fiş geri alınır (`fis_sil("Irsaliye", iid)`).
- Fatura onay/iptal: `kaynak_irsaliye_id` dolu ise `_cari_uygula` + `fis_uret/fis_sil` atlanır.
- `muhasebe.toplu_uret`: yalnız `kaynak_irsaliye_id IS NULL` faturalara fiş üretir; onaylı (Transfer hariç) irsaliyelere `Irsaliye` fişi üretir — **idempotent**.
- Dashboard satış özeti sorguları `'Satış Faturası','Satış İrsaliyesi'` ikisini kapsar.

**Değişen dosyalar:**
| Dosya | Değişiklik |
|---|---|
| `muhasebe.py` | `_irsaliye_satirlar()`; `fis_uret`'e `Irsaliye` dalı; `toplu_uret` güncellemesi; fiş listesine `Irsaliye` rozeti (`KAYNAK_LABEL`) |
| `irsaliye.py` | `_cari_uygula_irsaliye()`; onay/iptal rotalarına mali etki + bağlı fatura engeli |
| `fatura.py` | onay/iptal rotalarında kaynaklı faturalar için mali etki atlaması |
| `cari.py` | `BELGE_TIPLERI` + `Satış İrsaliyesi`, `Alış İrsaliyesi` |
| `app.py` | dashboard satış özeti sorguları |
| `db.py` | `seed_irsaliye()` irsaliye cari hareketleri ekler; `seed_fatura()` kaynaklı faturaların cari hareketlerini KALDIRDI (çifte kayıt yok) |
| `templates/irsaliye/detay.html` | "Faturalandı" + "Faturasız" banner metinleri F1'e uyarlandı (aşağıda) |
| `test_f1_mali.py` | YENİ — 25 kontrollük F1 e2e testi |
| `test_eksik_teslimat.py`, `test_manuel_satir.py` | temizlik artık `Irsaliye` fiş + cari kalıntılarını da siler |

---

## 3) Kullanıcı Bulgusu + Yapılan Son Düzeltme ✅

**Bulgu (kullanıcı):** `templates/irsaliye/detay.html`'de faturalandırılmış irsaliye altında hâlâ
*"mali etki (cari borç/alacak) faturada işlendi"* yazıyordu — F1'in tam tersi. Veri doğruydu (cari
hareket `ilgili_modul='Irsaliye'`, fiş `kaynak_modul='Irsaliye'`), yalnız ekran metni eskiydi.

**Yapılan düzeltme:** Aynı dosyada İKİ banner düzeltildi (ikisi de aynı eski iddiayı taşıyordu):
- **"Faturalandı"** (satır ~49) → yeni: *"…mali etki (cari borç/alacak) bu irsaliyenin onayında işlendi; fatura yalnızca belgeleştirir."*
- **"Faturasız"** (satır ~54) → yeni: *"Mali etki (cari borç/alacak + yevmiye) bu irsaliyenin onayında işlendi — oluşturulacak fatura yalnızca belgeleştirir."*

Render doğrulandı: `/irsaliye/1` (faturalandı) ve `/irsaliye/3` (faturasız) yeni metinleri gösteriyor,
eski "faturada işlendi" / "üretmez" kalıntısı yok.

---

## 4) Doğrulama Kanıtları

| Kanıt | Sonuç |
|---|---|
| `test_f1_mali.py` (25 kontrol: onay mali etkisi, kaynaklı fatura etkisizliği, irsaliyesiz regresyon, alış stoklu/manuel desen, transfer etkisizliği, iptal engeli + geri alış, FK/yetim bütünlüğü) | **25/25** ✅ |
| Tam regresyon — 14 paket (POS 41 dahil) | **313/313, 0 başarısız** ✅ |
| Temiz seed DB (`db.init_db()` + `db.seed()`) | FK temiz, kaynaklı fatura cari hareketi YOK, irsaliye cari hareketi 3 kayıt ✅ |
| Ekran görüntüleri | `docs/ekran-goruntuleri/yeni-tema/f1-{irsaliye-detay, cari-ekstre, muhasebe-fisler, fis-detay, dashboard}.png` (5 adet) |

**Kaynak zip (final):** `/home/user/BrnTeknoloji-ERP-v1.31.0-kaynak.zip` (413 dosya, temiz seed DB dahil)
- **MD5:** `3e09b4f9153ed2180578c6117abacae5`
- **SHA256:** `a97e2179a541f185447b767df609fe8c20f049041710023a08a5a763ece2973f`

---

## 5) SIRADAKİ İŞ — F2 ve F3 (henüz başlanmadı)

### F2 — KDV Dahil / Hariç Fiyat Girişi
- Belge başlığına tek toggle: **"Fiyat Girişi: KDV Hariç / KDV Dahil"**.
- **KDV Dahil** seçilirse girilen tutar geriye ayrıştırılır: `net = brüt / (1 + kdv%/100)`.
- **DB'de her zaman NET tutulur** — mevcut mizan/kar-zarar hesapları bozulmaz.
- Kapsam: **teklif, sipariş, irsaliye, fatura, POS** — hepsinde aynı ortak yardımcı: `core.py: kdv_ayikla()`.

### F3 — Ortak Arama / Tip-ahead Seçici
- Mevcut `barkod_bul()` / API arama altyapısı genişletilip **tüm stok/cari/tedarikçi seçim noktalarına**
  tek bir ortak bileşen olarak yayılır; uzun `<select>` listeleri yerine yazarak filtreleme.
- Noktalar: teklif, sipariş, irsaliye, fatura, satın alma talebi/teklif, servis, bakım sözleşmesi, CRM.

**Protokol:** her paket için önce (1) veri modeli + (2) ekran listesi + (3) test senaryosu hazırlanır,
uygulanır, e2e test + tam regresyon koşulur, dokümantasyon + ekran görüntüsü + zip + hash teslim edilir.

---

## 6) Yeni Oturuma Başlarken (dosyalar yoksa)

Yeni bir Arena.ai oturumu **workspace'i boş** başlıyorsa, bu rapor tek başına kodu geri getiremez.
Koda ulaşmak için iki yol var:
1. **Zip dosyası:** `BrnTeknoloji-ERP-v1.31.0-kaynak.zip` (yukarıdaki hash'lerle doğrulayıp `erp/` klasörüne açın).
2. **Workspace aktarımı:** aynı oturum devam ediyorsa kod zaten `/home/user/erp` içinde hazırdır.

Kritik dosyalar: `app.py`, `core.py`, `db.py`, `config.py`, `muhasebe.py`, `irsaliye.py`, `fatura.py`,
`cari.py`, `stok.py`, `pos.py`, `teklif.py`, `siparis.py`, `crm.py`, `bakim.py` + `templates/` + `test_*.py`.

> Not: `templates/fatura/form.html` satır ~11'de "mali etkinin oluştuğu adım" ifadesi irsaliyesiz/POS
> için doğru; kaynak irsaliyeli fatura formunda "oluştuğu adım irsaliyedir" nüansı opsiyonel olarak
> dinamikleştirilebilir (F1 kapsamında zorunlu değildi, kullanıcıya bırakıldı).
