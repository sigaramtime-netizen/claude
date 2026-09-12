# Faz 3 — Servis & Garanti (özet + test kanıtları — REVİZE)

**Tarih:** 2026-09-07 · **Firma:** Brn Teknoloji · **Kapsam:** Servis Takip (1.2), Seri No-Garanti (1.16), Notlar (1.1)

> Bu doküman Faz 3 sonu onay paketidir. Kullanıcının **şartlı onay** düzeltmesi (Servis → Fatura
> zinciri + `depo_id` netleştirme) uygulanmış ve test kanıtlarıyla birlikte yeniden sunulmuştur.

---

## 1) Veri Modeli Özeti

### 1.1 `servis_kayit` (yeni)
| Kolon | Tip | Açıklama |
|---|---|---|
| id | INTEGER PK | |
| servis_no | TEXT UNIQUE | `SRV-{yıl}-{NNN}` (K13 yıl bazlı sayaç) |
| cari_id | FK → cari_kart | müşteri |
| cihaz | TEXT | cihaz adı/modeli |
| seri_no | TEXT | garanti/geçmiş eşleşmesi için |
| ariza / aksesuar | TEXT | arıza ve teslim edilen aksesuar |
| gelis_tarihi | TEXT | `date('now','localtime')` |
| teknisyen_id | FK → kullanici | servis sorumlusu |
| durum | TEXT CHECK | `Alındı, Teşhis Edildi, Onay Bekliyor, Tamir Ediliyor, Tamamlandı, Teslim Edildi, İade` |
| garanti_kapsami | INTEGER | 1 = garantide |
| iscilik_ucreti | REAL | TL işçilik |
| aciklama | TEXT | |
| sube_id | FK → sube | K1 gereği baştan nullable |
| created_by / created_at / updated_at | | audit alanları |

### 1.2 `servis_parca` (yeni)
| Kolon | Tip | Açıklama |
|---|---|---|
| id | INTEGER PK | |
| servis_id | FK → servis_kayit | |
| stok_id | FK → stok_kart | kullanılan yedek parça |
| miktar / birim_fiyat / tutar | REAL | `tutar = miktar × birim_fiyat` |
| depo_id | FK → depo | **parçanın düşüleceği depo (K11)** — varsayılan Servis Yedek Parça deposu |
| aciklama | TEXT | |

### 1.3 Mevcut tablolara eklenen kolonlar (revizyon)
- `stok_kart.garanti_suresi_ay INTEGER NOT NULL DEFAULT 24`
- `stok_seri.garanti_baslangic TEXT`, `stok_seri.garanti_bitis TEXT`
- **`fatura.kaynak_servis_id INTEGER REFERENCES servis_kayit(id)`** — Servis → Fatura zinciri (K22/K8)
- **`servis_parca.depo_id INTEGER REFERENCES depo(id)`** — depo bazlı düşüm (K11)
- **`stok_kart.tip TEXT NOT NULL DEFAULT 'Urun'`** — `Urun` / `Hizmet`; servis işçiliği için stoksuz hizmet kalemi

### 1.4 `notlar` (Faz 1'den beri mevcut; Faz 3'te bağımsız ekran açıldı)
`ilgili_tablo, ilgili_id, metin, etiketler, hatirlatma, hatirlatildi, kullanici_id, created_at`

### 1.5 İndeksler
`idx_servis_durum`, `idx_servis_cari`

---

## 2) Finansal Etki Mimarisi (revize — Servis → Fatura zinciri, K22)

Eski davranış (kaldırıldı): "Teslim Edildi" doğrudan `cari_hareket`'e 690 TL borç yazıyordu
(`belge_tipi='Servis'`) — KDV'siz, K15 koruması dışında ve Fatura tablosuna hiç girmeyen bir kayıttı.

Yeni davranış (İrsaliye→Fatura deseniyle birebir aynı):

```
Servis "Teslim Edildi"
 ├─ 1) Parça stok düşümü  → stok_hareket "Servis Tüketimi" (−adet, servis_parca.depo_id'den)  [K11]
 └─ 2) Tutar > 0 ise      → fatura (Taslak, kaynak_servis_id → servis.id)                       [K8]
        ├─ parça satırları  : stok kartından (KDV stok kartından, iskonto K9)
        └─ işçilik satırı   : hizmet stok kartı (tip='Hizmet', HZM-SRV-ISCLK)
Fatura "Onaylandı"  → cari_hareket BORÇ (KDV dahil genel_toplam)                                 [K2/K6]
Fatura "İptal"      → cari hareket geri alınır                                                    [K15 deseni]
```

- Garanti kapsamında / ücretsiz serviste tutar 0 → fatura üretilmez, cari etki de olmaz.
- `POST /servis/{id}/faturala`: "Tamamlandı"/"Teslim Edildi" ama faturasız servisler için
  (K14 "faturasız irsaliye" deseni); listede "Faturasız" rozeti.
- Teslim geri alma engeli: aktif fatura veya parça varsa `Teslim Edildi`'den dönüş engellenir
  (önce fatura iptal edilmeli).

---

## 3) Ekran Listesi (rota → şablon)

| Rota | Yöntem | Ekran | Yetki |
|---|---|---|---|
| `/servis` | GET | Servis listesi (durum filtreli, "Faturasız" rozeti) | tüm roller |
| `/servis/yeni` | GET/POST | Yeni servis kaydı | Admin/Servis/Muhasebe |
| `/servis/{id}` | GET | Servis detayı (parçalar+depo, garanti, geçmiş, fatura kartı, notlar) | tüm roller |
| `/servis/{id}/durum` | POST | Durum geçişi (+ Teslim = stok düşümü + taslak fatura) | Admin/Servis/Muhasebe |
| `/servis/{id}/faturala` | POST | Faturasız servisi taslak faturaya dönüştür | Admin/Servis/Muhasebe |
| `/servis/{id}/guncelle` | POST | Teknisyen/işçilik/garanti/şube | Admin/Servis/Muhasebe |
| `/servis/{id}/parca` | POST | Yedek parça ekleme (+ depo seçimi) | Admin/Servis/Muhasebe |
| `/servis/parca/{pid}/sil` | POST | Parça silme | Admin/Servis/Muhasebe |
| `/garanti` | GET | Seri No-Garanti listesi (filtre, KPI) | tüm roller |
| `/garanti/yeni` | GET/POST | Yeni garanti kaydı | Admin/Muhasebe/Servis |
| `/garanti/{id}` | GET | Garanti detayı (satış + servis geçmişi) | tüm roller |
| `/garanti/{id}/guncelle` | POST | Garanti tarihlerini güncelle | Admin/Muhasebe/Servis |
| `/notlar` | GET | Not listesi (arama, etiket, hatırlatma filtresi) | tüm roller |
| `/notlar/yeni` | GET/POST | Yeni not (+ ilişkisel cari/servis/fatura) | tüm roller |
| `/notlar/{id}/sil` | POST | Not silme | tüm roller |

**Fatura detayı:** kaynak-servis izleme satırı eklendi (`🛠️ Kaynak servis: SRV-2026-xxx`).

**Dashboard:** "Açık Servis Kayıtları" + "Garanti Takibi" KPI'ları; `_garanti_tarama()` bildirim
taraması (süresi dolan → uyarı, ≤30 gün → bilgi).

**Seed (idempotent `seed_servis`):** 4 servis kaydı (BELGE-NNN Teslim Edildi · 002 Tamir Ediliyor
[450 TL işçilik + 240 TL kayış] · 003 Alındı · 004 Onay Bekliyor) + 1 yedek parça (depo_id=3);
satılan 3 seriye garanti 2026-06-01 → 2028-06-01; **hizmet stok kartı** `HZM-SRV-ISCLK`
(kategori "Hizmet", tip='Hizmet', KDV %20).

---

## 4) Örnek Test Senaryosu (modüller arası entegrasyon)

**Senaryo F3-1 — Garanti dışı servis teslimi (revize akış):**
1. Müşteri **Beyaz Eşya Tamir Atölyesi**'nden arızalı cihaz gelir; `/servis/yeni` ile kayıt açılır
   (durum **Alındı**).
2. Durum: Teşhis Edildi → Onay Bekliyor → Tamir Ediliyor.
3. `/servis/{id}/parca` ile **Vestel Çamaşır Makinesi Kayışı** (stok 7) 1 adet × 240 TL, **depo:
   Servis Yedek Parça** seçilir; işçilik 450 TL girilir.
4. Durum **Teslim Edildi** yapılır. Beklenen:
   - `stok_hareket` **"Servis Tüketimi" −1** (depo 3); stok 10 → 9. `cari_hareket` YAZILMAZ.
   - **Taslak Satış Faturası** oluşur (`kaynak_servis_id`): matrah 690 + KDV 138 = **828,00 TL**
     (parça + işçilik kalemleri ayrı; işçilik hizmet kartından).
5. Fatura **Onaylanır** → cari borç **828,00 TL** (KDV dahil). Fatura **İptal** edilirse borç
   geri alınır; iptal sonrası servis teslimi geri alınabilir.

**Senaryo F3-2 — Seri no ile garanti doğrulama:** (değişmedi) satılmış seri servise gelir → detayda
garanti bilgisi + servis geçmişi; `/garanti/{id}`'de ters yönde aynı geçmiş.

**Senaryo F3-3 — Garanti bildirimi:** (değişmedi) bitişi ≤30 gün kalan seri → dashboard bildirimi.

---

## 5) Çalıştırılmış Test Kanıtları (canlı uygulama, 2026-09-07 — REVİZE)

### Revizyon testleri (yeni mimari)
- **Teslim → cari hareket yazılmaz:** `POST /servis/2/durum → Teslim Edildi` sonrası
  `cari_hareket` **değişmedi** (19→19); `ilgili_modul='servis'` kayıt **0**.
- **Stok düşümü depo bazlı:** `stok_hareket` "Servis Tüketimi" −1, `depo_id=3`; `stok_seviye`
  (stok 7 / depo 3) **10 → 9**.
- **Taslak fatura:** `fatura.kaynak_servis_id=2` → **BELGE-NNN** Taslak; ara 690,00 + KDV
  **138,00** = genel **828,00**; kalemler = parça (stok 7, %20 KDV, 'Urun') + işçilik
  (HZM-SRV-ISCLK, %20 KDV, 'Hizmet').
- **Fatura onayı → mali etki:** onay sonrası cari **BORÇ 828,00 TL** (`belge_tipi='Satış Faturası'`).
- **Fatura iptali → geri alma:** iptal sonrası ilgili cari hareket **silindi** (0 kayıt).
- **Teslim geri alma engeli:** fatura varken `Teslim Edildi → Tamamlandı` denemesi **engellendi**
  (durum Teslim Edildi kaldı).
- **Faturala akışı:** "Tamamlandı" iken `POST /servis/2/faturala` → taslak fatura (690+138=828),
  stok düşümü YAPILMADI (faturala yalnız fatura üretir).
- **Garanti/ücretsiz:** BELGE-NNN (garantide, tutar 0) teslim → **fatura üretilmedi**; fatura/
  parça yok → teslim geri alınabildi (serbest).
- **Depo seçimi:** `servis_parca.depo_id=1` (Ana Depo) ile parça ekleme → `depo_id=1` kaydedildi.

### Önceki testler (değişmeyen alanlar)
- **Rota smoke:** 28 sayfa (Faz 1+2+3) **tamamı HTTP 200**.
- **Garanti hesaplama:** başlangıç 07.09.2026 + 12 ay → bitiş **07.09.2027** otomatik türetildi.
- **Not ilişkilendirme:** `ilgili_ref=servis_kayit|2` → `ilgili_tablo/ilgili_id` doğru ayrıştı.
- **Rol kontrolü:** `depo` kullanıcısı okuyabiliyor (200); `/servis/yeni`, `/garanti/yeni` **403**;
  `servis` rolü yazabiliyor (200).
- **Temiz seed korundu:** servis_kayit=4, servis_parca=1, fatura=3, cari_hareket=19,
  kasa_hareket=9, banka_hareket=7, bildirimler=6, doviz_kur=3, stok_hareket=18, stok_seri=18,
  notlar=0 (tüm test kayıtları silindi, `sqlite_sequence` sıfırlandı).

### Hata & düzeltme kaydı
- `_migrate` içinde `conn.execute` çoklu CREATE → `ProgrammingError`; `conn.executescript`'e çevrildi.
- `servis_durum` tesliminde `audit()` commit'ten önce çağrılıyordu → "database is locked";
  audit commit+close sonrasına alındı (K19.4). `db.get_conn`'a `busy_timeout=8000` + WAL eklendi.
- **Mimari revizyon (kullanıcı tespiti):** doğrudan `cari_hareket` yazımı kaldırıldı →
  K22 Servis → Fatura zinciri kuruldu (KDV'li taslak fatura + depo bazlı düşüm).

---

## 6) Onay

Revizyon uygulandı ve test kanıtlarıyla sunuldu. **Faz 3 tam onayı bekleniyor**; onay sonrası
**Faz 4 — e-Dönüşüm (e-Fatura/e-Arşiv, e-İrsaliye, Gelen Kutuları)** başlar.
