# Faz 5 — Genel Muhasebe (1.20) — özet + test kanıtları (revize)

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji · **Faz 5 / Modül 1/6** · **Durum:** şartlı onay giderildi ✅

> Faz 5 (Mali/Analitik) ilk modülü. Sıra (bkz. `docs/faz5-plan.md`): Genel Muhasebe → Kartoteks →
> Transfer → Finansal Analiz → Beyanname → Demirbaş. Faz sonunda tek onay paketi sunulur.

Kullanıcının şartlı onayındaki 3 madde bu revizyonda kapatıldı:
1. ✅ Çek/senet **ara hesapları** (101/121/103/321) bu modülde tamamlandı (Beyanname'ye ertelenmedi).
2. ✅ `yevmiye.sube_id` eklendi (K1) + kaynağından geri dolduruldu + mizan şube filtresi.
3. ✅ Atomiklik teyit edildi: cari hareket + yevmiye fişi **aynı işlem + tek commit**; fiş üretimi
   hata verirse transaction geri alınır (eksik hesap kodunda `RuntimeError`).

Ayrıca doğrulama sırasında **2 gerçek hata daha** bulunup düzeltildi:
- **Transfer çift kaydı:** seed'deki "Kasa → Banka" (TR-001) çift taraflı ayrı kayıt olarak girilmişti;
  `ilgili_modul='Transfer'` bağı kurulmadığı için GM'de 100/102 iki kez sayılıyordu → bağ kuruldu, mükerrer
  fiş silindi. Artık **GM Kasa/Banka bakiyesi = Kasa/Banka modülü neti** (100=36.700, 102=268.640).
- **Tedarikçi ödemeleri yanlış hesapta:** kasa/banka çıkışları cari tipine bakmadan 120'ye yazılıyordu;
  artık **Tedarikçi → 320 SATICILAR, Müşteri → 120 ALICILAR** (HerIkisi yön bazlı).

---

## 1) Veri Modeli Özeti

### 1.1 `hesap` (yeni — Tekdüzen Hesap Planı çekirdeği)
| Kolon | Tip | Açıklama |
|---|---|---|
| id | INTEGER PK | |
| kod | TEXT UNIQUE | 100 Kasa … 770 Genel Yönetim Gid. (27 hesap seed) |
| ad | TEXT | hesap adı |
| tip | TEXT CHECK | `Aktif, Pasif, Ozkaynak, Gelir, Gider` |
| ust_kod | TEXT | üst hesap (gruplama) |
| aktif | INTEGER | 1 |

### 1.2 `yevmiye` (yeni — fiş başlığı)
| Kolon | Tip | Açıklama |
|---|---|---|
| id | INTEGER PK | |
| fis_no | TEXT UNIQUE | `FIS-{YYYY}-{NNN}` (K13) |
| tarih / aciklama | TEXT | |
| kaynak_modul / kaynak_id | TEXT/INT | K8 izi (Fatura/Kasa/Banka/CekSenet/Muhasebe) |
| **kaynak_sahne** | TEXT | çek/senet çok-fiş ayracı (`giris`/`tahsil`/`odeme`; diğerleri NULL) |
| **sube_id** | FK→sube | **K1** — kaynağın şubesi (Fatura/Çek-Senet kendi; Kasa/Banka hesabın şubesi) |
| durum | TEXT CHECK | `Taslak, Onaylandı, İptal` |
| created_by / created_at / updated_at | | audit |

### 1.3 `yevmiye_kalem` (yeni — fiş satırları)
| Kolon | Tip | Açıklama |
|---|---|---|
| id | INTEGER PK | |
| yevmiye_id | FK → yevmiye | |
| hesap_id | FK → hesap | |
| borc / alacak | REAL | her satırda yalnız biri dolu |
| aciklama | TEXT | hesap kodu (referans) |

### 1.4 Entegrasyon
`fatura/kasa/banka` onay akışlarına kanca: `muhasebe.fis_uret(conn, kaynak, id)` / `fis_sil(...)`.
`cek_senet` **her durum geçişinde** `muhasebe.cek_senkron(conn, cid)` çağırır (cari + fiş seti
GÜNCEL durumla senkronize; `giris` fişi + cari kayıt **kayıt oluşturmada**, tahsil/ödeme fişi
durum geçişinde).

---

## 2) Ekran Listesi

| # | Ekran | Rota | Yetki |
|---|---|---|---|
| 1 | Yevmiye listesi (filtre + KPI) | `GET /muhasebe` | tüm roller |
| 2 | Yeni manüel fiş (çok satırlı) | `GET/POST /muhasebe/yeni` | Admin/Muhasebe |
| 3 | Fiş detayı (kalemler + audit) | `GET /muhasebe/{id}` | tüm roller |
| 4 | Fiş onay/iptal | `POST /muhasebe/{id}/durum` | Admin/Muhasebe |
| 5 | Hesap planı | `GET /muhasebe/hesaplar` | tüm roller |
| 6 | Mizan (**şube filtresi**) | `GET /muhasebe/mizan?sube_id=` | tüm roller |
| 7 | Büyük defter (hesap bazlı + bakiye) | `GET /muhasebe/defter` | tüm roller |
| 8 | Toplu fiş üretimi (retroaktif) | `POST /muhasebe/toplu-uret` | Admin/Muhasebe |
| 9 | Dönem açılış fişi | `POST /muhasebe/acilis` | Admin/Muhasebe |
| 10 | Dönem kapanış fişi | `POST /muhasebe/kapanis` | Admin/Muhasebe |

---

## 3) Örnek Test Senaryosu (canlı HTTP)

| # | Adım | Beklenen | Kanıt |
|---|---|---|---|
| 1 | `/muhasebe` açılış (seed) | 27 hesap + retroaktif **24 fiş** (4 fatura + 9 kasa + 6 banka + 5 çek giris) | ✅ |
| 2 | Mizan denge | borç = alacak (**831.133,60**) | ✅ |
| 3 | BELGE-NNN fişi | 120 borç 21.598,8 / 600 alacak 17.999 / 391 alacak 3.599,8 | ✅ |
| 4 | GM Kasa/Banka = modül neti | 100=36.700 ✓, 102=268.640 ✓ (transfer tek kayıt) | ✅ |
| 5 | Ara hesap = portföy | 101=58.440, 121=28.500, 103=−30.000, 321=0 | ✅ |
| 6 | Alınan çek: oluştur→Tahsile Verildi→Tahsil→Karşılıksız→İptal | giris(101/120)→(aynı)→+tahsil(100/101)→sil→cari geri al | ✅ |
| 7 | Verilen çek: oluştur→Ödendi→İptal | giris(320/103) + cari BORÇ→odeme(103/100)→temiz | ✅ |
| 8 | Tedarikçiye banka ödemesi | **320 borç / 102 alacak** + cari borç; iptalde ikisi de silinir | ✅ |
| 9 | sube_id | yeni banka fişi sube_id=1; mizan `?sube_id=1` farklı sonuç | ✅ |
| 10 | Manüel fiş (2 satır dengeli) | doğru borç/alacak eşleşmesi | ✅ |
| 11 | Manüel fiş (DENGESİZ) | reddedilir | ✅ |
| 12 | Toplu üretim 2. kez | 0 yeni (idempotent) | ✅ |
| 13 | Rol: depo | `/muhasebe/yeni` 403 | ✅ |
| 14 | Regresyon | 22 ana sayfa 200 | ✅ |

---

## 4) Notlar

- **Ciro:** otomatik fiş üretmez (karşı taraf bilgisi modelde yok); kullanıcıya manuel fiş önerilir
  (320 borç / 101 alacak). Karşılıksız/İptal net sıfır sağlar.
- **Seed devir kayıtları:** seed'deki bazı cari hareketler (ör. BELGE-NNN, BELGE-NNN) Faz 2
  öncesi tarihsel girişlerdir ve GM'de karşılığı yoktur — bunlar **dönem açılış (devir)** kapsamındadır;
  `POST /muhasebe/acilis` (fark → 500 Sermaye) ile taşınır. Mali müşavir incelemesi için ayrıca
  listelenmeye uygundur (Beyanname fazında).
- KDV/matrah ayrımı fatura kalemlerinden gelir; kur farkı faturasındaki %20 fallback (taşınan not #1)
  Beyanname modülünde netleştirilecek.
