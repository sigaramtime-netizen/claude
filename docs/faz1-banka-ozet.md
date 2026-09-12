# Faz 1 — Çekirdek: Banka Modülü (Özet & Onay)

> Proje komutundaki "her fazın sonunda veri modeli özeti + ekran listesi + örnek test
> senaryosu üret ve onay iste" kuralı gereği hazırlanmıştır. Faz 1'in 4. modülü.
> Kasa'daki cari bağlantısı düzeltmesiyle **aynı desen** Banka'da da uygulandı.

---

## 1) Bu fazda ne yapıldı?

- **Banka modülü** uçtan uca çalışır şekilde teslim edildi (LIVE PREVIEW: `admin / 1234`).
- Banka hesap tanımları (banka adı, şube, IBAN, hesap no), havale/EFT giriş/çıkış,
  açılış bakiyesi, banka ↔ kasa transferi, hesap ekstresi (yürüyen bakiye),
  CSV ekstre içe aktarma.
- **Cari bağlantısı (Kasa ile aynı desen):** Havale/EFT hareketinde opsiyonel cari
  seçilirse `cari_hareket` otomatik oluşur — çifte veri girişi yok.

## 2) Veri Modeli (yeni tablolar)

| Tablo | Amaç | Kritik Alanlar |
|---|---|---|
| `banka_hesap` | Banka hesap tanımları | kod, ad, banka_adi, sube, iban, hesap_no, para_birimi, aktif |
| `banka_hareket` | Banka hareketleri | banka_hesap_id, tarih, islem_tipi, tutar, **cari_id**, belge_no, aciklama, ilgili_modul, ilgili_kayit_id |

**İş mantığı:**

- Yön `islem_tipi` ile: `Açılış Bakiyesi(+)`, `Havale/EFT Girişi(+)`, `Kasa → Banka(+)`,
  `Banka Ekstresi (Giriş)(+)` / `Havale/EFT Çıkışı(−)`, `Banka → Kasa(−)`, `Banka Ekstresi (Çıkış)(−)`.
- Çıkış yönlü işlemlerde **yetersiz bakiye kontrolü**.
- **Cari karşılığı:** Havale/EFT Girişi + cari → `cari_hareket` Tahsilat (alacak);
  Havale/EFT Çıkışı + cari → Ödeme (borç); `ilgili_modul='Banka'`, `ilgili_kayit_id=banka_hareket.id`.
- **Kasa karşılığı:** Kasa → Banka / Banka → Kasa'da opsiyonel kasa seçilirse `kasa_hareket`
  otomatik (Transfer). Kasa modülünden girilen transferlerde de banka tarafı otomatik oluşur.
- **CSV içe aktarma:** `tarih;tutar;aciklama` satırları "Banka Ekstresi (Giriş/Çıkış)"
  hareketine dönüşür; otomatik mutabakat (faturalarla eşleştirme) Faz 2'de Fatura modülüyle gelecek.

## 3) API Uçları (route listesi)

| Metod | Yol | Yetki* | İşlev |
|---|---|---|---|
| GET | `/banka` | giriş | Hesap listesi + bakiyeler + hareketler (hesap filtresi) |
| GET/POST | `/banka/yeni` | A·M | Yeni banka hesabı |
| GET/POST | `/banka/hareket` | A·M | Havale/EFT, açılış, transfer (cari/kasa bağlantılı) |
| GET | `/banka/hesap/{id}` | giriş | Hesap ekstresi (yürüyen bakiye) |
| POST | `/banka/import` | A·M | CSV ekstre içe aktarma |

\* A=Admin, M=Muhasebe. Okuma tüm rollerde; yazma A/M.

## 4) Ekran Listesi

1. **Banka** — toplam bakiye KPI, hesap kartları (bakiye, IBAN, giriş/çıkış), hareket listesi,
   CSV içe aktarma kartı.
2. **Yeni Hesap** — hesap adı, banka, şube, IBAN, hesap no, para birimi.
3. **Banka Hareketi** — hesap, tarih, işlem tipi (giriş/çıkış gruplu), tutar, belge no,
   opsiyonel cari (havale/EFT) ve kasa (transfer).
4. **Hesap Ekstresi** — KPI'lar + yürüyen bakiyeli hareket listesi (cari linkli).

## 5) Örnek Test Senaryosu

1. `admin / 1234` → Banka. Ziraat ve Garanti hesaplarını bakiyeleriyle gör.
2. **Yeni hesap:** + Yeni Hesap → "İş Bankası — Ticari", IBAN ile kaydet.
3. **Havale tahsilat (cari bağlantılı):** Hareket → hesap Ziraat, "Havale/EFT Girişi",
   5.000 ₺, cari "Batman Çarşı Elektronik" → hem banka bakiyesi artar hem cari ekstresine
   "Tahsilat 5.000 ₺" (ilgili_modul='Banka') düşer.
4. **EFT ödeme (cari bağlantılı):** "Havale/EFT Çıkışı", 2.000 ₺, cari "Vestel Dist." →
   cari ekstresine "Ödeme 2.000 ₺" düşer.
5. **Transfer:** "Banka → Kasa", 3.000 ₺, kasa "Servis Kasası" → bankada çıkış, kasada giriş
   (iki taraf otomatik, Transfer referanslı).
6. **Yetersiz bakiye:** 999.999 ₺ çıkış dene → reddedilir, flash uyarı.
7. **CSV içe aktarma:** hesabı seç, `2026-09-05;1500;Havale` satırını yapıştır → "Banka
   Ekstresi (Giriş)" hareketi oluşur.
8. **Ekstre:** hesaba gir → yürüyen bakiye kolonu doğru sıralanır.
9. **Yetki:** `muhasebe` yazabilir; `satis`/`depo` görür ama yazamaz (403).

## 6) Sonraki Adım (onay bekleniyor)

Faz 1'in son modülü: **Depo/Şube** (çok şubeli yapı + şube bazlı yetkilendirme/raporlama).
Onay verirsen **Depo/Şube** modülüyle Faz 1'i tamamlarım.
