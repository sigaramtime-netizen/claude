# Devir: GM1 → GM2 (Arena GM) — D012 Direktifi

- **Tarih:** 2026-09-14
- **Devreden:** GM1 (Claude) — ücretsiz kotası doldu
- **Devralan:** GM2 (Arena GM) — **acil yedek devrede** (KRAL kuralı: GM2 yalnızca GM1 kotası
  dolduğunda görev alır; normal akışta tek karar mercii GM1'dir)
- **Konu:** D012 direktifinin kesinleştirilmesi + coder'a devri

---

## 1. Genel durum (GM2'ye özet)

- **D001–D011 ONAYLANDI.** Son mühür: **D011 v1.42.0** (GM1, 2026-09-14).
  Rapor: `denetim-raporlari/R011-denetim.md` (iki repoda).
- GM1, D011 denetiminin sonunda şunu yazdı: "D012 (satır bazlı KDV + çoklu döviz +
  Para Birimi/Birim'in tabloya taşınması) direktifi önceki turda netleştirildi —
  coder oraya geçebilir." Yani D012 kapsamı GM1 + KRAL tarafından zaten kararlaştırıldı;
  GM2'nin yapacağı, bu kapsamı **kesin direktif dosyasına** döküp coder'a devretmektir.

## 2. D012 kapsamı (GM1 + KRAL kararı — GM2 DEĞİŞTİRMESİN)

- **B — Satır bazlı KDV dahil/hariç:** her kalem satırına opsiyonel `kdv_dahil` override;
  boşsa belge geneli varsayılan. Kapsam: **irsaliye, fatura, teklif, sipariş** kalem
  satırları. Gerekçe: "bazı kalemler faturasız/istisna olabilir" — tek belgede karışık
  KDV muamelesi.
- **D — Çoklu döviz (eşzamanlı gösterim):** belge kaydedilirken kur sabitlenir (K2 deseni);
  ekranda döviz + TL karşılığı yan yana gösterilir; cari ekstrede para birimi filtresi
  (Tümü/TRY/USD/EUR) + döviz bazlı alt toplamlar.
- **Para Birimi & Birim tablo geçişi (KRAL revizyonu):** `PARA_BIRIMLERI` (sabit liste) ve
  `BIRIMLER` (sabit liste) → DB tablo (kod/ad, aktif, sirket_id); D011'deki inline ekleme
  deseni (＋ ekle → prompt → POST → select + seç, idempotent) + Ayarlar→Tanımlar pasifleştirme
  (K32: silme yok). Tohum: TRY/USD/EUR korunur; `doviz_kur.para_birimi` ile uyumlu.

## 3. GM2'nin netleştirmesi gereken AÇIK KARARLAR

1. **GBP:** GM1 ilk direktifte "yalnızca TRY/USD/EUR" dedi ama sistemde GBP de var
   (`PARA_BIRIMLERI=[TRY,USD,EUR,GBP]`, `TCMB_KODLARI=(USD,EUR,GBP)`). D012 kapsamına
   GBP dahil mi, hariç mi? (Tutarlılık için dahil önerilir.)
2. **Birim listesi:** `BIRIMLER` sabit listesindeki mevcut değerler DB'ye tohum olarak
   alınsın mı? (Adet, kg, metre vb.)
3. **Sürüm hedefi:** D011 v1.42.0 → D012 v1.43.0 (öneri).

## 4. GM2'den beklenen çıktı

`gm-direktifleri/D012-*.md` kesin direktif: SONUÇ + yukarıdaki 3 açık kararın cevabı +
kabul kriterleri + kanıt + teslim (ZIP, MD5/SHA256). Kral çıktıyı köprüye yapıştırır;
köprü iki repoya işler ve coder'a devreder.

## 5. GM2 rol hatırlatması (KRAL kuralı)

GM2 yalnızca **acil yedek**tir — şu an görevde çünkü GM1 kotası doldu. GM1 kotası
yenilendiğinde vardiya GM1'e döner. D012'yi GM1'in kararlaştırdığı kapsamın DIŞINA
taşıma (yeni konu ekleme); yalnızca yukarıdaki açık kararları netleştir.
