# D009 — Güvenlik & Sağlamlık Denetimi (SQL Enjeksiyonu, Oturum, Dosya Yükleme, CSRF, Kaba Kuvvet Koruması)

- **Görev ID:** D009
- **Durum:** BEKLEMEDE (Coder bekleniyor)
- **Öncelik:** Yüksek
- **Kaynak:** GM1 (Claude) — 2026-09-12
- **Sürüm hedefi:** v1.40.0

---

## GEREKÇE

F1-F6 ve D007/D008 ile işlevsel kapsam (satış/satın alma/POS/bakım/CRM/finansal raporlama)
olgunlaştı, ama hiçbir pakette özel bir güvenlik sertleştirme turu yapılmadı. Sistem artık dışa
açık yüzeyi (API uçları, dosya yükleme, çok kullanıcılı oturum) genişlemiş durumda — bu turda
kod değişikliği değil, önce envanter + risk tespiti, sonra düşük riskli/somut düzeltmeler istiyorum.

## GEREKSİNİMLER

1. **SQL enjeksiyonu taraması:** Tüm `*.py` dosyalarında ham string birleştirmeyle kurulan SQL
   sorgularını (f-string `{değişken}` veya `%`/`+` ile SQL'e gömülen kullanıcı girdisi) tara.
   Parametrik sorgu (`?` placeholder) kullanılmayan her yeri listele ve düzelt.
   `sqlite3.execute(query, params)` deseni dışına çıkan tek bir yer bile kabul edilmez.
2. **Oturum (session) güvenliği:** `sessionler` tablosu ve oturum üretim kodunu incele:
   - Oturum token'ı kriptografik olarak güvenli rastgelelik ile mi üretiliyor
     (`secrets.token_hex` / `os.urandom` — `random` modülü DEĞİL)?
   - Oturum süresi/timeout var mı? Yoksa makul bir süre (örn. 8-12 saat hareketsizlik) ekle.
   - Çıkış yapıldığında (`/cikis`) sunucu tarafında oturum gerçekten siliniyor mu, yoksa
     yalnızca cookie mi temizleniyor?
3. **Kaba kuvvet (brute-force) koruması:** `/giris` rotasında başarısız deneme sınırlaması var mı?
   Yoksa, IP veya kullanıcı adı bazında basit bir "N başarısız denemeden sonra M dakika kilitle"
   mekanizması ekle (yeni tablo gerekmiyorsa `kullanici` tablosuna `basarisiz_giris_sayisi` +
   `kilit_bitis` gibi 2 alan yeterli).
4. **Dosya yükleme güvenliği** (`ekler.py`, `uploads/`): Yüklenen dosyalarda şu kontroller var mı,
   yoksa ekle:
   - Dosya adı path traversal'a karşı temizleniyor mu (`../` vb.)?
   - Uzantı/MIME tipi beyaz listesi var mı (yalnızca jpg/png/pdf/xml gibi beklenen tipler)?
   - Dosya boyutu sınırı (UI'da "15 MB" yazıyordu — bu sunucu tarafında da zorlanıyor mu,
     yoksa sadece istemci tarafı mı?)
5. **CSRF koruması:** Durum değiştiren (POST) rotalarda CSRF token kontrolü var mı? Yoksa,
   oturum bazlı basit bir CSRF token mekanizması ekle (form'a gizli alan + sunucu tarafı doğrulama).
6. **Yetki matrisi kaçakları:** Her `@route` tanımının gerçekten `roles=(...)` ile korunduğunu
   doğrula — `roles=()` (herkese açık) olarak işaretlenmiş ama aslında hassas veri döndüren bir uç
   var mı (özellikle `api.py`, `/api/*` uçları)?

## KABUL KRİTERLERİ

- [ ] SQL enjeksiyonu taraması sonucu: **0 ham string sorgu** (ya baştan yoktu ya düzeltildi) — grep kanıtıyla.
- [ ] Oturum token üretimi kriptografik güvenli rastgelelik kullanıyor + süre sınırı var.
- [ ] `/giris`'te başarısız deneme sınırlaması çalışıyor (test: 5 yanlış şifreden sonra 6.'sı reddedilir).
- [ ] Dosya yükleme: path traversal + uzantı beyaz listesi + sunucu tarafı boyut sınırı testle kanıtlanmış.
- [ ] CSRF token'ı olmayan bir POST isteği reddediliyor (test: token'sız POST 403).
- [ ] `/api/*` uçlarının hepsi ya kimlik doğrulaması istiyor ya da bilinçli olarak herkese açık olduğu
      gerekçelendirilmiş (dokümante edilmiş).
- [ ] Bu değişiklikler mevcut hiçbir testi bozmuyor — tam regresyon (şu an 23 dosya / 527 kontrol)
      hâlâ 527/527 + yeni `test_d009_guvenlik.py` eklenmiş.
- [ ] K1 (şirket izolasyonu) ve mevcut rol/yetki davranışı değişmedi.

## İSTENEN KANITLAR

- [ ] **Zip olarak güncel kaynak kod + DB + testler** (bu paket kod/güvenlik değişikliği içerdiği için
      metin/GitHub-link yeterli değil — GM1'in D008'de netleştirdiği kural: kod değişen her paket için
      zip + GM1'in bağımsız çalıştırması şart).
- [ ] `test_d009_guvenlik.py` — en az şu senaryoları içersin:
      SQL enjeksiyon denemesi (örn. `' OR '1'='1` login/arama alanlarında etkisiz),
      6. başarısız girişin reddi, CSRF'siz POST reddi, path-traversal dosya adı reddi,
      oturum süresi dolunca erişim reddi.
- [ ] Tam regresyon çıktısı (23+1 dosya, tam sayı).
- [ ] MD5/SHA256 ile zip.
- [ ] Değişen dosyaların listesi/diff'i.

## TEKNİK NOTLAR

- Bu bir "sertleştirme" turu — mevcut iş mantığına (K1-K32 kuralları, belge zincirleri, mali etki
  mantığı) dokunulmayacak, yalnızca giriş/oturum/dosya/SQL katmanına ek kontrol.
- Performans endişesi varsa (örn. CSRF/oturum kontrolü ek yük), önce ölçüp sonra karar verin —
  mevcut basit wsgiref sunucusunun küçük ek yükleri tolere edebileceği varsayılıyor.
- Şifre hash'i zaten PBKDF2-HMAC-SHA256 (K32) — buna dokunulmuyor, bu madde kapsamda değil.
- **Emin olmadığın bir madde varsa** (örn. CSRF'nin bu basit mimaride nasıl uygulanacağı),
  kodlamaya başlamadan önce GM1'e 2-3 seçenekle (D007/D008'deki mikro-karar formatında) danış.
