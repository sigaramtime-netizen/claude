# Yetki Matrisi (Faz 6.1)

**Tarih:** 2026-09-08 · **Firma:** Brn Teknoloji

Kural: **Admin her rotada tam yetkilidir.** `herkese açık` = giriş gerekmez; 
`giriş yapmış herkes` = oturum yeterli (rol kısıtı yok); aksi halde listelenen roller + Admin.

Toplam **166 kayıtlı rota** — modül başına yazma/okuma uçları aşağıdadır.

## Modül özeti

| Modül | Rota | Yazma ucu |
|---|---|---|
| app | 9 | 2 |
| ayarlar | 9 | 8 |
| banka | 6 | 4 |
| beyanname | 3 | 0 |
| cari | 9 | 5 |
| cek_senet | 7 | 3 |
| demirbas | 9 | 7 |
| doviz | 6 | 4 |
| edonusum | 13 | 8 |
| ekler | 3 | 2 |
| fatura | 6 | 3 |
| finansal | 5 | 2 |
| garanti | 4 | 2 |
| irsaliye | 6 | 3 |
| kartoteks | 7 | 0 |
| kasa | 6 | 3 |
| muhasebe | 10 | 5 |
| notlar | 3 | 2 |
| servis | 8 | 6 |
| siparis | 6 | 3 |
| stok | 19 | 13 |
| sube | 5 | 3 |
| teklif | 6 | 3 |
| transfer | 1 | 0 |

## Rota listesi

| Rota | Metot | Yetki |
|---|---|---|
| `^/giris$` | GET,POST | herkese açık |
| `^/cikis$` | GET | giriş yapmış herkes |
| `^/$` | GET | giriş yapmış herkes |
| `^/bildirimler$` | GET | giriş yapmış herkes |
| `^/bildirimler/ayarlar$` | GET,POST | Admin (+Admin) |
| `^/bildirimler/tumunu-oku$` | GET | giriş yapmış herkes |
| `^/bildirimler/(?P<bid>\d+)/oku$` | GET | giriş yapmış herkes |
| `^/yetkiler$` | GET | Admin (+Admin) |
| `^/saglik$` | GET | herkese açık |
| `^/ayarlar$` | GET | Admin (+Admin) |
| `^/ayarlar/kullanicilar$` | GET,POST | Admin (+Admin) |
| `^/ayarlar/kullanici/(?P<uid>\d+)/rol$` | POST | Admin (+Admin) |
| `^/ayarlar/kullanici/(?P<uid>\d+)/durum$` | POST | Admin (+Admin) |
| `^/ayarlar/kullanici/(?P<uid>\d+)/sifre$` | POST | Admin (+Admin) |
| `^/ayarlar/firma$` | GET,POST | Admin (+Admin) |
| `^/ayarlar/bildirim$` | GET,POST | Admin (+Admin) |
| `^/ayarlar/entegrator$` | GET,POST | Admin (+Admin) |
| `^/profil/sifre$` | GET,POST | giriş yapmış herkes |
| `^/banka$` | GET | giriş yapmış herkes |
| `^/banka/yeni$` | GET,POST | Admin, Muhasebe (+Admin) |
| `^/banka/hareket$` | GET,POST | Admin, Muhasebe (+Admin) |
| `^/banka/hareket/(?P<sid>\d+)/iptal$` | POST | Admin, Muhasebe (+Admin) |
| `^/banka/hesap/(?P<bid>\d+)$` | GET | giriş yapmış herkes |
| `^/banka/import$` | POST | Admin, Muhasebe (+Admin) |
| `^/beyanname$` | GET | giriş yapmış herkes |
| `^/beyanname/denetim$` | GET | giriş yapmış herkes |
| `^/beyanname/denetim/csv$` | GET | giriş yapmış herkes |
| `^/cari$` | GET | giriş yapmış herkes |
| `^/cari/yeni$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/cari/rapor$` | GET | giriş yapmış herkes |
| `^/cari/gruplar$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/cari/(?P<cid>\d+)$` | GET | giriş yapmış herkes |
| `^/cari/(?P<cid>\d+)/ekstre$` | GET | giriş yapmış herkes |
| `^/cari/(?P<cid>\d+)/hareket$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/cari/(?P<cid>\d+)/duzenle$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/cari/(?P<cid>\d+)/not$` | POST | giriş yapmış herkes |
| `^/cek_senet$` | GET | giriş yapmış herkes |
| `^/cek_senet/vade$` | GET | giriş yapmış herkes |
| `^/cek_senet/yeni$` | GET,POST | Admin, Muhasebe (+Admin) |
| `^/cek_senet/(?P<cid>\d+)$` | GET | giriş yapmış herkes |
| `^/cek_senet/(?P<cid>\d+)/duzenle$` | GET,POST | Admin, Muhasebe (+Admin) |
| `^/cek_senet/(?P<cid>\d+)/durum$` | POST | Admin, Muhasebe (+Admin) |
| `^/cek_senet/(?P<cid>\d+)/yazdir$` | GET | giriş yapmış herkes |
| `^/demirbas$` | GET | giriş yapmış herkes |
| `^/demirbas/(?P<did>\d+)$` | GET | giriş yapmış herkes |
| `^/demirbas/ekle$` | POST | Admin, Muhasebe (+Admin) |
| `^/demirbas/(?P<did>\d+)/guncelle$` | POST | Admin, Muhasebe (+Admin) |
| `^/demirbas/(?P<did>\d+)/zimmet$` | POST | Admin, Muhasebe (+Admin) |
| `^/demirbas/(?P<did>\d+)/durum$` | POST | Admin, Muhasebe (+Admin) |
| `^/demirbas/(?P<did>\d+)/sil$` | POST | Admin, Muhasebe (+Admin) |
| `^/demirbas/amortisman-uret$` | POST | Admin, Muhasebe (+Admin) |
| `^/demirbas/kategori-ekle$` | POST | Admin, Muhasebe (+Admin) |
| `^/doviz$` | GET | giriş yapmış herkes |
| `^/doviz/kur$` | POST | Admin, Muhasebe (+Admin) |
| `^/doviz/kur/(?P<kid>\d+)/sil$` | POST | Admin, Muhasebe (+Admin) |
| `^/doviz/tcmb$` | POST | Admin, Muhasebe (+Admin) |
| `^/doviz/kur-farki$` | GET | giriş yapmış herkes |
| `^/doviz/kur-farki/(?P<fid>\d+)/fatura$` | POST | Admin, Muhasebe (+Admin) |
| `^/edonusum$` | GET | giriş yapmış herkes |
| `^/edonusum/yeni$` | GET | Admin, Muhasebe (+Admin) |
| `^/edonusum/olustur$` | POST | Admin, Muhasebe (+Admin) |
| `^/edonusum/(?P<eid>\d+)$` | GET | giriş yapmış herkes |
| `^/edonusum/(?P<eid>\d+)/gonder$` | POST | Admin, Muhasebe (+Admin) |
| `^/edonusum/(?P<eid>\d+)/durum-sorgula$` | POST | Admin, Muhasebe (+Admin) |
| `^/edonusum/(?P<eid>\d+)/mock-yanit$` | POST | Admin (+Admin) |
| `^/edonusum/ayarlar$` | GET,POST | Admin (+Admin) |
| `^/gelen$` | GET | giriş yapmış herkes |
| `^/gelen/yenile$` | POST | Admin, Muhasebe (+Admin) |
| `^/gelen/(?P<gid>\d+)$` | GET | giriş yapmış herkes |
| `^/gelen/(?P<gid>\d+)/durum$` | POST | Admin, Muhasebe (+Admin) |
| `^/gelen/(?P<gid>\d+)/donustur$` | POST | Admin, Muhasebe (+Admin) |
| `^/ek/yukle$` | POST | Admin, Muhasebe, Satis (+Admin) |
| `^/ek/(?P<eid>\d+)$` | GET | giriş yapmış herkes |
| `^/ek/(?P<eid>\d+)/sil$` | POST | Admin, Muhasebe, Satis (+Admin) |
| `^/fatura$` | GET | giriş yapmış herkes |
| `^/fatura/yeni$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/fatura/(?P<fid>\d+)$` | GET | giriş yapmış herkes |
| `^/fatura/(?P<fid>\d+)/duzenle$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/fatura/(?P<fid>\d+)/durum$` | POST | Admin, Muhasebe (+Admin) |
| `^/fatura/(?P<fid>\d+)/yazdir$` | GET | giriş yapmış herkes |
| `^/finansal$` | GET | giriş yapmış herkes |
| `^/finansal/urunler$` | GET | giriş yapmış herkes |
| `^/finansal/tahsilat$` | GET | giriş yapmış herkes |
| `^/finansal/butce$` | GET,POST | giriş yapmış herkes |
| `^/finansal/butce/(?P<bid>\d+)/sil$` | POST | Admin, Muhasebe (+Admin) |
| `^/garanti$` | GET | giriş yapmış herkes |
| `^/garanti/(?P<sid>\d+)$` | GET | giriş yapmış herkes |
| `^/garanti/(?P<sid>\d+)/guncelle$` | POST | Admin, Muhasebe, Servis (+Admin) |
| `^/garanti/yeni$` | GET,POST | Admin, Muhasebe, Servis (+Admin) |
| `^/irsaliye$` | GET | giriş yapmış herkes |
| `^/irsaliye/yeni$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/irsaliye/(?P<iid>\d+)$` | GET | giriş yapmış herkes |
| `^/irsaliye/(?P<iid>\d+)/duzenle$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/irsaliye/(?P<iid>\d+)/durum$` | POST | Admin, Muhasebe (+Admin) |
| `^/irsaliye/(?P<iid>\d+)/yazdir$` | GET | giriş yapmış herkes |
| `^/kartoteks$` | GET | giriş yapmış herkes |
| `^/kartoteks/cari$` | GET | giriş yapmış herkes |
| `^/kartoteks/stok$` | GET | giriş yapmış herkes |
| `^/kartoteks/cari/export$` | GET | giriş yapmış herkes |
| `^/kartoteks/stok/export$` | GET | giriş yapmış herkes |
| `^/kartoteks/cari/rapor$` | GET | giriş yapmış herkes |
| `^/kartoteks/stok/rapor$` | GET | giriş yapmış herkes |
| `^/kasa$` | GET | giriş yapmış herkes |
| `^/kasa/yeni$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/kasa/hareket$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/kasa/hareket/(?P<sid>\d+)/iptal$` | POST | Admin, Muhasebe, Satis (+Admin) |
| `^/kasa/rapor$` | GET | giriş yapmış herkes |
| `^/kasa/hareket/(?P<hid>\d+)/fis$` | GET | giriş yapmış herkes |
| `^/muhasebe$` | GET | giriş yapmış herkes |
| `^/muhasebe/yeni$` | GET,POST | Admin, Muhasebe (+Admin) |
| `^/muhasebe/toplu-uret$` | POST | Admin, Muhasebe (+Admin) |
| `^/muhasebe/acilis$` | POST | Admin, Muhasebe (+Admin) |
| `^/muhasebe/kapanis$` | POST | Admin, Muhasebe (+Admin) |
| `^/muhasebe/hesaplar$` | GET | giriş yapmış herkes |
| `^/muhasebe/mizan$` | GET | giriş yapmış herkes |
| `^/muhasebe/defter$` | GET | giriş yapmış herkes |
| `^/muhasebe/(?P<fid>\d+)$` | GET | giriş yapmış herkes |
| `^/muhasebe/(?P<fid>\d+)/durum$` | POST | Admin, Muhasebe (+Admin) |
| `^/notlar$` | GET | giriş yapmış herkes |
| `^/notlar/yeni$` | GET,POST | giriş yapmış herkes |
| `^/notlar/(?P<nid>\d+)/sil$` | POST | giriş yapmış herkes |
| `^/servis$` | GET | giriş yapmış herkes |
| `^/servis/yeni$` | GET,POST | Admin, Servis, Muhasebe (+Admin) |
| `^/servis/(?P<sid>\d+)$` | GET | giriş yapmış herkes |
| `^/servis/(?P<sid>\d+)/durum$` | POST | Admin, Servis, Muhasebe (+Admin) |
| `^/servis/(?P<sid>\d+)/faturala$` | POST | Admin, Servis, Muhasebe (+Admin) |
| `^/servis/(?P<sid>\d+)/guncelle$` | POST | Admin, Servis, Muhasebe (+Admin) |
| `^/servis/(?P<sid>\d+)/parca$` | POST | Admin, Servis, Muhasebe (+Admin) |
| `^/servis/parca/(?P<pid>\d+)/sil$` | POST | Admin, Servis, Muhasebe (+Admin) |
| `^/siparis$` | GET | giriş yapmış herkes |
| `^/siparis/yeni$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/siparis/(?P<sid>\d+)$` | GET | giriş yapmış herkes |
| `^/siparis/(?P<sid>\d+)/duzenle$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/siparis/(?P<sid>\d+)/durum$` | POST | Admin, Muhasebe (+Admin) |
| `^/siparis/(?P<sid>\d+)/yazdir$` | GET | giriş yapmış herkes |
| `^/stok$` | GET | giriş yapmış herkes |
| `^/stok/yeni$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/(?P<sid>\d+)/duzenle$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/(?P<sid>\d+)$` | GET | giriş yapmış herkes |
| `^/stok/(?P<sid>\d+)/not$` | POST | giriş yapmış herkes |
| `^/stok/(?P<sid>\d+)/minmax$` | POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/hareketler$` | GET | giriş yapmış herkes |
| `^/stok/hareketler/export$` | GET | giriş yapmış herkes |
| `^/stok/hareketler/rapor$` | GET | giriş yapmış herkes |
| `^/stok/ara$` | GET | giriş yapmış herkes |
| `^/stok/hareket/yeni$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/sayim$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/sayim/(?P<sid>\d+)$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/sayim/(?P<sid>\d+)/tamamla$` | POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/transferler$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/transferler/(?P<tid>\d+)$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/transferler/(?P<tid>\d+)/tamamla$` | POST | Admin, Muhasebe, Depo (+Admin) |
| `^/stok/toplu$` | GET,POST | Admin, Muhasebe (+Admin) |
| `^/stok/depolar$` | GET,POST | Admin, Muhasebe, Depo (+Admin) |
| `^/sube$` | GET | giriş yapmış herkes |
| `^/sube/yeni$` | GET,POST | Admin (+Admin) |
| `^/sube/(?P<sid>\d+)$` | GET | giriş yapmış herkes |
| `^/sube/(?P<sid>\d+)/duzenle$` | GET,POST | Admin (+Admin) |
| `^/sube/kullanicilar$` | GET,POST | Admin (+Admin) |
| `^/teklif$` | GET | giriş yapmış herkes |
| `^/teklif/yeni$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/teklif/(?P<tid>\d+)$` | GET | giriş yapmış herkes |
| `^/teklif/(?P<tid>\d+)/duzenle$` | GET,POST | Admin, Muhasebe, Satis (+Admin) |
| `^/teklif/(?P<tid>\d+)/durum$` | POST | Admin, Muhasebe, Satis (+Admin) |
| `^/teklif/(?P<tid>\d+)/yazdir$` | GET | giriş yapmış herkes |
| `^/transfer$` | GET | giriş yapmış herkes |
