# -*- coding: utf-8 -*-
"""Banka modülü (Faz 1): banka hesap tanımları, havale/EFT, banka-kasa transferi, ekstre,
CSV ekstre içe aktarma — CARİ BAĞLANTILI (Kasa ile aynı desen).

- "Havale/EFT Girişi" / "Havale/EFT Çıkışı" hareketinde opsiyonel cari seçilirse TEK işlemle
  cari_hareket otomatik oluşturulur (Giriş → Tahsilat/alacak, Çıkış → Ödeme/borc), ilgili_modul='Banka'.
- "Kasa → Banka" / "Banka → Kasa" transferlerinde opsiyonel kasa seçilirse kasa tarafına da
  otomatik karşı hareket yazılır (ilgili_modul='Transfer').
- CSV içe aktarma: banka ekstresi satırlarını "Banka Ekstresi" hareketi olarak kaydeder;
  otomatik mutabakat (faturalarla eşleştirme) Faz 2'de Fatura modülüyle birlikte gelecek.
"""
import datetime
import urllib.parse

import db
import cari
import muhasebe
from core import route, render_template, redirect, flash, audit, izole_sube, Response
from config import PARA_BIRIMLERI

BANKA_WRITE = ("Admin", "Muhasebe")
GIRIS = ["Açılış Bakiyesi", "Havale/EFT Girişi", "Kasa → Banka", "Banka Ekstresi (Giriş)"]
CIKIS = ["Havale/EFT Çıkışı", "Banka → Kasa", "Banka Ekstresi (Çıkış)"]
TRANSFER_TIPLERI = ("Kasa → Banka", "Banka → Kasa")
CARI_TIPLERI = ("Havale/EFT Girişi", "Havale/EFT Çıkışı")


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


def islem_yonu(tip):
    return 1 if tip in GIRIS else -1


def _bakiye_doviz(conn, hesap_id=None, tarih=None):
    """K18 — para birimi bazında net bakiye: {para_birimi: net_tutar}. Karışık para
    birimleri ASLA tek sayıya toplanmaz; her birim kendi cinsinden netlenir."""
    where, params = ["1=1"], []
    if hesap_id:
        where.append("banka_hesap_id=?")
        params.append(hesap_id)
    if tarih:
        where.append("tarih <= ?")
        params.append(tarih)
    rows = conn.execute(
        "SELECT islem_tipi, tutar, para_birimi FROM banka_hareket WHERE " + " AND ".join(where),
        params,
    ).fetchall()
    out = {}
    for r in rows:
        pb = r["para_birimi"] or "TRY"
        out[pb] = out.get(pb, 0.0) + islem_yonu(r["islem_tipi"]) * (r["tutar"] or 0)
    return out


def _bakiye(conn, hesap_id=None, tarih=None):
    """K18 — TL karşılık toplam bakiye (her hareketin kayıt kurundan: tutar × doviz_kur).
    TRY hareketlerinde doviz_kur=1 kabul edilir; döviz hareketleri TL'ye çevrilir."""
    where, params = ["1=1"], []
    if hesap_id:
        where.append("banka_hesap_id=?")
        params.append(hesap_id)
    if tarih:
        where.append("tarih <= ?")
        params.append(tarih)
    rows = conn.execute(
        "SELECT islem_tipi, tutar, doviz_kur FROM banka_hareket WHERE " + " AND ".join(where),
        params,
    ).fetchall()
    return round(sum(islem_yonu(r["islem_tipi"]) * (r["tutar"] or 0) * (r["doviz_kur"] or 1.0)
                     for r in rows), 2)


def _hesaplar(conn, sube_id=None, sid=None):
    where = "WHERE aktif=1"
    args = []
    if sube_id:
        where += " AND sube_id=?"
        args.append(sube_id)
    if sid is not None:
        where += " AND sirket_id=?"
        args.append(sid)
    return [dict(r) for r in conn.execute(f"SELECT * FROM banka_hesap {where} ORDER BY ad", args).fetchall()]


def _cariler(conn, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    return conn.execute("SELECT id, unvan, kod FROM cari_kart WHERE aktif=1" + extra +
                        " ORDER BY unvan", args).fetchall()


def _onayli_faturalar(conn, sid=None):
    extra = " AND f.sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    return conn.execute(
        "SELECT f.id, f.fatura_no, f.genel_toplam, c.unvan AS cari_unvan FROM fatura f "
        "LEFT JOIN cari_kart c ON c.id=f.cari_id WHERE f.durum='Onaylandı'" + extra +
        " ORDER BY f.id DESC", args
    ).fetchall()


def banka_hareket_olustur(conn, hesap_id, tarih, islem_tipi, tutar, aciklama=None, belge_no=None,
                          cari_id=None, ilgili_modul="Banka", ilgili_kayit_id=None, created_by=None,
                          para_birimi="TRY", doviz_kur=None, sirket_id=None):
    """Tek noktadan banka hareketi yazma (Kasa modülü transfer karşılığında da kullanılır)."""
    if sirket_id is None:
        sirket_id = (conn.execute("SELECT sirket_id FROM banka_hesap WHERE id=?",
                                  (hesap_id,)).fetchone() or {"sirket_id": 1})["sirket_id"]
    cur = conn.execute(
        "INSERT INTO banka_hareket(banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, "
        "belge_no, ilgili_modul, ilgili_kayit_id, created_by, para_birimi, doviz_kur, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no,
         ilgili_modul, ilgili_kayit_id, created_by, para_birimi, doviz_kur, sirket_id),
    )
    return cur.lastrowid


def _hareketler(conn, hesap_id=None, tarih=None, limit=200, sid=None):
    where, params = ["1=1"], []
    if sid is not None:
        where.append("h.sirket_id=?")
        params.append(sid)
    if hesap_id:
        where.append("h.banka_hesap_id=?")
        params.append(hesap_id)
    if tarih:
        where.append("h.tarih=?")
        params.append(tarih)
    rows = [dict(r) for r in conn.execute(
        "SELECT h.*, b.ad AS hesap_ad, b.kod AS hesap_kod, c.unvan AS cari_unvan, c.kod AS cari_kod "
        "FROM banka_hareket h JOIN banka_hesap b ON b.id=h.banka_hesap_id "
        "LEFT JOIN cari_kart c ON c.id=h.cari_id WHERE " + " AND ".join(where) +
        " ORDER BY h.tarih DESC, h.id DESC LIMIT ?",
        params + [limit],
    ).fetchall()]
    for r in rows:
        r["yon"] = islem_yonu(r["islem_tipi"])
    return rows


@route(r"/banka", roles=())
def banka_liste(req):
    conn = db.get_conn()
    hesaplar = _hesaplar(conn, izole_sube(req), db.sirket_id(req))
    for b in hesaplar:
        bd = _bakiye_doviz(conn, b["id"])
        b["bakiye_doviz"] = [(pb, bd[pb]) for pb in PARA_BIRIMLERI if abs(bd.get(pb, 0.0)) >= 0.005]
        b["bakiye"] = _bakiye(conn, b["id"])
        b["giris"] = _bakiye_giris(conn, b["id"])
        b["cikis"] = _bakiye_cikis(conn, b["id"])
    toplam = sum(b["bakiye"] for b in hesaplar)
    hesap_id = _i(req.q("hesap_id"))
    hareketler = _hareketler(conn, hesap_id=hesap_id, sid=db.sirket_id(req))
    conn.close()
    return render_template("banka/liste.html", hesaplar=hesaplar, toplam=toplam,
                           hareketler=hareketler, filtro_hesap=hesap_id)


def _bakiye_giris(conn, hesap_id=None):
    return round(conn.execute(
        "SELECT COALESCE(SUM(tutar * COALESCE(doviz_kur,1)),0) s FROM banka_hareket WHERE banka_hesap_id=? AND islem_tipi IN "
        "('Açılış Bakiyesi','Havale/EFT Girişi','Kasa → Banka','Banka Ekstresi (Giriş)')",
        (hesap_id,),
    ).fetchone()["s"], 2)


def _bakiye_cikis(conn, hesap_id=None):
    return round(conn.execute(
        "SELECT COALESCE(SUM(tutar * COALESCE(doviz_kur,1)),0) s FROM banka_hareket WHERE banka_hesap_id=? AND islem_tipi IN "
        "('Havale/EFT Çıkışı','Banka → Kasa','Banka Ekstresi (Çıkış)')",
        (hesap_id,),
    ).fetchone()["s"], 2)


@route(r"/banka/yeni", methods=("GET", "POST"), roles=BANKA_WRITE)
def banka_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        ad = (req.form.get("ad") or "").strip()
        kod = (req.form.get("kod") or "").strip()
        if ad:
            sid = db.sirket_id(req)
            if not kod:
                nxt = conn.execute(
                    "SELECT COALESCE(MAX(CAST(substr(kod,5) AS INTEGER)),0)+1 AS n FROM banka_hesap WHERE sirket_id=?",
                    (sid,)).fetchone()["n"]
                kod = f"BNK-{nxt:02d}"
                while conn.execute("SELECT 1 FROM banka_hesap WHERE sirket_id=? AND kod=?", (sid, kod)).fetchone():
                    nxt += 1
                    kod = f"BNK-{nxt:02d}"
            cur = conn.execute(
                "INSERT INTO banka_hesap(kod, ad, banka_adi, sube, iban, hesap_no, para_birimi, sube_id, sirket_id) "
                "VALUES(?,?,?,?,?,?,?,?,?)",
                (kod, ad, (req.form.get("banka_adi") or "").strip(),
                 (req.form.get("sube") or "").strip(), (req.form.get("iban") or "").strip(),
                 (req.form.get("hesap_no") or "").strip(), req.form.get("para_birimi") or "TRY",
                 izole_sube(req), sid),
            )
            conn.commit()
            audit(req, "banka_hesap", cur.lastrowid, "olustur", {"ad": ad, "kod": kod})
            flash(req, f"Banka hesabı eklendi: {ad}", "ok")
        conn.close()
        return redirect("/banka")
    conn.close()
    return render_template("banka/hesap_form.html")


@route(r"/banka/hareket", methods=("GET", "POST"), roles=BANKA_WRITE)
def banka_hareket(req):
    conn = db.get_conn()
    hesaplar = _hesaplar(conn, izole_sube(req), db.sirket_id(req))
    if req.method == "POST":
        hesap_id = _i(req.form.get("hesap_id"))
        islem_tipi = req.form.get("islem_tipi")
        tutar = _f(req.form.get("tutar"))
        tarih = req.form.get("tarih") or datetime.date.today().isoformat()
        cari_id = _i(req.form.get("cari_id"))
        kasa_id = _i(req.form.get("kasa_id"))
        aciklama = (req.form.get("aciklama") or "").strip()
        belge_no = (req.form.get("belge_no") or "").strip() or None
        if not hesap_id or not islem_tipi or tutar <= 0:
            flash(req, "Hesap, işlem tipi ve tutar (0'dan büyük) zorunludur.", "danger")
            conn.close()
            return redirect("/banka/hareket")

        # İstek 3 — çapraz şirket hedef ID koruması
        if not conn.execute("SELECT id FROM banka_hesap WHERE id=? AND sirket_id=?",
                            (hesap_id, db.sirket_id(req))).fetchone():
            conn.close()
            return Response("Bu hesap için yetkiniz yok.", "403 Forbidden")
        if cari_id and islem_tipi in CARI_TIPLERI and not conn.execute(
                "SELECT id FROM cari_kart WHERE id=? AND sirket_id=?",
                (cari_id, db.sirket_id(req))).fetchone():
            conn.close()
            flash(req, "Geçersiz cari seçimi (başka şirkete ait).", "danger")
            return redirect("/banka/hareket")
        if kasa_id and islem_tipi in TRANSFER_TIPLERI and not conn.execute(
                "SELECT id FROM kasa WHERE id=? AND sirket_id=?",
                (kasa_id, db.sirket_id(req))).fetchone():
            conn.close()
            flash(req, "Geçersiz kasa seçimi (başka şirkete ait).", "danger")
            return redirect("/banka/hareket")

        # K1/Faz 6 — şubeli kullanıcı yalnız kendi şubesinin hesabına işlem yazabilir.
        if izole_sube(req):
            b = conn.execute("SELECT sube_id FROM banka_hesap WHERE id=? AND sirket_id=?",
                             (hesap_id, db.sirket_id(req))).fetchone()
            if not b or b["sube_id"] != izole_sube(req):
                conn.close()
                return Response("Bu hesap için yetkiniz yok.", "403 Forbidden")

        # K18 — döviz: yalnız cari bağlantılı işlemlerde anlamlı; transfer/açılış TRY kalır
        para_birimi = "TRY"
        doviz_kur = None
        if islem_tipi in CARI_TIPLERI:
            para_birimi = req.form.get("para_birimi") if req.form.get("para_birimi") in db.para_birimleri(sid=db.sirket_id(req)) else "TRY"
            doviz_kur = _f(req.form.get("doviz_kur"), None)
            if para_birimi == "TRY":
                doviz_kur = None
            elif not doviz_kur or doviz_kur <= 0:
                doviz_kur = db.guncel_kur(conn, para_birimi, db.sirket_id(req))

        # yetersiz bakiye kontrolü (çıkış yönlü) — K18: ilgili para biriminde
        if islem_tipi in CIKIS and _bakiye_doviz(conn, hesap_id).get(para_birimi, 0.0) < tutar:
            flash(req, f"Banka bakiyesi bu işlem için yetersiz ({para_birimi}).", "danger")
            conn.close()
            return redirect("/banka/hareket")

        # karşı taraf (kasa) bakiyesi kontrolü — HİÇBİR kayıt yazılmadan önce (transferler TRY)
        if kasa_id and islem_tipi in TRANSFER_TIPLERI:
            import kasa
            if islem_tipi == "Kasa → Banka" and kasa._bakiye_doviz(conn, kasa_id).get("TRY", 0.0) < tutar:
                flash(req, "Kasa bakiyesi bu transfer için yetersiz.", "danger")
                conn.close()
                return redirect("/banka/hareket")

        fatura_id = _i(req.form.get("fatura_id"))
        ilgili_modul = "Transfer" if islem_tipi in TRANSFER_TIPLERI else "Banka"
        ilgili_kayit_id = None
        if fatura_id and islem_tipi in CARI_TIPLERI:
            f = conn.execute("SELECT id FROM fatura WHERE id=? AND durum='Onaylandı' AND sirket_id=?",
                             (fatura_id, db.sirket_id(req))).fetchone()
            if not f:
                conn.close()
                flash(req, "Bağlı fatura bulunamadı veya onaylı değil.", "danger")
                return redirect("/banka/hareket")
            ilgili_modul, ilgili_kayit_id = "Fatura", fatura_id
        hid = banka_hareket_olustur(conn, hesap_id, tarih, islem_tipi, tutar,
                                    aciklama, belge_no, cari_id, ilgili_modul, ilgili_kayit_id,
                                    req.user["id"], para_birimi, doviz_kur)
        muhasebe.fis_uret(conn, "Banka", hid)   # K26: otomatik yevmiye (transfer karşı kaydı atlanır)

        # --- Cari karşılığı (tek işlemle) ---
        if cari_id and islem_tipi in CARI_TIPLERI:
            tutar_tl = round(tutar * (doviz_kur or 1.0), 2)   # K18: cariye TL karşılığı
            if islem_tipi == "Havale/EFT Girişi":
                cari.hareket_ekle(conn, cari_id, tarih, "Tahsilat", belge_no, aciklama,
                                  alacak=tutar_tl, ilgili_modul="Banka", ilgili_kayit_id=hid,
                                  created_by=req.user["id"], para_birimi=para_birimi,
                                  doviz_kur=doviz_kur)
            else:  # Havale/EFT Çıkışı
                cari.hareket_ekle(conn, cari_id, tarih, "Ödeme", belge_no, aciklama,
                                  borc=tutar_tl, ilgili_modul="Banka", ilgili_kayit_id=hid,
                                  created_by=req.user["id"], para_birimi=para_birimi,
                                  doviz_kur=doviz_kur)

        # --- Kasa karşılığı (transfer, opsiyonel) ---
        if kasa_id and islem_tipi in TRANSFER_TIPLERI:
            import kasa  # döngüyü önlemek için lazy import
            kasa.kasa_hareket_olustur(conn, kasa_id, tarih, islem_tipi, tutar,
                                      aciklama, belge_no, ilgili_modul="Transfer",
                                      ilgili_kayit_id=hid, created_by=req.user["id"])

        conn.commit()
        audit(req, "banka_hareket", hid, islem_tipi, {"hesap_id": hesap_id, "tutar": tutar,
                                                     "cari_id": cari_id, "kasa_id": kasa_id})
        conn.close()
        flash(req, "Banka hareketi kaydedildi.", "ok")
        return redirect("/banka")

    cariler = _cariler(conn, db.sirket_id(req))
    faturalar = _onayli_faturalar(conn, db.sirket_id(req))
    try:
        import kasa
        kasalar = kasa._kasalar(conn, sid=db.sirket_id(req))
    except Exception:  # noqa: BLE001
        kasalar = []
    conn.close()
    return render_template("banka/hareket_form.html", hesaplar=hesaplar, giris=GIRIS, cikis=CIKIS,
                           cariler=cariler, kasalar=kasalar, faturalar=faturalar,
                           para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           bugun=datetime.date.today().isoformat())


@route(r"/banka/hareket/(?P<sid>\d+)/iptal", methods=("POST",), roles=BANKA_WRITE)
def banka_hareket_iptal(req, sid):
    """K15 — banka hareketi iptali: varsa cari karşılığı (Tahsilat/Ödeme) da geri alınır."""
    conn = db.get_conn()
    h = conn.execute("SELECT * FROM banka_hareket WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not h:
        conn.close()
        flash(req, "Banka hareketi bulunamadı.", "danger")
        return redirect("/banka")
    if h["islem_tipi"] in TRANSFER_TIPLERI or h["islem_tipi"] == "Açılış Bakiyesi" \
            or h["islem_tipi"].startswith("Banka Ekstresi"):
        conn.close()
        flash(req, "Bu hareket tipi tek başına iptal edilemez.", "danger")
        return redirect("/banka")
    conn.execute("DELETE FROM cari_hareket WHERE ilgili_modul='Banka' AND ilgili_kayit_id=?",
                 (int(sid),))
    muhasebe.fis_sil(conn, "Banka", int(sid))   # K26: fiş geri alınır
    conn.execute("DELETE FROM banka_hareket WHERE id=?", (int(sid),))
    conn.commit()
    audit(req, "banka_hareket", int(sid), "iptal",
          {"islem_tipi": h["islem_tipi"], "tutar": h["tutar"]})
    conn.close()
    flash(req, "Banka hareketi iptal edildi (varsa cari karşılığı geri alındı).", "ok")
    return redirect("/banka")


@route(r"/banka/hareket/(?P<hid>\d+)/fis", roles=())
def banka_fis(req, hid):
    """D014-A1 — banka hareket fişi (`kasa/fis.html` deseniyle birebir)."""
    conn = db.get_conn()
    h = conn.execute(
        "SELECT h.*, b.ad AS hesap_ad, b.kod AS hesap_kod, c.unvan AS cari_unvan "
        "FROM banka_hareket h JOIN banka_hesap b ON b.id=h.banka_hesap_id "
        "LEFT JOIN cari_kart c ON c.id=h.cari_id WHERE h.id=? AND h.sirket_id=?",
        (int(hid), db.sirket_id(req))).fetchone()
    if not h:
        conn.close()
        flash(req, "Hareket bulunamadı.", "danger")
        return redirect("/banka")
    h = dict(h)
    h["yon"] = islem_yonu(h["islem_tipi"])
    conn.close()
    return render_template("banka/fis.html", h=h, bugun=datetime.date.today().isoformat())


@route(r"/banka/hesap/(?P<bid>\d+)", roles=())
def banka_ekstre(req, bid):
    conn = db.get_conn()
    hesap = conn.execute("SELECT * FROM banka_hesap WHERE id=? AND sirket_id=?",
                         (int(bid), db.sirket_id(req))).fetchone()
    if not hesap:
        conn.close()
        flash(req, "Banka hesabı bulunamadı.", "danger")
        return redirect("/banka")
    hesap = dict(hesap)
    rows = [dict(r) for r in conn.execute(
        "SELECT h.*, c.unvan AS cari_unvan FROM banka_hareket h "
        "LEFT JOIN cari_kart c ON c.id=h.cari_id WHERE h.banka_hesap_id=? ORDER BY h.tarih, h.id",
        (hesap["id"],),
    ).fetchall()]
    bal = 0.0
    bd = {}
    for r in rows:
        tl = islem_yonu(r["islem_tipi"]) * (r["tutar"] or 0) * (r["doviz_kur"] or 1.0)
        bal += tl
        pb = r["para_birimi"] or "TRY"
        bd[pb] = bd.get(pb, 0.0) + islem_yonu(r["islem_tipi"]) * (r["tutar"] or 0)
        r["yon"] = islem_yonu(r["islem_tipi"])
        r["bakiye"] = round(bal, 2)
    bakiye_doviz = [(pb, bd[pb]) for pb in PARA_BIRIMLERI if abs(bd.get(pb, 0.0)) >= 0.005]
    conn.close()
    return render_template("banka/ekstre.html", hesap=hesap, rows=rows, bakiye=round(bal, 2),
                           bakiye_doviz=bakiye_doviz)


@route(r"/banka/import", methods=("POST",), roles=BANKA_WRITE)
def banka_import(req):
    hesap_id = _i(req.form.get("hesap_id"))
    csv_text = (req.form.get("csv_text") or "").strip()
    if not hesap_id or not csv_text:
        flash(req, "Hesap seçin ve CSV içeriği girin.", "danger")
        return redirect("/banka")
    conn = db.get_conn()
    hesap = conn.execute("SELECT id FROM banka_hesap WHERE id=? AND sirket_id=?",
                         (hesap_id, db.sirket_id(req))).fetchone()
    if not hesap:
        conn.close()
        flash(req, "Hesap bulunamadı.", "danger")
        return redirect("/banka")
    eklenen = 0
    for satir in csv_text.splitlines():
        satir = satir.strip()
        if not satir:
            continue
        parcalar = [p.strip() for p in satir.replace(",", ";").split(";")]
        if len(parcalar) < 2:
            continue
        tarih = parcalar[0]
        try:
            tutar = float(parcalar[1].replace(",", "."))
        except ValueError:
            continue
        if tutar == 0:
            continue
        aciklama = parcalar[2] if len(parcalar) > 2 else "Banka ekstresi"
        tip = "Banka Ekstresi (Giriş)" if tutar > 0 else "Banka Ekstresi (Çıkış)"
        banka_hareket_olustur(conn, hesap_id, tarih, tip, abs(tutar), aciklama,
                              ilgili_modul="Banka Ekstresi", created_by=req.user["id"])
        eklenen += 1
    conn.commit()
    audit(req, "banka_hareket", 0, "csv_import", {"hesap_id": hesap_id, "n": eklenen})
    conn.close()
    flash(req, f"CSV içe aktarıldı: {eklenen} satır eklendi.", "ok")
    return redirect(f"/banka/hesap/{hesap_id}")


def register():
    return "banka"
