# -*- coding: utf-8 -*-
"""Cari Hesap Yönetimi modülü (Faz 1).

BORÇ/ALACAK KONVANSİYONU (çift taraflı muhasebe, tip bazlı ters çevirme YOKTUR):
    bakiye = Σborç − Σalacak
- Müşteri (alıcı):  Satış Faturası → BORÇ (bize borçlanır), Tahsilat → ALACAK. (+) bakiye = müşteri bize borçlu.
- Tedarikçi (satıcı): Alış Faturası → ALACAK (ona borçlanırız), Ödeme → BORÇ.  (−) bakiye = biz ona borçluyuz.
Yön, cari kartının tipine göre değişmez; işaret (bakiye pozitif/negatif) "kim kime borçlu"yu söyler.
Faz 2'de Fatura modülü cari hareketlerini aynı konvansiyonla otomatik üretecektir.
"""
import datetime
import json
import urllib.parse

import db
from core import route, render_template, redirect, flash, audit, notify, Response

WRITE_ROLES = ("Admin", "Muhasebe", "Satis")
PARA_BIRIMLERI = ["TRY", "USD", "EUR", "GBP"]
BELGE_TIPLERI = [
    "Açılış Bakiyesi", "Satış Faturası", "Alış Faturası",
    "Satış İrsaliyesi", "Alış İrsaliyesi", "Tahsilat",
    "Ödeme", "İade Faturası", "Virman", "Diğer",
]
TIP_ETIKET = {"Musteri": "Müşteri", "Tedarikci": "Tedarikçi", "HerIkisi": "Müşteri + Tedarikçi"}


def _tip_etiket(tip):
    return TIP_ETIKET.get(tip, tip)


def hareket_ekle(conn, cari_id, tarih, belge_tipi, belge_no=None, aciklama=None,
                 borc=0.0, alacak=0.0, ilgili_modul=None, ilgili_kayit_id=None,
                 vade=None, created_by=None, para_birimi="TRY", doviz_kur=None):
    """Diğer modüllerden (Kasa/Banka/Fatura/Çek-Senet…) tek noktadan cari hareketi yazma.

    Kasa/Banka tahsilat ve ödemeleri burayı çağırır; böylece cari hesaba manuel ikinci
    kayıt girmek gerekmez (Bölüm 2 md.3: çifte veri girişi olmamalı).
    K18 — döviz: borc/alacak DAİMA TL karşılığı; para_birimi + doviz_kur yalnızca izleme."""
    cur = conn.execute(
        "INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, "
        "borc, alacak, para_birimi, doviz_kur, ilgili_modul, ilgili_kayit_id, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?, "
        "(SELECT sirket_id FROM cari_kart WHERE id=?))",
        (cari_id, tarih, vade, belge_tipi, belge_no, aciklama, borc, alacak,
         para_birimi or "TRY", doviz_kur, ilgili_modul, ilgili_kayit_id, created_by, cari_id),
    )
    return cur.lastrowid


def _aging(conn, cari_id, bugun=None):
    """Bakiye + vade yaşlandırması (sadece pozitif net = müşteri alacağı yaşlandırılır).

    bakiye = Σborç − Σalacak (net). Net ≤ 0 ise (tedarikçiye borçluyuz) yaşlandırma boş döner;
    net > 0 ise FIFO ile açık borç kalemleri vade dilimlerine ayrılır."""
    bugun = bugun or datetime.date.today()
    rows = conn.execute(
        "SELECT tarih, vade, borc, alacak FROM cari_hareket "
        "WHERE cari_id=? ORDER BY tarih, id",
        (cari_id,),
    ).fetchall()

    net = sum((r["borc"] or 0) - (r["alacak"] or 0) for r in rows)
    if net <= 0:
        return {"bakiye": net, "d0": 0.0, "d1": 0.0, "d2": 0.0, "d3": 0.0,
                "vadesi_gecen": 0.0, "gecikme_gun": 0}

    # net > 0: FIFO ile açık alacak (borç) kalemlerini eşleştir
    opens = []  # [vade (str|None), kalan tutar]
    for r in rows:
        amt = (r["borc"] or 0) - (r["alacak"] or 0)
        if amt > 0:
            opens.append([r["vade"], amt])
        elif amt < 0:
            pay = -amt
            for o in opens:
                if pay <= 0:
                    break
                if o[1] <= pay:
                    pay -= o[1]
                    o[1] = 0.0
                else:
                    o[1] -= pay
                    pay = 0.0

    d0 = d1 = d2 = d3 = 0.0
    gecikme = 0
    for vade, amt in opens:
        if amt <= 0.005:
            continue
        if not vade:
            continue  # vadesiz => güncel, gecikme yok
        vd = datetime.date.fromisoformat(vade)
        g = (bugun - vd).days
        if g <= 0:
            continue
        gecikme = max(gecikme, g)
        if g <= 30:
            d0 += amt
        elif g <= 60:
            d1 += amt
        elif g <= 90:
            d2 += amt
        else:
            d3 += amt

    return {
        "bakiye": net,
        "d0": d0, "d1": d1, "d2": d2, "d3": d3,
        "vadesi_gecen": d0 + d1 + d2 + d3,
        "gecikme_gun": gecikme,
    }


def _qs(req, sayfa):
    d = {
        "q": req.q("q"),
        "tip": req.q("tip"),
        "grup": req.q("grup"),
        "sayfa": sayfa,
    }
    return urllib.parse.urlencode({k: v for k, v in d.items() if v not in (None, "")})


def _gruplar(conn, sid=None, aktif=False):
    where, params = "", []
    if sid is not None:
        where, params = " WHERE g.sirket_id = ?", [sid]
    if aktif:
        where = (where + " AND g.aktif=1") if where else " WHERE g.aktif=1"
    return conn.execute(
        "SELECT g.*, (SELECT COUNT(*) FROM cari_kart c WHERE c.grup_id = g.id AND c.sirket_id = g.sirket_id) AS cari_sayisi "
        "FROM cari_grup g" + where + " ORDER BY g.tip, g.ad",
        params,
    ).fetchall()


def _notlar(conn, cari_id):
    return conn.execute(
        "SELECT n.*, u.kullanici_adi AS kullanici FROM notlar n "
        "LEFT JOIN kullanici u ON u.id = n.kullanici_id "
        "WHERE n.ilgili_tablo='cari_kart' AND n.ilgili_id=? ORDER BY n.id DESC",
        (cari_id,),
    ).fetchall()


# --------------------------------------------------------------------------
# Rotalar
# --------------------------------------------------------------------------
@route(r"/cari", roles=())
def cari_liste(req):
    conn = db.get_conn()
    q = req.q("q").strip()
    tip = req.q("tip")
    grup = req.q("grup")
    sayfa = max(1, int(req.q("sayfa") or 1))
    per = 25

    where, params = ["c.sirket_id = ?"], [db.sirket_id(req)]
    if q:
        where.append("(c.unvan LIKE ? OR c.kod LIKE ? OR c.vergi_no LIKE ? OR c.kisa_ad LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like, like]
    if tip in ("Musteri", "Tedarikci", "HerIkisi"):
        where.append("c.tip = ?")
        params.append(tip)
    if grup:
        where.append("c.grup_id = ?")
        params.append(int(grup))
    w = " AND ".join(where)

    toplam = conn.execute(f"SELECT COUNT(*) AS c FROM cari_kart c WHERE {w}", params).fetchone()["c"]
    rows = [dict(r) for r in conn.execute(
        f"SELECT c.*, g.ad AS grup_ad FROM cari_kart c LEFT JOIN cari_grup g ON g.id=c.grup_id "
        f"WHERE {w} ORDER BY c.id DESC LIMIT ? OFFSET ?",
        params + [per, (sayfa - 1) * per],
    ).fetchall()]

    bugun = datetime.date.today()
    for r in rows:
        a = _aging(conn, r["id"], bugun)
        r["bakiye"] = a["bakiye"]
        r["vade_gecikme"] = a["gecikme_gun"]
        r["tip_etiket"] = _tip_etiket(r["tip"])

    sid = db.sirket_id(req)

    def count(t):
        return conn.execute(
            "SELECT COUNT(*) AS c FROM cari_kart WHERE tip=? AND sirket_id=?", (t, sid)
        ).fetchone()["c"]

    ozetler = {
        "tum": conn.execute("SELECT COUNT(*) AS c FROM cari_kart WHERE sirket_id=?", (sid,)).fetchone()["c"],
        "musteri": count("Musteri"),
        "tedarikci": count("Tedarikci"),
        "herikisi": count("HerIkisi"),
        "toplam": toplam,
    }
    conn.close()

    return render_template(
        "cari/liste.html",
        rows=rows,
        gruplar=db_tmp_gruplar(req, aktif=True),
        filtro={"q": q, "tip": tip, "grup": grup},
        ozetler=ozetler,
        sayfa=sayfa,
        toplam_sayfa=max(1, -(-toplam // per)),
        querystring=lambda p: _qs(req, p),
    )


def db_tmp_gruplar(req=None, aktif=False):
    conn = db.get_conn()
    rows = _gruplar(conn, db.sirket_id(req) if req else None, aktif=aktif)
    conn.close()
    return rows


@route(r"/api/cari_grup/ekle", methods=("POST",), roles=WRITE_ROLES)
def api_cari_grup_ekle(req):
    """D011-A — Yeni cari grup ekle (Ajax, Marka deseni). tip varsayılan 'Bölge'; idempotent."""
    ad = (req.form.get("ad") or "").strip()
    if not ad:
        return Response(json.dumps({"hata": "Grup adı boş olamaz."}, ensure_ascii=False),
                        "400 Bad Request", [("Content-Type", "application/json; charset=utf-8")])
    conn = db.get_conn()
    sid = db.sirket_id(req)
    mevcut = conn.execute(
        "SELECT id FROM cari_grup WHERE lower(ad)=lower(?) AND (sirket_id=? OR sirket_id IS NULL) LIMIT 1",
        (ad, sid)).fetchone()
    if mevcut:
        conn.close()
        return Response(json.dumps({"id": mevcut["id"], "ad": ad}, ensure_ascii=False),
                        "200 OK", [("Content-Type", "application/json; charset=utf-8")])
    tip = (req.form.get("tip") or "Bölge").strip() or "Bölge"
    cur = conn.execute("INSERT INTO cari_grup(ad, tip, aktif, sirket_id) VALUES(?,?,1,?)",
                       (ad, tip, sid))
    conn.commit()
    audit(req, "cari_grup", cur.lastrowid, "olustur", {"ad": ad, "tip": tip})
    conn.close()
    return Response(json.dumps({"id": cur.lastrowid, "ad": ad, "tip": tip}, ensure_ascii=False),
                    "200 OK", [("Content-Type", "application/json; charset=utf-8")])


@route(r"/cari/yeni", methods=("GET", "POST"), roles=WRITE_ROLES)
def cari_yeni(req):
    if req.method == "POST":
        conn = db.get_conn()
        kod = (req.form.get("kod") or "").strip()
        unvan = (req.form.get("unvan") or "").strip()
        if not unvan:
            flash(req, "Unvan zorunludur.", "danger")
            conn.close()
            return redirect("/cari/yeni")
        if not kod:
            nxt = conn.execute("SELECT COALESCE(MAX(id),0)+1 AS n FROM cari_kart").fetchone()["n"]
            kod = f"CAR-{nxt:04d}"
        cur = conn.execute(
            "INSERT INTO cari_kart(kod, unvan, kisa_ad, tip, vergi_dairesi, vergi_no, adres, il, ilce, "
            "telefon, gsm, email, yetkili, kredi_limiti, para_birimi, iskonto_orani, grup_id, not_, "
            "e_fatura_mukellefi, created_by, sirket_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                kod, unvan,
                (req.form.get("kisa_ad") or "").strip(),
                req.form.get("tip") or "Musteri",
                (req.form.get("vergi_dairesi") or "").strip(),
                (req.form.get("vergi_no") or "").strip(),
                (req.form.get("adres") or "").strip(),
                (req.form.get("il") or "").strip(),
                (req.form.get("ilce") or "").strip(),
                (req.form.get("telefon") or "").strip(),
                (req.form.get("gsm") or "").strip(),
                (req.form.get("email") or "").strip(),
                (req.form.get("yetkili") or "").strip(),
                _f(req.form.get("kredi_limiti")),
                req.form.get("para_birimi") or "TRY",
                _f(req.form.get("iskonto_orani")),
                _i(req.form.get("grup_id")),
                (req.form.get("not_") or "").strip(),
                1 if req.form.get("e_fatura_mukellefi") else 0,
                req.user["id"],
                db.sirket_id(req),
            ),
        )
        cid = cur.lastrowid
        conn.commit()
        audit(req, "cari_kart", cid, "olustur", {"unvan": unvan, "kod": kod})
        conn.close()
        flash(req, f"Cari kartı oluşturuldu: {unvan} ({kod})", "ok")
        return redirect(f"/cari/{cid}")

    return render_template("cari/form.html", cari=None, gruplar=db_tmp_gruplar(req, aktif=True),
                           para_birimleri=db.para_birimleri(sid=db.sirket_id(req)))


@route(r"/cari/rapor", roles=())
def cari_rapor(req):
    conn = db.get_conn()
    bugun = datetime.date.today()
    caris = conn.execute(
        "SELECT c.*, g.ad AS grup_ad FROM cari_kart c LEFT JOIN cari_grup g ON g.id=c.grup_id "
        "WHERE c.aktif=1 AND c.sirket_id=? ORDER BY c.unvan", (db.sirket_id(req),)
    ).fetchall()
    rows = []
    toplam = {"d0": 0.0, "d1": 0.0, "d2": 0.0, "d3": 0.0}
    for c in caris:
        a = _aging(conn, c["id"], bugun)
        if a["bakiye"] <= 0.005:
            continue
        c = dict(c)
        c["tip_etiket"] = _tip_etiket(c["tip"])
        rows.append({"cari": c, **a})
        toplam["d0"] += a["d0"]
        toplam["d1"] += a["d1"]
        toplam["d2"] += a["d2"]
        toplam["d3"] += a["d3"]
    toplam["toplam"] = toplam["d0"] + toplam["d1"] + toplam["d2"] + toplam["d3"]
    conn.close()
    return render_template("cari/rapor.html", rows=rows, toplam=toplam)


@route(r"/cari/gruplar", methods=("GET", "POST"), roles=WRITE_ROLES)
def cari_gruplar(req):
    conn = db.get_conn()
    if req.method == "POST":
        ad = (req.form.get("ad") or "").strip()
        tip = req.form.get("tip") or "Bölge"
        if ad:
            conn.execute("INSERT INTO cari_grup(ad, tip, aciklama, sirket_id) VALUES(?,?,?,?)",
                         (ad, tip, (req.form.get("aciklama") or "").strip(), db.sirket_id(req)))
            conn.commit()
            flash(req, f"Grup eklendi: {ad}", "ok")
        conn.close()
        return redirect("/cari/gruplar")
    gruplar = _gruplar(conn, db.sirket_id(req))
    conn.close()
    return render_template("cari/gruplar.html", gruplar=gruplar)


@route(r"/cari/(?P<cid>\d+)", roles=())
def cari_detay(req, cid):
    conn = db.get_conn()
    cari = conn.execute(
        "SELECT c.*, g.ad AS grup_ad FROM cari_kart c LEFT JOIN cari_grup g ON g.id=c.grup_id "
        "WHERE c.id=? AND c.sirket_id=?",
        (int(cid), db.sirket_id(req)),
    ).fetchone()
    if not cari:
        conn.close()
        flash(req, "Cari kartı bulunamadı.", "danger")
        return redirect("/cari")
    sekme = req.q("sekme") or ""
    cari = dict(cari)
    cari["tip_etiket"] = _tip_etiket(cari["tip"])

    ozet = _aging(conn, cari["id"])
    hareketler = conn.execute(
        "SELECT * FROM cari_hareket WHERE cari_id=? ORDER BY tarih DESC, id DESC LIMIT 60",
        (cari["id"],),
    ).fetchall()
    notlar = _notlar(conn, cari["id"])
    loglar = conn.execute(
        "SELECT * FROM audit_log WHERE tablo='cari_kart' AND kayit_id=? ORDER BY id DESC",
        (cari["id"],),
    ).fetchall()
    silinebilir = db.referans_var(conn, "cari_kart", cari["id"]) is None
    conn.close()
    return render_template("cari/detay.html", cari=cari, sekme=sekme, ozet=ozet,
                           hareketler=hareketler, notlar=notlar, loglar=loglar,
                           silinebilir=silinebilir)


@route(r"/cari/(?P<cid>\d+)/sil", methods=("POST",), roles=WRITE_ROLES)
def cari_sil(req, cid):
    conn = db.get_conn()
    cari = conn.execute("SELECT * FROM cari_kart WHERE id=? AND sirket_id=?",
                        (int(cid), db.sirket_id(req))).fetchone()
    if not cari:
        conn.close()
        return redirect("/cari")
    ref = db.referans_var(conn, "cari_kart", int(cid))
    if ref:
        conn.close()
        flash(req, f"Bu cari silinemez — '{ref}' üzerinde kaydı var. Pasifleştirebilirsiniz.", "danger")
        return redirect(f"/cari/{cid}")
    audit(req, "cari_kart", int(cid), "sil", {"unvan": cari["unvan"], "kod": cari["kod"]})
    conn.execute("DELETE FROM cari_kart WHERE id=?", (int(cid),))
    conn.commit()
    conn.close()
    flash(req, "Cari silindi.", "ok")
    return redirect("/cari")


@route(r"/cari/(?P<cid>\d+)/ekstre", roles=())
def cari_ekstre(req, cid):
    conn = db.get_conn()
    cari = conn.execute("SELECT * FROM cari_kart WHERE id=? AND sirket_id=?",
                        (int(cid), db.sirket_id(req))).fetchone()
    if not cari:
        conn.close()
        return redirect("/cari")
    cari = dict(cari)
    cari["tip_etiket"] = _tip_etiket(cari["tip"])

    bas = req.q("bas")
    bit = req.q("bit") or datetime.date.today().isoformat()
    pb = req.q("pb")
    sid = db.sirket_id(req)
    pbs = db.para_birimleri(sid=sid)
    if pb and pb not in pbs:
        pb = None

    where, params = ["cari_id=?"], [cari["id"]]
    if bas:
        where.append("tarih >= ?")
        params.append(bas)
    if bit:
        where.append("tarih <= ?")
        params.append(bit)
    if pb:
        where.append("para_birimi=?")
        params.append(pb)
    rows = [dict(r) for r in conn.execute(
        "SELECT * FROM cari_hareket WHERE " + " AND ".join(where) + " ORDER BY tarih, id",
        params,
    ).fetchall()]

    opening = 0.0
    if bas:
        _ow, _op = ["cari_id=?", "tarih < ?"], [cari["id"], bas]
        if pb:
            _ow.append("para_birimi=?")
            _op.append(pb)
        opening = conn.execute(
            "SELECT COALESCE(SUM(borc-alacak),0) AS s FROM cari_hareket WHERE " + " AND ".join(_ow),
            _op,
        ).fetchone()["s"]
    bal = opening
    for h in rows:
        bal += (h["borc"] or 0) - (h["alacak"] or 0)
        h["bakiye"] = bal

    _tw, _tp = ["cari_id=?"], [cari["id"]]
    if pb:
        _tw.append("para_birimi=?")
        _tp.append(pb)
    tot = conn.execute(
        "SELECT COALESCE(SUM(borc),0) b, COALESCE(SUM(alacak),0) a FROM cari_hareket WHERE "
        + " AND ".join(_tw), _tp,
    ).fetchone()
    bakiye = tot["b"] - tot["a"]
    yas = _aging(conn, cari["id"])

    # D012-D — döviz bazlı alt toplamlar (Tümü için; filtre aktifken de bu kartlar gösterilir).
    pb_totals = []
    for _pb in pbs:
        r = conn.execute(
            "SELECT COALESCE(SUM(borc),0) b, COALESCE(SUM(alacak),0) a, "
            "AVG(CASE WHEN doviz_kur>0 THEN doviz_kur END) k "
            "FROM cari_hareket WHERE cari_id=? AND para_birimi=?", (cari["id"], _pb)).fetchone()
        pb_totals.append({"kod": _pb, "borc": r["b"], "alacak": r["a"],
                          "net": (r["b"] or 0) - (r["a"] or 0), "kur": r["k"] or 0.0})
    conn.close()

    return render_template(
        "cari/ekstre.html", cari=cari, hareketler=rows,
        bakiye=bakiye, top_borc=tot["b"], top_alacak=tot["a"],
        yas={"0_30": yas["d0"], "31_60": yas["d1"], "61_90": yas["d2"], "90_plus": yas["d3"]},
        pbs=pbs, pb=pb, pb_totals=pb_totals,
        filtro={"bas": bas, "bit": bit, "pb": pb},
    )


@route(r"/cari/(?P<cid>\d+)/hareket", methods=("GET", "POST"), roles=WRITE_ROLES)
def cari_hareket(req, cid):
    conn = db.get_conn()
    cari = conn.execute("SELECT * FROM cari_kart WHERE id=? AND sirket_id=?",
                        (int(cid), db.sirket_id(req))).fetchone()
    if not cari:
        conn.close()
        return redirect("/cari")

    if req.method == "POST":
        tarih = req.form.get("tarih") or datetime.date.today().isoformat()
        yon = req.form.get("yon")
        tutar = _f(req.form.get("tutar"))
        if tutar <= 0:
            flash(req, "Tutar 0'dan büyük olmalıdır.", "danger")
            conn.close()
            return redirect(f"/cari/{cid}/hareket")
        borc = tutar if yon == "borc" else 0.0
        alacak = tutar if yon == "alacak" else 0.0
        cur = conn.execute(
            "INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, borc, alacak, created_by, sirket_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?)",
            (
                cari["id"], tarih,
                req.form.get("vade") or None,
                req.form.get("belge_tipi") or "Diğer",
                (req.form.get("belge_no") or "").strip() or None,
                (req.form.get("aciklama") or "").strip(),
                borc, alacak, req.user["id"], db.sirket_id(req),
            ),
        )
        hid = cur.lastrowid
        conn.commit()
        audit(req, "cari_hareket", hid, "olustur", {"cari_id": cari["id"], "borc": borc, "alacak": alacak})
        conn.close()
        flash(req, "Hareket kaydedildi.", "ok")
        return redirect(f"/cari/{cid}/ekstre")

    a = _aging(conn, cari["id"])
    conn.close()
    return render_template("cari/hareket_form.html", cari=cari, bakiye=a["bakiye"],
                           belge_tipleri=BELGE_TIPLERI,
                           bugun=datetime.date.today().isoformat())


@route(r"/cari/(?P<cid>\d+)/duzenle", methods=("GET", "POST"), roles=WRITE_ROLES)
def cari_duzenle(req, cid):
    conn = db.get_conn()
    cari = conn.execute("SELECT * FROM cari_kart WHERE id=? AND sirket_id=?",
                        (int(cid), db.sirket_id(req))).fetchone()
    if not cari:
        conn.close()
        return redirect("/cari")

    if req.method == "POST":
        conn.execute(
            "UPDATE cari_kart SET unvan=?, kisa_ad=?, tip=?, vergi_dairesi=?, vergi_no=?, adres=?, il=?, ilce=?, "
            "telefon=?, gsm=?, email=?, yetkili=?, kredi_limiti=?, para_birimi=?, iskonto_orani=?, grup_id=?, not_=?, "
            "e_fatura_mukellefi=?, updated_by=?, updated_at=datetime('now','localtime') WHERE id=?",
            (
                (req.form.get("unvan") or "").strip(),
                (req.form.get("kisa_ad") or "").strip(),
                req.form.get("tip") or "Musteri",
                (req.form.get("vergi_dairesi") or "").strip(),
                (req.form.get("vergi_no") or "").strip(),
                (req.form.get("adres") or "").strip(),
                (req.form.get("il") or "").strip(),
                (req.form.get("ilce") or "").strip(),
                (req.form.get("telefon") or "").strip(),
                (req.form.get("gsm") or "").strip(),
                (req.form.get("email") or "").strip(),
                (req.form.get("yetkili") or "").strip(),
                _f(req.form.get("kredi_limiti")),
                req.form.get("para_birimi") or "TRY",
                _f(req.form.get("iskonto_orani")),
                _i(req.form.get("grup_id")),
                (req.form.get("not_") or "").strip(),
                1 if req.form.get("e_fatura_mukellefi") else 0,
                req.user["id"], cari["id"],
            ),
        )
        conn.commit()
        audit(req, "cari_kart", cari["id"], "guncelle", {"unvan": (req.form.get("unvan") or "").strip()})
        conn.close()
        flash(req, "Cari kartı güncellendi.", "ok")
        return redirect(f"/cari/{cid}")

    conn.close()
    return render_template("cari/form.html", cari=cari, gruplar=db_tmp_gruplar(req, aktif=True),
                           para_birimleri=db.para_birimleri(sid=db.sirket_id(req)))


@route(r"/cari/(?P<cid>\d+)/not", methods=("POST",), roles=())
def cari_not(req, cid):
    metin = (req.form.get("metin") or "").strip()
    if not metin:
        flash(req, "Not boş olamaz.", "danger")
        return redirect(f"/cari/{cid}?sekme=not")
    etiketler = ",".join(sorted({t for t in metin.split() if t.startswith("#")}))
    hatirlatma = req.form.get("hatirlatma") or None
    conn = db.get_conn()
    cur = conn.execute(
        "INSERT INTO notlar(ilgili_tablo, ilgili_id, metin, etiketler, hatirlatma, kullanici_id, sirket_id) "
        "VALUES(?,?,?,?,?,?,?)",
        ("cari_kart", int(cid), metin, etiketler or None, hatirlatma, req.user["id"],
         db.sirket_id(req)),
    )
    conn.commit()
    conn.close()
    flash(req, "Not eklendi.", "ok")
    return redirect(f"/cari/{cid}?sekme=not")


# --------------------------------------------------------------------------
def _f(v):
    try:
        return float(v or 0)
    except (TypeError, ValueError):
        return 0.0


def _i(v):
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def register():
    """Modül kaydı (bağımlılık sırası için ileride kullanılacak)."""
    return "cari"
