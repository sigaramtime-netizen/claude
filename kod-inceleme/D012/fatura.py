# -*- coding: utf-8 -*-
"""Fatura modülü (Faz 2 — Satış Döngüsü, zincirin 4. halkası).

Belge zinciri: Teklif → Sipariş → İrsaliye → Fatura.
- tip: 'Satis' = müşteriye satış faturası, 'Alis' = tedarikçiden alış faturası.
- K8: fatura.kaynak_irsaliye_id → irsaliye.id (nullable); onaylı irsaliyeden tek tıkla üretim.
- K10: yalnız 'Onaylandı' irsaliyeden fatura üretilebilir (Transfer irsaliyeden üretilemez).
- K2/K6: fatura onayı → cari_hareket (mali etki burada oluşur):
    Satış → müşteri BORÇ (bakiye +), Alış → tedarikçi ALACAK (bakiye −).
- Stok etkisi İrsaliye'de tamamlandı; fatura stok'a dokunmaz.
- İptal (onaylıyken) faturanın cari hareketini geri alır (K6 tek kaynak: fatura).
- K14: irsaliyenin 'faturalandı' bilgisi fatura tablosundan türetilir (irsaliye tarafında).
"""
import datetime
import urllib.parse

import db
import cari
import stok
import ekler
import muhasebe
from core import route, render_template, redirect, flash, audit, notify, izole_sube, sube_koruma, Response, kdv_ayikla, yazdir_belge
from config import PARA_BIRIMLERI

FATURA_WRITE = ("Admin", "Muhasebe", "Satis")
FATURA_ONAY = ("Admin", "Muhasebe")
TIPLER = ["Satis", "Alis"]
TIP_LABEL = {"Satis": "Satış Faturası", "Alis": "Alış Faturası"}
TIP_ON_EK = {"Satis": "SF", "Alis": "AF"}
DURUMLAR = ["Taslak", "Onaylandı", "İptal"]
DURUM_BADGE = {"Taslak": "b-muted", "Onaylandı": "b-ok", "İptal": "b-danger"}


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
        "SELECT id, kod, ad, alis_fiyat, satis_fiyat, kdv_orani, iskonto_orani "
        "FROM stok_kart WHERE aktif=1" + extra + " ORDER BY kod", args
    ).fetchall()


def _iskonto_default(conn, stok_row, cari_id):
    """K9 — iskonto varsayılan önceliği: stok özel > cari > 0."""
    if (stok_row["iskonto_orani"] or 0) > 0:
        return stok_row["iskonto_orani"]
    if cari_id:
        c = conn.execute("SELECT iskonto_orani FROM cari_kart WHERE id=?", (cari_id,)).fetchone()
        return (c["iskonto_orani"] if c else 0.0) or 0.0
    return 0.0


def _cari_secim(cariler, cari_id):
    """Seçili cari için görünür etiket (unvan + kod) ve iskonto oranı (K9 için)."""
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
            r["varyant_ad"] = ""
        else:
            r["stok_kod"] = s.get("kod", "?")
            r["stok_ad"] = s.get("ad", "?")
            # goruntu_adi boşsa gerçek stok adı; doldurulursa YALNIZCA belgede gösterilecek ad.
            r["gorunen_ad"] = (r.get("goruntu_adi") or "").strip() or s.get("ad", "?")
            r["birim"] = r.get("birim") or s.get("birim") or "Adet"
            r["varyant_ad"] = ""
            if r.get("varyant_id"):
                v = conn.execute("SELECT ad FROM stok_varyant WHERE id=?", (r["varyant_id"],)).fetchone()
                r["varyant_ad"] = v["ad"] if v else ""
        out.append(r)
    return out


def _fatura_detay(conn, fid, sid=None):
    where, params = "f.id=?", [int(fid)]
    if sid is not None:
        where += " AND f.sirket_id=?"
        params.append(sid)
    r = conn.execute(
        "SELECT f.*, c.unvan AS cari_unvan, c.kod AS cari_kod, c.il AS cari_il, "
        "sb.ad AS sube_ad, i.irsaliye_no AS kaynak_irsaliye_no, i.id AS kaynak_irsaliye_id, "
        "sv.servis_no AS kaynak_servis_no, sv.id AS kaynak_servis_id "
        "FROM fatura f LEFT JOIN cari_kart c ON c.id=f.cari_id "
        "LEFT JOIN sube sb ON sb.id=f.sube_id LEFT JOIN irsaliye i ON i.id=f.kaynak_irsaliye_id "
        "LEFT JOIN servis_kayit sv ON sv.id=f.kaynak_servis_id "
        "WHERE " + where, params,
    ).fetchone()
    if not r:
        return None
    r = dict(r)
    kalemler = conn.execute(
        "SELECT k.*, COALESCE(st.kod,'') AS stok_kod, COALESCE(st.ad, k.aciklama) AS stok_ad, "
        "COALESCE(k.birim, st.birim, 'Adet') AS birim_goster, v.ad AS varyant_ad, "
        "COALESCE(k.goruntu_adi, st.ad, k.aciklama) AS gorunen_ad, "
        "CASE WHEN k.stok_id IS NULL THEN 1 ELSE 0 END AS manuel "
        "FROM fatura_kalem k LEFT JOIN stok_kart st ON st.id=k.stok_id "
        "LEFT JOIN stok_varyant v ON v.id=k.varyant_id WHERE k.fatura_id=? ORDER BY k.id",
        (r["id"],),
    ).fetchall()
    return r, kalemler


def _irsaliye_kontrol(conn, irsaliye_id, sid=None):
    """K10 — yalnız Onaylandı irsaliyeden fatura üretilebilir; Transfer faturaya dönüşmez."""
    where, params = "id=?", [irsaliye_id]
    if sid is not None:
        where += " AND sirket_id=?"
        params.append(sid)
    i = conn.execute(f"SELECT * FROM irsaliye WHERE {where}", params).fetchone()
    if not i:
        return "Kaynak irsaliye bulunamadı."
    if i["tip"] == "Transfer":
        return "Transfer irsaliyesinden fatura üretilemez (cari yok)."
    if i["durum"] != "Onaylandı":
        return f"Yalnızca 'Onaylandı' durumundaki irsaliyeden fatura üretilebilir (irsaliye: {i['durum']})."
    return None


def _cari_uygula(conn, req, fatura, yon):
    """K2/K6 — fatura onayı/iptali için cari hareketi tek işlemde yaz/geri al.

    yon=+1 → hareket oluştur (Satış→BORÇ, Alış→ALACAK); yon=-1 → faturanın kendi
    cari hareketini sil (belge iptal → mali etki net sıfır).
    """
    if yon == -1:
        conn.execute(
            "DELETE FROM cari_hareket WHERE ilgili_modul='Fatura' AND ilgili_kayit_id=?",
            (fatura["id"],),
        )
        return
    pb = fatura.get("para_birimi") or "TRY"
    kur = fatura.get("doviz_kur") or 1.0
    tutar_tl = round((fatura["genel_toplam"] or 0.0) * kur, 2)   # K18: cariye TL karşılığı
    if fatura["tip"] == "Satis":
        cari.hareket_ekle(conn, fatura["cari_id"], fatura["tarih"], "Satış Faturası",
                          fatura["fatura_no"], fatura.get("aciklama"),
                          borc=tutar_tl, alacak=0.0,
                          ilgili_modul="Fatura", ilgili_kayit_id=fatura["id"],
                          vade=fatura.get("vade"), created_by=req.user["id"],
                          para_birimi=pb, doviz_kur=kur)
    else:
        cari.hareket_ekle(conn, fatura["cari_id"], fatura["tarih"], "Alış Faturası",
                          fatura["fatura_no"], fatura.get("aciklama"),
                          borc=0.0, alacak=tutar_tl,
                          ilgili_modul="Fatura", ilgili_kayit_id=fatura["id"],
                          vade=fatura.get("vade"), created_by=req.user["id"],
                          para_birimi=pb, doviz_kur=kur)


def _bagli_tahsilat_var(conn, fid):
    """K15 — faturaya bağlı (Kasa/Banka) tahsilat/ödeme hareketi var mı?"""
    return conn.execute(
        "SELECT (SELECT COUNT(*) FROM kasa_hareket WHERE ilgili_modul='Fatura' AND ilgili_kayit_id=?) "
        "+ (SELECT COUNT(*) FROM banka_hareket WHERE ilgili_modul='Fatura' AND ilgili_kayit_id=?) AS c",
        (fid, fid),
    ).fetchone()["c"]


def _odeme_durumu(conn, fid):
    """K15 — faturaya bağlı Kasa/Banka tahsilat/ödeme toplamları."""
    ks = conn.execute("SELECT islem_tipi, tutar FROM kasa_hareket WHERE ilgili_modul='Fatura' "
                      "AND ilgili_kayit_id=?", (fid,)).fetchall()
    bs = conn.execute("SELECT islem_tipi, tutar FROM banka_hareket WHERE ilgili_modul='Fatura' "
                      "AND ilgili_kayit_id=?", (fid,)).fetchall()
    giris = sum((r["tutar"] or 0) for r in ks if r["islem_tipi"] == "Nakit Girişi")
    giris += sum((r["tutar"] or 0) for r in bs if r["islem_tipi"] == "Havale/EFT Girişi")
    cikis = sum((r["tutar"] or 0) for r in ks if r["islem_tipi"] == "Nakit Çıkışı")
    cikis += sum((r["tutar"] or 0) for r in bs if r["islem_tipi"] == "Havale/EFT Çıkışı")
    return {"giris": round(giris, 2), "cikis": round(cikis, 2), "adet": len(ks) + len(bs)}


# --------------------------------------------------------------------------
# Rotalar
# --------------------------------------------------------------------------
@route(r"/fatura", roles=())
def fatura_liste(req):
    conn = db.get_conn()
    q = req.q("q").strip()
    durum = req.q("durum")
    tip = req.q("tip") if req.q("tip") in TIPLER else ""
    where, params = ["f.sirket_id = ?"], [db.sirket_id(req)]
    if q:
        where.append("(f.fatura_no LIKE ? OR c.unvan LIKE ? OR c.kod LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like]
    if durum in DURUMLAR:
        where.append("f.durum=?")
        params.append(durum)
    if tip:
        where.append("f.tip=?")
        params.append(tip)
    if izole_sube(req):
        where.append("f.sube_id=?")
        params.append(izole_sube(req))
    w = " AND ".join(where)
    rows = conn.execute(
        f"SELECT f.*, c.unvan AS cari_unvan, c.kod AS cari_kod, "
        f"(SELECT COUNT(*) FROM fatura_kalem k WHERE k.fatura_id=f.id) AS kalem_sayisi "
        f"FROM fatura f LEFT JOIN cari_kart c ON c.id=f.cari_id WHERE {w} ORDER BY f.id DESC",
        params,
    ).fetchall()
    ozet = {d: conn.execute("SELECT COUNT(*) c FROM fatura WHERE durum=? AND sirket_id=?",
                             (d, db.sirket_id(req))).fetchone()["c"]
            for d in DURUMLAR}
    conn.close()
    return render_template("fatura/liste.html", rows=rows, durumlar=DURUMLAR, tipler=TIPLER,
                           tip_label=TIP_LABEL, ozet=ozet, filtro={"q": q, "durum": durum, "tip": tip})


@route(r"/fatura/yeni", methods=("GET", "POST"), roles=FATURA_WRITE)
def fatura_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        return _form_post(req, conn, None)

    kaynak = _i(req.q("kaynak_irsaliye"))
    satirlar, kaynak_irsaliye_id = [], None
    irsaliye_row = None
    tip = "Satis"
    cari_id = None
    if kaynak:
        hata = _irsaliye_kontrol(conn, kaynak, db.sirket_id(req))
        if hata:
            conn.close()
            flash(req, hata, "danger")
            return redirect(f"/irsaliye/{kaynak}")
        irsaliye_row = dict(conn.execute("SELECT * FROM irsaliye WHERE id=? AND sirket_id=?",
                                         (kaynak, db.sirket_id(req))).fetchone())
        kaynak_irsaliye_id = kaynak
        tip = "Satis" if irsaliye_row["tip"] == "Satis" else "Alis"
        cari_id = irsaliye_row["cari_id"]
        kalemler = conn.execute(
            "SELECT * FROM irsaliye_kalem WHERE irsaliye_id=? ORDER BY id", (kaynak,),
        ).fetchall()
        satirlar = [{"stok_id": k["stok_id"], "varyant_id": k["varyant_id"], "miktar": k["miktar"],
                     "birim_fiyat": k["birim_fiyat"], "iskonto_orani": k["iskonto_orani"],
                     "kdv_orani": k["kdv_orani"], "birim": k["birim"], "goruntu_adi": k["goruntu_adi"],
                     "manuel_ad": (k["aciklama"] or "") if not k["stok_id"] else ""}
                    for k in kalemler]

    cariler = _cariler(conn, tip, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(x) for x in satirlar]) if satirlar else None
    cari_etiket, cari_iskonto = _cari_secim(cariler, cari_id)
    conn.close()
    return render_template(
        "fatura/form.html", fatura=None, satirlar=satirlar, cariler=cariler, stoklar=stoklar,
        toplamlar=toplamlar, tip=tip, cari_id=cari_id, cari_etiket=cari_etiket,
        cari_iskonto=cari_iskonto, kaynak_irsaliye_id=kaynak_irsaliye_id,
        kaynak_irsaliye=irsaliye_row, birimler=db.birimler(sid=db.sirket_id(req)), para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
        kdv_dahil=0, bugun=datetime.date.today().isoformat())


@route(r"/fatura/(?P<fid>\d+)", roles=())
def fatura_detay(req, fid):
    conn = db.get_conn()
    sonuc = _fatura_detay(conn, fid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "Fatura bulunamadı.", "danger")
        return redirect("/fatura")
    f, kalemler = sonuc
    if not sube_koruma(req, f["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    loglar = conn.execute("SELECT * FROM audit_log WHERE tablo='fatura' AND kayit_id=? ORDER BY id DESC",
                          (f["id"],)).fetchall()
    odeme = _odeme_durumu(conn, f["id"])
    odenen = round(odeme["giris"] - odeme["cikis"], 2) if f["tip"] == "Satis" else round(odeme["cikis"] - odeme["giris"], 2)
    kalan = round((f["genel_toplam"] or 0) - odenen, 2)
    ekler_list = ekler.ekler_for(conn, "Fatura", f["id"])
    ek_upload = req.user["rol"] in ekler.EK_WRITE
    e_belgeler = conn.execute(
        "SELECT id, belge_no, tur, durum FROM e_belge WHERE kaynak_fatura_id=? ORDER BY id",
        (f["id"],)).fetchall()
    conn.close()
    return render_template("fatura/detay.html", fatura=f, kalemler=kalemler, loglar=loglar,
                           tip_label=TIP_LABEL, odeme=odeme, odenen=odenen, kalan=kalan,
                           ekler=ekler_list, ek_upload=ek_upload, ek_modul="Fatura",
                           ek_kayit_id=f["id"], ek_geri=f"/fatura/{f['id']}",
                           e_belgeler=e_belgeler)


@route(r"/fatura/(?P<fid>\d+)/duzenle", methods=("GET", "POST"), roles=FATURA_WRITE)
def fatura_duzenle(req, fid):
    conn = db.get_conn()
    f = conn.execute("SELECT * FROM fatura WHERE id=? AND sirket_id=?",
                     (int(fid), db.sirket_id(req))).fetchone()
    if not f:
        conn.close()
        return redirect("/fatura")
    if f["durum"] != "Taslak":
        conn.close()
        flash(req, "Yalnızca 'Taslak' durumundaki faturalar düzenlenebilir.", "danger")
        return redirect(f"/fatura/{f['id']}")
    if req.method == "POST":
        return _form_post(req, conn, f)

    kalemler = conn.execute("SELECT * FROM fatura_kalem WHERE fatura_id=? ORDER BY id",
                            (f["id"],)).fetchall()
    satirlar = [{"stok_id": k["stok_id"], "varyant_id": k["varyant_id"], "miktar": k["miktar"],
                 "birim_fiyat": k["birim_fiyat"], "iskonto_orani": k["iskonto_orani"],
                 "kdv_orani": k["kdv_orani"], "kdv_dahil": k["kdv_dahil"],
                 "birim": k["birim"], "goruntu_adi": k["goruntu_adi"],
                 "manuel_ad": (k["aciklama"] or "") if not k["stok_id"] else ""}
                for k in kalemler]
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(x) for x in satirlar])
    cariler = _cariler(conn, f["tip"], db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, f["cari_id"])
    conn.close()
    return render_template("fatura/form.html", fatura=f, satirlar=satirlar, cariler=cariler,
                           stoklar=stoklar, toplamlar=toplamlar, tip=f["tip"], cari_id=f["cari_id"],
                           cari_etiket=cari_etiket, cari_iskonto=cari_iskonto,
                           kaynak_irsaliye_id=f["kaynak_irsaliye_id"], kaynak_irsaliye=None,
                           birimler=db.birimler(sid=db.sirket_id(req)), para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           kdv_dahil=(f["kdv_dahil"] or 0),
                           bugun=datetime.date.today().isoformat())


@route(r"/fatura/(?P<fid>\d+)/sil", methods=("POST",), roles=FATURA_WRITE)
def fatura_sil(req, fid):
    conn = db.get_conn()
    f = conn.execute("SELECT * FROM fatura WHERE id=? AND sirket_id=?",
                     (int(fid), db.sirket_id(req))).fetchone()
    if not f:
        conn.close()
        return redirect("/fatura")
    if not sube_koruma(req, f["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    if f["durum"] != "Taslak":
        conn.close()
        flash(req, "Yalnızca 'Taslak' faturalar silinebilir (onaylı kayıt iptal edilmelidir).", "danger")
        return redirect(f"/fatura/{f['id']}")
    audit(req, "fatura", f["id"], "sil", {"fatura_no": f["fatura_no"], "tip": f["tip"]})
    ekler.ek_temizle(conn, "Fatura", f["id"])
    conn.execute("DELETE FROM notlar WHERE ilgili_tablo='fatura' AND ilgili_id=?", (f["id"],))
    db.bildirim_sil(conn, "fatura", f["id"])
    conn.execute("DELETE FROM fatura_kalem WHERE fatura_id=?", (f["id"],))
    conn.execute("DELETE FROM fatura WHERE id=?", (f["id"],))
    conn.commit()
    conn.close()
    flash(req, "Fatura silindi.", "ok")
    return redirect("/fatura")


def _form_post(req, conn, mevcut):
    tip = req.form.get("tip") if req.form.get("tip") in TIPLER else "Satis"
    cari_id = _i(req.form.get("cari_id"))
    tarih = req.form.get("tarih") or datetime.date.today().isoformat()
    vade = (req.form.get("vade") or "").strip() or None
    aciklama = (req.form.get("aciklama") or "").strip()
    para_birimi = req.form.get("para_birimi") if req.form.get("para_birimi") in db.para_birimleri(sid=db.sirket_id(req)) else "TRY"
    doviz_kur = _f(req.form.get("doviz_kur"), None)
    if para_birimi == "TRY":
        doviz_kur = 1.0        # TRY için kur her zaman 1 (kolon NOT NULL)
    elif not doviz_kur or doviz_kur <= 0:
        doviz_kur = db.guncel_kur(conn, para_birimi, db.sirket_id(req))
    kaynak_irsaliye_id = _i(req.form.get("kaynak_irsaliye"))
    if mevcut:
        kaynak_irsaliye_id = mevcut["kaynak_irsaliye_id"]
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else 0
    satirlar = _satirlar_from_form(req, kdv_dahil)

    sil = req.form.get("sil")
    if sil is not None:
        idx = int(sil)
        if 0 <= idx < len(satirlar):
            del satirlar[idx]
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)

    if req.form.get("tip_degistir"):
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)

    action = req.form.get("action")
    if action == "ekle":
        sid = _i(req.form.get("stok_sec"))
        if sid:
            s = conn.execute("SELECT * FROM stok_kart WHERE id=? AND sirket_id=?",
                             (sid, db.sirket_id(req))).fetchone()
            if s:
                bf = s["alis_fiyat"] if tip == "Alis" else s["satis_fiyat"]
                isk = _iskonto_default(conn, s, cari_id)
                satirlar.append({"stok_id": sid, "varyant_id": 0, "miktar": 1, "birim_fiyat": bf,
                                 "iskonto_orani": isk, "kdv_orani": s["kdv_orani"],
                                 "manuel_ad": ""})
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)
    if action == "ekle_manuel":
        ad = (req.form.get("manuel_ad") or "").strip()
        miktar = _f(req.form.get("manuel_miktar"), 1)
        bf = _f(req.form.get("manuel_birim_fiyat"))
        isk = _f(req.form.get("manuel_iskonto"))
        kdv = _f(req.form.get("manuel_kdv"), 20)
        if ad and miktar > 0:
            satirlar.append({"stok_id": None, "varyant_id": 0, "miktar": miktar,
                             "birim_fiyat": bf, "iskonto_orani": isk,
                             "kdv_orani": kdv, "manuel_ad": ad})
        else:
            flash(req, "Manuel satır için açıklama ve miktar girin.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)
    if action == "barkod":
        barkod = (req.form.get("barkod_sec") or "").strip()
        if barkod:
            sonuc = stok.barkod_bul(conn, barkod, db.sirket_id(req))
            if sonuc:
                kart = sonuc["kart"]
                bf = kart["alis_fiyat"] if tip == "Alis" else kart["satis_fiyat"]
                isk = _iskonto_default(conn, kart, cari_id)
                satirlar.append({"stok_id": sonuc["stok_id"], "varyant_id": sonuc["varyant_id"],
                                 "miktar": 1, "birim_fiyat": bf, "iskonto_orani": isk,
                                 "kdv_orani": kart["kdv_orani"]})
            else:
                flash(req, f"Barkod bulunamadı: {barkod}", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)

    # --- kaydet ---
    if not cari_id:
        flash(req, "Cari seçimi zorunludur.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)
    if kaynak_irsaliye_id:
        hata = _irsaliye_kontrol(conn, kaynak_irsaliye_id, db.sirket_id(req))
        if hata:
            flash(req, hata, "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                                kaynak_irsaliye_id)
    gecerli = [s for s in satirlar if (s["stok_id"] or s.get("manuel_ad")) and s["miktar"] > 0]
    if not gecerli:
        flash(req, "En az bir geçerli satır ekleyin.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)
    # İstek 3 — çapraz şirket hedef ID koruması (doğrudan POST enjeksiyonuna karşı).
    if not conn.execute("SELECT id FROM cari_kart WHERE id=? AND sirket_id=?",
                        (cari_id, db.sirket_id(req))).fetchone():
        flash(req, "Geçersiz cari seçimi (başka şirkete ait).", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                            kaynak_irsaliye_id)
    _sidler = {s["stok_id"] for s in gecerli if s["stok_id"]}
    if _sidler:
        _ph = ",".join("?" * len(_sidler))
        _izinli = {r["id"] for r in conn.execute(
            f"SELECT id FROM stok_kart WHERE id IN ({_ph}) AND sirket_id=?",
            tuple(_sidler) + (db.sirket_id(req),)).fetchall()}
        if _sidler - _izinli:
            flash(req, "Geçersiz stok seçimi (başka şirkete ait).", "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                                kaynak_irsaliye_id)
    top = _toplamlar(gecerli)

    islem = None
    if mevcut:
        conn.execute(
            "UPDATE fatura SET tip=?, cari_id=?, tarih=?, vade=?, aciklama=?, para_birimi=?, "
            "doviz_kur=?, ara_toplam=?, iskonto_toplam=?, kdv_toplam=?, genel_toplam=?, "
            "kdv_dahil=?, updated_at=datetime('now','localtime') WHERE id=?",
            (tip, cari_id, tarih, vade, aciklama, para_birimi, doviz_kur,
             top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"], top["genel_toplam"],
             kdv_dahil, mevcut["id"]),
        )
        conn.execute("DELETE FROM fatura_kalem WHERE fatura_id=?", (mevcut["id"],))
        fid = mevcut["id"]
        islem = ("guncelle", {"fatura_no": mevcut["fatura_no"]}, "Fatura güncellendi.")
    else:
        on_ek = TIP_ON_EK[tip]
        no = db.sonraki_belge_no(conn, "fatura", "fatura_no", on_ek, tarih[:4], db.sirket_id(req))
        cur = conn.execute(
            "INSERT INTO fatura(fatura_no, tip, cari_id, kaynak_irsaliye_id, "
            "tarih, vade, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, "
            "genel_toplam, aciklama, kdv_dahil, sube_id, created_by, sirket_id) VALUES(?,?,?,?,?,?,'Taslak',?,?,?,?,?,?,?,?,?,?,?)",
            (no, tip, cari_id, kaynak_irsaliye_id, tarih, vade, para_birimi, doviz_kur,
             top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"], top["genel_toplam"],
             aciklama, kdv_dahil, izole_sube(req), req.user["id"], db.sirket_id(req)),
        )
        fid = cur.lastrowid
        islem = ("olustur", {"fatura_no": no}, f"Fatura oluşturuldu: {no}")

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
            "INSERT INTO fatura_kalem(fatura_id, stok_id, varyant_id, miktar, birim_fiyat, "
            "iskonto_orani, kdv_orani, kdv_dahil, tutar, aciklama, birim, goruntu_adi, sirket_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (fid, s["stok_id"], s["varyant_id"], s["miktar"], s["birim_fiyat"],
             s["iskonto_orani"], s["kdv_orani"], s.get("kdv_dahil"), s["tutar"],
             (s.get("manuel_ad") or "").strip() or None, birim, goruntu, db.sirket_id(req)),
        )
    conn.commit()
    audit(req, "fatura", fid, islem[0], islem[1])
    flash(req, islem[2], "ok")
    conn.close()
    return redirect(f"/fatura/{fid}")


def _form_render(req, conn, mevcut, satirlar, tip, cari_id, tarih, vade, aciklama,
                 kaynak_irsaliye_id):
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(s) for s in satirlar])
    cariler = _cariler(conn, tip, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, cari_id)
    fatura = dict(mevcut) if mevcut else {"tip": tip, "cari_id": cari_id, "tarih": tarih,
                                          "vade": vade, "aciklama": aciklama,
                                          "para_birimi": "TRY", "doviz_kur": None}
    if mevcut is None:
        for k in ("para_birimi", "doviz_kur"):
            if req.form.get(k) not in (None, ""):
                fatura[k] = req.form.get(k)
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else (0 if mevcut is None else (mevcut["kdv_dahil"] or 0))
    return render_template("fatura/form.html", fatura=fatura, satirlar=satirlar,
                           cariler=cariler, stoklar=stoklar, toplamlar=toplamlar,
                           cari_etiket=cari_etiket, cari_iskonto=cari_iskonto,
                           birimler=db.birimler(sid=db.sirket_id(req)), para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           tip=tip, cari_id=cari_id, kaynak_irsaliye_id=kaynak_irsaliye_id,
                           kaynak_irsaliye=None, kdv_dahil=kdv_dahil,
                           bugun=datetime.date.today().isoformat())


@route(r"/fatura/(?P<fid>\d+)/durum", methods=("POST",), roles=FATURA_ONAY)
def fatura_durum(req, fid):
    durum = req.form.get("durum")
    if durum not in ("Onaylandı", "İptal"):
        flash(req, "Geçersiz durum geçişi.", "danger")
        return redirect(f"/fatura/{fid}")
    conn = db.get_conn()
    f = conn.execute("SELECT * FROM fatura WHERE id=? AND sirket_id=?",
                     (int(fid), db.sirket_id(req))).fetchone()
    if not f:
        conn.close()
        return redirect("/fatura")

    if durum == "Onaylandı":
        if f["durum"] != "Taslak":
            conn.close()
            flash(req, "Yalnızca 'Taslak' durumundaki fatura onaylanabilir.", "danger")
            return redirect(f"/fatura/{fid}")
        # F1 — kaynak irsaliyesi olan fatura yalnızca belgeleştirir; mali etki
        # irsaliye onayında oluşmuştur (çifte kayıt önlenir).
        kaynakli = bool(f["kaynak_irsaliye_id"])
        if not kaynakli:
            _cari_uygula(conn, req, dict(f), yon=1)
        conn.execute("UPDATE fatura SET durum='Onaylandı' WHERE id=?", (int(fid),))
        if not kaynakli:
            muhasebe.fis_uret(conn, "Fatura", int(fid))   # K26: otomatik yevmiye
        # F4 — Satış faturası onayında otomatik e-belge taslağı (e-Fatura/e-Arşiv tip otomatik).
        # e-Dönüşüm yalnızca BELGELEŞTİRME katmanıdır; mali etki (cari+yevmiye) yukarıda işlendi.
        if f["tip"] == "Satis":
            try:
                import edonusum
                edonusum._olustur(conn, req, "fatura", int(fid))
            except Exception:
                pass  # e-belge üretimi hata verirse fatura onayını bloke etme
        conn.commit()
        audit(req, "fatura", int(fid), "durum", {"eski": f["durum"], "yeni": "Onaylandı"})
        mesaj = ("Fatura onaylandı (kaynak irsaliyeden mali etki zaten işlenmişti)."
                 if kaynakli else "Fatura onaylandı; cari hareket oluşturuldu.")
        notify("bilgi", "Fatura onaylandı", f"{f['fatura_no']} onaylandı.", "fatura", int(fid), sirket_id=db.sirket_id(req))
        conn.close()
        flash(req, mesaj, "ok")
        return redirect(f"/fatura/{fid}")

    # --- İptal ---
    # K25: GİB'e gönderilmiş/onaylanmış e-belge varsa iptal engellenir (K15 deseni).
    aktif = db.aktif_eb(conn, "kaynak_fatura_id", int(fid))
    if aktif:
        conn.close()
        flash(req, f"Bu faturadan üretilmiş {aktif['belge_no']} ({aktif['tur']}) e-belgesi "
                   f"'{aktif['durum']}' durumunda. GİB'e bildirilmiş bir belge doğrudan iptal "
                   f"edilemez; önce e-belge tarafında resmi iptal/düzeltme sürecini tamamlayın.",
              "danger")
        return redirect(f"/fatura/{fid}")
    if f["durum"] not in ("Taslak", "Onaylandı"):
        conn.close()
        flash(req, "Bu durumdaki fatura iptal edilemez.", "danger")
        return redirect(f"/fatura/{fid}")
    if f["durum"] == "Onaylandı":
        if _bagli_tahsilat_var(conn, int(fid)):
            conn.close()
            flash(req, "Bu faturaya bağlı tahsilat/ödeme kaydı var (Kasa/Banka). "
                       "Önce ilgili hareketi iptal edin, sonra faturayı iptal edin.", "danger")
            return redirect(f"/fatura/{fid}")
        # F1 — kaynaklı fatura mali etki üretmemişti; geri alınacak bir şey yok.
        if not f["kaynak_irsaliye_id"]:
            _cari_uygula(conn, req, dict(f), yon=-1)
            muhasebe.fis_sil(conn, "Fatura", int(fid))   # K26: fiş geri alınır
    conn.execute("UPDATE fatura SET durum='İptal' WHERE id=?", (int(fid),))
    # Kaynaksız kalan Taslak/Reddedildi e-belgeleri de İptal'e al (öksüz kalmasın)
    conn.execute(
        "UPDATE e_belge SET durum='İptal', hata_mesaji='Kaynak fatura iptal edildi' "
        "WHERE kaynak_fatura_id=? AND durum IN ('Taslak','Reddedildi')", (int(fid),))
    conn.commit()
    audit(req, "fatura", int(fid), "durum", {"eski": f["durum"], "yeni": "İptal"})
    conn.close()
    flash(req, "Fatura iptal edildi (cari hareket geri alındı).", "ok")
    return redirect(f"/fatura/{fid}")


@route(r"/fatura/(?P<fid>\d+)/yazdir", roles=())
def fatura_yazdir(req, fid):
    conn = db.get_conn()
    sonuc = _fatura_detay(conn, fid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "Fatura bulunamadı.", "danger")
        return redirect("/fatura")
    f, kalemler = sonuc
    # F6 — şube izolasyonu: başka şubeye ait belge yazdırılamaz.
    if not sube_koruma(req, f["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    belge = yazdir_belge(f, kalemler, "fatura_no", TIP_LABEL[f["tip"]])
    conn.close()
    return render_template("yazdir/belge.html", belge=belge)


def register():
    return "fatura"
