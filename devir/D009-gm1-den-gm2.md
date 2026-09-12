# DEVİR NOTU — D009 denetimi: GM1 (Claude) → GM2 (Arena GM)

- **Tarih:** 2026-09-12
- **Devreden:** GM1 = Claude (günlük hakkı doldu)
- **Devralan:** GM2 = Arena GM (gm@arena)
- **Neden:** GM1, D009 denetimine başladı (zip'i aldı, testleri çalıştıracaktı) ama hakkı bitmeden KARAR VEREMEDİ. D009 için henüz ONAYLANDI/REVİZYON kararı YOK.

---

## NEREDEYİZ?

- Proje: **v1.40.0** (D009 kodlu). D001–D008 ONAYLANDI.
- **D009 (Güvenlik & Sağlamlık Sertleştirme): KODLANDI — GM denetimi bekleniyor.**
- Coder işi bitirdi ve teslim etti (commit `11915a9`).
- KÖPRÜ (Arena danışman) bağımsız doğruladı: `test_d009_guvenlik.py` 18/18 + tam regresyon 24 dosya 545/545 (0 başarısız).

## GM2'NİN GÖREVİ: D009'u DENETLE ve KARAR VER

1) Şu metinleri oku (public raw link — interneti olan her Arena penceresi açabilir):
- Direktif:    https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/gm-direktifleri/D009-guvenlik-sertlestirme.md
- Mikro-karar: https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/gm-direktifleri/D009-mikro-karar.md  (CSRF=HİBRİT, teslim=ZIP)
- Coder raporu: https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/coder-raporlari/R009-guvenlik-sertlestirme.md
- KÖPRÜ doğrulaması: https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/gm1-paketleri/GM1-PAKET-D009-denetim.md

2) Kodu incele (okuma):
- Diff (özet): https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D009-diff.txt
- Tam dosyalar: https://raw.githubusercontent.com/sigaramtime-netizen/claude/main/kod-inceleme/D009/  (app.py, core.py, db.py, test_d009_guvenlik.py ...)

3) **İDEAL: Testleri BİZZAT çalıştır** (GM1 kuralı: kod paketinde bağımsız test şart).
   Bunun için private repoyu klonla (aşağıdaki komut) ve çalıştır:
   ```
   cd kod && python3 app.py   (port 8080)
   python3 test_d009_guvenlik.py    → 18/18 beklenir
   for t in test_*.py; do python3 $t; done   → 545/545 beklenir
   ```

4) Kararını ŞU FORMATTA yaz (kral kopyalayıp köprüye iletecek):
```
SONUÇ: ONAYLANDI  veya  SONUÇ: REVİZYON
Gerekçeler (madde madde):
1. ...
REVİZYON ise coder'ın düzelteceği maddeler:
1. [dosya] → [sorun] → [beklenen düzeltme]
Ek notlar / riskler:
- ...
```

## ÖNEMLİ BAĞLAM (GM2 bilmeli)

- CSRF tasarımı GM1 onaylı **HİBRİT**: token varsa eşleşmeli; Origin/Referer varsa host
  eşleşmeli (cross-site→403); ikisi de yoksa (eski test POST'ları) DOKUNULMAZ → regresyon bozulmaz.
- Kaba kuvvet: 5 hatalı giriş → 15 dk kilit (`kullanici` tablosuna 2 alan, idempotent).
- Oturum: `secrets.token_urlsafe(32)` + 12 saat hareketsizlik süresi + `/cikis` sunucu tarafı silme.
- Dosya yükleme zaten sağlamdı (beyaz liste + 15MB + traversal temizliği) — yalnızca testlendi.
- Yetki: tüm `/api/*` giriş ister; anonim yalnız `/giris` + `/saglik` (statik JSON probu).
- KÖPRÜ, coder'ın zip'inde 2 dosyada sansürsüz "gerçek müşteri adı" buldu ve düzeltti
  (sansür: kişi adı → MÜŞTERİ-A). Zip'in son hali: MD5 dfc3b9ac..., SHA256 e75da953...

## KURAL HATIRLATMASI

- KÖPRÜ karar VERMEZ, yalnızca işler. D009 kararı SENİNDİR (GM2).
- Kararını metin olarak yaz → kral köprüye iletir → köprü denetim-raporlari/R009-denetim.md
  olarak iki repoya işler + DURUM.md günceller.
