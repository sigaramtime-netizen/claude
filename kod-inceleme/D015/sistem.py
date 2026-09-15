# -*- coding: utf-8 -*-
"""D015-C — Sistem Bilgi Paneli (v1.46.0, yalnız Admin).

`GET /sistem/bilgi`: sürüm + commit hash, DB bütünlük/FK/boyut/tablo sayıları,
son yedek, şema bilgisi ve `/api/saglik` canlı gömülü durumu.
"""
import datetime
import os
import sqlite3
import subprocess

import db
import yedek
from config import BASE, DATA_DIR, DB_PATH, SURUM, SURUM_TARIHI
from core import route, render_template


def _commit_bilgi():
    """Git commit hash + tarih (repo dışı çalışmada 'bilinmiyor')."""
    kok = os.path.dirname(BASE)
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=kok, capture_output=True,
                             text=True, timeout=5)
        h = (out.stdout or "").strip()
        out2 = subprocess.run(["git", "log", "-1", "--format=%ci %s"], cwd=kok,
                              capture_output=True, text=True, timeout=5)
        return (h or "bilinmiyor"), ((out2.stdout or "").strip() or "—")
    except Exception:  # noqa: BLE001
        return "bilinmiyor", "—"


@route(r"/sistem/bilgi", roles=("Admin",))
def sistem_bilgi(req):
    conn = db.get_conn()
    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
    except Exception:  # noqa: BLE001
        integrity = "hata"
    try:
        fk_sorun = len(conn.execute("PRAGMA foreign_key_check").fetchall())
    except Exception:  # noqa: BLE001
        fk_sorun = -1
    tablolar = [r[0] for r in conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name").fetchall()]
    sayilar = []
    for t in tablolar:
        try:
            n = conn.execute(f'SELECT COUNT(*) c FROM "{t}"').fetchone()["c"]
        except Exception:  # noqa: BLE001
            n = -1
        sayilar.append({"ad": t, "satir": n})
    try:
        user_version = conn.execute("PRAGMA user_version").fetchone()[0]
    except Exception:  # noqa: BLE001
        user_version = -1
    try:
        conn.execute("SELECT 1").fetchone()
        db_durum = "ok"
    except Exception:  # noqa: BLE001
        db_durum = "hata"
    conn.close()

    boyut = 0
    for ek in ("", "-wal", "-shm", "-journal"):
        try:
            boyut += os.path.getsize(DB_PATH + ek)
        except OSError:
            pass
    try:
        yedekler = yedek._liste()
    except Exception:  # noqa: BLE001
        yedekler = []
    son_yedek = yedekler[0] if yedekler else None
    if son_yedek:
        son_yedek = dict(son_yedek)
        try:
            son_yedek["tarih"] = datetime.datetime.fromtimestamp(
                son_yedek["mtime"]).strftime("%d.%m.%Y %H:%M")
        except (TypeError, ValueError, OSError):
            son_yedek["tarih"] = "—"
    commit_hash, commit_aciklama = _commit_bilgi()
    return render_template(
        "sistem/bilgi.html", surum=SURUM, surum_tarihi=SURUM_TARIHI,
        commit_hash=commit_hash, commit_aciklama=commit_aciklama,
        integrity=integrity, fk_sorun=fk_sorun, db_durum=db_durum,
        tablo_sayisi=len(tablolar), sayilar=sayilar, boyut=boyut,
        sqlite_surum=sqlite3.sqlite_version, user_version=user_version,
        son_yedek=son_yedek, yedek_sayisi=len(yedekler),
        sirket_id=db.sirket_id(req),
        bugun=datetime.date.today().isoformat())


def register():
    pass
