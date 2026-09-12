# Faz 5 — MALİ & ANALİTİK: TAMAMLANDI ✅

> Proje planının **Faz 5'i (Mali/Analitik)** eksiksiz tamamlandı ve **tam onay** alındı.
> Bu dosya, Faz 6'ya geçiş için Faz 5'in konsolide kapanış özetidir.
> **Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji

---

## Teslim edilen modüller (6/6)

| # | Modül | İçerik | Durum |
|---|---|---|---|
| 1 | **Genel Muhasebe (1.20)** | Hesap planı, yevmiye/büyük defter/mizan (+şube mizan), açılış/kapanış, **otomatik yevmiye (K26)**, çek/senet ara hesapları (101/121/103/321) | ✅ onaylı |
| 2 | **Kartoteks (1.17)** | Salt-okunur kronolojik hareket geçmişi (stok+cari+kasa/banka), koşu bakiye, **Excel/CSV + PDF dışa aktarma + barkod hızlı sorgu** | ✅ onaylı |
| 3 | **Transfer (1.18)** | Tek modülde konsolide görünüm: depo transfer + kasa↔banka + kasalar arası (yetersiz bakiye/atomiklik + çift bacaklı iptal) | ✅ onaylı |
| 4 | **Finansal Analiz (1.19)** | Türetilmiş grafikler (inline SVG), bütçe (`butce`), **COGS aylık**, dönemsel karşılaştırma, Tahmini Brüt Kâr | ✅ onaylı |
| 5 | **Beyanname (1.21)** | KDV (tahakkuk + nakit esaslı + devreden), **Geçici Vergi (COGS kümülatif + zarar kuralı)**, Muhtasar, vergi denetim raporu, CSV | ✅ onaylı |
| 6 | **Demirbaş (1.22)** | Sabit kıymet, **normal amortisman (770/257 GM fişi)**, zimmet takibi, kategori yönetimi | ✅ onaylı |

## Yeni veri modeli (43 → 51 tablo)

| Modül | Yeni tablolar |
|---|---|
| Genel Muhasebe | `hesap`, `yevmiye`, `yevmiye_kalem` |
| Finansal Analiz | `butce` |
| Demirbaş | `demirbas_kategori`, `demirbas`, `demirbas_amortisman`, `demirbas_zimmet` |

> Kartoteks, Transfer, Finansal Analiz grafikleri ve Beyanname **türetilmiş görünümlerdir** — yeni
> tablo açılmaz (mevcut tablolardan hesaplanır). K4/K6 "ikinci doğruluk kaynağı açma" kuralı korunur.

## Mimari kurallar (eklenen)

`docs/mimari-kurallar.md` → **K26** Genel Muhasebe otomatik yevmiye · **K27** Transfer konsolide
görünüm · **K28** Finansal Analiz türetilmiş analitikler · **K29** Beyanname salt-okunur vergi
raporları · **K30** Demirbaş sabit kıymet + normal amortisman + zimmet.

## Entegrasyon zinciri (şartname Bölüm 2'ye uyum)

**Teklif → Sipariş → İrsaliye → Fatura → e-Fatura/e-Arşiv → Cari/Kasa/Banka → Genel Muhasebe**
tek belge zinciri olarak çalışır; **Fatura / Kasa / Banka / Çek-Senet / Demirbaş amortismanı** her
zaman yevmiye karşılığı üretir (manuel çifte veri girişi yok — K26). Kartoteks salt-okunur tek
kaynak; dövizde güncel kur otomatik (TCMB), kur farkı izlenir.

## Doğrulanan kritik sonuçlar (canlı + DB)

| Alan | Sonuç |
|---|---|
| Mizan | **dengeli 833.375,26 ₺** — 831.133,60 (Beyanname turu) + 2.241,66 (4 Demirbaş amortisman fişi) ✅ |
| Yevmiye | **28 fiş** (24 mali + 4 Demirbaş amortisman) |
| Beyanname KDV | hesaplanan 27.375,60 − indirilecek 17.200,00 = **ödenecek 10.175,60**; nakit esaslı **18.940,00** |
| Geçici Vergi | matrah (COGS kümülatif) **−39.622,00 → ödenecek 0,00** (zarar 39.622,00; asla negatif vergi yok) |
| Finansal Analiz | GM net kâr (geçici) **134.636,34** (amortisman dahil) · Tahmini Brüt Kâr (COGS) −39.622,00 |
| Demirbaş | KPI maliyet 89.000,00 / birikmiş 2.241,66 / net 86.758,34; 4 amortisman satırı (770/257) |
| Rota / tablo | **155 kayıtlı rota** · **51 tablo** |

## Test hijyeni

- Her modülün onay paketi: `docs/faz5-{genel-muhasebe,kartoteks,transfer,finansal-analiz,beyanname,demirbas}-ozet.md`.
- HTTP testleri sırasında oluşturulan geçici kayıtlar (test kartı BELGE-NNN + amortismanı,
  "Test Kat" kategorisi, audit satırları) **temizlendi** — test kartının silinmesi amortismanını ve
  fişlerini de geri aldığı için mizana net etkisi sıfırdır.
- 30 sayfa regresyon testi: tamamı 200; rol testleri: depo yazamaz (403), muhasebe yazabilir.

## Sonraki adım

**Faz 6 — Cila:** rol bazlı yetkilendirme ince ayarı, bildirim sistemi, dashboard, mobil/tablet
uyumu, PDF şablonları. Bu fazda yeni modül yoktur; mevcut altyapı doğrulanır, eksik tetikleyiciler
(örn. ödenmemiş cari bakiyesi uyarısı) tamamlanır ve ince ayar yapılır.
