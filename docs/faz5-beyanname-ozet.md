# Beyanname (1.21) — Onay Paketi

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Faz 5 · modül 5/6**

## Tasarım kararı (K4/K6)

Salt-okunur **hazırlık raporları** — **GİB'e gönderim yapılmaz**, mali müşavire aktarılabilecek
çıktı üretilir (ekran + yazdırma + CSV). **Yeni veri modeli yoktur**; her şey mevcut tablolardan
türetilir:

| Rapor | Kaynak | Kural |
|---|---|---|
| KDV — tahakkuk (dönemsel) | `fatura` (+kalem) | Hesaplanan = Satış KDV×kur; İndirilecek = Alış KDV×kur; GM 391/191 ile çapraz doğrulama |
| KDV — devreden | aylar arası kümülatif | Ödenecek = Hesaplanan − İndirilecek − Devreden(önc.); negatif → devreden |
| KDV — nakit esaslı | `fatura` + `cari_hareket` | cari bazında tahsilat/ödeme oranı; **çek/senet (CekSenet) hariç** |
| Geçici Vergi | `fatura_kalem` + `stok_kart` (**COGS, K28 ile ortak**) | çeyrek dönem; yılbaşından kümülatif **tahmini brüt kâr** × %25 − önceki dönem mahsubu |
| Muhtasar | — (stopaj modeli yok) | boş durum + açıklama (bordro/stopaj veri kaynağı eklenince otomatik dolar) |
| Vergi denetim raporu | `fatura` + `yevmiye` | bir KDV kaleminin kaynak belgelerle kanıtı + GM uyum rozeti |
| Gelen belge işaretleme | `gelen_belge` | `donusum_fatura_id` boş olanlar → "müşavire ayrı liste" |

## Ekran listesi

| # | Ekran | Rota | Yetki |
|---|---|---|---|
| 1 | Beyanname özeti (KDV tahakkuk/nakit, Geçici Vergi, Muhtasar, gelen belge işareti) | `GET /beyanname` | tüm roller |
| 2 | Vergi denetim raporu (kaynak faturalar + GM çapraz doğrulama) | `GET /beyanname/denetim?ay=` | tüm roller |
| 3 | KDV kaynak listesi CSV dışa aktarımı | `GET /beyanname/denetim/csv?ay=` | tüm roller |

## Örnek test senaryosu (canlı HTTP + DB doğrulaması)

| # | Adım | Beklenen | Kanıt |
|---|---|---|---|
| 1 | `GET /beyanname` | 200; KDV/Geçici Vergi/Muhtasar/gelen belge bölümleri | ✅ |
| 2 | KDV tahakkuk | Hesaplanan 27.375,60 (3.599,80+4.399,80+400×48,44) / İndirilecek 17.200,00 | ✅ DB eşleşti |
| 3 | Ödenecek KDV | 27.375,60 − 17.200,00 = **10.175,60** | ✅ |
| 4 | Devreden | önceki aylar boş → Eylül devreden 0 | ✅ |
| 4b | Devreden (İndirilecek > Hesaplanan) | sentetik: Oca 100/160 → devr. 60 · Şub 200/50 → ödenecek 90, devr. 0 · Mar 10/120 → devr. 110 · Nis 30/40 → devr. 120 (kümülatif taşınır) | ✅ saf fonksiyon |
| 5 | KDV oran dağılımı | Satış %20 → matrah 136.878,00 / KDV 27.375,60 | ✅ |
| 6 | Geçici Vergi (revize) | matrah = kümülatif **tahmini brüt kâr −39.622,00** → vergi **0,00** (mahsup 0); eski GM neti (136.878 → 34.219,50) kullanılmaz | ✅ |
| 6b | Geçici Vergi — zarar kuralı | negatif matrahta vergiye tabi matrah **0'ın altına inmez**; ödenecek **0,00** (asla negatif vergi yok); zarar 39.622,00 yıl içi kümülatif matrahtan düşer + zarar devri notu | ✅ canlı + sentetik |
| 6c | Geçici Vergi — kâr+zarar karışık | Nisan +1.000 / Tem −300 / Eyl −400 → kümülatif +300; hesaplanan 75, mahsup 250 → ödenecek **0** (negatif ödenecek yok) | ✅ sentetik |
| 7 | Nakit esaslı KDV | tahsil 23.940,00 − ödenen 5.000,00 = 18.940,00 (çek/senet hariç) | ✅ |
| 8 | Vergi denetim raporu | kaynak faturalar + GM 391/191 "✅ uyumlu" | ✅ |
| 9 | CSV | UTF-8 BOM + `;` ayraçlı, başlık satırı | ✅ |
| 10 | Regresyon | 29 sayfa 200; GM mizan dengeli (831.133,60); 24 yevmiye | ✅ |

## Faz 4'ten taşınan 3 açık noktanın durumu

1. **Kur farkı faturası KDV fallback:** "kaynak fatura kalemlerinden KDV oranı; tek oranlı değilse
   %20" kuralı korunur. Beyanname'de **KDV oran dağılımı** ekranı bu fallback'in sonucunu görünür
   kılar; dövizli kur farkı faturasının KDV'si (BELGE-NNN: 400×48,44=19.376,00) %20 oranıyla
   hesaplanan KDV toplamına doğru yansır (hesaplanan KDV 27.375,60 içinde).
2. **`HZM-GLN-ESLESME` fallback kartı:** eşleştirilmemiş gelen belgeler (`donusum_fatura_id` boş)
   Beyanname'de **"müşavire ayrı liste"** rozetiyle ayrıca işaretlenir (seed: 2 belge —
   GLN-BELGE-NNN1, GLN-BELGE-NNN1).
3. **Sabit %20 KDV'li hizmet kartları:** kart çoğaltma yaklaşımı korunur; hizmet KDV'si oran
   dağılımında %20 satırında görünür. Farklı oranlı hizmetler için kart başına ayrı KDV oranı
   girilmesi (mevcut `stok_kart.kdv_orani`) yeterlidir — ayrı tablo gerekmez.

## Notlar / kapsam kararları

- **Muhtasar:** Şartnamede bordro/stopaj veri modeli yoktur; rapor şablonu hazır ama veri kaynağı
  boş. İstenirse (a) tevkifatlı alış faturası desteği veya (b) basit ücret/stopaj kartı eklenebilir —
  bu, Faz 6 öncesi kararınıza bağlı; şimdilik kapsam dışı tutulmuştur.
- **Geçici vergi oranı %25** (2026 kurumlar vergisi) sabit alınmıştır; mevzuat değişiminde tek
  sabitten güncellenir. **Matrah = tahmini brüt kâr (COGS dahil)** — Finansal Analiz'in "Tahmini
  Brüt Kâr" yöntemiyle yılbaşından dönem sonuna kümülatif; GM net kârı (SMM kapanışa kadar
  devretmediği için brüt satışa yakın) kullanılmaz. **Tahminidir** — kesin matrah dönem kapanışında
  netleşir (ekranda "tahmini" rozeti).
- **Zarar kuralı:** vergiye tabi matrah **0'ın altına inemez** (max(0, matrah)); asla negatif
  "vergi" rakamı üretilmez. Zarar, yıl içindeki kümülatif matrahtan otomatik düşer (yıl içi zarar
  mahsubu); yıllar arası zarar devri dönem kapanışında / mali müşavirce netleşir — ekranda zararlı
  dönem uyarısıyla gösterilir.
- **Nakit esaslı KDV basitleştirilmiştir:** cari bazında tahsilat/ödeme oranıyla ölçeklenir; çek/senet
  kaynaklı hareketler (henüz nakde dönüşmemiş) dahil edilmez. Kesin fatura-bazlı eşleştirme mali
  müşavir onayı gerektirir.

## Revizyon (kullanıcı geri bildirimi — 2026-09-08)

**Geçici Vergi matrahı düzeltildi.** İlk sürümde matrah GM kümülatif kârı (136.878,00) üzerinden
hesaplanıyordu; bu rakam 620/SMM dönem kapanışına kadar devretmediği için satılan malın maliyetini
içermiyordu (→ 34.219,50 fazla vergi). Artık matrah, **Finansal Analiz'in şartlı onayını kapatan
"Tahmini Brüt Kâr (COGS dahil)"** yöntemiyle hesaplanır (K28 ile ortak `_cogs_aylik` kaynağı):
yılbaşından dönem sonuna kümülatif (ciro − adet × güncel alış). Seed verisiyle 2026-Q3 matrahı
**−39.622,00** (veri artefaktı: USD demo faturası alış maliyetinin altında) ve ödenecek geçici vergi
**0,00** olur — iki modül artık aynı kaynaktan, tutarlı.

**Zarar kuralı eklendi (2026-09-08).** Negatif matrah senaryosu demo verisiyle canlı test edildi:
Eylül tahmini brüt kârı **−39.622,00** iken vergiye tabi matrah **0,00**'a kilitlenir, "Hesaplanan"
ve "Ödenecek" kartları **0,00** gösterir — asla negatif vergi üretilmez. Zarar (39.622,00) yıl içi
kümülatif matrahtan otomatik düşer; yıllar arası zarar devri dönem kapanışında netleşeceği ekranda
ayrıca belirtilir. Sentetik testler: (a) kâr+zarar karışık dönemde kümülatif doğru (hesaplanan 75 −
mahsup 250 → ödenecek 0, negatif yok) ve (b) tam zararlı dönemde taban 0.
