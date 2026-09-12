# F1 — Mali Etki: "Zincirdeki İlk Belgede Bir Kere" · Faz Özeti (v1.31.0)

Tarih: 2026-09-11 · Paket: F (mali etki doğruluğu) · Kapsam: irsaliyeli akışta mali etkinin
(cari borç/alacak + yevmiye) **irsaliye onayında bir kere** oluşması; kaynak irsaliyesi olan
faturanın yalnızca belgeleştirmesi (mükerrer mali etki üretmemesi).

Kural (kullanıcı onaylı):
- **İrsaliyeli akış:** mali etki irsaliye **onayında** doğar.
- **Kaynaklı fatura** (`fatura.kaynak_irsaliye_id IS NOT NULL`) onaylandığında **mali etki üretmez**.
- **İrsaliyesiz akış** (POS, doğrudan fatura — `kaynak_irsaliye_id IS NULL`): mali etki **fatura
  onayında** doğmaya devam eder (eski davranışla birebir aynı, dokunulmadı).

---

## 1) Veri Modeli Özeti

Yeni tablo/migration **yok**. Değişiklik yalnız mevcut tabloların kullanım kuralında:

| Tablo | Değişiklik |
|---|---|
| `cari_hareket` | `ilgili_modul='Irsaliye'`, `belge_tipi ∈ {Satış İrsaliyesi, Alış İrsaliyesi}` kayıtları artık irsaliye onayında/iptalinde üretilir/silinir. |
| `yevmiye` / `yevmiye_kalem` | `kaynak_modul='Irsaliye'` fişleri irsaliye onayında üretilir, iptalinde silinir. |
| `fatura` | `kaynak_irsaliye_id` dolu ise onay/iptalde cari+fiş üretimi atlanır. |

### Mali etki deseni (`muhasebe._irsaliye_satirlar`)
| İrsaliye tipi | Fiş satırları |
|---|---|
| Satış | `120 borç (genel) / 600 alacak (matrah) + 391 alacak (KDV)` |
| Alış — stoklu | `153 borç (matrah) + 191 borç (KDV) / 320 alacak (genel)` |
| Alış — manuel | `770 borç (matrah) + 191 borç (KDV) / 320 alacak (genel)` |
| Transfer | mali etki **yok** (yalnız depo stok transferi) |

Cari hesap seçimi faturayla aynı (`_cari_hesap`): Müşteri → 120, Tedarikçi → 320.

### İş kuralları
1. İrsaliye **onayı**: stok hareketi + `cari.hareket_ekle` (yön=1) + `muhasebe.fis_uret("Irsaliye", iid)`.
2. İrsaliye **iptali**: kendisinden üretilmiş ve **iptal edilmemiş** fatura varsa iptal **engellenir**;
   yoksa stok geri alınır, cari hareket silinir (yön=-1), fiş silinir (`fis_sil("Irsaliye", iid)`).
3. Fatura **onay/iptal**: `kaynak_irsaliye_id` dolu ise `_cari_uygula` + `fis_uret/fis_sil`
   çağrıları **atlanır** (belge yalnız belgeleştirir).
4. `toplu_uret`: yalnız `kaynak_irsaliye_id IS NULL` faturalara fiş üretir; onaylı (Transfer hariç)
   irsaliyelere `Irsaliye` fişi üretir — **idempotent**.
5. Dashboard satış özeti sorguları hem `Satış Faturası` hem `Satış İrsaliyesi` hareketlerini kapsar
   (bugün / dün / toplam ciro kartları).

---

## 2) Ekran Listesi (etkilenen)

| Rota | Etki |
|---|---|
| `/irsaliye/<id>/durum` (POST) | Onay: stok + cari + yevmiye üretir · İptal: bağlı fatura engeli + geri alır |
| `/fatura/<id>/durum` (POST) | Kaynaklı faturada mali etki atlanır |
| `/muhasebe` · `/muhasebe/<fid>` | `Irsaliye` kaynaklı fişler listelenir/görüntülenir |
| `/muhasebe/mizan` · `/muhasebe/defter` | İrsaliye fişleri doğal olarak dahil (yevmiye bazlı) |
| `/cari/<cid>/ekstre` | `Satış/Alış İrsaliyesi` satırları görünür |
| `/` (dashboard) | Satış özeti irsaliyeleri kapsar |

---

## 3) Örnek Test Senaryosu (e2e — `test_f1_mali.py`, 25 kontrol)

1. Satış irsaliyesi onayı → cari BORÇ (Satış İrsaliyesi) + fiş `120/600/391`.
2. Kaynaklı fatura onayı → cari hareket **YOK** + fiş **YOK**.
3. İrsaliyesiz fatura onayı → cari + fiş **ÜRETİR** (regresyon garantisi).
4. Alış irsaliyesi (stoklu) → cari ALACAK + fiş `153/191/320`; (manuel) → `770/191/320`.
5. Transfer irsaliyesi → mali etki **YOK**; stok transferi **VAR**.
6. Fatura varken irsaliye iptali **engellenir**.
7. Kaynaklı fatura iptali → irsaliye cari hareketi **korunur**.
8. İrsaliye iptali (fatura iptalinden sonra) → cari + fiş **geri alınır**.
9. Bütünlük: FK temiz, yetim yevmiye yok, test kalıntısı yok.

**Sonuç:** `test_f1_mali.py` **25/25**; tam regresyon 14 paket / **313 kontrol / 0 başarısız**
(POS 41 kontrol dahil — irsaliyesiz akış bozulmadı).

---

## 4) Değişen Dosyalar

| Dosya | Değişiklik |
|---|---|
| `muhasebe.py` | `_irsaliye_satirlar()`; `fis_uret`'e `Irsaliye` dalı; `toplu_uret` güncellemesi |
| `irsaliye.py` | `_cari_uygula_irsaliye()`; onay/iptal rotalarına mali etki + bağlı fatura engeli |
| `fatura.py` | onay/iptal rotalarında kaynaklı faturalar için mali etki atlaması |
| `cari.py` | `BELGE_TIPLERI` + `Satış İrsaliyesi`, `Alış İrsaliyesi` |
| `app.py` | dashboard satış özeti sorguları |
| `db.py` | `seed_irsaliye()` irsaliye cari hareketleri; `seed_fatura()` kaynaklı fatura cari hareketleri kaldırıldı |
| `test_f1_mali.py` | YENİ — 25 kontrollük F1 e2e testi |
| `test_eksik_teslimat.py` · `test_manuel_satir.py` | temizlik artık `Irsaliye` fiş + cari kalıntılarını da siler |

---

## 5) Kanıtlar

- Ekran görüntüleri: `docs/ekran-goruntuleri/yeni-tema/f1-*.png` (5 adet).
- Test: `test_f1_mali.py` (25/25) + regresyon (313/313).
- Sürüm: `config.py SURUM = "1.31.0"`.
