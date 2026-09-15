# -*- coding: utf-8 -*-
"""Servis Takip modülü (Faz 3 — 1.2).

- Servis kaydı: cihaz, seri no, arıza, aksesuar, garanti kapsamı, teknisyen atama.
- Durum akışı: Alındı → Teşhis Edildi → Onay Bekliyor → Tamir Ediliyor → Tamamlandı → Teslim Edildi (İade de olabilir).
- Yedek parça ekleme: servise bağlı parça/tutar (stok kartından seçim, depo bazlı).

FİNANSAL ETKİ MİMARİSİ (İrsaliye→Fatura zinciriyle aynı desen):
- "Teslim Edildi" anında: parça **stok düşümü** (depo bazlı, "Servis Tüketimi") + tutar > 0 ise
  **Taslak Satış Faturası** üretilir (`fatura.kaynak_servis_id` → K8). Cari'ye DOĞRUDAN hareket yazılmaz.
- **Mali etki (cari_hareket) fatura ONAYLANDIĞINDA** doğar (mevcut K2/K6 akışı) — KDV'li genel toplam.
- İşçilik kalemi ayrı bir "hizmet" stok kartıyla (tip='Hizmet', kod HZM-SRV-ISCLK) faturaya girer;
  parça kalemleri kendi stok kartlarıyla (KDV oranları stok kartından, iskonto K9 önceliğiyle).
- Teslim geri alınamaz: faturası veya düşülen parçası varsa önce fatura iptal edilmeli (K15 benzeri).
- Roller: yazma Admin/Servis/Muhasebe; fatura ONAYI yine Admin/Muhasebe (FATURA_ONAY).
"""
import datetime

import db
import stok
import fatura
from core import route, render_template, redirect, flash, audit, notify, izole_sube, sube_koruma, Response

DURUMLAR = ["Alındı", "Teşhis Edildi", "Onay Bekliyor", "Tamir Ediliyor", "Tamamlandı", "Teslim Edildi", "İade"]
DURUM_BADGE = {"Alındı": "b-info", "Teşhis Edildi": "b-info", "Onay Bekliyor": "b-warn",
               "Tamir Ediliyor": "b-info", "Tamamlandı": "b-ok", "Teslim Edildi": "b-ok", "İade": "b-danger"}
YAZMA = ("Admin", "Servis", "Muhasebe")
HIZMET_KOD = "HZM-SRV-ISCLK"


def _servis_depo_id(conn, sid=None):
    """Yedek parça tüketimi için varsayılan Servis deposu; yoksa ilk depo."""
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [sid] if sid is not None else []
    d = conn.execute("SELECT id FROM depo WHERE tip='Servis' AND aktif=1" + extra +
                     " ORDER BY id LIMIT 1", args).fetchone()
    if d:
        return d["id"]
    d = conn.execute("SELECT id FROM depo WHERE aktif=1" + extra + " ORDER BY id LIMIT 1", args).fetchone()
    return d["id"] if d else 1


def _hizmet_stok(conn, sid=None):
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [HIZMET_KOD] + ([sid] if sid is not None else [])
    return conn.execute("SELECT * FROM stok_kart WHERE kod=? AND aktif=1" + extra, args).fetchone()


def _servis_fatura_olustur(conn, req, s):
    """Teslim edilen servis için KDV'li **Taslak Satış Faturası** üretir.

    Kalemler: yedek parçalar (stok kartından KDV + K9 iskonto) + işçilik (hizmet kalemi).
    Mali etki yoktur (durum Taslak); cari hareket fatura onayında doğar.
    Dönüş: oluşturulan fatura id, veya None (faturalanacak tutar yoksa — garanti/ücretsiz).
    """
    parcalar = conn.execute(
        "SELECT p.*, k.kdv_orani AS kart_kdv, k.iskonto_orani AS kart_isk FROM servis_parca p "
        "LEFT JOIN stok_kart k ON k.id=p.stok_id WHERE p.servis_id=?", (s["id"],)).fetchall()
    satirlar = []
    for p in parcalar:
        if float(p["miktar"] or 0) <= 0:
            continue
        stok_row = conn.execute("SELECT * FROM stok_kart WHERE id=? AND sirket_id=?",
                                 (p["stok_id"], s["sirket_id"])).fetchone()
        if not stok_row:
            continue
        isk = fatura._iskonto_default(conn, stok_row, s["cari_id"], s["sirket_id"])
        satirlar.append({"stok_id": p["stok_id"], "varyant_id": 0, "miktar": float(p["miktar"]),
                         "birim_fiyat": float(p["birim_fiyat"] or 0), "iskonto_orani": isk,
                         "kdv_orani": float(stok_row["kdv_orani"] or 20)})
    if float(s["iscilik_ucreti"] or 0) > 0:
        hizmet = _hizmet_stok(conn, s["sirket_id"])
        if hizmet:
            isk = fatura._iskonto_default(conn, hizmet, s["cari_id"], s["sirket_id"])
            satirlar.append({"stok_id": hizmet["id"], "varyant_id": 0, "miktar": 1,
                             "birim_fiyat": float(s["iscilik_ucreti"]), "iskonto_orani": isk,
                             "kdv_orani": float(hizmet["kdv_orani"] or 20)})
    gecerli = [x for x in satirlar if x["miktar"] > 0]
    if not gecerli:
        return None
    top = fatura._toplamlar(gecerli)
    yil = datetime.date.today().year
    no = db.sonraki_belge_no(conn, "fatura", "fatura_no", "SF", yil, s["sirket_id"])
    cur = conn.execute(
        "INSERT INTO fatura(fatura_no, tip, cari_id, sube_id, kaynak_servis_id, tarih, durum, "
        "para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,'Taslak','TRY',1,?,?,?,?,?,?,?)",
        (no, "Satis", s["cari_id"], s["sube_id"], s["id"], datetime.date.today().isoformat(),
         top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"], top["genel_toplam"],
         f"Servis {s['servis_no']} — {s['cihaz']}", req.user["id"], s["sirket_id"]))
    fid = cur.lastrowid
    for x in gecerli:
        conn.execute(
            "INSERT INTO fatura_kalem(fatura_id, stok_id, varyant_id, miktar, birim_fiyat, "
            "iskonto_orani, kdv_orani, tutar, sirket_id) VALUES(?,?,?,?,?,?,?,?,?)",
            (fid, x["stok_id"], x["varyant_id"], x["miktar"], x["birim_fiyat"],
             x["iskonto_orani"], x["kdv_orani"], x["tutar"], s["sirket_id"]))
    return fid


def _servis_faturasi(conn, sid):
    """Servise bağlı aktif (İptal edilmemiş) fatura kaydı."""
    return conn.execute(
        "SELECT id, fatura_no, durum, genel_toplam, kdv_toplam, ara_toplam FROM fatura "
        "WHERE kaynak_servis_id=? AND durum != 'İptal' ORDER BY id DESC LIMIT 1", (sid,)).fetchone()


@route(r"/servis", roles=())
def servis_liste(req):
    conn = db.get_conn()
    where, params = ["s.sirket_id = ?"], [db.sirket_id(req)]
    q = (req.q("q") or "").strip()
    if q:
        where.append("(s.servis_no LIKE ? OR s.cihaz LIKE ? OR s.seri_no LIKE ? OR c.unvan LIKE ?)")
        params += [f"%{q}%"] * 4
    durum = req.q("durum")
    if durum:
        where.append("s.durum=?")
        params.append(durum)
    if izole_sube(req):
        where.append("s.sube_id=?")
        params.append(izole_sube(req))
    rows = [dict(r) for r in conn.execute(
        "SELECT s.*, c.unvan AS cari_unvan, u.kullanici_adi AS teknisyen_adi, "
        "(SELECT COUNT(*) FROM fatura f WHERE f.kaynak_servis_id=s.id AND f.durum != 'İptal') AS fatura_sayisi "
        "FROM servis_kayit s LEFT JOIN cari_kart c ON c.id=s.cari_id "
        "LEFT JOIN kullanici u ON u.id=s.teknisyen_id "
        "WHERE " + " AND ".join(where) + " ORDER BY s.id DESC LIMIT 300", params).fetchall()]
    sayac = dict.fromkeys(DURUMLAR, 0)
    for r in rows:
        sayac[r["durum"]] = sayac.get(r["durum"], 0) + 1
    conn.close()
    return render_template("servis/liste.html", rows=rows, q=q, durum=durum, sayac=sayac,
                           DURUMLAR=DURUMLAR, DURUM_BADGE=DURUM_BADGE)


@route(r"/servis/yeni", methods=("GET", "POST"), roles=YAZMA)
def servis_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        cari_id = req.form.get("cari_id")
        cihaz = (req.form.get("cihaz") or "").strip()
        seri_no = (req.form.get("seri_no") or "").strip() or None
        ariza = (req.form.get("ariza") or "").strip()
        if not cari_id or not cihaz or not ariza:
            flash(req, "Cari, cihaz ve arıza zorunludur.", "danger")
            conn.close()
            return redirect("/servis/yeni")
        yil = datetime.date.today().year
        no = db.sonraki_belge_no(conn, "servis_kayit", "servis_no", "SRV", yil, db.sirket_id(req))
        cur = conn.execute(
            "INSERT INTO servis_kayit(servis_no, cari_id, cihaz, seri_no, ariza, aksesuar, "
            "teknisyen_id, durum, garanti_kapsami, sube_id, created_by, sirket_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (no, int(cari_id), cihaz, seri_no, ariza,
             (req.form.get("aksesuar") or "").strip() or None,
             int(req.form.get("teknisyen_id") or 0) or None,
             "Alındı", 1 if req.form.get("garanti_kapsami") == "1" else 0,
             izole_sube(req) or int(req.form.get("sube_id") or 0) or None, req.user["id"],
             db.sirket_id(req)))
        conn.commit()
        audit(req, "servis_kayit", cur.lastrowid, "olustur", {"cihaz": cihaz, "seri_no": seri_no})
        conn.close()
        flash(req, f"Servis kaydı oluşturuldu: {no}.", "ok")
        return redirect("/servis")
    cariler = conn.execute("SELECT id, unvan FROM cari_kart WHERE aktif=1 AND sirket_id=? ORDER BY unvan",
                            (db.sirket_id(req),)).fetchall()
    teknisyenler = conn.execute("SELECT id, kullanici_adi FROM kullanici WHERE rol IN ('Servis','Admin') ORDER BY kullanici_adi").fetchall()
    subeler = conn.execute("SELECT id, ad FROM sube WHERE sirket_id=? ORDER BY ad",
                           (db.sirket_id(req),)).fetchall()
    conn.close()
    return render_template("servis/form.html", cariler=cariler, teknisyenler=teknisyenler, subeler=subeler)


@route(r"/servis/(?P<sid>\d+)", roles=())
def servis_detay(req, sid):
    conn = db.get_conn()
    s = conn.execute(
        "SELECT s.*, c.unvan AS cari_unvan, c.telefon AS cari_tel, c.gsm AS cari_gsm, "
        "u.kullanici_adi AS teknisyen_adi, sb.ad AS sube_ad FROM servis_kayit s "
        "LEFT JOIN cari_kart c ON c.id=s.cari_id LEFT JOIN kullanici u ON u.id=s.teknisyen_id "
        "LEFT JOIN sube sb ON sb.id=s.sube_id WHERE s.id=? AND s.sirket_id=?",
        (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/servis")
    if not sube_koruma(req, s["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    parcalar = [dict(r) for r in conn.execute(
        "SELECT p.*, k.ad AS stok_ad, k.kod AS stok_kod, d.ad AS depo_ad FROM servis_parca p "
        "LEFT JOIN stok_kart k ON k.id=p.stok_id LEFT JOIN depo d ON d.id=p.depo_id "
        "WHERE p.servis_id=? ORDER BY p.id", (int(sid),)).fetchall()]
    toplam_parca = round(sum(float(p["tutar"] or 0) for p in parcalar), 2)
    gecmis = []
    if s["seri_no"]:
        gecmis = conn.execute(
            "SELECT id, servis_no, durum, gelis_tarihi FROM servis_kayit "
            "WHERE seri_no=? AND id!=? ORDER BY id DESC", (s["seri_no"], int(sid))).fetchall()
    seri = None
    if s["seri_no"]:
        seri = conn.execute(
            "SELECT g.*, k.ad AS stok_ad FROM stok_seri g JOIN stok_kart k ON k.id=g.stok_id "
            "WHERE g.seri_no=?", (s["seri_no"],)).fetchone()
    fatura_row = _servis_faturasi(conn, int(sid))
    stoklar = conn.execute("SELECT id, ad, kod FROM stok_kart WHERE aktif=1 AND tip != 'Hizmet' "
                            "AND sirket_id=? ORDER BY ad", (db.sirket_id(req),)).fetchall()
    teknisyenler = conn.execute("SELECT id, kullanici_adi FROM kullanici WHERE rol IN ('Servis','Admin') ORDER BY kullanici_adi").fetchall()
    subeler = conn.execute("SELECT id, ad FROM sube WHERE sirket_id=? ORDER BY ad",
                           (db.sirket_id(req),)).fetchall()
    depolar = conn.execute("SELECT id, ad, tip FROM depo WHERE aktif=1 AND sirket_id=? ORDER BY id",
                           (db.sirket_id(req),)).fetchall()
    servis_depo = conn.execute("SELECT id FROM depo WHERE tip='Servis' AND aktif=1 AND sirket_id=? ORDER BY id LIMIT 1",
                               (db.sirket_id(req),)).fetchone()
    notlar = conn.execute(
        "SELECT n.*, u.kullanici_adi FROM notlar n LEFT JOIN kullanici u ON u.id=n.kullanici_id "
        "WHERE n.ilgili_tablo='servis_kayit' AND n.ilgili_id=? ORDER BY n.id DESC", (int(sid),)).fetchall()
    conn.close()
    return render_template("servis/detay.html", s=s, parcalar=parcalar, toplam_parca=toplam_parca,
                           gecmis=gecmis, seri=seri, fatura_row=fatura_row, stoklar=stoklar,
                           teknisyenler=teknisyenler, subeler=subeler, depolar=depolar,
                           servis_depo=(servis_depo["id"] if servis_depo else None),
                           notlar=notlar, DURUMLAR=DURUMLAR, DURUM_BADGE=DURUM_BADGE)


@route(r"/servis/(?P<sid>\d+)/yazdir", roles=())
def servis_yazdir(req, sid):
    """D014-A1 — servis kaydı fişi (müşteri teslim + teknisyen iş emri, tek şablon)."""
    conn = db.get_conn()
    s = conn.execute(
        "SELECT s.*, c.unvan AS cari_unvan, c.telefon AS cari_tel, c.gsm AS cari_gsm, "
        "u.kullanici_adi AS teknisyen_adi, sb.ad AS sube_ad FROM servis_kayit s "
        "LEFT JOIN cari_kart c ON c.id=s.cari_id LEFT JOIN kullanici u ON u.id=s.teknisyen_id "
        "LEFT JOIN sube sb ON sb.id=s.sube_id WHERE s.id=? AND s.sirket_id=?",
        (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        flash(req, "Servis kaydı bulunamadı.", "danger")
        return redirect("/servis")
    if not sube_koruma(req, s["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    parcalar = [dict(r) for r in conn.execute(
        "SELECT p.*, k.ad AS stok_ad, k.kod AS stok_kod FROM servis_parca p "
        "LEFT JOIN stok_kart k ON k.id=p.stok_id "
        "WHERE p.servis_id=? ORDER BY p.id", (int(sid),)).fetchall()]
    conn.close()
    toplam_parca = round(sum(float(p["tutar"] or 0) for p in parcalar), 2)
    return render_template("servis/yazdir.html", s=s, parcalar=parcalar,
                           toplam_parca=toplam_parca)


@route(r"/servis/(?P<sid>\d+)/durum", methods=("POST",), roles=YAZMA)
def servis_durum(req, sid):
    conn = db.get_conn()
    s = conn.execute("SELECT * FROM servis_kayit WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/servis")
    yeni = req.form.get("durum")
    if yeni not in DURUMLAR:
        flash(req, "Geçersiz durum.", "danger")
        conn.close()
        return redirect(f"/servis/{sid}")

    # Teslim geri alma engeli: fatura varsa veya parça düşüldüyse önce fatura iptal edilmeli.
    if s["durum"] == "Teslim Edildi" and yeni != "Teslim Edildi":
        fat = _servis_faturasi(conn, int(sid))
        parca = conn.execute("SELECT COUNT(*) c FROM servis_parca WHERE servis_id=? AND miktar > 0",
                             (int(sid),)).fetchone()["c"]
        if fat or parca:
            conn.close()
            flash(req, "Teslim geri alınamaz: bu servisin faturası/parça düşümü var. "
                       "Önce faturayı iptal edin (ve gerekirse stok hareketini düzeltin).", "danger")
            return redirect(f"/servis/{sid}")

    yeni_fatura = None
    if yeni == "Teslim Edildi" and s["durum"] != "Teslim Edildi":
        # 1) Parça stok düşümü — depo bazlı (K11).
        parcalar_list = conn.execute("SELECT * FROM servis_parca WHERE servis_id=?", (int(sid),)).fetchall()
        for p in parcalar_list:
            if p["stok_id"] and float(p["miktar"] or 0) > 0:
                depo_id = p["depo_id"] or _servis_depo_id(conn, s["sirket_id"])
                stok._hareket_olustur(
                    conn, req, p["stok_id"], 0, depo_id, "Servis Tüketimi",
                    -float(p["miktar"]), birim_maliyet=float(p["birim_fiyat"] or 0),
                    aciklama=f"Servis {s['servis_no']} — {p['aciklama'] or 'yedek parça'}",
                    belge_no=s["servis_no"], ilgili_modul="servis", ilgili_kayit_id=int(sid))
        # 2) Taslak satış faturası (mali etki fatura ONAYINDA — K2/K6).
        if not _servis_faturasi(conn, int(sid)):
            yeni_fatura = _servis_fatura_olustur(conn, req, s)

    conn.execute("UPDATE servis_kayit SET durum=?, updated_at=datetime('now','localtime') WHERE id=?",
                 (yeni, int(sid)))
    conn.commit()
    conn.close()
    if yeni == "Tamamlandı" and s["durum"] != "Tamamlandı":
        # Faz 6 — "cihazınız hazır" müşteri bildirimi (SMS/e-posta entegrasyon noktası).
        _cc = db.get_conn()
        cr = _cc.execute("SELECT unvan, gsm, email FROM cari_kart WHERE id=?",
                         (s["cari_id"],)).fetchone() if s["cari_id"] else None
        _cc.close()
        if cr and (cr["gsm"] or cr["email"]):
            mesaj = (f"{s['servis_no']} nolu servis kaydınız ({s['cihaz']}) hazır; "
                     f"teslim alabilirsiniz. — Brn Teknoloji")
            if cr["gsm"]:
                notify("bilgi", "Cihazınız hazır", mesaj, "servis_kayit", int(sid),
                       hedef=cr["gsm"], kanal="sms", sirket_id=db.sirket_id(req))
            elif cr["email"]:
                notify("bilgi", "Cihazınız hazır", mesaj, "servis_kayit", int(sid),
                       hedef=cr["email"], kanal="eposta", sirket_id=db.sirket_id(req))
    if yeni == "Teslim Edildi" and s["durum"] != "Teslim Edildi":
        if yeni_fatura:
            audit(req, "servis_kayit", int(sid), "teslim_fatura",
                  {"fatura_id": yeni_fatura})
            audit(req, "fatura", yeni_fatura, "olustur", {"kaynak": "servis", "servis_id": int(sid)})
            flash(req, "Servis teslim edildi; Taslak satış faturası oluşturuldu. "
                       "Mali etki fatura onayında doğar (Fatura modülü).", "ok")
        else:
            flash(req, "Servis teslim edildi (garanti kapsamı/ücretsiz — faturalanacak tutar yok).", "ok")
    else:
        flash(req, f"Durum güncellendi: {yeni}.", "ok")
    audit(req, "servis_kayit", int(sid), "durum", {"onceki": s["durum"], "yeni": yeni})
    return redirect(f"/servis/{sid}")


@route(r"/servis/(?P<sid>\d+)/faturala", methods=("POST",), roles=YAZMA)
def servis_faturala(req, sid):
    """Tamamlanan (Teslim Edildi) ama henüz faturalanmamış servise taslak fatura üret (K14 deseni)."""
    conn = db.get_conn()
    s = conn.execute("SELECT * FROM servis_kayit WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/servis")
    if s["durum"] not in ("Tamamlandı", "Teslim Edildi"):
        conn.close()
        flash(req, "Yalnızca 'Tamamlandı' veya 'Teslim Edildi' durumundaki servis faturalanabilir.", "danger")
        return redirect(f"/servis/{sid}")
    mevcut = _servis_faturasi(conn, int(sid))
    if mevcut:
        conn.close()
        flash(req, f"Bu servisin zaten faturası var: {mevcut['fatura_no']}.", "info")
        return redirect(f"/fatura/{mevcut['id']}")
    fid = _servis_fatura_olustur(conn, req, s)
    if fid is None:
        conn.close()
        flash(req, "Faturalanacak tutar yok (garanti kapsamı/ücretsiz).", "danger")
        return redirect(f"/servis/{sid}")
    conn.commit()
    conn.close()
    audit(req, "fatura", fid, "olustur", {"kaynak": "servis", "servis_id": int(sid)})
    audit(req, "servis_kayit", int(sid), "faturala", {"fatura_id": fid})
    flash(req, "Taslak satış faturası oluşturuldu; onay için Fatura modülünü kullanın.", "ok")
    return redirect(f"/fatura/{fid}")


@route(r"/servis/(?P<sid>\d+)/guncelle", methods=("POST",), roles=YAZMA)
def servis_guncelle(req, sid):
    conn = db.get_conn()
    s = conn.execute("SELECT * FROM servis_kayit WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/servis")
    conn.execute(
        "UPDATE servis_kayit SET teknisyen_id=?, garanti_kapsami=?, iscilik_ucreti=?, "
        "aciklama=?, sube_id=?, updated_at=datetime('now','localtime') WHERE id=?",
        (int(req.form.get("teknisyen_id") or 0) or None,
         1 if req.form.get("garanti_kapsami") == "1" else 0,
         float(req.form.get("iscilik_ucreti") or 0) or 0,
         (req.form.get("aciklama") or "").strip() or None,
         int(req.form.get("sube_id") or 0) or None, int(sid)))
    conn.commit()
    audit(req, "servis_kayit", int(sid), "guncelle", {"iscilik": req.form.get("iscilik_ucreti")})
    conn.close()
    flash(req, "Servis güncellendi.", "ok")
    return redirect(f"/servis/{sid}")


@route(r"/servis/(?P<sid>\d+)/parca", methods=("POST",), roles=YAZMA)
def servis_parca_ekle(req, sid):
    conn = db.get_conn()
    s = conn.execute("SELECT * FROM servis_kayit WHERE id=? AND sirket_id=?",
                     (int(sid), db.sirket_id(req))).fetchone()
    if not s:
        conn.close()
        return redirect("/servis")
    stok_id = req.form.get("stok_id")
    miktar = float(req.form.get("miktar") or 0)
    birim_fiyat = float(req.form.get("birim_fiyat") or 0)
    if not stok_id or miktar <= 0:
        flash(req, "Parça seçin ve miktar girin.", "danger")
        conn.close()
        return redirect(f"/servis/{sid}")
    depo_id = int(req.form.get("depo_id") or 0) or _servis_depo_id(conn, s["sirket_id"])
    tutar = round(miktar * birim_fiyat, 2)
    cur = conn.execute(
        "INSERT INTO servis_parca(servis_id, stok_id, miktar, birim_fiyat, tutar, aciklama, depo_id, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?)",
        (int(sid), int(stok_id), miktar, birim_fiyat, tutar,
         (req.form.get("aciklama") or "").strip() or None, depo_id, s["sirket_id"]))
    conn.commit()
    audit(req, "servis_parca", cur.lastrowid, "ekle", {"servis": sid, "tutar": tutar, "depo_id": depo_id})
    conn.close()
    flash(req, "Yedek parça eklendi.", "ok")
    return redirect(f"/servis/{sid}")


@route(r"/servis/parca/(?P<pid>\d+)/sil", methods=("POST",), roles=YAZMA)
def servis_parca_sil(req, pid):
    conn = db.get_conn()
    p = conn.execute("SELECT * FROM servis_parca WHERE id=? AND sirket_id=?",
                     (int(pid), db.sirket_id(req))).fetchone()
    if p:
        sid = p["servis_id"]
        servis = conn.execute("SELECT durum FROM servis_kayit WHERE id=? AND sirket_id=?",
                              (sid, db.sirket_id(req))).fetchone()
        if servis and servis["durum"] in ("Tamamlandı", "Teslim Edildi", "İade"):
            conn.close()
            flash(req, "Tamamlanmış/teslim edilmiş serviste parça silinemez.", "danger")
            return redirect(f"/servis/{sid}")
        conn.execute("DELETE FROM servis_parca WHERE id=?", (int(pid),))
        conn.commit()
        audit(req, "servis_parca", int(pid), "sil", {})
        flash(req, "Parça silindi.", "ok")
        conn.close()
        return redirect(f"/servis/{sid}")
    conn.close()
    return redirect("/servis")
