# -*- coding: utf-8 -*-
"""İrsaliye modülü (Faz 2 — Satış Döngüsü, zincirin 3. halkası).

Belge zinciri: Teklif → Sipariş → İrsaliye → Fatura.
- tip: 'Satis' = müşteriye sevk (stok çıkışı), 'Alis' = tedarikçiden mal kabul (giriş),
  'Transfer' = depo → depo (kaynak çıkış + hedef giriş).
- K8: irsaliye.kaynak_siparis_id → siparis.id (nullable); onaylı siparişten tek tıkla üretim.
- K10: yalnız 'Onaylandı' siparişten irsaliye üretilebilir.
- K11: stok düşümü/girişi yalnız belgedeki depo bazında; siparişin `teslim_edilen`'i
  satır bazında artar, başlık durumu tüm satırlardan türetilir (tümü tam → Tamamlandı,
  herhangi biri >0 → Kısmi).
- Onay (Taslak→Onaylandı) yetki bazlıdır (Admin/Muhasebe); stok hareketi + rezervasyon
  serbest bırakma + teslim güncelleme TEK işlemde ve önce tüm kontroller geçerse yapılır.
- İptal, onaylı irsaliyeyi ters yönlü hareketle geri alır.
"""
import datetime
import urllib.parse

import db
import stok
import ekler
import cari
import muhasebe
from config import PARA_BIRIMLERI
from core import route, render_template, redirect, flash, audit, notify, izole_sube, sube_koruma, Response, kdv_ayikla, yazdir_belge

IRSALIYE_WRITE = ("Admin", "Muhasebe", "Satis")
IRSALIYE_ONAY = ("Admin", "Muhasebe")
TIPLER = ["Satis", "Alis", "Transfer"]
TIP_LABEL = {"Satis": "Satış İrsaliyesi", "Alis": "Alış İrsaliyesi", "Transfer": "Transfer İrsaliyesi"}
TIP_ON_EK = {"Satis": "IRS", "Alis": "IRA", "Transfer": "IRT"}
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
            r["gorunen_ad"] = (r.get("goruntu_adi") or "").strip() or s.get("ad", "?")
            r["birim"] = r.get("birim") or s.get("birim") or "Adet"
            r["varyant_ad"] = ""
            if r.get("varyant_id"):
                v = conn.execute("SELECT ad FROM stok_varyant WHERE id=?", (r["varyant_id"],)).fetchone()
                r["varyant_ad"] = v["ad"] if v else ""
        out.append(r)
    return out


def _irsaliye_detay(conn, iid, sid=None):
    where, params = "i.id=?", [int(iid)]
    if sid is not None:
        where += " AND i.sirket_id=?"
        params.append(sid)
    r = conn.execute(
        "SELECT i.*, c.unvan AS cari_unvan, c.kod AS cari_kod, c.il AS cari_il, "
        "d.kod AS depo_kod, d.ad AS depo_ad, hd.kod AS hedef_kod, hd.ad AS hedef_ad, "
        "sb.ad AS sube_ad, s.siparis_no AS kaynak_siparis_no "
        "FROM irsaliye i LEFT JOIN cari_kart c ON c.id=i.cari_id "
        "LEFT JOIN depo d ON d.id=i.depo_id LEFT JOIN depo hd ON hd.id=i.hedef_depo_id "
        "LEFT JOIN sube sb ON sb.id=i.sube_id LEFT JOIN siparis s ON s.id=i.kaynak_siparis_id "
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
        "FROM irsaliye_kalem k LEFT JOIN stok_kart st ON st.id=k.stok_id "
        "LEFT JOIN stok_varyant v ON v.id=k.varyant_id WHERE k.irsaliye_id=? ORDER BY k.id",
        (r["id"],),
    ).fetchall()
    return r, kalemler


def _siparis_kontrol(conn, siparis_id, sid=None):
    """K10 — yalnız Onaylandı siparişten irsaliye üretilebilir."""
    where, params = "id=?", [siparis_id]
    if sid is not None:
        where += " AND sirket_id=?"
        params.append(sid)
    s = conn.execute(f"SELECT * FROM siparis WHERE {where}", params).fetchone()
    if not s:
        return "Kaynak sipariş bulunamadı."
    if s["durum"] != "Onaylandı":
        return f"Yalnızca 'Onaylandı' durumundaki siparişten irsaliye oluşturulabilir (sipariş: {s['durum']})."
    return None


def _siparis_teslim_kontrol(conn, siparis_id, satirlar, mevcut_id=None):
    """Aşırı teslimat (over-delivery) koruması.

    Siparişten üretilen irsaliyede, aynı stok+varyant satırlarının toplamı ilgili
    sipariş satırının kalanını aşamaz; siparişte bulunmayan stok/varyant da kabul
    edilmez. Kalan hesabına, aynı siparişten açılmış **diğer Taslak irsaliyelerin**
    bekleyen miktarları da dahil edilir (henüz `teslim_edilen`'e yansımadığı için).
    Hata listesi döner (boş = geçerli).
    """
    kalemler = conn.execute(
        "SELECT stok_id, varyant_id, miktar, teslim_edilen, kalan_iptal "
        "FROM siparis_kalem WHERE siparis_id=?",
        (siparis_id,),
    ).fetchall()
    kalan = {}
    for k in kalemler:
        kalan[(k["stok_id"], k["varyant_id"] or 0)] = \
            (k["miktar"] or 0) - (k["teslim_edilen"] or 0) - (k["kalan_iptal"] or 0)

    # Aynı siparişten açılmış diğer Taslak irsaliyelerin bekleyen miktarını düş
    if mevcut_id:
        bekleyen = conn.execute(
            "SELECT k.stok_id, k.varyant_id, SUM(k.miktar) AS m FROM irsaliye_kalem k "
            "JOIN irsaliye i ON i.id=k.irsaliye_id "
            "WHERE i.kaynak_siparis_id=? AND i.durum='Taslak' AND i.id!=? "
            "GROUP BY k.stok_id, k.varyant_id", (siparis_id, mevcut_id),
        ).fetchall()
    else:
        bekleyen = conn.execute(
            "SELECT k.stok_id, k.varyant_id, SUM(k.miktar) AS m FROM irsaliye_kalem k "
            "JOIN irsaliye i ON i.id=k.irsaliye_id "
            "WHERE i.kaynak_siparis_id=? AND i.durum='Taslak' "
            "GROUP BY k.stok_id, k.varyant_id", (siparis_id,),
        ).fetchall()
    for b in bekleyen:
        kalan[(b["stok_id"], b["varyant_id"] or 0)] = kalan.get((b["stok_id"], b["varyant_id"] or 0), 0) - (b["m"] or 0)

    talep = {}
    for s in satirlar:
        if not s["stok_id"]:   # manuel (serbest metin) satır — teslim kontrolüne girmez
            continue
        key = (s["stok_id"], s["varyant_id"] or 0)
        talep[key] = talep.get(key, 0) + s["miktar"]

    hatalar = []
    for key, m in talep.items():
        s = conn.execute("SELECT kod FROM stok_kart WHERE id=?", (key[0],)).fetchone()
        kod = s["kod"] if s else f"#{key[0]}"
        if key not in kalan:
            hatalar.append(f"{kod}: bu ürün siparişte yok")
        elif m > kalan[key] + 1e-9:
            hatalar.append(f"{kod}: sipariş kalanı {kalan[key]:g}, istenen {m:g}")
    return hatalar


def _cari_uygula_irsaliye(conn, req, irs, yon):
    """F1 — irsaliyenin mali etkisi (cari hareket) tek işlemde yaz/geri al.

    yon=+1 → Satış→BORÇ, Alış→ALACAK (ilgili_modul='Irsaliye');
    yon=-1 → irsaliyenin kendi cari hareketini sil (iptal → net sıfır).
    Transfer'de cari yoktur → mali etki üretilmez."""
    if irs["tip"] == "Transfer" or not irs["cari_id"]:
        return
    if yon == -1:
        conn.execute(
            "DELETE FROM cari_hareket WHERE ilgili_modul='Irsaliye' AND ilgili_kayit_id=?",
            (irs["id"],),
        )
        return
    # D007 madde 5 — döviz: cari harekette borç/alacak DAİMA TL karşılığı (K18);
    # para_birimi + doviz_kur yalnızca izleme (fatura _cari_uygula deseniyle aynı).
    pb = irs.get("para_birimi") or "TRY"
    kur = irs.get("doviz_kur") or 1.0
    tutar = round((irs["genel_toplam"] or 0.0) * kur, 2)
    if irs["tip"] == "Satis":
        cari.hareket_ekle(conn, irs["cari_id"], irs["tarih"], "Satış İrsaliyesi",
                          irs["irsaliye_no"], irs.get("aciklama"),
                          borc=tutar, alacak=0.0,
                          ilgili_modul="Irsaliye", ilgili_kayit_id=irs["id"],
                          created_by=req.user["id"], para_birimi=pb, doviz_kur=kur)
    else:
        cari.hareket_ekle(conn, irs["cari_id"], irs["tarih"], "Alış İrsaliyesi",
                          irs["irsaliye_no"], irs.get("aciklama"),
                          borc=0.0, alacak=tutar,
                          ilgili_modul="Irsaliye", ilgili_kayit_id=irs["id"],
                          created_by=req.user["id"], para_birimi=pb, doviz_kur=kur)


def _siparis_durum_turet(conn, siparis_id):
    """K11 — başlık durumunu tüm satırların teslim oranından türet.

    B3: kalan_iptal (kısmi teslimatın bilinçli kapatılması) teslim edilmiş gibi sayılır.
    """
    kalemler = conn.execute(
        "SELECT miktar, teslim_edilen, kalan_iptal FROM siparis_kalem WHERE siparis_id=?",
        (siparis_id,)).fetchall()
    if not kalemler:
        return "Onaylandı"
    hepsi_tam = all((k["teslim_edilen"] or 0) + (k["kalan_iptal"] or 0) >= k["miktar"] - 1e-9
                    for k in kalemler)
    herhangi = any((k["teslim_edilen"] or 0) + (k["kalan_iptal"] or 0) > 0 for k in kalemler)
    if hepsi_tam:
        return "Tamamlandı"
    if herhangi:
        return "Kısmi"
    return "Onaylandı"


def _stok_kontrol_ve_uygula(conn, req, irs, kalemler, yon):
    """K11 — depo bazlı stok kontrolü + hareket + rezervasyon + teslim güncelleme.

    yon=+1 → onayla (uygula); yon=-1 → iptal (geri al). Hatalar listesi döner;
    boş liste = başarı. Herhangi bir hata varsa HİÇBİR kayıt yazılmaz.
    """
    hatalar = []
    depo_id = irs["depo_id"]
    # ---- önce kontroller (D007 madde 6: eksi stok izni — yetersiz stok onayı BLOKE ETMEZ) ----
    # Kullanıcı isteği: elde stok yoksa bile işlem devam etsin, bakiye eksiye düşsün.
    # Bu yüzden kontroller yalnızca log'a UYARI yazar; `hatalar` boş kalır.
    if yon == 1:
        if irs["tip"] == "Satis":
            for k in kalemler:
                if not k["stok_id"]:   # manuel satır stok kontrolüne girmez
                    continue
                if irs["kaynak_siparis_id"]:
                    sev = conn.execute(
                        "SELECT rezerve FROM stok_seviye WHERE stok_id=? AND varyant_id=? AND depo_id=?",
                        (k["stok_id"], k["varyant_id"], depo_id),
                    ).fetchone()
                    rezerve = (sev["rezerve"] or 0) if sev else 0
                    if rezerve < k["miktar"] - 1e-9:
                        print(f"[UYARI] eksi stok: {k['stok_kod']} rezervasyon {rezerve:g} < "
                              f"{k['miktar']:g} (eksiye düşmesine izin verildi)", flush=True)
                else:
                    sev = conn.execute(
                        "SELECT miktar, rezerve FROM stok_seviye WHERE stok_id=? AND varyant_id=? AND depo_id=?",
                        (k["stok_id"], k["varyant_id"], depo_id),
                    ).fetchone()
                    eldeki = ((sev["miktar"] or 0) - (sev["rezerve"] or 0)) if sev else 0
                    if eldeki < k["miktar"] - 1e-9:
                        print(f"[UYARI] eksi stok: {k['stok_kod']} eldeki {eldeki:g} < "
                              f"{k['miktar']:g} (eksiye düşmesine izin verildi)", flush=True)
        elif irs["tip"] == "Transfer":
            for k in kalemler:
                if not k["stok_id"]:   # manuel satır stok kontrolüne girmez
                    continue
                sev = conn.execute(
                    "SELECT miktar, rezerve FROM stok_seviye WHERE stok_id=? AND varyant_id=? AND depo_id=?",
                    (k["stok_id"], k["varyant_id"], depo_id),
                ).fetchone()
                eldeki = ((sev["miktar"] or 0) - (sev["rezerve"] or 0)) if sev else 0
                if eldeki < k["miktar"] - 1e-9:
                    print(f"[UYARI] eksi stok: {k['stok_kod']} kaynak depo eldeki {eldeki:g} < "
                          f"{k['miktar']:g} (eksiye düşmesine izin verildi)", flush=True)
    if hatalar:
        return hatalar

    # ---- uygula ----
    tarih = irs["tarih"]
    belge_no = irs["irsaliye_no"]
    iid = irs["id"]
    for k in kalemler:
        if not k["stok_id"]:   # manuel satır stok hareketi/rezervasyon üretmez
            continue
        if irs["tip"] == "Satis":
            isaretli = -k["miktar"] * yon
            islem_tipi = "İrsaliye Çıkışı" if yon == 1 else "İrsaliye İptali (Geri Alış)"
            stok._hareket_olustur(conn, req, k["stok_id"], k["varyant_id"], depo_id, islem_tipi,
                                  isaretli, birim_maliyet=None, aciklama=belge_no, belge_no=belge_no,
                                  ilgili_modul="Irsaliye", ilgili_kayit_id=iid, tarih=tarih)
            if irs["kaynak_siparis_id"]:
                conn.execute(
                    "UPDATE stok_seviye SET rezerve = MAX(rezerve - ?, 0) "
                    "WHERE stok_id=? AND varyant_id=? AND depo_id=?",
                    (k["miktar"] * yon, k["stok_id"], k["varyant_id"], depo_id),
                )
        elif irs["tip"] == "Alis":
            isaretli = k["miktar"] * yon
            islem_tipi = "İrsaliye Girişi" if yon == 1 else "İrsaliye İptali (Geri Veriş)"
            stok._hareket_olustur(conn, req, k["stok_id"], k["varyant_id"], depo_id, islem_tipi,
                                  isaretli, birim_maliyet=None, aciklama=belge_no, belge_no=belge_no,
                                  ilgili_modul="Irsaliye", ilgili_kayit_id=iid, tarih=tarih)
        else:  # Transfer
            stok._hareket_olustur(conn, req, k["stok_id"], k["varyant_id"], depo_id,
                                  "Depolar Arası Transfer", -k["miktar"] * yon,
                                  birim_maliyet=None, aciklama=belge_no, belge_no=belge_no,
                                  ilgili_modul="Irsaliye", ilgili_kayit_id=iid, tarih=tarih)
            stok._hareket_olustur(conn, req, k["stok_id"], k["varyant_id"], irs["hedef_depo_id"],
                                  "Depolar Arası Transfer", k["miktar"] * yon,
                                  birim_maliyet=None, aciklama=belge_no, belge_no=belge_no,
                                  ilgili_modul="Irsaliye", ilgili_kayit_id=iid, tarih=tarih)

    # ---- sipariş teslim güncelleme + durum türetme ----
    if irs["kaynak_siparis_id"]:
        for k in kalemler:
            if not k["stok_id"]:   # manuel satır sipariş teslim miktarını etkilemez
                continue
            conn.execute(
                "UPDATE siparis_kalem SET teslim_edilen = MAX(0, teslim_edilen + ?) "
                "WHERE siparis_id=? AND stok_id=? AND varyant_id=?",
                (k["miktar"] * yon, irs["kaynak_siparis_id"], k["stok_id"], k["varyant_id"]),
            )
        yeni_durum = _siparis_durum_turet(conn, irs["kaynak_siparis_id"])
        conn.execute("UPDATE siparis SET durum=? WHERE id=?", (yeni_durum, irs["kaynak_siparis_id"]))
    return []


# --------------------------------------------------------------------------
# Rotalar
# --------------------------------------------------------------------------
@route(r"/irsaliye", roles=())
def irsaliye_liste(req):
    conn = db.get_conn()
    q = req.q("q").strip()
    durum = req.q("durum")
    tip = req.q("tip") if req.q("tip") in TIPLER else ""
    faturasiz = req.q("faturasiz") == "1"
    where, params = ["i.sirket_id = ?"], [db.sirket_id(req)]
    if q:
        where.append("(i.irsaliye_no LIKE ? OR c.unvan LIKE ? OR c.kod LIKE ?)")
        like = f"%{q}%"
        params += [like, like, like]
    if faturasiz:
        # K14 — onaylı, Transfer olmayan ve onaylı faturası bulunmayan irsaliyeler
        where.append("i.durum='Onaylandı' AND i.tip != 'Transfer' "
                     "AND NOT EXISTS (SELECT 1 FROM fatura f WHERE f.kaynak_irsaliye_id=i.id "
                     "AND f.durum='Onaylandı')")
    elif durum in DURUMLAR:
        where.append("i.durum=?")
        params.append(durum)
    if tip:
        where.append("i.tip=?")
        params.append(tip)
    if izole_sube(req):
        where.append("i.sube_id=?")
        params.append(izole_sube(req))
    w = " AND ".join(where)
    rows = conn.execute(
        f"SELECT i.*, c.unvan AS cari_unvan, c.kod AS cari_kod, "
        f"(SELECT COUNT(*) FROM irsaliye_kalem k WHERE k.irsaliye_id=i.id) AS kalem_sayisi, "
        f"(SELECT f.fatura_no FROM fatura f WHERE f.kaynak_irsaliye_id=i.id "
        f" AND f.durum='Onaylandı' LIMIT 1) AS fatura_no "
        f"FROM irsaliye i LEFT JOIN cari_kart c ON c.id=i.cari_id WHERE {w} ORDER BY i.id DESC",
        params,
    ).fetchall()
    ozet = {d: conn.execute("SELECT COUNT(*) c FROM irsaliye WHERE durum=? AND sirket_id=?",
                             (d, db.sirket_id(req))).fetchone()["c"]
            for d in DURUMLAR}
    ozet["faturasiz"] = conn.execute(
        "SELECT COUNT(*) c FROM irsaliye i WHERE i.durum='Onaylandı' AND i.tip != 'Transfer' "
        "AND i.sirket_id=? "
        "AND NOT EXISTS (SELECT 1 FROM fatura f WHERE f.kaynak_irsaliye_id=i.id AND f.durum='Onaylandı')",
        (db.sirket_id(req),),
    ).fetchone()["c"]
    conn.close()
    return render_template("irsaliye/liste.html", rows=rows, durumlar=DURUMLAR, tipler=TIPLER,
                           tip_label=TIP_LABEL, ozet=ozet,
                           filtro={"q": q, "durum": durum, "tip": tip, "faturasiz": faturasiz})


@route(r"/irsaliye/yeni", methods=("GET", "POST"), roles=IRSALIYE_WRITE)
def irsaliye_yeni(req):
    conn = db.get_conn()
    if req.method == "POST":
        return _form_post(req, conn, None)

    kaynak = _i(req.q("kaynak_siparis"))
    satirlar, kaynak_siparis_id = [], None
    siparis_row = None
    tip = "Satis"
    depo_id = None
    if kaynak:
        hata = _siparis_kontrol(conn, kaynak, db.sirket_id(req))
        if hata:
            conn.close()
            flash(req, hata, "danger")
            return redirect(f"/siparis/{kaynak}")
        siparis_row = dict(conn.execute("SELECT * FROM siparis WHERE id=? AND sirket_id=?",
                                        (kaynak, db.sirket_id(req))).fetchone())
        kaynak_siparis_id = kaynak
        tip = "Satis" if siparis_row["tip"] == "Musteri" else "Alis"
        depo_id = siparis_row["depo_id"]
        kalemler = conn.execute(
            "SELECT k.*, COALESCE(k.miktar - k.teslim_edilen, 0) AS kalan "
            "FROM siparis_kalem k WHERE k.siparis_id=? ORDER BY k.id", (kaynak,),
        ).fetchall()
        satirlar = [{"stok_id": k["stok_id"], "varyant_id": k["varyant_id"],
                     "miktar": max(k["miktar"] - k["teslim_edilen"], 0),
                     "birim_fiyat": k["birim_fiyat"], "iskonto_orani": k["iskonto_orani"],
                     "kdv_orani": k["kdv_orani"], "birim": k["birim"],
                     "goruntu_adi": k["goruntu_adi"],
                     "manuel_ad": (k["aciklama"] or "") if not k["stok_id"] else ""}
                    for k in kalemler]
        satirlar = [s for s in satirlar if s["miktar"] > 0]

    cariler = _cariler(conn, tip, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    depolar = _depolar(conn, db.sirket_id(req))
    ilk_depo = depolar[0]["id"] if depolar else None
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(x) for x in satirlar]) if satirlar else None
    cari_id = None
    cari_etiket, cari_iskonto = _cari_secim(cariler, cari_id)
    conn.close()
    return render_template(
        "irsaliye/form.html", irsaliye=None, satirlar=satirlar, cariler=cariler, stoklar=stoklar,
        depolar=depolar, toplamlar=toplamlar, tip=tip, depo_id=depo_id or ilk_depo,
        hedef_depo_id=None, cari_id=cari_id, cari_etiket=cari_etiket, cari_iskonto=cari_iskonto, birimler=db.birimler(sid=db.sirket_id(req)),
        para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
        kaynak_siparis_id=kaynak_siparis_id, kaynak_siparis=siparis_row,
        kdv_dahil=0, bugun=datetime.date.today().isoformat())


@route(r"/irsaliye/(?P<iid>\d+)", roles=())
def irsaliye_detay(req, iid):
    conn = db.get_conn()
    sonuc = _irsaliye_detay(conn, iid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "İrsaliye bulunamadı.", "danger")
        return redirect("/irsaliye")
    r, kalemler = sonuc
    if not sube_koruma(req, r["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    kalemler = [dict(k) for k in kalemler]
    if r["tip"] == "Satis" and r["depo_id"]:
        for k in kalemler:
            if not k["stok_id"]:   # manuel satır — eldeki/rezerve göstermez
                continue
            sev = conn.execute(
                "SELECT miktar, rezerve FROM stok_seviye WHERE stok_id=? AND varyant_id=? AND depo_id=?",
                (k["stok_id"], k["varyant_id"], r["depo_id"]),
            ).fetchone()
            k["eldeki"] = (sev["miktar"] or 0) if sev else 0
            k["rezerve"] = (sev["rezerve"] or 0) if sev else 0
    loglar = conn.execute("SELECT * FROM audit_log WHERE tablo='irsaliye' AND kayit_id=? ORDER BY id DESC",
                          (r["id"],)).fetchall()
    faturalar = conn.execute(
        "SELECT id, fatura_no, durum, genel_toplam FROM fatura "
        "WHERE kaynak_irsaliye_id=? ORDER BY id", (r["id"],),
    ).fetchall()
    onayli_fatura = next((f for f in faturalar if f["durum"] == "Onaylandı"), None)
    faturalandi_no = onayli_fatura["fatura_no"] if onayli_fatura else None
    faturalandi_id = onayli_fatura["id"] if onayli_fatura else None
    ekler_list = ekler.ekler_for(conn, "Irsaliye", r["id"])
    ek_upload = req.user["rol"] in ekler.EK_WRITE
    e_belgeler = conn.execute(
        "SELECT id, belge_no, tur, durum FROM e_belge WHERE kaynak_irsaliye_id=? ORDER BY id",
        (r["id"],)).fetchall()
    conn.close()
    return render_template("irsaliye/detay.html", irsaliye=r, kalemler=kalemler, loglar=loglar,
                           faturalar=faturalar, faturalandi_no=faturalandi_no,
                           faturalandi_id=faturalandi_id, tip_label=TIP_LABEL,
                           ekler=ekler_list, ek_upload=ek_upload, ek_modul="Irsaliye",
                           ek_kayit_id=r["id"], ek_geri=f"/irsaliye/{r['id']}",
                           e_belgeler=e_belgeler)


@route(r"/irsaliye/(?P<iid>\d+)/duzenle", methods=("GET", "POST"), roles=IRSALIYE_WRITE)
def irsaliye_duzenle(req, iid):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM irsaliye WHERE id=? AND sirket_id=?",
                     (int(iid), db.sirket_id(req))).fetchone()
    if not r:
        conn.close()
        return redirect("/irsaliye")
    if r["durum"] != "Taslak":
        conn.close()
        flash(req, "Yalnızca 'Taslak' durumundaki irsaliyeler düzenlenebilir.", "danger")
        return redirect(f"/irsaliye/{r['id']}")
    if req.method == "POST":
        return _form_post(req, conn, r)

    kalemler = conn.execute("SELECT * FROM irsaliye_kalem WHERE irsaliye_id=? ORDER BY id",
                            (r["id"],)).fetchall()
    satirlar = [{"stok_id": k["stok_id"], "varyant_id": k["varyant_id"], "miktar": k["miktar"],
                 "birim_fiyat": k["birim_fiyat"], "iskonto_orani": k["iskonto_orani"],
                 "kdv_orani": k["kdv_orani"], "kdv_dahil": k["kdv_dahil"],
                 "birim": k["birim"], "goruntu_adi": k["goruntu_adi"],
                 "manuel_ad": (k["aciklama"] or "") if not k["stok_id"] else ""}
                for k in kalemler]
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(x) for x in satirlar])
    cariler = _cariler(conn, r["tip"], db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    depolar = _depolar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, r["cari_id"])
    conn.close()
    return render_template("irsaliye/form.html", irsaliye=r, satirlar=satirlar, cariler=cariler,
                           stoklar=stoklar, depolar=depolar, toplamlar=toplamlar, tip=r["tip"],
                           depo_id=r["depo_id"], hedef_depo_id=r["hedef_depo_id"],
                           cari_id=r["cari_id"], cari_etiket=cari_etiket, cari_iskonto=cari_iskonto, birimler=db.birimler(sid=db.sirket_id(req)),
                           para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           kaynak_siparis_id=r["kaynak_siparis_id"], kaynak_siparis=None,
                           kdv_dahil=(r["kdv_dahil"] or 0),
                           bugun=datetime.date.today().isoformat())


@route(r"/irsaliye/(?P<iid>\d+)/sil", methods=("POST",), roles=IRSALIYE_WRITE)
def irsaliye_sil(req, iid):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM irsaliye WHERE id=? AND sirket_id=?",
                     (int(iid), db.sirket_id(req))).fetchone()
    if not r:
        conn.close()
        return redirect("/irsaliye")
    if not sube_koruma(req, r["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    if r["durum"] != "Taslak":
        conn.close()
        flash(req, "Yalnızca 'Taslak' irsaliyeler silinebilir (onaylı kayıt iptal edilmelidir).", "danger")
        return redirect(f"/irsaliye/{r['id']}")
    audit(req, "irsaliye", r["id"], "sil", {"irsaliye_no": r["irsaliye_no"], "tip": r["tip"]})
    ekler.ek_temizle(conn, "Irsaliye", r["id"])
    db.bildirim_sil(conn, "irsaliye", r["id"])
    conn.execute("DELETE FROM irsaliye_kalem WHERE irsaliye_id=?", (r["id"],))
    conn.execute("DELETE FROM irsaliye WHERE id=?", (r["id"],))
    conn.commit()
    conn.close()
    flash(req, "İrsaliye silindi.", "ok")
    return redirect("/irsaliye")


def _form_post(req, conn, mevcut):
    tip = req.form.get("tip") if req.form.get("tip") in TIPLER else "Satis"
    cari_id = _i(req.form.get("cari_id"))
    depo_id = _i(req.form.get("depo_id"))
    hedef_depo_id = _i(req.form.get("hedef_depo_id"))
    tarih = req.form.get("tarih") or datetime.date.today().isoformat()
    aciklama = (req.form.get("aciklama") or "").strip()
    kaynak_siparis_id = _i(req.form.get("kaynak_siparis"))
    if mevcut:
        kaynak_siparis_id = mevcut["kaynak_siparis_id"]
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else 0
    # D007 madde 5 — irsaliye döviz: para birimi + kur (fatura deseniyle aynı).
    para_birimi = req.form.get("para_birimi") if req.form.get("para_birimi") in db.para_birimleri(sid=db.sirket_id(req)) else "TRY"
    doviz_kur = _f(req.form.get("doviz_kur"), None)
    if para_birimi == "TRY":
        doviz_kur = 1.0
    elif not doviz_kur or doviz_kur <= 0:
        doviz_kur = db.guncel_kur(conn, para_birimi, db.sirket_id(req))
    satirlar = _satirlar_from_form(req, kdv_dahil)

    sil = req.form.get("sil")
    if sil is not None:
        idx = int(sil)
        if 0 <= idx < len(satirlar):
            del satirlar[idx]
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)

    if req.form.get("tip_degistir"):
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)

    action = req.form.get("action")
    if action == "ekle":
        sid = _i(req.form.get("stok_sec"))
        if sid:
            s = conn.execute("SELECT * FROM stok_kart WHERE id=? AND sirket_id=?",
                             (sid, db.sirket_id(req))).fetchone()
            if s:
                bf = s["alis_fiyat"] if tip == "Alis" else s["satis_fiyat"]
                isk = _iskonto_default(conn, s, cari_id, db.sirket_id(req))
                satirlar.append({"stok_id": sid, "varyant_id": 0, "miktar": 1, "birim_fiyat": bf,
                                 "iskonto_orani": isk, "kdv_orani": s["kdv_orani"],
                                 "manuel_ad": ""})
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    if action == "ekle_manuel":
        ad = (req.form.get("manuel_ad") or "").strip()
        miktar = _f(req.form.get("manuel_miktar"), 1)
        bf = _f(req.form.get("manuel_birim_fiyat"))
        isk = _f(req.form.get("manuel_iskonto"))
        kdv = _f(req.form.get("manuel_kdv"), 20)
        if tip == "Transfer":
            flash(req, "Transfer irsaliyesinde manuel satır kullanılamaz.", "danger")
        elif ad and miktar > 0:
            satirlar.append({"stok_id": None, "varyant_id": 0, "miktar": miktar,
                             "birim_fiyat": bf, "iskonto_orani": isk,
                             "kdv_orani": kdv, "manuel_ad": ad})
        else:
            flash(req, "Manuel satır için açıklama ve miktar girin.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    if action == "barkod":
        barkod = (req.form.get("barkod_sec") or "").strip()
        if barkod:
            sonuc = stok.barkod_bul(conn, barkod, db.sirket_id(req))
            if sonuc:
                kart = sonuc["kart"]
                bf = kart["alis_fiyat"] if tip == "Alis" else kart["satis_fiyat"]
                isk = _iskonto_default(conn, kart, cari_id, db.sirket_id(req))
                satirlar.append({"stok_id": sonuc["stok_id"], "varyant_id": sonuc["varyant_id"],
                                 "miktar": 1, "birim_fiyat": bf, "iskonto_orani": isk,
                                 "kdv_orani": kart["kdv_orani"]})
            else:
                flash(req, f"Barkod bulunamadı: {barkod}", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)

    # --- kaydet ---
    if tip != "Transfer" and not cari_id:
        flash(req, "Cari seçimi zorunludur.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    if not depo_id:
        flash(req, "Depo seçimi zorunludur.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    if tip == "Transfer" and (not hedef_depo_id or hedef_depo_id == depo_id):
        flash(req, "Transfer için farklı bir hedef depo seçin.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    if kaynak_siparis_id:
        hata = _siparis_kontrol(conn, kaynak_siparis_id, db.sirket_id(req))
        if hata:
            flash(req, hata, "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                                tarih, aciklama, kaynak_siparis_id)
    gecerli = [s for s in satirlar if (s["stok_id"] or s.get("manuel_ad")) and s["miktar"] > 0]
    if not gecerli:
        flash(req, "En az bir geçerli satır ekleyin.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    # İstek 3 — çapraz şirket hedef ID koruması
    if tip != "Transfer" and not conn.execute(
            "SELECT id FROM cari_kart WHERE id=? AND sirket_id=?",
            (cari_id, db.sirket_id(req))).fetchone():
        flash(req, "Geçersiz cari seçimi (başka şirkete ait).", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    for _d in (depo_id, hedef_depo_id):
        if _d and not conn.execute("SELECT id FROM depo WHERE id=? AND sirket_id=?",
                                   (_d, db.sirket_id(req))).fetchone():
            flash(req, "Geçersiz depo seçimi (başka şirkete ait).", "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                                tarih, aciklama, kaynak_siparis_id)
    _sidler = {s["stok_id"] for s in gecerli if s["stok_id"]}
    if _sidler:
        _ph = ",".join("?" * len(_sidler))
        _izinli = {r["id"] for r in conn.execute(
            f"SELECT id FROM stok_kart WHERE id IN ({_ph}) AND sirket_id=?",
            tuple(_sidler) + (db.sirket_id(req),)).fetchall()}
        if _sidler - _izinli:
            flash(req, "Geçersiz stok seçimi (başka şirkete ait).", "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                                tarih, aciklama, kaynak_siparis_id)
    if tip == "Transfer" and any(not s["stok_id"] for s in gecerli):
        flash(req, "Transfer irsaliyesinde manuel (stoğa bağlı olmayan) satır kullanılamaz.", "danger")
        return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                            tarih, aciklama, kaynak_siparis_id)
    if kaynak_siparis_id:
        teslim_hata = _siparis_teslim_kontrol(conn, kaynak_siparis_id, gecerli,
                                              mevcut_id=mevcut["id"] if mevcut else None)
        if teslim_hata:
            flash(req, "Teslimat kontrolü: " + " · ".join(teslim_hata), "danger")
            return _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                                tarih, aciklama, kaynak_siparis_id)
    top = _toplamlar(gecerli)

    islem = None
    if mevcut:
        conn.execute(
            "UPDATE irsaliye SET tip=?, cari_id=?, depo_id=?, hedef_depo_id=?, tarih=?, aciklama=?, "
            "para_birimi=?, doviz_kur=?, ara_toplam=?, iskonto_toplam=?, kdv_toplam=?, genel_toplam=?, "
            "kdv_dahil=?, updated_at=datetime('now','localtime') WHERE id=?",
            (tip, cari_id if tip != "Transfer" else None, depo_id,
             hedef_depo_id if tip == "Transfer" else None, tarih, aciklama,
             para_birimi, doviz_kur,
             top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"], top["genel_toplam"],
             kdv_dahil, mevcut["id"]),
        )
        conn.execute("DELETE FROM irsaliye_kalem WHERE irsaliye_id=?", (mevcut["id"],))
        iid = mevcut["id"]
        islem = ("guncelle", {"irsaliye_no": mevcut["irsaliye_no"]}, "İrsaliye güncellendi.")
    else:
        on_ek = TIP_ON_EK[tip]
        no = db.sonraki_belge_no(conn, "irsaliye", "irsaliye_no", on_ek, tarih[:4], db.sirket_id(req))
        cur = conn.execute(
            "INSERT INTO irsaliye(irsaliye_no, tip, cari_id, depo_id, hedef_depo_id, kaynak_siparis_id, "
            "tarih, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, "
            "aciklama, kdv_dahil, sube_id, created_by, sirket_id) VALUES(?,?,?,?,?,?,?,'Taslak',?,?,?,?,?,?,?,?,?,?,?)",
            (no, tip, cari_id if tip != "Transfer" else None, depo_id,
             hedef_depo_id if tip == "Transfer" else None, kaynak_siparis_id, tarih,
             para_birimi, doviz_kur,
             top["ara_toplam"], top["iskonto_toplam"], top["kdv_toplam"], top["genel_toplam"],
             aciklama, kdv_dahil, izole_sube(req), req.user["id"], db.sirket_id(req)),
        )
        iid = cur.lastrowid
        islem = ("olustur", {"irsaliye_no": no}, f"İrsaliye oluşturuldu: {no}")

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
            "INSERT INTO irsaliye_kalem(irsaliye_id, stok_id, varyant_id, miktar, birim_fiyat, "
            "iskonto_orani, kdv_orani, kdv_dahil, tutar, aciklama, birim, goruntu_adi, sirket_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (iid, s["stok_id"], s["varyant_id"], s["miktar"], s["birim_fiyat"],
             s["iskonto_orani"], s["kdv_orani"], s.get("kdv_dahil"), s["tutar"],
             (s.get("manuel_ad") or "").strip() or None, birim, goruntu, db.sirket_id(req)),
        )
    conn.commit()
    audit(req, "irsaliye", iid, islem[0], islem[1])
    flash(req, islem[2], "ok")
    conn.close()
    return redirect(f"/irsaliye/{iid}")


def _form_render(req, conn, mevcut, satirlar, tip, cari_id, depo_id, hedef_depo_id,
                 tarih, aciklama, kaynak_siparis_id):
    satirlar = _satir_gorunum(conn, satirlar, db.sirket_id(req))
    toplamlar = _toplamlar([dict(s) for s in satirlar])
    cariler = _cariler(conn, tip, db.sirket_id(req))
    stoklar = _stoklar(conn, db.sirket_id(req))
    depolar = _depolar(conn, db.sirket_id(req))
    cari_etiket, cari_iskonto = _cari_secim(cariler, cari_id)
    irsaliye = dict(mevcut) if mevcut else {"tip": tip, "cari_id": cari_id, "depo_id": depo_id,
                                            "hedef_depo_id": hedef_depo_id, "tarih": tarih,
                                            "aciklama": aciklama}
    kdv_dahil = 1 if req.form.get("kdv_dahil") in ("1", "dahil", "on") else (0 if mevcut is None else (mevcut["kdv_dahil"] or 0))
    return render_template("irsaliye/form.html", irsaliye=irsaliye, satirlar=satirlar,
                           cariler=cariler, stoklar=stoklar, depolar=depolar, toplamlar=toplamlar,
                           tip=tip, depo_id=depo_id, hedef_depo_id=hedef_depo_id,
                           cari_id=cari_id, cari_etiket=cari_etiket, cari_iskonto=cari_iskonto, birimler=db.birimler(sid=db.sirket_id(req)),
                           para_birimleri=db.para_birimleri(sid=db.sirket_id(req)),
                           kaynak_siparis_id=kaynak_siparis_id, kaynak_siparis=None,
                           kdv_dahil=kdv_dahil, bugun=datetime.date.today().isoformat())


@route(r"/irsaliye/(?P<iid>\d+)/durum", methods=("POST",), roles=IRSALIYE_ONAY)
def irsaliye_durum(req, iid):
    durum = req.form.get("durum")
    if durum not in ("Onaylandı", "İptal"):
        flash(req, "Geçersiz durum geçişi.", "danger")
        return redirect(f"/irsaliye/{iid}")
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM irsaliye WHERE id=? AND sirket_id=?",
                     (int(iid), db.sirket_id(req))).fetchone()
    if not r:
        conn.close()
        return redirect("/irsaliye")

    if durum == "Onaylandı":
        if r["durum"] != "Taslak":
            conn.close()
            flash(req, "Yalnızca 'Taslak' durumundaki irsaliye onaylanabilir.", "danger")
            return redirect(f"/irsaliye/{iid}")
        kalemler = [dict(k) for k in conn.execute(
            "SELECT k.*, st.kod AS stok_kod FROM irsaliye_kalem k "
            "JOIN stok_kart st ON st.id=k.stok_id WHERE k.irsaliye_id=?", (int(iid),)).fetchall()]
        hatalar = _stok_kontrol_ve_uygula(conn, req, dict(r), kalemler, yon=1)
        if hatalar:
            conn.close()
            flash(req, "İrsaliye onaylanamadı: " + " · ".join(hatalar), "danger")
            return redirect(f"/irsaliye/{iid}")
        # F1 — mali etki (cari + yevmiye) irsaliye onayında oluşur (Transfer hariç).
        _cari_uygula_irsaliye(conn, req, dict(r), yon=1)
        conn.execute("UPDATE irsaliye SET durum='Onaylandı' WHERE id=?", (int(iid),))
        muhasebe.fis_uret(conn, "Irsaliye", int(iid))
        # F4 — Satış/Alış irsaliyesi onayında otomatik e-İrsaliye taslağı (Transfer hariç).
        # e-Dönüşüm yalnızca BELGELEŞTİRME katmanıdır; F1 mali etkisi yukarıda işlendi.
        if r["tip"] in ("Satis", "Alis"):
            try:
                import edonusum
                edonusum._olustur(conn, req, "irsaliye", int(iid))
            except Exception:
                pass  # e-belge üretimi hata verirse irsaliye onayını bloke etme
        conn.commit()
        audit(req, "irsaliye", int(iid), "durum", {"eski": r["durum"], "yeni": "Onaylandı"})
        notify("bilgi", "İrsaliye onaylandı",
               f"{r['irsaliye_no']} onaylandı; stok + cari hareket (borç/alacak) + yevmiye işlendi.",
               "irsaliye", int(iid), sirket_id=db.sirket_id(req))
        conn.close()
        flash(req, "İrsaliye onaylandı; cari hareket ve yevmiye oluşturuldu.", "ok")
        return redirect(f"/irsaliye/{iid}")

    # --- İptal ---
    # K25: GİB'e gönderilmiş/onaylanmış e-İrsaliye varsa iptal engellenir (K15 deseni).
    aktif = db.aktif_eb(conn, "kaynak_irsaliye_id", int(iid))
    if aktif:
        conn.close()
        flash(req, f"Bu irsaliyeden üretilmiş {aktif['belge_no']} ({aktif['tur']}) e-belgesi "
                   f"'{aktif['durum']}' durumunda. GİB'e bildirilmiş bir belge doğrudan iptal "
                   f"edilemez; önce e-belge tarafında resmi iptal/düzeltme sürecini tamamlayın.",
              "danger")
        return redirect(f"/irsaliye/{iid}")
    if r["durum"] not in ("Taslak", "Onaylandı"):
        conn.close()
        flash(req, "Bu durumdaki irsaliye iptal edilemez.", "danger")
        return redirect(f"/irsaliye/{iid}")
    # F1 — bu irsaliyeden üretilmiş (iptal edilmemiş) fatura varsa iptal engellenir:
    # mali etki irsaliyede olduğundan, fatura varken irsaliye iptali cari bakiyeyi bozar.
    bagli_fatura = conn.execute(
        "SELECT fatura_no FROM fatura WHERE kaynak_irsaliye_id=? AND durum != 'İptal'",
        (int(iid),)).fetchone()
    if bagli_fatura:
        conn.close()
        flash(req, f"Bu irsaliyeden {bagli_fatura['fatura_no']} faturası üretilmiş. "
                   f"Önce faturayı iptal edin, sonra irsaliyeyi iptal edin.", "danger")
        return redirect(f"/irsaliye/{iid}")
    if r["durum"] == "Onaylandı":
        kalemler = [dict(k) for k in conn.execute(
            "SELECT k.*, st.kod AS stok_kod FROM irsaliye_kalem k "
            "JOIN stok_kart st ON st.id=k.stok_id WHERE k.irsaliye_id=?", (int(iid),)).fetchall()]
        _stok_kontrol_ve_uygula(conn, req, dict(r), kalemler, yon=-1)
        # F1 — mali etki geri alınır (cari hareket sil + yevmiye fişi sil).
        _cari_uygula_irsaliye(conn, req, dict(r), yon=-1)
        muhasebe.fis_sil(conn, "Irsaliye", int(iid))
    conn.execute("UPDATE irsaliye SET durum='İptal' WHERE id=?", (int(iid),))
    # Kaynaksız kalan Taslak/Reddedildi e-İrsaliyeleri de İptal'e al (öksüz kalmasın)
    conn.execute(
        "UPDATE e_belge SET durum='İptal', hata_mesaji='Kaynak irsaliye iptal edildi' "
        "WHERE kaynak_irsaliye_id=? AND durum IN ('Taslak','Reddedildi')", (int(iid),))
    conn.commit()
    audit(req, "irsaliye", int(iid), "durum", {"eski": r["durum"], "yeni": "İptal"})
    conn.close()
    flash(req, "İrsaliye iptal edildi (stok hareketi geri alındı).", "ok")
    return redirect(f"/irsaliye/{iid}")


@route(r"/irsaliye/(?P<iid>\d+)/yazdir", roles=())
def irsaliye_yazdir(req, iid):
    conn = db.get_conn()
    sonuc = _irsaliye_detay(conn, iid, db.sirket_id(req))
    if not sonuc:
        conn.close()
        flash(req, "İrsaliye bulunamadı.", "danger")
        return redirect("/irsaliye")
    r, kalemler = sonuc
    # F6 — şube izolasyonu: başka şubeye ait belge yazdırılamaz.
    if not sube_koruma(req, r["sube_id"]):
        conn.close()
        return Response("Bu kayıt başka bir şubeye aittir.", "403 Forbidden")
    belge = yazdir_belge(r, kalemler, "irsaliye_no", TIP_LABEL[r["tip"]])
    conn.close()
    return render_template("yazdir/belge.html", belge=belge)


def register():
    return "irsaliye"
