# Faz 2 · Döviz Takip Modülü — Özet (onay için)

> Modül: **Döviz Takip** — Faz 2 Satış Döngüsü'nün **6. ve son halkası**
> (Teklif → Sipariş → İrsaliye → Fatura → Çek/Senet → **Döviz Takip**).
> Bu modülle Faz 2 kapanıyor. Kullanıcının Çek/Senet şartlı onayında sorduğu
> "çek/senet döviz cinsinden olabilir mi?" sorusu da burada **evet** olarak netleştirildi:
> `cek_senet`'e `para_birimi` + `doviz_kur` eklendi (K18).

---

## 1. Veri modeli

**`doviz_kur`** (yeni tablo)

| Alan | Açıklama |
|---|---|
| `para_birimi` | `USD` / `EUR` / `GBP` (TRY tabloda tutulmaz; kur = 1 varsayılır) |
| `kur` | 1 birim döviz = ? TL |
| `tarih` | Kurun geçerli olduğu tarih |
| `kaynak` | `Manuel` / `TCMB` |

**Eklenen alanlar (K18 migrasyonu)** — `para_birimi` (varsayılan `TRY`) + `doviz_kur`:

| Tablo | Durum |
|---|---|
| `fatura`, `teklif`, `siparis`, `cari_hareket` | Faz 2 kurulumunda zaten vardı — form/akış bu revizyonda bağlandı |
| `cek_senet` | **YENİ** — kullanıcının notu gereği eklendi (USD/EUR çek-senet) |
| `kasa_hareket`, `banka_hareket` | **YENİ** — döviz nakit/havale tahsilat-ödeme |

**Yardımcı:** `db.guncel_kur(conn, para_birimi)` — o güne kadarki son kur; TRY → 1.0.

---

## 2. Rotalar (6 yeni — toplam 86 → 92)

| Rota | Amaç | Yetki |
|---|---|---|
| `GET /doviz` | Kur yönetimi + çoklu para birimi raporu + kur geçmişi | herkes |
| `POST /doviz/kur` | Manuel kur gir/güncelle (aynı gün+para birimi → günceller) | Admin/Muhasebe |
| `POST /doviz/kur/{id}/sil` | Kur kaydı sil | Admin/Muhasebe |
| `POST /doviz/tcmb` | **TCMB entegrasyon noktası** — `today.xml` çekip USD/EUR/GBP günceller | Admin/Muhasebe |
| `GET /doviz/kur-farki` | Döviz faturaları + realize kur farkı tablosu | herkes |
| `POST /doviz/kur-farki/{id}/fatura` | **Kur farkı faturası kes** (TL, cariye işlenir) | Admin/Muhasebe |

---

## 3. Ekranlar (2 yeni şablon)

1. `doviz/kur.html` — güncel kurlar, kur girişi + TCMB butonu, çoklu para birimi raporu, kur geçmişi.
2. `doviz/kur_farki.html` — döviz faturaları; fatura kuru, toplanan/kalan döviz, realize kur farkı,
   "Kur Farkı Faturası Kes" aksiyonu.

Form eklemeleri: `fatura/form.html`, `cek_senet/form.html`, `kasa/hareket_form.html`,
`banka/hareket_form.html` → **Para Birimi** seçimi + **Kur (1 birim = TL)** alanı (döviz seçilince
kur otomatik doldurulur).

---

## 4. Davranış / kurallar (K18)

- **TL temel:** tüm cari tutarlar TL karşılığı saklanır (`borc/alacak`); `para_birimi`/`doviz_kur`
  yalnızca izleme. Döviz belgesinden üretilen cari hareket = **tutar × kur** TL.
- **TCMB:** gerçek TCMB servisi denendi ve **çalışıyor** (testte USD 48,4336 / EUR 56,2864 /
  GBP 65,659 çekildi). Ağ yoksa zarif uyarı → manuel giriş.
- **Kur farkı (KDV'li):** döviz faturası farklı kurdan kapatılırsa realize fark =
  Σ toplanan döviz × (tahsilat kuru − fatura kuru). Kur farkı faturası **KDV'ye tabidir**:
  matrah = |fark|, KDV oranı kaynak faturanın kalemlerinden (tek oranlı değilse %20),
  genel = matrah + KDV; cari hareket KDV dahil genel üzerinden işlenir.
- **Kur farkı kesim kapısı:** yalnız fatura **tamamen kapatıldığında** (kalan = 0) kesilebilir;
  her kaynak fatura için **tek** kur farkı faturası (mükerrer engel). Parçalı tahsilatların farkı
  kümülatif hesaplanır, tek faturada kapatılır.
- **Çek/Senet döviz:** USD/EUR çek-senet girilebilir; tahsil/öde → cariye tutar × kur TL işlenir.
- **Kasa/Banka döviz:** yalnız cari bağlantılı işlemlerde (Nakit Girişi/Çıkışı, Havale/EFT) anlamlı;
  transfer/açılış TRY kalır. **Karışık para birimi bakiyesi ayrı ayrı netlenip gösterilir**
  ("10.000 TL + 500 USD" + TL karşılık); yetersiz bakiye kontrolü ilgili para biriminde yapılır.

---

## 5. Örnek test senaryoları (hepsi bu turda çalıştırıldı ✅)

1. **Kur yönetimi** — `/doviz` 200; USD/EUR/GBP seed kurları listelendi. ✅
2. **Manuel kur girişi** — EUR 56,31 girildi; aynı gün+para birimi için güncelleme yapıldı (mükerrer satır yok). ✅
3. **TCMB güncelleme** — gerçek TCMB servisinden USD 48,4336 / EUR 56,2864 / GBP 65,659 çekildi, `kaynak='TCMB'`. ✅
4. **Döviz fatura seed** — BELGE-NNN (USD 2.400, kur 48,44) → cari borç **116.256,00 TL** (2400×48,44), para_birimi=USD. ✅
5. **USD tahsilat seed** — banka USD 2.400 @ 48,60 → cari alacak **116.640,00 TL**; net = kur farkı 384,00 TL. ✅
6. **Kur farkı ekranı** — BELGE-NNN için realize fark **384,00 TL** doğru hesaplandı. ✅
7. **Kur farkı faturası (KDV'li)** — tek tıkla BELGE-NNN oluştu: **matrah 384,00 TL + KDV 76,80 TL
   (%20, kaynak fatura kaleminden) = genel 460,80 TL**; cari borç **460,80 TL** (KDV dahil). ✅
8. **Mükerrer engel** — aynı faturadan ikinci kur farkı faturası engellendi (adayet 1→1). ✅
9. **USD çek/senet (kullanıcı notu)** — TEST-USD-001 (500 USD @ 48,44) oluşturuldu; Tahsil →
   cari alacak **24.220,00 TL** (500×48,44); İptal → net sıfır. ✅
10. **Formlar** — fatura/çek-senet/kasa/banka formlarında Para Birimi + Kur alanları görünür. ✅
11. **Regresyon** — 15 ana sayfa (dashboard, cari, stok, kasa, banka, teklif…doviz) 200 döndü. ✅
12. **Temiz seed** — test sonrası: doviz_kur=3 (TCMB), fatura=3 (BELGE-NNN USD), cek_senet=6
    (CEK-004 USD), cari_hareket=19, banka_hareket=7 (USD tahsilat). ✅
13. **Karışık para birimi — Kasa** — Kasa'ya USD 500 giriş + USD 400 çıkış → kartta
    **"30.500,00 ₺ · 100,00 USD"** ayrı ayrı + TL karşılık **35.343,36 ₺** (tek sayıya toplanmadı). ✅
14. **Karışık para birimi — Banka** — Ziraat hesabında **"120.000,00 ₺ · 2.400,00 USD · 200,00 EUR"**
    ayrı ayrı + TL karşılık **247.897,28 ₺**; Toplam Banka KPI "TL karşılığı" etiketli. ✅
15. **Para birimi bazında yetersiz bakiye kontrolü** — USD bakiyesi 500 iken USD 600 çıkış
    **reddedildi** (kayıt oluşmadı), USD 400 çıkış izin verildi. ✅
16. **Kur farkı kesim kapısı** — kısmi tahsilatlı faturada (kalan 600 USD) "Tam kapanınca kesilir"
    rozeti + kesim engellendi. ✅
17. **Regresyon** — 16 ana sayfa (dashboard, cari, stok, kasa, banka, teklif…doviz + kasa/rapor)
    200 döndü; dashboard kasa KPI TL karşılık (36.700,00 ₺). ✅

---

## 6. Sonraki adım

Faz 2 tamamlandı (3 şartlı-onay düzeltmesi dahil) → **Faz 3 — Servis & Garanti** (Servis Takip,
Seri No-Garanti, Notlar).
