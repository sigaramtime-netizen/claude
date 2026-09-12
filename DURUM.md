# Görev Durum Tablosu

> GM her kontrolde bu tabloyu günceller.

| Görev | Başlık | Durum | Not |
|-------|--------|-------|-----|
| D001  | Örnek direktif (şablon) | BEKLEMEDE | — |
| D002  | Coder v1.34.0 kodunu GitHub'a yüklesin + GM denetimi | ONAYLANDI | GM 2026-09-11 19:20 — F4 22/22 + 424/424, 6 ekran doğrulandı — F4 MÜHÜR ✅ |
| D003  | F5-A Finansal Analiz & Dashboard (bütçe/hedef vs gerçekleşen) | ONAYLANDI | GM 2026-09-11 20:10 — butce_hedef K1+UNIQUE, 6 kart + inline SVG, 18/18 + 442/442 — F5-A MÜHÜR v1.35.0 ✅ |
| D004  | F5-B Demirbaş & Amortisman Raporlama (plan, özet, API, CSV) | ONAYLANDI | GM 2026-09-11 20:35 — plan + kategori + API + CSV + SVG, 18/18 + 460/460 — F5-B MÜHÜR v1.36.0 ✅ |
| D005  | F5-C Beyanname Hazırlık Raporları (KDV devreden + Geçici + Nakit) | ONAYLANDI | GM 2026-09-12 08:20 — 4 kart + KDV oran SVG + /api/beyanname/ozet + kdv/csv, 18/18 + 478/478 — F5-C MÜHÜR v1.37.0 ✅ |
| D006  | F6 Son Cila: Bildirim API + Yetki CSV + Yazdırma + Şube Özet | ONAYLANDI | GM 2026-09-12 08:55 — v1.38.0 yeni tablo YOK; canlı HTTP 18/18 + tam regresyon 496/496 (22 dosya); /api/bildirimler 6 alan+filtr+K1, /yetkiler/csv 255 satır+rol, ortak yazdırma belge.html @media print (Fatura/İrsaliye/Sipariş K1 302 şube 403), /api/sube/ozet 2 şube, /api/saglik 1.38.0 db ok; F5-C/F5-B/F4/F1 korundu, FK0 — F6 MÜHÜR v1.38.0 ✅ |
| D007  | Kullanıcı Bildirimleri & İyileştirmeler (10 madde: KDV select, marka+, stok 8 alan, TTEC fix, irsaliye döviz, eksi stok, kartoteks typeahead, MÜŞTERİ-A 2 irsaliye bug, detay Sil, genelleme) | KODLANDI | Coder 2026-09-12 — v1.39.0; stok_kart +9 kolon (8 alan+model) + irsaliye.doviz_kur (idempotent PRAGMA); 10 madde tamam; test_d007 30 kontrol + tam regresyon 526/526 (23 dosya); FK0; kanitlar/v1.39.0; GM onayı bekliyor |

Durum akışı: `BEKLEMEDE` → `KODLANIYOR` → `KODLANDI` → `KONTROLDE` → `ONAYLANDI` / `REVIZYON`
