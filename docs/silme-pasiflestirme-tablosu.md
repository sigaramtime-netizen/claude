# Düzenleme / Silme — Modül Modül Kural Tablosu (İstek 2)

> Durum: **KODLANDI ✅** (şartlı onay + 3 netlik cevabı sonrası) — aşağıdaki 10 iş uygulandı,
> `test_silme_kurallari.py` (21/21) ile doğrulandı. K15/K25 ve mevcut kilitler bozulmadan korundu.
>
> **Lejant:** 🟢 = serbest · 🔴 = engelli · `[MEVCUT]` = bugün kodda zaten var (davranış korunur) ·
> `[YENİ]` = onay sonrası kodlanacak.
>
> Dayanaklar: K32 (finansal etkili / referans edilen veride sert silme yok, audit korunur),
> K15/K25 (onaylı belge + bağlı tahsilat/e-belge kilidi), Faz 6.1 (silme yerine pasifleştirme).

## A. Belgeler (döngü belgeleri)

### 1. Teklif
| İşlem | Kural | Durum |
|---|---|---|
| Düzenleme | 🟢 Taslak, Gönderildi, Süresi Doldu · 🔴 Onaylandı, Reddedildi | `[MEVCUT kısmen]` — **Eksik: onay/red kilidi yalnız UI'da; sunucu tarafına da eklenecek** `[YENİ]` |
| Silme | 🟢 Taslak / Reddedildi / Süresi Doldu **ve** hiç siparişe dönüşmemiş (`kaynak_teklif_id` bağlantısı yok) · 🔴 Onaylandı veya siparişe bağlı | `[YENİ]` |
| Not | Teklif hiçbir zaman finansal etki üretmez; silinen kayıt için audit satırı bırakılır. | — |

### 2. Sipariş
| İşlem | Kural | Durum |
|---|---|---|
| Düzenleme | 🟢 Bekliyor · 🔴 Onaylandı / Kısmi / Tamamlandı / İptal | `[MEVCUT]` (sunucu tarafı kilit) |
| Silme | 🟢 Bekliyor **ve** irsaliyeye dönüşmemiş (`kaynak_siparis_id` bağlantısı yok) · 🔴 diğer tüm durumlar | `[YENİ]` |
| Not | Onaylı sipariş silinemez; rezervasyon yalnız İptal ile serbest bırakılır (mevcut K11). | — |

### 3. İrsaliye
| İşlem | Kural | Durum |
|---|---|---|
| Düzenleme | 🟢 Taslak · 🔴 Onaylandı / İptal | `[MEVCUT]` (sunucu tarafı kilit) |
| Silme | 🟢 Taslak (stok hareketi hiç üretilmemiş) · 🔴 Onaylandı / İptal | `[YENİ]` |
| Not | Onaylı irsaliyede silme yok; İptal stoğu ters kayıtla geri alır ve bağlı e-İrsaliye'yi iptal eder (mevcut). K15/K25: bağlı **fatura** varsa İptal engellenir (mevcut zincir). | — |

### 4. Fatura
| İşlem | Kural | Durum |
|---|---|---|
| Düzenleme | 🟢 Taslak · 🔴 Onaylandı / İptal | `[MEVCUT]` (sunucu tarafı kilit) |
| Silme | 🟢 Taslak (cari hareket hiç üretilmemiş) · 🔴 Onaylandı / İptal | `[YENİ]` |
| **K15/K25** | **Bozulmaz.** `_bagli_tahsilat_var` + e-belge kontrolü aynen kalır: onaylı faturada bağlı tahsilat/e-belge varsa **İptal engellenir**. Silme zaten yalnız Taslak'ta mümkün olacağından bağlı kayıt içeremez. | `[MEVCUT korunur]` |

### 5. Çek / Senet
| İşlem | Kural | Durum |
|---|---|---|
| Düzenleme | 🟢 Bekliyor · 🔴 diğer tüm durumlar | `[MEVCUT]` (sunucu tarafı kilit) |
| Silme | 🟢 Bekliyor · 🔴 Tahsile Verildi / Tahsil Edildi / Ödendi / Karşılıksız / Ciro / İptal | `[YENİ]` |
| **K15/K25** | **Bozulmaz.** Durum geçiş matrisi + tahsilat/ödeme bağlantıları aynen kalır; mali etki (yevmiye) üreten durumlardan hiçbirinde silme mümkün olmaz. | `[MEVCUT korunur]` |

## B. Master data (K32)

### 6. Cari
| İşlem | Kural | Durum |
|---|---|---|
| Düzenleme | 🟢 her zaman (pasif/aktif ayrımıyla) | `[MEVCUT]` |
| Silme | 🟢 **hiç** `cari_hareket` + hiç bağlı belge (teklif/sipariş/irsaliye/fatura/çek) yoksa · 🔴 varsa → "silinemez, pasifleştirin" uyarısı | `[YENİ]` |
| Pasifleştirme | 🟢 her zaman (`aktif=0`) — geçmiş korunur | `[MEVCUT]` |

### 7. Stok (kart)
| İşlem | Kural | Durum |
|---|---|---|
| Düzenleme | 🟢 her zaman | `[MEVCUT]` |
| Silme | 🟢 **hiç** `stok_hareket`/`stok_seviye`/`stok_varyant`/`stok_seri`/bağlı belge kalemi yoksa · 🔴 varsa → engel | `[YENİ]` |
| Pasifleştirme | 🟢 her zaman (`aktif=0`) | `[MEVCUT]` |

### 8. Stok2 (kullanıcı: "hepsi" — hareketler + transferler + sayım)
| Ekran | Kural | Durum |
|---|---|---|
| Stok hareketleri / kartoteks | 🔴 salt-okunur (K4 tek kronolojik kaynak) — **silme eklenmez** | `[MEVCUT korunur]` |
| Depo transferleri | 🟢 Taslak transfer düzenlenebilir/silinebilir · 🔴 Tamamlandı silinemez | `[YENİ: silme]` |
| Stok sayımı | 🟢 Taslak sayım silinebilir · 🔴 Tamamlandı silinemez (mizan farkı işlenmiş) | `[YENİ: silme]` |

## C. Diğer modüller

| Modül | Kural | Durum |
|---|---|---|
| 9. Servis Takip | Kayıt silme yok (durum akışı: Alındı→…→Teslim/İade). Parça silme: 🟢 teslim edilmemiş kayıtta · 🔴 tamamlanmış/onaylı serviste | `[MEVCUT parça silme]` + `[YENİ: tamamlanmış serviste parça silme engeli]` |
| 10. Seri No-Garanti | Seri kaydı sert silinemez (stoğa/harekete bağlı); garanti tarihleri güncellenebilir | `[MEVCUT korunur]` |
| 11. Notlar | 🟢 silinebilir (confirm + audit) | `[MEVCUT]` |
| + Kullanıcı | 🔴 sert silme yok → pasifleştirme | `[MEVCUT]` |
| + Kategori / Marka / Grup / Depo / Şube / Kasa / Banka | 🔴 sert silme yok → pasifleştirme; referans varsa engel | `[MEVCUT]` |
| + Demirbaş | 🟢 silinebilir **ancak** zimmet/amortisman kaydı varsa 🔴 engel | `[MEVCUT silme]` + `[YENİ: engel doğrulaması]` |
| + Bütçe / Döviz kuru | 🟢 silinebilir (confirm + audit) | `[MEVCUT]` |
| + Yevmiye | 🟢 Taslak fiş silinebilir · 🔴 Onaylandı silinemez | `[MEVCUT]` |

## K15/K25 güvencesi (özet)

- **Fatura:** onaylı + bağlı tahsilat/e-belge → İptal **engellenir** (`_bagli_tahsilat_var`). Silme yalnız **Taslak**; bu yüzden bağlı kayıtla çakışması imkânsız. → koruma bozulmaz.
- **Çek/Senet:** tahsilat/ödeme/ciro/karşılıksız durumları mali iz üretir; bu durumlardan silme hiçbir koşulda mümkün olmaz. → koruma bozulmaz.
- **İrsaliye:** bağlı fatura varsa İptal engellenir; onaylı irsaliye silinemez. → koruma bozulmaz.

## Onay sonrası kodlanacak iş listesi (yalnızca bunlar) — **TAMAMI UYGULANDI ✅**

1. ✅ Teklif: sunucu tarafı düzenleme kilidi (Onaylandı/Reddedildi) + Taslak/Red/Süresi Doldu için **silme** (sipariş bağı yoksa).
2. ✅ Sipariş: Bekliyor + irsaliyeye dönüşmemiş için **silme**.
3. ✅ İrsaliye: Taslak için **silme** (kalem + header + ek dosyalar temizlenir).
4. ✅ Fatura: Taslak için **silme** (kalem + header + notlar + ek dosyalar temizlenir).
5. ✅ Çek/Senet: Bekliyor için **silme** (ek dosyalar temizlenir).
6. ✅ Cari: tüm referanslar (FK + polimorfik notlar/ek_dosya) yoksa **silme**, varsa engel (`db.referans_var`).
7. ✅ Stok: tüm referanslar yoksa **silme**, varsa engel (`db.referans_var` — jenerik FK taraması).
8. ✅ Depo transferi + Sayım: Taslak için **silme** (kalem + header).
9. ✅ Servis: tamamlanmış/teslim/iadeli serviste parça silme **engeli**.
10. ✅ Demirbaş: zimmet/amortisman varken silme **engeli** (önceden zorla siliniyordu; artık engel).
11. ✅ Diğer tüm kilitler **aynen korunur** (onaylı belgeler, K15/K25, pasifleştirme, audit).
