# -*- coding: utf-8 -*-
"""D015 — Toplu İçe/Dışa Aktarma + Yardım + Sistem Bilgi (v1.46.0) e2e testi.

12 kontrol. Sunucu 8080'de çalışırken:
    python3 test_d015_toplu_yardim_sistem.py

Kapsam (GM direktifi D015-toplu-ice-dis-aktarma-yardim-sistem-bilgi-v1.46.0.md):
  A (1-8)  Şablon + önizleme/onay aktarımı (5 liste) + validasyon + atlama + K1 + dışa aktarma
  B (9-10) /yardim kartlar + filtre + shortcuts.js + modal
  C (11)   /sistem/bilgi Admin 200 + yetkisiz 403
  F (12)   FK + kalıntı temizliği
"""
import re
import sqlite3

import requests

BASE = "http://127.0.0.1:8080"
DB = "data/erp.db"
MARK = "D015TEST"

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


def yukle(s, action, csv_metin, dosya_adi):
    return s.post(BASE + action, files={"dosya": (dosya_adi, csv_metin.encode("utf-8"),
                                                 "text/csv")})


def token_al(html):
    m = re.search(r'name="token" value="([0-9a-f]+)"', html)
    return m.group(1) if m else ""


s, r = giris()
assert r.status_code == 302, "admin girişi başarısız"

print("BÖLÜM A — Aktarım Birliği")
r1 = s.get(BASE + "/stok/sablon")
r2 = s.get(BASE + "/cari/sablon")
r3 = s.get(BASE + "/ayarlar/tanimlar/marka/sablon")
check("1. şablonlar 200 + BOM + doğru başlık",
      r1.status_code == 200 and r1.content.startswith(b"\xef\xbb\xbf")
      and "kod;ad;barkod;marka" in r1.text
      and r2.status_code == 200 and "kod;unvan;tip" in r2.text
      and r3.status_code == 200 and r3.text.replace("﻿", "").strip() == "ad",
      f"status={r1.status_code}/{r2.status_code}/{r3.status_code}")
# marka + birim + kategori aktarımı (stok/cari çözümüne girdi olur)
sonuclar = []
for tip, csv_metin in (
        ("marka", f"ad\n{MARK} Marka\n"),
        ("birim", f"ad\n{MARK} Birim\n"),
        ("kategori", f"ad;ust_kategori\n{MARK} Kat;\n")):
    act = f"/ayarlar/tanimlar/{tip}/ice-aktar"
    h = yukle(s, act, csv_metin, MARK + f"-{tip}.csv").text
    tok = token_al(h)
    var_oncesi = q1(f"SELECT COUNT(*) c FROM {tip} WHERE ad LIKE ?", MARK + "%")["c"]
    r = s.post(BASE + act + "?onay=1", data={"token": tok}, allow_redirects=False)
    var_sonra = q1(f"SELECT COUNT(*) c FROM {tip} WHERE ad LIKE ?", MARK + "%")["c"]
    sonuclar.append((tok != "" and var_oncesi == 0 and r.status_code == 302
                     and var_sonra == 1, tip, tok != "", r.status_code))
check("2. marka/birim/kategori: önizleme (yazma yok) + onay → DB'de",
      all(x[0] for x in sonuclar), str([(x[1], x[2], x[3]) for x in sonuclar]))
h = yukle(s, "/stok/ice-aktar",
          "kod;ad;barkod;marka;kategori;birim;kdv_orani;alis_fiyat;satis_fiyat;para_birimi;kritik_stok\n"
          f"{MARK}-STK;{MARK} Stok;;{MARK} Marka;{MARK} Kat;Adet;20;100;150;TRY;5\n",
          MARK + "-stok.csv").text
tok = token_al(h)
r = s.post(BASE + "/stok/ice-aktar?onay=1", data={"token": tok}, allow_redirects=False)
st = q1("SELECT s.*, m.ad AS marka_ad, k.ad AS kat_ad FROM stok_kart s "
        "LEFT JOIN marka m ON m.id=s.marka_id LEFT JOIN kategori k ON k.id=s.kategori_id "
        "WHERE s.kod=?", MARK + "-STK")
aud = q1("SELECT COUNT(*) c FROM audit_log WHERE islem='ice-aktar' AND detay LIKE ?",
         "%" + MARK + "%")["c"]
check("3. stok aktarım: FK çözümleme + audit",
      r.status_code == 302 and st and st["marka_ad"] == MARK + " Marka"
      and st["kat_ad"] == MARK + " Kat" and st["satis_fiyat"] == 150.0 and aud >= 1,
      f"status={r.status_code}, audit={aud}")
h = yukle(s, "/cari/ice-aktar",
          "kod;unvan;tip;telefon;email;vergi_no;adres;il;kredi_limiti;grup\n"
          f"{MARK}-C;{MARK} Cari;Musteri;555;;123;;Ankara;5000;\n",
          MARK + "-cari.csv").text
r = s.post(BASE + "/cari/ice-aktar?onay=1", data={"token": token_al(h)}, allow_redirects=False)
cc = q1("SELECT * FROM cari_kart WHERE kod=?", MARK + "-C")
check("4. cari aktarım: tip + limit doğru",
      r.status_code == 302 and cc and cc["tip"] == "Musteri" and cc["kredi_limiti"] == 5000.0,
      f"status={r.status_code}")
h = yukle(s, "/stok/ice-aktar",
          "kod;ad;barkod;marka;kategori;birim;kdv_orani;alis_fiyat;satis_fiyat;para_birimi;kritik_stok\n"
          "X1;;;;;;;;;;\n"
          f"X2;{MARK} Bozuk;;;;Adet;abc;0;0;TRY;0\n"
          f"X3;{MARK} Bozuk2;;{MARK}YOKMARKA;;Adet;20;0;0;TRY;0\n",
          MARK + "-hatali.csv").text
n_stok = q1("SELECT COUNT(*) c FROM stok_kart WHERE kod IN ('X1','X2','X3')")["c"]
check("5. validasyon: 3 hata + token yok + yazma yok",
      "zorunlu alan boş" in h and "sayı olmalı" in h and "bulunamadı" in h
      and token_al(h) == "" and n_stok == 0,
      f"hatalar listelendi, yazılan={n_stok}")
h = yukle(s, "/ayarlar/tanimlar/marka/ice-aktar", f"ad\n{MARK} Marka\n",
          MARK + "-marka2.csv").text
n_once = q1("SELECT COUNT(*) c FROM marka WHERE ad=?", MARK + " Marka")["c"]
r = s.post(BASE + "/ayarlar/tanimlar/marka/ice-aktar?onay=1", data={"token": token_al(h)},
           allow_redirects=False)
n_sonra = q1("SELECT COUNT(*) c FROM marka WHERE ad=?", MARK + " Marka")["c"]
check("6. mevcut kayıt atlanır (çift yazılmaz)",
      "Atlanacak" in h and n_once == 1 and n_sonra == 1,
      f"önce={n_once}, sonra={n_sonra}")
qx("INSERT INTO sirket(kod, unvan, aktif) VALUES(?,?,1)", MARK + "-S", MARK + " Sirket")
S2 = q1("SELECT id FROM sirket WHERE kod=?", MARK + "-S")["id"]
s.post(BASE + "/sirket/gec", data={"sirket_id": str(S2), "next": "/"}, allow_redirects=False)
h = yukle(s, "/ayarlar/tanimlar/marka/ice-aktar", f"ad\n{MARK} S2\n",
          MARK + "-s2.csv").text
s.post(BASE + "/ayarlar/tanimlar/marka/ice-aktar?onay=1", data={"token": token_al(h)},
       allow_redirects=False)
s.post(BASE + "/sirket/gec", data={"sirket_id": "1", "next": "/"}, allow_redirects=False)
m2 = q1("SELECT sirket_id FROM marka WHERE ad=?", MARK + " S2")
s1_csv = s.get(BASE + "/ayarlar/tanimlar/marka/dis-aktar").text
check("7. K1: s2 aktarımı izole (sirket_id + s1 dökümünde yok)",
      m2 and m2["sirket_id"] == S2 and MARK + " S2" not in s1_csv,
      f"sirket={m2['sirket_id'] if m2 else None}")
csv_stok = s.get(BASE + "/stok/dis-aktar").text
csv_cari = s.get(BASE + "/cari/dis-aktar").text
check("8. dışa aktarma CSV'de MARK satırları",
      MARK + "-STK" in csv_stok and MARK + " Stok" in csv_stok
      and MARK + "-C" in csv_cari and MARK + " Cari" in csv_cari,
      "stok+cari CSV OK")

print("BÖLÜM B — Yardım + Kısayollar")
h = s.get(BASE + "/yardim").text
n_kart = h.count("yardim-kart")
hf = s.get(BASE + "/yardim?q=amortisman").text
check("9. /yardim 12 kart + ?q filtresi",
      n_kart == 12 and "Demirbaş" in hf and "POS Hızlı Satış" not in hf,
      f"kart={n_kart}")
rj = s.get(BASE + "/static/js/shortcuts.js")
h0 = s.get(BASE + "/").text
check("10. shortcuts.js <2KB + base modal",
      rj.status_code == 200 and len(rj.content) < 2048 and 'id="kk"' in h0
      and 'id="kk-h"' in h0 and "shortcuts.js" in h0,
      f"boyut={len(rj.content)}")

print("BÖLÜM C — Sistem Bilgi")
h = s.get(BASE + "/sistem/bilgi").text
sv, _ = giris("satis", "1234")
r403 = sv.get(BASE + "/sistem/bilgi", allow_redirects=False)
import re as _re
check("11. admin 200 (sürüm+hash+integrity+FK+saglik) + satis 403",
      "v1.46.0" in h and _re.search(r"[0-9a-f]{40}", h) is not None
      and "Integrity Check" in h and ">ok<" in h and "0 sorun" in h
      and "api/saglik" in h and 'href="/sistem/bilgi"' in h0 and r403.status_code == 403,
      f"satis={r403.status_code}")

print("BÖLÜM F — Temizlik")
qx("DELETE FROM audit_log WHERE islem='ice-aktar' AND detay LIKE ?", "%" + MARK + "%")
qx("DELETE FROM stok_kart WHERE kod LIKE ?", MARK + "%")
qx("DELETE FROM cari_kart WHERE kod LIKE ?", MARK + "%")
qx("DELETE FROM kategori WHERE ad LIKE ?", MARK + "%")
qx("DELETE FROM birim WHERE ad LIKE ?", MARK + "%")
qx("DELETE FROM marka WHERE ad LIKE ?", MARK + "%")
qx("DELETE FROM sirket WHERE id=?", S2)
_c = sqlite3.connect(DB)
fk = _c.execute("PRAGMA foreign_key_check").fetchall()
_c.close()
kal = 0
for t, kol in (("stok_kart", "kod"), ("cari_kart", "kod"), ("kategori", "ad"),
               ("birim", "ad"), ("marka", "ad"), ("sirket", "kod")):
    kal += q1(f"SELECT COUNT(*) c FROM {t} WHERE {kol} LIKE ?", MARK + "%")["c"]
kal += q1("SELECT COUNT(*) c FROM audit_log WHERE detay LIKE ?", "%" + MARK + "%")["c"]
check("12. FK bütünlüğü 0 + D015TEST kalıntısı yok", len(fk) == 0 and kal == 0,
      f"fk={len(fk)}, kalıntı={kal}")

print(f"\n=== SONUÇ: {len(ok)} başarılı / {len(fail)} başarısız (toplam {len(ok) + len(fail)}) ===")
if fail:
    print("BAŞARISIZ:", fail)
    raise SystemExit(1)
print("TÜM D015 TESTLERİ GEÇTİ ✅")
