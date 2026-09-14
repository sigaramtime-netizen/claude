# Görev Durum Tablosu

> GM her kontrolde bu tabloyu günceller.

| Görev | Başlık | Durum | Not |
|-------|--------|-------|-----|
| D001  | Örnek direktif (şablon) | BEKLEMEDE | — |
| D002  | Coder v1.34.0 kodunu GitHub'a yüklesin + GM denetimi | ONAYLANDI | F4 22/22 + 424/424 — F4 MÜHÜR ✅ |
| D003  | F5-A Finansal Analiz & Dashboard | ONAYLANDI | 18/18 + 442/442 — MÜHÜR v1.35.0 ✅ |
| D004  | F5-B Demirbaş & Amortisman Raporlama | ONAYLANDI | 18/18 + 460/460 — MÜHÜR v1.36.0 ✅ |
| D005  | F5-C Beyanname Hazırlık Raporları | ONAYLANDI | 18/18 + 478/478 — MÜHÜR v1.37.0 ✅ |
| D006  | F6 Son Cila (bildirim API + yetki CSV + yazdırma + şube özet) | ONAYLANDI | 18/18 + 496/496 — MÜHÜR v1.38.0 ✅ |
| D007  | Kullanıcı Bildirimleri & İyileştirmeler (10 madde) | ONAYLANDI | GM1 (Claude) bağımsız denetim: 30/30 + 526/526, 10 madde kodda teyit, FK temiz — MÜHÜR v1.39.0 ✅ |
| D008  | Belgeleme tamamlama (CHANGELOG v1.34→v1.39 + 5 faz özeti) + bakim/detay stok seçici typeahead | ONAYLANDI | GM1 2.tur: 5 doküman F1/F2 şablonuyla doğrulandı — D008 MÜHÜR ✅. GM1 kuralı: kod/mantık paketlerinde zip + bağımsız test ŞART (ANAYASA v10) |
| D009  | Güvenlik & Sağlamlık Denetimi (SQL enjeksiyon, oturum, dosya yükleme, CSRF, kaba kuvvet) | ONAYLANDI | GM2 (Arena GM) nöbette: 18/18 + 545/545 (KÖPRÜ bağımsız doğruladı), CSRF hibrit, kaba kuvvet kilidi, oturum 12s, yetki matrisi temiz — D009 MÜHÜR v1.40.0 ✅ |
| D010  | Uygulama İçi Yedekleme & Geri Yükleme (yalnız Admin) | ONAYLANDI | GM1 (Claude) bizzat denetledi: test_d010 16/16 + 24 eski test 545/545 = 561/561 (köprü iddiasıyla birebir); path traversal 2 katman, çok şirketli izolasyon tutarlı, geri yükleme WAL-güvenli — D010 MÜHÜR v1.41.0 ✅. GM1 süreç itirazı: direktif GM1'den geçmeden "GM2 onayı" damgası yemiş; sonraki her direktif önce GM1'den geçmeli |
| D011  | Tanım Verileri (Kategori & Cari Grup) + Hızlı Barkod | ONAYLANDI | GM1 bizzat denetledi: 582/582 (ilk tur 2 hata GM1'in ardışık çalıştırmasından, taze zip'te temiz — kod hatası değil); kategori+cari grup inline + pasifleştirme (K32), hızlı barkod 3 formda, K1 izolasyonu — D011 MÜHÜR v1.42.0 ✅ |
| D012  | Satır Bazlı KDV + Çoklu Döviz + Para Birimi/Birim tablo geçişi (B+D+X) | BEKLEMEDE | GM2 (acil yedek) kesin direktif verdi (2026-09-14): GBP dahil, BIRIMLER 11 değer 1:1 tohum, v1.43.0. Kapsam B+D+X. Direktif: `gm-direktifleri/D012-satir-kdv-coklu-doviz-parabirimi-birim-db-v1.43.0.md` — coder'a devredilecek |
| D013  | Cari Tahsilat / Ödeme Ekranı (E) | BEKLEMEDE | GM1 kapsam kararı; D012'den sonra |

Durum akışı: `BEKLEMEDE` → `KODLANIYOR` → `KODLANDI` → `KONTROLDE` → `ONAYLANDI` / `REVIZYON`
