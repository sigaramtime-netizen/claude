# Satır Ekleme Akışı — Satır İçi Yazma + Canlı Arama — Uygulama Özeti

> Tarih: 2026-09-08 · Kapsam: Fatura + İrsaliye formları · Durum: **Tamamlandı, uçtan uca test edildi**
> Referans desen: WolvoxCloud / Akınsoft kalem girişi. Kural: `mimari-kurallar.md` **K34**.

---

## 1. Ne istendi?

Eski "önce stok seç, sonra satıra ekle" akışı yerine, kullanıcının **kalemler tablosuna
doğrudan yazarak** satır doldurduğu modern giriş:

1. Kalemler tablosunda sade **`+`** butonu; her tıklama **boş satır** açar, **sınır yok**.
2. Boş satırın içine tıklanıp **yazılır**:
   - **Ürün adı hücresi:** stok kartlarında **canlı arama/autocomplete**; *Stok Adı* ve
     *Stok Kodu* aranabilir.
   - Yazılan metin **hiçbir stokla eşleşmiyorsa** satır otomatik **manuel** olur (`stok_id NULL`).
   - Listeden stok **seçilirse** stoklu satır olur; barkod/KDV/fiyat otomatik gelir.
3. **Cari** alanı da yazarak aranabilir (sabit dropdown yok).
4. **Stoklu / manuel ayrımı kullanıcıya sorulmaz** — sistem metin eşleşmesine göre karar verir.

Önceki kararlar aynen korundu: manuel satır stoğa dokunmaz (K33), K9 iskonto önceliği manuelde
yok, Alış manuel **770**, Transfer'de manuel **yasak**.

## 2. Form sözleşmesi

`<form>` şu veri özniteliklerini taşır; ortak motor `static/js/form-satir.js` bunları okur:

| Öğe / Öznitelik | Görev |
|---|---|
| `data-belge` | `fatura` veya `irsaliye` |
| `data-tip` | `Satis` / `Alis` / `Transfer` |
| `data-manuel-yasak` | `1` ise (Transfer) manuel satır yasak + cari gizli |
| `#cari-ara`, `#cari-id`, `#cari-list` | Cari canlı arama girdisi, gizli id, öneri listesi |
| `#kalemler-body` | Satırların `tr.satir` konteyneri |
| `#satirlar-data` | Gönderilecek satırların JSON'u (hidden) |
| `#satir-ekle`, `#satir-bos` | `+` butonu ve boş satır şablonu |
| `#t-ara`, `#t-isk`, `#t-kdv`, `#t-genel` | Ara toplam / iskonto / KDV / genel toplam |

Satır alanları: `k_stok_id` (boş = manuel), `k_varyant_id`, `k_manuel_ad`, `k_miktar`,
`k_birim_fiyat`, `k_isk`, `k_kdv`.

## 3. Karar akışı (stoklu ↔ manuel)

```
yazım (input)  →  satır "çözülmemiş" olur  →  170ms debounce  →  /api/stok/ara?q=
   ├─ kullanıcı listeden SEÇERSE (tık / Enter)      → stoklu: barkod/KDV/fiyat otomatik (K9 aktif)
   ├─ kullanıcı çözümlemeden ayrılırsa (blur/Enter):
   │      önce manuel kabul edilir (veri kaybolmasın),
   │      sonra async tam eşleşme (kod / barkod / ad) varsa → stoğa YÜKSELTİLİR
   └─ tam eşleşme yoksa → manuel kalır (Transfer'de ise satır temizlenir + uyarı)
```

- **Stable guard (`settled`):** çözümlenmiş satır tekrar çözümlenmez; yalnız yeni `input`
  satırı yeniden açar. Böylece "tam kod + Enter" ile seçilen stok, kullanıcı başka hücreye
  geçtiğinde yanlışlıkla manuele dönmez.

## 4. API uçları

| Uç | Davranış |
|---|---|
| `GET /api/stok/ara?q=` | Stok kodu, adı, barkod üzerinden canlı arama (LIMIT ~10); eşleşme yoksa `[]` |
| `GET /api/cari/ara?q=&tip=` | Unvan + kod araması; `tip=Satis|Alis` filtresi (yanlış tip boş döner) |

## 5. Test sonuçları

| Test | Kapsam | Sonuç |
|---|---|---|
| `test_form_satir.js` (jsdom) | Boş satır, autocomplete, otomatik fiyat/KDV/tutar, manuel fallback, toplamlar, tam kod + Enter, cari arama, satır silme, form dizi hizası | **16/16 ✅** |
| `test_form_satir2.js` (jsdom) | Transfer'de manuel yasak + uyarı ipucu + tam kod stoklu; K9 iskonto önceliği (stok > cari > 0) | **6/6 ✅** |
| `test_form_satir3.js` (jsdom → HTTP) | UI'da kurulan stoklu + manuel satırın gerçek sunucuya kaydı; kalem/cari/toplam doğrulandı (fatura oluşup temizlendi) | **✅** |
| `test_manuel_satir.py` (regresyon) | K33 manuel satır uçtan uca akışı | **28/28 ✅** |

## 6. Bu akışta tespit edilip düzeltilen hata

- **`form-satir.js` `blur` yeniden çözümleme:** tam kod + Enter ile stok seçildikten sonra,
  kullanıcı başka hücreye geçince `blur` satırı yeniden çözüp, ekranda kalan tam kodu manuel
  açıklamaya çeviriyordu → satır stoksuz kaydediliyordu. `settled` bayrağı ile giderildi;
  `test_form_satir3.js` bu senaryoyu uçtan uca doğrular.

## 7. Etkilenen dosyalar

- `api.py` — `GET /api/stok/ara`, `GET /api/cari/ara` (yeni)
- `static/js/form-satir.js` — ortak satır içi yazma + autocomplete motoru (yeni)
- `static/style.css` — canlı arama + satır içi input stilleri
- `fatura.py`, `irsaliye.py` — `_cari_secim(cariler, cari_id) → (etiket, iskonto)`; view'ler form
  sözleşmesini geçiyor
- `templates/fatura/form.html`, `templates/irsaliye/form.html` — yeni akışa yeniden yazıldı;
  irsaliye Transfer'de `data-manuel-yasak=1` + cari gizli + tip değişimi otomatik submit
- `test_form_satir.js`, `test_form_satir2.js`, `test_form_satir3.js` — jsdom testleri (yeni)
