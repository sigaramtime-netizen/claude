# Finansal Analiz (1.19) — Onay Paketi

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Faz 5 · modül 4/6**

## Tasarım kararı (K4/K6)

Tüm analitikler **türetilmiştir (salt-okunur)** — ayrı veri girişi yoktur. Tek doğruluk kaynakları:

| Analiz | Kaynak | Kural |
|---|---|---|
| Satış (aylık matrah/KDV/adet) | `fatura` (tip=Satis, durum=Onaylandı) | TL karşılık: `ara_toplam × doviz_kur` |
| Kâr/Zarar (aylık) — **iki satır** | ① Genel Muhasebe `hesap` bakiyeleri ② `fatura_kalem` + güncel alış | ① GM net kâr (Gelir − Gider, geçici) ② **Tahmini brüt kâr (COGS dahil)** = ciro − (adet × alış) |
| Nakit akışı (aylık) | `kasa_hareket` + `banka_hareket` | **transfer ve açılış bakiyesi hariç** (kasa içi kaydırma — mükerrer sayım yok, K27 dersi) |
| En çok satan / en kârlı | `fatura_kalem` × `stok_kart` × `kategori` | kâr = (birim satış × kur − güncel alış) × adet (tahmini) |
| Tahsilat performansı | `cari_hareket` | bakiye = Σborç − Σalacak; oran = tahsilat / fatura borcu |
| Servis geliri | `servis_kayit` + `servis_parca` | işçilik + yedek parça |
| Bütçe | **`butce` (YENİ tablo)** | Odoo mantığı: yıl+ay+tip(Gelir/Gider)+hedef |

**Yeni veri modeli yalnızca `butce` tablosudur** (bütçe hedefi); analitiklerin kendisi kaynak
tablolardan canlı türetilir.

## Ekran listesi

| # | Ekran | Rota | Yetki |
|---|---|---|---|
| 1 | Özet: KPI + satış/kâr-zarar/nakit akışı grafikleri + dönemsel karşılaştırma | `GET /finansal` | tüm roller |
| 2 | Ürün/kategori: en çok satan + en kârlı + kategori payı | `GET /finansal/urunler` | tüm roller |
| 3 | Tahsilat performansı + servis gelir analizi | `GET /finansal/tahsilat` | tüm roller |
| 4 | Bütçe: hedef tanımla / sil + 12 aylık gerçekleşen karşılaştırması | `GET/POST /finansal/butce` | görüntüleme: tüm · yazma: Admin/Muhasebe |
| 5 | Bütçe hedefi silme | `POST /finansal/butce/{id}/sil` | Admin/Muhasebe |

Grafikler **satır içi SVG** ile çizilir (harici kütüphane/CDN yok → çevrimdışı önizlemede de çalışır).

## Örnek test senaryosu (canlı HTTP + DB doğrulaması)

| # | Adım | Beklenen | Kanıt |
|---|---|---|---|
| 1 | `GET /finansal` | 200; 3 SVG grafik + KPI | ✅ |
| 2 | Satış matrahı doğruluğu | Eylül = 136.878,00 (21.999 + 17.999 + 2.000×48,44) | ✅ DB eşleşti |
| 3 | Kâr-zarar (GM) | Eylül gelir 136.878,00 / gider 0 → net 136.878,00 | ✅ |
| 3b | **Tahmini brüt kâr (COGS dahil)** | Eylül ciro 136.878,00 − maliyet 176.500,00 = **−39.622,00** (iki satır birlikte, lejantlı) | ✅ |
| 4 | Nakit akışı (transfer/açılış hariç) | Ağustos giriş 54.400,00 / çıkış 55.700,00; Haziran (0,0) — açılışlar sayılmaz | ✅ |
| 5 | Dönemsel karşılaştırma | bu ay / geçen ay / geçen yıl + ▲▼ % | ✅ |
| 6 | En çok satan | TV-43-SAM-001 (11 adet, ciro 114.879,00) | ✅ |
| 7 | En kârlı (tahmini) | KLM-12000-VST-005 (4.999,00) | ✅ |
| 8 | Tahsilat oranı | cari bazlı oran rozetleri (≥80 yeşil, ≥50 sarı, <50 kırmızı) | ✅ |
| 9 | Servis geliri | işçilik + parça toplamı + durum/garanti özeti | ✅ |
| 10 | Bütçe ekle/sil (Admin) | 4→5→4 satır; flash + tabloya yansıma | ✅ |
| 11 | Yetki | depo: görüntüleme serbest, POST engelli (flash), silme 403 | ✅ |
| 12 | Regresyon | 34 sayfa 200; GM mizan dengeli (831.133,60); 24 yevmiye | ✅ |

## Notlar

- **Kâr-zarar iki satırla gösterilir** (işletme sahibinin "bu ay ne kazandım" sorusuna doğru
  cevap için): **(yeşil)** Muhasebe net kârı — GM Gelir − Gider; 620 (SMM) dönem sonu kapanışına
  kadar devretmediği için *geçici* etiketiyle. **(turuncu)** Tahmini brüt kâr — fatura kalemi
  satış fiyatının TL karşılığından ürün kartının güncel alış fiyatı düşülür ("En Kârlı Ürün" ile
  aynı yöntem; ekstra veri kaynağı yok).
- **Nakit akışı** işletme hareketleridir; Kasa↔Banka transferleri ve açılış bakiyeleri **dahil
  edilmez** (transfer çift sayımı dersinin nakit akışına uygulanması).
- **"En kârlı" ve "tahmini brüt kâr" tahminidir:** tarihsel maliyet yerine ürün kartının güncel
  alış fiyatı kullanılır; dövizli faturalarda birim fiyat fatura kuruyla TL'ye çevrilir (karma
  para birimi hatası önlendi).
- **Demo sınırı:** seed'de 3 onaylı satış faturası (biri USD kur farkı demosu) ve tek şube olduğu
  için "en çok satan" listesi kısa ve "geçen yıl" karşılaştırması boş (0) görünür — veri geldikçe
  otomatik dolar. USD demo faturası (200 USD/birim ≈ 9.688 TL) alış maliyetinin (14.500 TL)
  altında olduğundan Eylül tahmini brüt kârı **−39.622,00** görünür — veri artefaktıdır, hesap
  hatası değildir.
- Bütçe seed'i (örnek): 2026-08/09 Gelir+Gider hedefleri; Eylül gelir gerçekleşmesi
  136.878,00 / 200.000,00 hedef = %68,4.
- **Çapraz kullanım (Beyanname 1.21):** Buradaki **"Tahmini Brüt Kâr (COGS dahil)"** satırı aynı
  zamanda Beyanname'nin **Geçici Vergi matrahıdır** (K29 — ortak `_cogs_aylik` kaynağı). GM net
  kârı SMM'siz olduğundan geçici vergi matrahı olarak kullanılmaz; iki modül tek kaynaktan tutarlı
  çalışır.
