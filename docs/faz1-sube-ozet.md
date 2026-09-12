# Faz 1 — Çekirdek: Depo/Şube Modülü (Detaylı Özet & Onay)

> Proje komutundaki "her fazın sonunda veri modeli özeti + ekran listesi + örnek test
> senaryosu üret ve onay iste" kuralı gereği hazırlanmıştır. **Faz 1'in son modülü.**
> Diğer modüllerle (Cari/Stok/Stok2/Kasa/Banka) aynı formattadır.

---

## 1) Bu fazda ne yapıldı?

- **Şube modülü:** şube tanımı + CRUD; depo–şube bağlama; kullanıcı–şube atama;
  şube bazlı raporlama; **şube bazlı veri görünürlüğü/izolasyonu** (test edildi — Bölüm 5).
- Depo yönetimi (çoklu depo, transfer, min/max) Stok2'de zaten teslim edilmişti; bu fazda
  depolara `sube_id` bağlantısı eklendi.
- Bu modülün getirdiği izolasyon düzeltmesi: şubeye atanmış, Admin olmayan bir kullanıcı
  artık **yalnızca kendi şubesini ve o şubenin depolarını** görebilir.

## 2) Veri Modeli

| Tablo/Sütun | Amaç | Kritik Alanlar |
|---|---|---|
| `sube` | Şube tanımı | kod, ad, il, ilce, adres, telefon, aktif |
| `depo.sube_id` | Deponun bağlı olduğu şube (FK → sube) | NULL = şubesiz depo |
| `kullanici.sube_id` | Kullanıcının bağlı olduğu şube (FK → sube) | NULL = tüm şubeler |

**İzolasyon kuralı (kodda):**
- Kullanıcı `sube_id` taşıyor ve Admin değilse: Stok listesi yalnızca kendi şubesinin
  depolarındaki ürünleri gösterir; Şube listesi ve detayı yalnızca kendi şubesini gösterir.
- Kullanıcının `sube_id` NULL ise (atanmamış): tüm şubeleri/depoları görür.
- Admin: her zaman tüm veriyi görür.

**Bilinçli kapsam sınırı (önemli, net):** Satır düzeyinde tam şube izolasyonu şu an
**yalnızca Stok listesi + Şube ekranlarında** uygulanıyor. Cari, Kasa, Banka ve hareket
ekranları henüz şube kapsamına alınmadı — bunlar işletme fiilen çok şubeye geçtiğinde
"Faz 6 — Cila" kapsamında tüm tablolara `sube_id` taşınarak tamamlanacak. (Komut 1.12
"şube bazlı yetkilendirme ve raporlama" hedefi; şu an şube bazlı **raporlama + stok
görünürlüğü** çalışıyor, tam satır izolasyonu sonraki fazın işi.)

## 3) API Uçları (route listesi)

| Metod | Yol | Yetki* | İşlev |
|---|---|---|---|
| GET | `/sube` | giriş | Şube listesi (izolasyon uygulanır) |
| GET/POST | `/sube/yeni` | Admin | Yeni şube |
| GET | `/sube/{id}` | giriş | Şube detayı (izolasyon: başka şube → yönlendirme) |
| GET/POST | `/sube/{id}/duzenle` | Admin | Şube düzenleme |
| GET/POST | `/sube/kullanicilar` | Admin | Kullanıcı–şube ataması |

\* Şube yönetimi (yazma) yalnızca Admin; görüntüleme tüm rollerde ama izolasyon kuralına tabi.

Ayrıca Stok2'ye şube bağlantısı: `POST /stok/depolar` artık `sube_id` alıyor;
depo listesinde "Şube" sütunu var.

## 4) Ekran Listesi

1. **Şubeler** — kod, il/ilçe, depo sayısı, toplam stok, kullanıcı sayısı.
2. **Şube Detayı** — depolar (stok/kalem), şubedeki kullanıcılar, en çok stok tutan ürünler.
3. **Yeni/Düzenle Şube** — ad, kod, il/ilçe, adres, telefon.
4. **Kullanıcı–Şube Atama** — kullanıcı listesi + şube seçimi (boş = tüm şubeler).
5. **Depolar** (Stok2) — "Şube" sütunu + depo eklerken şube seçimi.
6. Topbar — kullanıcının şubesini gösteren rozet ("🏢 Batman Merkez Şube" / "🏢 Tüm Şubeler").

## 5) Örnek Test Senaryosu — Şube Bazlı Veri İzolasyonu

**Kurulum:**
1. Admin ile 2. şube "Diyarbakır Şube" oluşturulur.
2. Bu şubeye "Diyarbakır Şube Deposu" (Ana) bağlanır.
3. `satis` kullanıcısı "Diyarbakır Şube"ye atanır.
4. Diyarbakır deposuna yalnızca "MARKA-B 43\" TV" için 5 adet stok girilir
   (diğer 8 ürün Batman deposunda).

**Doğrulama (gerçek HTTP test sonuçları):**

| # | Kontrol | Beklenen | Sonuç |
|---|---|---|---|
| 1 | `satis` → `/stok` ürün sayısı | 1 (sadece TV-43) | ✅ 1 |
| 2 | `satis` → `/sube` şube sayısı | 1 (sadece Diyarbakır) | ✅ 1 |
| 3 | `satis` → `/sube/1` (Batman, başka şube) | yönlendirilir | ✅ 302 → /sube |
| 4 | `satis` → `/sube/2` (kendi şubesi) | 200 | ✅ 200 |
| 5 | `satis` → `/sube/yeni` | 403 | ✅ 403 |
| 6 | `satis` → `/sube/kullanicilar` | 403 | ✅ 403 |
| 7 | `depo` (şubesiz) → `/stok` | 9 (tümü) | ✅ 9 |
| 8 | `depo` (şubesiz) → `/sube` | 2 (tümü) | ✅ 2 |
| 9 | `admin` → `/stok` | 9 (tümü) | ✅ 9 |
| 10 | `admin` → `/sube` | 2 (tümü) | ✅ 2 |
| 11 | `admin` → `/sube/1` ve `/sube/2` | 200, 200 | ✅ 200, 200 |

**Sonuç:** Şubeye atanmış kullanıcı kendi şubesinin dışındaki depo/şube verisini göremez;
şubesiz kullanıcı ve Admin tüm veriyi görür; şube yönetimi Admin'e kapalıdır.

**Genel senaryo (modülün kendisi):**
1. Admin → Depo/Şube: "Batman Merkez Şube" 3 depo ile listelenir.
2. Yeni şube oluştur → depo bağla → kullanıcı ata.
3. Şube detayında depo listesi, kullanıcılar ve en çok stok tutan ürünler doğru gelir.
4. Yetki matrisi yukarıdaki tablo gibi çalışır.

## 6) Sonraki Adım (onay bekleniyor)

**Faz 1 tamamlandı.** Onay verirsen **Faz 2 — Satış Döngüsü** başlar:
Teklif → Sipariş → İrsaliye → Fatura → Çek/Senet → Döviz Takip.

---

## 7) Ek — Bu modül vesilesiyle kapatılan açık noktalar

1. **Borç/alacak yönü:** evrensel çift taraflı konvansiyon (`bakiye = Σborç − Σalacak`);
   müşteri pozitif, tedarikçi negatif. Seed düzeltildi (Alış Faturası → Alacak), `_aging`
   negatif bakiyede boş döner. (Detay: `faz1-kasa-ozet.md` Bölüm 7.)
2. **Transfer karşı taraf kontrolü:** Kasa↔Banka transferlerinde karşı taraf bakiyesi
   **hiçbir kayıt yazılmadan önce** kontrol edilir; yetersizse tam red. (Detay: aynı dosya.)
