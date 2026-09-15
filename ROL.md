# ROL DURUMU

> Bu dosya: kim ne rolde, tek kaynak. KÖPRÜ (Arena danışman) günceller.

- **GM1 (beyin, karar)**  : CLAUDE (web) — DEVREDE (Asil GM, kotası açık)
- **GM2 (acil yedek GM)** : ARENA GM (gm@arena) — BEKLEMEDE (Acil yedek)
- **Coder (kod)**         : ARENA CODER (coder@arena)
- **Danışman + Köprü**    : ARENA (bu pencere — GM kararlarını repoya işler)

## NÖBETTEKİ GM: **CLAUDE (GM1 — Asil GM)** ← vardiya şalteri

Son güncelleme: 2026-09-15

## ⚠️ GM süreç kuralı (2026-09-14 — KRAL onaylı, kalıcı)

- **Tek karar mercii: GM1 (Claude).** Her direktif önce GM1'den geçmeli; mikro-kararlar
  GM1'e sorulmalı; coder'ın hazırladığı aday konu doğrudan yürürlüğe giremez.
- **GM2 (Arena GM) = YALNIZCA ACİL YEDEK.** Sadece GM1 kotası dolduğunda devreye girer.
  Normal akışta direktif yazamaz/onaylayamaz. (KRAL kararı 2026-09-14.)

## Devir kaydı
| Tarih | Olay | Not |
|-------|------|-----|
| 2026-09-12 | Köprü sistemi kuruldu (ANAYASA v6) | Claude GM1 |
| 2026-09-12 | **NÖBET GM2'ye geçti** (Claude kotası doldu) | D009 denetimi GM2'de: `devir/D009-gm1-den-gm2.md` |
| 2026-09-14 | **NÖBET GM1'e döndü** | D010 denetimi GM1'de: `devir/D010-gm2-den-gm1.md` |
| 2026-09-14 | **GM1 süreç kuralı koydu** | "GM2 tanımıyorum; her direktif önce benden geçmeli" → R010 |
| 2026-09-14 | **KRAL kararı: GM2 = yalnız acil yedek** | Normal akışta tek karar mercii GM1; GM2 yalnız kota-dolu anlarda |
| 2026-09-14 | **D011 ONAYLANDI (GM1)** | v1.42.0 MÜHÜR → R011 |
| 2026-09-14 | **NÖBET GM2'ye geçti** (GM1 ücretsiz kotası doldu) | D012 direktifi GM2'de: `devir/D011-gm1-den-gm2.md` |
| 2026-09-15 | **NÖBET GM1'e döndü** (GM1 devrede) | D012 ONAYLANDI (v1.43.0 MÜHÜR), D013 kesin direktif verildi |
