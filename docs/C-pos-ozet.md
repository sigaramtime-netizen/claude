# C — POS (Satış Noktası) · Faz Özeti (v1.28.0)

Tarih: 2026-09-11 · Paket: C — POS (Satış Noktası) · Kapsam: terminal + satış + ödeme + rapor

---

## 1) Veri Modeli Özeti

C paketi 3 yeni tablo getirir; satış zinciri tamamen mevcut modüllerin tek noktadan
çağrılan yardımcılarıyla kurulur (manuel ikinci kayıt yok).

### Yeni tablolar
| Tablo | Amaç | Kritik alanlar |
|---|---|---|
| `pos_terminal` | Terminal kartı | `ad`, `kasa_id` (nakit), `banka_id` (kart/havale), `depo_id` (stok düşümü), `komisyon_orani`, `max_taksit`, `aktif` |
| `pos_satis` | POS satış başlığı | `fatura_id` (UNIQUE → 1:1 Onaylı Satış Faturası), `terminal_id`, `taksit`, `komisyon_toplam`, `veresiye_tutar` |
| `pos_satis_odeme` | Ödeme dağılımı | `tip` CHECK ∈ {Nakit, Kart, Havale, Veresiye, Cek, Senet}, `tutar`, `komisyon`, `cek_senet_id` |

### Üretim kuralları (tek istekte, tek işlemde)
1. **Fatura** → `durum='Onaylandı'`, `tip='Satis'`, ön ek `SF` (`TIP_ON_EK`). KDV/iskonto aynı genel mantık.
2. **Cari + yevmiye** → `fatura._cari_uygula(yon=1)` (Satış → cariye BORÇ) + `muhasebe.fis_uret("Fatura", fid)` (120 / 600 / 391).
3. **Stok** → `stok._hareket_olustur(..., "POS Çıkışı", -miktar)` terminalin `depo_id`'sinden düşer.
4. **Tahsilat** (ödeme tipine göre):
   - **Nakit** → `kasa.kasa_hareket_olustur` + `fis_uret("Kasa", hid)` + cariye ALACAK.
   - **Kart** → bankaya **net** tutar (`tutar − komisyon`) + `fis_uret("Banka", hid)` + cariye ALACAK (brüt).
   - **Havale** → bankaya brüt (komisyonsuz) + fiş + cariye ALACAK.
   - **Veresiye** → yalnızca fatura vadesi + `pos_satis.veresiye_tutar`; cari borç açık kalır.
   - **Çek/Senet** → `cek_senet` (Alinan) + `muhasebe.cek_senkron` (cariye ALACAK + yevmiye).
   - Ödenmeyen fark otomatik **Veresiye** satırına düşer; ödeme fazlası engellenir.
5. **Kart komisyonu** → `tutar × komisyon_orani/100`, `pos_satis_odeme.komisyon` + `pos_satis.komisyon_toplam`'da izlenir; bankaya net girer.

### Varsayılanlar
- Cari seçilmezse **"Peşin (Perakende) Müşteri"** (`PER-001`, sirket bazında seed).
- Çek/senet vadesi zorunlu; taksit `max_taksit` ile sınırlı.
- **Tüm zincir tek kod yolundan** (`pos_satis_olustur`) üretilir: rota ve seed (`db.seed_pos`)
  aynı çekirdeği çağırır → fatura/cari/stok/kasa-banka/yevmiye tutarlılığı yapısal olarak garanti.
- `seed_pos()` örnek veri olarak 3 demo satış üretir (idempotent): BELGE-NNN (Nakit+Kart,
  komisyon 207,62) · BELGE-NNN (Havale) · BELGE-NNN (Veresiye 17.198,80).

---

## 2) Ekran Listesi

| Rota | Yöntem | Yetki | Açıklama |
|---|---|---|---|
| `/pos` | GET | Admin · Satis | Hızlı satış: canlı ürün arama (barkod/kod/ad), sepet, bölünmüş ödeme, taksit/vade |
| `/pos/satis` | POST | Admin · Satis | Satışı tamamlar → Onaylı Satış Faturası + tüm entegrasyon |
| `/pos/satislar` | GET | herkes | POS satış listesi (fatura no/müşteri aramalı) |
| `/pos/satis/<id>` | GET | herkes | Ödeme dağılımı + komisyon/veresiye özeti + çek bağlantısı |
| `/pos/terminaller` | GET | Admin · Muhasebe | Terminal kartları |
| `/pos/terminal/yeni` | GET/POST | Admin · Muhasebe | Yeni terminal (kasa + banka + depo + komisyon + taksit) |
| `/pos/terminal/<id>/duzenle` | GET/POST | Admin · Muhasebe | Terminal düzenleme |
| `/pos/terminal/<id>/durum` | POST | Admin · Muhasebe | Aktif/pasif geçişi |
| `/pos/rapor` | GET | herkes | Günlük rapor: ödeme şekline göre tahsilat + terminal bazında ciro/komisyon |

**NAV:** "POS (Satış Noktası)" grubu — Hızlı Satış · POS Satışları · Günlük Rapor · Terminaller.

---

## 3) Örnek Test Senaryosu (e2e — `test_pos.py`, 41 kontrol)

1. Terminal kartı: oluştur + listele + düzenle + pasifleştir/aktifleştir; pasif terminalle satış engellenir.
2. Bölünmüş ödeme (Nakit 72 + Kart 48; genel 120) → Onaylı Satış Faturası + kalem + pos_satis + 2 ödeme satırı.
3. Kart komisyonu otomatik: `48 × 1,79% = 0,86`; bankaya net `47,14`; komisyon satırda + başlıkta.
4. Cari net sıfır (tam tahsilat: borç 120 − alacak 120); stok −1 (POS Çıkışı, depo 2).
5. Yevmiye: Fatura + Kasa + Banka fişleri (3 ayrı fiş).
6. Havale: komisyonsuz brüt banka girişi.
7. Veresiye: 40 nakit → 80 veresiye; fatura vadesi yazılır; cari borç 80 kalır.
8. Çek: `cek_senet` (Alinan/Cek, vade) + cari ALACAK + çek yevmiyesi + ödeme satırı referansı.
9. Perakende müşteri (boş cari) → PER-001.
10. Korumalar: stok yetersiz / ödeme fazlası / vadesiz senet / yabancı şirket ürünü → satış engellenir.
11. Günlük rapor + satış listesi + detay render.
12. Yetki: Depo kullanıcısı `/pos` 403.
13. Şirket izolasyonu: 2. şirket terminal göremez; çapraz terminalle satış engellenir.
14. Temizlik: yetim `pos_satis` yok, `PRAGMA foreign_key_check` boş, **yetim yevmiye fişi yok**
    (`yevmiye.kaynak_id` polimorfik referans olduğu için elle taranır — SQLite FK'sı bunu görmez).

---

## 4) Doğrulama Kanıtı

- Test: `test_pos.py` **41/41** ✅ (tam regresyon: 12 paket / **259** kontrol yeşil, 0 başarısız).
- Ekran görüntüleri (`docs/ekran-goruntuleri/yeni-tema/`): `pos-satis-ekrani`, `pos-satislar`,
  `pos-satis-detay`, `pos-gunluk-rapor`, `pos-terminaller` (20260911-084138).
- Örnek veri (seed'den, tekrarlanabilir): `BELGE-NNN` (Nakit+Kart bölünmüş, komisyon 207,62),
  `BELGE-NNN` (Havale), `BELGE-NNN` (Veresiye 17.198,80).
- `data/erp.db` **sıfırdan temiz seed** ile üretildi: yetim fiş yok, FK boş, test artığı yok.
