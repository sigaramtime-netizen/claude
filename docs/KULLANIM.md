# Brn Teknoloji ERP — Kullanım Kılavuzu

**Elektronikçi İşletme Yönetim Sistemi · 22 modül / 6 faz**

Bu kılavuz sistemi nasıl **çalıştıracağınızı** ve **günlük olarak nasıl kullanacağınızı**
anlatır. Teknik değil, pratik bir rehberdir.

---

## 1) Sistemi çalıştırma

### Gereksinimler
- **Python 3.8+** (standart kütüphane yeterli)
- Ek paketler: **Jinja2** (şablon motoru) ve **openpyxl** (yalnızca Excel dışa aktarma için)

Kurulum (ilk kez):
```bash
pip install jinja2 openpyxl
```

### Başlatma
```bash
cd /home/user/erp
python3 app.py
```

Ekranda şunu görürsünüz:
```
* Brn Teknoloji ERP başlatılıyor: http://0.0.0.0:8080
```

Tarayıcıda açın: **http://localhost:8080**

> İlk açılışta örnek (seed) veriler otomatik yüklenir: örnek müşteriler, stok kartları,
> kasalar, 2 şube ve birkaç örnek belge. Gerçek kullanıma geçerken bu verileri silip/değiştirip
> kendi verinizi girebilirsiniz.

### Durdurma
Sunucunun çalıştığı terminalde **Ctrl+C**.

---

## 2) Giriş ve kullanıcılar

Demo kullanıcılar — **şifre hepsi `1234`**:

| Kullanıcı | Rol | Gördüğü şubeler |
|---|---|---|
| `admin` | Yönetici | Tüm şubeler, tüm yetkiler (yetki matrisi, bildirim ayarları) |
| `muhasebe` | Muhasebe | Tüm şubeler (muhasebe, beyanname, finansal analiz) |
| `satis` | Satış | Tüm şubeler (teklif→fatura zinciri) |
| `servis` | Servis Teknisyeni | Tüm şubeler (servis, garanti) |
| `depo` | Depo | **Yalnız Batman Merkez Şube** (şube izolasyonu örneği) |

> **Şube izolasyonu:** `depo` kullanıcısı Diyarbakır şubesinin kayıtlarını göremez,
> yazamaz (403 alır). `admin` her şeyi görür. Şubeli kullanıcı eklemek için **Depo/Şube**
> menüsünden kullanıcıyı şubeye bağlayın.

---

## 3) Arayüz turu

- **Sol menü** 6 bölümden oluşur: Genel · Çekirdek · Satış Döngüsü · Servis&Garanti ·
  e-Dönüşüm · Mali&Analitik.
- **Üst çubuk:** kullanıcı adı + rol, şube adı, 🔔 bildirim rozeti (okunmamış sayısı),
  🔑 **şifre değiştir** kısayolu.
- **Dashboard** (açılış ekranı): günlük KPI'lar, vadesi yaklaşan çek/senetler, vadesi geçen
  cari bakiyeleri, açık servis kayıtları.

---

## 4) Günlük iş akışları (modül modül)

### Satış zinciri (en önemli akış)
```
Teklif → Sipariş → İrsaliye → Fatura → e-Fatura/e-Arşiv → Cari/Kasa/Banka → Muhasebe
```

1. **Cari** (`/cari`): Önce müşteri/tedarikçi kartı açın. Bakiyesi otomatik işler.
2. **Teklif** (`/teklif`): Müşteriye fiyat teklifi. Onaylanan tekliften **Sipariş** türetilir.
3. **Sipariş** (`/siparis`): Onaylı siparişten **İrsaliye** türetilir.
4. **İrsaliye** (`/irsaliye`): Mal çıkışı → **stok düşer**. İrsaliyeden **Fatura** türetilir.
5. **Fatura** (`/fatura`): Onaylanınca → **cari borç/alacak + stok + muhasebe yevmiyesi**
   hepsi otomatik işler. "Yazdır" ile PDF çıktısı.
6. **e-Fatura / e-Arşiv** (`/edonusum`): Fatura **Gönderildi/Onaylandı** olana kadar e-belge
   sürecinde takip edilir (mock entegratör; gerçek sağlayıcı ayarlardan bağlanır).

> **Manuel (serbest metin) satır:** İrsaliye ve Fatura'da, stok seçmeden **"+ Manuel Satır"**
> çubuğuyla açıklama + miktar + fiyat + KDV + iskonto girerek satır ekleyebilirsiniz (örn.
> kargo, nakliye, montaj hizmeti). Bu satır **stoğa dokunmaz** (stok hareketi üretmez), yalnız
> belge toplamına girer. Muhasebede: satışta 600'a, alışta **770 Genel Yönetim Giderleri**'ne
> yazılır (stoklu alış satırı 153'te kalır). Transfer irsaliyesinde manuel satır kullanılamaz.

### Tahsilat / Ödeme
- **Kasa** (`/kasa`): Tahsilat → müşteri borcu **düşer**, kasa **artar** (tek işlem, otomatik
  yevmiye). Ödeme → borç/alacak yönüne göre.
- **Banka** (`/banka`): Aynı mantık banka hesapları için. Kasa↔Banka aktarımı **Transfer**
  menüsünden.

### Çek / Senet (`/cek_senet`)
- Verilen/alınan çek-senetler; **vade takvimi** ve **vadesi yaklaşan uyarısı** otomatik.
- Durumlar: Beklemede → Tahsil Edildi / Tahsile Verildi / Karşılıksız (karşılıksızda tahsil
  geri alınır).

### Servis & Garanti
- **Servis Takip** (`/servis`): Cihaz kabul → Arıza → Onarım → **Tamamlandı** (müşteriye
  "cihazınız hazır" bildirimi gider) → Teslim. Tamamlanınca fatura türetilebilir.
- **Seri No - Garanti** (`/garanti`): Garanti süresi otomatik; dolan garantiler uyarı üretir.

### Stok & Depo
- **Stok** (`/stok`): Stok kartları, kritik seviye uyarısı.
- **Stok2 · Depo/Transfer** (`/stok/depolar`): Depolar arası transfer.
- **Depo/Şube** (`/sube`): Şube, depo, kasa tanımları; kullanıcı-şube atama.

### Mali & Analitik (aylık / dönemsel)
- **Genel Muhasebe** (`/muhasebe`): Yevmiye, mizan, defter. Fatura/kasa/banka/çek-senet/demirbaş
  otomatik fiş üretir — **elle çifte kayıt gerekmez**.
- **Demirbaş** (`/demirbas`): Sabit kıymetler; aylık amortisman **otomatik** yevmiye üretir
  (770/257).
- **Beyanname** (`/beyanname`): KDV, Geçici Vergi taslakları (salt-okunur, tahmini).
- **Finansal Analiz** (`/finansal`): Kârlılık, nakit, bütçe, ürün/tahsilat analizleri.
- **Kartoteks** (`/kartoteks`): Tüm stok hareketlerinin salt-okunur geçmişi; barkod hızlı
  sorgu + Excel/CSV/PDF dışa aktarma.

### Döviz (`/doviz`)
- USD/EUR/GBP kurları; **TCMB'den güncelle** butonu güncel kur çeker.

### Bildirimler (`/bildirimler`)
- Stok azaldı · çek/senet vadesi · garanti doldu · ödenmemiş cari bakiyesi · not hatırlatması
  gibi uyarılar burada toplanır.

### Ayarlar — Sistem Yönetimi (`/ayarlar`, yalnız Admin)
Sol menüdeki **Yönetim → Ayarlar** tüm sistem yönetimini tek yerde toplar:

- **👥 Kullanıcı Yönetimi** (`/ayarlar/kullanicilar`)
  - Yeni kullanıcı ekleme (kullanıcı adı, ad-soyad, e-posta, rol, şube, ilk şifre)
  - Rol değiştirme (tablodan anında)
  - **Aktif/Pasif** — silme yerine pasifleştirme; geçmiş (audit) kayıtları korunur
  - **Şifre sıfırlama** (şifresini unutan kullanıcı için yeni şifre belirleyin)
- **🏢 Firma Bilgileri** (`/ayarlar/firma`) — ünvan, adres, vergi dairesi/no, telefon,
  e-posta, logo; belge antetlerinde (yazdırma/PDF) kullanılır.
- **📡 Bildirim Kanalı** (`/ayarlar/bildirim`) — SMS/e-posta kanalı seçimi (varsayılan
  **kapalı**; mock sağlayıcı) + gönderim günlüğü.
- **🔌 e-Belge Entegratörü** (`/ayarlar/entegrator`) — GİB entegratör bağlantısı
  (Mock/Sandbox aktif; gerçek API anahtarı gelince buradan).
- **Tanımlar (hızlı erişim):** Şube/Depo, Kasalar, Banka Hesapları, Yetki Matrisi.

> Eski yollar (`/bildirimler/ayarlar`, `/edonusum/ayarlar`) artık bu ekranlara yönlendirir.

### Şifre değiştirme (`/profil/sifre`, tüm kullanıcılar)
Üst çubuktaki **🔑** simgesinden her kullanıcı **kendi şifresini** değiştirebilir
(mevcut şifre + yeni şifre). Yeni şifre **en az 8 karakter ve bir rakam** içermelidir.

---

## 5) Sık sorulanlar

**S: Veri nereye kaydediliyor?**
`data/erp.db` — tek SQLite dosyası. Bu dosya tüm sistemin kaynağıdır.

**S: Yedek nasıl alınır?**
```bash
python3 yedek_al.py yedek 30          # son 30 yedeği saklar
python3 yedek_al.py /mnt/yedek 30     # harici disk hedefi (önerilir)
```
Yedek, uygulama çalışırken bile **tutarlı** alınır ve **bütünlük doğrulanır** (bozuksa uyarı
verir). Haftalık cron örneği betiğin başındaki açıklamada.

**S: Belge numaraları nasıl oluşur?**
Otomatik: `{ÖNEK}-{YIL}-{SIRA}` (örn. `BELGE-NNN`).

**S: Yazdır/PDF nasıl?**
Belge detayında **Yazdır** → tarayıcıdan "PDF olarak kaydet".

**S: Şifremi unuttum?**
Yöneticiden (**Ayarlar → Kullanıcılar → 🔑 Sıfırla**) yeni şifre belirlemesini isteyin.
Demo kullanıcıların varsayılan şifresi `1234`'tür; uygulamadan yeni/sıfırlanan şifreler
en az 8 karakter ve bir rakam olmalıdır.

**S: Mobilde çalışır mı?**
Evet; tablet ve telefonda da kullanılabilir (responsive tasarım).

**S: Şifreler nasıl saklanıyor?**
PBKDF2-HMAC-SHA256 (tuzlu, 600.000 yineleme) ile hash'lenir; düz metin olarak hiçbir yerde
tutulmaz. Eski formattaki (salted SHA-256) hash'ler girişte otomatik PBKDF2'ye yükseltilir.

---

## 6) Güvenlik & roller (özet)

- Her işlem **audit log**'a yazılır (kim, ne, ne zaman).
- Rol bazlı erişim: `admin` her şey; diğer roller kendi işlerine göre sınırlı.
- **Ayarlar** menüsü (kullanıcı/firma/bildirim/entegratör) yalnız Admin'e açık;
  **şifre değiştirme** herkesin kendi hesabı için açık.
- **Yetki Matrisi** ekranı (`/yetkiler`, yalnız Admin) hangi rolün hangi rotada yetkili
  olduğunu listeler.
- Şubeli kullanıcı yalnız kendi şubesini görür/yazar.
- Şifreler PBKDF2 ile hash'li saklanır; kullanıcı silme yok — pasifleştirme var
  (audit geçmişi kopmaz).
