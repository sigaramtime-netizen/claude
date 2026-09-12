# E — CRM (Aktivite / Görev Takibi) · Faz Özeti (v1.30.0)

Tarih: 2026-09-11 · Paket: E — CRM · Kapsam: müşteri ilişkileri aktivite/görev takibi
(arama · toplantı · görev · takip) + cari/sorumlu bağlantısı + hatırlatma bildirimi.

Tasarım kararları (kullanıcı onaylı):
1. Kapsam: **sadece aktivite/görev takibi** (fırsat/huni ve teklif dönüşümü YOK).
2. Hatırlatma: **evet** — günü gelen hatırlatmalar bildirim merkezine düşer.

---

## 1) Veri Modeli Özeti

E paketi 1 yeni tablo getirir; başka tablo/migration yok (cari + kullanıcı FK ile bağlanır).

### Yeni tablo
| Tablo | Amaç | Kritik alanlar |
|---|---|---|
| `crm_aktivite` | Aktivite/görev kaydı | `aktivite_no` (AKT-YYYY-NNN), `tip` ∈ {Arama, Toplanti, Gorev, Takip}, `baslik`, `aciklama`, `cari_id`, `sorumlu_id` (kullanici), `tarih`, `saat`, `hatirlatma_tarihi`, `hatirlatildi`, `durum` ∈ {Planlandı, Tamamlandı, İptal}, `oncelik` ∈ {Dusuk, Normal, Yuksek}, `sube_id`, `sirket_id` |

### İş kuralları
1. **Doğrulama:** başlık + tarih zorunlu; `hatirlatma_tarihi ≤ tarih` zorunlu; cari ve sorumlu
   (kullanıcı) varlığı denetlenir; tip/durum/öncelik sabit kümelerle sınırlı (CHECK + rota).
2. **Durum akışı:** `Planlandı ↔ Tamamlandı` (tek tıkla geçiş) ve `İptal` (ayrı rota).
3. **Hatırlatma:** `_crm_aktivite_tarama` (app.py) günü gelen `hatirlatma_tarihi`'ni bildirime
   çevirir; `hatirlatildi` bayrağı aynı aktivite için mükerrer bildirimi engeller; düzenlemede
   bayrak sıfırlanır (yeni hatırlatma yeniden bildirilir).
4. **Silme:** aktivite silinirken `db.bildirim_sil("crm_aktivite", id)` ile ilişkili bildirimler
   de temizlenir; `db.bildirim_yetim_temizle` beyaz listesine `crm_aktivite` eklendi.
5. **K1 izolasyon:** her satır `sirket_id` + `sube_id` taşır; tüm sorgular `sirket_id` ile süzülür;
   çapraz şirketten detay/düzenleme erişimi engellenir.

### Varsayılanlar
- `seed_crm()` idempotent; 5 demo aktivite (BELGE-NNN…005): tahsilat görüşmesi (Yüksek,
  hatırlatmalı), teklif sunumu (Toplantı), aksiyon takibi, demo kurulumu (Görev), memnuniyet
  araması (Tamamlandı).
- Yeni numara `db.sonraki_belge_no` ile `AKT-<yıl>-<sıra>` üretilir.

---

## 2) Ekran Listesi

| Rota | Yöntem | Yetki | Açıklama |
|---|---|---|---|
| `/crm` | GET | herkes | Aktivite listesi (tip/durum/arama filtreleri + öncelik + günü geçti rozeti) |
| `/crm/yeni` | GET/POST | Admin·Satis·Servis | Yeni aktivite (tip, başlık, cari, sorumlu, tarih/saat, hatırlatma, durum, öncelik) |
| `/crm/<id>` | GET | herkes | Detay + durum/iptal/sil aksiyonları |
| `/crm/<id>/duzenle` | GET/POST | Admin·Satis·Servis | Düzenleme |
| `/crm/<id>/durum` | POST | Admin·Satis·Servis | Planlandı ↔ Tamamlandı |
| `/crm/<id>/iptal` | POST | Admin·Satis·Servis | İptal |
| `/crm/<id>/sil` | POST | Admin·Satis·Servis | Sil (bildirimlerle birlikte) |
| `/crm/rapor` | GET | herkes | Özet: bugün/yaklaşan/günü geçen + tip dağılımı + sorumlu bazında açık görevler |

**NAV:** "CRM (Müşteri İlişkileri)" grubu — Aktiviteler · Yeni Aktivite · CRM Raporu.
**Dashboard:** "CRM Aktiviteleri" KPI kartı (bugün · günü geçen).

---

## 3) Örnek Test Senaryosu (e2e — `test_crm.py`, 25 kontrol)

1. Liste render (demo aktiviteler + Türkçe tip/durum etiketleri).
2. Aktivite oluştur (AKT-YYYY-NNN, tip/durum/öncelik/cari doğru).
3. Doğrulamalar: boş başlık, hatırlatma > tarih, geçersiz cari, geçersiz sorumlu engeli.
4. Düzenleme (başlık/tip güncellenir).
5. Durum geçişi: Planlandı → Tamamlandı → Planlandı → İptal.
6. Hatırlatma → bildirim (dashboard taraması) + mükerrer üretim engeli.
7. Silme + ilişkili bildirimin temizlenmesi.
8. Rapor render.
9. Yetki: Depo/Muhasebe `/crm/yeni` 403; Satis izinli.
10. Şirket izolasyonu: 2. şirkette liste boş; çapraz şirket detay engeli.
11. Bütünlük: FK boş, yetim CRM bildirimi yok, POSTEST kalıntısı yok.

---

## 4) Doğrulama Kanıtı

- Test: `test_crm.py` **25/25** ✅ (tam regresyon: 14 paket / **313** kontrol yeşil, 0 başarısız).
- Ekran görüntüleri (`docs/ekran-goruntuleri/yeni-tema/`): `crm-aktiviteler`, `crm-yeni`,
  `crm-detay`, `crm-rapor`, `dashboard-e-crm` (20260911-105845).
- Örnek veri (seed'den, tekrarlanabilir): BELGE-NNN (Arama, Yüksek, hatırlatmalı),
  BELGE-NNN (Toplantı), BELGE-NNN (Takip), BELGE-NNN (Görev), BELGE-NNN (Tamamlandı).
- `data/erp.db` **sıfırdan temiz seed** ile üretildi: yetim fiş yok, FK boş, test artığı yok.
