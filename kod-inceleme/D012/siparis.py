# -*- coding: utf-8 -*-
"""Sipariş modülü (Faz 2 — Satış Döngüsü, zincirin 2. halkası).

Belge zinciri: Teklif → Sipariş → İrsaliye → Fatura.
- tip: 'Musteri' = müşteriye satış siparişi, 'Alis' = tedarikçiye satın alma siparişi.
- Durum akışı (K10): Bekliyor → Onaylandı → (İrsaliye ile) Kısmi → Tamamlandı · İptal.
- Onay (Bekliyor→Onaylandı) yetki bazlıdır (Admin/Muhasebe); müşteri siparişi
  onaylanırken stok rezervasyonu yapılır (stok_seviye.rezerve artar), iptalde serbest
  bırakılır. Alış siparişi rezervasyon yapmaz (mal girişi İrsaliye/Fatura'da olur).
- K8: siparis.kaynak_teklif_id → teklif.id (nullable); onaylanan tekliften tek tıkla
  sipariş üretilebilir. K9: iskonto varsayılan önceliği stok özel > cari > 0.

Konvansiyon: siparis_kalem.tutar = satır net tutarı (KDV hariç).
"""
import datetime
import urllib.parse

import db
import stok
from core import route, render_template, redirect, flash, audit, notify, izole_sube, sube_koruma, Response, kdv_ayikla, yazdir_belge

SIPARIS_WRITE = ("Admin", "Muhasebe", "Satis")
SIPARIS_ONAY = ("Admin", "Muhasebe")
TIPLER = ["Musteri", "Alis"]
TIP_LABEL = {"Musteri": "Müşteri Siparişi", "Alis": "Satın Alma Siparişi"}
DURUMLAR = ["Bekliyor", "Onaylandı", "Kısmi", "Tamamlandı", "İptal"]
DURUM_BADGE = {
    "Bekliyor": "b-muted",
    "Onaylandı": "b-ok",
    "Kısmi": "b-info",
    "Tamamlandı": "b-ok",
    "İptal": "b-danger",
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


def _cariler(conn, tip, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    if tip == "Alis":
        return conn.execute(
            "SELECT id, unvan, kod, iskonto_orani FROM cari_kart "
            "WHERE aktif=1 AND tip IN ('Tedarikci','HerIkisi')" + extra + " ORDER BY unvan", args
        ).fetchall()
    return conn.execute(
        "SELECT id, unvan, kod, iskonto_orani FROM cari_kart "
        "WHERE aktif=1 AND tip IN ('Musteri','HerIkisi')" + extra + " ORDER BY unvan", args
    ).fetchall()


def _stoklar(conn, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    return conn.execute(
        "SELECT id, kod, ad, alis_fiyat, satis_fiyat, kdv_orani, iskonto_orani, birim "
        "FROM stok_kart WHERE aktif=1" + extra + " ORDER BY kod", args
    ).fetchall()


def _depolar(conn, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    return conn.execute("SELECT id, kod, ad FROM depo WHERE aktif=1" + extra + " ORDER BY kod",
                        args).fetchall()


def _iskonto_default(conn, stok_row, cari_id, sid=None):
    """K9 — iskonto varsayılan önceliği: stok özel > cari > 0."""
    if (stok_row["iskonto_orani"] or 0) > 0:
        return stok_row["iskonto_orani"]
    if cari_id:
        extra = " AND sirket_id=?" if sid is not None else ""
        args = [cari_id] + ([sid] if sid is not None else [])
        c = conn.execute("SELECT iskonto_orani FROM cari_kart WHERE id=?" + extra, args).fetchone()
        return (c["iskonto_orani"] if c else 0.0) or 0.0
    return 0.0


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


def _siparis_detay(conn, sid, sirket_id=None):
    where, params = "s.id=?", [int(sid)]
    if sirket_id is not None:
        where += " AND s.sirket_id=?"
        params.append(sirket_id)
    s = conn.execute(
        "SELECT s.*, c.unvan AS cari_unvan, c.kod AS cari_kod, c.il AS cari_il, "
        "d.kod AS depo_kod, d.ad AS depo_ad, sb.ad AS sube_ad, t.teklif_no AS kaynak_teklif_no "
        "FROM siparis s JOIN cari_kart c ON c.id=s.cari_id "
        "LEFT JOIN depo d ON d.id=s.depo_id LEFT JOIN sube sb ON sb.id=s.sube_id "
        "LEFT JOIN teklif t ON t.id=s.kaynak_teklif_id WHERE " + where, params
    ).fetchone()
    if not s:
        return None
    s = dict(s)
    kalemler = conn.execute(
        "SELECT k.*, COALESCE(st.kod,'') AS stok_kod, COALESCE(st.ad, k.aciklama) AS stok_ad, "
        "COALESCE(k.birim, st.birim, 'Adet') AS birim_goster, v.ad AS varyant_ad, "
        "COALESCE(k.goruntu_adi, st.ad, k.aciklama) AS gorunen_ad, "
        "CASE WHEN k.stok_id IS NULL THEN 1 ELSE 0 END AS manuel "
        "FROM siparis_kalem k LEFT JOIN stok_kart st ON st.id=k.stok_id "
        "LEFT JOIN stok_varyant v ON v.id=k.varyant_id "
        "WHERE k.siparis_id=? ORDER BY k.id", (s["id"],)
    ).fetchall()
    return s, kalemler


def _teklif_kaynak_kontrol(conn, kaynak_id, sid=None):
    """K10 — yalnız Onaylandı tekliften sipariş üretilebilir."""
    where, params = "id=?", [kaynak_id]
    if sid is not None:
        where += " AND sirket_id=?"
        params.append(sid)
    t = conn.execute(f"SELECT * FROM teklif WHERE {where}", params).fetchone()
    if not t:
        return "Kaynak teklif bulunamadı."
    if t["durum"] != "Onaylandı":
        return f"Yalnızca 'Onaylandı' durumundaki tekliften sipariş oluşturulabilir (teklif: {t['durum']})."
    return None


# --------------------------------------------------------------------------
# Rotalar
# --------------------------------------------------------------------------
@route(r"/siparis", roles=())
def siparis_liste(req):
    conn = db.get_conn()
    q = req.q("q").strip()
    durum = req.q("durum")
    tip = req.q("tip") if req.q("tip") in TIPLER else ""
    where, params = ["s.sirket_id = ?"], [db.sirket_id(req)]
    if q:
        where.append("(s.siparis_no LIKE ? OR c.unvan LIKE ? OR c.kod LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like]
    if durum in DURUMLAR:
        where.append("s.durum=?")
        params.append(durum)
    if tip:
        where.append("s.tip=?")
        params.append(tip)
    if izole_sube(req):
        where.append("s.sube_id=?")
        params.append(izole_sube(req))
    w = " AND ".join(where)
    rows = conn.execute(
        f"SELECT s.*, c.unvan AS cari_unvan, c.kod AS cari_kod, "
        f"(SELECT COUNT(*) FROM siparis_kalem k WHERE k.siparis_id=s.id) AS kalem_sayisi "
        f"FROM siparis s JOIN cari_kart c ON c.id=s.cari_id WHERE {w} ORDER BY s.id DESC",
        params,
    ).fetchall()
    ozet = {d: conn.execute("SELECT COUNT(*) c FROM siparis WHERE durum=? AND sirket_id=?",
                             (d, db.sirket_id(req))).fetchone()["c"]
            for d in DURUMLAR}
    conn.close()
    return render_template("siparis/liste.html", rows=rows, durumlar=DURUMLAR, tipler=TIPLER,
                           tip_label=TIP_LABEL, ozet=ozet, filtro={"q": q, "durum": durum, "tip": tip})


@route(r"/siparis/yeni", methods=("GET", "POST"), roles=SIPARIS_WRITE)
def siparis_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        return _form_post(req, conn, None)

    kaynak = _i(req.q("kaynak_teklif"))
    satirlar, kaynak_teklif_id, onceki_siparisler = [], None, []
    teklif = None
    if kaynak:
        hata = _teklif_kaynak_kontrol(conn, kaynak, db.sirket_id(req))
        if hata:
            conn.close()
            flash(req, hata, "danger")
            return redirect(f"/teklif/{kaynak}")
        teklif = dict(conn.execute("SELECT * FROM teklif WHERE id=? AND sirket_id=?",
                                   (kaynak, db.sirket_id(req))).fetchone())
        kaynak_teklif_id = kaynak
        kalemler = conn.execute(
            "SELECT * FROM teklif_kalem WHERE teklif_id=? ORDER BY id", (kaynak,)
        ).fetchall()
        satirlar = [{"stok_id": k["stok_id"], "varyant_id": k["varyant_id"], "miktar": k["miktar"],
                     "birim_fiyat": k["birim_fiyat"], "iskonto_orani": k["iskonto_orani"],
                     "kdv_orani": k["kdv_orani"], "birim": k["birim"], "goruntu_adi": k["goruntu_adi"],
                     "manuel_ad": (k["aciklama"] or "") if not k["stok_id"] else ""} for k in kalemler]
        # K12 — bu tekliften daha önce oluşturulan siparişler (bilgilendirme amaçlı)
        onceki_siparisler = conn.execute(
            "SELECT siparis_no, durum FROM siparis WHERE kaynak_teklif_id=? ORDER BY id", (kaynak,)
        ).fetchall()

    cariler = _cariler(conn, "Musteri", db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    depolar = _depolar(conn, db.sirket_id(req))
    ilk_depo = depolar[0]["id"] if depolar else None
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(x) for x in satirlar]) if satirlar else None
    cari_etiket, cari_iskonto = _cari_secim(cariler, teklif["cari_id"] if teklif else None)
    conn.close()
    return render_template(
        "siparis/form.html", siparis=None, satirlar=satirlar,
        cariler=cariler, stoklar=stoklar, depolar=depolar, toplamlar=toplamlar,
        tip="Musteri", depo_id=ilk_depo, kaynak_teklif_id=kaynak_teklif_id,
        kaynak_teklif=teklif, onceki_siparisler=onceki_siparisler,
        cari_etiket=cari_etiket, cari_iskonto=cari_iskonto, birimler=db.birimler(sid=db.sirket_id(req)),
        kdv_dahil=0, bugun=datetime.date.today().isoformat())


@route(r"/siparis/(?P<sid>\d+)", roles=())
def siparis_detay(req, sid):
    conn = db.get_conn()
    sonuc = _siparis_detay(conn, sid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "Sipariş bulunamadı.", "danger")
        return redirect("/siparis")
    s, kalemler = sonuc
    if not sube_koruma(req, s["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    kalemler = [dict(k) for k in kalemler]
    if s["tip"] == "Musteri" and s["depo_id"]:
        for k in kalemler:
            if not k["stok_id"]:  # manuel satır stoğa dokunmaz (K33) — eldeki/rezerve gösterilmez
                continue
            sev = conn.execute(
                "SELECT miktar, rezerve FROM stok_seviye WHERE stok_id=? AND varyant_id=0 AND depo_id=?",
                (k["stok_id"], s["depo_id"]),
            ).fetchone()
            k["eldeki"] = (sev["miktar"] or 0) if sev else 0
            k["rezerve"] = (sev["rezerve"] or 0) if sev else 0
    loglar = conn.execute("SELECT * FROM audit_log WHERE tablo='siparis' AND kayit_id=? ORDER BY id DESC",
                          (s["id"],)).fetchall()
    irsaliyeler = conn.execute(
        "SELECT i.id, i.irsaliye_no, i.durum, i.tarih, i.genel_toplam FROM irsaliye i "
        "WHERE i.kaynak_siparis_id=? ORDER BY i.id", (s["id"],),
    ).fetchall()
    conn.close()
    return render_template("siparis/detay.html", siparis=s, kalemler=kalemler, loglar=loglar,
                           irsaliyeler=irsaliyeler, tip_label=TIP_LABEL)


@route(r"/siparis/(?P<sid>\d+)/duzenle", methods=("GET", "POST"), roles=SIPARIS_WRITE)
def siparis_duzenle(req, sid):
    conn = db.get_conn()
    s = conn.execute("SELECT * FROM siparis WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/siparis")
    if s["durum"] != "Bekliyor":
        conn.close()
        flash(req, "Yalnızca 'Bekliyor' durumundaki siparişler düzenlenebilir.", "danger")
        return redirect(f"/siparis/{s['id']}")
    if req.method == "POST":
        return _form_post(req, conn, s)

    kalemler = conn.execute("SELECT * FROM siparis_kalem WHERE siparis_id=? ORDER BY id",
                            (s["id"],)).fetchall()
    satirlar = [{"stok_id": k["stok_id"], "varyant_id": k["varyant_id"], "miktar": k["miktar"],
                 "birim_fiyat": k["birim_fiyat"], "iskonto_orani": k["iskonto_orani"],
                 "kdv_orani": k["kdv_orani"], "kdv_dahil": k["kdv_dahil"],
                 "birim": k["birim"], "goruntu_adi": k["goruntu_adi"],
                 "manuel_ad": (k["aciklama"] or "") if not k["stok_id"] else ""} for k in kalemler]
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(x) for x in satirlar])
    cariler = _cariler(conn, s["tip"], db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    depolar = _depolar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, s["cari_id"])
    conn.close()
    return render_template("siparis/form.html", siparis=s, satirlar=satirlar,
                           cariler=cariler, stoklar=stoklar, depolar=depolar, toplamlar=toplamlar,
                           tip=s["tip"], depo_id=s["depo_id"], kaynak_teklif_id=s["kaynak_teklif_id"],
                           kaynak_teklif=None, cari_etiket=cari_etiket, cari_iskonto=cari_iskonto,
                           birimler=db.birimler(sid=db.sirket_id(req)), kdv_dahil=(s["kdv_dahil"] or 0),
                           bugun=datetime.date.today().isoformat())


@route(r"/siparis/(?P<sid>\d+)/sil", methods=("POST",), roles=SIPARIS_WRITE)
def siparis_sil(req, sid):
    conn = db.get_conn()
    s = conn.execute("SELECT * FROM siparis WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/siparis")
    if not sube_koruma(req, s["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    if s["durum"] != "Bekliyor":
        conn.close()
        flash(req, "Yalnızca 'Bekliyor' durumundaki siparişler silinebilir.", "danger")
        return redirect(f"/siparis/{s['id']}")
    if conn.execute("SELECT 1 FROM irsaliye WHERE kaynak_siparis_id=? LIMIT 1", (s["id"],)).fetchone():
        conn.close()
        flash(req, "Bu siparişten irsaliye üretilmiş — silinemez.", "danger")
        return redirect(f"/siparis/{s['id']}")
    audit(req, "siparis", s["id"], "sil", {"siparis_no": s["siparis_no"]})
    db.bildirim_sil(conn, "siparis", s["id"])
    conn.execute("DELETE FROM siparis_kalem WHERE siparis_id=?", (s["id"],))
    conn.execute("DELETE FROM siparis WHERE id=?", (s["id"],))
    conn.commit()
    conn.close()
    flash(req, "Sipariş silindi.", "ok")
    return redirect("/siparis")


def _form_post(req, conn, mevcut):
    tip = req.form.get("tip") if req.form.get("tip") in TIPLER else "Musteri"
    cari_id = _i(req.form.get("cari_id"))
    depo_id = _i(req.form.get("depo_id"))
    tarih = req.form.get("tarih") or datetime.date.today().isoformat()
    teslim = req.form.get("teslim_tarihi") or None
    aciklama = (req.form.get("aciklama") or "").strip()
    kaynak_teklif_id = _i(req.form.get("kaynak_teklif"))
    if mevcut:
        kaynak_teklif_id = mevcut["kaynak_teklif_id"]  # düzenlemede kaynak değişmez
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else 0
    satirlar = _satirlar_from_form(req, kdv_dahil)

    sil = req.form.get("sil")
    if sil is not None:
        idx = int(sil)
        if 0 <= idx < len(satirlar):
            del satirlar[idx]
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)

    if req.form.get("tip_degistir"):
        # tip değişince cari listesi yeniden filtrelenir (kayıt yapılmaz)
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)

    action = req.form.get("action")
    if action == "ekle":
        sid = _i(req.form.get("stok_sec"))
        if sid:
            s = conn.execute("SELECT * FROM stok_kart WHERE id=? AND sirket_id=?",
                             (sid, db.sirket_id(req))).fetchone()
            if s:
                bf = s["alis_fiyat"] if tip == "Alis" else s["satis_fiyat"]
                isk = _iskonto_default(conn, s, cari_id, db.sirket_id(req))
                satirlar.append({"stok_id": sid, "miktar": 1, "birim_fiyat": bf,
                                 "iskonto_orani": isk, "kdv_orani": s["kdv_orani"]})
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)

    # --- kaydet ---
    if not cari_id:
        flash(req, "Cari seçimi zorunludur.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)
    if tip == "Musteri" and not depo_id:
        flash(req, "Müşteri siparişi için depo seçimi zorunludur.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)
    if kaynak_teklif_id:
        hata = _teklif_kaynak_kontrol(conn, kaynak_teklif_id, db.sirket_id(req))
        if hata:
            flash(req, hata, "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                                aciklama, kaynak_teklif_id)
    gecerli = [s for s in satirlar if (s["stok_id"] or s.get("manuel_ad")) and s["miktar"] > 0]
    if not gecerli:
        flash(req, "En az bir geçerli satır ekleyin.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)
    # İstek 3 — çapraz şirket hedef ID koruması
    if not conn.execute("SELECT id FROM cari_kart WHERE id=? AND sirket_id=?",
                        (cari_id, db.sirket_id(req))).fetchone():
        flash(req, "Geçersiz cari seçimi (başka şirkete ait).", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)
    if depo_id and not conn.execute("SELECT id FROM depo WHERE id=? AND sirket_id=?",
                                    (depo_id, db.sirket_id(req))).fetchone():
        flash(req, "Geçersiz depo seçimi (başka şirkete ait).", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                            aciklama, kaynak_teklif_id)
    _sidler = {s["stok_id"] for s in gecerli if s["stok_id"]}
    if _sidler:
        _ph = ",".join("?" * len(_sidler))
        _izinli = {r["id"] for r in conn.execute(
            f"SELECT id FROM stok_kart WHERE id IN ({_ph}) AND sirket_id=?",
            tuple(_sidler) + (db.sirket_id(req),)).fetchall()}
        if _sidler - _izinli:
            flash(req, "Geçersiz stok seçimi (başka şirkete ait).", "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                                aciklama, kaynak_teklif_id)
    top = _toplamlar(gecerli)

    islem = None
    if mevcut:
        conn.execute(
            "UPDATE siparis SET tip=?, cari_id=?, depo_id=?, tarih=?, teslim_tarihi=?, aciklama=?, "
            "ara_toplam=?, iskonto_toplam=?, kdv_toplam=?, genel_toplam=?, kdv_dahil=?, "
            "updated_at=datetime('now','localtime') WHERE id=?",
            (tip, cari_id, depo_id if tip == "Musteri" else None, tarih, teslim, aciklama,
             top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"], top["genel_toplam"],
             kdv_dahil, mevcut["id"]),
        )
        conn.execute("DELETE FROM siparis_kalem WHERE siparis_id=?", (mevcut["id"],))
        sid = mevcut["id"]
        islem = ("guncelle", {"siparis_no": mevcut["siparis_no"]}, "Sipariş güncellendi.")
    else:
        on_ek = "SIP" if tip == "Musteri" else "SAP"
        no = db.sonraki_belge_no(conn, "siparis", "siparis_no", on_ek, tarih[:4], db.sirket_id(req))
        cur = conn.execute(
            "INSERT INTO siparis(siparis_no, tip, cari_id, depo_id, kaynak_teklif_id, tarih, "
            "teslim_tarihi, durum, para_birimi, ara_toplam, iskonto_toplam, kdv_toplam, "
            "genel_toplam, aciklama, kdv_dahil, sube_id, created_by, sirket_id) "
            "VALUES(?,?,?,?,?,?,?,'Bekliyor','TRY',?,?,?,?,?,?,?,?,?)",
            (no, tip, cari_id, depo_id if tip == "Musteri" else None, kaynak_teklif_id, tarih,
             teslim, top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"],
             top["genel_toplam"], aciklama, kdv_dahil, izole_sube(req), req.user["id"], db.sirket_id(req)),
        )
        sid = cur.lastrowid
        islem = ("olustur", {"siparis_no": no}, f"Sipariş oluşturuldu: {no}")

    stok_birim = {}
    _stok_ids = {s["stok_id"] for s in gecerli if s["stok_id"]}
    if _stok_ids:
        _ph = ",".join("?" * len(_stok_ids))
        stok_birim = {r["id"]: r["birim"] for r in conn.execute(
            f"SELECT id, birim FROM stok_kart WHERE id IN ({_ph})", tuple(_stok_ids)).fetchall()}
    for s in gecerli:
        birim = s.get("birim") or None
        if not birim:
            birim = (stok_birim.get(s["stok_id"]) or "Adet") if s["stok_id"] else "Adet"
        goruntu = (s.get("goruntu_adi") or "").strip() or None
        conn.execute(
            "INSERT INTO siparis_kalem(siparis_id, stok_id, varyant_id, miktar, teslim_edilen, "
            "birim_fiyat, iskonto_orani, kdv_orani, kdv_dahil, tutar, aciklama, birim, goruntu_adi, sirket_id) "
            "VALUES(?,?,?,?,0,?,?,?,?,?,?,?,?,?)",
            (sid, s["stok_id"], s["varyant_id"] or 0, s["miktar"], s["birim_fiyat"],
             s["iskonto_orani"], s["kdv_orani"], s.get("kdv_dahil"), s["tutar"],
             (s.get("manuel_ad") or "").strip() or None, birim, goruntu, db.sirket_id(req)),
        )
    conn.commit()
    audit(req, "siparis", sid, islem[0], islem[1])
    flash(req, islem[2], "ok")
    conn.close()
    return redirect(f"/siparis/{sid}")


def _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, tarih, teslim,
                 aciklama, kaynak_teklif_id):
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(s) for s in satirlar])
    cariler = _cariler(conn, tip, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    depolar = _depolar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, cari_id)
    siparis = dict(mevcut) if mevcut else {"tip": tip, "cari_id": cari_id, "depo_id": depo_id,
                                           "tarih": tarih, "teslim_tarihi": teslim,
                                           "aciklama": aciklama}
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else (0 if mevcut is None else (mevcut["kdv_dahil"] or 0))
    return render_template("siparis/form.html", siparis=siparis, satirlar=satirlar,
                           cariler=cariler, stoklar=stoklar, depolar=depolar, toplamlar=toplamlar,
                           tip=tip, depo_id=depo_id, kaynak_teklif_id=kaynak_teklif_id,
                           kaynak_teklif=None, cari_etiket=cari_etiket, cari_iskonto=cari_iskonto,
                           birimler=db.birimler(sid=db.sirket_id(req)), kdv_dahil=kdv_dahil,
                           bugun=datetime.date.today().isoformat())


@route(r"/siparis/(?P<sid>\d+)/durum", methods=("POST",), roles=SIPARIS_ONAY)
def siparis_durum(req, sid):
    durum = req.form.get("durum")
    if durum not in ("Onaylandı", "İptal"):
        flash(req, "Geçersiz durum geçişi.", "danger")
        return redirect(f"/siparis/{sid}")
    conn = db.get_conn()
    s = conn.execute("SELECT * FROM siparis WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/siparis")

    kalemler = conn.execute("SELECT * FROM siparis_kalem WHERE siparis_id=?", (int(sid),)).fetchall()

    if durum == "Onaylandı":
        if s["durum"] != "Bekliyor":
            conn.close()
            flash(req, "Yalnızca 'Bekliyor' durumundaki siparişler onaylanabilir.", "danger")
            return redirect(f"/siparis/{sid}")
        # Müşteri siparişi → stok yeterliliği kontrolü + rezervasyon (K11)
        # Manuel (serbest metin) satırlar stoğa dokunmaz — K11 kontrolüne girmez (İrsaliye ayrımı).
        if s["tip"] == "Musteri":
            yetersiz = []
            for k in kalemler:
                if not k["stok_id"]:
                    continue
                sev = conn.execute(
                    "SELECT miktar, rezerve FROM stok_seviye WHERE stok_id=? AND varyant_id=0 AND depo_id=?",
                    (k["stok_id"], s["depo_id"]),
                ).fetchone()
                eldeki = ((sev["miktar"] or 0) - (sev["rezerve"] or 0)) if sev else 0
                if eldeki < k["miktar"]:
                    st = conn.execute("SELECT kod, ad FROM stok_kart WHERE id=?", (k["stok_id"],)).fetchone()
                    yetersiz.append(f"{st['kod']} {st['ad']} (eldeki: {eldeki:g}, istenen: {k['miktar']:g})")
            if yetersiz:
                conn.close()
                flash(req, "Stok yetersiz, onaylanamadı: " + " · ".join(yetersiz), "danger")
                return redirect(f"/siparis/{sid}")
            for k in kalemler:
                if not k["stok_id"]:
                    continue
                conn.execute(
                    "UPDATE stok_seviye SET rezerve = rezerve + ? WHERE stok_id=? AND varyant_id=0 AND depo_id=?",
                    (k["miktar"], k["stok_id"], s["depo_id"]),
                )
        conn.execute("UPDATE siparis SET durum='Onaylandı' WHERE id=?", (int(sid),))
        conn.commit()
        audit(req, "siparis", int(sid), "durum", {"eski": s["durum"], "yeni": "Onaylandı"})
        if s["tip"] == "Musteri":
            notify("bilgi", "Sipariş onaylandı",
                   f"{s['siparis_no']} onaylandı; stok rezervasyonu yapıldı.", "siparis", int(sid), sirket_id=db.sirket_id(req))
        conn.close()
        flash(req, "Sipariş onaylandı (rezervasyon yapıldı).", "ok")
        return redirect(f"/siparis/{sid}")

    # --- İptal ---
    if s["durum"] not in ("Bekliyor", "Onaylandı"):
        conn.close()
        flash(req, "Bu durumdaki sipariş iptal edilemez.", "danger")
        return redirect(f"/siparis/{sid}")
    if s["durum"] == "Onaylandı" and s["tip"] == "Musteri":
        for k in kalemler:
            if not k["stok_id"]:  # manuel satır rezerve edilmemişti (K33)
                continue
            conn.execute(
                "UPDATE stok_seviye SET rezerve = MAX(rezerve - ?, 0) "
                "WHERE stok_id=? AND varyant_id=0 AND depo_id=?",
                (k["miktar"], k["stok_id"], s["depo_id"]),
            )
    conn.execute("UPDATE siparis SET durum='İptal' WHERE id=?", (int(sid),))
    conn.commit()
    audit(req, "siparis", int(sid), "durum", {"eski": s["durum"], "yeni": "İptal"})
    conn.close()
    flash(req, "Sipariş iptal edildi (rezervasyon serbest bırakıldı).", "ok")
    return redirect(f"/siparis/{sid}")


@route(r"/siparis/(?P<sid>\d+)/yazdir", roles=())
def siparis_yazdir(req, sid):
    conn = db.get_conn()
    sonuc = _siparis_detay(conn, sid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "Sipariş bulunamadı.", "danger")
        return redirect("/siparis")
    s, kalemler = sonuc
    # F6 — şube izolasyonu: başka şubeye ait belge yazdırılamaz.
    if not sube_koruma(req, s["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    belge = yazdir_belge(s, kalemler, "siparis_no", TIP_LABEL[s["tip"]])
    conn.close()
    return render_template("yazdir/belge.html", belge=belge)


def register():
    return "siparis"
