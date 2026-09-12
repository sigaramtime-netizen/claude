# F3 — Ortak Arama / Type-ahead Seçici (v1.33.0)

**GM emri:** `uploads/F3-EMIR-PAKETI-arena-ai-icindir.txt` · **Durum:** ✅ TAMAMLANDI (30/30 test, regresyon yeşil)

---

## 1. Ne yapıldı

Bütün uzun `<select>` listeleri öldürüldü. Tek bir `/api/ara` endpoint'i + tek bir
`static/js/typeahead.js` bileşeni. 14 noktada aynı widget: yazarak anında filtreleme
(kod + ad + barkod), klavye ile seçim (↑/↓/Enter/Escape), seçince hidden input'a KOD,
ekranda AD görünür.

## 2. Mimari (TEK KAYNAK prensibi)

```
GET /api/ara?tip=stok|cari&q=...&cari_tip=Alis|Satis
   ├─ tip=stok  → kod/ad/barkod (+ varyant)  [api.py: _stok_ara()]
   ├─ tip=cari  → kod/unvan (+ cari_tip filtresi)  [api.py: _cari_ara()]
   ├─ q boş     → ilk 20 aktif kayıt
   ├─ LIMIT 20  → asla 20'den fazla satır
   └─ K1        → her sorgu WHERE sirket_id=? ile süzülür
```

- Eski `/api/stok/ara` ve `/api/cari/ara` **ayrı sorgu yazmaz**; aynı `_stok_ara()` /
  `_cari_ara()` fonksiyonlarını çağıran ince sarmalayıcılardır (test_izolasyon_e2e
  bu uçları kullandığı için kaldırılmadı).
- Frontend: `static/js/typeahead.js` → `.typeahead` div'ini input + dropdown + hidden
  input'a çevirir; seçimde `document`'a `ta:select` olayı fırlatır (form-satir.js cari
  iskonto senkronu bunu dinler). `base.html`'de global yüklenir (tüm girişli sayfalar).

## 3. Kapsam — 14 nokta (GM tablosu)

| # | Modül | Alan | Durum |
|---|-------|------|-------|
| 1-8 | Teklif/Sipariş/İrsaliye/Fatura | cari başlık + stok satırı | cari → `typeahead.js` widget; stok satırı → `form-satir.js` (zaten typeahead, artık `/api/ara` çağırır) |
| 9 | POS | barkod/ürün arama | `/api/ara` (ad+kod+barkod) + müşteri → widget |
| 10 | Satın Alma Talebi | stok satırı + tedarikçi | stok `/api/ara`; tedarikçi → widget (Alis) |
| 11 | Satın Alma Teklifi | stok + tedarikçi | stok `/api/ara`; tedarikçi → widget (Alis) |
| 12 | Servis Fişi | müşteri + parça (stok) | ikisi de widget |
| 13 | Bakım Sözleşmesi | müşteri | widget (düzenlemede kilitli gösterim) |
| 14 | CRM Aktivite | müşteri | widget (allow-empty) |

## 4. Yapılmaması gerekenler — uyum

- ❌ Ayrı API yazılmadı → tek `/api/ara`.
- ❌ Ayrı JS kopyalanmadı → tek `typeahead.js`.
- ❌ DB şeması değişmedi (yeni tablo/kolon YOK).
- ❌ F1/F2 mantığına dokunulmadı (KDV/mali etki aynen).
- ❌ `<select>` tamamen silinip JS'siz çalışmaz hale getirilmedi → hidden input hep form ile POST edilir; JS kapalıysa edit modunda sunucudan gelen değer korunur; Enter'da elle yazılan kod ile tam eşleşme çözülür (fallback).

## 5. Test

- `test_f3_arama.py` → **30/30** (GM "en az 18 kontrol" istedi; 30 kontrol yapıldı).
  GM'in 18 senaryosu gerçek seed verisine uyarlandı (seed'de ST00001/CR0001/"Yılmaz" yok;
  karşılıkları `BUZ-510-VST-003` / `BAT-001` / "Batman Çarşı Elektronik").
- Kapsanan senaryolar: kod/ad/barkod/boş/yok arama, K1 izolasyon (A stoğu B'de görünmez),
  limit 20 (30 stoğa rağmen), 5 belge tipinde hidden-input POST, POS adla arama + satış,
  statik dosya 200, 11 şablonda widget varlığı, tek endpoint (eski uç çağrısı yok), FK/yetim/kalıntı.

## 6. Değişen dosyalar

- `api.py` — `/api/ara` + `_stok_ara()`/`_cari_ara()` + sarmalayıcılar.
- `static/js/typeahead.js` — **YENİ** ortak bileşen.
- `static/style.css` — `.ta-wrap/.ta-clear` stilleri.
- `templates/base.html` — `typeahead.js` global yükleme.
- `static/js/form-satir.js` — stok fetch `/api/ara`; cari blok → `ta:select` iskonto senkronu.
- `templates/{fatura,irsaliye,teklif,siparis}/form.html` — cari başlık → widget.
- `templates/pos/satis.html` — ürün fetch `/api/ara` + müşteri widget.
- `templates/satin_alma/{form,teklif_form}.html` — tedarikçi widget + stok fetch `/api/ara`.
- `templates/servis/{form,detay}.html`, `templates/bakim/form.html`, `templates/crm/form.html` — cari/parça widget.
- `config.py` — SURUM **1.33.0**; `CHANGELOG.md`; `docs/F3-arama-ozet.md`; `test_f3_arama.py`.
