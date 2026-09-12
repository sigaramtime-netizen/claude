# D005 — F5-C Beyanname Hazırlık Raporları Cilası (v1.36.0 → v1.37.0)

- **Görev ID:** D005
- **Başlık:** F5-C — Beyanname (KDV devreden + Geçici Vergi + Nakit esaslı + Denetim izi) Cila
- **Durum:** BEKLEMEDE → KODLANIYOR (Coder bekleniyor)
- **Öncelik:** Yüksek (F5 serisinin son halkası — mali müşavire gidecek rapor)
- **Önceki:** D004 ONAYLANDI — F5-B v1.36.0 Demirbaş 18/18 + 460/460

---

## 1. Amaç

Beyanname modülü çalışıyor (`beyanname.py` — KDV tahakkuk/nakit, Geçici Vergi, Muhtasar, Gelen eşleşmemiş, denetim + CSV) ama **cilasız**:
- Dashboard kartları yok (ödencek KDV, devreden, geçici vergi matrahı tek bakışta görünmüyor)
- KDV oran dağılımı sadece tablo — grafik yok
- Mali müşavire verilecek çıktı sadece denetim CSV — KDV devreden cetvel CSV yok
- API yok (finansal/demirbaş gibi `/api/beyanname/ozet` ile entegrasyon yok)

Bu pakette **yeni tablo YOK** — mevcut `fatura`, `yevmiye`, `gelen_belge`, `cari_hareket` üzerinden raporlama cilası eklenir. GİB'e gönderim YOK (hazırlık raporu).

## 2. Kapsam (5 alt modül)

| # | Alt Modül | Ne Olacak |
|---|-----------|-----------|
| 1 | **Özet Kartlar (beyanname üstü)** | 4 kart: Bu Ay Hesaplanan KDV, İndirilecek KDV, Ödenecek (devreden düşülmüş), Devreden Sonraki Ay + Geçici Vergi matrah/ödenecek rozeti |
| 2 | **KDV Oran Dağılımı Grafik** | Satış/alış KDV oran bazında inline SVG bar (F5-A/F5-B gibi harici YOK) — `%1/%10/%20` matrah + KDV |
| 3 | **API Özet Ucu** | `GET /api/beyanname/ozet?ay=YYYY-MM` → JSON: `hesaplanan, indirilecek, odenecek, devreden_sonraki, devreden_tablo[12], gecici_vergi{matrah, odenecek}, nakit{odenecek}, eslesmemis_adet` |
| 4 | **KDV Devreden CSV** | `GET /beyanname/kdv/csv?yil=YYYY` → 12 aylık devredenli KDV cetveli CSV (ay, hesaplanan, indirilecek, devreden_on, odenecek, devreden_son) |
| 5 | **Gelen Eşleşmemiş Vurgu + Denetim Koruması** | `/beyanname` üstünde eşleşmemiş gelen belge uyarı kartı (varsa kırmızı badge + liste linki) + `/beyanname/denetim` zaten var — korunur, ek test ile doğrulanır |

## 3. Veri Modeli

**YENİ TABLO YOK.** Mevcut kaynaklar salt-okunur:

- KDV tahakkuk: `fatura` (durum=Onaylandı, tip, ara_toplam, kdv_toplam, doviz_kur) — F2 KDV dahil/hariç zaten net tutulur.
- GM çapraz: `yevmiye` + `hesap` (391/191) — beyanname zaten çaprazlıyor, korunur.
- Geçici Vergi: `finansal._cogs_aylik` (tahmini brüt kâr COGS) — F5-A ile ortak kaynak, oran 25%.
- Nakit esaslı: `fatura` (genel) vs `cari_hareket` (Tahsilat/Ödeme, CekSenet hariç).
- Gelen eşleşmemiş: `gelen_belge WHERE donusum_fatura_id IS NULL`.

Migration YOK. K1: tüm sorgular `sirket_id = db.sirket_id(req)` ile süzülür.

## 4. Teknik Uygulama

**A) Backend — `beyanname.py`**

- `beyanname_index` (`/beyanname`): üstte 4 özet kart + `devreden_tablo` zaten var — kartlara `odenecek` (aktif ay) + `devreden_sonraki` (12. ay sonu) + `gecici_vergi.odenecek` göster. Mevcut tablo korunur, sadece üstüne kart eklenir.
- `GET /api/beyanname/ozet?ay=YYYY-MM` (yeni, `roles=()`):
  ```json
  {
    "ay": "2026-09",
    "hesaplanan": 12345.0,
    "indirilecek": 6789.0,
    "odenecek": 5556.0,
    "devreden_sonraki": 0.0,
    "devreden_tablo": [{"ay":1,"hesaplanan":..., "odenecek":...}, ...],
    "gecici_vergi": {"ceyrek":"3. Dönem","matrah":..., "odenecek":...},
    "nakit": {"odenecek": ...},
    "eslesmemis_adet": 2
  }
  ```
  `odenecek` = `max(0, hesaplanan - indirilecek - devreden_on)` ( _devreden_satirlar ile aynı).
- `GET /beyanname/kdv/csv?yil=YYYY` (yeni, `roles=("Admin","Muhasebe")`):
  - `Content-Type: text/csv; charset=utf-8`, `Content-Disposition: attachment; filename="kdv-devreden-YYYY.csv"`
  - Başlık: `Ay, Hesaplanan KDV, Indirilecek KDV, Devreden (Onceki), Odenecek, Devreden (Sonraki)`
  - Veri: `_devreden_satirlar(kdv, yil, 0)` 12 satır (ay 1..12). `;` ayraç, `,` ondalık değil `.` (mevcut denetim CSV gibi).
- Gelen eşleşmemiş: `eslesmemis_adet = len(_gelen_eslesmemis(conn, sid))` → template'e aktar, varsa uyarı.

**B) Frontend — `templates/beyanname/`**

- `index.html`: 4 KPI kart (hesaplanan/indirilecek/ödenecek/devreden) + geçici vergi matrah kartı (yanında). KDV oran dağılımı için 2 bar grafik (satış + alış) inline SVG (F5-A/B deseni, renk: satış `#4f8cff`, alış `#f0a34a`). Eşleşmemiş uyarı kartı: `if eslesmemis_adet>0` → kırmızı badge.
- `denetim.html` korunur — dokunma (sadece test ile doğrulanır).
- Grafik: inline SVG `_bar_svg` kopyası (beyanname.py içinde helper) — **harici kütüphane YOK**.

**C) Yetkilendirme**

- `/beyanname`, `/beyanname/denetim`, `/api/beyanname/ozet`: `roles=()` (giriş yapmış herkes — mevcut korunur).
- `/beyanname/kdv/csv`, `/beyanname/denetim/csv`: `Admin, Muhasebe` sadece (Depo 403).

## 5. Yapmaman Gerekenler

- Yeni tablo / migration ekleme
- GİB'e gönderim kodu ekleme (hazırlık raporu — sadece çıktı)
- KDV formülünü değiştirme (`_devreden_satirlar`, `_gecici_vergi`, `_nakit_kdv` korunur)
- Harici grafik kütüphanesi (Chart.js CDN dahil) ekleme
- `finansal._cogs_aylik` COGS yöntemini değiştirme (Geçici Vergi matrahı ile ortak)
- K1 `sirket_id` filtresini kaldırma

## 6. Test Senaryosu — `test_f5c_beyanname.py` (YENİ, ZORUNLU)

`test_f5c_beyanname.py` oluştur, en az 18 kontrol, canlı sunucuya HTTP:

1.  `test_kpi_kartlar`: `GET /beyanname?ay=2026-09` → 4 kart etiketi var mı? (Hesaplanan, İndirilecek, Ödenecek, Devreden)
2.  `test_grafik`: HTML'de `<svg` var mı? (oran dağılımı bar)
3.  `test_api_ozet`: `GET /api/beyanname/ozet?ay=2026-09` → hesaplanan, indirilecek, odenecek, devreden_tablo[12] var mı?
4.  `test_api_k1`: Şirket B'de A verisi görünmez (hesaplanan 0)
5.  `test_devreden_dogruluk`: API `odenecek` = devreden tablodaki aktif ay `odenecek` ile eş mi?
6.  `test_gecici_vergi`: API `gecici_vergi.ceyrek` ve `odenecek` var mı? (3. dönem için)
7.  `test_nakit`: API `nakit.odenecek` var mı?
8.  `test_eslesmemis_kart`: `/beyanname` → eşleşmemiş adet rozeti var mı? (en az 0, HTML'de `eşleşmemiş` kelimesi)
9.  `test_kdv_csv`: `GET /beyanname/kdv/csv?yil=2026` → 200, `text/csv`, başlık satırı `Ay;Hesaplanan` içeriyor mu?, en az 12 veri satırı
10. `test_kdv_csv_k1`: Şirket B CSV'si A hesaplananını içermez (farklı)
11. `test_denetim_korundu`: `GET /beyanname/denetim?ay=2026-09` → 200
12. `test_denetim_csv_korundu`: `GET /beyanname/denetim/csv?ay=2026-09` → 200, `text/csv`, `Tip;Belge No` başlığı
13. `test_yeni_fatura_kdv_yansidi`: POST yeni satış faturası (KDV %20, 1000 TL) → API `hesaplanan` en az 200 arttı mı? (MARK=F5CTEST, sonra sil)
14. `test_fatura_sil_kdv_dustu`: faturayı sil → hesaplanan geri düştü mü?
15. `test_yetki_csv`: Depo rolü `/beyanname/kdv/csv?yil=2026` → 403, `/beyanname/denetim/csv` → 403
16. `test_f1_korundu`: beyanname sorguları mali tabloya dokunmaz (cari_hareket/yevmiye artmadı)
17. `test_f5a_f5b_korundu`: `/finansal/butce`, `/api/demirbas/ozet` hala 200
18. `test_fk_kalinti`: `PRAGMA foreign_key_check` 0 + MARK kalıntısı yok (fatura/gelen/sirket)

Her test K1 izole, temizlik ile bitir, `MARK = "F5CTEST"` ile kalıntı bırakma. `temizle()` örneği F5-B'deki gibi.

## 7. Teslim — ZİPSİZ PROTOKOL (AYNI)

**7.1 Dosya Listesi:**
```bash
find . -type f | sort
```

**7.2 Değişen Dosyalar (cat ile dök):**
- `beyanname.py` (kart verisi + /api/beyanname/ozet + /beyanname/kdv/csv + SVG helper)
- `templates/beyanname/index.html` (4 KPI + 2 grafik + eşleşmemiş uyarı)
- `test_f5c_beyanname.py` (TAMAMI)
- `config.py` (SURUM = "1.37.0")

**7.3 Test Kanıtı:**
```bash
python3 test_f5c_beyanname.py  # 18/18 olmalı
python3 test_f5b_demirbas.py    # 18/18 hala yeşil?
python3 test_f5a_finansal.py    # 18/18 hala yeşil?
python3 test_f4_edonusum.py     # 22/22 hala yeşil?
# Tam regresyon:
for f in test_*.py; do echo "== $f =="; python3 $f; done
# Toplam: 460 + 18 = 478 olmalı, 0 başarısız
```

**7.4 Ekran Kanıtı (opsiyonel):**
- `/beyanname?ay=2026-09` → 4 kart + 2 bar grafik + eşleşmemiş uyarı
- `/api/beyanname/ozet?ay=2026-09` JSON
- CSV indirme (KDV devreden)

**7.5 Sürüm:**
- `config.py`: `SURUM = "1.37.0"`, `SURUM_TARIHI = "2026-09-11"`
- `docs/F5C-beyanname-hazirlik-ozet.md` oluştur (özet, F5A/B gibi)

## 8. Uygulama Sırası

1.  `beyanname.py` → kart verisi + `_bar_svg` helper + `/api/beyanname/ozet` + `/beyanname/kdv/csv`
2.  `templates/beyanname/index.html` → 4 KPI + 2 grafik + eşleşmemiş kart
3.  Yetki kontrolü (CSV sadece Admin/Muhasebe)
4.  `test_f5c_beyanname.py` yaz, tek tek koş
5.  Tam regresyon 478/478
6.  TXT kanıtlarını topla, `kanitlar/v1.37.0/` altına koy, rapor yaz

**KURAL:** Tam regresyon yeşil olmadan teslim etme. Yeni tablo ekleme. GİB'e gönderim YOK.

---

## 9. Başla

Şimdi `beyanname.py` ile başla (`_bar_svg` + API + CSV).
Her adımda ne yaptığını logla, TXT kanıtlarını hazırla.

GM onayı için `coder-raporlari/R005-...md` + `kanitlar/v1.37.0/` ile `git push` at.
