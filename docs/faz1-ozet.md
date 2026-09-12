# Faz 1 — Çekirdek: Cari Modülü (Özet & Onay)

> Bu dosya, proje komutundaki "her fazın sonunda veri modeli özeti + ekran listesi +
> örnek test senaryosu üret ve onay iste" kuralı gereği hazırlanmıştır.

---

## 1) Bu fazda ne yapıldı?

- Proje iskeleti kuruldu: kendi WSGI çekirdeği, SQLite şeması, oturum + rol denetimi,
  audit log, bildirim altyapısı, koyu/duyarlı (responsive) tema, Türkçe arayüz.
- **Cari modülü** uçtan uca çalışır durumda teslim edildi.
- Örnek (seed) veri yüklendi: 5 kullanıcı, 1 firma, 9 cari grubu, 8 cari kartı,
  15 cari hareketi, örnek bildirimler.

---

## 2) Veri Modeli (tablolar)

| Tablo | Amaç | Kritik Alanlar |
|---|---|---|
| `kullanici` | Kullanıcı ve roller | kullanici_adi, sifre_hash, rol (Admin/Muhasebe/Satis/Servis/Depo) |
| `sessionler` | Oturum | token, kullanici_id |
| `firma` | İşletme bilgisi (fatura alt bilgisi için) | unvan, vergi_dairesi, vergi_no, logo |
| `cari_grup` | Bölge/Segment/Sadakat grupları | ad, tip, aciklama |
| `cari_kart` | Müşteri & tedarikçi kartı | kod, unvan, tip, vergi_no/tckn, il/ilce, kredi_limiti, para_birimi, iskonto_orani, grup_id |
| `cari_hareket` | Borç/alacak hareketleri | cari_id, tarih, vade, belge_tipi, belge_no, borc, alacak, ilgili_modul/ilgili_kayit_id |
| `notlar` | İlişkisel notlar (cari/fatura/servis) | ilgili_tablo, ilgili_id, metin, etiketler, hatirlatma, hatirlatildi |
| `audit_log` | Kim/ne zaman/ne değiştirdi | kullanici_adi, tablo, kayit_id, islem, detay |
| `bildirimler` | Uyarı sistemi | tip, baslik, mesaj, ilgili_tablo, okundu |
| `meta` | Şema sürümü vb. | anahtar, deger |

**Kurallar / İş mantığı:**

- Bakiye = Σborç − Σalacak. Yaşlandırma **FIFO** ile hesaplanır: ödemeler (alacak)
  en eski vadeden başlayarak kapatılır; kalan açık kalemler vade gününe göre
  0-30 / 31-60 / 61-90 / 90+ dilimlerine ayrılır.
- Kredi limiti aşımı ve vadesi geçen alacak için kartta ve dashboard'da otomatik uyarı.
- Notlardaki `#etiket`'ler ayrıştırılır; `hatirlatma` tarihi gelince bildirim üretilir.

---

## 3) API Uçları (route listesi)

| Metod | Yol | Yetki | İşlev |
|---|---|---|---|
| GET | `/cari` | giriş | Filtreli + sayfalı cari listesi |
| GET/POST | `/cari/yeni` | Admin, Muhasebe, Satış | Yeni cari kartı |
| GET | `/cari/rapor` | giriş | Yaşlandırma raporu (tüm cariler) |
| GET/POST | `/cari/gruplar` | Admin, Muhasebe, Satış | Grup listesi + yeni grup |
| GET | `/cari/{id}` | giriş | Kart detayı (bilgi/hareket/not/audit sekmeleri) |
| GET | `/cari/{id}/ekstre` | giriş | Hesap ekstresi (tarih aralıklı, yürüyen bakiye) |
| GET/POST | `/cari/{id}/hareket` | Admin, Muhasebe, Satış | Manuel borç/alacak hareketi |
| GET/POST | `/cari/{id}/duzenle` | Admin, Muhasebe, Satış | Kart güncelleme |
| POST | `/cari/{id}/not` | giriş | İlişkisel not ekle |

Ayrıca: `GET /` (dashboard), `GET/POST /giris`, `GET /cikis`, `GET /bildirimler`,
`GET /bildirimler/{id}/oku`, `GET /saglik`.

---

## 4) Ekran Listesi

1. **Giriş** — demo kullanıcı bilgileriyle.
2. **Dashboard** — günlük satış, toplam cari alacak, vadesi geçen, kritik uyarılar,
   faz durumu, cari hızlı bakış.
3. **Cari Listesi** — tip sekmeleri, arama/filtre, bakiye/vade/kredi kolonları.
4. **Cari Kartı** — 4 sekme: Bilgiler, Hareketler, Notlar, Geçmiş (audit).
5. **Cari Ekstresi** — KPI'lar (bakiye, toplam borç/alacak, limit), yaşlandırma,
   tarih aralıklı yürüyen bakiyeli hareket listesi.
6. **Hareket Ekle** — borç/alacak yönü, belge tipi, vade.
7. **Yaşlandırma Raporu** — tüm carilerin vade dilimi özeti.
8. **Cari Grupları** — grup listesi + ekleme.
9. **Bildirimler** — okundu işaretleme.

---

## 5) Örnek Test Senaryosu

1. `admin / 1234` ile giriş yap.
2. **Yeni cari:** Cari → Yeni Cari → unvan "Diyarbakır Bayi A.Ş.", tip Müşteri,
   kredi limiti 75.000 ₺ → Kaydet. Kod otomatik `CAR-00X` üretilir.
3. **Hareket:** karta gir → Ekstre → +Hareket Ekle → Tarih bugün, belge "Satış Faturası",
   yön "Borç", tutar 40.000 ₺, vade +30 gün → Kaydet. Bakiye 40.000 ₺ olur.
4. **Tahsilat:** +Hareket Ekle → belge "Tahsilat", yön "Alacak", 15.000 ₺ → bakiye 25.000 ₺.
5. **Doğrulama:** Ekstrede yürüyen bakiye kolonu sırayla 40.000 → 25.000 gösterir;
   yaşlandırma kutuları ve dashboard "Toplam Cari Alacak" güncellenir.
6. **Kredi limiti uyarısı:** aynı cariye 60.000 ₺ daha borç yaz → kartta ve listede
   "limit aşımı" rozeti belirir.
7. **Not + hatırlatma:** kart → Notlar → "`#tahsilat` haftaya ara", hatırlatma yarın →
   dashboard'da ertesi gün bildirim düşer.
8. **Yetki:** `servis / 1234` ile gir → cari listesi açılır, "Yeni Cari" 403 verir.
9. **Audit:** kart → Geçmiş sekmesinde tüm oluşturma/güncelleme kayıtları görünür.

---

## 6) Sonraki Adım (onay bekleniyor)

Faz 1'in kalan modülleri: **Stok/Stok2, Kasa, Banka, Depo/Şube** — aynı iskelet üzerinde
aynı desenle (tablo + CRUD + ekran + entegrasyon) eklenecek. Onay verirsen **Stok**
modülünden devam ederim.
