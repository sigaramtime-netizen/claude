# BRN Teknoloji ERP — Final Kabul & Prod Checklist

**Sürüm:** v1.38.0 — F6 Son Cila (D006 ONAYLANDI)  
**Commit:** `51f8ec5 [GM] D006 ONAYLANDI — F6 v1.38.0 18/18+496/496`  
**Tarih:** 2026-09-12 (Europe/Istanbul)  
**Branch:** `main` — `origin/main` senkron  
**DB:** `kod/data/erp.db` (SQLite, 67 tablo, FK0)  
**Durum:** Faz 1-6 tamam — **KABUL TESTİNE HAZIR**

> GM notu kral: Bu belge prod'a çıkmadan önceki son kapıdır. Buradaki her tik atılmadan canlıya alma yok. Eksik görürsen direkt yaz, acımam düzeltiriz.

---

## 1) Kapsam Özeti (Ne Teslim Edildi?)

### Fazlar
| Faz | Kod | İçerik | Test |
|-----|-----|--------|------|
| F1 | Çekirdek | Teklif→Sipariş→İrsaliye→Fatura zinciri, otomatik yevmiye, cari/kasa/banka, K1 sirket + sube izolasyon | `test_f1_mali 25` |
| F2 | KDV | `kdv_ayikla / kdv_hesapla`, dahil/hariç tek kaynak, mizan denge | `test_f2_kdv 34` |
| F3 | Arama | `/api/ara` tek endpoint (stok/cari), typeahead 11 şablon, limit 20 | `test_f3_arama 30` |
| F4 | e-Dönüşüm | Mock EDM entegratör, `/edonusum + /e-fatura + /e-irsaliye + /gelen`, GİB durum makinesi, gelen→Alış dönüşüm (manuel satır dahil) | `test_f4_edonusum 22` |
| F5A | Finansal | `butce_hedef` (K1 UNIQUE), 6 kart dashboard, `/api/finansal/ozet`, nakit akış, en çok satan/karlı | `test_f5a_finansal 18` |
| F5B | Demirbaş | Kategori özet, 12 ay amortisman plan, birikmiş çizgi SVG, `/api/demirbas/ozet` + CSV + zimmet | `test_f5b_demirbas 18` |
| F5C | Beyanname | 4 KPI kart, KDV oran bar SVG, `/api/beyanname/ozet` (12 satır devreden + geçici ç3 + nakit), KDV/denetim CSV | `test_f5c_beyanname 18` |
| F6 | Cila | `/api/bildirimler` + `/yetkiler/csv` + ortak `yazdir/belge.html` + `/api/sube/ozet` + `/api/saglik` | `test_f6_cila 18` |

**Toplam regresyon:** 22 test dosyası, **496/496** (tümü canlı HTTP, 127.0.0.1:8080).  
**Yeni tablo yok (F6):** sadece `core.yazdir_belge()` helper + 5 route. 67 tablo korunuyor.

### 22 Modül Kontrol Listesi
| # | Modül | Rota Örnek | Durum |
|---|-------|------------|-------|
| 1 | Cari | `/cari` | ✅ |
| 2 | Stok / Stok Varyant | `/stok` | ✅ |
| 3 | Kasa | `/kasa` | ✅ |
| 4 | Banka | `/banka` | ✅ |
| 5 | Depo / Şube | `/sube` + `/api/sube/ozet` | ✅ |
| 6 | Teklif | `/teklif` | ✅ |
| 7 | Sipariş | `/siparis` | ✅ |
| 8 | İrsaliye | `/irsaliye` + `/irsaliye/:id/yazdir` | ✅ |
| 9 | Fatura | `/fatura` + `/fatura/:id/yazdir` | ✅ (POS dahil) |
| 10 | Çek-Senet | `/cek_senet` | ✅ |
| 11 | Döviz | `config.PARA_BIRIMLERI TRY/USD/EUR/GBP` | ✅ |
| 12 | Servis | `/servis` | ✅ |
| 13 | Garanti | `/garanti` | ✅ |
| 14 | Notlar | `/notlar` | ✅ |
| 15 | e-Fatura / e-Arşiv | `/e-fatura` + `/edonusum` | ✅ Mock |
| 16 | e-İrsaliye | `/e-irsaliye` | ✅ Mock |
| 17 | Gelen Kutuları | `/gelen` , `/e-fatura/gelen` | ✅ |
| 18 | Genel Muhasebe | `/muhasebe` (mizan, yevmiye) | ✅ |
| 19 | Beyanname | `/beyanname` | ✅ |
| 20 | Demirbaş | `/demirbas` | ✅ |
| 21 | Kartoteks | `/kartoteks` | ✅ |
| 22 | Transfer / Sayım | `/stok/transfer` | ✅ |
| + | Finansal Analiz | `/finansal/butce` | ✅ |
| + | POS | `/pos` | ✅ |
| + | CRM / Bakım | `/crm` , `/bakim` | ✅ |

---

## 2) Prod'a Çıkış Öncesi — Teknik Checklist

### A. Kod & Sürüm
- [ ] `kod/config.py` → `SURUM = "1.38.0"` , `SURUM_TARIHI` güncel
- [ ] `git log --oneline` → son 3 commit: `51f8ec5 D006 ONAYLANDI` → `c937bdc CODER F6` → `4551ee0 GM direktif`
- [ ] `git status` → clean (sadece `data/erp.db` ve `uploads/` gitignore'da)
- [ ] `python3 -c "import db; db.init_db(); print('ok')"` → FK0, 67 tablo
- [ ] `grep -r "WOLVOX" --include="*.py" --include="*.html"` → 0 (marka taklidi yok)

### B. Güvenlik
- [ ] 5 Rol: `Admin / Muhasebe / Satis / Servis / Depo` — `ALL_ROLES` korunuyor
- [ ] `ROUTES` tablosu yetki matrisinde her route `roles=()` doğru (yetkisiz 403, şirket dışı 302)
- [ ] Login: `POST /giris` → hash'li şifre (düz metin yok), session `HttpOnly` cookie
- [ ] K1 izolasyon: `db.sirket_id(req)` her sorguda WHERE `sirket_id=?` (cari, stok, fatura, kasa, yevmiye, bildirim, gelen_belge, entegrator_ayar)
- [ ] Şube izolasyon: `izole_sube(req)` + `sube_koruma()` — `/fatura/:id/yazdir` 403, liste filtreli
- [ ] `SECRET` / `api_anahtar` env'den geliyor, repo'ya commitlenmedi
- [ ] `uploads/` + `data/` klasörleri web'den direkt erişilemez (nginx `deny`)
- [ ] CSRF: form POST'ları `origin` kontrolü / token (varsa) aktif

### C. Veri & Muhasebe Bütünlüğü
- [ ] Altın kural: Teklif→Sipariş→İrsaliye→Fatura tek zincir, çifte yevmiye yok — `test_f1_mali 25/25`
- [ ] KDV tek kaynak `core.kdv_ayikla` — dahil/hariç net aynı → `test_f2_kdv 34/34`
- [ ] Mizan dengesi: `borç == alacak` her kapanışta (ör. 971960.44) — manuel satır testinde de dengeli
- [ ] Stok seviye: `stok_seviye.miktar` seed'e eşit mi? (id5 BUZ 8.0, id1 TV 10.0, …) — F4 temizliğinde seviye geri alınmama notu düzeltildi
- [ ] FK bütünlüğü: `PRAGMA foreign_key_check` → 0 satır (tüm F* testlerinde)
- [ ] Silme kuralları: Onaylı belge silinemez, bağlı fatura varken irsaliye iptal engeli, amortisman varken demirbaş silinemez — `test_silme_kurallari 23/23`
- [ ] Döviz: `para_birimi + doviz_kur` zincirde sabit (Teklif USD 30.0 → SAP'ye sabit)

### D. Altyapı & Deployment
- [ ] Python 3.11+ , `pip install -r requirements.txt` (veya `pyproject.toml`) sorunsuz
- [ ] `PORT` env okunuyor (`config.PORT = int(os.environ.get("PORT",8080))`), `HOST=0.0.0.0`
- [ ] Prod server: `gunicorn app:app -w 4 -b 0.0.0.0:8080` veya `systemd` servisi (`Restart=always`)
- [ ] Reverse proxy: Nginx → `proxy_pass http://127.0.0.1:8080`, `client_max_body_size 20M` (ek_dosya)
- [ ] HTTPS: Let's Encrypt sertifika, HTTP→HTTPS redirect, HSTS
- [ ] Dosya izinleri: `chmod 640 data/erp.db`, `chmod 750 uploads/`, `chown app:app`
- [ ] `data/` ve `uploads/` ayrı volume / mount (dokunulmaz backup)

### E. Yedekleme & Geri Alma
- [ ] Günlük cron: `0 2 * * * sqlite3 /opt/erp/kod/data/erp.db ".backup /backup/erp-$(date +\%F).db"`
- [ ] Haftalık `uploads/` tar: `tar czf /backup/uploads-$(date +\%F).tar.gz /opt/erp/kod/uploads`
- [ ] Retantion: 30 gün günlük + 12 ay aylık
- [ ] Restore tatbikatı yapıldı: `.restore` ile 1.1M DB < 5 sn açılıyor, `PRAGMA integrity_check` ok
- [ ] `DB_PATH` ve `UPLOAD_DIR` env ile override edilebilir (12-factor)

### F. İzleme & Sağlık
- [ ] `/saglik` → `{"durum":"ok"}` (anonim), `/api/saglik` → `{"surum":"1.38.0","db":"ok","sirket_id":1}` (auth'lu)
- [ ] Uptime check: her 60 sn `curl -f https://erp.brnteknoloji.com/saglik` → alert (Telegram/Email)
- [ ] Log: `app.py` stdout → `journalctl -u erp` + `logrotate` (günlük, 14 gün)
- [ ] `audit_log` tablosu doluyor mu? `SELECT COUNT(*) FROM audit_log` > 0
- [ ] `bildirim` üretimi: `POST /fatura/yeni` → bildirim satırı (tip uyari/bilgi)
- [ ] Disk: `df -h` / `du -sh data/ uploads` alarm eşiği %80

### G. Performans & Limitler
- [ ] `/api/ara?tip=stok&q=BUZ` → < 200 ms, limit 20 (30 stokta 20 döner)
- [ ] Liste sayfaları pagination / `ORDER BY id DESC` indexli
- [ ] `ek_dosya` XML yazımı `UPLOAD_DIR` + `ek_dosya` tablosu (K16) — büyük dosya 10 MB altı
- [ ] `stok_kart` barkod araması `idx` var

### H. Entegratör (Mock → Gerçek Geçiş Notu)
- [ ] Şu an **MockEntegrator** (`test_modu=1` → Gönder→Onaylandı anında). Gerçek EDM/İzibiz için `entegrator_ayar` tablosuna `api_anahtar` + `entegrator=EDM` yaz, `test_modu=0` yap
- [ ] Mock hinti: `/ayarlar/edonusum` → "simülasyon / sandbox / bağlanmaz" metni görünüyor — prod'da gerçek entegratörde kaybolur
- [ ] Gelen kutusu `/_gelen_aktar` dedup `belge_no + sirket_id` ile

### I. Dokümantasyon
- [ ] `docs/F6-cila-ozet.md`, `docs/F5C-...`, `kanitlar/v1.38.0/*` güncel ve commitli
- [ ] `DURUM.md` → D006 ONAYLANDI mühürlü
- [ ] Kurulum adımları README'de: `git clone → pip install → python -m db.init_db → python app.py`

---

## 3) Kabul Testi — Senin Yapacakların (Kral, sıra sende)

### Hazırlık (2 dk)
```bash
git pull origin main
python3 -c "import db; db.init_db(); print('db ok')"
python3 kod/app.py   # veya prod: systemctl start erp
curl -s http://127.0.0.1:8080/saglik
curl -s http://127.0.0.1:8080/api/saglik -b cookie.txt  # login sonrası
```

Login: `admin / 1234` (roller: Admin, Muhasebe, Satis, Depo, Servis — test için kullanıcıyı `/ayarlar/kullanicilar`'dan değiştir)

### Smoke Turu (15 dk — her modüle 1 dokunuş)
1. **Cari** → yeni müşteri ekle → listede gör → sil (referanssız ise silinir)
2. **Stok** → TV ekle → barkod `8691234500011` ile ara (`/api/ara?tip=stok&q=8691`) → POS'ta görünüyor mu
3. **Teklif→Sipariş→İrsaliye→Fatura→e-Fatura** → tam zinciri 1 müşteride döndür, mizanı kontrol et
4. **Kasa/Banka** → hareket ekle → mizan `100 KASA / 102 BANKA` değişti mi → şirket B'de görünmüyor mu (K1)
5. **Çek-Senet** → alınan çek → tahsil → yevmiye oluştu mu
6. **Servis + Garanti + CRM + Bakım** → 1 kayıt aç → bildirim düştü mü (`/api/bildirimler`)
7. **Demirbaş** → `DBR-...` ekle → amortisman üret → plan tablosu 12 ay + SVG grafik + CSV indir
8. **Beyanname** → 4 kart + bar grafik + `/api/beyanname/ozet` devreden 12 satır + KDV CSV + denetim CSV
9. **F6 yenilikler:**
   - `/api/bildirimler?tip=uyari` filtre
   - `/yetkiler` → tablo görünüyor mu, `CSV indir` → 255 satır
   - `/fatura/1/yazdir` → şık A4, Yazdır düğmesi, `@media print`te düğme kayboluyor mu
   - Şirket B'ye geç → A faturasını yazdır → **302** mi
   - `/api/sube/ozet` → 2 şube, `fatura_adet + kasa_bakiye`
   - `/api/saglik` → surum 1.38.0

### Derin Tur (30 dk — para konuşur)
- **Manuel satır:** Faturaya `Kargo Ücreti 200 ₺` manuel satır ekle → 600 tek satır + 120/391 doğru mu, stok düşmedi mi
- **Transfer irsaliye:** Depo 1→2 transfer → stok 1 depo1 -5 depo2 +5
- **Döviz:** USD teklif kur 30 → SAP'ye kur sabitlendi mi
- **İptal kilitleri:** Onaylı irsaliyeden fatura varken irsaliye iptal → engel mesajı
- **K1 izolasyon:** Şirket B'de A'nın carisi / stoku / faturası görünmüyor, `/api/cari/ara` dönmüyor

---

## 4) Hata Bildirimi — Nasıl Yazacaksın?

Her bulduğun sorun için **tek mesajda şu formatta** at (kopyala-yapıştır):

```
[BUG-00] Başlık: Fatura yazdır K1 bypass
Şiddet: Yüksek / Orta / Düşük
Rol: Depo
Şirket: A (1) → B (2) geçiş sonrası
Adımlar:
 1. Admin ile giriş
 2. /fatura/5/yazdir aç
 3. Şirket B'ye geç, aynı URL'yi aç
Beklenen: 302 / 403
Gerçek: 200 ve belge görünüyor
Ek: ekran görüntüsü + curl -i http://.../fatura/5/yazdir (header)
DB: stok_seviye id5=?
```

**Şiddet rehberi:**
- **Kritik:** Para/mizan bozulması, FK hatası, şirket verisi sızması, açık yetki bypass
- **Yüksek:** Zincir kırılması (Sipariş→İrsaliye engeli yok), KDV yanlış, e-belge çifte üretim
- **Orta:** UI bozuk, CSV eksik, grafik render yok, bildirim düşmüyor
- **Düşük:** Yazım, renk, hizalama

**İstenecek ekler (varsa):** `curl -i`, `sqlite3 data/erp.db "SELECT ..."` çıktısı, browser console hatası.

> WOLVOX uyarısı: Ekranlarda/logo'da WOLVOX benzerliği yok — marka taklidi kontrolü prod'da da korunacak.

---

## 5) Bilinen Notlar & Kısıtlar

- e-Dönüşüm **Mock** — gerçek GİB entegrasyonu için `entegrator_ayar` + gerçek sertifika gerekir; test modu KAPALI iken `Gönderildi` durum sorgusu gerekir.
- Stok seviye drift: F4 temizlik helper'ı `DELETE FROM stok_hareket` ile seviye düzeltmez; GM 2026-09-12'de seed'e resetlendi (8.0). Prod'da normal iptal yolu `yon=-1` ile seviye geri alınır, sorun yok.
- Upload XP: `uploads/` 20MB üstü dosya nginx'te kesilir — büyük XML için artır.
- SQLite prod: eşzamanlı yazma < 50 req/s için ideal; yüksek trafikte Postgres'e geçiş planla (db.py soyut).

---

## 6) Onay Kutusu

| Rol | İsim | Tarih | İmza |
|-----|------|-------|------|
| GM (Teknik) | — | 2026-09-12 08:55 | ✅ D006 mühürlendi |
| Ürün Sahibi (Kral) |  |  | ☐ Kabul / ☐ Şerhli kabul |
| Muhasebe |  |  | ☐ |
| Satış |  |  | ☐ |

**Karar:**
- [ ] **KABUL** — prod'a alınır (yedek + izleme aktif)
- [ ] **ŞERHLİ KABUL** — düşük/orta buglarla alınır, fix takvimi ekte
- [ ] **RED** — kritik bug var, D007 revizyon açılır

---

## 7) Prod'a Alma Komutları (Kopyala-Yapıştır)

```bash
# sunucuda
cd /opt/BRN-Teknoloji-ERP
git pull origin main
python3 -m pip install -r requirements.txt
python3 -c "import db; db.init_db(); print('init ok')"
# yedek
cp kod/data/erp.db /backup/pre-prod-$(date +%F).db
# servis
sudo systemctl restart erp
sleep 3; curl -s https://erp.brnteknoloji.com/saglik
curl -s https://erp.brnteknoloji.com/api/saglik -H "Cookie: $(cat /tmp/cookie)"
sudo journalctl -u erp -n 50 --no-pager
```

**Rollback (30 sn):**
```bash
sudo systemctl stop erp
cp /backup/pre-prod-2026-09-12.db kod/data/erp.db
sudo systemctl start erp
```

---

> Kral, bu checklist'i tikleyip bana `KABUL` veya `BUG-XX` ile dön. Ben de her bug'ı aynı gün D007 olarak coder'a direktifleyip, fix'i aynı pipeline ile (test + kanit + FK0 + push) mühürleyeceğim. Prod candır, şakası yok.
