# -*- coding: utf-8 -*-
"""Teklif modülü (Faz 2 — Satış Döngüsü, zincirin 1. halkası).

Belge zinciri: Teklif → Sipariş → İrsaliye → Fatura. Teklif; müşteriye fiyat teklifi
hazırlama, durum akışı (Taslak → Gönderildi → Onaylandı/Reddedildi/Süresi Doldu),
geçerlilik tarihi + otomatik hatırlatma ve PDF/yazdır çıktısı içerir.
Onaylanan teklif, Sipariş modülünde tek tıkla siparişe dönüştürülecek (zincir hazır).

Konvansiyon: teklif_kalem.tutar = satır net tutarı (KDV hariç).
ara_toplam = Σ net; kdv_toplam = Σ (net × kdv/100); genel = ara + kdv.
"""
import datetime
import urllib.parse

import db
import stok
from core import route, render_template, redirect, flash, audit, izole_sube, sube_koruma, Response, kdv_ayikla

TEKLIF_WRITE = ("Admin", "Muhasebe", "Satis")
DURUMLAR = ["Taslak", "Gönderildi", "Onaylandı", "Reddedildi", "Süresi Doldu"]
DURUM_BADGE = {
    "Taslak": "b-muted",
    "Gönderildi": "b-info",
    "Onaylandı": "b-ok",
    "Reddedildi": "b-danger",
    "Süresi Doldu": "b-warn",
}


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


def _cariler(conn, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    return conn.execute(
        "SELECT id, unvan, kod, iskonto_orani FROM cari_kart "
        "WHERE aktif=1 AND tip IN ('Musteri','HerIkisi')" + extra + " ORDER BY unvan", args
    ).fetchall()


def _stoklar(conn, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    return conn.execute(
        "SELECT id, kod, ad, satis_fiyat, kdv_orani, iskonto_orani, birim FROM stok_kart "
        "WHERE aktif=1" + extra + " ORDER BY kod", args
    ).fetchall()


def _cari_secim(cariler, cari_id):
    """Seçili cari için görünen etiket (unvan + kod) ve iskonto oranı (K9 için)."""
    for c in cariler:
        if c["id"] == cari_id:
            return f"{c['unvan']} ({c['kod']})", (c["iskonto_orani"] or 0.0)
    return "", 0.0


def _satirlar_from_form(req, kdv_dahil=0):
    stok_ids = req.form_list.get("k_stok_id", [])
    varyantlar = req.form_list.get("k_varyant_id", [])
    manuel_adlar = req.form_list.get("k_manuel_ad", [])
    birimler = req.form_list.get("k_birim", [])
    gorunen_adlar = req.form_list.get("k_goruntu_ad", [])
    miktarlar = req.form_list.get("k_miktar", [])
    bf = req.form_list.get("k_birim_fiyat", [])
    isk = req.form_list.get("k_iskonto", [])
    kdv = req.form_list.get("k_kdv", [])
    kdv_dahil_list = req.form_list.get("k_kdv_dahil", [])
    n = max(len(stok_ids), len(manuel_adlar), len(miktarlar))
    rows = []
    for i in range(n):
        sid_raw = (stok_ids[i] if i < len(stok_ids) else "").strip()
        sid = int(sid_raw) if sid_raw.isdigit() else None
        manuel_ad = (manuel_adlar[i] if i < len(manuel_adlar) else "").strip()
        kdv_orani = _f(kdv[i] if i < len(kdv) else 20, 20)
        birim_fiyat = _f(bf[i] if i < len(bf) else 0)
        # D012-B — satır bazlı KDV: açık "1"=dahil, "0"=hariç, boş=belge genelini izler.
        raw_line = (kdv_dahil_list[i] if i < len(kdv_dahil_list) else "").strip()
        if raw_line in ("1", "dahil", "on"):
            line_dahil, line_db = 1, 1
        elif raw_line in ("0", "haric"):
            line_dahil, line_db = 0, 0
        else:
            line_dahil, line_db = kdv_dahil, None
        # F2 — KDV dahil girişte DB'ye NET yazılır (tek kaynak: core.kdv_ayikla).
        if line_dahil:
            birim_fiyat = kdv_ayikla(birim_fiyat, kdv_orani)
        rows.append({
            "stok_id": sid,  # None → manuel (serbest metin) satır
            "varyant_id": _i(varyantlar[i]) or 0 if i < len(varyantlar) else 0,
            "miktar": _f(miktarlar[i] if i < len(miktarlar) else 1, 1),
            "birim_fiyat": birim_fiyat,
            "iskonto_orani": _f(isk[i] if i < len(isk) else 0),
            "kdv_orani": kdv_orani,
            "kdv_dahil": line_db,
            "manuel_ad": manuel_ad,
            "birim": (birimler[i] if i < len(birimler) else "").strip() or None,
            "goruntu_adi": (gorunen_adlar[i] if i < len(gorunen_adlar) else "").strip() or None,
        })
    return rows


def _toplamlar(rows):
    ara = isk = kdv = 0.0
    for r in rows:
        brut = r["miktar"] * r["birim_fiyat"]
        isk_t = brut * r["iskonto_orani"] / 100
        net = brut - isk_t
        r["tutar"] = round(net, 2)
        ara += net
        isk += isk_t
        # D012-B — KDV her satırda net × oran/100 hesaplanır; "dahil" yalnızca girişi brüt→net çevirir.
        kdv += net * r["kdv_orani"] / 100
    return {"ara_toplam": round(ara, 2), "iskonto_toplam": round(isk, 2),
            "kdv_toplam": round(kdv, 2), "genel_toplam": round(ara + kdv, 2)}


def _satir_gorunum(conn, rows, sid=None):
    stok_map = {s["id"]: dict(s) for s in _stoklar(conn, sid)}
    out = []
    for r in rows:
        s = stok_map.get(r["stok_id"], {})
        r = dict(r)
        manuel = not r.get("stok_id")
        r["manuel"] = manuel
        if manuel:
            r["stok_kod"] = ""
            r["stok_ad"] = r.get("manuel_ad") or "(manuel satır)"
            r["gorunen_ad"] = r.get("manuel_ad") or "(manuel satır)"
            r["birim"] = r.get("birim") or "Adet"
        else:
            r["stok_kod"] = s.get("kod", "?")
            r["stok_ad"] = s.get("ad", "?")
            r["gorunen_ad"] = (r.get("goruntu_adi") or "").strip() or s.get("ad", "?")
            r["birim"] = r.get("birim") or s.get("birim") or "Adet"
        out.append(r)
    return out


def _teklif_detay(conn, tid, sid=None):
    where, params = "t.id=?", [int(tid)]
    if sid is not None:
        where += " AND t.sirket_id=?"
        params.append(sid)
    t = conn.execute(
        "SELECT t.*, c.unvan AS cari_unvan, c.kod AS cari_kod, c.il AS cari_il, "
        "sb.ad AS sube_ad FROM teklif t JOIN cari_kart c ON c.id=t.cari_id "
        "LEFT JOIN sube sb ON sb.id=t.sube_id WHERE " + where, params
    ).fetchone()
    if not t:
        return None
    t = dict(t)
    kalemler = conn.execute(
        "SELECT k.*, COALESCE(st.kod,'') AS stok_kod, COALESCE(st.ad, k.aciklama) AS stok_ad, "
        "COALESCE(k.birim, st.birim, 'Adet') AS birim_goster, v.ad AS varyant_ad, "
        "COALESCE(k.goruntu_adi, st.ad, k.aciklama) AS gorunen_ad, "
        "CASE WHEN k.stok_id IS NULL THEN 1 ELSE 0 END AS manuel "
        "FROM teklif_kalem k LEFT JOIN stok_kart st ON st.id=k.stok_id "
        "LEFT JOIN stok_varyant v ON v.id=k.varyant_id "
        "WHERE k.teklif_id=? ORDER BY k.id", (t["id"],)
    ).fetchall()
    return t, kalemler


# --------------------------------------------------------------------------
# Rotalar
# --------------------------------------------------------------------------
@route(r"/teklif", roles=())
def teklif_liste(req):
    conn = db.get_conn()
    q = req.q("q").strip()
    durum = req.q("durum")
    where, params = ["t.sirket_id = ?"], [db.sirket_id(req)]
    if q:
        where.append("(t.teklif_no LIKE ? OR c.unvan LIKE ? OR c.kod LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like]
    if durum in DURUMLAR:
        where.append("t.durum=?")
        params.append(durum)
    if izole_sube(req):
        where.append("t.sube_id=?")
        params.append(izole_sube(req))
    w = " AND ".join(where)
    rows = conn.execute(
        f"SELECT t.*, c.unvan AS cari_unvan, c.kod AS cari_kod, "
        f"(SELECT COUNT(*) FROM teklif_kalem k WHERE k.teklif_id=t.id) AS kalem_sayisi "
        f"FROM teklif t JOIN cari_kart c ON c.id=t.cari_id WHERE {w} ORDER BY t.id DESC",
        params,
    ).fetchall()
    ozet = {d: conn.execute("SELECT COUNT(*) c FROM teklif WHERE durum=? AND sirket_id=?",
                             (d, db.sirket_id(req))).fetchone()["c"] for d in DURUMLAR}
    conn.close()
    return render_template("teklif/liste.html", rows=rows, durumlar=DURUMLAR, ozet=ozet,
                           filtro={"q": q, "durum": durum})


@route(r"/teklif/yeni", methods=("GET", "POST"), roles=TEKLIF_WRITE)
def teklif_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        return _form_post(req, conn, None)
    cariler = _cariler(conn, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, None)
    conn.close()
    return render_template("teklif/form.html", teklif=None, satirlar=[],
                           cariler=cariler, stoklar=stoklar, toplamlar=None,
                           cari_etiket=cari_etiket, cari_iskonto=cari_iskonto,
                           birimler=db.birimler(sid=db.sirket_id(req)), kdv_dahil=0,
                           bugun=datetime.date.today().isoformat())


@route(r"/teklif/(?P<tid>\d+)", roles=())
def teklif_detay(req, tid):
    conn = db.get_conn()
    sonuc = _teklif_detay(conn, tid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "Teklif bulunamadı.", "danger")
        return redirect("/teklif")
    t, kalemler = sonuc
    if not sube_koruma(req, t["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    loglar = conn.execute("SELECT * FROM audit_log WHERE tablo='teklif' AND kayit_id=? ORDER BY id DESC", (t["id"],)).fetchall()
    siparisler = conn.execute(
        "SELECT s.id, s.siparis_no, s.durum, s.tarih, s.genel_toplam FROM siparis s "
        "WHERE s.kaynak_teklif_id=? ORDER BY s.id", (t["id"],),
    ).fetchall()
    conn.close()
    return render_template("teklif/detay.html", teklif=t, kalemler=kalemler, loglar=loglar,
                           siparisler=siparisler, durumlar=DURUMLAR)


@route(r"/teklif/(?P<tid>\d+)/sil", methods=("POST",), roles=TEKLIF_WRITE)
def teklif_sil(req, tid):
    conn = db.get_conn()
    t = conn.execute("SELECT * FROM teklif WHERE id=? AND sirket_id=?",
                     (int(tid), db.sirket_id(req))).fetchone()
    if not t:
        conn.close()
        return redirect("/teklif")
    if not sube_koruma(req, t["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    if t["durum"] not in ("Taslak", "Reddedildi", "Süresi Doldu"):
        conn.close()
        flash(req, "Yalnızca Taslak / Reddedildi / Süresi Doldu teklifler silinebilir.", "danger")
        return redirect(f"/teklif/{t['id']}")
    if conn.execute("SELECT 1 FROM siparis WHERE kaynak_teklif_id=? LIMIT 1", (t["id"],)).fetchone():
        conn.close()
        flash(req, "Bu tekliften sipariş üretilmiş — silinemez.", "danger")
        return redirect(f"/teklif/{t['id']}")
    audit(req, "teklif", t["id"], "sil", {"teklif_no": t["teklif_no"], "durum": t["durum"]})
    db.bildirim_sil(conn, "teklif", t["id"])
    conn.execute("DELETE FROM teklif_kalem WHERE teklif_id=?", (t["id"],))
    conn.execute("DELETE FROM teklif WHERE id=?", (t["id"],))
    conn.commit()
    conn.close()
    flash(req, "Teklif silindi.", "ok")
    return redirect("/teklif")


@route(r"/teklif/(?P<tid>\d+)/duzenle", methods=("GET", "POST"), roles=TEKLIF_WRITE)
def teklif_duzenle(req, tid):
    conn = db.get_conn()
    t = conn.execute("SELECT * FROM teklif WHERE id=? AND sirket_id=?",
                     (int(tid), db.sirket_id(req))).fetchone()
    if not t:
        conn.close()
        return redirect("/teklif")
    if t["durum"] in ("Onaylandı", "Reddedildi"):
        conn.close()
        flash(req, "Onaylanmış veya reddedilmiş teklifler düzenlenemez.", "danger")
        return redirect(f"/teklif/{t['id']}")
    if req.method == "POST":
        return _form_post(req, conn, t)
    kalemler = conn.execute("SELECT * FROM teklif_kalem WHERE teklif_id=? ORDER BY id", (t["id"],)).fetchall()
    satirlar = [{"stok_id": k["stok_id"], "varyant_id": k["varyant_id"], "miktar": k["miktar"],
                 "birim_fiyat": k["birim_fiyat"], "iskonto_orani": k["iskonto_orani"],
                 "kdv_orani": k["kdv_orani"], "kdv_dahil": k["kdv_dahil"],
                 "birim": k["birim"], "goruntu_adi": k["goruntu_adi"],
                 "manuel_ad": (k["aciklama"] or "") if not k["stok_id"] else ""} for k in kalemler]
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(s) for s in satirlar])
    cariler = _cariler(conn, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, t["cari_id"])
    conn.close()
    return render_template("teklif/form.html", teklif=t, satirlar=satirlar,
                           cariler=cariler, stoklar=stoklar, toplamlar=toplamlar,
                           cari_etiket=cari_etiket, cari_iskonto=cari_iskonto,
                           birimler=db.birimler(sid=db.sirket_id(req)), kdv_dahil=(t["kdv_dahil"] or 0),
                           bugun=datetime.date.today().isoformat())


def _form_post(req, conn, mevcut):
    cari_id = _i(req.form.get("cari_id"))
    tarih = req.form.get("tarih") or datetime.date.today().isoformat()
    gecerlilik = req.form.get("gecerlilik_tarihi") or None
    aciklama = (req.form.get("aciklama") or "").strip()
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else 0
    satirlar = _satirlar_from_form(req, kdv_dahil)

    sil = req.form.get("sil")
    if sil is not None:
        idx = int(sil)
        if 0 <= idx < len(satirlar):
            del satirlar[idx]
        return _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet=False)

    action = req.form.get("action")
    if action == "ekle":
        sid = _i(req.form.get("stok_sec"))
        if sid:
            s = conn.execute("SELECT * FROM stok_kart WHERE id=? AND sirket_id=?",
                             (sid, db.sirket_id(req))).fetchone()
            if s:
                # K9 — iskonto varsayılan önceliği: stok özel > cari > 0
                if (s["iskonto_orani"] or 0) > 0:
                    isk = s["iskonto_orani"]
                else:
                    cari_isk = 0.0
                    if cari_id:
                        c = conn.execute("SELECT iskonto_orani FROM cari_kart WHERE id=? AND sirket_id=?",
                                         (cari_id, db.sirket_id(req))).fetchone()
                        cari_isk = c["iskonto_orani"] if c else 0.0
                    isk = cari_isk
                satirlar.append({"stok_id": sid, "miktar": 1, "birim_fiyat": s["satis_fiyat"],
                                 "iskonto_orani": isk, "kdv_orani": s["kdv_orani"]})
        return _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet=False)
    if action == "barkod":
        # D011-C — hızlı barkod: okut/yaz + Enter → satır otomatik eklenir.
        barkod = (req.form.get("barkod_sec") or "").strip()
        if barkod:
            sonuc = stok.barkod_bul(conn, barkod, db.sirket_id(req))
            if sonuc:
                kart = sonuc["kart"]
                isk = 0.0
                if (kart["iskonto_orani"] or 0) > 0:
                    isk = kart["iskonto_orani"]
                elif cari_id:
                    c = conn.execute("SELECT iskonto_orani FROM cari_kart WHERE id=? AND sirket_id=?",
                                     (cari_id, db.sirket_id(req))).fetchone()
                    isk = c["iskonto_orani"] if c else 0.0
                satirlar.append({"stok_id": sonuc["stok_id"], "varyant_id": sonuc["varyant_id"],
                                 "miktar": 1, "birim_fiyat": kart["satis_fiyat"],
                                 "iskonto_orani": isk, "kdv_orani": kart["kdv_orani"]})
            else:
                flash(req, f"Barkod bulunamadı: {barkod}", "danger")
        return _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet=False)

    # --- kaydet ---
    if not cari_id:
        flash(req, "Cari seçimi zorunludur.", "danger")
        return _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet=False)
    geçerli = [s for s in satirlar if (s["stok_id"] or s.get("manuel_ad")) and s["miktar"] > 0]
    if not geçerli:
        flash(req, "En az bir geçerli satır ekleyin.", "danger")
        return _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet=False)
    # İstek 3 — çapraz şirket hedef ID koruması
    if not conn.execute("SELECT id FROM cari_kart WHERE id=? AND sirket_id=?",
                        (cari_id, db.sirket_id(req))).fetchone():
        flash(req, "Geçersiz cari seçimi (başka şirkete ait).", "danger")
        return _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet=False)
    _sidler = {s["stok_id"] for s in geçerli if s["stok_id"]}
    if _sidler:
        _ph = ",".join("?" * len(_sidler))
        _izinli = {r["id"] for r in conn.execute(
            f"SELECT id FROM stok_kart WHERE id IN ({_ph}) AND sirket_id=?",
            tuple(_sidler) + (db.sirket_id(req),)).fetchall()}
        if _sidler - _izinli:
            flash(req, "Geçersiz stok seçimi (başka şirkete ait).", "danger")
            return _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet=False)
    top = _toplamlar(geçerli)

    islem = None
    if mevcut:
        conn.execute(
            "UPDATE teklif SET cari_id=?, tarih=?, gecerlilik_tarihi=?, aciklama=?, ara_toplam=?, "
            "iskonto_toplam=?, kdv_toplam=?, genel_toplam=?, kdv_dahil=?, "
            "updated_at=datetime('now','localtime') WHERE id=?",
            (cari_id, tarih, gecerlilik, aciklama, top["ara_toplam"], top["iskonto_toplam"],
             top["kdv_toplam"], top["genel_toplam"], kdv_dahil, mevcut["id"]),
        )
        conn.execute("DELETE FROM teklif_kalem WHERE teklif_id=?", (mevcut["id"],))
        tid = mevcut["id"]
        islem = ("guncelle", {"teklif_no": mevcut["teklif_no"]}, "Teklif güncellendi.")
    else:
        no = db.sonraki_belge_no(conn, "teklif", "teklif_no", "TKF", tarih[:4], db.sirket_id(req))
        cur = conn.execute(
            "INSERT INTO teklif(teklif_no, cari_id, tarih, gecerlilik_tarihi, durum, para_birimi, "
            "ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama, kdv_dahil, sube_id, created_by, sirket_id) "
            "VALUES(?,?,?,?,'Taslak','TRY',?,?,?,?,?,?,?,?,?)",
            (no, cari_id, tarih, gecerlilik, top["ara_toplam"], top["iskonto_toplam"],
             top["kdv_toplam"], top["genel_toplam"], aciklama, kdv_dahil, izole_sube(req), req.user["id"],
             db.sirket_id(req)),
        )
        tid = cur.lastrowid
        islem = ("olustur", {"teklif_no": no}, f"Teklif oluşturuldu: {no}")

    stok_birim = {}
    _stok_ids = {s["stok_id"] for s in geçerli if s["stok_id"]}
    if _stok_ids:
        _ph = ",".join("?" * len(_stok_ids))
        stok_birim = {r["id"]: r["birim"] for r in conn.execute(
            f"SELECT id, birim FROM stok_kart WHERE id IN ({_ph})", tuple(_stok_ids)).fetchall()}
    for s in geçerli:
        birim = s.get("birim") or None
        if not birim:
            birim = (stok_birim.get(s["stok_id"]) or "Adet") if s["stok_id"] else "Adet"
        goruntu = (s.get("goruntu_adi") or "").strip() or None
        conn.execute(
            "INSERT INTO teklif_kalem(teklif_id, stok_id, varyant_id, miktar, birim_fiyat, "
            "iskonto_orani, kdv_orani, kdv_dahil, tutar, aciklama, birim, goruntu_adi, sirket_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (tid, s["stok_id"], s["varyant_id"] or 0, s["miktar"], s["birim_fiyat"],
             s["iskonto_orani"], s["kdv_orani"], s.get("kdv_dahil"), s["tutar"],
             (s.get("manuel_ad") or "").strip() or None, birim, goruntu, db.sirket_id(req)),
        )
    conn.commit()
    audit(req, "teklif", tid, islem[0], islem[1])
    flash(req, islem[2], "ok")
    conn.close()
    return redirect(f"/teklif/{tid}")


def _form_render(req, conn, mevcut, satirlar, cari_id, tarih, gecerlilik, aciklama, flash_kaydet):
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(s) for s in satirlar])
    cariler = _cariler(conn, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, cari_id)
    teklif = dict(mevcut) if mevcut else {"cari_id": cari_id, "tarih": tarih,
                                          "gecerlilik_tarihi": gecerlilik, "aciklama": aciklama}
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else (0 if mevcut is None else (mevcut["kdv_dahil"] or 0))
    return render_template("teklif/form.html", teklif=teklif, satirlar=satirlar,
                           cariler=cariler, stoklar=stoklar, toplamlar=toplamlar,
                           cari_etiket=cari_etiket, cari_iskonto=cari_iskonto,
                           birimler=db.birimler(sid=db.sirket_id(req)), kdv_dahil=kdv_dahil,
                           bugun=datetime.date.today().isoformat())


@route(r"/teklif/(?P<tid>\d+)/durum", methods=("POST",), roles=TEKLIF_WRITE)
def teklif_durum(req, tid):
    durum = req.form.get("durum")
    if durum not in DURUMLAR:
        flash(req, "Geçersiz durum.", "danger")
        return redirect(f"/teklif/{tid}")
    conn = db.get_conn()
    t = conn.execute("SELECT * FROM teklif WHERE id=? AND sirket_id=?",
                     (int(tid), db.sirket_id(req))).fetchone()
    if not t:
        conn.close()
        return redirect("/teklif")
    conn.execute("UPDATE teklif SET durum=? WHERE id=?", (durum, int(tid)))
    conn.commit()
    audit(req, "teklif", int(tid), "durum", {"eski": t["durum"], "yeni": durum})
    conn.close()
    flash(req, f"Teklif durumu güncellendi: {durum}", "ok")
    return redirect(f"/teklif/{tid}")


@route(r"/teklif/(?P<tid>\d+)/yazdir", roles=())
def teklif_yazdir(req, tid):
    conn = db.get_conn()
    sonuc = _teklif_detay(conn, tid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "Teklif bulunamadı.", "danger")
        return redirect("/teklif")
    t, kalemler = sonuc
    conn.close()
    return render_template("teklif/yazdir.html", teklif=t, kalemler=kalemler)


def register():
    return "teklif"
