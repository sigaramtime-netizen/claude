# -*- coding: utf-8 -*-
"""Faz 6.1 — Sistem Yönetimi (Ayarlar).

Admin'e özel merkezi yönetim merkezi:
  * Kullanıcı yönetimi (ekle / rol değiştir / aktif-pasif / şifre sıfırlama)
  * Firma bilgileri düzenleme
  * Bildirim kanalı (SMS/e-posta) — eski /bildirimler/ayarlar buraya taşındı
  * e-Belge entegratör ayarları — eski /edonusum/ayarlar buraya taşındı
  * Tanım ekranlarına (Şube/Depo/Kasa/Banka) hızlı erişim

Kendi şifresini değiştirme (/profil/sifre) TÜM kullanıcılara açıktır.

Tasarım kararları:
  * Silme yerine PASİFLEŞTİRME (audit geçmişi korunur; sert silme yok).
  * Şifreler PBKDF2-HMAC-SHA256 ile saklanır (düz metin asla).
  * Audit detayına şifre/parola YAZILMAZ.
"""
import sqlite3

import db
import bildirim_saglayici
import entegrator as ent

from core import route, render_template, redirect, flash, audit, firma_yenile

ROLLER = ["Admin", "Muhasebe", "Satis", "Servis", "Depo"]
ADMIN = ("Admin",)


def _sifre_gecerli(s):
    """Parola politikası: en az 8 karakter ve en az bir rakam."""
    if not isinstance(s, str) or len(s) < 8:
        return False
    return any(ch.isdigit() for ch in s)


def _int(v, default=None):
    try:
        return int(v)
    except (TypeError, ValueError):
        return default


# ---------------------------------------------------------------------------
# Ana hub
# ---------------------------------------------------------------------------
@route(r"/ayarlar", roles=ADMIN)
def ayarlar_index(req):
    conn = db.get_conn()
    toplam = conn.execute("SELECT COUNT(*) c FROM kullanici").fetchone()["c"]
    aktif = conn.execute("SELECT COUNT(*) c FROM kullanici WHERE aktif=1").fetchone()["c"]
    _k = conn.execute("SELECT deger FROM meta WHERE anahtar='bildirim.kanal'").fetchone()
    kanal = _k["deger"] if _k else "kapali"
    _e = {r["anahtar"]: r["deger"] for r in
          conn.execute("SELECT anahtar, deger FROM meta WHERE anahtar LIKE 'entegrator_%'").fetchall()}
    conn.close()
    enteg = ent._entegrator_uret({k.replace("entegrator_", ""): v for k, v in _e.items()})
    saglik = enteg.saglik()
    return render_template("ayarlar/index.html", toplam=toplam, aktif=aktif,
                           kanal=kanal, enteg=enteg, saglik=saglik)


# ---------------------------------------------------------------------------
# Kullanıcı yönetimi
# ---------------------------------------------------------------------------
@route(r"/ayarlar/kullanicilar", methods=("GET", "POST"), roles=ADMIN)
def ayarlar_kullanicilar(req):
    conn = db.get_conn()
    if req.method == "POST":
        kadi = (req.form.get("kullanici_adi") or "").strip()
        adsoyad = (req.form.get("ad_soyad") or "").strip()
        email = (req.form.get("email") or "").strip() or None
        rol = req.form.get("rol") or ""
        sube_id = req.form.get("sube_id") or ""
        sifre = req.form.get("sifre") or ""
        if not kadi or not adsoyad:
            flash(req, "Kullanıcı adı ve ad-soyad zorunludur.", "danger")
        elif rol not in ROLLER:
            flash(req, "Geçersiz rol.", "danger")
        elif not _sifre_gecerli(sifre):
            flash(req, "İlk şifre en az 8 karakter ve en az bir rakam içermeli.", "danger")
        else:
            try:
                cur = conn.execute(
                    "INSERT INTO kullanici(kullanici_adi, ad_soyad, email, sifre_hash, rol, aktif, sube_id) "
                    "VALUES(?,?,?,?,?,1,?)",
                    (kadi, adsoyad, email, db.hash_sifre(sifre), rol,
                     _int(sube_id)),
                )
                uid = cur.lastrowid
                # İstek 3 — N-N şirket üyeliği: Admin tümüne zaten erişir (kullanici_sirket'e gerek yok);
                # diğer roller için seçilen şirketlere üyelik yazılır. Hiç seçilmezse şirket 1'e düşer.
                secili = {_int(v) for v in req.form_list.get("sirketler", []) if _int(v)}
                if rol == "Admin":
                    secili = set()
                if not secili:
                    secili = {1}
                for sirket_id in secili:
                    conn.execute(
                        "INSERT OR IGNORE INTO kullanici_sirket(kullanici_id, sirket_id) VALUES(?,?)",
                        (uid, sirket_id))
                conn.commit()
                audit(req, "kullanici", uid, "ekle",
                      {"kullanici_adi": kadi, "rol": rol, "sube_id": _int(sube_id),
                       "sirketler": sorted(secili)})
                flash(req, f"Kullanıcı eklendi: {kadi}", "ok")
            except sqlite3.IntegrityError:
                flash(req, f"'{kadi}' kullanıcı adı zaten mevcut.", "danger")
            except sqlite3.Error:
                flash(req, "Kullanıcı eklenirken bir hata oluştu.", "danger")
        conn.close()
        return redirect("/ayarlar/kullanicilar")

    kullanicilar = conn.execute(
        "SELECT k.id, k.kullanici_adi, k.ad_soyad, k.email, k.rol, k.aktif, k.sube_id, sb.ad AS sube_ad "
        "FROM kullanici k LEFT JOIN sube sb ON sb.id = k.sube_id "
        "ORDER BY k.aktif DESC, k.ad_soyad"
    ).fetchall()
    subeler = conn.execute("SELECT id, kod, ad FROM sube WHERE sirket_id=? ORDER BY ad",
                            (db.sirket_id(req),)).fetchall()
    sirketler = conn.execute("SELECT id, kod, unvan FROM sirket WHERE aktif=1 ORDER BY id").fetchall()
    uyeler = conn.execute("SELECT kullanici_id, sirket_id FROM kullanici_sirket").fetchall()
    uye_sirketler = {}
    for row in uyeler:
        uye_sirketler.setdefault(row["kullanici_id"], set()).add(row["sirket_id"])
    conn.close()
    return render_template("ayarlar/kullanicilar.html", kullanicilar=kullanicilar,
                           subeler=subeler, sirketler=sirketler, uye_sirketler=uye_sirketler,
                           ROLLER=ROLLER)


@route(r"/ayarlar/kullanici/(?P<uid>\d+)/sirketler", methods=("POST",), roles=ADMIN)
def ayarlar_kullanici_sirketler(req, uid):
    """İstek 3 — kullanıcının şirket üyeliklerini (N-N) günceller. Admin kendisi için atlanır."""
    conn = db.get_conn()
    hedef = conn.execute("SELECT id, kullanici_adi, rol FROM kullanici WHERE id=?",
                         (int(uid),)).fetchone()
    if not hedef:
        conn.close()
        return redirect("/ayarlar/kullanicilar")
    if hedef["rol"] == "Admin":
        conn.close()
        flash(req, "Admin tüm şirketlere zaten erişir — üyelik düzenlemesi gerekmez.", "danger")
        return redirect("/ayarlar/kullanicilar")
    secili = {_int(v) for v in req.form_list.get("sirketler", []) if _int(v)}
    if not secili:
        secili = {1}
    conn.execute("DELETE FROM kullanici_sirket WHERE kullanici_id=?", (int(uid),))
    for sirket_id in secili:
        conn.execute(
            "INSERT OR IGNORE INTO kullanici_sirket(kullanici_id, sirket_id) VALUES(?,?)",
            (int(uid), sirket_id))
    conn.commit()
    audit(req, "kullanici", int(uid), "sirket_uyeligi",
          {"kullanici_adi": hedef["kullanici_adi"], "sirketler": sorted(secili)})
    conn.close()
    flash(req, f"'{hedef['kullanici_adi']}' şirket üyelikleri güncellendi.", "ok")
    return redirect("/ayarlar/kullanicilar")


@route(r"/ayarlar/kullanici/(?P<uid>\d+)/rol", methods=("POST",), roles=ADMIN)
def ayarlar_kullanici_rol(req, uid):
    rol = req.form.get("rol") or ""
    conn = db.get_conn()
    hedef = conn.execute("SELECT id, kullanici_adi, rol FROM kullanici WHERE id=?",
                         (_int(uid),)).fetchone()
    if not hedef:
        flash(req, "Kullanıcı bulunamadı.", "danger")
    elif rol not in ROLLER:
        flash(req, "Geçersiz rol.", "danger")
    elif _int(uid) == req.user["id"]:
        flash(req, "Kendi rolünüzü değiştiremezsiniz.", "danger")
    else:
        conn.execute("UPDATE kullanici SET rol=? WHERE id=?", (rol, _int(uid)))
        conn.commit()
        audit(req, "kullanici", _int(uid), "rol_degistir",
              {"eski": hedef["rol"], "yeni": rol})
        flash(req, f"{hedef['kullanici_adi']} rolü güncellendi: {rol}", "ok")
    conn.close()
    return redirect("/ayarlar/kullanicilar")


@route(r"/ayarlar/kullanici/(?P<uid>\d+)/durum", methods=("POST",), roles=ADMIN)
def ayarlar_kullanici_durum(req, uid):
    conn = db.get_conn()
    hedef = conn.execute("SELECT id, kullanici_adi, rol, aktif FROM kullanici WHERE id=?",
                         (_int(uid),)).fetchone()
    if not hedef:
        flash(req, "Kullanıcı bulunamadı.", "danger")
    elif _int(uid) == req.user["id"]:
        flash(req, "Kendi hesabınızı pasifleştiremezsiniz.", "danger")
    else:
        yeni = 0 if hedef["aktif"] else 1
        if yeni == 0 and hedef["rol"] == "Admin":
            aktif_admin = conn.execute(
                "SELECT COUNT(*) c FROM kullanici WHERE rol='Admin' AND aktif=1"
            ).fetchone()["c"]
            if aktif_admin <= 1:
                flash(req, "Son aktif yönetici pasifleştirilemez.", "danger")
                conn.close()
                return redirect("/ayarlar/kullanicilar")
        conn.execute("UPDATE kullanici SET aktif=? WHERE id=?", (yeni, _int(uid)))
        conn.commit()
        audit(req, "kullanici", _int(uid), "durum", {"aktif": yeni})
        flash(req, f"{hedef['kullanici_adi']} "
              f"{'aktifleştirildi' if yeni else 'pasifleştirildi'}.", "ok")
    conn.close()
    return redirect("/ayarlar/kullanicilar")


@route(r"/ayarlar/kullanici/(?P<uid>\d+)/sifre", methods=("POST",), roles=ADMIN)
def ayarlar_kullanici_sifre(req, uid):
    sifre = req.form.get("sifre") or ""
    conn = db.get_conn()
    hedef = conn.execute("SELECT id, kullanici_adi FROM kullanici WHERE id=?",
                         (_int(uid),)).fetchone()
    if not hedef:
        flash(req, "Kullanıcı bulunamadı.", "danger")
    elif not _sifre_gecerli(sifre):
        flash(req, "Yeni şifre en az 8 karakter ve en az bir rakam içermeli.", "danger")
    else:
        conn.execute("UPDATE kullanici SET sifre_hash=? WHERE id=?",
                     (db.hash_sifre(sifre), _int(uid)))
        # Güvenlik: mevcut oturumları geçersiz kıl (şifre değişti).
        conn.execute("DELETE FROM sessionler WHERE kullanici_id=?", (_int(uid),))
        conn.commit()
        audit(req, "kullanici", _int(uid), "sifre_sifirla",
              {"kullanici_adi": hedef["kullanici_adi"]})
        flash(req, f"{hedef['kullanici_adi']} şifresi sıfırlandı.", "ok")
    conn.close()
    return redirect("/ayarlar/kullanicilar")


# ---------------------------------------------------------------------------
# Firma bilgileri
# ---------------------------------------------------------------------------
@route(r"/ayarlar/firma", methods=("GET", "POST"), roles=ADMIN)
def ayarlar_firma(req):
    """Aktif şirketin kimlik bilgileri (İstek 3: firma → sirket)."""
    conn = db.get_conn()
    sid = req.user["sirket_id"] if req.user else 1
    if req.method == "POST":
        f = {
            "unvan": (req.form.get("unvan") or "").strip(),
            "kisa_ad": (req.form.get("kisa_ad") or "").strip(),
            "vergi_dairesi": (req.form.get("vergi_dairesi") or "").strip(),
            "vergi_no": (req.form.get("vergi_no") or "").strip(),
            "adres": (req.form.get("adres") or "").strip(),
            "telefon": (req.form.get("telefon") or "").strip(),
            "email": (req.form.get("email") or "").strip(),
            "logo": (req.form.get("logo") or "").strip(),
        }
        if not f["unvan"]:
            flash(req, "Ünvan zorunludur.", "danger")
        else:
            conn.execute(
                "UPDATE sirket SET unvan=?, kisa_ad=?, vergi_dairesi=?, vergi_no=?, "
                "adres=?, telefon=?, email=?, logo=? WHERE id=?",
                (f["unvan"], f["kisa_ad"], f["vergi_dairesi"], f["vergi_no"],
                 f["adres"], f["telefon"], f["email"], f["logo"], sid),
            )
            conn.commit()
            audit(req, "sirket", sid, "guncelle", {"unvan": f["unvan"]})
            firma_yenile()
            flash(req, "Şirket bilgileri güncellendi.", "ok")
        conn.close()
        return redirect("/ayarlar/firma")
    f = conn.execute("SELECT * FROM sirket WHERE id=?", (sid,)).fetchone()
    conn.close()
    return render_template("ayarlar/firma.html", f=f)


# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# İstek 3 — Çoklu Şirket: şirket CRUD (liste + yeni + düzenle + pasifleştirme)
# ---------------------------------------------------------------------------
@route(r"/ayarlar/sirketler", methods=("GET", "POST"), roles=ADMIN)
def ayarlar_sirketler(req):
    """Şirket yönetimi. Yeni şirket → db.sirket_seed (hesap planı + kategoriler + depo)."""
    conn = db.get_conn()
    if req.method == "POST":
        kod = (req.form.get("kod") or "").strip().upper()
        unvan = (req.form.get("unvan") or "").strip()
        if not kod or not unvan:
            flash(req, "Şirket kodu ve ünvan zorunludur.", "danger")
        else:
            try:
                cur = conn.execute(
                    "INSERT INTO sirket(kod, unvan, kisa_ad, vergi_dairesi, vergi_no, "
                    "adres, telefon, email) VALUES(?,?,?,?,?,?,?,?)",
                    (kod, unvan,
                     (req.form.get("kisa_ad") or "").strip() or None,
                     (req.form.get("vergi_dairesi") or "").strip() or None,
                     (req.form.get("vergi_no") or "").strip() or None,
                     (req.form.get("adres") or "").strip() or None,
                     (req.form.get("telefon") or "").strip() or None,
                     (req.form.get("email") or "").strip() or None))
                yeni_id = cur.lastrowid
                db.sirket_seed(conn, yeni_id)
                # Oluşturan (Admin) şirkete N-N üye yapılır (yoksa geçiş listesinde görünmez).
                conn.execute(
                    "INSERT OR IGNORE INTO kullanici_sirket(kullanici_id, sirket_id) VALUES(?,?)",
                    (req.user["id"], yeni_id))
                conn.commit()
                audit(req, "sirket", yeni_id, "ekle", {"kod": kod, "unvan": unvan})
                firma_yenile()
                flash(req, f"Şirket oluşturuldu: {unvan} — hesap planı, demirbaş kategorileri "
                           "ve varsayılan depo otomatik seed edildi.", "ok")
            except sqlite3.IntegrityError:
                flash(req, f"'{kod}' şirket kodu zaten mevcut.", "danger")
            except sqlite3.Error:
                flash(req, "Şirket oluşturulurken bir hata oluştu.", "danger")
        conn.close()
        return redirect("/ayarlar/sirketler")

    sirketler = conn.execute(
        "SELECT s.*, (SELECT COUNT(*) FROM kullanici_sirket ks WHERE ks.sirket_id=s.id) AS uye_sayisi "
        "FROM sirket s ORDER BY s.aktif DESC, s.id"
    ).fetchall()
    conn.close()
    return render_template("ayarlar/sirketler.html", sirketler=sirketler)


@route(r"/ayarlar/sirket/(?P<sid>\d+)/guncelle", methods=("POST",), roles=ADMIN)
def ayarlar_sirket_guncelle(req, sid):
    conn = db.get_conn()
    s = conn.execute("SELECT id, kod FROM sirket WHERE id=?", (int(sid),)).fetchone()
    if not s:
        conn.close()
        return redirect("/ayarlar/sirketler")
    unvan = (req.form.get("unvan") or "").strip()
    if not unvan:
        conn.close()
        flash(req, "Ünvan zorunludur.", "danger")
        return redirect("/ayarlar/sirketler")
    conn.execute(
        "UPDATE sirket SET unvan=?, kisa_ad=?, vergi_dairesi=?, vergi_no=?, adres=?, telefon=?, "
        "email=?, logo=? WHERE id=?",
        (unvan,
         (req.form.get("kisa_ad") or "").strip() or None,
         (req.form.get("vergi_dairesi") or "").strip() or None,
         (req.form.get("vergi_no") or "").strip() or None,
         (req.form.get("adres") or "").strip() or None,
         (req.form.get("telefon") or "").strip() or None,
         (req.form.get("email") or "").strip() or None,
         (req.form.get("logo") or "").strip() or None,
         int(sid)))
    conn.commit()
    audit(req, "sirket", int(sid), "guncelle", {"unvan": unvan})
    firma_yenile()
    conn.close()
    flash(req, "Şirket bilgileri güncellendi.", "ok")
    return redirect("/ayarlar/sirketler")


@route(r"/ayarlar/sirket/(?P<sid>\d+)/durum", methods=("POST",), roles=ADMIN)
def ayarlar_sirket_durum(req, sid):
    """Aktif/Pasif geçişi (K32: sert silme yok; en az bir aktif şirket korunur)."""
    conn = db.get_conn()
    s = conn.execute("SELECT id, kod, aktif FROM sirket WHERE id=?", (int(sid),)).fetchone()
    if not s:
        conn.close()
        return redirect("/ayarlar/sirketler")
    if s["aktif"]:
        aktif_sayisi = conn.execute("SELECT COUNT(*) c FROM sirket WHERE aktif=1").fetchone()["c"]
        if aktif_sayisi <= 1:
            conn.close()
            flash(req, "En az bir aktif şirket kalmalıdır — pasifleştirme engellendi.", "danger")
            return redirect("/ayarlar/sirketler")
        conn.execute("UPDATE sirket SET aktif=0 WHERE id=?", (int(sid),))
        mesaj = f"'{s['kod']}' pasifleştirildi. Bu şirkette kalan oturumlar bir sonraki girişte ilk yetkili şirkete düşer."
    else:
        conn.execute("UPDATE sirket SET aktif=1 WHERE id=?", (int(sid),))
        mesaj = f"'{s['kod']}' yeniden aktifleştirildi."
    conn.commit()
    audit(req, "sirket", int(sid), "durum", {"aktif": not s["aktif"]})
    firma_yenile()
    conn.close()
    flash(req, mesaj, "ok")
    return redirect("/ayarlar/sirketler")


# ---------------------------------------------------------------------------
# Bildirim kanalı (eski /bildirimler/ayarlar → buraya)
# ---------------------------------------------------------------------------
@route(r"/ayarlar/bildirim", methods=("GET", "POST"), roles=ADMIN)
def ayarlar_bildirim(req):
    conn = db.get_conn()
    if req.method == "POST":
        kanal = req.form.get("kanal") or "kapali"
        if bildirim_saglayici.ayar_guncelle(kanal):
            audit(req, "meta", 0, "bildirim_ayar", {"bildirim.kanal": kanal})
            flash(req, f"Bildirim kanalı güncellendi: {kanal}", "ok")
        else:
            flash(req, "Geçersiz kanal.", "danger")
        conn.close()
        return redirect("/ayarlar/bildirim")
    _k = conn.execute("SELECT deger FROM meta WHERE anahtar='bildirim.kanal'").fetchone()
    kanal = _k["deger"] if _k else "kapali"
    gonderimler = conn.execute("SELECT * FROM bildirim_gonderim ORDER BY id DESC LIMIT 50").fetchall()
    conn.close()
    return render_template("bildirimler/ayarlar.html", kanal=kanal, gonderimler=gonderimler)


# ---------------------------------------------------------------------------
# e-Belge entegratörü (eski /edonusum/ayarlar → buraya)
# ---------------------------------------------------------------------------
@route(r"/ayarlar/entegrator", methods=("GET", "POST"), roles=ADMIN)
def ayarlar_entegrator(req):
    conn = db.get_conn()
    if req.method == "POST":
        saglayici = (req.form.get("saglayici") or "Mock").strip()
        anahtar = (req.form.get("api_anahtari") or "").strip()
        test_modu = "1" if req.form.get("test_modu") == "1" else "0"
        conn.execute("INSERT INTO meta(anahtar, deger) VALUES('entegrator_saglayici',?) "
                     "ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger", (saglayici,))
        conn.execute("INSERT INTO meta(anahtar, deger) VALUES('entegrator_api_anahtari',?) "
                     "ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger", (anahtar,))
        conn.execute("INSERT INTO meta(anahtar, deger) VALUES('entegrator_test_modu',?) "
                     "ON CONFLICT(anahtar) DO UPDATE SET deger=excluded.deger", (test_modu,))
        conn.commit()
        conn.close()
        flash(req, "Entegratör ayarları kaydedildi.", "ok")
        return redirect("/ayarlar/entegrator")
    rows = {r["anahtar"]: r["deger"] for r in
            conn.execute("SELECT anahtar, deger FROM meta WHERE anahtar LIKE 'entegrator_%'").fetchall()}
    conn.close()
    enteg = ent._entegrator_uret({k.replace("entegrator_", ""): v for k, v in rows.items()})
    saglik = enteg.saglik()
    return render_template("edonusum/ayarlar.html", ayar=rows, enteg=enteg, saglik=saglik)


# ---------------------------------------------------------------------------
# Kendi şifreni değiştir (tüm kullanıcılar)
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# D011-A — Tanımlar (Kategori & Cari Grup): liste + pasifleştir (K32: silme yok)
# ---------------------------------------------------------------------------
@route(r"/ayarlar/tanimlar", roles=ADMIN)
def ayarlar_tanimlar(req):
    conn = db.get_conn()
    sid = db.sirket_id(req)
    kategoriler = conn.execute(
        "SELECT k.*, (SELECT COUNT(*) FROM stok_kart s WHERE s.kategori_id=k.id AND s.sirket_id=k.sirket_id) AS kullanim "
        "FROM kategori k WHERE k.sirket_id=? ORDER BY k.ad", (sid,)).fetchall()
    gruplar = conn.execute(
        "SELECT g.*, (SELECT COUNT(*) FROM cari_kart c WHERE c.grup_id=g.id AND c.sirket_id=g.sirket_id) AS kullanim "
        "FROM cari_grup g WHERE g.sirket_id=? ORDER BY g.tip, g.ad", (sid,)).fetchall()
    # D012-X — para birimi + birim (DB tablo)
    para_birimleri = conn.execute(
        "SELECT p.*, (SELECT COUNT(*) FROM stok_kart s WHERE s.para_birimi=p.kod AND s.sirket_id=p.sirket_id) AS kullanim "
        "FROM para_birimi p WHERE p.sirket_id=? ORDER BY p.id", (sid,)).fetchall()
    birimler = conn.execute(
        "SELECT b.*, (SELECT COUNT(*) FROM stok_kart s WHERE s.birim=b.ad AND s.sirket_id=b.sirket_id) AS kullanim "
        "FROM birim b WHERE b.sirket_id=? ORDER BY b.id", (sid,)).fetchall()
    conn.close()
    return render_template("ayarlar/tanimlar.html", kategoriler=kategoriler, gruplar=gruplar,
                           para_birimleri=para_birimleri, birimler=birimler)


@route(r"/ayarlar/tanimlar/kategori/(?P<kid>\d+)/durum", methods=("POST",), roles=ADMIN)
def ayarlar_tanimlar_kategori_durum(req, kid):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM kategori WHERE id=? AND sirket_id=?",
                     (int(kid), db.sirket_id(req))).fetchone()
    if r:
        yeni = 0 if r["aktif"] else 1
        conn.execute("UPDATE kategori SET aktif=? WHERE id=?", (yeni, int(kid)))
        conn.commit()
        audit(req, "kategori", int(kid),
              "pasiflestir" if yeni == 0 else "aktiflestir", {"ad": r["ad"]})
    conn.close()
    return redirect("/ayarlar/tanimlar")


@route(r"/ayarlar/tanimlar/cari-grup/(?P<gid>\d+)/durum", methods=("POST",), roles=ADMIN)
def ayarlar_tanimlar_cari_grup_durum(req, gid):
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM cari_grup WHERE id=? AND sirket_id=?",
                     (int(gid), db.sirket_id(req))).fetchone()
    if r:
        yeni = 0 if r["aktif"] else 1
        conn.execute("UPDATE cari_grup SET aktif=? WHERE id=?", (yeni, int(gid)))
        conn.commit()
        audit(req, "cari_grup", int(gid),
              "pasiflestir" if yeni == 0 else "aktiflestir", {"ad": r["ad"]})
    conn.close()
    return redirect("/ayarlar/tanimlar")


@route(r"/ayarlar/tanimlar/para-birimi/(?P<pid>\d+)/durum", methods=("POST",), roles=ADMIN)
def ayarlar_tanimlar_para_birimi_durum(req, pid):
    """D012-X — para birimi pasifleştir/aktifleştir (K32: silme yok). TRY temel olduğu için korunur."""
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM para_birimi WHERE id=? AND sirket_id=?",
                     (int(pid), db.sirket_id(req))).fetchone()
    if r:
        yeni = 0 if r["aktif"] else 1
        # TRY temel para birimidir; pasifleştirilemez (belge toplamları TRY'ye dayanır).
        if yeni == 0 and r["kod"] == "TRY":
            flash(req, "TRY temel para birimidir, pasifleştirilemez.", "danger")
        else:
            conn.execute("UPDATE para_birimi SET aktif=? WHERE id=?", (yeni, int(pid)))
            conn.commit()
            audit(req, "para_birimi", int(pid),
                  "pasiflestir" if yeni == 0 else "aktiflestir", {"kod": r["kod"]})
    conn.close()
    return redirect("/ayarlar/tanimlar")


@route(r"/ayarlar/tanimlar/birim/(?P<bid>\d+)/durum", methods=("POST",), roles=ADMIN)
def ayarlar_tanimlar_birim_durum(req, bid):
    """D012-X — birim pasifleştir/aktifleştir (K32: silme yok)."""
    conn = db.get_conn()
    r = conn.execute("SELECT * FROM birim WHERE id=? AND sirket_id=?",
                     (int(bid), db.sirket_id(req))).fetchone()
    if r:
        yeni = 0 if r["aktif"] else 1
        conn.execute("UPDATE birim SET aktif=? WHERE id=?", (yeni, int(bid)))
        conn.commit()
        audit(req, "birim", int(bid),
              "pasiflestir" if yeni == 0 else "aktiflestir", {"ad": r["ad"]})
    conn.close()
    return redirect("/ayarlar/tanimlar")


@route(r"/profil/sifre", methods=("GET", "POST"), roles=())
def profil_sifre(req):
    if req.method == "POST":
        mevcut = req.form.get("mevcut") or ""
        yeni = req.form.get("yeni") or ""
        yeni2 = req.form.get("yeni2") or ""
        conn = db.get_conn()
        u = conn.execute("SELECT sifre_hash FROM kullanici WHERE id=?",
                         (req.user["id"],)).fetchone()
        if not db.dogrula_sifre(mevcut, u["sifre_hash"]):
            flash(req, "Mevcut şifre hatalı.", "danger")
        elif not _sifre_gecerli(yeni):
            flash(req, "Yeni şifre en az 8 karakter ve en az bir rakam içermeli.", "danger")
        elif yeni != yeni2:
            flash(req, "Yeni şifreler birbiriyle uyuşmuyor.", "danger")
        elif mevcut == yeni:
            flash(req, "Yeni şifre eskisinden farklı olmalı.", "danger")
        else:
            conn.execute("UPDATE kullanici SET sifre_hash=? WHERE id=?",
                         (db.hash_sifre(yeni), req.user["id"]))
            # Diğer oturumları geçersiz kıl; kendi oturumu açık kalsın.
            conn.execute("DELETE FROM sessionler WHERE kullanici_id=? AND token != ?",
                         (req.user["id"], req.session_token))
            conn.commit()
            audit(req, "kullanici", req.user["id"], "sifre_degistir", None)
            flash(req, "Şifreniz güncellendi.", "ok")
        conn.close()
        return redirect("/profil/sifre")
    return render_template("ayarlar/sifre.html")
