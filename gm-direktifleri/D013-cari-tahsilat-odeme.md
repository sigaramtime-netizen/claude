# D013 — CARİ TAHSİLAT / ÖDEME EKRANI DİREKTİFİ

**Tarih:** 2026-09-15  
**Veren:** GM1 (Genel Müdür 1 — Claude)  
**Öncelik:** Yüksek (Kullanıcı şikayetinin son maddesi, D011+D012 ile kapsam netleşti)  
**Sürüm:** v1.43.0 → v1.44.0  

---

## GEREKÇE
Sistemde kasa/banka/çek-senet üzerinden bir cariye para hareketi kaydetmek teknik olarak mümkün (`cari_id` alanı zaten var), ama kullanıcı için tek, açık bir "bu müşteriden param var, tahsil ettim" veya "bu tedarikçiye ödeme yaptım" ekranı yok. Bunu POS'un ödeme-dağılım desenini yeniden kullanarak kapatıyoruz — yeni bir mali mantık icat etmiyoruz.

---

## GEREKSİNİMLER

1. **İki yeni rota, tek ortak ekran mantığı:**
   - `GET/POST /cari/<id>/tahsilat` — müşteriden (bakiye pozitifse, yani cari borçluysa) para alma.
   - `GET/POST /cari/<id>/odeme` — tedarikçiye (bakiye negatifse) para verme.
   - İkisi de cari kartından/kartoteksten/ekstre sayfasından tek tıkla erişilebilir bir buton ile açılmalı.

2. **Ödeme şekli seçimi — POS'un `pos_satis_olustur`'daki `odemeler` desenini birebir tekrar et:**
   - Bölünebilir, aynı ekranda birden fazla satır (Nakit + Kart + Havale gibi karışık olabilir).
   - **Nakit** → `kasa.kasa_hareket_olustur(..., cari_id=..., ilgili_modul="CariTahsilat"/"CariOdeme", ...)`.
   - **Havale/EFT** → `banka.banka_hareket_olustur(..., cari_id=..., ...)`.
   - **Kredi Kartı** → POS'taki terminal/komisyon mantığı yeniden kullanılır (net tutar bankaya, komisyon ayrı izlenir) — yeni bir terminal seçme alanı ekle.
   - **Çek/Senet** → `cek_senet.py`'deki mevcut Alinan/Verilen akışı çağrılır (tahsilat ekranında yalnızca *Alınan*, ödeme ekranında yalnızca *Verilen* seçeneği sunulur).

3. **Muhasebe & Cari Entegrasyonu:**
   - Her ödeme satırı sonrası cari hareket (K26 deseniyle borç/alacak) + ilgili yevmiye fişi otomatik üretilir — yeni bir muhasebe mantığı yazılmayacak, mevcut `_cari_uygula` / `fis_uret` fonksiyonları çağrılacak.

4. **Döviz desteği (D012 ile tutarlı):**
   - Tahsilat/ödeme belge para biriminde (`TRY/USD/EUR/GBP`) girilebilir; kur D012'deki gibi sabitlenir, TL karşılığı eşzamanlı gösterilir.

5. **Kısmi tahsilat/ödeme:**
   - Girilen tutar cari bakiyeden az olabilir (kısmi kapatma) — sistem kalanı otomatik hesaplar, hata vermez.

6. **Fazla tahsilat/ödeme uyarısı:**
   - Girilen toplam, cari bakiyeyi aşarsa engellenmez (avans alınır/verilir) ama arayüzde açık bir uyarı gösterilir (*"Bakiyeyi X ₺ aşıyorsunuz — avans olarak işlenecek"*).

7. **Yetki:**
   - Tahsilat (para girişi): `Admin` · `Muhasebe` · `Satis`
   - Ödeme (para çıkışı): `Admin` · `Muhasebe` (Satış rolü yapamaz — tedarikçiye para çıkışı daha hassas).

---

## KABUL KRİTERLERİ

- [ ] Tahsilat ekranından yapılan Nakit+Kart karışık bir işlem, doğru kasa hareketi + doğru banka hareketi (komisyon düşülmüş net) + doğru cari alacak kaydı + doğru yevmiye fişlerini üretiyor.
- [ ] Ödeme ekranından yapılan bir Havale işlemi, doğru banka çıkışı + cari borç azaltma + yevmiye üretiyor.
- [ ] Çek/Senet seçimi, tahsilatta yalnız "Alınan", ödemede yalnız "Verilen" seçeneklerini gösteriyor; ikisi de mevcut `cek_senet.py` akışını çağırıyor (kod tekrarı yok).
- [ ] Kısmi tahsilat/ödeme sorunsuz çalışıyor; kalan bakiye doğru güncelleniyor.
- [ ] Fazla tahsilat/ödeme engellenmiyor ama arayüzde uyarı var.
- [ ] Döviz cinsinden tahsilat/ödeme, D012'deki kur sabitleme + TL karşılığı deseniyle tutarlı.
- [ ] Yetki matrisi doğru (Satış tahsilat yapabilir ama ödeme yapamaz — test: Satış rolüyle `/cari/<id>/odeme` POST → 403).
- [ ] Tam regresyon (27 eski dosya + D013'ün kendisi = 28 dosya) hâlâ tam yeşil (603 + yeni test sayısı).
- [ ] K1 şirket izolasyonu korunuyor.

---

## İSTENEN KANITLAR & TESLİM
- ZIP (kod + demo seed'li DB + testler) + MD5/SHA256
- `test_d013_cari_tahsilat_odeme.py` (en az: karışık ödeme, havale, çek/senet iki yön, kısmi, avans uyarısı, döviz, yetki 403, K1, FK temizliği)
- Tam regresyon çıktısı (28 dosya, tam sayı)
- Değişen/yeni dosya listesi
