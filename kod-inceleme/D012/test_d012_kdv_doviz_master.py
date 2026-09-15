# -*- coding: utf-8 -*-
"""D012 — Satır Bazlı KDV + Çoklu Döviz + Para Birimi & Birim DB Tablo (v1.43.0) e2e testi.

21 kontrol. Sunucu 8080'de çalışırken:
    python3 test_d012_kdv_doviz_master.py

Kapsam (GM direktifi D012-satir-kdv-coklu-doviz-parabirimi-birim-db-v1.43.0.md):
  B2-4   Satır bazlı KDV: karışık (dahil/hariç) aynı belgede; boş=belge geneli; toplamlar doğru
  X5-15  Para birimi & birim DB tablo: tohum 4/11, inline idempotent, pasifleştir (silme yok),
         TRY koruması, 403 yetki, K1 sirket_id izolasyonu
  D16-20 Döviz + TL: belge detayında döviz+TL, cari hareket TL karşılığı (K2), ekstre filtresi,
         kartoteks filtresi + döviz alt toplamları
  F21    Bütünlük: FK=0 + D012TEST kalıntısı yok
"""
import sqlite3

import requests

BASE = "http://127.0.0.1:8080"
DB = "data/erp.db"
MARK = "D012TEST"

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


def temizle_fatura(fid):
    qx("DELETE FROM yevmiye_kalem WHERE yevmiye_id IN "
       "(SELECT id FROM yevmiye WHERE kaynak_modul='Fatura' AND kaynak_id=?)", fid)
    qx("DELETE FROM yevmiye WHERE kaynak_modul='Fatura' AND kaynak_id=?", fid)
    qx("DELETE FROM cari_hareket WHERE ilgili_modul='Fatura' AND ilgili_kayit_id=?", fid)
    qx("DELETE FROM audit_log WHERE tablo='fatura' AND kayit_id=?", fid)
    qx("DELETE FROM fatura_kalem WHERE fatura_id=?", fid)
    qx("DELETE FROM fatura WHERE id=?", fid)


# Önceki çalışmalardan kalıntı temizliği
qx("DELETE FROM para_birimi WHERE kod LIKE ?", MARK + "%")
qx("DELETE FROM birim WHERE ad LIKE ?", MARK + "%")
qx("DELETE FROM sirket WHERE kod=?", MARK)
qx("DELETE FROM kullanici_sirket WHERE sirket_id NOT IN (SELECT id FROM sirket)")

s, r = giris()
check("1. admin girişi", r.status_code == 302 and bool(r.cookies.get("erp_session")),
      f"status={r.status_code}")

musteri = q1("SELECT id, unvan FROM cari_kart WHERE aktif=1 AND tip IN ('Musteri','HerIkisi') ORDER BY id LIMIT 1")
stok = q1("SELECT id, ad FROM stok_kart WHERE aktif=1 ORDER BY id LIMIT 1")

# =============================================================================
print("=" * 70)
print("BÖLÜM B — Satır Bazlı KDV (aynı belgede karışık dahil/hariç)")
print("=" * 70)

r = s.post(BASE + "/fatura/yeni", data=[
    ("tip", "Satis"), ("cari_id", str(musteri["id"])), ("tarih", "2026-09-14"),
    ("para_birimi", "TRY"), ("doviz_kur", ""), ("vade", ""), ("aciklama", MARK + "-KDV-KARISIK"),
    ("action", "kaydet"),
    ("k_stok_id", str(stok["id"])), ("k_stok_id", ""),
    ("k_varyant_id", "0"), ("k_varyant_id", "0"),
    ("k_manuel_ad", ""), ("k_manuel_ad", MARK + " hizmet"),
    ("k_miktar", "1"), ("k_miktar", "1"),
    ("k_birim_fiyat", "100"), ("k_birim_fiyat", "120"),
    ("k_iskonto", "0"), ("k_iskonto", "0"),
    ("k_kdv", "20"), ("k_kdv", "20"),
    ("k_kdv_dahil", "0"), ("k_kdv_dahil", "1"),
], allow_redirects=False)
f1 = q1("SELECT id, ara_toplam, kdv_toplam, genel_toplam FROM fatura WHERE aciklama=? ORDER BY id DESC", MARK + "-KDV-KARISIK")
k1 = qall("SELECT kdv_dahil, birim_fiyat, tutar FROM fatura_kalem WHERE fatura_id=? ORDER BY id", f1["id"])
# satır1 hariç(0): 100 net + 20 KDV; satır2 dahil(1): 120 → net 100 (KDV yine net×%20)
check("2. karışık KDV toplamları doğru (ara=200, kdv=40, genel=240)",
      (f1["ara_toplam"], f1["kdv_toplam"], f1["genel_toplam"]) == (200.0, 40.0, 240.0),
      f"{f1['ara_toplam']}/{f1['kdv_toplam']}/{f1['genel_toplam']}")
check("3. kalemlerde kdv_dahil override saklandı (0,1) + dahil satır net yazıldı",
      [k["kdv_dahil"] for k in k1] == [0, 1] and round(k1[1]["birim_fiyat"], 2) == 100.0,
      f"{[(k['kdv_dahil'], round(k['birim_fiyat'],2)) for k in k1]}")
temizle_fatura(f1["id"])

# Boş k_kdv_dahil → belge genelini izler (kdv_dahil=1 belge geneli)
r = s.post(BASE + "/fatura/yeni", data=[
    ("tip", "Satis"), ("cari_id", str(musteri["id"])), ("tarih", "2026-09-14"),
    ("para_birimi", "TRY"), ("doviz_kur", ""), ("vade", ""), ("aciklama", MARK + "-KDV-GENEL"),
    ("kdv_dahil", "1"), ("action", "kaydet"),
    ("k_stok_id", str(stok["id"])), ("k_varyant_id", "0"), ("k_manuel_ad", ""),
    ("k_miktar", "1"), ("k_birim_fiyat", "120"), ("k_iskonto", "0"), ("k_kdv", "20"),
], allow_redirects=False)
f2 = q1("SELECT id, ara_toplam, kdv_toplam, genel_toplam FROM fatura WHERE aciklama=? ORDER BY id DESC", MARK + "-KDV-GENEL")
k2 = q1("SELECT kdv_dahil, birim_fiyat FROM fatura_kalem WHERE fatura_id=?", f2["id"])
check("4. boş override → belge geneli uygulanır (kdv_dahil NULL + net yazılır, kdv=20, genel=120)",
      k2["kdv_dahil"] is None and round(k2["birim_fiyat"], 2) == 100.0
      and f2["kdv_toplam"] == 20.0 and f2["genel_toplam"] == 120.0,
      f"kdv_dahil={k2['kdv_dahil']}, fiyat={round(k2['birim_fiyat'],2)}, kdv={f2['kdv_toplam']}, genel={f2['genel_toplam']}")
temizle_fatura(f2["id"])

# =============================================================================
print("=" * 70)
print("BÖLÜM X — Para Birimi & Birim DB Tablo (tohum / inline / pasifleştir / K1)")
print("=" * 70)

check("5. tohum: para_birimi 4 (TRY/USD/EUR/GBP) + birim 11",
      q1("SELECT COUNT(*) c FROM para_birimi WHERE sirket_id=1")["c"] == 4
      and q1("SELECT COUNT(*) c FROM birim WHERE sirket_id=1")["c"] == 11,
      f"pb={q1('SELECT COUNT(*) c FROM para_birimi')['c']}, br={q1('SELECT COUNT(*) c FROM birim')['c']}")

r = s.post(BASE + "/api/birim/ekle", data={"ad": MARK + "BRM"}, allow_redirects=False)
brm_id = r.json().get("id") if r.status_code == 200 else None
br = q1("SELECT aktif, sirket_id FROM birim WHERE id=?", brm_id)
check("6. birim inline ekleme (200 + aktif=1 + sirket_id=1)",
      r.status_code == 200 and brm_id and br and br["aktif"] == 1 and br["sirket_id"] == 1,
      f"status={r.status_code}, id={brm_id}")

r2 = s.post(BASE + "/api/birim/ekle", data={"ad": (MARK + "BRM").lower()}, allow_redirects=False)
check("7. birim idempotent (küçük harf → aynı id)",
      r2.status_code == 200 and r2.json().get("id") == brm_id, f"id={r2.json().get('id')}")

r = s.post(BASE + "/api/para-birimi/ekle", data={"kod": MARK + "PB", "ad": MARK + " Para Birimi"},
           allow_redirects=False)
pb_id = r.json().get("id") if r.status_code == 200 else None
pbr = q1("SELECT aktif, sirket_id FROM para_birimi WHERE id=?", pb_id)
check("8. para birimi inline ekleme (200 + aktif=1 + sirket_id=1)",
      r.status_code == 200 and pb_id and pbr and pbr["aktif"] == 1 and pbr["sirket_id"] == 1,
      f"status={r.status_code}, id={pb_id}")

r2 = s.post(BASE + "/api/para-birimi/ekle", data={"kod": (MARK + "PB").lower(), "ad": ""},
            allow_redirects=False)
check("9. para birimi idempotent (küçük harf kod → aynı id)",
      r2.status_code == 200 and r2.json().get("id") == pb_id, f"id={r2.json().get('id')}")

# 403 — servis rolü STOK_WRITE dışı
sv, _ = giris("servis", "1234")
r = sv.post(BASE + "/api/birim/ekle", data={"ad": "X"}, allow_redirects=False)
check("10. STOK_WRITE dışı rol (servis) → 403", r.status_code == 403, f"status={r.status_code}")

# Pasifleştir: birim (silme yok)
r = s.post(BASE + "/ayarlar/tanimlar/birim/" + str(brm_id) + "/durum", allow_redirects=False)
br = q1("SELECT aktif FROM birim WHERE id=?", brm_id)
check("11. birim pasifleştirildi (aktif=0, silinmedi)",
      r.status_code == 302 and br["aktif"] == 0 and q1("SELECT COUNT(*) c FROM birim WHERE id=?", brm_id)["c"] == 1,
      f"aktif={br['aktif']}")
r = s.get(BASE + "/stok/yeni", allow_redirects=False)
check("12. pasif birim stok formunda seçilemez",
      r.status_code == 200 and MARK + "BRM" not in r.text, f"status={r.status_code}")

# Pasifleştir: para birimi + TRY koruması
r = s.post(BASE + "/ayarlar/tanimlar/para-birimi/" + str(pb_id) + "/durum", allow_redirects=False)
pbr = q1("SELECT aktif FROM para_birimi WHERE id=?", pb_id)
check("13. para birimi pasifleştirildi (aktif=0, silinmedi)",
      r.status_code == 302 and pbr["aktif"] == 0, f"aktif={pbr['aktif']}")

try_id = q1("SELECT id FROM para_birimi WHERE kod='TRY' AND sirket_id=1")["id"]
r = s.post(BASE + "/ayarlar/tanimlar/para-birimi/" + str(try_id) + "/durum", allow_redirects=False)
try_aktif = q1("SELECT aktif FROM para_birimi WHERE id=?", try_id)["aktif"]
check("14. TRY pasifleştirilemez (aktif=1 korunur)", try_aktif == 1, f"aktif={try_aktif}")

# K1 izolasyonu — ikinci şirket
qx("INSERT INTO sirket(kod, unvan, aktif) VALUES(?,?,1)", MARK, "D012 İkinci Şirket")
s2 = q1("SELECT id FROM sirket WHERE kod=?", MARK)["id"]
qx("INSERT OR IGNORE INTO kullanici_sirket(kullanici_id, sirket_id) "
   "SELECT id, ? FROM kullanici WHERE kullanici_adi='admin'", s2)
s.post(BASE + "/sirket/gec", data={"sirket_id": str(s2), "next": "/"}, allow_redirects=False)
r = s.post(BASE + "/api/birim/ekle", data={"ad": MARK + "BRM"}, allow_redirects=False)
brm_id_b = r.json().get("id") if r.status_code == 200 else None
r = s.post(BASE + "/api/para-birimi/ekle", data={"kod": MARK + "PB", "ad": ""}, allow_redirects=False)
pb_id_b = r.json().get("id") if r.status_code == 200 else None
s.post(BASE + "/sirket/gec", data={"sirket_id": "1", "next": "/"}, allow_redirects=False)
check("15. K1 izolasyonu (birim + para birimi şirket bazlı ayrı kayıt)",
      brm_id_b and pb_id_b and brm_id_b != brm_id and pb_id_b != pb_id
      and q1("SELECT sirket_id FROM birim WHERE id=?", brm_id_b)["sirket_id"] == s2
      and q1("SELECT sirket_id FROM para_birimi WHERE id=?", pb_id_b)["sirket_id"] == s2,
      f"brm={brm_id}(1)/{brm_id_b}({s2}), pb={pb_id}(1)/{pb_id_b}({s2})")

# =============================================================================
print("=" * 70)
print("BÖLÜM D — Döviz + TL Eşzamanlı Gösterim & Filtreler")
print("=" * 70)

KUR = 34.2
r = s.post(BASE + "/fatura/yeni", data=[
    ("tip", "Satis"), ("cari_id", str(musteri["id"])), ("tarih", "2026-09-14"),
    ("para_birimi", "USD"), ("doviz_kur", str(KUR)), ("vade", ""), ("aciklama", MARK + "-USD"),
    ("action", "kaydet"),
    ("k_stok_id", str(stok["id"])), ("k_varyant_id", "0"), ("k_manuel_ad", ""),
    ("k_miktar", "1"), ("k_birim_fiyat", "100"), ("k_iskonto", "0"), ("k_kdv", "20"),
    ("k_kdv_dahil", "0"),
], allow_redirects=False)
fUSD = q1("SELECT id, fatura_no, para_birimi, doviz_kur, genel_toplam FROM fatura WHERE aciklama=? ORDER BY id DESC", MARK + "-USD")
# TRY fatura (filtre ayırt ediciliği için)
r = s.post(BASE + "/fatura/yeni", data=[
    ("tip", "Satis"), ("cari_id", str(musteri["id"])), ("tarih", "2026-09-14"),
    ("para_birimi", "TRY"), ("doviz_kur", ""), ("vade", ""), ("aciklama", MARK + "-TRY"),
    ("action", "kaydet"),
    ("k_stok_id", str(stok["id"])), ("k_varyant_id", "0"), ("k_manuel_ad", ""),
    ("k_miktar", "1"), ("k_birim_fiyat", "50"), ("k_iskonto", "0"), ("k_kdv", "20"),
], allow_redirects=False)
fTRY = q1("SELECT id, fatura_no, genel_toplam FROM fatura WHERE aciklama=? ORDER BY id DESC", MARK + "-TRY")

s.post(BASE + f"/fatura/{fUSD['id']}/durum", data={"durum": "Onaylandı"}, allow_redirects=False)
s.post(BASE + f"/fatura/{fTRY['id']}/durum", data={"durum": "Onaylandı"}, allow_redirects=False)

r = s.get(BASE + f"/fatura/{fUSD['id']}", allow_redirects=False)
check("16. USD fatura detayında döviz + TL karşılığı görünür",
      r.status_code == 200 and "Belge dövizi" in r.text and "USD" in r.text and "≈" in r.text,
      f"status={r.status_code}")

ch = q1("SELECT para_birimi, doviz_kur, borc FROM cari_hareket "
        "WHERE ilgili_modul='Fatura' AND ilgili_kayit_id=?", fUSD["id"])
check("17. cari hareket K2: TL karşılığı (borc = genel×kur) + para_birimi=USD",
      ch and ch["para_birimi"] == "USD" and round(ch["borc"], 2) == round(fUSD["genel_toplam"] * KUR, 2),
      f"borc={ch['borc'] if ch else '?'}, beklenen={round(fUSD['genel_toplam']*KUR,2)}")

r = s.get(BASE + f"/cari/{musteri['id']}/ekstre?pb=USD", allow_redirects=False)
check("18. ekstre Para Birimi filtresi: USD hareket görünür, TRY gizlenir",
      r.status_code == 200 and fUSD["fatura_no"] in r.text and fTRY["fatura_no"] not in r.text,
      f"status={r.status_code}")

r = s.get(BASE + f"/cari/{musteri['id']}/ekstre", allow_redirects=False)
check("19. ekstre döviz alt toplamları (Tümü) + kartoteks pb filtresi",
      r.status_code == 200 and "Döviz Alt Toplamları" in r.text and "USD" in r.text,
      f"status={r.status_code}")
r = s.get(BASE + f"/kartoteks/cari?cari_id={musteri['id']}&pb=USD", allow_redirects=False)
check("20. kartoteks Para Birimi filtresi + döviz alt toplamları",
      r.status_code == 200 and "Döviz alt toplamları" in r.text and "USD" in r.text,
      f"status={r.status_code}")

# =============================================================================
print("=" * 70)
print("BÖLÜM F — Bütünlük + Kalıntı Temizliği")
print("=" * 70)

temizle_fatura(fUSD["id"])
temizle_fatura(fTRY["id"])
qx("DELETE FROM audit_log WHERE tablo='birim' AND kayit_id IN "
   "(SELECT id FROM birim WHERE ad LIKE ?)", MARK + "%")
qx("DELETE FROM audit_log WHERE tablo='para_birimi' AND kayit_id IN "
   "(SELECT id FROM para_birimi WHERE kod LIKE ?)", MARK + "%")
qx("DELETE FROM para_birimi WHERE kod LIKE ?", MARK + "%")
qx("DELETE FROM birim WHERE ad LIKE ?", MARK + "%")
qx("DELETE FROM kullanici_sirket WHERE sirket_id=?", s2)
qx("DELETE FROM sirket WHERE id=?", s2)

fk = q1("SELECT COUNT(*) c FROM pragma_foreign_key_check")["c"]
kalinti = (q1("SELECT COUNT(*) c FROM para_birimi WHERE kod LIKE ?", MARK + "%")["c"]
           + q1("SELECT COUNT(*) c FROM birim WHERE ad LIKE ?", MARK + "%")["c"]
           + q1("SELECT COUNT(*) c FROM fatura WHERE aciklama LIKE ?", MARK + "%")["c"]
           + q1("SELECT COUNT(*) c FROM sirket WHERE kod=?", MARK)["c"])
check("21. FK bütünlüğü 0 + D012TEST kalıntısı yok", fk == 0 and kalinti == 0,
      f"fk={fk}, kalıntı={kalinti}")

print()
print(f"=== SONUÇ: {len(ok)} başarılı / {len(fail)} başarısız (toplam {len(ok) + len(fail)}) ===")
if fail:
    print("BAŞARISIZ:", fail)
    raise SystemExit(1)
print("TÜM D012 TESTLERİ GEÇTİ ✅")
