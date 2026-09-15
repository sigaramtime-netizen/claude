# -*- coding: utf-8 -*-
"""D013 — Cari Tahsilat / Ödeme Ekranı (v1.44.0) e2e testi.

14 kontrol. Sunucu 8080'de çalışırken:
    python3 test_d013_cari_tahsilat_odeme.py

Kapsam (GM direktifi D013-cari-tahsilat-odeme.md):
  1-2  GET formları (tahsilat→Alınan, odeme→Verilen) + kart/ekstre butonları
  3-5  Karışık tahsilat (Nakit+Kart): kasa + banka net + cari alacak + yevmiye + kısmi kalan
  6    Havale ödeme: banka çıkış + cari borç + 320/102 fişi
  7-8  Çek (Alınan) tahsilat + Senet (Verilen) ödeme: cek_senet akışı + fiş
  9    Döviz tahsilat: kur sabitleme + TL karşılığı (K18)
  10   Avans uyarısı: fazla tutar engellenmez, "avans" arayüzde görünür
  11   Yetki: Satis tahsilat OK, odeme POST/GET → 403
  12   K1: başka şirket carisi → 403 + kayıt yok
  13   Çek vadesiz → hata + kayıt yok
  14   FK bütünlüğü + D013TEST kalıntısı yok
"""
import sqlite3

import requests

BASE = "http://127.0.0.1:8080"
DB = "data/erp.db"
MARK = "D013TEST"

ok, fail = [], []


def check(name, cond, detay=""):
    (ok if cond else fail).append(name)
    print((("  ✅ " if cond else "  ❌ ") + name + (f"  → {detay}" if detay else "")))


def q1(q, *a):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    r = c.execute(q, a).fetchone(); c.close(); return r


def qall(q, *a):
    c = sqlite3.connect(DB); c.row_factory = sqlite3.Row
    r = c.execute(q, a).fetchall(); c.close(); return r


def qx(q, *a):
    c = sqlite3.connect(DB); c.execute(q, a); c.commit(); c.close()


def giris(kadi="admin", sifre="1234"):
    s = requests.Session()
    r = s.post(BASE + "/giris", data={"kullanici_adi": kadi, "sifre": sifre},
               allow_redirects=False)
    return s, r


def bakiye(cid):
    r = q1("SELECT COALESCE(SUM(borc),0) b, COALESCE(SUM(alacak),0) a "
           "FROM cari_hareket WHERE cari_id=?", cid)
    return round(r["b"] - r["a"], 2)


def fis_kalemler(kaynak_modul, kaynak_id, sahne=None):
    if sahne is None:
        f = q1("SELECT id FROM yevmiye WHERE kaynak_modul=? AND kaynak_id=? "
               "AND COALESCE(kaynak_sahne,'')=''",
               kaynak_modul, kaynak_id)
    else:
        f = q1("SELECT id FROM yevmiye WHERE kaynak_modul=? AND kaynak_id=? AND kaynak_sahne=?",
               kaynak_modul, kaynak_id, sahne)
    if not f:
        return None, []
    rows = qall("SELECT h.kod, k.borc, k.alacak FROM yevmiye_kalem k "
                "JOIN hesap h ON h.id=k.hesap_id WHERE k.yevmiye_id=?", f["id"])
    return f["id"], [(r["kod"], r["borc"], r["alacak"]) for r in rows]


s, r = giris()
assert r.status_code == 302, "admin girişi başarısız"

# --- Kurulum (MARK etiketli, test sonunda tamamı silinir) ---
qx("INSERT INTO kasa(kod, ad, aktif, sirket_id) VALUES(?,?,1,1)", MARK + "-K", MARK + " Kasa")
KASA = q1("SELECT id FROM kasa WHERE kod=?", MARK + "-K")["id"]
qx("INSERT INTO kasa_hareket(kasa_id, tarih, islem_tipi, tutar, aciklama, sirket_id) "
   "VALUES(?, date('now','localtime'), 'Açılış Bakiyesi', 100000, ?, 1)", KASA, MARK + " açılış")
qx("INSERT INTO banka_hesap(kod, ad, aktif, sirket_id) VALUES(?,?,1,1)", MARK + "-B", MARK + " Banka")
BANKA = q1("SELECT id FROM banka_hesap WHERE kod=?", MARK + "-B")["id"]
qx("INSERT INTO banka_hareket(banka_hesap_id, tarih, islem_tipi, tutar, aciklama, sirket_id) "
   "VALUES(?, date('now','localtime'), 'Açılış Bakiyesi', 100000, ?, 1)", BANKA, MARK + " açılış")
qx("INSERT INTO pos_terminal(ad, kasa_id, banka_id, depo_id, komisyon_orani, aktif, sirket_id) "
   "VALUES(?,?,?,?,2.0,1,1)", MARK + " Terminal", KASA, BANKA, 1)
TERM = q1("SELECT id FROM pos_terminal WHERE ad=?", MARK + " Terminal")["id"]
qx("INSERT INTO cari_kart(kod, unvan, tip, sirket_id) VALUES(?,?,?,1)",
   MARK + "-M", MARK + " Musteri", "Musteri")
M = q1("SELECT id FROM cari_kart WHERE kod=?", MARK + "-M")["id"]
qx("INSERT INTO cari_kart(kod, unvan, tip, sirket_id) VALUES(?,?,?,1)",
   MARK + "-T", MARK + " Tedarikci", "Tedarikci")
T = q1("SELECT id FROM cari_kart WHERE kod=?", MARK + "-T")["id"]
qx("INSERT INTO cari_hareket(cari_id, tarih, belge_tipi, belge_no, aciklama, borc, alacak, sirket_id) "
   "VALUES(?, date('now','localtime'), 'Açılış', ?, ?, 10000, 0, 1)", M, MARK + "-AC", MARK + " açılış")
qx("INSERT INTO cari_hareket(cari_id, tarih, belge_tipi, belge_no, aciklama, borc, alacak, sirket_id) "
   "VALUES(?, date('now','localtime'), 'Açılış', ?, ?, 0, 8000, 1)", T, MARK + "-AC", MARK + " açılış")

print("BÖLÜM A — Formlar + Butonlar")
r = s.get(BASE + f"/cari/{M}/tahsilat")
check("1. GET tahsilat 200 + Alınan notu", r.status_code == 200 and "Alınan" in r.text,
      f"status={r.status_code}")
r = s.get(BASE + f"/cari/{T}/odeme")
check("2. GET odeme 200 + Verilen notu + kart/ekstre butonları",
      r.status_code == 200 and "Verilen" in r.text
      and f"/cari/{T}/tahsilat" in s.get(BASE + f"/cari/{T}").text
      and f"/cari/{T}/odeme" in s.get(BASE + f"/cari/{T}/ekstre").text,
      f"status={r.status_code}")

print("BÖLÜM B — Karışık Tahsilat (Nakit 3000 + Kart 2000, komisyon %2)")
r = s.post(BASE + f"/cari/{M}/tahsilat", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "TRY"), ("doviz_kur", ""),
    ("kasa_id", str(KASA)), ("banka_hesap_id", str(BANKA)), ("terminal_id", str(TERM)),
    ("aciklama", MARK + " karisik"),
    ("p_tip", "Nakit"), ("p_tutar", "3000"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
    ("p_tip", "Kart"), ("p_tutar", "2000"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
], allow_redirects=False)
kh = q1("SELECT * FROM kasa_hareket WHERE cari_id=? AND islem_tipi='Nakit Girişi' "
        "ORDER BY id DESC", M)
bh = q1("SELECT * FROM banka_hareket WHERE cari_id=? ORDER BY id DESC", M)
ch = qall("SELECT * FROM cari_hareket WHERE cari_id=? AND belge_tipi='Tahsilat' "
          "AND aciklama LIKE ?", M, "%" + MARK + "%")
alacak_top = round(sum(h["alacak"] or 0 for h in ch), 2)
fid_k, kal_k = fis_kalemler("Kasa", kh["id"]) if kh else (None, [])
fid_b, kal_b = fis_kalemler("Banka", bh["id"]) if bh else (None, [])
check("3. kasa 3000 + banka net 1960 + cari alacak 5000 + 2 fiş",
      r.status_code == 302 and kh and abs(kh["tutar"] - 3000) < 0.01
      and kh["ilgili_modul"] == "CariTahsilat"
      and bh and abs(bh["tutar"] - 1960) < 0.01 and "komisyon" in (bh["aciklama"] or "").lower()
      and abs(alacak_top - 5000) < 0.01 and fid_k and fid_b,
      f"status={r.status_code}, kasa={kh['tutar'] if kh else None}, banka={bh['tutar'] if bh else None}, "
      f"alacak={alacak_top}, fis={fid_k}/{fid_b}")
kodlar_k = sorted(k[0] for k in kal_k)
check("4. kasa fişi 100/120 + banka fişi 102/120 (müşteri)",
      "100" in kodlar_k and "120" in kodlar_k
      and sorted(k[0] for k in kal_b) == ["102", "120"],
      f"kasa={kal_k}, banka={kal_b}")
check("5. kısmi kapatma: kalan bakiye 5000", abs(bakiye(M) - 5000) < 0.01,
      f"bakiye={bakiye(M)}")

print("BÖLÜM C — Karışık Ödeme (Havale 3000 + Nakit 500)")
r = s.post(BASE + f"/cari/{T}/odeme", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "TRY"), ("doviz_kur", ""),
    ("kasa_id", str(KASA)), ("banka_hesap_id", str(BANKA)), ("aciklama", MARK + " havale"),
    ("p_tip", "Havale"), ("p_tutar", "3000"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
    ("p_tip", "Nakit"), ("p_tutar", "500"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
], allow_redirects=False)
bh2 = q1("SELECT * FROM banka_hareket WHERE cari_id=? ORDER BY id DESC", T)
kh2 = q1("SELECT * FROM kasa_hareket WHERE cari_id=? AND islem_tipi='Nakit Çıkışı' "
         "ORDER BY id DESC", T)
ch2 = qall("SELECT * FROM cari_hareket WHERE cari_id=? AND belge_tipi='Ödeme' "
           "AND aciklama LIKE ?", T, "%" + MARK + "%")
borc_top = round(sum(h["borc"] or 0 for h in ch2), 2)
fid_b2, kal_b2 = fis_kalemler("Banka", bh2["id"]) if bh2 else (None, [])
fid_k2, kal_k2 = fis_kalemler("Kasa", kh2["id"]) if kh2 else (None, [])
check("6. banka çıkış 3000 + kasa çıkış 500 + cari borç 3500 + 320 fişleri + kalan -4500",
      r.status_code == 302 and bh2 and bh2["islem_tipi"] == "Havale/EFT Çıkışı"
      and abs(bh2["tutar"] - 3000) < 0.01 and bh2["ilgili_modul"] == "CariOdeme"
      and kh2 and abs(kh2["tutar"] - 500) < 0.01 and kh2["ilgili_modul"] == "CariOdeme"
      and abs(borc_top - 3500) < 0.01 and fid_b2 and fid_k2
      and sorted(k[0] for k in kal_b2) == ["102", "320"]
      and sorted(k[0] for k in kal_k2) == ["100", "320"]
      and abs(bakiye(T) - (-4500)) < 0.01,
      f"status={r.status_code}, banka_fis={kal_b2}, kasa_fis={kal_k2}, bakiye={bakiye(T)}")

print("BÖLÜM D — Çek/Senet İki Yön")
r = s.post(BASE + f"/cari/{M}/tahsilat", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "TRY"), ("aciklama", MARK + " cek"),
    ("p_tip", "Cek"), ("p_tutar", "1000"), ("p_no", MARK + "-CEK1"),
    ("p_banka", MARK + " Bank"), ("p_vade", "2026-10-15"),
], allow_redirects=False)
cek = q1("SELECT * FROM cek_senet WHERE no=?", MARK + "-CEK1")
fid_c, _kal_c = fis_kalemler("CekSenet", cek["id"], "giris") if cek else (None, [])
ch_cek = q1("SELECT * FROM cari_hareket WHERE ilgili_modul='CekSenet' AND ilgili_kayit_id=?",
            cek["id"]) if cek else None
check("7. tahsilatta çek → tip Alinan + cari alacak 1000 + giris fişi",
      r.status_code == 302 and cek and cek["tip"] == "Alinan" and cek["tur"] == "Cek"
      and ch_cek and abs(ch_cek["alacak"] - 1000) < 0.01 and fid_c,
      f"status={r.status_code}, tip={cek['tip'] if cek else None}, fis={fid_c}")
r = s.post(BASE + f"/cari/{T}/odeme", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "TRY"), ("aciklama", MARK + " senet"),
    ("p_tip", "Senet"), ("p_tutar", "1000"), ("p_no", MARK + "-SEN1"),
    ("p_banka", ""), ("p_vade", "2026-11-15"),
], allow_redirects=False)
sen = q1("SELECT * FROM cek_senet WHERE no=?", MARK + "-SEN1")
fid_s, _kal_s = fis_kalemler("CekSenet", sen["id"], "giris") if sen else (None, [])
ch_sen = q1("SELECT * FROM cari_hareket WHERE ilgili_modul='CekSenet' AND ilgili_kayit_id=?",
            sen["id"]) if sen else None
check("8. ödemede senet → tip Verilen + cari borç 1000 + giris fişi",
      r.status_code == 302 and sen and sen["tip"] == "Verilen" and sen["tur"] == "Senet"
      and ch_sen and abs(ch_sen["borc"] - 1000) < 0.01 and fid_s,
      f"status={r.status_code}, tip={sen['tip'] if sen else None}, fis={fid_s}")

print("BÖLÜM E — Döviz + Avans + Yetki + K1 + Vade")
r = s.post(BASE + f"/cari/{M}/tahsilat", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "USD"), ("doviz_kur", "40"),
    ("kasa_id", str(KASA)), ("aciklama", MARK + " doviz"),
    ("p_tip", "Nakit"), ("p_tutar", "50"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
], allow_redirects=False)
kh_d = q1("SELECT * FROM kasa_hareket WHERE cari_id=? AND para_birimi='USD' ORDER BY id DESC", M)
ch_d = q1("SELECT * FROM cari_hareket WHERE cari_id=? AND belge_tipi='Tahsilat' "
          "AND para_birimi='USD' ORDER BY id DESC", M)
check("9. USD 50 kur 40 → cari alacak 2000 TL + kur sabitlenmiş",
      r.status_code == 302 and kh_d and abs(kh_d["doviz_kur"] - 40) < 0.001
      and ch_d and abs(ch_d["alacak"] - 2000) < 0.01 and ch_d["para_birimi"] == "USD"
      and abs(bakiye(M) - 2000) < 0.01,
      f"status={r.status_code}, alacak={ch_d['alacak'] if ch_d else None}, bakiye={bakiye(M)}")
r = s.post(BASE + f"/cari/{M}/tahsilat", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "TRY"), ("kasa_id", str(KASA)),
    ("aciklama", MARK + " avans"),
    ("p_tip", "Nakit"), ("p_tutar", "5000"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
], allow_redirects=True)
check("10. fazla tahsilat engellenmez + 'avans' uyarısı arayüzde + bakiye -3000",
      "avans" in r.text.lower() and abs(bakiye(M) - (-3000)) < 0.01,
      f"bakiye={bakiye(M)}")
sv, _rv = giris("satis", "1234")
r_opost = sv.post(BASE + f"/cari/{T}/odeme", data=[("p_tip", "Nakit"), ("p_tutar", "10")],
                 allow_redirects=False)
r_oget = sv.get(BASE + f"/cari/{T}/odeme", allow_redirects=False)
r = sv.post(BASE + f"/cari/{M}/tahsilat", data=[
    ("tarih", "2026-09-15"), ("para_birimi", "TRY"), ("kasa_id", str(KASA)),
    ("aciklama", MARK + " satis"),
    ("p_tip", "Nakit"), ("p_tutar", "100"), ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
], allow_redirects=False)
check("11. Satis: tahsilat 302 OK, odeme POST+GET → 403",
      r.status_code == 302 and r_opost.status_code == 403 and r_oget.status_code == 403,
      f"tahsilat={r.status_code}, odeme_post={r_opost.status_code}, odeme_get={r_oget.status_code}")
qx("INSERT INTO sirket(kod, unvan, aktif) VALUES(?,?,1)", MARK + "-S", MARK + " Sirket")
S2 = q1("SELECT id FROM sirket WHERE kod=?", MARK + "-S")["id"]
qx("INSERT INTO cari_kart(kod, unvan, tip, sirket_id) VALUES(?,?,?,?)",
   MARK + "-X", MARK + " Yabanci", "Musteri", S2)
X = q1("SELECT id FROM cari_kart WHERE kod=?", MARK + "-X")["id"]
n_kh_once = q1("SELECT COUNT(*) c FROM kasa_hareket")["c"]
r = s.post(BASE + f"/cari/{X}/tahsilat", data=[
    ("kasa_id", str(KASA)), ("p_tip", "Nakit"), ("p_tutar", "100"),
    ("p_no", ""), ("p_banka", ""), ("p_vade", ""),
], allow_redirects=False)
check("12. K1: başka şirket carisi → 403 + kayıt yok",
      r.status_code == 403 and q1("SELECT COUNT(*) c FROM kasa_hareket")["c"] == n_kh_once
      and bakiye(X) == 0,
      f"status={r.status_code}")
r = s.post(BASE + f"/cari/{M}/tahsilat", data=[
    ("aciklama", MARK + " vadesiz"),
    ("p_tip", "Cek"), ("p_tutar", "500"), ("p_no", MARK + "-VADESIZ"),
    ("p_banka", ""), ("p_vade", ""),
], allow_redirects=False)
check("13. çek vadesiz → forma dönüş (302) + kayıt yok",
      r.status_code == 302 and "/tahsilat" in (r.headers.get("Location") or "")
      and not q1("SELECT id FROM cek_senet WHERE no=?", MARK + "-VADESIZ"),
      f"status={r.status_code}, loc={r.headers.get('Location')}")

print("BÖLÜM F — Temizlik + Bütünlük")

kh_ids = [r["id"] for r in qall("SELECT id FROM kasa_hareket WHERE kasa_id=? OR cari_id IN (?,?,?)",
                                KASA, M, T, X)]
bh_ids = [r["id"] for r in qall("SELECT id FROM banka_hareket WHERE banka_hesap_id=? OR cari_id IN (?,?)",
                                BANKA, M, T)]
cs_ids = [r["id"] for r in qall("SELECT id FROM cek_senet WHERE cari_id IN (?,?)", M, T)]
for modul, ids in (("Kasa", kh_ids), ("Banka", bh_ids), ("CekSenet", cs_ids)):
    for i in ids:
        qx("DELETE FROM yevmiye_kalem WHERE yevmiye_id IN "
           "(SELECT id FROM yevmiye WHERE kaynak_modul=? AND kaynak_id=?)", modul, i)
        qx("DELETE FROM yevmiye WHERE kaynak_modul=? AND kaynak_id=?", modul, i)
        qx("DELETE FROM audit_log WHERE tablo=? AND kayit_id=?",
           {"Kasa": "kasa_hareket", "Banka": "banka_hareket", "CekSenet": "cek_senet"}[modul], i)
qx(f"DELETE FROM cari_hareket WHERE cari_id IN (?,?,?)", M, T, X)
qx(f"DELETE FROM kasa_hareket WHERE kasa_id=? OR cari_id IN (?,?,?)", KASA, M, T, X)
qx(f"DELETE FROM banka_hareket WHERE banka_hesap_id=? OR cari_id IN (?,?)", BANKA, M, T)
qx(f"DELETE FROM cek_senet WHERE cari_id IN (?,?)", M, T)
qx("DELETE FROM pos_terminal WHERE id=?", TERM)
qx("DELETE FROM kasa WHERE id=?", KASA)
qx("DELETE FROM banka_hesap WHERE id=?", BANKA)
qx(f"DELETE FROM cari_kart WHERE id IN (?,?,?)", M, T, X)
qx("DELETE FROM sirket WHERE id=?", S2)
fk = qall("PRAGMA foreign_key_check")
kal = 0
for t, kol in (("cari_kart", "kod"), ("kasa", "kod"), ("banka_hesap", "kod"),
               ("pos_terminal", "ad"), ("sirket", "kod"), ("cek_senet", "no")):
    kal += q1(f"SELECT COUNT(*) c FROM {t} WHERE {kol} LIKE ?", MARK + "%")["c"]
kal += q1("SELECT COUNT(*) c FROM cari_hareket WHERE aciklama LIKE ?", "%" + MARK + "%")["c"]
kal += q1("SELECT COUNT(*) c FROM kasa_hareket WHERE aciklama LIKE ?", "%" + MARK + "%")["c"]
kal += q1("SELECT COUNT(*) c FROM banka_hareket WHERE aciklama LIKE ?", "%" + MARK + "%")["c"]
check("14. FK bütünlüğü 0 + D013TEST kalıntısı yok", len(fk) == 0 and kal == 0,
      f"fk={len(fk)}, kalıntı={kal}")

print(f"\n=== SONUÇ: {len(ok)} başarılı / {len(fail)} başarısız (toplam {len(ok) + len(fail)}) ===")
if fail:
    print("BAŞARISIZ:", fail)
    raise SystemExit(1)
print("TÜM D013 TESTLERİ GEÇTİ ✅")
