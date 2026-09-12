# Faz 1 — Çekirdek: Kasa Modülü (Özet & Onay)

> Proje komutundaki "her fazın sonunda veri modeli özeti + ekran listesi + örnek test
> senaryosu üret ve onay iste" kuralı gereği hazırlanmıştır. Faz 1'in 3. modülü.

---

## 1) Bu fazda ne yapıldı?

- **Kasa modülü** uçtan uca çalışır şekilde teslim edildi (LIVE PREVIEW: `admin / 1234`).
- Çoklu kasa desteği, nakit giriş/çıkış, açılış bakiyesi, kasa fişi (yazdırılabilir),
  günlük kasa raporu, kasa ↔ banka transferi (Banka modülüne bağlanacak şekilde).
- Dashboard "Kasa Durumu" KPI'ı artık gerçek toplam nakit bakiyesini gösteriyor.

## 2) Veri Modeli (yeni tablolar)

| Tablo | Amaç | Kritik Alanlar |
|---|---|---|
| `kasa` | Kasa tanımları (mağaza, servis…) | kod, ad, aktif |
| `kasa_hareket` | Kasa hareketleri | kasa_id, tarih, islem_tipi, tutar, belge_no, aciklama, ilgili_modul, ilgili_kayit_id |

**İş mantığı:**

- `islem_tipi` yönü belirler: `Açılış Bakiyesi (+)`, `Nakit Girişi (+)`, `Banka → Kasa (+)`,
  `Nakit Çıkışı (−)`, `Kasa → Banka (−)`. `tutar` her zaman pozitif tutulur.
- Bakiye = Σ(giriş) − Σ(çıkış). "Nakit Çıkışı" ve "Kasa → Banka" için **yetersiz bakiye kontrolü** vardır.
- Kasa ↔ banka hareketleri `ilgili_modul='Transfer'` ile işaretlenir; Faz 1'deki Banka
  modülü bu hareketlerin karşı tarafını otomatik üretecek (entegrasyon noktası hazır).

## 3) API Uçları (route listesi)

| Metod | Yol | Yetki* | İşlev |
|---|---|---|---|
| GET | `/kasa` | giriş | Kasa listesi + bakiyeler + hareketler (kasa filtresi) |
| GET/POST | `/kasa/yeni` | A·M·S | Yeni kasa tanımı |
| GET/POST | `/kasa/hareket` | A·M·S | Nakit giriş/çıkış, açılış, transfer |
| GET | `/kasa/rapor` | giriş | Günlük rapor (açılış/giriş/çıkış/kapanış) — `?tarih=` |
| GET | `/kasa/hareket/{id}/fis` | giriş | Yazdırılabilir kasa fişi |

\* A=Admin, M=Muhasebe, S=Satış. Okuma tüm rollerde; yazma A/M/S.

## 4) Ekran Listesi

1. **Kasa** — toplam nakit KPI, kasa kartları (bakiye, giriş/çıkış), hareket listesi.
2. **Yeni Kasa** — ad + otomatik kod.
3. **Kasa Hareketi** — kasa, tarih, işlem tipi (giriş/çıkış gruplu), tutar, belge no, açıklama.
4. **Günlük Rapor** — tarih seçimi, genel KPI'lar, kasa bazlı açılış/kapanış ve hareketler.
5. **Kasa Fişi** — yazıcı dostu (monospace) fiş, yazdır/PDF.

## 5) Örnek Test Senaryosu

1. `admin / 1234` → Kasa. "Mağaza Kasası" ve "Servis Kasası" bakiyelerini gör.
2. **Yeni kasa:** + Yeni Kasa → "Depo Kasası" → görünür, bakiye 0.
3. **Açılış bakiyesi:** Hareket → Depo Kasası, işlem "Açılış Bakiyesi", 10.000 ₺ → bakiye 10.000 ₺.
4. **Nakit girişi:** 2.500 ₺ "Nakit Girişi" (belge T-099) → bakiye 12.500 ₺.
5. **Nakit çıkışı (yetersiz bakiye):** 50.000 ₺ "Nakit Çıkışı" dene → reddedilir, flash uyarı.
6. **Transfer:** Mağaza Kasası → "Kasa → Banka" 5.000 ₺ → bakiye düşer, hareket "Transfer" rozetli.
7. **Günlük rapor:** /kasa/rapor?tarih=bugün → açılış/giriş/çıkış/kapanış tutarları doğru.
8. **Fiş:** herhangi bir hareketin "Fiş" butonu → yazdırılabilir fiş açılır.
9. **Yetki:** `depo` ve `servis` /kasa'yı görür (200), hareket giremez (403).

## 6) Sonraki Adım (onay bekleniyor)

Faz 1'in kalan modülleri: **Banka → Depo/Şube**. Onay verirsen **Banka** modülüyle devam ederim.

---

## 7) Ek — Onay sonrası düzeltme: Cari ↔ Kasa bağlantısı

İşaret edilen eksik kapatıldı:

1. **`kasa_hareket.cari_id`** eklendi (opsiyonel, `cari_kart` FK). Var olan veritabanı
   için `init_db` içinde `_migrate` ile `ALTER TABLE` uygulanır (test edildi).
2. **Tek işlem = iki kayıt:** Kasa Hareketi ekranında "Nakit Girişi / Nakit Çıkışı"
   seçilince opsiyonel **Cari** alanı çıkar. Cari seçilirse:
   - Nakit Girişi → `cari_hareket` **Tahsilat (alacak)**, `ilgili_modul='Kasa'`,
     `ilgili_kayit_id = kasa_hareket.id`
   - Nakit Çıkışı → `cari_hareket` **Ödeme (borç)**, aynı referansla
   - Cari seçilmezse (tezgah satışı, kırtasiye gideri) yalnızca kasa kaydı yazılır — eski davranış korunur.
3. Kasa listesi ve fişinde **Cari** sütunu gösterilir (cari kartına linkli).
4. Aynı düzeltilmiş desen **Banka modülüne** de uygulandı (havale/EFT giriş/çıkış + cari).

Kasa ↔ Banka transferleri de opsiyonel karşılık üretir: kasa tarafında banka hesabı
seçilirse `banka_hareket`, banka tarafında kasa seçilirse `kasa_hareket` otomatik yazılır
(`ilgili_modul='Transfer'`).
