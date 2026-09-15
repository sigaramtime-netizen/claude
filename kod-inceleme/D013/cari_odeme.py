# -*- coding: utf-8 -*-
"""D013 — Cari Tahsilat / Ödeme ekranı (v1.44.0).

Tek ekran, iki yön:  GET/POST /cari/<id>/tahsilat  (para girişi)
                     GET/POST /cari/<id>/odeme     (para çıkışı)

- Ödeme dağılımı POS `pos_satis_olustur` `odemeler` deseninin aynısı: bölünebilir
  çoklu satır (Nakit + Kart + Havale + Çek/Senet karışık olabilir).
- Yeni muhasebe mantığı YOK: mevcut `kasa_hareket_olustur` / `banka_hareket_olustur` /
  `cek_senet.cek_olustur` + `fis_uret` / `cek_senkron` + `cari.hareket_ekle` çağrılır.
- Döviz: D012 kur sabitleme deseni (TRY→kur None; form kuru yoksa `guncel_kur`);
  cariye + fişlere TL karşılığı yazılır (K18).
- Kısmi kapatma serbest; fazla tutar engellenmez, avans uyarısı verilir.
- Yetki: tahsilat Admin·Muhasebe·Satis; ödeme Admin·Muhasebe (Satis ödeme yapamaz).
- K1: cari + kasa + banka + terminal hep aktif şirketten doğrulanır.
"""
import datetime

import db
import cari
import kasa
import banka
import cek_senet
import muhasebe
import pos
from core import route, render_template, redirect, flash, audit, izole_sube, Response

TAHSILAT_ROLLERI = ("Admin", "Muhasebe", "Satis")
ODEME_ROLLERI = ("Admin", "Muhasebe")

ODEME_TIPLERI = ["Nakit", "Havale", "Kart", "Cek", "Senet"]
TIP_LABEL = {"Nakit": "Nakit", "Havale": "Havale/EFT", "Kart": "Kredi Kartı (POS)",
             "Cek": "Çek", "Senet": "Senet"}


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


def _bakiye(conn, cari_id):
    """Cari net bakiye = Σborç − Σalacak. (+) müşteri bize borçlu, (−) biz borçluyuz."""
    r = conn.execute("SELECT COALESCE(SUM(borc),0) b, COALESCE(SUM(alacak),0) a "
                     "FROM cari_hareket WHERE cari_id=?", (cari_id,)).fetchone()
    return round((r["b"] or 0.0) - (r["a"] or 0.0), 2)


def _odemeler_from_form(req):
    """POS `p_tip/p_tutar/p_vade` deseni + çek/senet ek alanları (p_no/p_banka)."""
    tipler = req.form_list.get("p_tip", [])
    tutarlar = req.form_list.get("p_tutar", [])
    vadeler = req.form_list.get("p_vade", [])
    nolar = req.form_list.get("p_no", [])
    bankalar = req.form_list.get("p_banka", [])
    out = []
    for i in range(len(tipler)):
        tip = (tipler[i] or "").strip()
        if tip not in ODEME_TIPLERI:
            continue
        tutar = _f(tutarlar[i] if i < len(tutarlar) else 0)
        if tutar <= 0:
            continue
        out.append({
            "tip": tip,
            "tutar": round(tutar, 2),
            "vade": (vadeler[i] if i < len(vadeler) else "").strip(),
            "no": (nolar[i] if i < len(nolar) else "").strip(),
            "banka": (bankalar[i] if i < len(bankalar) else "").strip(),
        })
    return out


def tahsilat_odeme_olustur(conn, req, cari_kart, yon, odemeler, kasa_id=None,
                           banka_hesap_id=None, terminal_id=None, tarih=None,
                           para_birimi="TRY", doviz_kur=None, aciklama=""):
    """D013 çekirdeği: tahsilat/ödeme satırlarını tek işlemde yazar.

    `conn` açık gelir; COMMIT çağıranın işidir (POS `pos_satis_olustur` deseni).
    Başarıda (sonuc, None); hatada (None, mesaj). "YASAK:" öneki → 403'lük ihlal.
    """
    sid = db.sirket_id(req)
    if yon not in ("tahsilat", "odeme"):
        return None, "Geçersiz işlem yönü."
    giris = (yon == "tahsilat")
    odemeler = [o for o in (odemeler or []) if o["tip"] in ODEME_TIPLERI and o["tutar"] > 0]
    if not odemeler:
        return None, "En az bir ödeme satırı girin (tutar 0'dan büyük olmalı)."
    for o in odemeler:
        if o["tip"] in ("Cek", "Senet") and not o["vade"]:
            return None, "Çek/senet satırı için vade girin."

    # Hesap doğrulamaları (K1: aktif şirket + aktif kayıt)
    lazim_kasa = any(o["tip"] == "Nakit" for o in odemeler)
    lazim_banka = any(o["tip"] in ("Havale", "Kart") for o in odemeler)
    lazim_term = any(o["tip"] == "Kart" for o in odemeler)
    if lazim_kasa:
        if not kasa_id or not conn.execute(
                "SELECT id FROM kasa WHERE id=? AND aktif=1 AND sirket_id=?",
                (kasa_id, sid)).fetchone():
            return None, "Nakit satırı için geçerli bir kasa seçin."
        if izole_sube(req):  # kasa.py deseni: şubeli kullanıcı yalnız kendi kasası
            k = conn.execute("SELECT sube_id FROM kasa WHERE id=? AND sirket_id=?",
                             (kasa_id, sid)).fetchone()
            if not k or k["sube_id"] != izole_sube(req):
                return None, "YASAK:Bu kasa için yetkiniz yok."
    if lazim_banka:
        if not banka_hesap_id or not conn.execute(
                "SELECT id FROM banka_hesap WHERE id=? AND aktif=1 AND sirket_id=?",
                (banka_hesap_id, sid)).fetchone():
            return None, "Havale/Kart satırı için geçerli bir banka hesabı seçin."
        if izole_sube(req):  # banka.py deseni
            b = conn.execute("SELECT sube_id FROM banka_hesap WHERE id=? AND sirket_id=?",
                             (banka_hesap_id, sid)).fetchone()
            if not b or b["sube_id"] != izole_sube(req):
                return None, "YASAK:Bu banka hesabı için yetkiniz yok."
    term = None
    if lazim_term:
        term = conn.execute("SELECT * FROM pos_terminal WHERE id=? AND sirket_id=? AND aktif=1",
                            (terminal_id, sid)).fetchone() if terminal_id else None
        if not term:
            return None, "Kart satırı için aktif bir POS terminali seçin."
    kom_oran = float(term["komisyon_orani"] or 0) if term else 0.0

    # D012 kur sabitleme deseni (kasa.py/cek_senet.py ile birebir)
    pbs = db.para_birimleri(sid=sid)
    pb = para_birimi if para_birimi in pbs else "TRY"
    kur = None
    if pb != "TRY":
        kur = doviz_kur if (doviz_kur and doviz_kur > 0) else db.guncel_kur(conn, pb, sid)
    oran = kur or 1.0

    bugun = tarih or datetime.date.today().isoformat()
    on_ek = "THS" if giris else "ODM"
    no = db.sonraki_belge_no(conn, "cari_hareket", "belge_no", on_ek, bugun[:4], sid)
    bakiye_once = _bakiye(conn, cari_kart["id"])
    modul = "CariTahsilat" if giris else "CariOdeme"
    belge_tipi = "Tahsilat" if giris else "Ödeme"
    aciklama = (aciklama or "").strip()

    # Çıkış yönü nakit: kasa bakiye kontrolü (kasa.py deseni — ilgili para biriminde)
    if not giris and lazim_kasa:
        toplam_nakit = round(sum(o["tutar"] for o in odemeler if o["tip"] == "Nakit"), 2)
        if kasa._bakiye_doviz(conn, kasa_id).get(pb, 0.0) < toplam_nakit:
            return None, f"Kasa bakiyesi bu işlem için yetersiz ({pb})."

    toplam = toplam_tl = komisyon_toplam = 0.0
    auditler = []  # audit kendi bağlantısını açar → commit SONRASI yazılır (kasa.py deseni)
    for idx, o in enumerate(odemer for odemer in odemeler):
        tutar_tl = round(o["tutar"] * oran, 2)
        toplam = round(toplam + o["tutar"], 2)
        toplam_tl = round(toplam_tl + tutar_tl, 2)
        satir_acik = (f"{cari_kart['unvan']} {belge_tipi.lower()} — {TIP_LABEL[o['tip']]}"
                      + (f" ({aciklama})" if aciklama else ""))
        if o["tip"] == "Nakit":
            hid = kasa.kasa_hareket_olustur(
                conn, kasa_id, bugun, "Nakit Girişi" if giris else "Nakit Çıkışı",
                o["tutar"], satir_acik, no, cari_kart["id"], modul, None,
                req.user["id"], pb, kur, sid)
            muhasebe.fis_uret(conn, "Kasa", hid)
            cari.hareket_ekle(conn, cari_kart["id"], bugun, belge_tipi, no, satir_acik,
                              borc=0.0 if giris else tutar_tl,
                              alacak=tutar_tl if giris else 0.0,
                              ilgili_modul="Kasa", ilgili_kayit_id=hid,
                              created_by=req.user["id"], para_birimi=pb, doviz_kur=kur)
            auditler.append(("kasa_hareket", hid, yon, {"belge_no": no, "tutar": o["tutar"], "pb": pb}))
        elif o["tip"] in ("Havale", "Kart"):
            kom = 0.0
            yazilacak = o["tutar"]
            if o["tip"] == "Kart":  # POS deseni: komisyon düşülmüş NET bankaya
                kom = round(o["tutar"] * kom_oran / 100, 2)
                komisyon_toplam = round(komisyon_toplam + kom, 2)
                yazilacak = round(o["tutar"] - kom, 2)
                satir_acik += f" (terminal: {term['ad']}, komisyon %{kom_oran:g} → {kom:,.2f} {pb})"
            hid = banka.banka_hareket_olustur(
                conn, banka_hesap_id, bugun, "Havale/EFT Girişi" if giris else "Havale/EFT Çıkışı",
                yazilacak, satir_acik, no, cari_kart["id"], modul, None,
                req.user["id"], pb, kur, sid)
            muhasebe.fis_uret(conn, "Banka", hid)
            cari.hareket_ekle(conn, cari_kart["id"], bugun, belge_tipi, no, satir_acik,
                              borc=0.0 if giris else tutar_tl,
                              alacak=tutar_tl if giris else 0.0,
                              ilgili_modul="Banka", ilgili_kayit_id=hid,
                              created_by=req.user["id"], para_birimi=pb, doviz_kur=kur)
            auditler.append(("banka_hareket", hid, yon, {"belge_no": no, "tutar": yazilacak,
                                                        "komisyon": kom, "pb": pb}))
        else:  # Cek / Senet — mevcut cek_senet akışı (kod tekrarı yok)
            tur = "Cek" if o["tip"] == "Cek" else "Senet"
            cek_tip = "Alinan" if giris else "Verilen"
            cek_no = o["no"] or f"{no}-C{idx + 1}"
            cid = cek_senet.cek_olustur(
                conn, req, cek_tip, tur, cek_no, cari_kart["id"], o["banka"], "",
                o["tutar"], pb, kur, bugun, o["vade"], satir_acik)
            auditler.append(("cek_senet", cid, yon, {"belge_no": no, "no": cek_no, "tip": cek_tip}))

    # Avans hesabı: tahsilatta (+) bakiyeyi, ödemede (−) bakiyeyi aşan kısım
    acik = bakiye_once if giris else -bakiye_once
    avans = round(toplam_tl - max(acik, 0.0), 2)
    avans = avans if avans > 0.005 else 0.0
    bakiye_sonra = round(bakiye_once - toplam_tl if giris else bakiye_once + toplam_tl, 2)
    return {"belge_no": no, "toplam": toplam, "toplam_tl": toplam_tl,
            "komisyon": komisyon_toplam, "para_birimi": pb, "kur": kur,
            "bakiye_once": bakiye_once, "bakiye_sonra": bakiye_sonra,
            "avans": avans, "satir": len(odemeler), "auditler": auditler}, None


def _cari_getir(conn, cid, sid):
    """K1: cari aktif şirketteyse dict, başka şirketteyse 'YASAK', yoksa None."""
    r = conn.execute("SELECT * FROM cari_kart WHERE id=? AND sirket_id=?", (cid, sid)).fetchone()
    if r:
        return dict(r), None
    else:
        var = conn.execute("SELECT id FROM cari_kart WHERE id=?", (cid,)).fetchone()
        if var:
            return None, "YASAK"
        return None, "YOK"


def _sunum(req, cid, yon):
    giris = (yon == "tahsilat")
    conn = db.get_conn()
    sid = db.sirket_id(req)
    cari_kart, sorun = _cari_getir(conn, cid, sid)
    if sorun == "YASAK":
        conn.close()
        return Response("Bu cari için yetkiniz yok.", "403 Forbidden")
    if not cari_kart:
        conn.close()
        flash(req, "Cari bulunamadı.", "danger")
        return redirect("/cari")

    if req.method == "POST":
        odemeler = _odemeler_from_form(req)
        sonuc, hata = tahsilat_odeme_olustur(
            conn, req, cari_kart, yon, odemeler,
            kasa_id=_i(req.form.get("kasa_id")),
            banka_hesap_id=_i(req.form.get("banka_hesap_id")),
            terminal_id=_i(req.form.get("terminal_id")),
            tarih=(req.form.get("tarih") or "").strip() or None,
            para_birimi=req.form.get("para_birimi"),
            doviz_kur=_f(req.form.get("doviz_kur"), None),
            aciklama=req.form.get("aciklama") or "")
        if hata:
            conn.close()
            if hata.startswith("YASAK:"):
                return Response(hata[6:], "403 Forbidden")
            flash(req, hata, "danger")
            return redirect(f"/cari/{cid}/{yon}")
        conn.commit()
        for tablo, kayit_id, islem, detay in sonuc["auditler"]:
            audit(req, tablo, kayit_id, islem, detay)
        conn.close()
        etiket = "Tahsilat" if giris else "Ödeme"
        flash(req, f"{etiket} kaydedildi: {sonuc['belge_no']} — "
                   f"{sonuc['toplam']:,.2f} {sonuc['para_birimi']} "
                   f"({sonuc['satir']} satır, kalan bakiye {sonuc['bakiye_sonra']:,.2f} ₺)", "ok")
        if sonuc["avans"] > 0:
            flash(req, f"Bakiyeyi {sonuc['avans']:,.2f} ₺ aşıyorsunuz — "
                       "avans olarak işlenecek", "warn")
        return redirect(f"/cari/{cid}/ekstre")

    bakiye = _bakiye(conn, cid)
    kasalar = kasa._kasalar(conn, izole_sube(req), sid)
    bankalar = banka._hesaplar(conn, izole_sube(req), sid)
    terminaller = pos._terminaller(conn, sid)
    conn.close()
    return render_template("cari/tahsilat_odeme.html", cari=cari_kart, bakiye=bakiye, yon=yon,
                           giris=giris, kasalar=kasalar, bankalar=bankalar,
                           terminaller=terminaller, odeme_tipleri=ODEME_TIPLERI,
                           tip_label=TIP_LABEL, para_birimleri=db.para_birimleri(sid=sid),
                           cek_tip="Alınan" if giris else "Verilen",
                           bugun=datetime.date.today().isoformat())


@route(r"/cari/(?P<cid>\d+)/tahsilat", methods=("GET", "POST"), roles=TAHSILAT_ROLLERI)
def cari_tahsilat(req, cid):
    return _sunum(req, int(cid), "tahsilat")


@route(r"/cari/(?P<cid>\d+)/odeme", methods=("GET", "POST"), roles=ODEME_ROLLERI)
def cari_odeme(req, cid):
    return _sunum(req, int(cid), "odeme")


def register():
    pass
