# D002 — Gerçek Proje Dosyalarının GitHub'a Yüklenmesi + GM Denetim Listesi

- **Görev ID:** D002
- **Başlık:** Coder'ın v1.34.0 proje dosyalarını GitHub'a yüklemesi + GM denetimi
- **Durum:** BEKLEMEDE (Coder bekleniyor)
- **Öncelik:** Kritik

---

## Durum tespiti (GM)

Coder, `PROJE-DOKUMANTASYONU-v1.34.0.txt` raporunu GM'ye iletti. Rapor şunları iddia ediyor:
- Brn Teknoloji ERP v1.34.0 — Python 3 (stdlib), SQLite (65 tablo), 525 dosya
- 18 test paketi, toplam 424 kontrol → 424/424 GEÇTİ
- F4 (e-Dönüşüm Mock/Sandbox) paketi kapandı

**SORUN:** GitHub repo'sunda (`sigaramtime-netizen/BRN-Teknoloji-ERP`) yalnızca iş akışı
şablonları var. **Gerçek kod dosyaları repo'da YOK.** Rapor, tek başına denetim için
yeterli DEĞİLDİR — iddialar gerçek dosyalarla doğrulanmalıdır.

---

## CODER'A TALİMAT

`/home/user/erp` içindeki gerçek projeyi repo'nun **`kod/`** klasörüne yükle.

### Coder penceresinde çalıştırılacak komutlar

```bash
git config --global user.name  "CODER"
git config --global user.email "coder@arena.local"

cd /home/user
git clone https://sigaramtime-netizen:TOKEN@github.com/sigaramtime-netizen/BRN-Teknoloji-ERP.git repo
cd repo

# ERP projesini kod/ altına kopyala
mkdir -p kod
cp -r /home/user/erp/. kod/

# Opsiyonel temizlik (önerilir):
#   data/erp.db  -> 900 KB'lık binary, ilk açılışta otomatik üretilir, repo'ya gerekmez
#   uploads/     -> ham XML dosyaları, .gitignore'a alınabilir
rm -f kod/data/erp.db
rm -rf kod/uploads

# Kanıtları kanitlar/ altına koy (varsa):
mkdir -p kanitlar/v1.34.0
# cp /home/user/indirme/kanit_f4_*.txt kanitlar/v1.34.0/   (varsa)

git add -A
git commit -m "[CODER] v1.34.0 ERP projesi kod/ klasörüne yüklendi"
git push
```

> `TOKEN` yerine kendi token'ını yaz. Yükleme bittikten sonra GM'ye haber ver
> (commit mesajı + repo'daki dosya listesiyle).

---

## GM DENETİM KONTROL LİSTESİ (kod geldikten sonra doldurulacak)

```bash
cd repo && git pull
```

- [ ] `kod/` klasöründe dosyalar var mı? Rapor 525 dosya diyor → `find kod -type f | wc -l`
- [ ] Ana modüller mevcut mu? (`app.py`, `core.py`, `db.py`, `config.py`, `fatura.py`...)
- [ ] Sunucu başlıyor mu? → `cd kod && python3 app.py` → tarayıcıda aç, `admin / 1234` ile gir
- [ ] Veritabanı 65 tablo mu? → `sqlite3 kod/data/erp.db ".tables"` (ilk açılıştan sonra)
- [ ] F4 testi geçiyor mu? → `cd kod && python3 test_f4_edonusum.py` → **22/22 olmalı**
- [ ] Tam regresyon geçiyor mu? → `for t in test_*.py; do python3 $t; done` → **424/424 olmalı**
- [ ] Kanıt dosyaları `kanitlar/` klasöründe var mı? (ekran görüntüsü + test çıktısı)
- [ ] Rapordaki iddialar gerçek dosyalarla ÖRTÜŞÜYOR mu? (tutarsızlık varsa → REVİZYON)

### Karar kuralı
- Hepsinden geçti → `[GM] D002 ONAYLANDI` commit'i at.
- Eksik/tutarsız → `[GM] D002 REVIZYON: ...` commit'i at, eksikleri listele.

---

**ÖNEMLİ NOT:** Rapor ne kadar detaylı olursa olsun, **kod GitHub'da değilken hiçbir
paket "tamamlandı" sayılmaz.** Denetimin tek geçerli dayanağı: repo'ya çekilmiş gerçek
dosyalar + o dosyalarla çalıştırılan testlerdir.
