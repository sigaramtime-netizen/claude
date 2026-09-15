# -*- coding: utf-8 -*-
"""Bakım Sözleşmesi modülü — D paketi.

- Cihaz bazlı periyodik bakım sözleşmeleri (cari + dönem + periyot + bedel + kapsanan cihazlar).
- Periyodik fatura: sözleşme bedeli tek tıkla Onaylı Satış Faturası olarak kesilir
  (cari + yevmiye); aynı dönem için mükerrer üretim engellenir.
- İş emri: sözleşme kapsamında servis kaydı açılır (kapsam dahili → garanti_kapsami=1/ücretsiz).
- Yenileme: bitişe yaklaşan sözleşmeler için uyarı + tek tıkla yeni döneme yenileme.
- K1 şube izolasyonu + çoklu şirket (sirket_id) + çapraz-şirket koruması.
"""
import datetime

import db
import fatura as fatura_mod
import muhasebe
from core import route, render_template, redirect, flash, audit, notify, izole_sube, Response

YAZMA = ("Admin", "Servis", "Muhasebe")
FATURA = ("Admin", "Muhasebe")
PERIYOTLAR = ["Aylik", "3 Aylik", "6 Aylik", "Yillik"]
PERIYOT_LABEL = {"Aylik": "Aylık", "3 Aylik": "3 Aylık", "6 Aylik": "6 Aylık", "Yillik": "Yıllık"}
HIZMET_KOD = "HZM-BKM-SOZL"
YAKLASMA_GUN = 30


def _f(v, default=0.0):
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _i(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _hizmet_stok(conn, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [HIZMET_KOD] + ([sid] if sid is not None else [])
    return conn.execute("SELECT * FROM stok_kart WHERE kod=? AND aktif=1" + extra, args).fetchone()


def _durum_turet(s, bugun):
    """Saklanan durum (Aktif/İptal) üzerine süre türetimi: Süresi Doldu / Yaklaşıyor."""
    if s["durum"] == "İptal":
        return "İptal"
    bitis = s["bitis"] or ""
    if bitis and bitis < bugun.isoformat():
        return "Süresi Doldu"
    if bitis and bitis <= (bugun + datetime.timedelta(days=YAKLASMA_GUN)).isoformat():
        return "Yaklaşıyor"
    return "Aktif"


DURUM_BADGE = {"Aktif": "b-ok", "Yaklaşıyor": "b-warn", "Süresi Doldu": "b-danger", "İptal": "b-muted"}


def _donem_etiket(periyot, tarih):
    d = datetime.date.fromisoformat(tarih)
    if periyot == "Aylik":
        return f"{d.year}-{d.month:02d}"
    if periyot == "3 Aylik":
        return f"{d.year}-Q{(d.month - 1) // 3 + 1}"
    if periyot == "6 Aylik":
        return f"{d.year}-H{(1 if d.month <= 6 else 2)}"
    return str(d.year)


def _donem_faturalandi(conn, sozlesme_id, donem):
    return conn.execute(
        "SELECT 1 FROM bakim_sozlesme_fatura WHERE sozlesme_id=? AND donem=?",
        (sozlesme_id, donem)).fetchone() is not None


def _fatura_uret(conn, req, soz):
    """Periyodik bedel için Onaylı Satış Faturası üretir (cari + yevmiye). Dönüş: (fid, hata)."""
    bugun = datetime.date.today().isoformat()
    donem = _donem_etiket(soz["periyot"], bugun)
    if _donem_faturalandi(conn, soz["id"], donem):
        return None, f"Bu dönem için fatura zaten üretildi ({donem})."
    hizmet = _hizmet_stok(conn, soz["sirket_id"])
    if not hizmet:
        return None, "Bakım hizmeti stok kalemi bulunamadı (seed eksik)."
    satirlar = [{"stok_id": hizmet["id"], "varyant_id": 0, "miktar": 1,
                 "birim_fiyat": _f(soz["bedel"]),
                 "iskonto_orani": fatura_mod._iskonto_default(conn, hizmet, soz["cari_id"]),
                 "kdv_orani": float(hizmet["kdv_orani"] or 20)}]
    top = fatura_mod._toplamlar(satirlar)
    yil = datetime.date.today().year
    no = db.sonraki_belge_no(conn, "fatura", "fatura_no", "SF", yil, soz["sirket_id"])
    cur = conn.execute(
        "INSERT INTO fatura(fatura_no, tip, cari_id, sube_id, tarih, durum, para_birimi, "
        "doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama, "
        "created_by, sirket_id) VALUES(?,?,?,?,?,'Onaylandı','TRY',1,?,?,?,?,?,?,?)",
        (no, "Satis", soz["cari_id"], soz["sube_id"], bugun,
         top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"], top["genel_toplam"],
         f"Bakım sözleşmesi {soz['sozlesme_no']} — {donem} dönemi", req.user["id"],
         soz["sirket_id"]))
    fid = cur.lastrowid
    for x in satirlar:
        conn.execute(
            "INSERT INTO fatura_kalem(fatura_id, stok_id, varyant_id, miktar, birim_fiyat, "
            "iskonto_orani, kdv_orani, tutar, birim, sirket_id) VALUES(?,?,?,?,?,?,?,?,?,?)",
            (fid, x["stok_id"], x["varyant_id"], x["miktar"], x["birim_fiyat"],
             x["iskonto_orani"], x["kdv_orani"], x["tutar"], hizmet["birim"], soz["sirket_id"]))
    conn.execute("INSERT INTO bakim_sozlesme_fatura(sozlesme_id, fatura_id, donem, sirket_id) "
                 "VALUES(?,?,?,?)", (soz["id"], fid, donem, soz["sirket_id"]))
    f = conn.execute("SELECT * FROM fatura WHERE id=?", (fid,)).fetchone()
    fatura_mod._cari_uygula(conn, req, dict(f), yon=1)
    muhasebe.fis_uret(conn, "Fatura", fid)
    return fid, None


def _soz(conn, sid_req, soz_id):
    return conn.execute("SELECT * FROM bakim_sozlesme WHERE id=? AND sirket_id=?",
                        (soz_id, sid_req)).fetchone()


@route(r"/bakim/sozlesmeler", roles=())
def bakim_liste(req):
    conn = db.get_conn()
    sid = db.sirket_id(req)
    q = (req.q("q") or "").strip()
    durum = req.q("durum") or ""
    where, params = ["s.sirket_id=?"], [sid]
    if q:
        where.append("(s.sozlesme_no LIKE ? OR c.unvan LIKE ?)")
        like = f"%{q}%"
        params += [like, like]
    w = " AND ".join(where)
    rows = [dict(r) for r in conn.execute(
        f"SELECT s.*, c.unvan AS cari_unvan, c.kod AS cari_kod, "
        f"(SELECT COUNT(*) FROM bakim_sozlesme_cihaz z WHERE z.sozlesme_id=s.id) AS cihaz_sayisi, "
        f"(SELECT COUNT(*) FROM bakim_sozlesme_fatura f2 WHERE f2.sozlesme_id=s.id) AS fatura_sayisi "
        f"FROM bakim_sozlesme s JOIN cari_kart c ON c.id=s.cari_id "
        f"WHERE {w} ORDER BY s.id DESC LIMIT 200", params).fetchall()]
    bugun = datetime.date.today()
    for r in rows:
        r["durum_turet"] = _durum_turet(r, bugun)
    if durum:
        rows = [r for r in rows if r["durum_turet"] == durum]
    conn.close()
    return render_template("bakim/liste.html", rows=rows, durumlar=["Aktif", "Yaklaşıyor", "Süresi Doldu", "İptal"],
                           durum_badge=DURUM_BADGE, periyot_label=PERIYOT_LABEL,
                           filtro={"q": q, "durum": durum})


@route(r"/bakim/sozlesme/yeni", methods=("GET", "POST"), roles=YAZMA)
def bakim_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        sid = db.sirket_id(req)
        cari_id = _i(req.form.get("cari_id"))
        bas = (req.form.get("baslangic") or "").strip()
        bit = (req.form.get("bitis") or "").strip()
        periyot = req.form.get("periyot") or "Yillik"
        bedel = _f(req.form.get("bedel"))
        if not cari_id or not bas or not bit:
            conn.close()
            flash(req, "Cari, başlangıç ve bitiş zorunludur.", "danger")
            return redirect("/bakim/sozlesme/yeni")
        if bit <= bas:
            conn.close()
            flash(req, "Bitiş tarihi başlangıçtan sonra olmalıdır.", "danger")
            return redirect("/bakim/sozlesme/yeni")
        if not conn.execute("SELECT 1 FROM cari_kart WHERE id=? AND sirket_id=? AND aktif=1",
                            (cari_id, sid)).fetchone():
            conn.close()
            flash(req, "Geçersiz müşteri.", "danger")
            return redirect("/bakim/sozlesme/yeni")
        yil = datetime.date.today().year
        no = db.sonraki_belge_no(conn, "bakim_sozlesme", "sozlesme_no", "BKM", yil, sid)
        cur = conn.execute(
            "INSERT INTO bakim_sozlesme(sozlesme_no, cari_id, baslangic, bitis, periyot, bedel, "
            "para_birimi, durum, aciklama, sube_id, created_by, sirket_id) "
            "VALUES(?,?,?,?,?,?,'TRY','Aktif',?,?,?,?)",
            (no, cari_id, bas, bit, periyot, bedel,
             (req.form.get("aciklama") or "").strip() or None,
             izole_sube(req), req.user["id"], sid))
        conn.commit()
        audit(req, "bakim_sozlesme", cur.lastrowid, "olustur", {"sozlesme_no": no})
        flash(req, f"Sözleşme oluşturuldu: {no}", "ok")
        conn.close()
        return redirect(f"/bakim/sozlesme/{cur.lastrowid}")
    cariler = conn.execute(
        "SELECT id, kod, unvan FROM cari_kart WHERE aktif=1 AND tip IN ('Musteri','HerIkisi') "
        "AND sirket_id=? ORDER BY unvan", (db.sirket_id(req),)).fetchall()
    conn.close()
    return render_template("bakim/form.html", mevcut=None, cariler=cariler, periyotlar=PERIYOTLAR,
                           periyot_label=PERIYOT_LABEL)


@route(r"/bakim/sozlesme/(?P<sid>\d+)", roles=())
def bakim_detay(req, sid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    s = conn.execute(
        "SELECT s.*, c.unvan AS cari_unvan, c.kod AS cari_kod FROM bakim_sozlesme s "
        "JOIN cari_kart c ON c.id=s.cari_id WHERE s.id=? AND s.sirket_id=?",
        (int(sid), sirket)).fetchone()
    if not s:
        conn.close()
        flash(req, "Sözleşme bulunamadı.", "danger")
        return redirect("/bakim/sozlesmeler")
    bugun = datetime.date.today()
    durum_turet = _durum_turet(s, bugun)
    cihazlar = conn.execute(
        "SELECT z.*, k.kod AS stok_kod, k.ad AS stok_ad FROM bakim_sozlesme_cihaz z "
        "LEFT JOIN stok_kart k ON k.id=z.stok_id WHERE z.sozlesme_id=? ORDER BY z.id",
        (s["id"],)).fetchall()
    faturalar = conn.execute(
        "SELECT f.id, f.fatura_no, f.tarih, f.genel_toplam, f.durum, bf.donem "
        "FROM bakim_sozlesme_fatura bf JOIN fatura f ON f.id=bf.fatura_id "
        "WHERE bf.sozlesme_id=? ORDER BY bf.id DESC", (s["id"],)).fetchall()
    is_emirleri = conn.execute(
        "SELECT id, servis_no, cihaz, seri_no, ariza, durum, garanti_kapsami "
        "FROM servis_kayit WHERE bakim_sozlesme_id=? ORDER BY id DESC", (s["id"],)).fetchall()
    teknisyenler = conn.execute(
        "SELECT id, kullanici_adi FROM kullanici WHERE rol IN ('Servis','Admin') ORDER BY kullanici_adi").fetchall()
    bugun_donem = _donem_etiket(s["periyot"], bugun.isoformat())
    donem_faturalandi = _donem_faturalandi(conn, s["id"], bugun_donem)
    conn.close()
    return render_template("bakim/detay.html", s=s, durum_turet=durum_turet, cihazlar=cihazlar,
                           faturalar=faturalar, is_emirleri=is_emirleri, teknisyenler=teknisyenler,
                           durum_badge=DURUM_BADGE, periyot_label=PERIYOT_LABEL,
                           bugun_donem=bugun_donem, donem_faturalandi=donem_faturalandi)


@route(r"/bakim/sozlesme/(?P<sid>\d+)/yazdir", roles=())
def bakim_yazdir(req, sid):
    """D014-A1 — bakım sözleşmesi çıktısı (sözleşme metni + kapsanan cihazlar)."""
    conn = db.get_conn()
    s = conn.execute(
        "SELECT s.*, c.unvan AS cari_unvan, c.kod AS cari_kod, c.telefon AS cari_tel, "
        "c.adres AS cari_adres FROM bakim_sozlesme s "
        "JOIN cari_kart c ON c.id=s.cari_id WHERE s.id=? AND s.sirket_id=?",
        (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        flash(req, "Sözleşme bulunamadı.", "danger")
        return redirect("/bakim/sozlesmeler")
    cihazlar = conn.execute(
        "SELECT z.*, k.kod AS stok_kod, k.ad AS stok_ad FROM bakim_sozlesme_cihaz z "
        "LEFT JOIN stok_kart k ON k.id=z.stok_id WHERE z.sozlesme_id=? ORDER BY z.id",
        (s["id"],)).fetchall()
    conn.close()
    return render_template("bakim/yazdir.html", s=s, cihazlar=cihazlar,
                           periyot_label=PERIYOT_LABEL)


@route(r"/bakim/sozlesme/(?P<sid>\d+)/duzenle", methods=("GET", "POST"), roles=YAZMA)
def bakim_duzenle(req, sid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    s = _soz(conn, sirket, int(sid))
    if not s:
        conn.close()
        flash(req, "Sözleşme bulunamadı.", "danger")
        return redirect("/bakim/sozlesmeler")
    if req.method == "POST":
        bas = (req.form.get("baslangic") or "").strip()
        bit = (req.form.get("bitis") or "").strip()
        periyot = req.form.get("periyot") or s["periyot"]
        bedel = _f(req.form.get("bedel"), s["bedel"])
        if bit <= bas:
            conn.close()
            flash(req, "Bitiş tarihi başlangıçtan sonra olmalıdır.", "danger")
            return redirect(f"/bakim/sozlesme/{s['id']}/duzenle")
        conn.execute(
            "UPDATE bakim_sozlesme SET baslangic=?, bitis=?, periyot=?, bedel=?, aciklama=?, "
            "updated_at=datetime('now','localtime') WHERE id=?",
            (bas, bit, periyot, bedel,
             (req.form.get("aciklama") or "").strip() or None, s["id"]))
        conn.commit()
        audit(req, "bakim_sozlesme", s["id"], "guncelle", {"sozlesme_no": s["sozlesme_no"]})
        flash(req, "Sözleşme güncellendi.", "ok")
        conn.close()
        return redirect(f"/bakim/sozlesme/{s['id']}")
    cariler = conn.execute(
        "SELECT id, kod, unvan FROM cari_kart WHERE aktif=1 AND sirket_id=? ORDER BY unvan",
        (sirket,)).fetchall()
    conn.close()
    return render_template("bakim/form.html", mevcut=s, cariler=cariler, periyotlar=PERIYOTLAR,
                           periyot_label=PERIYOT_LABEL)


@route(r"/bakim/sozlesme/(?P<sid>\d+)/cihaz", methods=("POST",), roles=YAZMA)
def bakim_cihaz_ekle(req, sid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    s = _soz(conn, sirket, int(sid))
    if not s:
        conn.close()
        flash(req, "Sözleşme bulunamadı.", "danger")
        return redirect("/bakim/sozlesmeler")
    stok_id = _i(req.form.get("stok_id"))
    seri = (req.form.get("seri_no") or "").strip() or None
    acik = (req.form.get("cihaz_aciklama") or "").strip() or None
    if not stok_id and not acik:
        conn.close()
        flash(req, "Cihaz (stok) veya açıklama girin.", "danger")
        return redirect(f"/bakim/sozlesme/{s['id']}")
    conn.execute(
        "INSERT INTO bakim_sozlesme_cihaz(sozlesme_id, stok_id, seri_no, cihaz_aciklama, sirket_id) "
        "VALUES(?,?,?,?,?)", (s["id"], stok_id, seri, acik, sirket))
    conn.commit()
    audit(req, "bakim_sozlesme_cihaz", conn.execute(
        "SELECT id FROM bakim_sozlesme_cihaz WHERE sozlesme_id=? ORDER BY id DESC LIMIT 1",
        (s["id"],)).fetchone()["id"], "olustur", {"sozlesme_no": s["sozlesme_no"]})
    flash(req, "Cihaz eklendi.", "ok")
    conn.close()
    return redirect(f"/bakim/sozlesme/{s['id']}")


@route(r"/bakim/sozlesme/cihaz/(?P<cid>\d+)/sil", methods=("POST",), roles=YAZMA)
def bakim_cihaz_sil(req, cid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    z = conn.execute("SELECT * FROM bakim_sozlesme_cihaz WHERE id=? AND sirket_id=?",
                     (int(cid), sirket)).fetchone()
    if z:
        conn.execute("DELETE FROM bakim_sozlesme_cihaz WHERE id=?", (z["id"],))
        conn.commit()
        audit(req, "bakim_sozlesme_cihaz", z["id"], "sil", {})
        flash(req, "Cihaz kaldırıldı.", "ok")
        soz_id = z["sozlesme_id"]
    else:
        soz_id = None
    conn.close()
    return redirect(f"/bakim/sozlesme/{soz_id}" if soz_id else "/bakim/sozlesmeler")


@route(r"/bakim/sozlesme/(?P<sid>\d+)/fatura-uret", methods=("POST",), roles=FATURA)
def bakim_fatura_uret(req, sid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    s = _soz(conn, sirket, int(sid))
    if not s:
        conn.close()
        flash(req, "Sözleşme bulunamadı.", "danger")
        return redirect("/bakim/sozlesmeler")
    fid, hata = _fatura_uret(conn, req, dict(s))
    if hata:
        conn.close()
        flash(req, hata, "danger")
        return redirect(f"/bakim/sozlesme/{s['id']}")
    conn.commit()
    f = conn.execute("SELECT fatura_no, genel_toplam FROM fatura WHERE id=?", (fid,)).fetchone()
    audit(req, "fatura", fid, "olustur", {"fatura_no": f["fatura_no"], "kaynak": "Bakım Sözleşmesi"})
    notify("bilgi", "Bakım faturası kesildi",
           f"{s['sozlesme_no']} → {f['fatura_no']} ({f['genel_toplam']:,.2f} TL).",
           "fatura", fid, sirket_id=sirket)
    flash(req, f"Fatura üretildi: {f['fatura_no']} — {f['genel_toplam']:,.2f} TL", "ok")
    conn.close()
    return redirect(f"/bakim/sozlesme/{s['id']}")


@route(r"/bakim/sozlesme/(?P<sid>\d+)/is-emri", methods=("POST",), roles=YAZMA)
def bakim_is_emri(req, sid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    s = _soz(conn, sirket, int(sid))
    if not s:
        conn.close()
        flash(req, "Sözleşme bulunamadı.", "danger")
        return redirect("/bakim/sozlesmeler")
    cihaz_id = _i(req.form.get("cihaz_id"))
    ariza = (req.form.get("ariza") or "").strip()
    if not ariza:
        conn.close()
        flash(req, "Arıza açıklaması zorunludur.", "danger")
        return redirect(f"/bakim/sozlesme/{s['id']}")
    z = conn.execute("SELECT * FROM bakim_sozlesme_cihaz WHERE id=? AND sozlesme_id=?",
                     (cihaz_id, s["id"])).fetchone() if cihaz_id else None
    cihaz_adi = ""
    seri_no = None
    if z:
        if z["stok_id"]:
            k = conn.execute("SELECT ad FROM stok_kart WHERE id=?", (z["stok_id"],)).fetchone()
            cihaz_adi = k["ad"] if k else (z["cihaz_aciklama"] or "")
        else:
            cihaz_adi = z["cihaz_aciklama"] or ""
        seri_no = z["seri_no"]
    yil = datetime.date.today().year
    no = db.sonraki_belge_no(conn, "servis_kayit", "servis_no", "SRV", yil, sirket)
    cur = conn.execute(
        "INSERT INTO servis_kayit(servis_no, cari_id, cihaz, seri_no, ariza, teknisyen_id, durum, "
        "garanti_kapsami, bakim_sozlesme_id, aciklama, sube_id, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (no, s["cari_id"], cihaz_adi, seri_no, ariza,
         _i(req.form.get("teknisyen_id")) or None, "Alındı", 1, s["id"],
         f"Bakım sözleşmesi {s['sozlesme_no']} kapsamında", s["sube_id"], req.user["id"], sirket))
    conn.commit()
    audit(req, "servis_kayit", cur.lastrowid, "olustur",
          {"servis_no": no, "kaynak": "Bakım Sözleşmesi", "sozlesme_id": s["id"]})
    notify("bilgi", "Bakım iş emri açıldı", f"{no} — {s['sozlesme_no']} kapsamında (ücretsiz).",
           "servis_kayit", cur.lastrowid, sirket_id=sirket)
    flash(req, f"İş emri açıldı: {no} (sözleşme kapsamında)", "ok")
    conn.close()
    return redirect(f"/bakim/sozlesme/{s['id']}")


@route(r"/bakim/sozlesme/(?P<sid>\d+)/yenile", methods=("POST",), roles=YAZMA)
def bakim_yenile(req, sid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    s = _soz(conn, sirket, int(sid))
    if not s:
        conn.close()
        flash(req, "Sözleşme bulunamadı.", "danger")
        return redirect("/bakim/sozlesmeler")
    bas = datetime.date.fromisoformat(s["bitis"]) + datetime.timedelta(days=1)
    sure = datetime.date.fromisoformat(s["bitis"]) - datetime.date.fromisoformat(s["baslangic"])
    bit = bas + sure
    yil = datetime.date.today().year
    no = db.sonraki_belge_no(conn, "bakim_sozlesme", "sozlesme_no", "BKM", yil, sirket)
    cur = conn.execute(
        "INSERT INTO bakim_sozlesme(sozlesme_no, cari_id, baslangic, bitis, periyot, bedel, "
        "para_birimi, durum, aciklama, sube_id, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,'Aktif',?,?,?,?)",
        (no, s["cari_id"], bas.isoformat(), bit.isoformat(), s["periyot"], s["bedel"],
         s["para_birimi"], f"{s['sozlesme_no']} yenilemesi", s["sube_id"], req.user["id"], sirket))
    yeni_id = cur.lastrowid
    for z in conn.execute("SELECT * FROM bakim_sozlesme_cihaz WHERE sozlesme_id=?",
                          (s["id"],)).fetchall():
        conn.execute(
            "INSERT INTO bakim_sozlesme_cihaz(sozlesme_id, stok_id, seri_no, cihaz_aciklama, sirket_id) "
            "VALUES(?,?,?,?,?)",
            (yeni_id, z["stok_id"], z["seri_no"], z["cihaz_aciklama"], sirket))
    conn.commit()
    audit(req, "bakim_sozlesme", yeni_id, "olustur", {"sozlesme_no": no, "yenileme": s["sozlesme_no"]})
    notify("bilgi", "Sözleşme yenilendi", f"{s['sozlesme_no']} → {no}",
           "bakim_sozlesme", yeni_id, sirket_id=sirket)
    flash(req, f"Sözleşme yenilendi: {no}", "ok")
    conn.close()
    return redirect(f"/bakim/sozlesme/{yeni_id}")


@route(r"/bakim/sozlesme/(?P<sid>\d+)/durum", methods=("POST",), roles=YAZMA)
def bakim_durum(req, sid):
    conn = db.get_conn()
    sirket = db.sirket_id(req)
    s = _soz(conn, sirket, int(sid))
    if s:
        yeni = "İptal" if s["durum"] == "Aktif" else "Aktif"
        conn.execute("UPDATE bakim_sozlesme SET durum=? WHERE id=?", (yeni, s["id"]))
        conn.commit()
        audit(req, "bakim_sozlesme", s["id"], "durum", {"yeni": yeni})
        flash(req, "Sözleşme " + ("iptal edildi." if yeni == "İptal" else "aktifleştirildi."), "ok")
    conn.close()
    return redirect("/bakim/sozlesmeler")


@route(r"/bakim/rapor", roles=())
def bakim_rapor(req):
    conn = db.get_conn()
    sid = db.sirket_id(req)
    bugun = datetime.date.today()
    esik = (bugun + datetime.timedelta(days=YAKLASMA_GUN)).isoformat()
    rows = [dict(r) for r in conn.execute(
        "SELECT s.*, c.unvan AS cari_unvan, "
        "(SELECT COUNT(*) FROM bakim_sozlesme_cihaz z WHERE z.sozlesme_id=s.id) AS cihaz_sayisi "
        "FROM bakim_sozlesme s JOIN cari_kart c ON c.id=s.cari_id WHERE s.sirket_id=? "
        "ORDER BY s.bitis", (sid,)).fetchall()]
    aktif = yaklasan = dolan = 0
    toplam_bedel = 0.0
    for r in rows:
        t = _durum_turet(r, bugun)
        r["durum_turet"] = t
        if t == "Aktif":
            aktif += 1
            toplam_bedel += (r["bedel"] or 0)
        elif t == "Yaklaşıyor":
            yaklasan += 1
            toplam_bedel += (r["bedel"] or 0)
        elif t == "Süresi Doldu":
            dolan += 1
    conn.close()
    return render_template("bakim/rapor.html", rows=rows, aktif=aktif, yaklasan=yaklasan,
                           dolan=dolan, toplam_bedel=toplam_bedel, esik=esik,
                           durum_badge=DURUM_BADGE, periyot_label=PERIYOT_LABEL)


def register():
    pass
