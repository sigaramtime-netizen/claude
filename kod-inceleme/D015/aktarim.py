# -*- coding: utf-8 -*-
"""D015-A — Toplu İçe/Dışa Aktarma Birliği (v1.46.0).

5 liste (Stok, Cari, Kategori, Birim, Marka) için standart CSV aktarımı:
  GET  /<alan>/sablon     — UTF-8 BOM'lu boş şablon (başlık satırı)
  GET  /<alan>/ice-aktar  — dosya yükleme formu
  POST /<alan>/ice-aktar  — önizleme (validasyon; yazma YOK)
  POST /<alan>/ice-aktar?onay=1&token=... — doğrulanan satırları yazar
  GET  /<alan>/dis-aktar  — mevcut listenin CSV dökümü

- Ayraç ';' (Türkçe Excel); tek sütun gelirse ',' denenir.
- Önizlemede hatalı satır varsa yazma kapalıdır; onay tek kullanımlık token ile
  aynı şirket oturumuna bağlıdır (K1). Mevcut kayıtlar (kod/ad) atlanır, üzerine
  yazılmaz. Her toplu yazma tek audit satırı üretir.
"""
import csv
import datetime
import io
import secrets

import db
import stok
import cari
from core import route, render_template, redirect, flash, audit, Response

STOK_ROLLERI = stok.STOK_WRITE
CARI_ROLLERI = cari.WRITE_ROLES
TANIM_ROLLERI = ("Admin",)
TANIM_TIPLERI = ("kategori", "birim", "marka")

MAX_BYTES = 5 * 1024 * 1024
MAX_SATIR = 2000
ONIZLEME_SATIR = 50

# tip → (başlık satırı, zorunlu alanlar)
SABLONLAR = {
    "stok": (["kod", "ad", "barkod", "marka", "kategori", "birim", "kdv_orani",
              "alis_fiyat", "satis_fiyat", "para_birimi", "kritik_stok"], ["ad"]),
    "cari": (["kod", "unvan", "tip", "telefon", "email", "vergi_no", "adres", "il",
              "kredi_limiti", "grup"], ["unvan"]),
    "kategori": (["ad", "ust_kategori"], ["ad"]),
    "birim": (["ad"], ["ad"]),
    "marka": (["ad"], ["ad"]),
}
ETIKET = {"stok": "Stok", "cari": "Cari", "kategori": "Kategori",
          "birim": "Birim", "marka": "Marka"}
TABLO = {"stok": "stok_kart", "cari": "cari_kart", "kategori": "kategori",
         "birim": "birim", "marka": "marka"}

# onay bekleyen önizlemeler: token → {tip, sid, satirlar} (tek kullanımlık)
BEKLEYENLER = {}


def _sayi(v, default=0.0):
    """TR (1.234,56) ve EN (1234.56) sayı biçimlerini kabul eder."""
    if v is None:
        return default
    s = str(v).strip()
    if not s:
        return default
    try:
        if "," in s:
            s = s.replace(".", "").replace(",", ".")
        return float(s)
    except (TypeError, ValueError):
        return None


def _csv_oku(data):
    """BOM'lu/BOM'suz CSV → (başlıklar, satırlar). Ayraç otomatik (; veya ,)."""
    try:
        metin = data.decode("utf-8-sig")
    except (UnicodeDecodeError, AttributeError):
        try:
            metin = data.decode("iso-8859-9")
        except (UnicodeDecodeError, AttributeError):
            return None, "Dosya UTF-8 veya Türkçe (ISO-8859-9) kodlu olmalı."
    satirlar = [s for s in metin.splitlines() if s.strip()]
    if not satirlar:
        return None, "Dosya boş."
    ayrac = ";" if ";" in satirlar[0] else ","
    try:
        okunan = list(csv.reader(io.StringIO(metin), delimiter=ayrac))
    except Exception:  # noqa: BLE001
        return None, "CSV çözümlenemedi."
    okunan = [[h.strip() for h in r] for r in okunan if any(h.strip() for h in r)]
    if not okunan:
        return None, "Dosya boş."
    return okunan, None


def _dogrula(conn, tip, basliklar, ham_satirlar, sid):
    """Satırları doğrula → (temiz_satirlar, hatalar, atlanacak).
    temiz: yazılabilir dict listesi; hatalar: [(no, mesaj)]; atlanacak: mevcut sayısı."""
    beklenen, zorunlu = SABLONLAR[tip]
    norm = [b.strip().lower() for b in basliklar]
    if norm != beklenen:
        return [], [(0, f"Başlık satırı şablona uymuyor (beklenen: {';'.join(beklenen)})")], 0
    pbs = db.para_birimleri(sid=sid)
    temiz, hatalar, atlanan = [], [], 0
    for i, ham in enumerate(ham_satirlar, start=2):
        if len(ham) != len(beklenen):
            hatalar.append((i, f"sütun sayısı hatalı ({len(ham)} yerine {len(beklenen)})"))
            continue
        r = {k: (ham[j] or "").strip() for j, k in enumerate(beklenen)}
        eksik = [z for z in zorunlu if not r[z]]
        if eksik:
            hatalar.append((i, f"zorunlu alan boş: {', '.join(eksik)}"))
            continue
        if tip == "stok":
            for alan in ("kdv_orani", "alis_fiyat", "satis_fiyat", "kritik_stok"):
                v = _sayi(r[alan], 0.0)
                if v is None:
                    hatalar.append((i, f"'{alan}' sayı olmalı: {r[alan]}"))
                    break
                r[alan] = v
            else:
                if r["para_birimi"] and r["para_birimi"] not in pbs:
                    hatalar.append((i, f"geçersiz para birimi: {r['para_birimi']}"))
                    continue
                r["para_birimi"] = r["para_birimi"] or "TRY"
                r["birim"] = r["birim"] or "Adet"
                for alan, tablo in (("marka", "marka"), ("kategori", "kategori")):
                    if r[alan]:
                        hit = conn.execute(
                            f"SELECT id FROM {tablo} WHERE lower(ad)=lower(?) AND sirket_id=?",
                            (r[alan], sid)).fetchone()
                        if not hit:
                            hatalar.append((i, f"{alan} bulunamadı: {r[alan]}"))
                            break
                        r[alan + "_id"] = hit["id"]
                else:
                    if r["birim"] != "Adet" and not conn.execute(
                            "SELECT id FROM birim WHERE ad=? AND sirket_id=?",
                            (r["birim"], sid)).fetchone():
                        hatalar.append((i, f"birim bulunamadı: {r['birim']}"))
                        continue
                    if r["kod"] and conn.execute(
                            "SELECT id FROM stok_kart WHERE kod=? AND sirket_id=?",
                            (r["kod"], sid)).fetchone():
                        atlanan += 1
                        continue
                    temiz.append(r)
                    continue
                continue
        elif tip == "cari":
            if r["tip"] and r["tip"] not in ("Musteri", "Tedarikci", "HerIkisi"):
                hatalar.append((i, f"geçersiz tip: {r['tip']} (Musteri/Tedarikci/HerIkisi)"))
                continue
            r["tip"] = r["tip"] or "Musteri"
            v = _sayi(r["kredi_limiti"], 0.0)
            if v is None:
                hatalar.append((i, f"'kredi_limiti' sayı olmalı: {r['kredi_limiti']}"))
                continue
            r["kredi_limiti"] = v
            if r["grup"]:
                hit = conn.execute("SELECT id FROM cari_grup WHERE lower(ad)=lower(?) AND sirket_id=?",
                                   (r["grup"], sid)).fetchone()
                if not hit:
                    hatalar.append((i, f"grup bulunamadı: {r['grup']}"))
                    continue
                r["grup_id"] = hit["id"]
            if r["kod"] and conn.execute("SELECT id FROM cari_kart WHERE kod=? AND sirket_id=?",
                                         (r["kod"], sid)).fetchone():
                atlanan += 1
                continue
            temiz.append(r)
        elif tip == "kategori":
            if r["ust_kategori"]:
                hit = conn.execute("SELECT id FROM kategori WHERE lower(ad)=lower(?) AND sirket_id=?",
                                   (r["ust_kategori"], sid)).fetchone()
                if not hit:
                    hatalar.append((i, f"üst kategori bulunamadı: {r['ust_kategori']}"))
                    continue
                r["ust_id"] = hit["id"]
            if conn.execute("SELECT id FROM kategori WHERE lower(ad)=lower(?) AND sirket_id=?",
                            (r["ad"], sid)).fetchone():
                atlanan += 1
                continue
            temiz.append(r)
        else:  # birim / marka (ad tekil, case-insensitive)
            tablo = TABLO[tip]
            if conn.execute(f"SELECT id FROM {tablo} WHERE lower(ad)=lower(?) AND sirket_id=?",
                            (r["ad"], sid)).fetchone():
                atlanan += 1
                continue
            temiz.append(r)
    return temiz, hatalar, atlanan


def _yaz(conn, req, tip, satirlar, sid):
    """Doğrulanmış satırları yazar → eklenen adedi (çift kayıtlar yeniden atlanır)."""
    n = 0
    uid = req.user["id"]
    for r in satirlar:
        if tip == "stok":
            if r["kod"] and conn.execute("SELECT id FROM stok_kart WHERE kod=? AND sirket_id=?",
                                         (r["kod"], sid)).fetchone():
                continue
            conn.execute(
                "INSERT INTO stok_kart(kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, "
                "alis_fiyat, satis_fiyat, para_birimi, kritik_stok, aktif, created_by, sirket_id) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,?,1,?,?)",
                (r["kod"] or None, r["ad"], r["barkod"] or None, r.get("marka_id"),
                 r.get("kategori_id"), r["birim"], r["kdv_orani"], r["alis_fiyat"],
                 r["satis_fiyat"], r["para_birimi"], r["kritik_stok"], uid, sid))
        elif tip == "cari":
            if r["kod"] and conn.execute("SELECT id FROM cari_kart WHERE kod=? AND sirket_id=?",
                                         (r["kod"], sid)).fetchone():
                continue
            conn.execute(
                "INSERT INTO cari_kart(kod, unvan, tip, telefon, email, vergi_no, adres, il, "
                "kredi_limiti, grup_id, aktif, created_by, sirket_id) "
                "VALUES(?,?,?,?,?,?,?,?,?,?,1,?,?)",
                (r["kod"] or None, r["unvan"], r["tip"], r["telefon"] or None,
                 r["email"] or None, r["vergi_no"] or None, r["adres"] or None,
                 r["il"] or None, r["kredi_limiti"], r.get("grup_id"), uid, sid))
        elif tip == "kategori":
            if conn.execute("SELECT id FROM kategori WHERE lower(ad)=lower(?) AND sirket_id=?",
                            (r["ad"], sid)).fetchone():
                continue
            conn.execute("INSERT INTO kategori(ad, ust_id, aktif, sirket_id) VALUES(?,?,1,?)",
                         (r["ad"], r.get("ust_id"), sid))
        else:
            tablo = TABLO[tip]
            if conn.execute(f"SELECT id FROM {tablo} WHERE lower(ad)=lower(?) AND sirket_id=?",
                            (r["ad"], sid)).fetchone():
                continue
            if tip == "birim":
                conn.execute("INSERT INTO birim(ad, aktif, sirket_id) VALUES(?,1,?)", (r["ad"], sid))
            else:
                conn.execute("INSERT INTO marka(ad, aktif, sirket_id) VALUES(?,1,?)", (r["ad"], sid))
        n += 1
    return n


def _csv_indir(basliklar, satirlar, dosya_adi):
    buf = io.StringIO()
    w = csv.writer(buf, delimiter=";", lineterminator="\r\n")
    w.writerow(basliklar)
    w.writerows(satirlar)
    return Response("﻿" + buf.getvalue(), "200 OK", [
        ("Content-Type", "text/csv; charset=utf-8"),
        ("Content-Disposition", f'attachment; filename="{dosya_adi}"'),
    ])


def _dis_aktar_satirlari(conn, tip, sid):
    basliklar, _ = SABLONLAR[tip]
    if tip == "stok":
        rows = conn.execute(
            "SELECT s.kod, s.ad, s.barkod, m.ad, k.ad, s.birim, s.kdv_orani, s.alis_fiyat, "
            "s.satis_fiyat, s.para_birimi, s.kritik_stok FROM stok_kart s "
            "LEFT JOIN marka m ON m.id=s.marka_id LEFT JOIN kategori k ON k.id=s.kategori_id "
            "WHERE s.sirket_id=? ORDER BY s.kod, s.ad", (sid,)).fetchall()
    elif tip == "cari":
        rows = conn.execute(
            "SELECT c.kod, c.unvan, c.tip, c.telefon, c.email, c.vergi_no, c.adres, c.il, "
            "c.kredi_limiti, g.ad FROM cari_kart c LEFT JOIN cari_grup g ON g.id=c.grup_id "
            "WHERE c.sirket_id=? ORDER BY c.kod, c.unvan", (sid,)).fetchall()
    elif tip == "kategori":
        rows = conn.execute(
            "SELECT k.ad, u.ad FROM kategori k LEFT JOIN kategori u ON u.id=k.ust_id "
            "WHERE k.sirket_id=? ORDER BY k.ad", (sid,)).fetchall()
    else:
        tablo = TABLO[tip]
        rows = conn.execute(f"SELECT ad FROM {tablo} WHERE sirket_id=? ORDER BY ad", (sid,)).fetchall()
    return basliklar, [[(c if c is not None else "") for c in r] for r in rows]


def _sablon(req, tip):
    basliklar, _ = SABLONLAR[tip]
    return _csv_indir(basliklar, [], f"{tip}-sablon.csv")


def _dis_aktar(req, tip):
    conn = db.get_conn()
    basliklar, satirlar = _dis_aktar_satirlari(conn, tip, db.sirket_id(req))
    conn.close()
    gun = datetime.date.today().isoformat()
    return _csv_indir(basliklar, satirlar, f"{tip}-liste-{gun}.csv")


def _ice_aktar_form(req, tip, action):
    return render_template("aktarim/form.html", tip=tip, etiket=ETIKET[tip], action=action,
                           basliklar=SABLONLAR[tip][0])


def _ice_aktar_post(req, tip, action, geri_url):
    # Onay adımı (?onay=1 + token): bekleyen önizlemeyi yazar (tek kullanımlık).
    if req.q("onay") == "1":
        token = req.form.get("token") or ""
        bek = BEKLEYENLER.pop(token, None)
        if not bek or bek["tip"] != tip or bek["sid"] != db.sirket_id(req):
            flash(req, "Önizleme süresi dolmuş veya geçersiz — dosyayı yeniden yükleyin.", "danger")
            return redirect(action)
        conn = db.get_conn()
        n = _yaz(conn, req, tip, bek["satirlar"], bek["sid"])
        conn.commit()
        conn.close()
        audit(req, TABLO[tip], None, "ice-aktar",
              {"tip": tip, "eklenen": n, "dosya": bek.get("dosya")})
        flash(req, f"İçe aktarma tamamlandı: {n} kayıt eklendi ({ETIKET[tip]}).", "ok")
        return redirect(geri_url)
    # Önizleme adımı: dosya yükle + doğrula (yazma YOK).
    if not req.files:
        flash(req, "CSV dosyası seçin.", "danger")
        return redirect(action)
    f = req.files[0]
    if len(f["data"]) > MAX_BYTES:
        flash(req, "Dosya çok büyük (en fazla 5 MB).", "danger")
        return redirect(action)
    if not f["data"]:
        flash(req, "Dosya boş.", "danger")
        return redirect(action)
    okunan, hata = _csv_oku(f["data"])
    if hata:
        flash(req, hata, "danger")
        return redirect(action)
    if len(okunan) - 1 > MAX_SATIR:
        flash(req, f"En fazla {MAX_SATIR} satır aktarılabilir.", "danger")
        return redirect(action)
    conn = db.get_conn()
    temiz, hatalar, atlanan = _dogrula(conn, tip, okunan[0], okunan[1:], db.sirket_id(req))
    conn.close()
    token = ""
    if temiz and not hatalar:
        token = secrets.token_hex(16)
        BEKLEYENLER[token] = {"tip": tip, "sid": db.sirket_id(req),
                              "satirlar": temiz, "dosya": f["filename"]}
    return render_template("aktarim/onizleme.html", tip=tip, etiket=ETIKET[tip], action=action,
                           basliklar=SABLONLAR[tip][0], satirlar=temiz[:ONIZLEME_SATIR],
                           toplam=len(temiz), hatalar=hatalar[:50], hata_toplam=len(hatalar),
                           atlanan=atlanan, token=token, dosya=f["filename"])


# --- Stok ---
@route(r"/stok/sablon", roles=())
def stok_sablon(req):
    return _sablon(req, "stok")


@route(r"/stok/dis-aktar", roles=())
def stok_dis_aktar(req):
    return _dis_aktar(req, "stok")


@route(r"/stok/ice-aktar", methods=("GET", "POST"), roles=STOK_ROLLERI)
def stok_ice_aktar(req):
    if req.method == "POST":
        return _ice_aktar_post(req, "stok", "/stok/ice-aktar", "/stok")
    return _ice_aktar_form(req, "stok", "/stok/ice-aktar")


# --- Cari ---
@route(r"/cari/sablon", roles=())
def cari_sablon(req):
    return _sablon(req, "cari")


@route(r"/cari/dis-aktar", roles=())
def cari_dis_aktar(req):
    return _dis_aktar(req, "cari")


@route(r"/cari/ice-aktar", methods=("GET", "POST"), roles=CARI_ROLLERI)
def cari_ice_aktar(req):
    if req.method == "POST":
        return _ice_aktar_post(req, "cari", "/cari/ice-aktar", "/cari")
    return _ice_aktar_form(req, "cari", "/cari/ice-aktar")


# --- Tanımlar (Admin) ---
@route(r"/ayarlar/tanimlar/(?P<tip>kategori|birim|marka)/sablon", roles=TANIM_ROLLERI)
def tanim_sablon(req, tip):
    return _sablon(req, tip)


@route(r"/ayarlar/tanimlar/(?P<tip>kategori|birim|marka)/dis-aktar", roles=TANIM_ROLLERI)
def tanim_dis_aktar(req, tip):
    return _dis_aktar(req, tip)


@route(r"/ayarlar/tanimlar/(?P<tip>kategori|birim|marka)/ice-aktar", methods=("GET", "POST"), roles=TANIM_ROLLERI)
def tanim_ice_aktar(req, tip):
    action = f"/ayarlar/tanimlar/{tip}/ice-aktar"
    if req.method == "POST":
        return _ice_aktar_post(req, tip, action, "/ayarlar/tanimlar")
    return _ice_aktar_form(req, tip, action)


def register():
    pass
