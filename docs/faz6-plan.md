# Faz 6 — CİLA (plan → TAMAMLANDI ✅)

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Önceki faz:** Faz 5 tam onay ✅

> **Durum:** Faz 6 tamamlandı ve test edildi — onay paketi `docs/faz6-ozet.md`.

## Kapsam (şartname madde 3.6 + kullanıcı)

> **Faz 6 — Cila:** Rol bazlı yetkilendirme, bildirim sistemi, dashboard, mobil/tablet uyumu, PDF şablonları.

Bu fazda **yeni modül yoktur**; önceki fazlarda kurulan çapraz altyapı doğrulanır, eksikler
kapatılır ve ince ayar yapılır.

## Mevcut durum (önceki fazlardan hazır olan)

| Alan | Durum |
|---|---|
| Rol bazlı yetkilendirme | ✅ Tam matris (okuma tüm roller, yazma role özel); HTTP testleriyle doğrulandı |
| Bildirim sistemi | ✅ `bildirimler` tablosu + `/bildirimler` merkezi + tetikleyiciler: not hatırlatma, teklif geçerlilik, çek/senet vade (≤3 gün), garanti (≤30 gün), stok kritik |
| Dashboard | ✅ Günlük/aylık satış, kasa, toplam alacak, vadesi geçen, açık servis, garanti yaklaşan/dolan, teklif/sipariş/irsaliye sayaçları, son uyarılar, en borçlu 5 cari |
| Responsive tema | ✅ Viewport + `@media (max-width: 900px)` + koyu tema |
| PDF/yazdır | ✅ Modül bazlı yazdır şablonları (fatura, irsaliye, çek/senet, kasa fişi, …) |
| Audit log | ✅ Tüm yazma uçlarında |

## Faz 6 iş paketleri (5)

1. **Bildirim ince ayarı**
   - Eksik tetikleyici: **ödenmemiş / vadesi geçen cari bakiyesi otomatik uyarısı** (şartname
     satır 23'te açıkça isteniyor; şu an dashboard KPI'ında görünür ama periyodik bildirim üretimi yok).
   - Bildirim merkezi: "tümünü okundu" + okunmamış sayaç rozeti + tip filtre.
   - (Opsiyonel) SMS/e-posta entegrasyon noktası — `entegrator` deseniyle mock.

2. **Dashboard ince ayarı** — vadesi yaklaşan tahsilat/ödemeler listesi, KPI düzeni, eksik özetler.

3. **Mobil/tablet uyumu** — küçük ekranda navigasyon, tablolarda yatay kaydırma, KPI kart grid'i;
   telefon + tablet doğrulaması.

4. **PDF şablonları** — tüm yazdır görünümlerinde tutarlı antet (firma bilgisi) + Türkçe kuruş
   formatı doğrulaması.

5. **Rol matrisi + K1 gözden geçirme** — merkezi yetki matrisi dokümanı; şube izolasyonu (K1)
   durumu netleştirilir.

## Veri modeli

Yeni tablo beklentisi **yok** (gerekirse bildirim için minimal ek — karar anında netleşir).

## Çıktı

Faz sonunda: veri modeli özeti + ekran listesi + örnek test senaryosu + onay paketi
(`docs/faz6-ozet.md`).
