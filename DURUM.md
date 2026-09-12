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
| D008  | Belgeleme disiplini: CHANGELOG + F5-F6/D007 faz özetleri | BEKLEMEDE | GM1 önerisi: kod/test tamam ama kayıt dokümanları eksik |

Durum akışı: `BEKLEMEDE` → `KODLANIYOR` → `KODLANDI` → `KONTROLDE` → `ONAYLANDI` / `REVIZYON`

---
**ÖNEMLİ NOT (GM1 riski):** `templates/bakim/detay.html` içinde cihaz eklerken `stok_id` düz
sayısal input (select değil) — D008'e dahil edilebilir.
