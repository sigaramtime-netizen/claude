# -*- coding: utf-8 -*-
"""D014 — Yazdırma/Çıktı Tamamlama + Tanım Verileri Düzenleme (v1.45.0) e2e testi.

16 kontrol. Sunucu 8080'de çalışırken:
    python3 test_d014_yazdirma_tanimlar.py

Kapsam (GM direktifi D014-yazdirma-tanimlar-duzenleme.md):
  A1 (1-4)   Makbuz + Servis fişi + Bakım sözleşmesi + Banka fişi (Wolvox #1e4e79)
  A2 (5-9)   Transfer sevk (fiyatsız) + Demirbaş amortisman + Talep + Alınan teklif
             + Teklif konsolidasyonu (yazdir_belge)
  A3 (10)    Rapor Yazdır butonları + POS fatura kısayolu
  B (11-14)  5 tip Düzenle + kod/tip/birim koruması + Marka pasifleştirme
  K1/FK (15-16) izolasyon + bütünlük + kalıntı temizliği
"""
import sqlite3

import requests

BASE = "http://127.0.0.1:8080"
DB = "data/erp.db"
MARK = "D014TEST"

ok, fail = [], []


def check(name, cond, detay=""):
    (ok if cond else fail).append(name)
    print((("  ✅ " if cond else "  ❌ ") + name + (f"  → {detay}" if detay else "")))


def q1(q, *a):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    r = c.execute(q, a).fetchone(); c.close(); return r


def qx(q, *a):
    c = sqlite3.connect(DB); c.execute(q, a); c.commit(); c.close()


def giris(kadi="admin", sifre="1234"):
    s = requests.Session()
    r = s.post(BASE + "/giris", data={"kullanici_adi": kadi, "sifre": sifre},
               allow_redirects=False)
    return s, r


s, r = giris()
assert r.status_code == 302, "admin girişi başarısız"

# --- Kurulum (MARK etiketli, test sonunda tamamı silinir) ---
qx("INSERT INTO cari_kart(kod, unvan, tip, sirket_id) VALUES(?,?,?,1)",
   MARK + "-M", MARK + " Musteri", "Musteri")
M = q1("SELECT id FROM cari_kart WHERE kod=?", MARK + "-M")["id"]
qx("INSERT INTO cari_kart(kod, unvan, tip, sirket_id) VALUES(?,?,?,1)",
   MARK + "-T", MARK + " Tedarikci", "Tedarikci")
T = q1("SELECT id FROM cari_kart WHERE kod=?", MARK + "-T")["id"]
qx("INSERT INTO kasa(kod, ad, aktif, sirket_id) VALUES(?,?,1,1)", MARK + "-K", MARK + " Kasa")
KASA = q1("SELECT id FROM kasa WHERE kod=?", MARK + "-K")["id"]
qx("INSERT INTO kasa_hareket(kasa_id, tarih, islem_tipi, tutar, aciklama, sirket_id) "
   "VALUES(?, date('now','localtime'), 'Açılış Bakiyesi', 50000, ?, 1)", KASA, MARK + " açılış")
qx("INSERT INTO banka_hesap(kod, ad, aktif, sirket_id) VALUES(?,?,1,1)", MARK + "-B", MARK + " Banka")
BANKA = q1("SELECT id FROM banka_hesap WHERE kod=?", MARK + "-B")["id"]
qx("INSERT INTO banka_hareket(banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, sirket_id) "
   "VALUES(?, date('now','localtime'), 'Havale/EFT Girişi', 2500, ?, ?, 1)", BANKA, M, MARK + " fis")
BH = q1("SELECT id FROM banka_hareket WHERE aciklama=?", MARK + " fis")["id"]
qx("INSERT INTO servis_kayit(servis_no, cari_id, cihaz, ariza, aksesuar, teknisyen_id, durum, "
   "garanti_kapsami, iscilik_ucreti, sirket_id) VALUES(?,?,?,?,?,?,?, ?,?,1)",
   MARK + "-SRV", M, MARK + " Cihaz", MARK + " Ariza", MARK + " Aksesuar", 1, "Alındı", 1, 500)
SRV = q1("SELECT id FROM servis_kayit WHERE servis_no=?", MARK + "-SRV")["id"]
qx("INSERT INTO servis_parca(servis_id, stok_id, miktar, birim_fiyat, tutar, sirket_id) "
   "VALUES(?,?,2,100,200,1)", SRV, 1)
qx("INSERT INTO bakim_sozlesme(sozlesme_no, cari_id, baslangic, bitis, periyot, bedel, "
   "para_birimi, durum, sirket_id) VALUES(?,?,?,?,?,?,?,?,1)",
   MARK + "-SOZ", M, "2026-01-01", "2026-12-31", "Aylik", 12000, "TRY", "Aktif")
SOZ = q1("SELECT id FROM bakim_sozlesme WHERE sozlesme_no=?", MARK + "-SOZ")["id"]
qx("INSERT INTO bakim_sozlesme_cihaz(sozlesme_id, stok_id, seri_no, cihaz_aciklama, sirket_id) "
   "VALUES(?,?,?, ?,1)", SOZ, 1, MARK + "-SERI", MARK + " cihaz")
qx("INSERT INTO depo_transfer(kaynak_depo_id, hedef_depo_id, tarih, durum, sirket_id) "
   "VALUES(1,2, date('now','localtime'), 'Taslak', 1)")
TR = q1("SELECT id FROM depo_transfer ORDER BY id DESC")["id"]
qx("INSERT INTO depo_transfer_kalem(transfer_id, stok_id, miktar, sirket_id) VALUES(?,?,5,1)", TR, 1)
STOK_AD = q1("SELECT ad FROM stok_kart WHERE id=1")["ad"]
STOK_HTML = STOK_AD.replace('"', "&#34;")  # Jinja tırnak kaçışı
qx("INSERT INTO demirbas(kod, ad, alis_tarihi, sirket_id) VALUES(?,?,?,1)",
   MARK + "-DB", MARK + " Demirbas", "2026-01-15")
DBS = q1("SELECT id FROM demirbas WHERE kod=?", MARK + "-DB")["id"]
qx("INSERT INTO demirbas_amortisman(demirbas_id, donem, tutar, birikmis, net_deger) "
   "VALUES(?, '2026-06', 1000, 6000, 6000)", DBS)
qx("INSERT INTO satin_alma_talebi(talep_no, durum, sirket_id) VALUES(?,?,1)", MARK + "-TLP", "Onay Bekliyor")
TLP = q1("SELECT id FROM satin_alma_talebi WHERE talep_no=?", MARK + "-TLP")["id"]
qx("INSERT INTO satin_alma_talebi_kalem(talep_id, stok_id, miktar, birim, tahmini_fiyat, sirket_id) "
   "VALUES(?,?,?,?,100,1)", TLP, 1, 10, "Adet")
qx("INSERT INTO alinan_teklif(teklif_no, tedarikci_id, tarih, para_birimi, durum, ara_toplam, "
   "iskonto_toplam, kdv_toplam, genel_toplam, sirket_id) VALUES(?,?,?,?,?,?,?,?,?,1)",
   MARK + "-ATF", T, "2026-09-15", "TRY", "Alındı", 1500, 0, 300, 1800)
ATF = q1("SELECT id FROM alinan_teklif WHERE teklif_no=?", MARK + "-ATF")["id"]
qx("INSERT INTO alinan_teklif_kalem(teklif_id, stok_id, miktar, birim, birim_fiyat, iskonto_orani, "
   "kdv_orani, tutar, sirket_id) VALUES(?,?,?,?,500,0,20,1800,1)", ATF, 1, 3, "Adet")
qx("INSERT INTO kategori(ad, aktif, sirket_id) VALUES(?,1,1)", MARK + " Kat")
KAT = q1("SELECT id FROM kategori WHERE ad=?", MARK + " Kat")["id"]
qx("INSERT INTO cari_grup(ad, tip, aktif, sirket_id) VALUES(?,?,1,1)", MARK + " Grup", "Bölge")
GRP = q1("SELECT id FROM cari_grup WHERE ad=?", MARK + " Grup")["id"]
qx("INSERT INTO para_birimi(kod, ad, aktif, sirket_id) VALUES(?,?,1,1)", "DT14", MARK + " Doviz")
PB = q1("SELECT id FROM para_birimi WHERE kod='DT14' AND sirket_id=1")["id"]
qx("INSERT INTO para_birimi(kod, ad, aktif, sirket_id) VALUES(?,?,1,1)", "DU14", MARK + " Bos")
PBB = q1("SELECT id FROM para_birimi WHERE kod='DU14' AND sirket_id=1")["id"]
qx("INSERT INTO birim(ad, aktif, sirket_id) VALUES(?,1,1)", MARK + " Birim")
BRM = q1("SELECT id FROM birim WHERE ad=?", MARK + " Birim")["id"]
qx("INSERT INTO marka(ad, aktif, sirket_id) VALUES(?,1,1)", MARK + " Marka")
MRK = q1("SELECT id FROM marka WHERE ad=?", MARK + " Marka")["id"]
# kullanım bağları (koruma testleri için)
qx("INSERT INTO stok_kart(kod, ad, kategori_id, marka_id, birim, para_birimi, sirket_id) "
   "VALUES(?,?,?,?,?,?,1)", MARK + "-STK", MARK + " Stok", KAT, MRK, MARK + " Birim", "DT14")
qx("INSERT INTO cari_kart(kod, unvan, tip, grup_id, sirket_id) VALUES(?,?,?, ?,1)",
   MARK + "-G", MARK + " Gruplu", "Musteri", GRP)
G = q1("SELECT id FROM cari_kart WHERE kod=?", MARK + "-G")["id"]
# D013 tahsilat → gerçek THS belgesi (makbuz testine girdi)
r = s.post(BASE + f"/cari/{M}/tahsilat", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "TRY"), ("kasa_id", str(KASA)),
    ("banka_hesap_id", str(BANKA)), ("aciklama", MARK + " makbuz"),
    ("p_tip", "Nakit"), ("p_tutar", "1000"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
    ("p_tip", "Havale"), ("p_tutar", "500"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
], allow_redirects=False)
assert r.status_code == 302, f"D013 tahsilat kurulumu başarısız: {r.status_code}"
BELGE = q1("SELECT belge_no FROM kasa_hareket WHERE cari_id=? AND belge_no LIKE 'THS-%' "
           "ORDER BY id DESC", M)["belge_no"]

print("BÖLÜM A1 — Fiziksel Çıktılar")
r = s.get(BASE + f"/cari/{M}/makbuz/{BELGE}")
h = r.text
check("1. makbuz 200 + belge/cari/kırılım/toplam/imza/kullanıcı",
      r.status_code == 200 and BELGE in h and MARK in h and "Nakit" in h and "Havale" in h
      and "1.500,00" in h and "admin" in h and "İmza" in h and "#1e4e79" in h,
      f"status={r.status_code}, belge={BELGE}")
r = s.get(BASE + f"/servis/{SRV}/yazdir")
h = r.text
check("2. servis fişi 200 + no/ariza/teknisyen/parça/işçilik",
      r.status_code == 200 and MARK + "-SRV" in h and MARK + " Ariza" in h and "admin" in h
      and STOK_HTML in h and "500,00" in h and "#1e4e79" in h,
      f"status={r.status_code}")
r = s.get(BASE + f"/bakim/sozlesme/{SOZ}/yazdir")
h = r.text
check("3. bakım sözleşmesi 200 + no/cihaz/bedel/koşullar",
      r.status_code == 200 and MARK + "-SOZ" in h and MARK + "-SERI" in h
      and "12.000,00" in h and "Sözleşme Koşulları" in h and "#1e4e79" in h,
      f"status={r.status_code}")
r = s.get(BASE + f"/banka/hareket/{BH}/fis")
h = r.text
check("4. banka fişi 200 + BANKA FİŞİ/hesap/tutar",
      r.status_code == 200 and "BANKA FİŞİ" in h and MARK + " Banka" in h
      and "2.500,00" in h and "#1e4e79" in h,
      f"status={r.status_code}")

print("BÖLÜM A2 — Arşiv Çıktıları (yazdir_belge)")
r = s.get(BASE + f"/stok/transferler/{TR}/yazdir")
h = r.text
check("5. transfer sevk 200 + DT-no/ürün/depolar, fiyatsız",
      r.status_code == 200 and f"DT-{TR:06d}" in h and STOK_HTML in h
      and "Birim Fiyat" not in h and "Genel Toplam" not in h,
      f"status={r.status_code}")
r = s.get(BASE + "/demirbas/amortisman/yazdir?yil=2026")
h = r.text
check("6. demirbaş amortisman 200 + kod/dönem/net değer",
      r.status_code == 200 and MARK + "-DB" in h and "2026-06" in h
      and "6.000,00" in h and "#1e4e79" in h,
      f"status={r.status_code}")
r = s.get(BASE + f"/satin-alma/talepler/{TLP}/yazdir")
h = r.text
check("7. satın alma talebi 200 + no/ürün/tahmini toplam",
      r.status_code == 200 and MARK + "-TLP" in h and STOK_HTML in h
      and "1.000,00" in h and "Genel Toplam" in h,
      f"status={r.status_code}")
r = s.get(BASE + f"/satin-alma/teklifler/{ATF}/yazdir")
h = r.text
check("8. alınan teklif 200 + no/tedarikçi/genel toplam",
      r.status_code == 200 and MARK + "-ATF" in h and MARK + " Tedarikci" in h
      and "1.800,00" in h and "Genel Toplam" in h,
      f"status={r.status_code}")
seed_tkf = q1("SELECT id, teklif_no FROM teklif WHERE sirket_id=1 ORDER BY id LIMIT 1")
r = s.get(BASE + f"/teklif/{seed_tkf['id']}/yazdir")
h = r.text
check("9. teklif konsolidasyonu: ortak şablon (no + Genel Toplam)",
      r.status_code == 200 and seed_tkf["teklif_no"] in h and "Genel Toplam" in h,
      f"status={r.status_code}, no={seed_tkf['teklif_no']}")

print("BÖLÜM A3 — Rapor Butonları + POS Kısayolu")
crm_ok = "window.print" in s.get(BASE + "/crm/rapor").text
eks_ok = "window.print" in s.get(BASE + "/satin-alma/eksik-teslimatlar").text
rap_ok = "window.print" in s.get(BASE + "/satin-alma/rapor").text
ps = q1("SELECT id, fatura_id FROM pos_satis ORDER BY id LIMIT 1")
pos_ok = f"/fatura/{ps['fatura_id']}/yazdir" in s.get(BASE + f"/pos/satis/{ps['id']}").text
check("10. CRM/eksik/rapor Yazdır + POS fatura kısayolu",
      crm_ok and eks_ok and rap_ok and pos_ok,
      f"crm={crm_ok}, eksik={eks_ok}, rapor={rap_ok}, pos={pos_ok}")

print("BÖLÜM B — Tanım Düzenleme + Koruma + Marka Pasif")
def duzenle(tip_, kid, **data):
    return s.post(BASE + f"/ayarlar/tanimlar/{tip_}/{kid}/duzenle", data=data,
                  allow_redirects=False)
r1 = duzenle("kategori", KAT, ad=MARK + " Kat Yeni")
r2 = duzenle("cari-grup", GRP, ad=MARK + " Grup Yeni", tip="Bölge", aciklama="yeni")
r3 = duzenle("para-birimi", PB, ad=MARK + " Doviz Yeni", kod="DT14")
r4 = duzenle("marka", MRK, ad=MARK + " Marka Yeni")
check("11. 4 tipte ad düzenleme OK (kategori/grup/döviz/marka)",
      r1.status_code == 302 and q1("SELECT ad FROM kategori WHERE id=?", KAT)["ad"] == MARK + " Kat Yeni"
      and r2.status_code == 302 and q1("SELECT ad FROM cari_grup WHERE id=?", GRP)["ad"] == MARK + " Grup Yeni"
      and r3.status_code == 302 and q1("SELECT ad FROM para_birimi WHERE id=?", PB)["ad"] == MARK + " Doviz Yeni"
      and r4.status_code == 302 and q1("SELECT ad FROM marka WHERE id=?", MRK)["ad"] == MARK + " Marka Yeni",
      f"status={r1.status_code}/{r2.status_code}/{r3.status_code}/{r4.status_code}")
r = duzenle("para-birimi", PB, ad=MARK + " Doviz Yeni", kod="YYY")
kod_simdi = q1("SELECT kod FROM para_birimi WHERE id=?", PB)["kod"]
r_bos = duzenle("para-birimi", PBB, ad=MARK + " Bos", kod="ZZ9")
kod_bos = q1("SELECT kod FROM para_birimi WHERE id=?", PBB)["kod"]
check("12. kullanılan PB kodu kilitli (DT14 korunur) + boşta kod değişir",
      r.status_code == 302 and kod_simdi == "DT14"
      and r_bos.status_code == 302 and kod_bos == "ZZ9",
      f"kullanılan={kod_simdi}, boşta={kod_bos}")
r = s.post(BASE + f"/ayarlar/tanimlar/marka/{MRK}/durum", allow_redirects=False)
pasif = q1("SELECT aktif FROM marka WHERE id=?", MRK)["aktif"] == 0
stok_form = s.get(BASE + "/stok/yeni").text
check("13. marka pasifleştirme + stok formunda seçilemez",
      r.status_code == 302 and pasif and MARK + " Marka Yeni" not in stok_form,
      f"status={r.status_code}, aktif=0")
r = duzenle("cari-grup", GRP, ad=MARK + " Grup Yeni", tip="Sektör", aciklama="")
tip_simdi = q1("SELECT tip FROM cari_grup WHERE id=?", GRP)["tip"]
r2 = duzenle("birim", BRM, ad=MARK + " Birim Yeni")
ad_simdi = q1("SELECT ad FROM birim WHERE id=?", BRM)["ad"]
check("14. kullanılan grup tipi + birim adı kilitli",
      tip_simdi == "Bölge" and ad_simdi == MARK + " Birim",
      f"tip={tip_simdi}, birim={ad_simdi}")

print("BÖLÜM K1/FK — İzolasyon + Bütünlük")
qx("INSERT INTO sirket(kod, unvan, aktif) VALUES(?,?,1)", MARK + "-S", MARK + " Sirket")
S2 = q1("SELECT id FROM sirket WHERE kod=?", MARK + "-S")["id"]
qx("INSERT INTO servis_kayit(servis_no, cihaz, sirket_id) VALUES(?,?,?)", MARK + "-YAB", MARK + "-Y", S2)
SY = q1("SELECT id FROM servis_kayit WHERE servis_no=?", MARK + "-YAB")["id"]
qx("INSERT INTO marka(ad, aktif, sirket_id) VALUES(?,1,?)", MARK + " Yabanci", S2)
MY = q1("SELECT id FROM marka WHERE ad=?", MARK + " Yabanci")["id"]
r_srv = s.get(BASE + f"/servis/{SY}/yazdir", allow_redirects=False)
r_mrk = duzenle("marka", MY, ad="Hack")
ad_yab = q1("SELECT ad FROM marka WHERE id=?", MY)["ad"]
check("15. K1: yabancı servis yazdır + yabancı marka düzenle engellenir",
      r_srv.status_code == 302 and r_mrk.status_code == 302 and ad_yab == MARK + " Yabanci",
      f"servis={r_srv.status_code}, marka={r_mrk.status_code}")

print("BÖLÜM F — Temizlik")
_c = sqlite3.connect(DB)
kh_ids = [r[0] for r in _c.execute("SELECT id FROM kasa_hareket WHERE kasa_id=? OR cari_id IN (?,?)",
                                   (KASA, M, T)).fetchall()]
bh_ids = [r[0] for r in _c.execute("SELECT id FROM banka_hareket WHERE banka_hesap_id=? OR cari_id IN (?,?)",
                                   (BANKA, M, T)).fetchall()]
_c.close()
for modul, ids in (("Kasa", kh_ids), ("Banka", bh_ids)):
    for i in ids:
        qx("DELETE FROM yevmiye_kalem WHERE yevmiye_id IN "
           "(SELECT id FROM yevmiye WHERE kaynak_modul=? AND kaynak_id=?)", modul, i)
        qx("DELETE FROM yevmiye WHERE kaynak_modul=? AND kaynak_id=?", modul, i)
        qx("DELETE FROM audit_log WHERE tablo=? AND kayit_id=?",
           {"Kasa": "kasa_hareket", "Banka": "banka_hareket"}[modul], i)
qx("DELETE FROM cari_hareket WHERE cari_id IN (?,?,?)", M, T, G)
qx("DELETE FROM kasa_hareket WHERE kasa_id=? OR cari_id IN (?,?)", KASA, M, T)
qx("DELETE FROM banka_hareket WHERE banka_hesap_id=? OR cari_id IN (?,?)", BANKA, M, T)
qx("DELETE FROM servis_parca WHERE servis_id IN (?,?)", SRV, SY)
qx("DELETE FROM servis_kayit WHERE id IN (?,?)", SRV, SY)
qx("DELETE FROM bakim_sozlesme_cihaz WHERE sozlesme_id=?", SOZ)
qx("DELETE FROM bakim_sozlesme WHERE id=?", SOZ)
qx("DELETE FROM depo_transfer_kalem WHERE transfer_id=?", TR)
qx("DELETE FROM depo_transfer WHERE id=?", TR)
qx("DELETE FROM demirbas_amortisman WHERE demirbas_id=?", DBS)
qx("DELETE FROM demirbas WHERE id=?", DBS)
qx("DELETE FROM satin_alma_talebi_kalem WHERE talep_id=?", TLP)
qx("DELETE FROM satin_alma_talebi WHERE id=?", TLP)
qx("DELETE FROM alinan_teklif_kalem WHERE teklif_id=?", ATF)
qx("DELETE FROM alinan_teklif WHERE id=?", ATF)
qx("DELETE FROM stok_kart WHERE kod=?", MARK + "-STK")
qx("DELETE FROM cari_kart WHERE id IN (?,?,?)", M, T, G)
qx("DELETE FROM kategori WHERE id=?", KAT)
qx("DELETE FROM cari_grup WHERE id=?", GRP)
qx("DELETE FROM para_birimi WHERE id IN (?,?)", PB, PBB)
qx("DELETE FROM birim WHERE id=?", BRM)
qx("DELETE FROM marka WHERE id IN (?,?)", MRK, MY)
qx("DELETE FROM kasa WHERE id=?", KASA)
qx("DELETE FROM banka_hesap WHERE id=?", BANKA)
qx("DELETE FROM sirket WHERE id=?", S2)
_c2 = sqlite3.connect(DB)
fk = _c2.execute("PRAGMA foreign_key_check").fetchall()
_c2.close()
kal = 0
for t, kol in (("cari_kart", "kod"), ("kasa", "kod"), ("banka_hesap", "kod"),
               ("servis_kayit", "servis_no"), ("bakim_sozlesme", "sozlesme_no"),
               ("demirbas", "kod"), ("satin_alma_talebi", "talep_no"),
               ("alinan_teklif", "teklif_no"), ("kategori", "ad"), ("cari_grup", "ad"),
               ("para_birimi", "ad"), ("birim", "ad"), ("marka", "ad"),
               ("sirket", "kod"), ("stok_kart", "kod")):
    kal += q1(f"SELECT COUNT(*) c FROM {t} WHERE {kol} LIKE ?", MARK + "%")["c"]
kal += q1("SELECT COUNT(*) c FROM kasa_hareket WHERE aciklama LIKE ?", "%" + MARK + "%")["c"]
kal += q1("SELECT COUNT(*) c FROM banka_hareket WHERE aciklama LIKE ?", "%" + MARK + "%")["c"]
kal += q1("SELECT COUNT(*) c FROM cari_hareket WHERE aciklama LIKE ?", "%" + MARK + "%")["c"]
check("16. FK bütünlüğü 0 + D014TEST kalıntısı yok", len(fk) == 0 and kal == 0,
      f"fk={len(fk)}, kalıntı={kal}")

print(f"\n=== SONUÇ: {len(ok)} başarılı / {len(fail)} başarısız (toplam {len(ok) + len(fail)}) ===")
if fail:
    print("BAŞARISIZ:", fail)
    raise SystemExit(1)
print("TÜM D014 TESTLERİ GEÇTİ ✅")
