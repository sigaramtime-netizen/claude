# D004 — F5-B Demirbaş & Amortisman Raporlama Cilası (v1.35.0 → v1.36.0)

- **Görev ID:** D004
- **Başlık:** F5-B — Demirbaş Amortisman Otomasyonu + Raporlama (plan önizleme, özet kartlar, API, grafik)
- **Durum:** BEKLEMEDE → KODLANIYOR (Coder bekleniyor)
- **Öncelik:** Yüksek (F5-A sonrası mali cilanın 2. adımı)
- **Önceki:** D003 ONAYLANDI — F5-A v1.35.0 Finansal Analiz 18/18 + 442/442

---

## 1. Amaç

Demirbaş modülü çalışıyor (kategori + kart + zimmet + aylık amortisman + GM fişi 770/257) ama **raporlama zayıf**:
- Amortisman planını geleceğe dönük göremiyorsun (kaç ay kaldı, ne zaman bitecek?)
- Kategori bazlı özet yok (Bilgisayar kaç TL maliyet, ne kadarı amorti oldu?)
- Grafik yok, mali müşavire verecek cetvel yok
- Toplu üretim durumu API'de yok (dashboard otomasyonu için)

Bu pakette **yeni tablo YOK** — mevcut 4 tablo (`demirbas_kategori`, `demirbas`, `demirbas_amortisman`, `demirbas_zimmet`) üzerine raporlama cilası eklenir.

## 2. Kapsam (5 alt modül)

| # | Alt Modül | Ne Olacak |
|---|-----------|-----------|
| 1 | **Amortisman Plan Önizleme** | Demirbaş detayında gelecek 12 ayın amortisman tablosu (donem, tutar, birikmiş, net) — üretilmemiş aylar tahmini, üretilmişler gerçek |
| 2 | **Kategori Bazlı Özet Kartları** | `/demirbas` listesi üstünde 4 kart: Toplam Maliyet, Toplam Birikmiş, Toplam Net, Aktif Adet + kategori tablosu (kategori → maliyet / birikmiş / net) |
| 3 | **Durum Rozetleri + Grafik** | Demurbaş listesinde amortisman durumu rozeti (🟢 Aktif / 🟡 Tamamlandı / 🔴 Durdu (Satıldı/Hurda)) + demirbaş detayında birikmiş amortisman çizgi grafik (inline SVG, F5-A gibi) |
| 4 | **API Özet Ucu** | `GET /api/demirbas/ozet` → JSON: `toplam_maliyet, toplam_birikmis, toplam_net, aktif_adet, kategori_ozet[], yaklasan_bitis[]` (3 ay içinde bitecekler) |
| 5 | **CSV Cetvel** | `GET /demirbas/amortisman/csv?yil=2026` → yıl bazlı amortisman cetveli CSV (demirbaş kod, ad, donem, tutar, birikmiş, net) — ZİPSİZ protokol için txt kanıtı destekler |

## 3. Veri Modeli

**YENİ TABLO YOK.** Mevcut tablolar kullanılır. Migration YOK.

- `demirbas_amortisman` → `UNIQUE(demirbas_id, donem)` zaten var, `sirket_id` zaten K1.
- Hesap: aylık = `(maliyet - hurda) / (omur_yil * 12)` — mevcut `_amortisman_uret` ile aynı formül.
- K1: tüm sorgular `sirket_id = db.sirket_id(req)` ile süzülür (zorunlu).
- Şube izolasyonu: `izole_sube(req)` korunur.

## 4. Teknik Uygulama

**A) Backend — `demirbas.py`**

- `demirbas_index` (`/demirbas`): üstte 4 özet kart + kategori özet tablosu (kategori ad, adet, maliyet toplam, birikmiş toplam, net toplam). Mevcut liste korunur, sadece üstüne eklenir.
- `demirbas_detay` (`/demirbas/<id>`): gelecek 12 ay plan tablosu ekle — `_amortisman_plan(demirbas)` helper (üretilmiş + tahmini karışık). Grafik için `birikmis` serisini hazırla.
- `GET /api/demirbas/ozet` (yeni, `roles=()` herkes giriş yapmış görebilir ama K1 filtreli):
  ```json
  {
    "toplam_maliyet": 89000,
    "toplam_birikmis": 12300,
    "toplam_net": 76700,
    "aktif_adet": 3,
    "kategori_ozet": [{"kategori":"Bilgisayar & Ekipman","adet":1,"maliyet":45000,"birikmis":...,"net":...}],
    "yaklasan_bitis": [{"kod":"BELGE-001","ad":"Dizüstü","bitis":"2027-08","kalan_ay":3}]
  }
  ```
  `yaklasan_bitis`: `alis_tarihi + omur_yil*12` - bugün = 0..3 ay kalanlar.
- `GET /demirbas/amortisman/csv?yil=YYYY` (yeni, `roles=("Admin","Muhasebe")`):
  - `Content-Type: text/csv`, `Content-Disposition: attachment; filename="amortisman-YYYY.csv"`
  - Sütunlar: `Demirbas Kod, Demirbas Ad, Kategori, Donem, Tutar, Birikmis, Net Deger, Durum`
  - Yıl filtresi: `donem LIKE 'YYYY-%'`; K1 ile süz.

**B) Frontend — `templates/demirbas/`**

- `index.html`: 4 KPI kart + kategori özet tablosu (mevcut tablo altına). Amortisman durumu rozeti: `Aktif` → yeşil, `Tamamlandı` (birikmiş >= taban) → sarı, `Satıldı/Hurda` → kırmızı.
- `detay.html`: alt kısımda "Amortisman Planı (gelecek 12 ay)" tablosu + inline SVG çizgi grafik (birikmiş). Mevcut amortisman tablosu korunur, plan tablosu ayrı.
- Grafik: F5-A'daki `_bar_svg` / `_hbar_svg` gibi inline SVG — **harici kütüphane YOK**, `static/js` ekleme.

**C) Grafik**

- Inline SVG line: x=ay, y=birikmiş. `width=640 height=230` gibi, F5-A ile aynı yardımcı deseni kullan (kopyala ama renk farklı: `#8b5cf6` mor).

**D) Yetkilendirme**

- Liste/detay/API: giriş yapmış herkes (mevcut `roles=()` korunur).
- CSV: `Admin, Muhasebe` sadece (test 15 gibi 403).

## 5. Yapmaman Gerekenler

- Yeni tablo ekleme (migration yok)
- `demirbas_amortisman` UNIQUE'sini bozma veya `sirket_id` K1'ini kaldırma
- Harici grafik kütüphanesi (Chart.js CDN dahil) ekleme
- Amortisman formülünü değiştirme (mevcut `taban/(omur*12)` korunur)
- Otomatik üretimi bozma (`_amortisman_uret` idempotent kalır, aynı donem 2 kez üretilmez)
- Zimmet geçmişini silme veya `demirbas_zimmet`'i değiştirme

## 6. Test Senaryosu — `test_f5b_demirbas.py` (YENİ, ZORUNLU)

`test_f5b_demirbas.py` oluştur, en az 18 kontrol, canlı sunucuya HTTP (F5-A gibi):

1.  `test_kategori_ozet`: `/demirbas` → Bilgisayar kategorisi maliyet 45000 görünüyor mu? (seed)
2.  `test_kpi_kartlar`: dashboard `/demirbas` → 4 kart (Toplam Maliyet, Birikmiş, Net, Aktif Adet) var mı?
3.  `test_api_ozet`: `/api/demirbas/ozet` → toplam_maliyet, kategori_ozet, yaklasan_bitis anahtarları var mı?
4.  `test_api_k1`: Şirket B'de A demirbaşı görünmez (API toplam_maliyet 0)
5.  `test_plan_tablo`: `/demirbas/1` detay → gelecek 12 ay plan tablosu var mı? (donem sütunu)
6.  `test_grafik`: detay HTML'de `<svg` var mı? (birikmiş çizgi)
7.  `test_csv`: `GET /demirbas/amortisman/csv?yil=2026` → 200, `Content-Type` csv, ilk satır başlık, en az 1 veri satırı
8.  `test_csv_k1`: Şirket B CSV'si A satırını içermez
9.  `test_durum_rozeti`: listede `b-ok / b-warn / b-danger` rozet sınıfları var mı?
10. `test_yeni_demirbas_ekle`: POST `/demirbas/ekle` → DB'de var mı? (MARK=F5BTEST)
11. `test_amortisman_uret_yeni`: yeni demirbaş için `POST /demirbas/amortisman-uret?donem=YYYY-MM` → `demirbas_amortisman` en az 1 satır arttı mı? GM fişi üretildi mi? (yevmiye `Demirbas` kaynaklı)
12. `test_cifte_uretim_engeli`: aynı dönem tekrar üret → satır sayısı artmadı (idempotent)
13. `test_zimmet_korundu`: zimmet POST hala çalışıyor mu? (Faz 5 korunum)
14. `test_sil_engeli_korundu`: amortismanı olan demirbaş `POST /sil` → engellendi (302 + flash değil, silinmedi)
15. `test_yetki_csv`: Depo rolü `/demirbas/amortisman/csv` → 403
16. `test_f1_korundu`: bütçe/amortisman mali etki dışında cikmadı mı? (cari_hareket artmadı)
17. `test_f5a_korundu`: `/finansal/butce` ve `/api/finansal/ozet` hala 200
18. `test_fk_kalinti`: `PRAGMA foreign_key_check` 0 + MARK kalıntısı yok (fatura/demirbas/amortisman/sirket)

Her test `sirket_id` izole, temizlik ile bitir, `MARK = "F5BTEST"` ile kalıntı bırakma. F5-A'daki gibi `temizle()` fonksiyonu.

## 7. Teslim — ZİPSİZ PROTOKOL (AYNI)

**7.1 Dosya Listesi:**
```bash
find . -type f | sort
```

**7.2 Değişen Dosyalar (cat ile dök):**
- `demirbas.py` (kategori özet + plan + /api/demirbas/ozet + /demirbas/amortisman/csv)
- `templates/demirbas/index.html` (4 KPI + kategori tablo + rozet)
- `templates/demirbas/detay.html` (plan tablosu + SVG)
- `test_f5b_demirbas.py` (TAMAMI)
- `config.py` (SURUM = "1.36.0")

**7.3 Test Kanıtı:**
```bash
python3 test_f5b_demirbas.py  # 18/18 olmalı
python3 test_f5a_finansal.py   # 18/18 hala yeşil?
python3 test_f4_edonusum.py    # 22/22 hala yeşil?
# Tam regresyon:
for f in test_*.py; do echo "== $f =="; python3 $f; done
# Toplam: 442 + 18 = 460 olmalı, 0 başarısız
```

**7.4 Ekran Kanıtı (opsiyonel, PNG isterse Playwright):**
- `/demirbas` liste: 4 KPI kart + kategori özet + rozetler
- `/demirbas/1` detay: plan tablosu + SVG grafik
- `/api/demirbas/ozet` JSON
- CSV indirme

**7.5 Sürüm:**
- `config.py`: `SURUM = "1.36.0"`, `SURUM_TARIHI = "2026-09-11"`
- `docs/F5B-demirbas-amortisman-ozet.md` oluştur (özet, F5A gibi)

## 8. Uygulama Sırası

1.  `demirbas.py` → kategori özet helper + `_amortisman_plan` + `/api/demirbas/ozet` + `/demirbas/amortisman/csv`
2.  `templates/demirbas/index.html` → 4 KPI + kategori tablo + rozet
3.  `templates/demirbas/detay.html` → plan tablosu + SVG
4.  Yetki kontrolü (CSV sadece Admin/Muhasebe)
5.  `test_f5b_demirbas.py` yaz, tek tek koş
6.  Tam regresyon 460/460
7.  TXT kanıtlarını topla, `kanitlar/v1.36.0/` altına koy, rapor yaz

**KURAL:** Tam regresyon yeşil olmadan teslim etme. Yeni tablo ekleme.

---

## 9. Başla

Şimdi `demirbas.py` ile başla (`_amortisman_plan` + kategori özet).
Her adımda ne yaptığını logla, TXT kanıtlarını hazırla.

GM onayı için `coder-raporlari/R004-...md` + `kanitlar/v1.36.0/` ile `git push` at.
