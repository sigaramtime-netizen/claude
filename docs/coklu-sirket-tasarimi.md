# Çoklu Şirket — Tasarım Önerisi (İstek 3)

> Durum: **ONAY BEKLİYOR** — 3 soru cevaplanmadan kodlama başlamaz.

## Mevcut durum

- Uygulama tek bir firma üzerine kurulu: `firma` tablosu (tek satır), tüm tablolar tek DB
  (`data/erp.db`) içinde; izolasyon yalnızca **şube** (`sube_id`, K1) ile yapılıyor.
- Cari kartlar bilinçli olarak ortak (şube izolasyonuna tabi değil).
- Tüm sorgular tek `sube_id` filtresiyle çalışıyor.

## İki temel mimari seçeneği

### Seçenek A — Tek DB + `sirket_id` (üst tablo + her tabloya kolon)

| Artılar | Eksiler |
|---|---|
| Tek yedek, tek migrasyon, tek bağlantı | Her tabloya `sirket_id` kolonu + her sorguya filtre (büyük ama mekanik değişiklik) |
| Şirketler arası konsolide raporlar (ör. tüm şirketler toplamı) tek sorguda mümkün | Yanlış filtre unutulursa **şirketler arası veri sızıntısı** riski → tüm route'larda `sirket_koruma` denetimi gerekir |
| Kullanıcı aynı oturumda şirket değiştirebilir (üst çubuk) | Mevcut 53 tablonun tamamına kolon + `UNIQUE` dizin düzenlemeleri (ör. `fatura_no` artık `sirket_id` ile birlikte unique) |
| Cari/Stok ortak havuz istenirse esnek (sirket_id boş = ortak) | Kademeli geçiş gerektirir; eski veri tek şirkete atanır |

**Nasıl:** `sirket` tablosu; `session.sirket_id`; `db` katmanına otomatik `WHERE sirket_id=?` enjekte eden
bir sarmalayıcı (kuralın merkezileştirilmesi, her route'a elle yazılmaması). `sube` artık `sirket_id` altında
hiyerarşi: **Sirket → Şube → Depo**.

### Seçenek B — Ayrı DB dosyası her şirket için (`data/sirket_{id}.db`)

| Artılar | Eksiler |
|---|---|
| **Tam izolasyon** — şirket verisi fiziksel olarak ayrı, sızıntı riski sıfır | Şirketler arası tek konsolide rapor sorgusu imkânsız (ayrı DB) |
| Mevcut kod neredeyse hiç değişmez (yalnızca DB yolu seçimi) | Yedekleme/migrasyon her DB için ayrı çalıştırılmalı |
| Her şirket farklı yapıda büyüyebilir, çok büyük veride performans avantajı | Kullanıcı şirket değiştirince oturum/bağlantı yeniden kurulmalı |
| "Bir muhasebe ofisi, N müşteri firma" senaryosu için en güvenli seçim | Şirketler arası transfer/kesişen kayıtlar desteklenmez (zaten istenmiyor) |

## Şirket değiştirme UX

- **Oturum bazlı:** girişte şirket seç, oturum boyunca sabit; değiştirmek için yeniden seçim ekranı.
- **Üst çubukta anlık:** her sayfada sağ üstte şirket seçici (dropdown); değişince aynı oturumda veri seti değişir.
  (A seçeneğinde kolay; B seçeneğinde DB değiştirme + oturum anahtarına sirket_id yazma.)

## Kullanıcı modeli

- **Kullanıcı çoklu şirkete erişebilir:** `kullanici_sirket` ara tablosu (N-N); girişte/üst çubukta yetkili
  olduğu şirketler listelenir. Muhasebe ofisi senaryosuna uygun.
- **Şirket bazında ayrı kullanıcı:** her kullanıcı tek `sirket_id`'ye bağlı; şirket değiştirmek için başka
  kullanıcı gerekir. Daha basit ama çok şirketli kullanıcılar için zahmetli.

## Öneri (varsayılan)

Orta ölçekli bir ERP için **Seçenek A + üst çubuk anlık değiştirme + kullanıcı-sirket N-N** dengeli bir
başlangıçtır; ama "tam izolasyon kritik" deniyorsa **Seçenek B** daha güvenli ve daha az invazivdir.
Karar kullanıcıya aittir (aşağıdaki 3 soru).
