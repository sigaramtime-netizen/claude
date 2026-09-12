# Faz 5 — Mali & Analitik (plan + taşınan açık noktalar)

**Tarih:** 2026-09-07 · **Firma:** Brn Teknoloji · **Faz 4 durumu:** TAM ONAY ✅

Kapsam (şartname): Genel Muhasebe (1.20), Beyanname (1.21), Demirbaş (1.22),
Finansal Analiz (1.19), Kartoteks (1.17), Transfer (1.18).

## Uygulama sırası (bağımlılık sırası)

| # | Modül | Bağımlılık | Not |
|---|---|---|---|
| 1 | Genel Muhasebe (1.20) | K2/K6 cari konvansiyonu | ✅ TAMAM — yevmiye/büyük defter/mizan + otomatik fiş (K26 revize) |
| 2 | Kartoteks (1.17) | stok_hareket/cari_hareket (hazır) | ✅ TAMAM — salt-okunur kronolojik görünüm + koşu bakiye |
| 3 | Transfer (1.18) | depo_transfer + kasa↔banka (kısmi hazır) | ✅ TAMAM — tek modül konsolide görünüm + kasalar arası eklendi |
| 4 | Finansal Analiz (1.19) | tüm hareket tabloları | ✅ TAMAM — türetilmiş grafikler + bütçe (`butce`) + dönemsel karşılaştırma |
| 5 | Beyanname (1.21) | Genel Muhasebe + KDV verisi | ✅ TAMAM — KDV (tahakkuk/nakit) + Geçici Vergi + Muhtasar boş + denetim raporu + CSV |
| 6 | Demirbaş (1.22) | Genel Muhasebe (fiş) + kullanici/sube | ✅ TAMAM — sabit kıymet + normal amortisman (770/257) + zimmet |

## Taşınan açık noktalar (Faz 4 sonu / kullanıcı)

1. **Kur farkı faturası KDV fallback:** kaynak fatura kalemlerinden tek oran yoksa **%20** fallback
   davranışının **karma KDV oranlı** faturalardaki doğruluğu — Genel Muhasebe/Beyanname'de netleştirilecek.
2. **`HZM-GLN-ESLESME` fallback kartı:** bu karta düşen (manuel eşleştirilmemiş) gelen belge kalemleri
   **Beyanname'de ayrıca işaretlenecek** (mali müşavire ayrı liste sunulabilir).
3. **Sabit %20 KDV'li hizmet kartları** (`HZM-SRV-ISCLK` gibi): farklı KDV oranlı hizmet türleri için
   kart çoğaltma yaklaşımı — Beyanname öncesi gözden geçirilecek.

## Faz 5 hedefi (faz sonu onay paketi)

Her modül için veri modeli özeti + ekran listesi + örnek test senaryosu; faz sonunda tek onay paketi.
