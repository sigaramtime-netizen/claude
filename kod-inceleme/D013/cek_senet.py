# -*- coding: utf-8 -*-
"""Çek / Senet modülü (Faz 2 — Satış Döngüsü, zincirin 5. halkası).

- tip: 'Alinan' = müşteriden aldığımız (tahsil edeceğimiz) çek/senet,
       'Verilen' = tedarikçiye verdiğimiz (ödeyeceğimiz) çek/senet.
- tur: 'Cek' / 'Senet'.
- K2/K6: tahsil/öde işlemi cari hareketi TEK işlemde üretir:
    Alinan → 'Tahsil Edildi' → müşteri ALACAK (belge_tipi 'Tahsilat').
    Verilen → 'Ödendi'       → tedarikçi BORÇ (belge_tipi 'Ödeme').
    ilgili_modul='CekSenet', ilgili_kayit_id=çek/senet id.
- K15: tahsil/öde yapılmış çek/senet, iptalde kendi cari hareketini geri alır.
- Ek dosya (attachment): fiziksel çek/senet görüntüsü eklenir (ekler.py — genel
  `ek_dosya` tablosu, ilgili_modul='CekSenet').
"""
import datetime
import urllib.parse

import db
import ekler
import muhasebe
from config import PARA_BIRIMLERI
from core import route, render_template, redirect, flash, audit, notify, izole_sube, sube_koruma, Response

CEK_WRITE = ("Admin", "Muhasebe")
TIPLER = ["Alinan", "Verilen"]
TIP_LABEL = {"Alinan": "Alınan (Tahsil)", "Verilen": "Verilen (Ödeme)"}
TURLER = ["Cek", "Senet"]
DURUMLAR = ["Bekliyor", "Tahsile Verildi", "Tahsil Edildi", "Ödendi",
            "Karşılıksız", "Ciro", "İptal"]
DURUM_LABEL = {"Bekliyor": "Portföyde", "Tahsile Verildi": "Tahsile Verildi",
               "Tahsil Edildi": "Tahsil Edildi", "Ödendi": "Ödendi",
               "Karşılıksız": "Karşılıksız", "Ciro": "Ciro", "İptal": "İptal"}
DURUM_BADGE = {"Bekliyor": "b-warn", "Tahsile Verildi": "b-info", "Tahsil Edildi": "b-ok",
               "Ödendi": "b-ok", "Karşılıksız": "b-danger", "Ciro": "b-info",
               "İptal": "b-muted"}


def _f(v, default=0.0):
    try:
        return float(v if v not in (None, "") else default)
    except (TypeError, ValueError):
        return default


def _i(v):
    try:
        return int(v) if v not in (None, "") else None
    except (TypeError, ValueError):
        return None


def cek_olustur(conn, req, tip, tur, no, cari_id, banka="", sube_ad="", tutar=0.0,
                para_birimi="TRY", doviz_kur=None, keside=None, vade=None, aciklama=""):
    """D013 — tek noktadan çek/senet yazma (Bekliyor + K26 senkron).

    `_form_post` insert dalı ile D013 tahsilat/ödeme ekranı aynı kodu kullanır →
    kod tekrarı yok. COMMIT çağıranın işidir (POS `pos_satis_olustur` deseni).
    Dönüş: yeni çek/senet id.
    """
    cur = conn.execute(
        "INSERT INTO cek_senet(no, tip, tur, cari_id, banka, sube_ad, tutar, para_birimi, "
        "doviz_kur, keside_tarihi, vade, durum, aciklama, sube_id, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,'Bekliyor',?,?,?,?)",
        (no, tip, tur, cari_id, banka, sube_ad, tutar, para_birimi, doviz_kur,
         keside, vade, aciklama, izole_sube(req), req.user["id"], db.sirket_id(req)),
    )
    cid = cur.lastrowid
    # K26: çek alındığında cari kapanır (ALACAK/BORÇ) + giris fişi (101/121/103/321)
    muhasebe.cek_senkron(conn, cid, created_by=req.user["id"])
    return cid


def _cariler(conn, tip, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    if tip == "Verilen":
        return conn.execute(
            "SELECT id, unvan, kod FROM cari_kart WHERE aktif=1 AND tip IN ('Tedarikci','HerIkisi') "
            + extra + " ORDER BY unvan", args).fetchall()
    return conn.execute(
        "SELECT id, unvan, kod FROM cari_kart WHERE aktif=1 AND tip IN ('Musteri','HerIkisi') "
        + extra + " ORDER BY unvan", args).fetchall()


def _detay(conn, cid, sid=None):
    where, params = "c.id=?", [int(cid)]
    if sid is not None:
        where += " AND c.sirket_id=?"
        params.append(sid)
    r = conn.execute(
        "SELECT c.*, k.unvan AS cari_unvan, k.kod AS cari_kod, sb.ad AS sube_ad "
        "FROM cek_senet c LEFT JOIN cari_kart k ON k.id=c.cari_id "
        "LEFT JOIN sube sb ON sb.id=c.sube_id WHERE " + where, params,
    ).fetchone()
    return dict(r) if r else None


# Cari hareket artık `muhasebe.cek_senkron` ile yönetilir (K26 revize): çek alındığında
# (giris) cari kapanır; tahsil/ödeme ara hesaptan (101/121/103/321) kasaya geçer.
# --------------------------------------------------------------------------
# Rotalar
# --------------------------------------------------------------------------
@route(r"/cek_senet", roles=())
def cek_liste(req):
    conn = db.get_conn()
    q = req.q("q").strip()
    tip = req.q("tip") if req.q("tip") in TIPLER else ""
    tur = req.q("tur") if req.q("tur") in TURLER else ""
    durum = req.q("durum") if req.q("durum") in DURUMLAR else ""
    where, params = ["c.sirket_id = ?"], [db.sirket_id(req)]
    if q:
        where.append("(c.no LIKE ? OR c.banka LIKE ? OR k.unvan LIKE ? OR k.kod LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like, like]
    if tip:
        where.append("c.tip=?")
        params.append(tip)
    if tur:
        where.append("c.tur=?")
        params.append(tur)
    if durum:
        where.append("c.durum=?")
        params.append(durum)
    if izole_sube(req):
        where.append("c.sube_id=?")
        params.append(izole_sube(req))
    w = " AND ".join(where)
    rows = conn.execute(
        f"SELECT c.*, k.unvan AS cari_unvan, k.kod AS cari_kod, "
        f"(SELECT COUNT(*) FROM ek_dosya e WHERE e.ilgili_modul='CekSenet' AND e.ilgili_kayit_id=c.id) "
        f"AS ek_sayisi FROM cek_senet c LEFT JOIN cari_kart k ON k.id=c.cari_id "
        f"WHERE {w} ORDER BY c.vade, c.id DESC", params,
    ).fetchall()
    bugun = datetime.date.today()
    _rows = []
    for r in rows:
        r = dict(r)
        try:
            d = datetime.date.fromisoformat(r["vade"])
            r["gun"] = (d - bugun).days
        except (ValueError, TypeError):
            r["gun"] = None
        r["gecikmis"] = r["gun"] is not None and r["gun"] < 0 and r["durum"] in ("Bekliyor", "Tahsile Verildi")
        _rows.append(r)
    ozet = {d: conn.execute("SELECT COUNT(*) c FROM cek_senet WHERE durum=? AND sirket_id=?",
                             (d, db.sirket_id(req))).fetchone()["c"]
            for d in DURUMLAR}
    portfoy = conn.execute(
        "SELECT COALESCE(SUM(CASE WHEN tip='Alinan' THEN tutar ELSE 0 END),0) a, "
        "COALESCE(SUM(CASE WHEN tip='Verilen' THEN tutar ELSE 0 END),0) v "
        "FROM cek_senet WHERE durum IN ('Bekliyor','Tahsile Verildi') AND sirket_id=?",
        (db.sirket_id(req),)).fetchone()
    conn.close()
    return render_template("cek_senet/liste.html", rows=_rows, tip_label=TIP_LABEL, tipler=TIPLER,
                           turler=TURLER, durumlar=DURUMLAR, durum_label=DURUM_LABEL,
                           durum_badge=DURUM_BADGE, ozet=ozet,
                           portfoy={"al_inan": portfoy["a"], "verilen": portfoy["v"]},
                           filtro={"q": q, "tip": tip, "tur": tur, "durum": durum})


@route(r"/cek_senet/vade", roles=())
def cek_vade_takvimi(req):
    """Vade takvimi: bekleyen/tahsile verilmiş çek/senetleri vade dilimlerine ayırır."""
    conn = db.get_conn()
    bugun = datetime.date.today()
    iz = izole_sube(req)
    rows = conn.execute(
        "SELECT c.*, k.unvan AS cari_unvan, k.kod AS cari_kod FROM cek_senet c "
        "LEFT JOIN cari_kart k ON k.id=c.cari_id "
        "WHERE c.durum IN ('Bekliyor','Tahsile Verildi') AND c.sirket_id=?"
        + (" AND c.sube_id=?" if iz else "") +
        " ORDER BY c.vade", [db.sirket_id(req)] + ([iz] if iz else [])).fetchall()
    gecikmis, bugun_list, yaklasan, ileriki = [], [], [], []
    for r in rows:
        r = dict(r)
        try:
            d = datetime.date.fromisoformat(r["vade"])
            r["gun"] = (d - bugun).days
        except (ValueError, TypeError):
            r["gun"] = None
        if r["gun"] is None:
            ileriki.append(r)
        elif r["gun"] < 0:
            gecikmis.append(r)
        elif r["gun"] == 0:
            bugun_list.append(r)
        elif r["gun"] <= 7:
            yaklasan.append(r)
        else:
            ileriki.append(r)
    conn.close()
    return render_template("cek_senet/vade.html", gecikmis=gecikmis, bugun=bugun_list,
                           yaklasan=yaklasan, ileriki=ileriki, tip_label=TIP_LABEL,
                           durum_label=DURUM_LABEL, durum_badge=DURUM_BADGE)


@route(r"/cek_senet/yeni", methods=("GET", "POST"), roles=CEK_WRITE)
def cek_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        return _form_post(req, conn, None)
    cariler = _cariler(conn, "Alinan", db.sirket_id(req))
    conn.close()
    return render_template("cek_senet/form.html", cek=None, cariler=cariler,
                           tip="Alinan", para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           bugun=datetime.date.today().isoformat())


@route(r"/cek_senet/(?P<cid>\d+)", roles=())
def cek_detay(req, cid):
    conn = db.get_conn()
    cek = _detay(conn, cid, db.sirket_id(req))
    if not cek:
        conn.close()
        flash(req, "Çek/senet bulunamadı.", "danger")
        return redirect("/cek_senet")
    if not sube_koruma(req, cek["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    ekler_list = ekler.ekler_for(conn, "CekSenet", cek["id"])
    loglar = conn.execute("SELECT * FROM audit_log WHERE tablo='cek_senet' AND kayit_id=? "
                          "ORDER BY id DESC", (cek["id"],)).fetchall()
    ek_upload = req.user["rol"] in ekler.EK_WRITE
    conn.close()
    return render_template("cek_senet/detay.html", cek=cek, ekler=ekler_list, loglar=loglar,
                           tip_label=TIP_LABEL, durum_label=DURUM_LABEL, durum_badge=DURUM_BADGE,
                           ek_upload=ek_upload, ek_modul="CekSenet", ek_kayit_id=cek["id"],
                           ek_geri=f"/cek_senet/{cek['id']}")


@route(r"/cek_senet/(?P<cid>\d+)/duzenle", methods=("GET", "POST"), roles=CEK_WRITE)
def cek_duzenle(req, cid):
    conn = db.get_conn()
    cek = conn.execute("SELECT * FROM cek_senet WHERE id=? AND sirket_id=?",
                       (int(cid), db.sirket_id(req))).fetchone()
    if not cek:
        conn.close()
        return redirect("/cek_senet")
    if cek["durum"] != "Bekliyor":
        conn.close()
        flash(req, "Yalnızca 'Bekliyor' durumundaki çek/senet düzenlenebilir.", "danger")
        return redirect(f"/cek_senet/{cek['id']}")
    if req.method == "POST":
        return _form_post(req, conn, cek)
    cariler = _cariler(conn, cek["tip"], db.sirket_id(req))
    conn.close()
    return render_template("cek_senet/form.html", cek=cek, cariler=cariler, tip=cek["tip"],
                           para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           bugun=datetime.date.today().isoformat())


@route(r"/cek_senet/(?P<cid>\d+)/sil", methods=("POST",), roles=CEK_WRITE)
def cek_sil(req, cid):
    conn = db.get_conn()
    cek = conn.execute("SELECT * FROM cek_senet WHERE id=? AND sirket_id=?",
                       (int(cid), db.sirket_id(req))).fetchone()
    if not cek:
        conn.close()
        return redirect("/cek_senet")
    if not sube_koruma(req, cek["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    if cek["durum"] != "Bekliyor":
        conn.close()
        flash(req, "Yalnızca 'Bekliyor' çek/senet silinebilir (diğer durumlar mali iz taşır).", "danger")
        return redirect(f"/cek_senet/{cek['id']}")
    audit(req, "cek_senet", cek["id"], "sil", {"no": cek["no"], "tip": cek["tip"], "tur": cek["tur"]})
    # K26: Bekliyor çek/senet oluşturulurken cari hareketi + giriş fişi üretilir; silinirken
    # bu mali iz geri alınır (yetim cari_hareket / yevmiye fişi kalmasın).
    conn.execute("DELETE FROM cari_hareket WHERE ilgili_modul='CekSenet' AND ilgili_kayit_id=?",
                 (cek["id"],))
    muhasebe.fis_sil_tumu(conn, "CekSenet", cek["id"])
    ekler.ek_temizle(conn, "CekSenet", cek["id"])
    db.bildirim_sil(conn, "cek_senet", cek["id"])
    conn.execute("DELETE FROM cek_senet WHERE id=?", (cek["id"],))
    conn.commit()
    conn.close()
    flash(req, "Çek/Senet silindi.", "ok")
    return redirect("/cek_senet")


def _form_post(req, conn, mevcut):
    tip = req.form.get("tip") if req.form.get("tip") in TIPLER else "Alinan"
    tur = req.form.get("tur") if req.form.get("tur") in TURLER else "Cek"
    no = (req.form.get("no") or "").strip()
    cari_id = _i(req.form.get("cari_id"))
    banka = (req.form.get("banka") or "").strip()
    sube_ad = (req.form.get("sube_ad") or "").strip()
    tutar = _f(req.form.get("tutar"))
    keside = (req.form.get("keside_tarihi") or "").strip() or None
    vade = (req.form.get("vade") or "").strip()
    aciklama = (req.form.get("aciklama") or "").strip()
    para_birimi = req.form.get("para_birimi") if req.form.get("para_birimi") in db.para_birimleri(sid=db.sirket_id(req)) else "TRY"
    doviz_kur = _f(req.form.get("doviz_kur"), None)
    if para_birimi == "TRY":
        doviz_kur = None
    elif not doviz_kur or doviz_kur <= 0:
        doviz_kur = db.guncel_kur(conn, para_birimi, db.sirket_id(req))

    if req.form.get("tip_degistir"):
        return _form_render(req, conn, mevcut)

    if not no:
        flash(req, "Çek/senet numarası zorunludur.", "danger")
        return _form_render(req, conn, mevcut)
    if not cari_id:
        flash(req, "Cari seçimi zorunludur.", "danger")
        return _form_render(req, conn, mevcut)
    if tutar <= 0:
        flash(req, "Tutar sıfırdan büyük olmalıdır.", "danger")
        return _form_render(req, conn, mevcut)
    if not vade:
        flash(req, "Vade zorunludur.", "danger")
        return _form_render(req, conn, mevcut)

    if mevcut:
        conn.execute(
            "UPDATE cek_senet SET tip=?, tur=?, no=?, cari_id=?, banka=?, sube_ad=?, tutar=?, "
            "para_birimi=?, doviz_kur=?, keside_tarihi=?, vade=?, aciklama=?, "
            "updated_at=datetime('now','localtime') WHERE id=?",
            (tip, tur, no, cari_id, banka, sube_ad, tutar, para_birimi, doviz_kur,
             keside, vade, aciklama, mevcut["id"]),
        )
        cid = mevcut["id"]
        # K26: cari + fiş setini yeni değerlerle yeniden senkronize et
        muhasebe.cek_senkron(conn, cid, created_by=req.user["id"], zorla=True)
        islem = ("guncelle", {"no": no}, "Çek/senet güncellendi.")
    else:
        # D013: insert dalı tek-nokta çekirdeğe taşındı (davranış birebir aynı).
        cid = cek_olustur(conn, req, tip, tur, no, cari_id, banka, sube_ad, tutar,
                          para_birimi, doviz_kur, keside, vade, aciklama)
        islem = ("olustur", {"no": no}, f"Çek/senet oluşturuldu: {no}")
    conn.commit()
    audit(req, "cek_senet", cid, islem[0], islem[1])
    flash(req, islem[2], "ok")
    conn.close()
    return redirect(f"/cek_senet/{cid}")


def _form_render(req, conn, mevcut):
    tip = req.form.get("tip") if req.form.get("tip") in TIPLER else (
        mevcut["tip"] if mevcut else "Alinan")
    if mevcut:
        cek = dict(mevcut)
        for k in ("tip", "tur", "no", "banka", "sube_ad", "tutar", "aciklama",
                  "para_birimi", "doviz_kur"):
            f = req.form.get(k)
            if f not in (None, ""):
                cek[k] = f
    else:
        cek = {
            "tip": tip,
            "tur": req.form.get("tur") if req.form.get("tur") in TURLER else "Cek",
            "no": (req.form.get("no") or "").strip(),
            "cari_id": _i(req.form.get("cari_id")),
            "banka": (req.form.get("banka") or "").strip(),
            "sube_ad": (req.form.get("sube_ad") or "").strip(),
            "tutar": _f(req.form.get("tutar")),
            "keside_tarihi": (req.form.get("keside_tarihi") or "").strip() or None,
            "vade": (req.form.get("vade") or "").strip(),
            "aciklama": (req.form.get("aciklama") or "").strip(),
            "para_birimi": req.form.get("para_birimi") if req.form.get("para_birimi") in db.para_birimleri(sid=db.sirket_id(req)) else "TRY",
            "doviz_kur": _f(req.form.get("doviz_kur"), None),
        }
    cariler = _cariler(conn, tip, db.sirket_id(req))
    return render_template("cek_senet/form.html", cek=cek, cariler=cariler, tip=tip,
                           para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           bugun=datetime.date.today().isoformat())


@route(r"/cek_senet/(?P<cid>\d+)/durum", methods=("POST",), roles=CEK_WRITE)
def cek_durum(req, cid):
    hedef = req.form.get("durum")
    if hedef not in DURUMLAR:
        flash(req, "Geçersiz durum geçişi.", "danger")
        return redirect(f"/cek_senet/{cid}")
    conn = db.get_conn()
    cek = conn.execute("SELECT * FROM cek_senet WHERE id=? AND sirket_id=?",
                       (int(cid), db.sirket_id(req))).fetchone()
    if not cek:
        conn.close()
        return redirect("/cek_senet")

    izinli = {
        "Bekliyor": ["Tahsile Verildi", "Tahsil Edildi", "Ödendi", "Ciro", "İptal"],
        "Tahsile Verildi": ["Tahsil Edildi", "Karşılıksız", "İptal"],
        "Tahsil Edildi": ["Karşılıksız", "İptal"],
        "Ödendi": ["İptal"],
        "Karşılıksız": ["Tahsil Edildi", "Ciro", "İptal"],
        "Ciro": ["İptal"],
        "İptal": [],
    }
    if hedef not in izinli.get(cek["durum"], []):
        conn.close()
        flash(req, f"'{cek['durum']}' durumundan '{hedef}' durumuna geçilemez.", "danger")
        return redirect(f"/cek_senet/{cid}")

    # Tip kısıtları: Tahsil/Tahsile Verildi/Karşılıksız/Ciro yalnız Alınan; Ödendi yalnız Verilen
    alinan_ozel = {"Tahsile Verildi", "Tahsil Edildi", "Karşılıksız", "Ciro"}
    if hedef in alinan_ozel and cek["tip"] != "Alinan":
        conn.close()
        flash(req, f"'{hedef}' durumu yalnızca alınan çek/senet için geçerlidir.", "danger")
        return redirect(f"/cek_senet/{cid}")
    if hedef == "Ödendi" and cek["tip"] != "Verilen":
        conn.close()
        flash(req, "Alınan çek/senet 'Ödendi' olamaz (Tahsil Edildi kullanın).", "danger")
        return redirect(f"/cek_senet/{cid}")

    # İptal engeli: çek/senete bağlı Kasa/Banka hareketi varsa önce onu çöz
    if hedef == "İptal":
        bagli = conn.execute(
            "SELECT (SELECT COUNT(*) FROM kasa_hareket WHERE ilgili_modul='CekSenet' AND ilgili_kayit_id=?) "
            "+ (SELECT COUNT(*) FROM banka_hareket WHERE ilgili_modul='CekSenet' AND ilgili_kayit_id=?) AS c",
            (cek["id"], cek["id"]),
        ).fetchone()["c"]
        if bagli:
            conn.close()
            flash(req, "Bu çek/senete bağlı Kasa/Banka hareketi var. Önce o hareketi iptal edin, "
                       "sonra çek/senedi iptal edin.", "danger")
            return redirect(f"/cek_senet/{cek['id']}")

    conn.execute("UPDATE cek_senet SET durum=?, updated_at=datetime('now','localtime') WHERE id=?",
                 (hedef, int(cid)))

    # K26 revize: cari hareket + yevmiye seti GÜNCEL durumla senkronize edilir.
    # Cari, çek alındığında (giris) kapanır; tahsil/ödeme ara hesaptan (101/121/103/321) kasaya geçer.
    muhasebe.cek_senkron(conn, int(cid), created_by=req.user["id"])
    conn.commit()
    audit(req, "cek_senet", int(cid), "durum", {"eski": cek["durum"], "yeni": hedef})
    if hedef in ("Tahsil Edildi", "Ödendi"):
        notify("bilgi", "Çek/senet işlendi",
               f"{cek['no']} nolu çek/senet {hedef.lower()} olarak işlendi; ara hesap kapatıldı.",
               "cek_senet", int(cid), sirket_id=db.sirket_id(req))
    elif hedef == "Karşılıksız":
        notify("uyari", "Çek/senet karşılıksız çıktı",
               f"{cek['no']} nolu çek/senet karşılıksız çıktı; cari borç geri alındı.",
               "cek_senet", int(cid), sirket_id=db.sirket_id(req))
    elif hedef == "Ciro":
        notify("bilgi", "Çek/senet ciro edildi",
               f"{cek['no']} ciro edildi; karşı taraf kaydı için Genel Muhasebe'de manuel fiş girin.",
               "cek_senet", int(cid), sirket_id=db.sirket_id(req))
    conn.close()
    flash(req, f"Çek/senet durumu '{hedef}' olarak güncellendi.", "ok")
    return redirect(f"/cek_senet/{cid}")


@route(r"/cek_senet/(?P<cid>\d+)/yazdir", roles=())
def cek_yazdir(req, cid):
    conn = db.get_conn()
    cek = _detay(conn, cid, db.sirket_id(req))
    conn.close()
    if not cek:
        return redirect("/cek_senet")
    return render_template("cek_senet/yazdir.html", cek=cek, tip_label=TIP_LABEL)


def register():
    return "cek_senet"
