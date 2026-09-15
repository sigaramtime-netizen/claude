# -*- coding: utf-8 -*-
"""Veritabanı katmanı: bağlantı, şema oluşturma ve örnek (seed) veri."""
import os
import re
import sqlite3
import hashlib
import secrets
import datetime

from config import DB_PATH, DATA_DIR, FIRMA_ADI, PARA_BIRIMLERI

SCHEMA_VERSION = 2

SCHEMA = """
CREATE TABLE IF NOT EXISTS meta (
    anahtar TEXT PRIMARY KEY,
    deger  TEXT
);

CREATE TABLE IF NOT EXISTS kullanici (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_adi TEXT NOT NULL UNIQUE,
    ad_soyad      TEXT NOT NULL,
    email         TEXT,
    sifre_hash    TEXT NOT NULL,
    rol           TEXT NOT NULL CHECK (rol IN ('Admin','Muhasebe','Satis','Servis','Depo')),
    aktif         INTEGER NOT NULL DEFAULT 1,
    sube_id       INTEGER REFERENCES sube(id),
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    basarisiz_giris_sayisi INTEGER NOT NULL DEFAULT 0,
    kilit_bitis             TEXT
);

CREATE TABLE IF NOT EXISTS sessionler (
    token        TEXT PRIMARY KEY,
    kullanici_id INTEGER NOT NULL REFERENCES kullanici(id),
    olusturma    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    son_erisim   TEXT
);

CREATE TABLE IF NOT EXISTS audit_log (
    id             INTEGER PRIMARY KEY AUTOINCREMENT,
    kullanici_id   INTEGER,
    kullanici_adi  TEXT,
    tablo          TEXT,
    kayit_id       INTEGER,
    islem          TEXT,
    detay          TEXT,
    tarih          TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS bildirimler (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    tip           TEXT,
    baslik        TEXT,
    mesaj         TEXT,
    ilgili_tablo  TEXT,
    ilgili_id     INTEGER,
    okundu        INTEGER NOT NULL DEFAULT 0,
    olusturma     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS bildirim_gonderim (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    bildirim_id   INTEGER,
    kanal         TEXT NOT NULL,
    hedef         TEXT,
    baslik        TEXT,
    mesaj         TEXT,
    ilgili_tablo  TEXT,
    ilgili_id     INTEGER,
    durum         TEXT NOT NULL DEFAULT 'Bekliyor',
    olusturma     TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS cari_grup (
    id         INTEGER PRIMARY KEY AUTOINCREMENT,
    ad         TEXT NOT NULL,
    tip        TEXT NOT NULL DEFAULT 'Bölge' CHECK (tip IN ('Bölge','Segment','Sadakat')),
    aciklama   TEXT,
    aktif      INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS cari_kart (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    kod           TEXT UNIQUE,
    unvan         TEXT NOT NULL,
    kisa_ad       TEXT,
    tip           TEXT NOT NULL DEFAULT 'Musteri' CHECK (tip IN ('Musteri','Tedarikci','HerIkisi')),
    vergi_dairesi TEXT,
    vergi_no      TEXT,
    tckn          TEXT,
    adres         TEXT,
    il            TEXT,
    ilce          TEXT,
    telefon       TEXT,
    gsm           TEXT,
    email         TEXT,
    yetkili       TEXT,
    kredi_limiti  REAL NOT NULL DEFAULT 0,
    para_birimi   TEXT NOT NULL DEFAULT 'TRY',
    iskonto_orani REAL NOT NULL DEFAULT 0,
    grup_id       INTEGER REFERENCES cari_grup(id),
    not_          TEXT,
    aktif         INTEGER NOT NULL DEFAULT 1,
    created_by    INTEGER,
    updated_by    INTEGER,
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at    TEXT
);

CREATE TABLE IF NOT EXISTS cari_hareket (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    cari_id         INTEGER NOT NULL REFERENCES cari_kart(id),
    tarih           TEXT NOT NULL,
    vade            TEXT,
    belge_tipi      TEXT NOT NULL DEFAULT 'Diğer',
    belge_no        TEXT,
    aciklama        TEXT,
    borc            REAL NOT NULL DEFAULT 0,
    alacak          REAL NOT NULL DEFAULT 0,
    para_birimi     TEXT NOT NULL DEFAULT 'TRY',
    doviz_kur       REAL,
    ilgili_modul    TEXT,
    ilgili_kayit_id INTEGER,
    created_by      INTEGER,
    created_at      TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS notlar (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    ilgili_tablo  TEXT NOT NULL,
    ilgili_id     INTEGER NOT NULL,
    metin         TEXT NOT NULL,
    etiketler     TEXT,
    hatirlatma    TEXT,
    hatirlatildi  INTEGER NOT NULL DEFAULT 0,
    kullanici_id  INTEGER,
    created_at    TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS kategori (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ust_id INTEGER REFERENCES kategori(id),
    ad TEXT NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS marka (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL UNIQUE,
    aktif INTEGER NOT NULL DEFAULT 1
);

-- D012-X — Para birimi (config sabit listesi → DB tablo). K1: sirket_id izolasyonlu.
CREATE TABLE IF NOT EXISTS para_birimi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT NOT NULL,
    ad TEXT NOT NULL DEFAULT '',
    aktif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    sirket_id INTEGER NOT NULL DEFAULT 1,
    UNIQUE(sirket_id, kod)
);

-- D012-X — Birim (config sabit listesi → DB tablo). K1: sirket_id izolasyonlu.
CREATE TABLE IF NOT EXISTS birim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    sirket_id INTEGER NOT NULL DEFAULT 1,
    UNIQUE(sirket_id, ad)
);

CREATE TABLE IF NOT EXISTS sube (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT UNIQUE,
    ad TEXT NOT NULL,
    il TEXT,
    ilce TEXT,
    adres TEXT,
    telefon TEXT,
    aktif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS depo (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT UNIQUE,
    ad TEXT NOT NULL,
    tip TEXT NOT NULL DEFAULT 'Ana' CHECK (tip IN ('Ana','Mağaza','Servis')),
    aktif INTEGER NOT NULL DEFAULT 1,
    sube_id INTEGER REFERENCES sube(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- NOT: İleride eklenecek "fiyat_kural" tablosu (stok_id, cari_id, cari_grup_id nullable,
-- baslangic_tarih, bitis_tarih, tip, deger, oncelik) için stok_kart üzerinde bu alanlarla
-- çakışacak bir sütun adı kullanılmaz; kural tablosu ayrı tutulacak.
CREATE TABLE IF NOT EXISTS stok_kart (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT UNIQUE,
    ad TEXT NOT NULL,
    barkod TEXT,
    marka_id INTEGER REFERENCES marka(id),
    kategori_id INTEGER REFERENCES kategori(id),
    birim TEXT NOT NULL DEFAULT 'Adet',
    kdv_orani REAL NOT NULL DEFAULT 20,
    otv_orani REAL NOT NULL DEFAULT 0,
    alis_fiyat REAL NOT NULL DEFAULT 0,
    satis_fiyat REAL NOT NULL DEFAULT 0,
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    iskonto_orani REAL NOT NULL DEFAULT 0,
    kritik_stok REAL NOT NULL DEFAULT 0,
    seri_lot_takibi INTEGER NOT NULL DEFAULT 0,
    varyant_takibi INTEGER NOT NULL DEFAULT 0,
    teknik_ozellikler TEXT,
    aktif INTEGER NOT NULL DEFAULT 1,
    created_by INTEGER,
    updated_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS stok_varyant (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
    varyant_kodu TEXT,
    ad TEXT NOT NULL,
    ozellikler TEXT,
    barkod TEXT,
    alis_fiyat REAL NOT NULL DEFAULT 0,
    satis_fiyat REAL NOT NULL DEFAULT 0,
    kritik_stok REAL NOT NULL DEFAULT 0,
    aktif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS stok_seviye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    depo_id INTEGER NOT NULL REFERENCES depo(id),
    miktar REAL NOT NULL DEFAULT 0,
    rezerve REAL NOT NULL DEFAULT 0,
    min_stok REAL NOT NULL DEFAULT 0,
    max_stok REAL NOT NULL DEFAULT 0,
    UNIQUE(stok_id, varyant_id, depo_id)
);

-- Kartoteks'in beslendiği TEK kronolojik hareket tablosu (salt-okunur kaynak).
CREATE TABLE IF NOT EXISTS stok_hareket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    depo_id INTEGER NOT NULL REFERENCES depo(id),
    tarih TEXT NOT NULL,
    islem_tipi TEXT NOT NULL,
    miktar REAL NOT NULL DEFAULT 0,
    birim_maliyet REAL,
    aciklama TEXT,
    belge_no TEXT,
    seri_nolar TEXT,
    ilgili_modul TEXT,
    ilgili_kayit_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS stok_seri (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    seri_no TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'Stokta',
    depo_id INTEGER,
    giris_tarihi TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    cikis_tarihi TEXT,
    ilgili_modul TEXT,
    ilgili_kayit_id INTEGER,
    UNIQUE(stok_id, seri_no)
);

CREATE TABLE IF NOT EXISTS stok_sayim (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    depo_id INTEGER NOT NULL REFERENCES depo(id),
    tarih TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    durum TEXT NOT NULL DEFAULT 'Taslak' CHECK (durum IN ('Taslak','Tamamlandi')),
    aciklama TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS stok_sayim_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sayim_id INTEGER NOT NULL REFERENCES stok_sayim(id),
    stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    sistem_miktar REAL NOT NULL DEFAULT 0,
    sayilan_miktar REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS stok_tedarikci (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
    cari_id INTEGER NOT NULL REFERENCES cari_kart(id),
    tedarikci_kod TEXT,
    alis_fiyat REAL,
    oncelik INTEGER NOT NULL DEFAULT 0,
    aktif INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    UNIQUE(stok_id, cari_id)
);

CREATE TABLE IF NOT EXISTS depo_transfer (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kaynak_depo_id INTEGER NOT NULL REFERENCES depo(id),
    hedef_depo_id INTEGER NOT NULL REFERENCES depo(id),
    tarih TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'Taslak' CHECK (durum IN ('Taslak','Tamamlandi')),
    aciklama TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS depo_transfer_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    transfer_id INTEGER NOT NULL REFERENCES depo_transfer(id),
    stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    miktar REAL NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS kasa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT UNIQUE,
    ad TEXT NOT NULL,
    aktif INTEGER NOT NULL DEFAULT 1,
    sube_id INTEGER REFERENCES sube(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- islem_tipi yönü belirler: Açılış Bakiyesi(+), Nakit Girişi(+), Banka→Kasa(+),
-- Nakit Çıkışı(−), Kasa→Banka(−). tutar her zaman pozitif tutulur.
CREATE TABLE IF NOT EXISTS kasa_hareket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kasa_id INTEGER NOT NULL REFERENCES kasa(id),
    tarih TEXT NOT NULL,
    islem_tipi TEXT NOT NULL,
    tutar REAL NOT NULL DEFAULT 0,
    cari_id INTEGER REFERENCES cari_kart(id),
    aciklama TEXT,
    belge_no TEXT,
    ilgili_modul TEXT,
    ilgili_kayit_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS banka_hesap (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    kod TEXT UNIQUE,
    ad TEXT NOT NULL,
    banka_adi TEXT,
    sube TEXT,
    iban TEXT,
    hesap_no TEXT,
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    aktif INTEGER NOT NULL DEFAULT 1,
    sube_id INTEGER REFERENCES sube(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- islem_tipi yönü belirler: Açılış Bakiyesi(+), Havale/EFT Girişi(+), Kasa → Banka(+),
-- Banka Ekstresi (Giriş)(+); Havale/EFT Çıkışı(−), Banka → Kasa(−), Banka Ekstresi (Çıkış)(−).
CREATE TABLE IF NOT EXISTS banka_hareket (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    banka_hesap_id INTEGER NOT NULL REFERENCES banka_hesap(id),
    tarih TEXT NOT NULL,
    islem_tipi TEXT NOT NULL,
    tutar REAL NOT NULL DEFAULT 0,
    cari_id INTEGER REFERENCES cari_kart(id),
    aciklama TEXT,
    belge_no TEXT,
    ilgili_modul TEXT,
    ilgili_kayit_id INTEGER,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

-- ============ FAZ 2 — Satış Döngüsü belgeleri (K1: hepsi nullable sube_id taşır) ============
CREATE TABLE IF NOT EXISTS teklif (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teklif_no TEXT UNIQUE,
    cari_id INTEGER NOT NULL REFERENCES cari_kart(id),
    sube_id INTEGER REFERENCES sube(id),
    tarih TEXT NOT NULL,
    gecerlilik_tarihi TEXT,
    durum TEXT NOT NULL DEFAULT 'Taslak' CHECK (durum IN ('Taslak','Gönderildi','Onaylandı','Reddedildi','Süresi Doldu')),
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    doviz_kur REAL,
    ara_toplam REAL NOT NULL DEFAULT 0,
    iskonto_toplam REAL NOT NULL DEFAULT 0,
    kdv_toplam REAL NOT NULL DEFAULT 0,
    genel_toplam REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    kdv_dahil INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS teklif_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teklif_id INTEGER NOT NULL REFERENCES teklif(id),
    stok_id INTEGER REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    miktar REAL NOT NULL DEFAULT 1,
    birim_fiyat REAL NOT NULL DEFAULT 0,
    iskonto_orani REAL NOT NULL DEFAULT 0,
    kdv_orani REAL NOT NULL DEFAULT 20,
    kdv_dahil INTEGER,
    tutar REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    birim TEXT,
    goruntu_adi TEXT
);

-- Sipariş (K8: kaynak_teklif_id → teklif.id nullable FK; K1: sube_id nullable)
-- tip: Musteri = müşteriye satış siparişi, Alis = tedarikçiye satın alma siparişi.
CREATE TABLE IF NOT EXISTS siparis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    siparis_no TEXT UNIQUE,
    tip TEXT NOT NULL DEFAULT 'Musteri' CHECK (tip IN ('Musteri','Alis')),
    cari_id INTEGER NOT NULL REFERENCES cari_kart(id),
    sube_id INTEGER REFERENCES sube(id),
    depo_id INTEGER REFERENCES depo(id),
    kaynak_teklif_id INTEGER REFERENCES teklif(id),
    tarih TEXT NOT NULL,
    teslim_tarihi TEXT,
    durum TEXT NOT NULL DEFAULT 'Bekliyor' CHECK (durum IN ('Bekliyor','Onaylandı','Kısmi','Tamamlandı','İptal')),
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    doviz_kur REAL,
    ara_toplam REAL NOT NULL DEFAULT 0,
    iskonto_toplam REAL NOT NULL DEFAULT 0,
    kdv_toplam REAL NOT NULL DEFAULT 0,
    genel_toplam REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    kdv_dahil INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS siparis_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    siparis_id INTEGER NOT NULL REFERENCES siparis(id),
    stok_id INTEGER REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    miktar REAL NOT NULL DEFAULT 1,
    teslim_edilen REAL NOT NULL DEFAULT 0,
    kalan_iptal REAL NOT NULL DEFAULT 0,
    birim_fiyat REAL NOT NULL DEFAULT 0,
    iskonto_orani REAL NOT NULL DEFAULT 0,
    kdv_orani REAL NOT NULL DEFAULT 20,
    kdv_dahil INTEGER,
    tutar REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    birim TEXT,
    goruntu_adi TEXT
);

-- Satın Alma Talebi (B1 — Satın Alma Yönetimi giriş noktası).
-- durum: Taslak / Onay Bekliyor / Onaylandı / Reddedildi / Siparişe Dönüştü.
-- K8: donusen_siparis_id → siparis.id (nullable); onaylı talepten tek seferlik SAP üretilir (K10 deseni).
-- K13: talep_no = "SAT-{YYYY}-{NNN}" (şirket başına bağımsız sayaç, UNIQUE(sirket_id, talep_no)).
CREATE TABLE IF NOT EXISTS satin_alma_talebi (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    talep_no TEXT NOT NULL,
    sube_id INTEGER REFERENCES sube(id),
    depo_id INTEGER REFERENCES depo(id),
    tedarikci_id INTEGER REFERENCES cari_kart(id),
    kaynak TEXT NOT NULL DEFAULT 'Yurt İçi' CHECK (kaynak IN ('Yurt İçi','Yurt Dışı')),
    gerekce TEXT,
    durum TEXT NOT NULL DEFAULT 'Taslak' CHECK (durum IN ('Taslak','Onay Bekliyor','Onaylandı','Reddedildi','Siparişe Dönüştü')),
    talep_eden_id INTEGER,
    onaylayan_id INTEGER,
    onay_tarihi TEXT,
    red_nedeni TEXT,
    donusen_siparis_id INTEGER REFERENCES siparis(id),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    sirket_id INTEGER NOT NULL DEFAULT 1,
    UNIQUE(sirket_id, talep_no)
);

CREATE TABLE IF NOT EXISTS satin_alma_talebi_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    talep_id INTEGER NOT NULL REFERENCES satin_alma_talebi(id),
    stok_id INTEGER REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    miktar REAL NOT NULL DEFAULT 1,
    birim TEXT,
    tahmini_fiyat REAL NOT NULL DEFAULT 0,
    oncelik TEXT NOT NULL DEFAULT 'Normal' CHECK (oncelik IN ('Normal','Acil')),
    aciklama TEXT,
    sirket_id INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_talep_sirket       ON satin_alma_talebi(sirket_id);
CREATE INDEX IF NOT EXISTS idx_talep_kalem_talep  ON satin_alma_talebi_kalem(talep_id);

-- B2 — Alınan Teklif (Satın Alma Yönetimi)
-- durum: Taslak / Alındı / Kazanan / Elendi / Siparişe Dönüştü.
-- para_birimi + doviz_kur: teklif döviz (USD/EUR/GBP) olabilir; toplamlar para birimi cinsinden,
--   TRY karşılığı = genel_toplam × doviz_kur (K2 konvansiyonu, fatura/siparis ile aynı).
-- K8: donusen_siparis_id → siparis.id (nullable); kazanan tekliften tek seferlik SAP.
-- K13: teklif_no = "ALT-{YYYY}-{NNN}" (şirket başına bağımsız sayaç).
CREATE TABLE IF NOT EXISTS alinan_teklif (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teklif_no TEXT NOT NULL,
    talep_id INTEGER REFERENCES satin_alma_talebi(id),
    tedarikci_id INTEGER NOT NULL REFERENCES cari_kart(id),
    sube_id INTEGER REFERENCES sube(id),
    depo_id INTEGER REFERENCES depo(id),
    tarih TEXT NOT NULL DEFAULT (date('now','localtime')),
    gecerlilik_tarihi TEXT,
    teslim_suresi_gun INTEGER,
    odeme_vadesi_gun INTEGER,
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    doviz_kur REAL NOT NULL DEFAULT 1,
    durum TEXT NOT NULL DEFAULT 'Taslak'
        CHECK (durum IN ('Taslak','Alındı','Kazanan','Elendi','Siparişe Dönüştü')),
    ara_toplam REAL NOT NULL DEFAULT 0,
    iskonto_toplam REAL NOT NULL DEFAULT 0,
    kdv_toplam REAL NOT NULL DEFAULT 0,
    genel_toplam REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    donusen_siparis_id INTEGER REFERENCES siparis(id),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    sirket_id INTEGER NOT NULL DEFAULT 1,
    UNIQUE(sirket_id, teklif_no)
);

CREATE TABLE IF NOT EXISTS alinan_teklif_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teklif_id INTEGER NOT NULL REFERENCES alinan_teklif(id),
    stok_id INTEGER REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    miktar REAL NOT NULL DEFAULT 1,
    birim TEXT,
    birim_fiyat REAL NOT NULL DEFAULT 0,
    iskonto_orani REAL NOT NULL DEFAULT 0,
    kdv_orani REAL NOT NULL DEFAULT 0,
    tutar REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    sirket_id INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_alt_sirket        ON alinan_teklif(sirket_id);
CREATE INDEX IF NOT EXISTS idx_alt_talep         ON alinan_teklif(talep_id);
CREATE INDEX IF NOT EXISTS idx_alt_kalem_teklif  ON alinan_teklif_kalem(teklif_id);

-- C — POS (Satış Noktası)
-- pos_terminal: kasa (nakit) + banka hesabı (kart/havale) + komisyon + taksit + stok düşüm deposu.
-- POS satışı doğrudan Onaylı Satış Faturası üretir (cari + stok + yevmiye);
--   ödeme dağılımı pos_satis_odeme'de izlenir (K2: cari kapanışı ödeme tipine göre).
CREATE TABLE IF NOT EXISTS pos_terminal (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ad TEXT NOT NULL,
    kasa_id INTEGER REFERENCES kasa(id),
    banka_id INTEGER REFERENCES banka_hesap(id),
    depo_id INTEGER REFERENCES depo(id),
    komisyon_orani REAL NOT NULL DEFAULT 0,
    max_taksit INTEGER NOT NULL DEFAULT 1,
    aktif INTEGER NOT NULL DEFAULT 1,
    sube_id INTEGER REFERENCES sube(id),
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    sirket_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS pos_satis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fatura_id INTEGER NOT NULL REFERENCES fatura(id),
    terminal_id INTEGER REFERENCES pos_terminal(id),
    taksit INTEGER NOT NULL DEFAULT 1,
    komisyon_toplam REAL NOT NULL DEFAULT 0,
    veresiye_tutar REAL NOT NULL DEFAULT 0,
    sube_id INTEGER REFERENCES sube(id),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    sirket_id INTEGER NOT NULL DEFAULT 1,
    UNIQUE(fatura_id)
);

CREATE TABLE IF NOT EXISTS pos_satis_odeme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    pos_satis_id INTEGER NOT NULL REFERENCES pos_satis(id),
    tip TEXT NOT NULL CHECK (tip IN ('Nakit','Kart','Havale','Veresiye','Cek','Senet')),
    tutar REAL NOT NULL DEFAULT 0,
    komisyon REAL NOT NULL DEFAULT 0,
    cek_senet_id INTEGER REFERENCES cek_senet(id),
    sirket_id INTEGER NOT NULL DEFAULT 1
);

CREATE INDEX IF NOT EXISTS idx_pos_terminal_sirket ON pos_terminal(sirket_id);
CREATE INDEX IF NOT EXISTS idx_pos_satis_fatura    ON pos_satis(fatura_id);
CREATE INDEX IF NOT EXISTS idx_pos_odeme_satis     ON pos_satis_odeme(pos_satis_id);

-- D — Bakım Sözleşmesi
-- bakim_sozlesme: cihaz bazlı periyodik bakım sözleşmesi (cari + dönem + periyot + bedel).
--   Fatura üretimi → Onaylı Satış Faturası (cari + yevmiye); dönem bakim_sozlesme_fatura'da izlenir.
--   İş emri → servis_kayit.bakim_sozlesme_id (kapsam dahili → garanti_kapsami=1, ücretsiz).
CREATE TABLE IF NOT EXISTS bakim_sozlesme (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sozlesme_no TEXT NOT NULL,
    cari_id INTEGER NOT NULL REFERENCES cari_kart(id),
    baslangic TEXT NOT NULL,
    bitis TEXT NOT NULL,
    periyot TEXT NOT NULL DEFAULT 'Yillik' CHECK (periyot IN ('Aylik','3 Aylik','6 Aylik','Yillik')),
    bedel REAL NOT NULL DEFAULT 0,
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    durum TEXT NOT NULL DEFAULT 'Aktif' CHECK (durum IN ('Aktif','İptal')),
    aciklama TEXT,
    sube_id INTEGER REFERENCES sube(id),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    sirket_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bakim_sozlesme_cihaz (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sozlesme_id INTEGER NOT NULL REFERENCES bakim_sozlesme(id),
    stok_id INTEGER REFERENCES stok_kart(id),
    seri_no TEXT,
    cihaz_aciklama TEXT,
    sirket_id INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS bakim_sozlesme_fatura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    sozlesme_id INTEGER NOT NULL REFERENCES bakim_sozlesme(id),
    fatura_id INTEGER NOT NULL REFERENCES fatura(id),
    donem TEXT NOT NULL,
    sirket_id INTEGER NOT NULL DEFAULT 1,
    UNIQUE(fatura_id),
    UNIQUE(sozlesme_id, donem)
);

CREATE INDEX IF NOT EXISTS idx_bakim_soz_sirket   ON bakim_sozlesme(sirket_id);
CREATE INDEX IF NOT EXISTS idx_bakim_cihaz_soz    ON bakim_sozlesme_cihaz(sozlesme_id);
CREATE INDEX IF NOT EXISTS idx_bakim_fat_soz      ON bakim_sozlesme_fatura(sozlesme_id);

-- E — CRM: Aktivite / Görev takibi
-- Arama · Toplantı · Görev · Takip; cari + sorumlu + tarih + hatırlatma + durum/öncelik.
-- Hatırlatma: app.py'deki _crm_aktivite_tarama günü gelen hatırlatmayı bildirime çevirir.
CREATE TABLE IF NOT EXISTS crm_aktivite (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    aktivite_no TEXT NOT NULL,
    tip TEXT NOT NULL DEFAULT 'Gorev' CHECK (tip IN ('Arama','Toplanti','Gorev','Takip')),
    baslik TEXT NOT NULL,
    aciklama TEXT,
    cari_id INTEGER REFERENCES cari_kart(id),
    sorumlu_id INTEGER REFERENCES kullanici(id),
    tarih TEXT NOT NULL,
    saat TEXT,
    hatirlatma_tarihi TEXT,
    hatirlatildi INTEGER NOT NULL DEFAULT 0,
    durum TEXT NOT NULL DEFAULT 'Planlandı' CHECK (durum IN ('Planlandı','Tamamlandı','İptal')),
    oncelik TEXT NOT NULL DEFAULT 'Normal' CHECK (oncelik IN ('Dusuk','Normal','Yuksek')),
    sube_id INTEGER REFERENCES sube(id),
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    sirket_id INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX IF NOT EXISTS idx_crm_akt_sirket   ON crm_aktivite(sirket_id);
CREATE INDEX IF NOT EXISTS idx_crm_akt_cari     ON crm_aktivite(cari_id);
CREATE INDEX IF NOT EXISTS idx_crm_akt_sorumlu  ON crm_aktivite(sorumlu_id);
CREATE INDEX IF NOT EXISTS idx_crm_akt_durum    ON crm_aktivite(durum);
CREATE INDEX IF NOT EXISTS idx_crm_akt_tarih    ON crm_aktivite(tarih);

-- İrsaliye (K8: kaynak_siparis_id → siparis.id nullable FK; K1: sube_id nullable)
-- tip: Satis = müşteriye sevk (stok çıkışı), Alis = tedarikçiden giriş, Transfer = depo→depo.
CREATE TABLE IF NOT EXISTS irsaliye (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    irsaliye_no TEXT UNIQUE,
    tip TEXT NOT NULL DEFAULT 'Satis' CHECK (tip IN ('Satis','Alis','Transfer')),
    cari_id INTEGER REFERENCES cari_kart(id),
    sube_id INTEGER REFERENCES sube(id),
    depo_id INTEGER REFERENCES depo(id),
    hedef_depo_id INTEGER REFERENCES depo(id),
    kaynak_siparis_id INTEGER REFERENCES siparis(id),
    tarih TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'Taslak' CHECK (durum IN ('Taslak','Onaylandı','İptal')),
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    ara_toplam REAL NOT NULL DEFAULT 0,
    iskonto_toplam REAL NOT NULL DEFAULT 0,
    kdv_toplam REAL NOT NULL DEFAULT 0,
    genel_toplam REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    kdv_dahil INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS irsaliye_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    irsaliye_id INTEGER NOT NULL REFERENCES irsaliye(id),
    stok_id INTEGER REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    miktar REAL NOT NULL DEFAULT 1,
    birim_fiyat REAL NOT NULL DEFAULT 0,
    iskonto_orani REAL NOT NULL DEFAULT 0,
    kdv_orani REAL NOT NULL DEFAULT 20,
    kdv_dahil INTEGER,
    tutar REAL NOT NULL DEFAULT 0,
    aciklama TEXT
);

CREATE TABLE IF NOT EXISTS fatura (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fatura_no TEXT UNIQUE,
    tip TEXT NOT NULL DEFAULT 'Satis' CHECK (tip IN ('Satis','Alis')),
    cari_id INTEGER REFERENCES cari_kart(id),
    sube_id INTEGER REFERENCES sube(id),
    kaynak_irsaliye_id INTEGER REFERENCES irsaliye(id),
    tarih TEXT NOT NULL,
    vade TEXT,
    durum TEXT NOT NULL DEFAULT 'Taslak' CHECK (durum IN ('Taslak','Onaylandı','İptal')),
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    doviz_kur REAL NOT NULL DEFAULT 1,
    ara_toplam REAL NOT NULL DEFAULT 0,
    iskonto_toplam REAL NOT NULL DEFAULT 0,
    kdv_toplam REAL NOT NULL DEFAULT 0,
    genel_toplam REAL NOT NULL DEFAULT 0,
    aciklama TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT,
    kdv_dahil INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS fatura_kalem (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    fatura_id INTEGER NOT NULL REFERENCES fatura(id),
    stok_id INTEGER REFERENCES stok_kart(id),
    varyant_id INTEGER NOT NULL DEFAULT 0,
    miktar REAL NOT NULL DEFAULT 1,
    birim_fiyat REAL NOT NULL DEFAULT 0,
    iskonto_orani REAL NOT NULL DEFAULT 0,
    kdv_orani REAL NOT NULL DEFAULT 20,
    kdv_dahil INTEGER,
    tutar REAL NOT NULL DEFAULT 0,
    aciklama TEXT
);

CREATE TABLE IF NOT EXISTS cek_senet (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    no TEXT NOT NULL,
    tip TEXT NOT NULL DEFAULT 'Alinan' CHECK (tip IN ('Alinan','Verilen')),
    tur TEXT NOT NULL DEFAULT 'Cek' CHECK (tur IN ('Cek','Senet')),
    cari_id INTEGER REFERENCES cari_kart(id),
    sube_id INTEGER REFERENCES sube(id),
    banka TEXT,
    sube_ad TEXT,
    tutar REAL NOT NULL DEFAULT 0,
    para_birimi TEXT NOT NULL DEFAULT 'TRY',
    doviz_kur REAL,
    keside_tarihi TEXT,
    vade TEXT NOT NULL,
    durum TEXT NOT NULL DEFAULT 'Bekliyor' CHECK (durum IN ('Bekliyor','Tahsile Verildi','Tahsil Edildi','Ödendi','Karşılıksız','Ciro','İptal')),
    aciklama TEXT,
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
    updated_at TEXT
);

CREATE TABLE IF NOT EXISTS ek_dosya (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ilgili_modul TEXT NOT NULL,
    ilgili_kayit_id INTEGER NOT NULL,
    dosya_adi TEXT NOT NULL,
    dosya_yolu TEXT NOT NULL,
    dosya_tipi TEXT NOT NULL,
    boyut INTEGER NOT NULL DEFAULT 0,
    aciklama TEXT,
    yukleyen_kullanici INTEGER,
    tarih TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE TABLE IF NOT EXISTS doviz_kur (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    para_birimi TEXT NOT NULL,
    kur REAL NOT NULL,
    tarih TEXT NOT NULL,
    kaynak TEXT NOT NULL DEFAULT 'Manuel',
    created_by INTEGER,
    created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
);

CREATE INDEX IF NOT EXISTS idx_cari_hareket_cari ON cari_hareket(cari_id);
CREATE INDEX IF NOT EXISTS idx_audit_tarih       ON audit_log(tarih);
CREATE INDEX IF NOT EXISTS idx_bildirim_okunmamis ON bildirimler(okundu);
CREATE INDEX IF NOT EXISTS idx_bildirim_gonderim ON bildirim_gonderim(bildirim_id);
CREATE INDEX IF NOT EXISTS idx_notlar_ilgili     ON notlar(ilgili_tablo, ilgili_id);
CREATE INDEX IF NOT EXISTS idx_stok_hareket_stok ON stok_hareket(stok_id);
CREATE INDEX IF NOT EXISTS idx_stok_hareket_tarih ON stok_hareket(tarih);
CREATE INDEX IF NOT EXISTS idx_stok_seviye_stok  ON stok_seviye(stok_id);
CREATE INDEX IF NOT EXISTS idx_kasa_hareket_kasa ON kasa_hareket(kasa_id);
CREATE INDEX IF NOT EXISTS idx_kasa_hareket_tarih ON kasa_hareket(tarih);
CREATE INDEX IF NOT EXISTS idx_banka_hareket_hesap ON banka_hareket(banka_hesap_id);
CREATE INDEX IF NOT EXISTS idx_banka_hareket_tarih ON banka_hareket(tarih);
CREATE INDEX IF NOT EXISTS idx_teklif_cari ON teklif(cari_id);
CREATE INDEX IF NOT EXISTS idx_teklif_kalem_teklif ON teklif_kalem(teklif_id);
CREATE INDEX IF NOT EXISTS idx_siparis_cari ON siparis(cari_id);
CREATE INDEX IF NOT EXISTS idx_siparis_kaynak ON siparis(kaynak_teklif_id);
CREATE INDEX IF NOT EXISTS idx_siparis_kalem_siparis ON siparis_kalem(siparis_id);
CREATE INDEX IF NOT EXISTS idx_irsaliye_cari ON irsaliye(cari_id);
CREATE INDEX IF NOT EXISTS idx_irsaliye_kaynak ON irsaliye(kaynak_siparis_id);
CREATE INDEX IF NOT EXISTS idx_irsaliye_kalem_irsaliye ON irsaliye_kalem(irsaliye_id);
CREATE INDEX IF NOT EXISTS idx_fatura_cari ON fatura(cari_id);
CREATE INDEX IF NOT EXISTS idx_fatura_kaynak ON fatura(kaynak_irsaliye_id);
CREATE INDEX IF NOT EXISTS idx_fatura_kalem_fatura ON fatura_kalem(fatura_id);
CREATE INDEX IF NOT EXISTS idx_cek_senet_cari ON cek_senet(cari_id);
CREATE INDEX IF NOT EXISTS idx_cek_senet_vade ON cek_senet(vade);
CREATE INDEX IF NOT EXISTS idx_ek_dosya_ilgili ON ek_dosya(ilgili_modul, ilgili_kayit_id);
CREATE INDEX IF NOT EXISTS idx_doviz_kur_pb_tarih ON doviz_kur(para_birimi, tarih);
"""


def get_conn():
    """Her çağrıda yeni bir bağlantı döndür (thread-safe)."""
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 8000")
    return conn


def init_db():
    os.makedirs(DATA_DIR, exist_ok=True)
    conn = get_conn()
    conn.execute("PRAGMA journal_mode = WAL")
    conn.executescript(SCHEMA)
    _migrate(conn)
    conn.execute(
        "INSERT OR IGNORE INTO meta(anahtar, deger) VALUES('sema_versiyonu', ?)",
        (str(SCHEMA_VERSION),),
    )
    conn.commit()
    conn.close()


def _migrate(conn):
    """Var olan veritabanlarına yeni sütun ekleme (CREATE IF NOT EXISTS bunu yapmaz)."""
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(kasa_hareket)")}
    if "cari_id" not in cols:
        conn.execute("ALTER TABLE kasa_hareket ADD COLUMN cari_id INTEGER REFERENCES cari_kart(id)")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(depo)")}
    if "sube_id" not in cols:
        conn.execute("ALTER TABLE depo ADD COLUMN sube_id INTEGER REFERENCES sube(id)")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(kullanici)")}
    if "sube_id" not in cols:
        conn.execute("ALTER TABLE kullanici ADD COLUMN sube_id INTEGER REFERENCES sube(id)")
    # D009 — kaba kuvvet koruması: kullanıcı bazında başarısız giriş sayacı + kilit bitişi.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(kullanici)")}
    if "basarisiz_giris_sayisi" not in cols:
        conn.execute("ALTER TABLE kullanici ADD COLUMN basarisiz_giris_sayisi INTEGER NOT NULL DEFAULT 0")
    if "kilit_bitis" not in cols:
        conn.execute("ALTER TABLE kullanici ADD COLUMN kilit_bitis TEXT")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(kasa)")}
    if "sube_id" not in cols:
        conn.execute("ALTER TABLE kasa ADD COLUMN sube_id INTEGER REFERENCES sube(id)")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(banka_hesap)")}
    if "sube_id" not in cols:
        conn.execute("ALTER TABLE banka_hesap ADD COLUMN sube_id INTEGER REFERENCES sube(id)")
    # B3 — siparis_kalem.kalan_iptal: kısmi teslimatın bilinçli kapatılması
    # (kalan = miktar - teslim_edilen - kalan_iptal).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(siparis_kalem)")}
    if "kalan_iptal" not in cols:
        conn.execute("ALTER TABLE siparis_kalem ADD COLUMN kalan_iptal REAL NOT NULL DEFAULT 0")
    # D — servis_kayit.bakim_sozlesme_id: bakım sözleşmesi kapsamında açılan iş emri bağlantısı.
    # (servis_kayit bu fonksiyonun ilerleyen adımında kurulur; yalnızca tablo mevcutsa ALTER.)
    if conn.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='servis_kayit'").fetchone():
        cols = {r["name"] for r in conn.execute("PRAGMA table_info(servis_kayit)")}
        if "bakim_sozlesme_id" not in cols:
            conn.execute("ALTER TABLE servis_kayit ADD COLUMN bakim_sozlesme_id INTEGER REFERENCES bakim_sozlesme(id)")
    # K17 — cek_senet.durum CHECK genişletildi (Tahsile Verildi + Karşılıksız eklendi).
    # SQLite CHECK değiştirilemediği için tablo yeniden kurulur (hiçbir tablo FK ile
    # cek_senet'e bağlanmaz; ek_dosya ilgili_kayit_id'yi FK'sız taşır).
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name='cek_senet'").fetchone()
    if row and "Karşılıksız" not in (row["sql"] or ""):
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            """
            ALTER TABLE cek_senet RENAME TO _cek_senet_eski;
            CREATE TABLE cek_senet (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                no TEXT NOT NULL,
                tip TEXT NOT NULL DEFAULT 'Alinan' CHECK (tip IN ('Alinan','Verilen')),
                tur TEXT NOT NULL DEFAULT 'Cek' CHECK (tur IN ('Cek','Senet')),
                cari_id INTEGER REFERENCES cari_kart(id),
                sube_id INTEGER REFERENCES sube(id),
                banka TEXT,
                sube_ad TEXT,
                tutar REAL NOT NULL DEFAULT 0,
                keside_tarihi TEXT,
                vade TEXT NOT NULL,
                durum TEXT NOT NULL DEFAULT 'Bekliyor' CHECK (durum IN ('Bekliyor','Tahsile Verildi','Tahsil Edildi','Ödendi','Karşılıksız','Ciro','İptal')),
                aciklama TEXT,
                created_by INTEGER,
                created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
                updated_at TEXT
            );
            INSERT INTO cek_senet(id,no,tip,tur,cari_id,sube_id,banka,sube_ad,tutar,keside_tarihi,vade,durum,aciklama,created_by,created_at,updated_at)
                SELECT id,no,tip,tur,cari_id,sube_id,banka,sube_ad,tutar,keside_tarihi,vade,durum,aciklama,created_by,created_at,updated_at
                FROM _cek_senet_eski;
            DROP TABLE _cek_senet_eski;
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cek_senet_cari ON cek_senet(cari_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_cek_senet_vade ON cek_senet(vade)")

    # K18 — Döviz Takip: para_birimi + doviz_kur eklendi (cek_senet, kasa_hareket, banka_hareket).
    # Fatura/teklif/siparis/cari_hareket zaten bu alanları taşıyordu (Faz 2 kurulumunda).
    for tablo in ("cek_senet", "kasa_hareket", "banka_hareket"):
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tablo})")}
        if "para_birimi" not in cols:
            conn.execute(f"ALTER TABLE {tablo} ADD COLUMN para_birimi TEXT NOT NULL DEFAULT 'TRY'")
        if "doviz_kur" not in cols:
            conn.execute(f"ALTER TABLE {tablo} ADD COLUMN doviz_kur REAL")

    # --- Faz 6.1 — Manuel (serbest metin) satır: *_kalem.stok_id nullable ---
    # SQLite NOT NULL kaldıramadığı için tablo yeniden kurulur (cek_senet deseni).
    for tablo, parent, indeks, index_sql in (
        ("irsaliye_kalem", "irsaliye_id", "idx_irsaliye_kalem_irsaliye",
         "CREATE INDEX IF NOT EXISTS idx_irsaliye_kalem_irsaliye ON irsaliye_kalem(irsaliye_id)"),
        ("fatura_kalem", "fatura_id", "idx_fatura_kalem_fatura",
         "CREATE INDEX IF NOT EXISTS idx_fatura_kalem_fatura ON fatura_kalem(fatura_id)"),
    ):
        col = conn.execute(f"PRAGMA table_info({tablo})").fetchall()
        stok_col = next((c for c in col if c["name"] == "stok_id"), None)
        if stok_col is None or not stok_col["notnull"]:
            continue
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            f"""
            ALTER TABLE {tablo} RENAME TO _{tablo}_eski;
            CREATE TABLE {tablo} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {parent} INTEGER NOT NULL REFERENCES {tablo.split('_')[0]}(id),
                stok_id INTEGER REFERENCES stok_kart(id),
                varyant_id INTEGER NOT NULL DEFAULT 0,
                miktar REAL NOT NULL DEFAULT 1,
                birim_fiyat REAL NOT NULL DEFAULT 0,
                iskonto_orani REAL NOT NULL DEFAULT 0,
                kdv_orani REAL NOT NULL DEFAULT 20,
                tutar REAL NOT NULL DEFAULT 0,
                aciklama TEXT
            );
            INSERT INTO {tablo}(id, {parent}, stok_id, varyant_id, miktar, birim_fiyat,
                                iskonto_orani, kdv_orani, tutar, aciklama)
                SELECT id, {parent}, stok_id, varyant_id, miktar, birim_fiyat,
                       iskonto_orani, kdv_orani, tutar, aciklama
                FROM _{tablo}_eski;
            DROP TABLE _{tablo}_eski;
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(index_sql)

    # --- Faz 6.1 sonrası (v1.23) — Teklif/Sipariş kalemlerine de manuel satır: stok_id nullable ---
    for tablo, parent, extra_cols, extra_select, indeks, index_sql in (
        ("teklif_kalem", "teklif_id", "", "",
         "idx_teklif_kalem_teklif", "CREATE INDEX IF NOT EXISTS idx_teklif_kalem_teklif ON teklif_kalem(teklif_id)"),
        ("siparis_kalem", "siparis_id", "teslim_edilen REAL NOT NULL DEFAULT 0,",
         "teslim_edilen,", "idx_siparis_kalem_siparis",
         "CREATE INDEX IF NOT EXISTS idx_siparis_kalem_siparis ON siparis_kalem(siparis_id)"),
    ):
        col = conn.execute(f"PRAGMA table_info({tablo})").fetchall()
        stok_col = next((c for c in col if c["name"] == "stok_id"), None)
        if stok_col is None or not stok_col["notnull"]:
            continue
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.executescript(
            f"""
            ALTER TABLE {tablo} RENAME TO _{tablo}_eski;
            CREATE TABLE {tablo} (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                {parent} INTEGER NOT NULL REFERENCES {tablo.split('_')[0]}(id),
                stok_id INTEGER REFERENCES stok_kart(id),
                varyant_id INTEGER NOT NULL DEFAULT 0,
                miktar REAL NOT NULL DEFAULT 1,
                {extra_cols}
                birim_fiyat REAL NOT NULL DEFAULT 0,
                iskonto_orani REAL NOT NULL DEFAULT 0,
                kdv_orani REAL NOT NULL DEFAULT 20,
                tutar REAL NOT NULL DEFAULT 0,
                aciklama TEXT
            );
            INSERT INTO {tablo}(id, {parent}, stok_id, varyant_id, miktar, {extra_select}
                                birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama)
                SELECT id, {parent}, stok_id, varyant_id, miktar, {extra_select}
                       birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama
                FROM _{tablo}_eski;
            DROP TABLE _{tablo}_eski;
            """
        )
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute(index_sql)

    # --- Faz 3 — Servis & Garanti ---
    # Servis Takip (1.2): servis kaydı + kullanılan yedek parçalar.
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS servis_kayit (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servis_no TEXT NOT NULL UNIQUE,
            cari_id INTEGER REFERENCES cari_kart(id),
            cihaz TEXT NOT NULL,
            seri_no TEXT,
            ariza TEXT,
            aksesuar TEXT,
            gelis_tarihi TEXT NOT NULL DEFAULT (date('now','localtime')),
            teknisyen_id INTEGER REFERENCES kullanici(id),
            durum TEXT NOT NULL DEFAULT 'Alındı' CHECK (durum IN ('Alındı','Teşhis Edildi','Onay Bekliyor','Tamir Ediliyor','Tamamlandı','Teslim Edildi','İade')),
            garanti_kapsami INTEGER NOT NULL DEFAULT 0,
            iscilik_ucreti REAL NOT NULL DEFAULT 0,
            aciklama TEXT,
            sube_id INTEGER REFERENCES sube(id),
            bakim_sozlesme_id INTEGER REFERENCES bakim_sozlesme(id),
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS servis_parca (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            servis_id INTEGER NOT NULL REFERENCES servis_kayit(id),
            stok_id INTEGER NOT NULL REFERENCES stok_kart(id),
            miktar REAL NOT NULL DEFAULT 1,
            birim_fiyat REAL NOT NULL DEFAULT 0,
            tutar REAL NOT NULL DEFAULT 0,
            aciklama TEXT
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_servis_durum ON servis_kayit(durum)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_servis_cari ON servis_kayit(cari_id)")

    # Faz 3 düzeltmesi — Servis → Fatura zinciri (K8) + depo bazlı parça düşümü (K11).
    # fatura.kaynak_servis_id: servis tesliminde üretilen taslak faturanın kaynağı.
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(fatura)")}
    if "kaynak_servis_id" not in cols:
        conn.execute("ALTER TABLE fatura ADD COLUMN kaynak_servis_id INTEGER REFERENCES servis_kayit(id)")
    # servis_parca.depo_id: yedek parçanın hangi depodan düşüleceği (K11).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(servis_parca)")}
    if "depo_id" not in cols:
        conn.execute("ALTER TABLE servis_parca ADD COLUMN depo_id INTEGER REFERENCES depo(id)")
    # stok_kart.tip: 'Urun' | 'Hizmet' — servis işçiliği gibi stoksuz kalemler (fatura kalemi için).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(stok_kart)")}
    if "tip" not in cols:
        conn.execute("ALTER TABLE stok_kart ADD COLUMN tip TEXT NOT NULL DEFAULT 'Urun'")

    # Seri No-Garanti (1.16): garanti süresi (ürün kartında) + garanti tarihleri (seri no üzerinde).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(stok_kart)")}
    if "garanti_suresi_ay" not in cols:
        conn.execute("ALTER TABLE stok_kart ADD COLUMN garanti_suresi_ay INTEGER NOT NULL DEFAULT 24")
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(stok_seri)")}
    if "garanti_baslangic" not in cols:
        conn.execute("ALTER TABLE stok_seri ADD COLUMN garanti_baslangic TEXT")
    if "garanti_bitis" not in cols:
        conn.execute("ALTER TABLE stok_seri ADD COLUMN garanti_bitis TEXT")

    # --- Faz 4 — e-Dönüşüm ---
    # 1.13 e-Fatura/e-Arşiv/e-İrsaliye: giden e-belge (GİB durum takibi CHECK ile).
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS e_belge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            belge_no TEXT UNIQUE,
            tur TEXT NOT NULL CHECK (tur IN ('EFatura','EArsiv','EIrsaliye')),
            kaynak_fatura_id INTEGER REFERENCES fatura(id),
            kaynak_irsaliye_id INTEGER REFERENCES irsaliye(id),
            cari_id INTEGER REFERENCES cari_kart(id),
            alici_vkn TEXT,
            alici_unvan TEXT,
            senaryo TEXT NOT NULL DEFAULT 'Temel',
            ettn TEXT,
            durum TEXT NOT NULL DEFAULT 'Taslak' CHECK (durum IN ('Taslak','Gönderildi','Onaylandı','Reddedildi','İptal')),
            hata_mesaji TEXT,
            gonderim_tarihi TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS gelen_belge (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            belge_no TEXT UNIQUE,
            tur TEXT NOT NULL CHECK (tur IN ('EFatura','EIrsaliye')),
            gonderen_vkn TEXT,
            gonderen_unvan TEXT,
            alici_vkn TEXT,
            belge_tarih TEXT,
            tutar REAL NOT NULL DEFAULT 0,
            kdv REAL NOT NULL DEFAULT 0,
            para_birimi TEXT NOT NULL DEFAULT 'TRY',
            durum TEXT NOT NULL DEFAULT 'Okunmadi' CHECK (durum IN ('Okunmadi','Kabul','Red','Itiraz')),
            donusum_fatura_id INTEGER REFERENCES fatura(id),
            donusum_irsaliye_id INTEGER REFERENCES irsaliye(id),
            aciklama TEXT,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_e_belge_durum ON e_belge(durum)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_e_belge_kaynak ON e_belge(kaynak_fatura_id, kaynak_irsaliye_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_gelen_durum ON gelen_belge(durum)")
    # Cari: e-Fatura mükellefiyeti → giden belge tipini otomatik belirleme (e-Fatura/e-Arşiv).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(cari_kart)")}
    if "e_fatura_mukellefi" not in cols:
        conn.execute("ALTER TABLE cari_kart ADD COLUMN e_fatura_mukellefi INTEGER NOT NULL DEFAULT 0")
    # F4 — Entegratör ayarları (şirket başına TEK satır, K1: sirket_id PK).
    # Mock (Sandbox) varsayılan; gerçek sağlayıcı (EDM/İzibiz/QNB) API anahtarıyla buradan seçilir.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS entegrator_ayar (
            sirket_id INTEGER PRIMARY KEY REFERENCES sirket(id),
            entegrator TEXT NOT NULL DEFAULT 'Mock',
            api_anahtar TEXT,
            test_modu INTEGER NOT NULL DEFAULT 1,
            updated_at TEXT
        )
        """
    )

    # F5-A (v1.35.0) — Bütçe hedefi: şirket + yıl + ay başına TEK satır (K1, UNIQUE).
    # hedef_satis / hedef_kar kullanıcı tarafından MANUEL girilir; otomatik üretim yok.
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS butce_hedef (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sirket_id INTEGER NOT NULL REFERENCES sirket(id),
            yil INTEGER NOT NULL,
            ay INTEGER NOT NULL,
            hedef_satis REAL NOT NULL DEFAULT 0,
            hedef_kar REAL NOT NULL DEFAULT 0,
            olusturan INTEGER,
            olusturma_tarihi TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(sirket_id, yil, ay)
        )
        """
    )

    # --- Faz 5 — Genel Muhasebe (hesap planı + yevmiye) ---
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS hesap (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE NOT NULL,
            ad TEXT NOT NULL,
            tip TEXT NOT NULL DEFAULT 'Aktif' CHECK (tip IN ('Aktif','Pasif','Ozkaynak','Gelir','Gider')),
            ust_kod TEXT,
            aktif INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS yevmiye (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fis_no TEXT UNIQUE NOT NULL,
            tarih TEXT NOT NULL,
            aciklama TEXT,
            kaynak_modul TEXT,
            kaynak_id INTEGER,
            kaynak_sahne TEXT,
            sube_id INTEGER REFERENCES sube(id),
            durum TEXT NOT NULL DEFAULT 'Onaylandı' CHECK (durum IN ('Taslak','Onaylandı','İptal')),
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS yevmiye_kalem (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yevmiye_id INTEGER NOT NULL REFERENCES yevmiye(id),
            hesap_id INTEGER REFERENCES hesap(id),
            borc REAL NOT NULL DEFAULT 0,
            alacak REAL NOT NULL DEFAULT 0,
            aciklama TEXT
        );
        -- Finansal Analiz (1.19): bütçe hedefleri (Odoo bütçe mantığı — dönem+tip+hedef).
        CREATE TABLE IF NOT EXISTS butce (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            yil INTEGER NOT NULL,
            ay INTEGER NOT NULL,
            tip TEXT NOT NULL DEFAULT 'Gelir' CHECK (tip IN ('Gelir','Gider')),
            tutar REAL NOT NULL DEFAULT 0,
            aciklama TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_yevmiye_kaynak ON yevmiye(kaynak_modul, kaynak_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_yevmiye_kalem_yid ON yevmiye_kalem(yevmiye_id)")

    # Faz 5 revizyonu — yevmiye'ye sube_id (K1) + kaynak_sahne (çek/senet çok-fiş modeli).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(yevmiye)")}
    if "sube_id" not in cols:
        conn.execute("ALTER TABLE yevmiye ADD COLUMN sube_id INTEGER REFERENCES sube(id)")
    if "kaynak_sahne" not in cols:
        conn.execute("ALTER TABLE yevmiye ADD COLUMN kaynak_sahne TEXT")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_yevmiye_kaynak_sahne ON yevmiye(kaynak_modul, kaynak_id, kaynak_sahne)")

    # --- Faz 5 — Demirbaş (1.22): sabit kıymet + amortisman + zimmet ---
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS demirbas_kategori (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad TEXT NOT NULL,
            omur_yil REAL NOT NULL DEFAULT 5,
            aciklama TEXT,
            aktif INTEGER NOT NULL DEFAULT 1
        );
        CREATE TABLE IF NOT EXISTS demirbas (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT UNIQUE NOT NULL,
            ad TEXT NOT NULL,
            kategori_id INTEGER REFERENCES demirbas_kategori(id),
            alis_tarihi TEXT NOT NULL,
            maliyet REAL NOT NULL DEFAULT 0,
            hurda_degeri REAL NOT NULL DEFAULT 0,
            omur_yil REAL,
            sube_id INTEGER REFERENCES sube(id),
            zimmetli_kullanici_id INTEGER REFERENCES kullanici(id),
            durum TEXT NOT NULL DEFAULT 'Aktif' CHECK (durum IN ('Aktif','Satıldı','Hurda')),
            aciklama TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            updated_at TEXT
        );
        CREATE TABLE IF NOT EXISTS demirbas_amortisman (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demirbas_id INTEGER NOT NULL REFERENCES demirbas(id),
            donem TEXT NOT NULL,
            tutar REAL NOT NULL DEFAULT 0,
            birikmis REAL NOT NULL DEFAULT 0,
            net_deger REAL NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime')),
            UNIQUE(demirbas_id, donem)
        );
        CREATE TABLE IF NOT EXISTS demirbas_zimmet (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            demirbas_id INTEGER NOT NULL REFERENCES demirbas(id),
            kullanici_id INTEGER REFERENCES kullanici(id),
            sube_id INTEGER REFERENCES sube(id),
            islem TEXT NOT NULL DEFAULT 'Teslim' CHECK (islem IN ('Teslim','Devir','İade')),
            tarih TEXT NOT NULL DEFAULT (date('now','localtime')),
            aciklama TEXT,
            created_by INTEGER,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        """
    )
    conn.execute("CREATE INDEX IF NOT EXISTS idx_demirbas_sube ON demirbas(sube_id)")
    conn.execute("CREATE INDEX IF NOT EXISTS idx_demirbas_amortisman_did ON demirbas_amortisman(demirbas_id)")

    # --- Satır ekleme akışı + stok kartı birimi (v1.19): belge kalemlerinde birim + görünen ad ---
    # birim: stoklu satırda stok kartındaki birim, manuel satırda kullanıcının seçtiği birim.
    # goruntu_adi: boşsa stok adı gösterilir; doldurulursa YALNIZCA o belgede görünen adı override eder
    #              (stok kartındaki gerçek ad asla değişmez — Kartoteks/Genel Muhasebe gerçek adı kullanır).
    for _tablo in ("fatura_kalem", "irsaliye_kalem", "teklif_kalem", "siparis_kalem"):
        _cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({_tablo})")}
        if "birim" not in _cols:
            conn.execute(f"ALTER TABLE {_tablo} ADD COLUMN birim TEXT")
        if "goruntu_adi" not in _cols:
            conn.execute(f"ALTER TABLE {_tablo} ADD COLUMN goruntu_adi TEXT")


    # --- F2 (v1.32) — KDV dahil/hariç fiyat girişi: belge başlıklarına kdv_dahil bayrağı ---
    # DB'de fiyatlar HER ZAMAN NET (KDV hariç) tutulur; bayrak yalnızca giriş/gösterim biçimini
    # kaydeder (düzenlemede aynı modda açılması için). Varsayılan 0 = KDV hariç.
    for tablo in ("teklif", "siparis", "irsaliye", "fatura"):
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tablo})")}
        if "kdv_dahil" not in cols:
            conn.execute(f"ALTER TABLE {tablo} ADD COLUMN kdv_dahil INTEGER NOT NULL DEFAULT 0")

    # --- D012-B (v1.43) — satır bazlı KDV: kalem tablolarına kdv_dahil override ---
    # NULL = satır belge genelini izler; 0 = açıkça hariç; 1 = açıkça dahil.
    for tablo in ("fatura_kalem", "irsaliye_kalem", "teklif_kalem", "siparis_kalem"):
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tablo})")}
        if "kdv_dahil" not in cols:
            conn.execute(f"ALTER TABLE {tablo} ADD COLUMN kdv_dahil INTEGER")

    # --- D007 (v1.39.0) — Stok kart ek alanlar (8 + model) + irsaliye döviz kuru ---
    # Wolvox/Akınsoft referanslı alanlar: tevkifat, istisna, grup hiyerarşisi, özel kod 1-3.
    # Geriye dönük uyumlu: mevcut kartlarda default 0/NULL; raporlar etkilenmez.
    _stok_cols = {r["name"] for r in conn.execute("PRAGMA table_info(stok_kart)")}
    for _kol in ("tevkifat_orani", "istisna_kodu", "grubu", "ana_grup", "alt_grup",
                 "ozel_kod1", "ozel_kod2", "ozel_kod3", "model"):
        if _kol not in _stok_cols:
            if _kol == "tevkifat_orani":
                conn.execute("ALTER TABLE stok_kart ADD COLUMN tevkifat_orani REAL NOT NULL DEFAULT 0")
            else:
                conn.execute(f"ALTER TABLE stok_kart ADD COLUMN {_kol} TEXT")
    # irsaliye.para_birimi zaten var; eksik olan doviz_kur eklenir (fatura deseniyle aynı).
    _irs_cols = {r["name"] for r in conn.execute("PRAGMA table_info(irsaliye)")}
    if "doviz_kur" not in _irs_cols:
        conn.execute("ALTER TABLE irsaliye ADD COLUMN doviz_kur REAL NOT NULL DEFAULT 1")


    # --- v1.20 — belge kalemlerinde birim + görünen ad (K34.2 / K34.7) ---
    # birim: stoklu satırda stok kartındaki birim, manuel satırda kullanıcının seçtiği birim.
    # goruntu_adi: boşsa stok adı gösterilir; doldurulursa YALNIZCA o belgede görünen adı override eder
    #              (stok kartındaki gerçek ad asla değişmez — Kartoteks/Genel Muhasebe gerçek adı kullanır).
    for tablo in ("fatura_kalem", "irsaliye_kalem"):
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tablo})")}
        if "birim" not in cols:
            conn.execute(f"ALTER TABLE {tablo} ADD COLUMN birim TEXT")
        if "goruntu_adi" not in cols:
            conn.execute(f"ALTER TABLE {tablo} ADD COLUMN goruntu_adi TEXT")

    # --- İstek 3 — Çoklu Şirket (Seçenek A): DDL + migrasyon + backfill ---
    _migrate_coklu_sirket(conn)

    # --- F4 (v1.34.0) — e-belge/gelen türevleri üst belge silinince otomatik temizle ---
    # Uygulama bağlantılarında FK ON olsa da test/araç bağlantıları (FK OFF) üst belgeyi
    # doğrudan sildiğinde yetim e_belge (FK ihlali) kalmasın diye TRIGGER ile cascade yapılır.
    # (e_belge.kaynak_* -> fatura/irsaliye; gelen_belge.donusum_* -> fatura/irsaliye.)
    conn.execute(
        "DELETE FROM e_belge WHERE "
        "(kaynak_fatura_id IS NOT NULL AND kaynak_fatura_id NOT IN (SELECT id FROM fatura)) "
        "OR (kaynak_irsaliye_id IS NOT NULL AND kaynak_irsaliye_id NOT IN (SELECT id FROM irsaliye))"
    )
    conn.executescript(
        """
        CREATE TRIGGER IF NOT EXISTS trg_fatura_sil_ebelge
        AFTER DELETE ON fatura
        BEGIN
            DELETE FROM e_belge WHERE kaynak_fatura_id = OLD.id;
            UPDATE gelen_belge SET donusum_fatura_id = NULL WHERE donusum_fatura_id = OLD.id;
        END;

        CREATE TRIGGER IF NOT EXISTS trg_irsaliye_sil_ebelge
        AFTER DELETE ON irsaliye
        BEGIN
            DELETE FROM e_belge WHERE kaynak_irsaliye_id = OLD.id;
            UPDATE gelen_belge SET donusum_irsaliye_id = NULL WHERE donusum_irsaliye_id = OLD.id;
        END;
        """
    )


# ---------------------------------------------------------------------------
# İstek 3 — Çoklu Şirket (Seçenek A): tek DB + sirket_id
# ---------------------------------------------------------------------------
# Şirket kapsamında benzersiz olması gereken kolonlar. K13'ten beri bu kolonlar
# GLOBAL UNIQUE olarak kurulmuştu; iki şirket aynı "TKF-2026-001"/"001" değerini
# üretemeyince çakışırdı. UNIQUE tek kolondan bileşiğe çevrilemez (SQLite ALTER
# desteklemez), bu yüzden tablo yeniden kurulur (cek_senet CHECK deseni).
_SIRKET_UNIQUE = {
    "teklif": "teklif_no", "siparis": "siparis_no", "irsaliye": "irsaliye_no",
    "fatura": "fatura_no", "e_belge": "belge_no", "gelen_belge": "belge_no",
    "yevmiye": "fis_no", "servis_kayit": "servis_no",
    "cari_kart": "kod", "stok_kart": "kod", "demirbas": "kod", "depo": "kod",
    "kasa": "kod", "banka_hesap": "kod", "hesap": "kod", "sube": "kod", "marka": "ad",
}

# Rebuild sonrası yeniden oluşturulacak indexler (DROP TABLE _eski indexleri de düşürür).
_SIRKET_INDEXLER = {
    "teklif": ["CREATE INDEX IF NOT EXISTS idx_teklif_cari ON teklif(cari_id)"],
    "siparis": [
        "CREATE INDEX IF NOT EXISTS idx_siparis_cari ON siparis(cari_id)",
        "CREATE INDEX IF NOT EXISTS idx_siparis_kaynak ON siparis(kaynak_teklif_id)",
    ],
    "irsaliye": [
        "CREATE INDEX IF NOT EXISTS idx_irsaliye_cari ON irsaliye(cari_id)",
        "CREATE INDEX IF NOT EXISTS idx_irsaliye_kaynak ON irsaliye(kaynak_siparis_id)",
    ],
    "fatura": [
        "CREATE INDEX IF NOT EXISTS idx_fatura_cari ON fatura(cari_id)",
        "CREATE INDEX IF NOT EXISTS idx_fatura_kaynak ON fatura(kaynak_irsaliye_id)",
    ],
    "e_belge": [
        "CREATE INDEX IF NOT EXISTS idx_e_belge_durum ON e_belge(durum)",
        "CREATE INDEX IF NOT EXISTS idx_e_belge_kaynak ON e_belge(kaynak_fatura_id, kaynak_irsaliye_id)",
    ],
    "gelen_belge": ["CREATE INDEX IF NOT EXISTS idx_gelen_durum ON gelen_belge(durum)"],
    "yevmiye": [
        "CREATE INDEX IF NOT EXISTS idx_yevmiye_kaynak ON yevmiye(kaynak_modul, kaynak_id)",
        "CREATE INDEX IF NOT EXISTS idx_yevmiye_kaynak_sahne ON yevmiye(kaynak_modul, kaynak_id, kaynak_sahne)",
    ],
    "servis_kayit": [
        "CREATE INDEX IF NOT EXISTS idx_servis_durum ON servis_kayit(durum)",
        "CREATE INDEX IF NOT EXISTS idx_servis_cari ON servis_kayit(cari_id)",
    ],
    "demirbas": ["CREATE INDEX IF NOT EXISTS idx_demirbas_sube ON demirbas(sube_id)"],
}

# UNIQUE içermeyen, yalnızca sirket_id kolonu eklenecek veri tabloları (ALTER ADD COLUMN).
_SIRKET_TABLOLAR = (
    # master data
    "cari_grup", "kategori", "demirbas_kategori", "stok_varyant", "stok_tedarikci", "doviz_kur",
    # işlem + kalem
    "cari_hareket", "stok_hareket", "stok_seviye", "stok_seri", "stok_sayim",
    "stok_sayim_kalem", "depo_transfer", "depo_transfer_kalem", "kasa_hareket",
    "banka_hareket", "teklif_kalem", "siparis_kalem", "irsaliye_kalem", "fatura_kalem",
    "cek_senet", "servis_parca", "yevmiye_kalem", "butce",
    "demirbas_amortisman", "demirbas_zimmet",
    # polimorfik / yardımcı
    "notlar", "ek_dosya", "bildirimler", "audit_log",
)


def _sirket_rebuild(conn, tablo, ucol):
    """Global UNIQUE(tablo.ucol) → UNIQUE(sirket_id, ucol) + sirket_id kolonu (tablo rebuild)."""
    cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tablo})")}
    if "sirket_id" in cols:  # önceki göçte yapıldıysa atla (idempotent)
        return
    row = conn.execute("SELECT sql FROM sqlite_master WHERE type='table' AND name=?", (tablo,)).fetchone()
    if not row:
        return
    sql = row["sql"]
    pat = re.compile(r"(\b" + re.escape(ucol) + r"\s+TEXT[^,()]*?)\bUNIQUE\b", re.IGNORECASE)
    yeni, n = pat.subn(r"\1", sql)
    if n != 1:  # UNIQUE zaten yoksa sirket_id'yi yine de ekle (korumacı)
        yeni = sql
    i = yeni.rfind(")")
    yeni = (yeni[:i] + ", sirket_id INTEGER NOT NULL DEFAULT 1, UNIQUE(sirket_id, "
            + ucol + ")" + yeni[i:])
    # Yeni şema geçici adla kurulur, veri kopyalanır, eski tablo DROP edilir, geçici ad
    # asıl ada çevrilir. (SQLite resmi 12-adım prosedürü: eski ad RENAME edilirse çocuk
    # tabloların FK'ları "_eski" adına yeniden yazılır ve bozulur; DROP+RENAME ise çocuk
    # FK'larının asıl adı işaret etmesini korur.)
    yeni = yeni.replace(f"CREATE TABLE {tablo}", f"CREATE TABLE {tablo}_yeni", 1)
    conn.commit()  # açık işlemi kapat — PRAGMA foreign_keys işlem içinde no-op olur
    conn.execute("PRAGMA foreign_keys = OFF")
    try:
        conn.execute(yeni)
        conn.execute(f"INSERT INTO {tablo}_yeni SELECT *, 1 FROM {tablo}")
        conn.execute(f"DROP TABLE {tablo}")
        conn.execute(f"ALTER TABLE {tablo}_yeni RENAME TO {tablo}")
    finally:
        conn.commit()
        conn.execute("PRAGMA foreign_keys = ON")
    for idx in _SIRKET_INDEXLER.get(tablo, []):
        conn.execute(idx)
    conn.commit()


def _migrate_coklu_sirket(conn):
    """İstek 3 — Çoklu Şirket Adım 1: DDL + migrasyon + backfill (idempotent).

    - `sirket` + `kullanici_sirket` tabloları kurulur.
    - `firma` (tek satır) → `sirket.id=1` taşınır (Mikro karar D; tablo silme Adım 2'de).
    - Tüm kullanıcılar `(id, 1)` ile 1. şirkete bağlanır (N-N backfill).
    - `sessionler.sirket_id` eklenir (oturum bazlı geçişin taşıyıcısı).
    - Global UNIQUE kolonlar composite'e çevrilir; diğer veri tablolarına sirket_id eklenir.
    DEFAULT 1 sayesinde mevcut tüm veri 1. şirkete bağlanır → tek şirket davranışı korunur.
    """
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS sirket (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            kod TEXT NOT NULL UNIQUE,
            unvan TEXT NOT NULL,
            kisa_ad TEXT,
            vergi_dairesi TEXT,
            vergi_no TEXT,
            adres TEXT,
            telefon TEXT,
            email TEXT,
            logo TEXT,
            aktif INTEGER NOT NULL DEFAULT 1,
            created_at TEXT NOT NULL DEFAULT (datetime('now','localtime'))
        );
        CREATE TABLE IF NOT EXISTS kullanici_sirket (
            kullanici_id INTEGER NOT NULL REFERENCES kullanici(id),
            sirket_id INTEGER NOT NULL REFERENCES sirket(id),
            PRIMARY KEY (kullanici_id, sirket_id)
        );
        """
    )

    # sirket.id=1 seed: eski `firma` tablosundan taşı (varsa); yoksa config'ten (taze kurulum).
    has_firma = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type='table' AND name='firma'").fetchone()
    if conn.execute("SELECT COUNT(*) c FROM sirket").fetchone()["c"] == 0:
        f = None
        if has_firma:
            f = conn.execute("SELECT * FROM firma ORDER BY id LIMIT 1").fetchone()
        if f:
            conn.execute(
                "INSERT INTO sirket(id, kod, unvan, kisa_ad, vergi_dairesi, vergi_no, "
                "adres, telefon, email, logo, aktif) VALUES(1, 'BRN', ?, ?, ?, ?, ?, ?, ?, ?, 1)",
                (f["unvan"], f["kisa_ad"], f["vergi_dairesi"], f["vergi_no"],
                 f["adres"], f["telefon"], f["email"], f["logo"]),
            )
        else:
            conn.execute(
                "INSERT INTO sirket(id, kod, unvan, aktif) VALUES(1, 'BRN', ?, 1)",
                (FIRMA_ADI or "Brn Teknoloji",),
            )

    # N-N backfill: tüm mevcut kullanıcılar 1. şirkete üye.
    conn.execute(
        "INSERT OR IGNORE INTO kullanici_sirket(kullanici_id, sirket_id) SELECT id, 1 FROM kullanici"
    )

    # sessionler.sirket_id → oturum bazlı aktif şirket (nullable; girişte set edilir).
    cols = {r["name"] for r in conn.execute("PRAGMA table_info(sessionler)")}
    if "sirket_id" not in cols:
        conn.execute("ALTER TABLE sessionler ADD COLUMN sirket_id INTEGER")

    # Global UNIQUE → composite UNIQUE(sirket_id, kolon) (tablo rebuild).
    for tablo, ucol in _SIRKET_UNIQUE.items():
        _sirket_rebuild(conn, tablo, ucol)

    # Diğer veri tablolarına sirket_id kolonu (idempotent ALTER).
    for tablo in _SIRKET_TABLOLAR:
        cols = {r["name"] for r in conn.execute(f"PRAGMA table_info({tablo})")}
        if "sirket_id" not in cols:
            conn.execute(f"ALTER TABLE {tablo} ADD COLUMN sirket_id INTEGER NOT NULL DEFAULT 1")

    conn.execute("INSERT OR REPLACE INTO meta(anahtar, deger) VALUES('sema_versiyonu', ?)",
                 (str(SCHEMA_VERSION),))

    # Mikro karar D — `firma` (tek satır) kaldırılır; kimlik `sirket` tablosunda yaşar.
    # (Hiçbir tablo firma'ya FK bağlamaz; içerik sirket.id=1'e taşındığı için güvenli.)
    if has_firma:
        conn.execute("DROP TABLE firma")


# --- K32 yardımcısı: bir master data kaydına işaret eden herhangi bir referans var mı? ---
_POLIMORFIK_REF = {
    # hedef tablo -> [(ara tablo, modül kolonu, id kolonu, bu tablodaki modül değeri)]
    "cari_kart": [
        ("notlar", "ilgili_tablo", "ilgili_id", "cari_kart"),
        ("ek_dosya", "ilgili_modul", "ilgili_kayit_id", "Cari"),
    ],
    "stok_kart": [
        ("notlar", "ilgili_tablo", "ilgili_id", "stok_kart"),
        ("ek_dosya", "ilgili_modul", "ilgili_kayit_id", "Stok"),
    ],
}


def sirket_id(req):
    """Aktif şirket id'si (İstek 3). Kullanıcı bağlamı yoksa 1 (seed/iç akış güvenli)."""
    try:
        v = req.user.get("sirket_id") if req and getattr(req, "user", None) else None
    except Exception:
        v = None
    return int(v) if v else 1


def referans_var(conn, hedef_tablo, kid):
    """`hedef_tablo` ('cari_kart' | 'stok_kart') id=`kid` kaydına işaret eden kayıt var mı?

    - Bildirilmiş tüm yabancı anahtarlar jenerik taranır (PRAGMA foreign_key_list) → ileride
      yeni bir tablo `..._id REFERENCES {hedef_tablo}(id)` bildirirse bu kontrol otomatik kapsar
      (elle liste güncellemek gerekmez).
    - FK ile ifade edilemeyen polimorfik referanslar (notlar/ek_dosya gibi modül+kayıt çifti)
      `_POLIMORFIK_REF` açık listesiyle denetlenir.
    - audit_log bilinçli olarak hariçtir: silme izi olarak kalır.
    Referans varsa ilk bulunan tablonun adını döndürür; yoksa None."""
    tablolar = [r["name"] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")]
    for t in tablolar:
        try:
            fks = conn.execute(f"PRAGMA foreign_key_list({t})").fetchall()
        except Exception:
            continue
        for fk in fks:
            if fk["table"] == hedef_tablo:
                col = fk["from"]
                try:
                    r = conn.execute(f"SELECT 1 FROM {t} WHERE {col}=? LIMIT 1", (kid,)).fetchone()
                except Exception:
                    continue
                if r:
                    return t
    for t, modul_col, id_col, deger in _POLIMORFIK_REF.get(hedef_tablo, []):
        r = conn.execute(
            f"SELECT 1 FROM {t} WHERE {modul_col}=? AND {id_col}=? LIMIT 1", (deger, kid)
        ).fetchone()
        if r:
            return t
    return None


# ---------------------------------------------------------------------------
# Bildirim temizliği (temiz seed disiplini)
# ---------------------------------------------------------------------------
# `bildirimler.ilgili_tablo` değerinden gerçek tablo adına eşleme. Yalnızca bu
# beyaz listedeki ebeveyn tablolar denetlenir; bilinmeyen/placeholder kayıtlar
# (ör. 'Sistem kuruldu', 'Döviz kurları güncellendi') asla silinmez.
_BILDIRIM_EBEVEYN = {
    "fatura": "fatura",
    "irsaliye": "irsaliye",
    "siparis": "siparis",
    "teklif": "teklif",
    "cek_senet": "cek_senet",
    "cari_kart": "cari_kart",
    "stok_kart": "stok_kart",
    "stok_seri": "stok_seri",
    "servis_kayit": "servis_kayit",
    "demirbas": "demirbas",
    "kasa": "kasa",
    "banka_hesap": "banka_hesap",
    "depo_transfer": "depo_transfer",
    "stok_sayim": "stok_sayim",
    "gelen_belge": "gelen_belge",
    "e_belge": "e_belge",
    "crm_aktivite": "crm_aktivite",
}


def bildirim_sil(conn, tablo, kayit_id):
    """`tablo`.`kayit_id` kaydına ilişkin bildirimleri ve gönderim kuyruğunu temizle."""
    conn.execute(
        "DELETE FROM bildirim_gonderim WHERE ilgili_tablo=? AND ilgili_id=?",
        (tablo, kayit_id),
    )
    conn.execute(
        "DELETE FROM bildirimler WHERE ilgili_tablo=? AND ilgili_id=?",
        (tablo, kayit_id),
    )


def bildirim_yetim_temizle(conn):
    """Ebeveyn kaydı silinmiş (yetim) bildirimleri temizle.

    Yalnızca `_BILDIRIM_EBEVEYN` beyaz listesi denetlenir; `ilgili_id<=0` (placeholder)
    ve listeye girmeyen tablolar korunur. Idempotenttir — her çağrıda aynı sonucu verir.
    """
    for ilgili_tablo, tablo in _BILDIRIM_EBEVEYN.items():
        conn.execute(
            f"DELETE FROM bildirim_gonderim WHERE ilgili_tablo=? AND ilgili_id>0 "
            f"AND ilgili_id NOT IN (SELECT id FROM {tablo})",
            (ilgili_tablo,),
        )
        conn.execute(
            f"DELETE FROM bildirimler WHERE ilgili_tablo=? AND ilgili_id>0 "
            f"AND ilgili_id NOT IN (SELECT id FROM {tablo})",
            (ilgili_tablo,),
        )


def guncel_kur(conn, para_birimi, sid=None):
    """1 birim dövizin TL karşılığı (K18). TRY/boş → 1.0; kayıt yoksa 1.0 (güvenli)."""
    if not para_birimi or para_birimi == "TRY":
        return 1.0
    extra = " AND sirket_id=?" if sid is not None else ""
    args = [para_birimi] + ([sid] if sid is not None else [])
    r = conn.execute(
        "SELECT kur FROM doviz_kur WHERE para_birimi=? AND tarih <= date('now','localtime') "
        + extra + " ORDER BY tarih DESC, id DESC LIMIT 1",
        args,
    ).fetchone()
    return float(r["kur"]) if r else 1.0


_PBKDF2_ITERASYON = 600_000


def hash_sifre(sifre, salt=None):
    """PBKDF2-HMAC-SHA256 (tuzlu, 600.000 yineleme) — `pbkdf2_sha256$iter$salt$hash`."""
    if salt is None:
        salt = secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac(
        "sha256", sifre.encode("utf-8"), salt.encode("utf-8"), _PBKDF2_ITERASYON
    ).hex()
    return f"pbkdf2_sha256${_PBKDF2_ITERASYON}${salt}${h}"


def hash_guncel_mi(stored):
    """Saklanan hash'in güncel (PBKDF2) formatta olup olmadığını döndürür."""
    return bool(stored) and stored.startswith("pbkdf2_sha256$")


def dogrula_sifre(sifre, stored):
    if not stored:
        return False
    if stored.startswith("pbkdf2_sha256$"):
        try:
            _, iters, salt, h = stored.split("$", 3)
            yeni = hashlib.pbkdf2_hmac(
                "sha256", sifre.encode("utf-8"), salt.encode("utf-8"), int(iters)
            ).hex()
            return yeni == h
        except (ValueError, TypeError):
            return False
    # Eski format (salt:sha256-hex) — geriye dönük uyumluluk; girişte otomatik yükseltilir.
    try:
        salt, h = stored.split(":", 1)
    except ValueError:
        return False
    return hashlib.sha256((salt + sifre).encode("utf-8")).hexdigest() == h


def sonraki_belge_no(conn, tablo, kolon, on_ek, yil, sirket_id=None):
    """K13 — yıl bazlı sıfırlanan sayaç: {on_ek}-{yil}-{NNN} (NNN o yıl + ön ek için 1'den başlar).

    İstek 3 (Mikro karar C): sayaç şirket başına bağımsızdır — sirket_id verilirse aynı
    şirketteki kayıtlar üzerinden sıradaki numara bulunur (görünür format değişmez)."""
    pos = len(on_ek) + 7  # "TKF-2026-001" → rakam kısmı 10. karakterden başlar
    where, params = f"{kolon} LIKE ?", [f"{on_ek}-{yil}-%"]
    if sirket_id is not None:
        where += " AND sirket_id = ?"
        params.append(sirket_id)
    row = conn.execute(
        f"SELECT COALESCE(MAX(CAST(substr({kolon}, ?) AS INTEGER)), 0) AS n "
        f"FROM {tablo} WHERE {where}",
        [pos] + params,
    ).fetchone()
    return f"{on_ek}-{yil}-{row[0] + 1:03d}"


def seed():
    """İlk açılışta örnek verileri yükle."""
    # D012-X — para birimi + birim tohumları (hem taze kurulumda hem geriye dönük doldurmada).
    seed_para_birimi()
    seed_birim()
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM kullanici").fetchone()["c"]
    if n > 0:
        conn.close()
        seed_stok()
        seed_kasa()
        seed_banka()
        seed_sube()
        seed_teklif()
        seed_siparis()
        seed_satin_alma()
        seed_alinan_teklif()
        seed_eksik_teslimat()
        seed_irsaliye()
        seed_fatura()
        seed_cek_senet()
        seed_doviz()
        seed_servis()
        seed_edonusum()
        seed_muhasebe()
        seed_pos()
        seed_bakim()
        seed_crm()
        seed_finansal()
        seed_demirbas()
        seed_faz6()
        return

    # --- Kullanıcılar (varsayılan şifre: 1234) ---
    users = [
        ("admin", "Sistem Yöneticisi", "yonetici@brnteknoloji.com", "Admin"),
        ("muhasebe", "Ayşe Demir", "muhasebe@brnteknoloji.com", "Muhasebe"),
        ("satis", "Mehmet Kaya", "satis@brnteknoloji.com", "Satis"),
        ("servis", "Hüseyin Çelik", "servis@brnteknoloji.com", "Servis"),
        ("depo", "Fatma Şahin", "depo@brnteknoloji.com", "Depo"),
    ]
    for u, ad, mail, rol in users:
        conn.execute(
            "INSERT INTO kullanici(kullanici_adi, ad_soyad, email, sifre_hash, rol) VALUES(?,?,?,?,?)",
            (u, ad, mail, hash_sifre("1234"), rol),
        )

    # --- Şirket bilgisi (İstek 3) ---
    # Migrasyon sirket.id=1'i ya eski firma'dan ya da config'ten kurdu; burada zenginleştirilir
    # (yalnızca boşsa — mevcut kullanıcı düzenlemelerini ezmemek için).
    conn.execute(
        "UPDATE sirket SET kisa_ad=COALESCE(NULLIF(kisa_ad,''), unvan), "
        "vergi_dairesi=COALESCE(vergi_dairesi, 'Batman'), "
        "vergi_no=COALESCE(vergi_no, '4810001234'), "
        "adres=COALESCE(adres, 'Kültür Mah. Atatürk Bulvarı No:12 Batman'), "
        "telefon=COALESCE(telefon, '+90 488 215 44 55'), "
        "email=COALESCE(email, 'info@brnteknoloji.com') "
        "WHERE id=1 AND (vergi_no IS NULL OR vergi_no='')",
    )
    # N-N: yeni oluşturulan kullanıcıları 1. şirkete üye yap.
    conn.execute(
        "INSERT OR IGNORE INTO kullanici_sirket(kullanici_id, sirket_id) SELECT id, 1 FROM kullanici"
    )

    # --- Cari grupları ---
    gruplar = [
        ("Batman", "Bölge", "Batman ve ilçeleri"),
        ("Diyarbakır", "Bölge", "Diyarbakır ve ilçeleri"),
        ("Siirt", "Bölge", "Siirt ve ilçeleri"),
        ("Mardin", "Bölge", "Mardin ve ilçeleri"),
        ("Kurumsal", "Segment", "Kurumsal müşteriler"),
        ("Bayi", "Segment", "Bayi / toptan alıcılar"),
        ("Son Kullanıcı", "Segment", "Bireysel son kullanıcı"),
        ("VIP", "Sadakat", "Yüksek hacimli sadık müşteriler"),
        ("Standart", "Sadakat", "Standart müşteriler"),
    ]
    grup_ids = {}
    for ad, tip, aciklama in gruplar:
        cur = conn.execute(
            "INSERT INTO cari_grup(ad, tip, aciklama) VALUES(?,?,?)", (ad, tip, aciklama)
        )
        grup_ids[ad] = cur.lastrowid

    # --- Cari kartlar ---
    cariler = [
        # kod, unvan, kisa_ad, tip, vd, vno, adres, il, ilce, tel, gsm, mail, yetkili, limit, pb, isk, grup
        ("BAT-001", "Batman Çarşı Elektronik", "Çarşı Elektronik", "Musteri",
         "Batman", "4810009988", "Eski Sanayi Cad. No:45", "Batman", "Merkez",
         "0488 213 10 20", "0532 111 22 33", "carsi@ornek.com", "Serdar Acar", 50000, "TRY", 5, "Batman"),
        ("DIY-001", "Dicle AVM Beyaz Eşya", "Dicle AVM", "Musteri",
         "Diyarbakır", "4510002233", "Yenişehir Mah. AVM Kat:2", "Diyarbakır", "Yenişehir",
         "0412 228 77 88", "0533 444 55 66", "dicleavm@ornek.com", "Zeynep Doğan", 120000, "TRY", 8, "Diyarbakır"),
        ("SRT-001", "Siirt Teknoloji Market", "Siirt Tekno", "Musteri",
         "Siirt", "4610004455", "Hükümet Cad. No:8", "Siirt", "Merkez",
         "0484 223 33 44", "0534 777 88 99", "siirt@ornek.com", "İbrahim Kurt", 30000, "TRY", 0, "Siirt"),
        ("MRD-001", "Mardin Star Dayanıklı Tüketim", "Mardin Star", "Musteri",
         "Mardin", "4710005566", "1. Cadde No:23", "Mardin", "Artuklu",
         "0482 213 55 66", "0535 222 33 44", "mardin@ornek.com", "Selma Ay", 45000, "TRY", 3, "Mardin"),
        ("TED-001", "Vestel Bölge Distribütörü A.Ş.", "Vestel Dist.", "Tedarikci",
         "İstanbul", "7310001122", "Organize Sanayi Bölgesi", "İstanbul", "Esenyurt",
         "0212 886 60 00", "0530 123 45 67", "bayi@vesteldist.com", "Cem Yılmaz", 0, "TRY", 0, "Bayi"),
        ("TED-002", "Arçelik Pazarlama A.Ş.", "Arçelik Paz.", "Tedarikci",
         "İstanbul", "7310002233", "Sütlüce Mah.", "İstanbul", "Beyoğlu",
         "0212 314 34 34", "0530 999 88 77", "bayi@arcelikpaz.com", "Ali Vural", 0, "TRY", 0, "Kurumsal"),
        ("MSU-001", "Güneş Teknik Servis", "Güneş Servis", "HerIkisi",
         "Batman", "4810003344", "Diyarbakır Cad. No:3", "Batman", "Merkez",
         "0488 214 12 12", "0536 555 66 77", "gunesservis@ornek.com", "Halil Güneş", 20000, "TRY", 2, "Batman"),
        ("MSU-002", "Beyaz Eşya Tamir Atölyesi", "Tamir Atölyesi", "Musteri",
         "Batman", "4810006677", "Sanayi Sitesi C Blok", "Batman", "Merkez",
         "0488 215 90 90", "0537 111 00 22", "atolye@ornek.com", "Osman Koç", 10000, "TRY", 0, "Son Kullanıcı"),
    ]
    cari_ids = {}
    for c in cariler:
        (kod, unvan, kisa, tip, vd, vno, adres, il, ilce, tel, gsm, mail, yetkili,
         limit, pb, isk, grup) = c
        cur = conn.execute(
            "INSERT INTO cari_kart(kod, unvan, kisa_ad, tip, vergi_dairesi, vergi_no, adres, il, ilce, "
            "telefon, gsm, email, yetkili, kredi_limiti, para_birimi, iskonto_orani, grup_id) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (kod, unvan, kisa, tip, vd, vno, adres, il, ilce, tel, gsm, mail, yetkili,
             limit, pb, isk, grup_ids.get(grup)),
        )
        cari_ids[kod] = cur.lastrowid

    # --- Cari hareketler (örnek ekstre) ---
    hareketler = [
        ('BAT-001', '2026-05-15', '2026-06-15', 'Açılış Bakiyesi', 'ACL-001', 'Dönem açılış bakiyesi', 25000.0, 0.0),
        ('BAT-001', '2026-06-20', '2026-07-20', 'Satış Faturası', 'SF-2026-001', 'Beyaz eşya satışı', 18500.0, 0.0),
        ('BAT-001', '2026-07-10', None, 'Tahsilat', 'T-001', 'Nakit tahsilat', 0.0, 15000.0),
        ('BAT-001', '2026-08-10', '2026-08-25', 'Satış Faturası', 'SF-2026-014', 'TV + buzdolabı satışı', 9000.0, 0.0),
        ('DIY-001', '2026-08-02', '2026-09-15', 'Satış Faturası', 'SF-2026-021', 'Kurumsal satış', 60000.0, 0.0),
        ('DIY-001', '2026-08-20', None, 'Tahsilat', 'T-002', 'Havale ile tahsilat', 0.0, 20000.0),
        ('SRT-001', '2026-07-05', '2026-08-05', 'Satış Faturası', 'SF-2026-007', 'Klima satışı', 22000.0, 0.0),
        ('SRT-001', '2026-08-01', None, 'Tahsilat', 'T-003', 'Kısmi tahsilat', 0.0, 12000.0),
        ('MRD-001', '2026-06-10', '2026-07-10', 'Satış Faturası', 'SF-2026-003', 'Çamaşır makinesi', 14000.0, 0.0),
        ('MRD-001', '2026-08-28', '2026-09-28', 'Satış Faturası', 'SF-2026-027', 'Televizyon satışı', 18000.0, 0.0),
        ('TED-001', '2026-07-22', '2026-08-30', 'Alış Faturası', 'AF-2026-009', 'Vestel ürün alımı', 0.0, 80000.0),
        ('TED-001', '2026-08-12', None, 'Ödeme', 'O-001', 'Havale ile ödeme', 30000.0, 0.0),
        ('TED-002', '2026-08-18', '2026-09-18', 'Alış Faturası', 'AF-2026-015', 'Arçelik parça alımı', 0.0, 45000.0),
        ('MSU-001', '2026-08-25', '2026-09-10', 'Satış Faturası', 'SF-2026-030', 'Yedek parça satışı', 6500.0, 0.0),
        ('MSU-002', '2026-09-01', '2026-09-15', 'Satış Faturası', 'SF-2026-033', 'Servis parçası satışı', 3200.0, 0.0),
    ]
    for h in hareketler:
        kod, tarih, vade, bt, bno, acik, borc, alacak = h
        conn.execute(
            "INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, borc, alacak) "
            "VALUES(?,?,?,?,?,?,?,?)",
            (cari_ids.get(kod), tarih, vade, bt, bno, acik, borc, alacak),
        )

    conn.commit()
    conn.close()
    seed_stok()
    seed_kasa()
    seed_banka()
    seed_sube()
    seed_teklif()
    seed_siparis()
    seed_satin_alma()
    seed_alinan_teklif()
    seed_eksik_teslimat()
    seed_irsaliye()
    seed_fatura()
    seed_cek_senet()
    seed_doviz()
    seed_servis()
    seed_edonusum()
    seed_muhasebe()
    seed_pos()
    seed_bakim()
    seed_crm()
    seed_finansal()
    seed_demirbas()
    seed_faz6()


# --- D012-X — para birimi + birim tohumları (config sabit listelerinden, idempotent) ---
PARA_BIRIMI_SEED = [("TRY", "Türk Lirası"), ("USD", "ABD Doları"),
                    ("EUR", "Euro"), ("GBP", "İngiliz Sterlini")]
BIRIM_SEED = ["Adet", "Kutu", "Paket", "Çift", "Takım", "Metre", "m²", "Kg", "Lt", "Top", "Rulo"]


def seed_para_birimi():
    """D012-X — para_birimi tablosunu config sabit listesinden tohumlar (idempotent)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM para_birimi WHERE sirket_id=1").fetchone()["c"]
    if n == 0:
        for kod, ad in PARA_BIRIMI_SEED:
            conn.execute("INSERT OR IGNORE INTO para_birimi(kod, ad, aktif, sirket_id) "
                         "VALUES(?,?,1,1)", (kod, ad))
        conn.commit()
    conn.close()


def seed_birim():
    """D012-X — birim tablosunu config sabit listesinden tohumlar (idempotent)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) c FROM birim WHERE sirket_id=1").fetchone()["c"]
    if n == 0:
        for ad in BIRIM_SEED:
            conn.execute("INSERT OR IGNORE INTO birim(ad, aktif, sirket_id) VALUES(?,1,1)", (ad,))
        conn.commit()
    conn.close()


def para_birimleri(conn=None, sid=None, aktif=True):
    """D012-X — aktif para birimi kodları (DB tablo). Tablo boşsa config sabit listesine düşer."""
    own = conn is None
    if own:
        conn = get_conn()
    try:
        sid = sid if sid is not None else 1
        q = "SELECT kod FROM para_birimi WHERE sirket_id=?"
        if aktif:
            q += " AND aktif=1"
        q += " ORDER BY id"
        kodlar = [r["kod"] for r in conn.execute(q, (sid,)).fetchall()]
        if not kodlar:
            kodlar = list(PARA_BIRIMLERI)
        return kodlar
    finally:
        if own:
            conn.close()


def birimler(conn=None, sid=None, aktif=True):
    """D012-X — aktif birim adları (DB tablo). Tablo boşsa config sabit listesine düşer."""
    own = conn is None
    if own:
        conn = get_conn()
    try:
        sid = sid if sid is not None else 1
        q = "SELECT ad FROM birim WHERE sirket_id=?"
        if aktif:
            q += " AND aktif=1"
        q += " ORDER BY id"
        adlar = [r["ad"] for r in conn.execute(q, (sid,)).fetchall()]
        if not adlar:
            adlar = list(BIRIM_SEED)
        return adlar
    finally:
        if own:
            conn.close()


def seed_demirbas():
    """Faz 5 — Demirbaş (1.22): örnek kategoriler + 3 demirbaş kartı (idempotent)."""
    conn = get_conn()
    if conn.execute("SELECT COUNT(*) c FROM demirbas_kategori").fetchone()["c"] == 0:
        for ad, omur, acik in (
            ("Bilgisayar & Ekipman", 4, "VUK: %25 — 4 yıl"),
            ("Mobilya & Demirbaş", 10, "VUK: %10 — 10 yıl"),
            ("Makine & Teçhizat", 10, "VUK: %10 — 10 yıl"),
            ("Taşıt", 5, "VUK: %20 — 5 yıl"),
            ("Diğer", 5, "VUK: %20 — 5 yıl"),
        ):
            conn.execute("INSERT INTO demirbas_kategori(ad, omur_yil, aciklama) VALUES(?,?,?)",
                         (ad, omur, acik))
    if conn.execute("SELECT COUNT(*) c FROM demirbas").fetchone()["c"] == 0:
        for kod, ad, kat, alis, maliyet, hurda, zim, acik in (
            ("DBR-2026-001", "Dizüstü Bilgisayar (Muhasebe)", "Bilgisayar & Ekipman",
             "2026-08-15", 45000.0, 0.0, "muhasebe", "Muhasebe odası dizüstü bilgisayar"),
            ("DBR-2026-002", "Klima (Mağaza)", "Makine & Teçhizat",
             "2026-09-02", 28000.0, 0.0, "depo", "Mağaza salon kliması"),
            ("DBR-2026-003", "Servis Tezgahı", "Mobilya & Demirbaş",
             "2026-09-05", 16000.0, 0.0, "servis", "Teknik servis tezgahı"),
        ):
            kat_id = conn.execute("SELECT id FROM demirbas_kategori WHERE ad=?", (kat,)).fetchone()
            u = conn.execute("SELECT id FROM kullanici WHERE kullanici_adi=?", (zim,)).fetchone()
            s = conn.execute("SELECT id FROM sube ORDER BY id LIMIT 1").fetchone()
            conn.execute(
                "INSERT INTO demirbas(kod, ad, kategori_id, alis_tarihi, maliyet, hurda_degeri, "
                "sube_id, zimmetli_kullanici_id, aciklama) VALUES(?,?,?,?,?,?,?,?,?)",
                (kod, ad, kat_id["id"] if kat_id else None, alis, maliyet, hurda,
                 s["id"] if s else None, u["id"] if u else None, acik))
            did = conn.execute("SELECT id FROM demirbas WHERE kod=?", (kod,)).fetchone()["id"]
            conn.execute(
                "INSERT INTO demirbas_zimmet(demirbas_id, kullanici_id, sube_id, islem, aciklama) "
                "VALUES(?,?,?,?,?)",
                (did, u["id"] if u else None, s["id"] if s else None, "Teslim", "İlk zimmet (örnek)"))
    conn.commit()
    conn.close()


def seed_faz6():
    """Faz 6 — Cila: ikinci örnek şube + şube atamaları + belge sube_id backfill (idempotent).

    K1 (şube izolasyonu) Faz 6'da açıldığı için:
    1. Mevcut tek şubeli verilerin belge tablolarındaki NULL sube_id'leri ilk şubeye bağlanır.
    2. Demo amaçlı ikinci bir şube (Diyarbakır) + kendi depo/kasa'sı eklenir (mizana etkisi yok).
    3. `depo` kullanıcısı Batman Merkez Şube'ye (sube 1) atanır → şubeli kullanıcı örneği.
    """
    conn = get_conn()
    ilk = conn.execute("SELECT id FROM sube WHERE aktif=1 ORDER BY id LIMIT 1").fetchone()
    if not ilk:
        conn.close()
        return
    sid1 = ilk["id"]

    # 1) Belge tablolarında NULL kalan sube_id'leri ilk şubeye bağla (tek şubeli geçmiş veri).
    for t in ("teklif", "siparis", "irsaliye", "fatura", "cek_senet", "servis_kayit"):
        conn.execute(f"UPDATE {t} SET sube_id=? WHERE sube_id IS NULL", (sid1,))

    # Yevmiye fişleri kaynağından backfill (muhasebe.sube_backfill ile aynı mantık).
    try:
        import muhasebe  # noqa: F401
        muhasebe.sube_backfill(conn)
    except Exception:
        pass

    # 2) İkinci örnek şube + depo + kasa (idempotent).
    n2 = conn.execute("SELECT COUNT(*) c FROM sube WHERE kod='SUB-02'").fetchone()["c"]
    if n2 == 0:
        conn.execute(
            "INSERT INTO sube(kod, ad, il, ilce, adres, telefon, aktif) "
            "VALUES('SUB-02','Diyarbakır Şube','Diyarbakır','Merkez',"
            "'Ofis Mah. Yenişehir Cad. No:8 Diyarbakır','+90 412 228 11 22',1)")
        sid2 = conn.execute("SELECT id FROM sube WHERE kod='SUB-02'").fetchone()["id"]
        conn.execute("INSERT INTO depo(kod, ad, tip, aktif, sube_id) "
                     "VALUES('DYB','Diyarbakır Depo','Ana',1,?)", (sid2,))
        conn.execute("INSERT INTO kasa(kod, ad, aktif, sube_id) "
                     "VALUES('KAS-DYB','Diyarbakır Kasa',1,?)", (sid2,))

    # 3) `depo` kullanıcısını ilk şubeye ata (yalnızca henüz atanmamışsa).
    conn.execute("UPDATE kullanici SET sube_id=? WHERE kullanici_adi='depo' AND sube_id IS NULL",
                 (sid1,))

    # Bildirim sağlayıcı varsayılan ayarı (kapalı).
    conn.execute(
        "INSERT INTO meta(anahtar, deger) VALUES('bildirim.kanal','kapali') "
        "ON CONFLICT(anahtar) DO NOTHING")
    conn.commit()
    conn.close()


def seed_stok():
    """Örnek veriler (seed_stok)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM stok_kart").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # kategori
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (1, None, 'Televizyon', 1))
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (2, None, 'Buzdolabı', 1))
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (3, None, 'Çamaşır Makinesi', 1))
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (4, None, 'Klima', 1))
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (5, None, 'Küçük Ev Aletleri', 1))
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (6, None, 'Yedek Parça', 1))
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (7, 3, 'Kurutma Makinesi', 1))
    conn.execute("INSERT INTO kategori(id, ust_id, ad, aktif) VALUES(?,?,?,?)", (8, None, 'Telefon', 1))
    # marka
    conn.execute("INSERT INTO marka(id, ad, aktif) VALUES(?,?,?)", (1, 'Vestel', 1))
    conn.execute("INSERT INTO marka(id, ad, aktif) VALUES(?,?,?)", (2, 'Arçelik', 1))
    conn.execute("INSERT INTO marka(id, ad, aktif) VALUES(?,?,?)", (3, 'Samsung', 1))
    conn.execute("INSERT INTO marka(id, ad, aktif) VALUES(?,?,?)", (4, 'LG', 1))
    conn.execute("INSERT INTO marka(id, ad, aktif) VALUES(?,?,?)", (5, 'Bosch', 1))
    conn.execute("INSERT INTO marka(id, ad, aktif) VALUES(?,?,?)", (6, 'Beko', 1))
    conn.execute("INSERT INTO marka(id, ad, aktif) VALUES(?,?,?)", (7, 'TTEC', 1))
    # stok_kart
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (1, 'TV-43-SAM-001', 'Samsung 43" Crystal UHD 4K TV', '8691234500011', 3, 1, 'Adet', 20.0, 0.0, 14500.0, 17999.0, 'TRY', 0.0, 3.0, 1, 0, 'Ekran: 43" UHD · Çözünürlük: 3840x2160 · HDR · 3xHDMI · Smart TV', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (2, 'TV-55-SAM-002', 'Samsung 55" QLED 4K TV', '8691234500028', 3, 1, 'Adet', 20.0, 0.0, 28000.0, 34999.0, 'TRY', 5.0, 2.0, 1, 0, 'Ekran: 55" QLED · 120Hz · Dolby Atmos', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (3, 'BUZ-510-VST-003', 'Vestel 510L No-Frost Buzdolabı', '8691234500035', 1, 2, 'Adet', 20.0, 0.0, 16000.0, 19499.0, 'TRY', 3.0, 2.0, 0, 0, 'Hacim: 510L · No-Frost · A+ enerji', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (4, 'CM-9KG-ARC-004', 'Arçelik 9kg 1400 Devir Çamaşır Makinesi', '8691234500042', 2, 3, 'Adet', 20.0, 0.0, 15000.0, 18499.0, 'TRY', 5.0, 2.0, 0, 0, '9kg · 1400 devir · Buhar destekli', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (5, 'KLM-12000-VST-005', 'Vestel 12000 BTU Inverter Klima', '8691234500059', 1, 4, 'Adet', 20.0, 0.0, 17000.0, 21999.0, 'TRY', 5.0, 2.0, 0, 0, '12000 BTU · A++ · Inverter', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (6, 'TEL-13-BEK-006', 'Beko 13 Programlı Bulaşık Makinesi', '8691234500066', 6, 5, 'Adet', 20.0, 0.0, 13500.0, 16499.0, 'TRY', 0.0, 2.0, 0, 0, '13 program · 6 kişilik', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (7, 'PAR-DRM-VST-007', 'Vestel Çamaşır Makinesi Kayışı (Yedek Parça)', '8691234500073', 1, 6, 'Adet', 20.0, 0.0, 120.0, 240.0, 'TRY', 0.0, 5.0, 0, 0, 'Servis yedek parça', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (8, 'PAR-KRT-ARC-008', 'Arçelik Buzdolabı Kompresörü', '8691234500080', 2, 6, 'Adet', 20.0, 0.0, 2500.0, 3800.0, 'TRY', 0.0, 2.0, 0, 0, 'Servis yedek parça', 1))
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (9, 'TEL-14-LG-009', 'LG 14kg Yıkama + 8kg Kurutma (Beyaz)', '8691234500097', 4, 3, 'Adet', 20.0, 0.0, 32000.0, 39999.0, 'TRY', 8.0, 1.0, 0, 1, 'Kombine · Renk: Beyaz · Inox (varyant)', 1))
    # D007 madde 4 — "TTEC" ürünü (kullanıcı bildirimi repro'su; typeahead filtre testi)
    conn.execute("INSERT INTO stok_kart(id, kod, ad, barkod, marka_id, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, teknik_ozellikler, aktif) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (10, 'TV-40-TTEC-010', 'TTEC 40" Full HD TV', '8691234500127', 7, 1, 'Adet', 20.0, 0.0, 9000.0, 11999.0, 'TRY', 0.0, 2.0, 0, 0, 'Ekran: 40" FHD · HDMI · USB', 1))
    # stok_varyant
    conn.execute("INSERT INTO stok_varyant(id, stok_id, varyant_kodu, ad, ozellikler, barkod, alis_fiyat, satis_fiyat, kritik_stok, aktif) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 9, 'TEL-14-LG-009-W', 'Beyaz', 'Renk: Beyaz', '8691234500103', 32000.0, 39999.0, 1.0, 1))
    conn.execute("INSERT INTO stok_varyant(id, stok_id, varyant_kodu, ad, ozellikler, barkod, alis_fiyat, satis_fiyat, kritik_stok, aktif) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 9, 'TEL-14-LG-009-I', 'Inox', 'Renk: Inox', '8691234500110', 33000.0, 41499.0, 1.0, 1))
    # stok_tedarikci
    conn.execute("INSERT INTO stok_tedarikci(id, stok_id, cari_id, tedarikci_kod, alis_fiyat, oncelik, aktif) VALUES(?,?,?,?,?,?,?)", (1, 1, 5, 'VST-430', 14500.0, 1, 1))
    conn.execute("INSERT INTO stok_tedarikci(id, stok_id, cari_id, tedarikci_kod, alis_fiyat, oncelik, aktif) VALUES(?,?,?,?,?,?,?)", (2, 4, 6, 'ARC-9KG', 15000.0, 1, 1))
    conn.execute("INSERT INTO stok_tedarikci(id, stok_id, cari_id, tedarikci_kod, alis_fiyat, oncelik, aktif) VALUES(?,?,?,?,?,?,?)", (3, 3, 5, 'VST-510', 16000.0, 1, 1))
    # stok_seri
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 1, 0, 'SAM43UHD00001', 'Satıldı', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 1, 0, 'SAM43UHD00002', 'Satıldı', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (3, 1, 0, 'SAM43UHD00003', 'Satıldı', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (4, 1, 0, 'SAM43UHD00004', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (5, 1, 0, 'SAM43UHD00005', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (6, 1, 0, 'SAM43UHD00006', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (7, 1, 0, 'SAM43UHD00007', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (8, 1, 0, 'SAM43UHD00008', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (9, 1, 0, 'SAM43UHD00009', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (10, 1, 0, 'SAM43UHD00010', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (11, 1, 0, 'SAM43UHD00011', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (12, 1, 0, 'SAM43UHD00012', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (13, 2, 0, 'SAM55QLED0001', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (14, 2, 0, 'SAM55QLED0002', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (15, 2, 0, 'SAM55QLED0003', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (16, 2, 0, 'SAM55QLED0004', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (17, 2, 0, 'SAM55QLED0005', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    conn.execute("INSERT INTO stok_seri(id, stok_id, varyant_id, seri_no, durum, depo_id, giris_tarihi, cikis_tarihi, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (18, 2, 0, 'SAM55QLED0006', 'Stokta', 1, '2026-09-07 12:34:27', None, None, None))
    # stok_hareket
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (1, 1, 0, 1, '2026-06-01', 'Stok Girişi (Alış)', 15.0, 14500.0, 'Vestel Dist. alım', 'AF-2026-001', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (2, 1, 0, 1, '2026-07-20', 'Satış Çıkışı', -3.0, 14500.0, 'Satış Faturası', 'SF-2026-014', None, 'Satis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (3, 2, 0, 1, '2026-07-02', 'Stok Girişi (Alış)', 8.0, 28000.0, 'Vestel Dist. alım', 'AF-2026-002', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (4, 2, 0, 1, '2026-08-10', 'Satış Çıkışı', -2.0, 28000.0, 'Satış Faturası', 'SF-2026-021', None, 'Satis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (5, 3, 0, 1, '2026-06-05', 'Stok Girişi (Alış)', 10.0, 16000.0, 'Vestel Dist. alım', 'AF-2026-003', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (6, 3, 0, 1, '2026-07-05', 'Satış Çıkışı', -2.0, 16000.0, 'Satış Faturası', 'SF-2026-007', None, 'Satis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (7, 4, 0, 1, '2026-06-10', 'Stok Girişi (Alış)', 8.0, 15000.0, 'Arçelik Paz. alım', 'AF-2026-004', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (8, 4, 0, 1, '2026-06-11', 'Depolar Arası Transfer', -2.0, 15000.0, 'Ana → Mağaza', 'TRF-2026-001', None, 'Transfer', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (9, 4, 0, 2, '2026-06-11', 'Depolar Arası Transfer', 2.0, 15000.0, 'Ana → Mağaza', 'TRF-2026-001', None, 'Transfer', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (10, 5, 0, 1, '2026-07-01', 'Stok Girişi (Alış)', 5.0, 17000.0, 'Vestel Dist. alım', 'AF-2026-005', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (11, 6, 0, 1, '2026-07-08', 'Stok Girişi (Alış)', 2.0, 13500.0, 'Arçelik Paz. alım', 'AF-2026-006', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (12, 7, 0, 3, '2026-08-12', 'Stok Girişi (Alış)', 10.0, 120.0, 'Arçelik Paz. alım', 'AF-2026-015', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (13, 8, 0, 3, '2026-08-12', 'Stok Girişi (Alış)', 2.0, 2500.0, 'Arçelik Paz. alım', 'AF-2026-015', None, 'Alis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (14, 7, 0, 3, '2026-08-15', 'Servis Tüketimi', -2.0, 120.0, 'Servis kaydı SV-2026-005', 'SV-2026-005', None, 'Servis', None))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (15, 1, 0, 1, '2026-09-06', 'İrsaliye Çıkışı', -1.0, None, 'IRS-2026-001', 'IRS-2026-001', None, 'Irsaliye', 1))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (16, 2, 0, 1, '2026-09-06', 'İrsaliye Girişi', 2.0, None, 'IRA-2026-001', 'IRA-2026-001', None, 'Irsaliye', 2))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (17, 4, 0, 1, '2026-09-06', 'İrsaliye Girişi', 2.0, None, 'IRA-2026-001', 'IRA-2026-001', None, 'Irsaliye', 2))
    conn.execute("INSERT INTO stok_hareket(id, stok_id, varyant_id, depo_id, tarih, islem_tipi, miktar, birim_maliyet, aciklama, belge_no, seri_nolar, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (18, 1, 0, 1, '2026-09-07', 'İrsaliye Çıkışı', -1.0, None, 'IRS-2026-002', 'IRS-2026-002', None, 'Irsaliye', 3))
    # stok_seviye
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (1, 1, 0, 1, 10.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (2, 1, 0, 2, 2.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (3, 2, 0, 1, 8.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (4, 2, 0, 2, 1.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (5, 3, 0, 1, 8.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (6, 3, 0, 2, 2.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (7, 4, 0, 1, 8.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (8, 4, 0, 2, 2.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (9, 5, 0, 1, 5.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (10, 6, 0, 1, 2.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (11, 7, 0, 1, 8.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (12, 7, 0, 3, 10.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (13, 8, 0, 1, 3.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (14, 8, 0, 3, 2.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (15, 9, 1, 1, 2.0, 0.0, 0.0, 0.0))
    conn.execute("INSERT INTO stok_seviye(id, stok_id, varyant_id, depo_id, miktar, rezerve, min_stok, max_stok) VALUES(?,?,?,?,?,?,?,?)", (16, 9, 2, 1, 1.0, 0.0, 0.0, 0.0))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_kasa():
    """Örnek veriler (seed_kasa)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM kasa").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # kasa
    conn.execute("INSERT INTO kasa(id, kod, ad, aktif, sube_id) VALUES(?,?,?,?,?)", (1, 'KAS-01', 'Mağaza Kasası', 1, 1))
    conn.execute("INSERT INTO kasa(id, kod, ad, aktif, sube_id) VALUES(?,?,?,?,?)", (2, 'KAS-02', 'Servis Kasası', 1, 1))
    # kasa_hareket
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 1, '2026-06-01', 'Açılış Bakiyesi', 20000.0, None, 'Dönem açılış bakiyesi', None, None, None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 1, '2026-07-10', 'Nakit Girişi', 15000.0, 1, 'Batman Çarşı Elektronik tahsilat', 'T-001', None, None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (3, 1, '2026-08-01', 'Nakit Girişi', 12000.0, 3, 'Siirt Tekno kısmi tahsilat', 'T-003', None, None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (4, 1, '2026-08-12', 'Kasa → Banka', 30000.0, None, 'Banka hesabına yatırıldı', 'TR-001', 'Transfer', None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (5, 1, '2026-08-20', 'Nakit Girişi', 20000.0, 2, 'Dicle AVM tahsilat', 'T-002', None, None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (6, 1, '2026-08-25', 'Nakit Çıkışı', 6500.0, 5, 'Vestel Dist. küçük ödeme (nakit)', 'O-002', None, None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (7, 2, '2026-06-01', 'Açılış Bakiyesi', 5000.0, None, 'Servis kasası açılış', None, None, None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (8, 2, '2026-08-15', 'Nakit Girişi', 2400.0, 7, 'Servis işçilik tahsilatı', 'SV-2026-005', None, None))
    conn.execute("INSERT INTO kasa_hareket(id, kasa_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (9, 2, '2026-08-28', 'Nakit Çıkışı', 1200.0, 6, 'Servis yedek parça peşin ödemesi', 'O-003', None, None))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_banka():
    """Örnek veriler (seed_banka)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM banka_hesap").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # banka_hesap
    conn.execute("INSERT INTO banka_hesap(id, kod, ad, banka_adi, sube, iban, hesap_no, para_birimi, aktif, sube_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 'BNK-01', 'Ziraat Bankası — Ticari Hesap', 'Ziraat Bankası', 'Batman Merkez', 'TR12 0001 0001 1234 5678 9012 34', '001234-001', 'TRY', 1, 1))
    conn.execute("INSERT INTO banka_hesap(id, kod, ad, banka_adi, sube, iban, hesap_no, para_birimi, aktif, sube_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 'BNK-02', 'Garanti BBVA — Cari Hesap', 'Garanti BBVA', 'Batman Merkez', 'TR62 0006 2000 1234 0006 1234 56', '612345-01', 'TRY', 1, 1))
    # banka_hareket
    conn.execute("INSERT INTO banka_hareket(id, banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 1, '2026-06-01', 'Açılış Bakiyesi', 100000.0, None, 'Dönem açılış bakiyesi', None, None, None))
    conn.execute("INSERT INTO banka_hareket(id, banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 1, '2026-08-12', 'Havale/EFT Çıkışı', 30000.0, 5, 'Vestel Dist. ödeme', 'O-001', None, None))
    conn.execute("INSERT INTO banka_hareket(id, banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (3, 1, '2026-08-12', 'Kasa → Banka', 30000.0, None, 'Kasadan yatırılan', 'TR-001', 'Transfer', 4))
    conn.execute("INSERT INTO banka_hareket(id, banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (4, 1, '2026-08-20', 'Havale/EFT Girişi', 20000.0, 2, 'Dicle AVM havale tahsilat', 'T-002', None, None))
    conn.execute("INSERT INTO banka_hareket(id, banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (5, 2, '2026-06-01', 'Açılış Bakiyesi', 50000.0, None, 'Dönem açılış bakiyesi', None, None, None))
    conn.execute("INSERT INTO banka_hareket(id, banka_hesap_id, tarih, islem_tipi, tutar, cari_id, aciklama, belge_no, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?)", (6, 2, '2026-08-25', 'Havale/EFT Çıkışı', 18000.0, 6, 'Arçelik Paz. kısmi ödeme', 'O-004', None, None))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_sube():
    """Örnek veriler (seed_sube)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM sube").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # sube
    conn.execute("INSERT INTO sube(id, kod, ad, il, ilce, adres, telefon, aktif) VALUES(?,?,?,?,?,?,?,?)", (1, 'SUB-01', 'Batman Merkez Şube', 'Batman', 'Merkez', 'Kültür Mah. Atatürk Bulvarı No:12 Batman', '+90 488 215 44 55', 1))
    # depo
    conn.execute("INSERT INTO depo(id, kod, ad, tip, aktif, sube_id) VALUES(?,?,?,?,?,?)", (1, 'ANA', 'Ana Depo (Batman)', 'Ana', 1, 1))
    conn.execute("INSERT INTO depo(id, kod, ad, tip, aktif, sube_id) VALUES(?,?,?,?,?,?)", (2, 'MAG', 'Mağaza Deposu', 'Mağaza', 1, 1))
    conn.execute("INSERT INTO depo(id, kod, ad, tip, aktif, sube_id) VALUES(?,?,?,?,?,?)", (3, 'SRV', 'Servis Yedek Parça', 'Servis', 1, 1))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_teklif():
    """Örnek veriler (seed_teklif)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM teklif").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # teklif
    conn.execute("INSERT INTO teklif(id, teklif_no, cari_id, sube_id, tarih, gecerlilik_tarihi, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (1, 'TKF-2026-001', 1, None, '2026-08-25', '2026-09-25', 'Gönderildi', 'TRY', None, 53572.05, 924.95, 10714.41, 64286.46, 'Kurumsal kampanya teklifi'))
    conn.execute("INSERT INTO teklif(id, teklif_no, cari_id, sube_id, tarih, gecerlilik_tarihi, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (2, 'TKF-2026-002', 2, None, '2026-09-02', '2026-09-16', 'Taslak', 'TRY', None, 98540.19, 3954.81, 19708.04, 118248.23, 'Yeni mağaza açılışı için beyaz eşya'))
    conn.execute("INSERT INTO teklif(id, teklif_no, cari_id, sube_id, tarih, gecerlilik_tarihi, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (3, 'TKF-2026-003', 3, None, '2026-08-10', '2026-08-20', 'Onaylandı', 'TRY', None, 33249.05, 1749.95, 6649.81, 39898.86, 'Mağaza vitrini TV teklifi'))
    # teklif_kalem
    conn.execute("INSERT INTO teklif_kalem(id, teklif_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 1, 1, 0, 2.0, 17999.0, 0.0, 20.0, 35998.0, None))
    conn.execute("INSERT INTO teklif_kalem(id, teklif_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 1, 4, 0, 1.0, 18499.0, 5.0, 20.0, 17574.05, None))
    conn.execute("INSERT INTO teklif_kalem(id, teklif_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (3, 2, 3, 0, 3.0, 19499.0, 3.0, 20.0, 56742.09, None))
    conn.execute("INSERT INTO teklif_kalem(id, teklif_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (4, 2, 5, 0, 2.0, 21999.0, 5.0, 20.0, 41798.1, None))
    conn.execute("INSERT INTO teklif_kalem(id, teklif_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (5, 3, 2, 0, 1.0, 34999.0, 5.0, 20.0, 33249.05, None))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_siparis():
    """Örnek veriler (seed_siparis)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM siparis").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # siparis
    conn.execute("INSERT INTO siparis(id, siparis_no, tip, cari_id, sube_id, depo_id, kaynak_teklif_id, tarih, teslim_tarihi, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (1, 'SIP-2026-001', 'Musteri', 1, None, 1, None, '2026-09-03', '2026-09-18', 'Tamamlandı', 'TRY', None, 17999.0, 0.0, 3599.8, 21598.8, 'Mağaza vitrini TV siparişi'))
    conn.execute("INSERT INTO siparis(id, siparis_no, tip, cari_id, sube_id, depo_id, kaynak_teklif_id, tarih, teslim_tarihi, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (2, 'SIP-2026-002', 'Musteri', 2, None, 1, None, '2026-09-05', '2026-09-25', 'Bekliyor', 'TRY', None, 58727.11, 2269.89, 11745.42, 70472.53, 'Yeni mağaza açılışı beyaz eşya siparişi'))
    conn.execute("INSERT INTO siparis(id, siparis_no, tip, cari_id, sube_id, depo_id, kaynak_teklif_id, tarih, teslim_tarihi, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (3, 'SAP-2026-001', 'Alis', 5, None, None, None, '2026-09-04', '2026-09-20', 'Tamamlandı', 'TRY', None, 86000.0, 0.0, 17200.0, 103200.0, 'Vestel distribütöründen ürün alım siparişi'))
    # siparis_kalem
    conn.execute("INSERT INTO siparis_kalem(id, siparis_id, stok_id, varyant_id, miktar, teslim_edilen, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (1, 1, 1, 0, 1.0, 1.0, 17999.0, 0.0, 20.0, 17999.0, None))
    conn.execute("INSERT INTO siparis_kalem(id, siparis_id, stok_id, varyant_id, miktar, teslim_edilen, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (2, 2, 3, 0, 2.0, 0.0, 19499.0, 3.0, 20.0, 37828.06, None))
    conn.execute("INSERT INTO siparis_kalem(id, siparis_id, stok_id, varyant_id, miktar, teslim_edilen, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (3, 2, 5, 0, 1.0, 0.0, 21999.0, 5.0, 20.0, 20899.05, None))
    conn.execute("INSERT INTO siparis_kalem(id, siparis_id, stok_id, varyant_id, miktar, teslim_edilen, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (4, 3, 2, 0, 2.0, 2.0, 28000.0, 0.0, 20.0, 56000.0, None))
    conn.execute("INSERT INTO siparis_kalem(id, siparis_id, stok_id, varyant_id, miktar, teslim_edilen, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?)", (5, 3, 4, 0, 2.0, 2.0, 15000.0, 0.0, 20.0, 30000.0, None))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_satin_alma():
    """Örnek veriler (B1 — Satın Alma Talebi)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM satin_alma_talebi").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    conn.execute(
        "INSERT INTO satin_alma_talebi(id, talep_no, sube_id, depo_id, tedarikci_id, kaynak, gerekce, durum, talep_eden_id, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (1, 'SAT-2026-001', None, 1, 5, 'Yurt İçi',
         'Vestel buzdolabı stoku kritik seviyeye yaklaştı; sezon öncesi takviye.', 'Onay Bekliyor', 5, 1))
    conn.execute(
        "INSERT INTO satin_alma_talebi(id, talep_no, sube_id, depo_id, tedarikci_id, kaynak, gerekce, durum, talep_eden_id, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?)",
        (2, 'SAT-2026-002', None, 1, 6, 'Yurt İçi',
         'Servis için Arçelik kompresör stoku bitti; acil tedarik.', 'Taslak', 4, 1))
    conn.execute(
        "INSERT INTO satin_alma_talebi_kalem(talep_id, stok_id, varyant_id, miktar, birim, tahmini_fiyat, oncelik, aciklama, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (1, 3, 0, 3.0, 'Adet', 16000.0, 'Normal', None, 1))
    conn.execute(
        "INSERT INTO satin_alma_talebi_kalem(talep_id, stok_id, varyant_id, miktar, birim, tahmini_fiyat, oncelik, aciklama, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?)",
        (2, 8, 0, 2.0, 'Adet', 2500.0, 'Acil', None, 1))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_alinan_teklif():
    """Örnek veriler (B2 — Alınan Teklif)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM alinan_teklif").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # ALT-2026-001: SAT-2026-001 (buzdolabı) için TED-001 (Vestel) teklifi — Alındı
    conn.execute(
        "INSERT INTO alinan_teklif(id, teklif_no, talep_id, tedarikci_id, depo_id, tarih, "
        "gecerlilik_tarihi, teslim_suresi_gun, odeme_vadesi_gun, para_birimi, doviz_kur, durum, "
        "ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (1, 'ALT-2026-001', 1, 5, 1, '2026-09-08', '2026-09-30', 7, 30, 'TRY', 1.0, 'Alındı',
         48000.0, 0.0, 9600.0, 57600.0, 'Vestel teklifi — sezon takviyesi', 1, 1))
    conn.execute(
        "INSERT INTO alinan_teklif_kalem(teklif_id, stok_id, varyant_id, miktar, birim, "
        "birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama, sirket_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (1, 3, 0, 3.0, 'Adet', 16000.0, 0.0, 20.0, 48000.0, None, 1))
    # ALT-2026-002: aynı talep için TED-002 (Arçelik) alternatif teklifi — Alındı (karşılaştırma için)
    conn.execute(
        "INSERT INTO alinan_teklif(id, teklif_no, talep_id, tedarikci_id, depo_id, tarih, "
        "gecerlilik_tarihi, teslim_suresi_gun, odeme_vadesi_gun, para_birimi, doviz_kur, durum, "
        "ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (2, 'ALT-2026-002', 1, 6, 1, '2026-09-09', '2026-10-10', 14, 45, 'TRY', 1.0, 'Alındı',
         47400.0, 0.0, 9480.0, 56880.0, 'Arçelik alternatif teklifi', 2, 1))
    conn.execute(
        "INSERT INTO alinan_teklif_kalem(teklif_id, stok_id, varyant_id, miktar, birim, "
        "birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama, sirket_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (2, 3, 0, 3.0, 'Adet', 15800.0, 0.0, 20.0, 47400.0, None, 1))
    # ALT-2026-003: SAT-2026-002 (kompresör) için TED-002 teklifi — Taslak
    conn.execute(
        "INSERT INTO alinan_teklif(id, teklif_no, talep_id, tedarikci_id, depo_id, tarih, "
        "gecerlilik_tarihi, teslim_suresi_gun, odeme_vadesi_gun, para_birimi, doviz_kur, durum, "
        "ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama, created_by, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (3, 'ALT-2026-003', 2, 6, 1, '2026-09-10', '2026-10-01', 5, 15, 'TRY', 1.0, 'Taslak',
         5000.0, 0.0, 1000.0, 6000.0, 'Arçelik kompresör teklifi (taslak)', 2, 1))
    conn.execute(
        "INSERT INTO alinan_teklif_kalem(teklif_id, stok_id, varyant_id, miktar, birim, "
        "birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama, sirket_id) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (3, 8, 0, 2.0, 'Adet', 2500.0, 0.0, 20.0, 5000.0, None, 1))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_eksik_teslimat():
    """B3 demo: kısmi teslim edilmiş bir Alış siparişi (Eksik Teslimatlar ekranı için)."""
    conn = get_conn()
    n = conn.execute(
        "SELECT COUNT(*) c FROM siparis_kalem k JOIN siparis sp ON sp.id=k.siparis_id "
        "WHERE sp.tip='Alis' AND (k.miktar - k.teslim_edilen - k.kalan_iptal) > 1e-9"
    ).fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    cur = conn.execute(
        "INSERT INTO siparis(siparis_no, tip, cari_id, sube_id, depo_id, tarih, teslim_tarihi, "
        "durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, "
        "aciklama, created_by, sirket_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
        ("SAP-2026-002", "Alis", 5, None, 1, "2026-09-05", "2026-09-08", "Kısmi",
         "TRY", 1.0, 80000.0, 0.0, 16000.0, 96000.0,
         "Vestel buzdolabı sezon takviyesi — kısmi teslim (demo)", 1, 1))
    sid = cur.lastrowid
    conn.execute(
        "INSERT INTO siparis_kalem(siparis_id, stok_id, varyant_id, miktar, teslim_edilen, "
        "kalan_iptal, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama, birim, sirket_id) "
        "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
        (sid, 3, 0, 5.0, 2.0, 0.0, 16000.0, 0.0, 20.0, 80000.0, None, "Adet", 1))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_pos():
    """C — POS: örnek terminal + varsayılan perakende müşteri + 3 demo satış.

    Demo satışlar `pos.pos_satis_olustur` çekirdeğiyle üretilir (rota ile aynı kod yolu) →
    fatura/cari/stok/kasa-banka/yevmiye tutarlılığı yapısal olarak garanti edilir
    (yetim fiş/hareket oluşmaz). Idempotent: mevcut kayıtları bozmaz, yalnız eksikleri tamamlar.
    """
    conn = get_conn()
    # 1) Varsayılan perakende müşteri
    if not conn.execute("SELECT id FROM cari_kart WHERE unvan='Peşin (Perakende) Müşteri' "
                        "AND sirket_id=1").fetchone():
        conn.execute("INSERT INTO cari_kart(kod, unvan, tip, telefon, sirket_id) "
                     "VALUES('PER-001','Peşin (Perakende) Müşteri','Musteri','',1)")
    # 2) Örnek terminal
    if conn.execute("SELECT COUNT(*) AS c FROM pos_terminal").fetchone()["c"] == 0:
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO pos_terminal(id, ad, kasa_id, banka_id, depo_id, komisyon_orani, "
            "max_taksit, aktif, sirket_id) VALUES(?,?,?,?,?,?,?,?,?)",
            (1, 'Mağaza POS 1', 1, 1, 2, 1.79, 12, 1, 1))
        conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # 3) Demo satışlar (yalnızca hiç POS satışı yokken; fatura/kasa/banka seed'inden sonra çağrılır)
    if conn.execute("SELECT COUNT(*) AS c FROM pos_satis").fetchone()["c"] == 0:
        try:
            import pos as pos_mod  # lazy import: db <-> pos döngüsünü önler
            req = pos_mod._BasitReq(user_id=1, sirket_id=1)
            vade_15 = (datetime.date.today() + datetime.timedelta(days=15)).isoformat()
            demolar = [
                # (stok_id, miktar, birim_fiyat, [(tip, tutar, vade)...], fatura_vadesi)
                (1, 1, 17999.0, [("Nakit", 10000.0, ""), ("Kart", 11598.80, "")], ""),
                (3, 1, 19499.0, [("Havale", 23398.80, "")], ""),
                (4, 1, 18499.0, [("Nakit", 5000.0, "")], vade_15),
            ]
            for stok_id, mik, fiyat, odemeler, fvade in demolar:
                satirlar = [{"stok_id": stok_id, "varyant_id": 0, "miktar": mik,
                             "birim_fiyat": fiyat, "iskonto_orani": 0.0, "kdv_orani": 20.0,
                             "manuel_ad": ""}]
                od = [{"tip": t, "tutar": tut, "vade": v} for (t, tut, v) in odemeler]
                _fid, hata = pos_mod.pos_satis_olustur(
                    conn, req, 1, None, satirlar, od, taksit=1, vade=fvade or None)
                if hata:
                    print(f"[seed_pos] demo satış atlandı: {hata}")
            conn.commit()
        except Exception as e:  # noqa: BLE001
            print(f"[seed_pos] demo satış üretilemedi: {e}")
            conn.rollback()
    conn.close()


def seed_bakim():
    """D — Bakım Sözleşmesi: hizmet stok kartı + örnek sözleşmeler (cihazlı). Idempotent."""
    conn = get_conn()
    # 1) Bakım hizmeti stok kalemi (periyodik fatura kalemi)
    if not conn.execute("SELECT 1 FROM stok_kart WHERE kod='HZM-BKM-SOZL' AND sirket_id=1").fetchone():
        conn.execute("PRAGMA foreign_keys = OFF")
        conn.execute(
            "INSERT INTO stok_kart(kod, ad, birim, tip, kdv_orani, satis_fiyat, aktif, sirket_id) "
            "VALUES('HZM-BKM-SOZL','Bakım Sözleşmesi Hizmeti','Hizmet','Hizmet',20,0,1,1)")
        conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()

    # 2) Örnek sözleşmeler (yalnızca hiç yoksa)
    if conn.execute("SELECT COUNT(*) c FROM bakim_sozlesme").fetchone()["c"] == 0:
        bugun = datetime.date.today()
        stok_id = {r["kod"]: r["id"] for r in conn.execute(
            "SELECT id, kod FROM stok_kart WHERE sirket_id=1").fetchall()}
        cari_id = {r["kod"]: r["id"] for r in conn.execute(
            "SELECT id, kod FROM cari_kart WHERE sirket_id=1").fetchall()}
        demolar = [
            # (no, cari_kod, baslangic, bitis, periyot, bedel, [(stok_kod, seri, aciklama)])
            ("BKM-2026-001", "BAT-001",
             (bugun - datetime.timedelta(days=335)).isoformat(),
             (bugun + datetime.timedelta(days=15)).isoformat(),
             "Aylik", 1500.0,
             [("TV-43-SAM-001", "SN-BKM-1001", "Mağaza içi 43\" TV (teşhir)")]),
            ("BKM-2026-002", "DIY-001",
             (bugun - datetime.timedelta(days=90)).isoformat(),
             (bugun + datetime.timedelta(days=275)).isoformat(),
             "Yillik", 9600.0,
             [("CM-9KG-ARC-004", "SN-BKM-2002", "Çamaşır makinesi"),
              ("BUZ-510-VST-003", "SN-BKM-2003", "Buzdolabı")]),
        ]
        for no, ckod, bas, bit, per, bedel, cihazlar in demolar:
            if ckod not in cari_id:
                continue
            cur = conn.execute(
                "INSERT INTO bakim_sozlesme(sozlesme_no, cari_id, baslangic, bitis, periyot, "
                "bedel, para_birimi, durum, aciklama, sirket_id) "
                "VALUES(?,?,?,?,?,?,'TRY','Aktif',?,1)",
                (no, cari_id[ckod], bas, bit, per, bedel,
                 f"{ckod} periyodik bakım sözleşmesi"))
            sid = cur.lastrowid
            for skod, seri, acik in cihazlar:
                conn.execute(
                    "INSERT INTO bakim_sozlesme_cihaz(sozlesme_id, stok_id, seri_no, "
                    "cihaz_aciklama, sirket_id) VALUES(?,?,?,?,1)",
                    (sid, stok_id.get(skod), seri, acik))
        conn.commit()
    conn.close()


def seed_crm():
    """E — CRM: örnek aktivite/görev kayıtları (hatırlatmalı ve hatırlatmasız). Idempotent."""
    conn = get_conn()
    if conn.execute("SELECT COUNT(*) c FROM crm_aktivite").fetchone()["c"] > 0:
        conn.close()
        return
    bugun = datetime.date.today()
    cari = {r["kod"]: r["id"] for r in conn.execute(
        "SELECT id, kod FROM cari_kart WHERE sirket_id=1").fetchall()}
    kul = {r["kullanici_adi"]: r["id"] for r in conn.execute(
        "SELECT id, kullanici_adi FROM kullanici").fetchall()}
    demolar = [
        # (no, tip, baslik, aciklama, cari_kod, sorumlu, tarih, hatirlatma, durum, oncelik)
        ("AKT-2026-001", "Arama", "Tahsilat görüşmesi",
         "Açık bakiyenin kapatılması için arayınız.", "BAT-001", "admin",
         (bugun + datetime.timedelta(days=1)).isoformat(),
         (bugun + datetime.timedelta(days=1)).isoformat(), "Planlandı", "Yuksek"),
        ("AKT-2026-002", "Toplanti", "Yeni dönem teklif sunumu",
         "2026 son çeyrek bakım sözleşmesi yenileme görüşmesi.", "DIY-001", "admin",
         (bugun + datetime.timedelta(days=3)).isoformat(),
         (bugun + datetime.timedelta(days=2)).isoformat(), "Planlandı", "Normal"),
        ("AKT-2026-003", "Takip", "Geçen toplantı aksiyonları",
         "Sözleşme taslağının müşteriyle paylaşılması takibi.", "BAT-001", "servis",
         bugun.isoformat(), None, "Planlandı", "Dusuk"),
        ("AKT-2026-004", "Gorev", "Demo cihaz kurulumu",
         "Teşhir mağazası için demo cihaz kurulum ve devreye alma.", "BAT-001", "servis",
         (bugun + datetime.timedelta(days=5)).isoformat(),
         (bugun + datetime.timedelta(days=5)).isoformat(), "Planlandı", "Normal"),
        ("AKT-2026-005", "Arama", "Memnuniyet araması",
         "Geçen ay teslim edilen ürünler için memnuniyet kontrolü.", "DIY-001", "admin",
         (bugun - datetime.timedelta(days=2)).isoformat(), None, "Tamamlandı", "Dusuk"),
    ]
    for no, tip, baslik, acik, ckod, sorumlu, tarih, hat, durum, oncelik in demolar:
        conn.execute(
            "INSERT INTO crm_aktivite(aktivite_no, tip, baslik, aciklama, cari_id, "
            "sorumlu_id, tarih, saat, hatirlatma_tarihi, hatirlatildi, durum, oncelik, "
            "created_by, sirket_id) VALUES(?,?,?,?,?,?,?,?,?,0,?,?,?,1)",
            (no, tip, baslik, acik, cari.get(ckod), kul.get(sorumlu), tarih,
             "10:00", hat, durum, oncelik, kul.get("admin") or 1))
    conn.commit()
    conn.close()


def seed_irsaliye():
    """Örnek veriler (seed_irsaliye)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM irsaliye").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # irsaliye
    conn.execute("INSERT INTO irsaliye(id, irsaliye_no, tip, cari_id, sube_id, depo_id, hedef_depo_id, kaynak_siparis_id, tarih, durum, para_birimi, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (1, 'IRS-2026-001', 'Satis', 1, None, 1, None, 1, '2026-09-06', 'Onaylandı', 'TRY', 17999.0, 0.0, 3599.8, 21598.8, 'Sipariş sevkiyatı'))
    conn.execute("INSERT INTO irsaliye(id, irsaliye_no, tip, cari_id, sube_id, depo_id, hedef_depo_id, kaynak_siparis_id, tarih, durum, para_birimi, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (2, 'IRA-2026-001', 'Alis', 5, None, 1, None, 3, '2026-09-06', 'Onaylandı', 'TRY', 86000.0, 0.0, 17200.0, 103200.0, 'Vestel mal kabul'))
    conn.execute("INSERT INTO irsaliye(id, irsaliye_no, tip, cari_id, sube_id, depo_id, hedef_depo_id, kaynak_siparis_id, tarih, durum, para_birimi, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (3, 'IRS-2026-002', 'Satis', 1, None, 1, None, None, '2026-09-07', 'Onaylandı', 'TRY', 17999.0, 0.0, 3599.8, 21598.8, 'Standalone sevk (faturası henüz kesilmedi)'))
    # irsaliye_kalem
    conn.execute("INSERT INTO irsaliye_kalem(id, irsaliye_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 1, 1, 0, 1.0, 17999.0, 0.0, 20.0, 17999.0, None))
    conn.execute("INSERT INTO irsaliye_kalem(id, irsaliye_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 2, 2, 0, 2.0, 28000.0, 0.0, 20.0, 56000.0, None))
    conn.execute("INSERT INTO irsaliye_kalem(id, irsaliye_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (3, 2, 4, 0, 2.0, 15000.0, 0.0, 20.0, 30000.0, None))
    conn.execute("INSERT INTO irsaliye_kalem(id, irsaliye_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (4, 3, 1, 0, 1.0, 17999.0, 0.0, 20.0, 17999.0, None))
    # F1 — mali etki (cari hareket) onaylı irsaliyede oluşur; yevmiye fişleri
    # seed_muhasebe → toplu_uret tarafından geriye dönük üretilir (kaynaklı faturalar atlanır).
    conn.execute("INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, borc, alacak, para_birimi, doviz_kur, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (1, '2026-09-06', None, 'Satış İrsaliyesi', 'IRS-2026-001', 'Sipariş sevkiyatı', 21598.8, 0.0, 'TRY', 1.0, 'Irsaliye', 1))
    conn.execute("INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, borc, alacak, para_birimi, doviz_kur, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (5, '2026-09-06', None, 'Alış İrsaliyesi', 'IRA-2026-001', 'Vestel mal kabul', 0.0, 103200.0, 'TRY', 1.0, 'Irsaliye', 2))
    conn.execute("INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, borc, alacak, para_birimi, doviz_kur, ilgili_modul, ilgili_kayit_id) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)", (1, '2026-09-07', None, 'Satış İrsaliyesi', 'IRS-2026-002', 'Standalone sevk (faturası henüz kesilmedi)', 21598.8, 0.0, 'TRY', 1.0, 'Irsaliye', 3))
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_fatura():
    """Fatura modülü (Faz 2) için örnek veriler (onaylı; K2 cari hareketleriyle)."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM fatura").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # fatura
    conn.execute("INSERT INTO fatura(id, fatura_no, tip, cari_id, sube_id, kaynak_irsaliye_id, tarih, vade, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (1, 'SF-2026-001', 'Satis', 1, None, 1, '2026-09-06', '2026-10-06', 'Onaylandı', 'TRY', 1.0, 17999.0, 0.0, 3599.8, 21598.8, 'IRS-2026-001 karşılığı'))
    conn.execute("INSERT INTO fatura(id, fatura_no, tip, cari_id, sube_id, kaynak_irsaliye_id, tarih, vade, durum, para_birimi, doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)", (2, 'AF-2026-001', 'Alis', 5, None, 2, '2026-09-06', '2026-10-06', 'Onaylandı', 'TRY', 1.0, 86000.0, 0.0, 17200.0, 103200.0, 'IRA-2026-001 karşılığı'))
    # fatura_kalem
    conn.execute("INSERT INTO fatura_kalem(id, fatura_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (1, 1, 1, 0, 1.0, 17999.0, 0.0, 20.0, 17999.0, None))
    conn.execute("INSERT INTO fatura_kalem(id, fatura_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (2, 2, 2, 0, 2.0, 28000.0, 0.0, 20.0, 56000.0, None))
    conn.execute("INSERT INTO fatura_kalem(id, fatura_id, stok_id, varyant_id, miktar, birim_fiyat, iskonto_orani, kdv_orani, tutar, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?)", (3, 2, 4, 0, 2.0, 15000.0, 0.0, 20.0, 30000.0, None))
    # F1 — kaynak irsaliyesi olan faturalar yalnızca belgeleştirir; cari hareket burada
    # YAZILMAZ (mali etki seed_irsaliye'de onaylı irsaliyelere işlendi — çifte kayıt yok).
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_cek_senet():
    """Çek/Senet modülü (Faz 2) için örnek veriler."""
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM cek_senet").fetchone()["c"]
    if n > 0:
        conn.close()
        return
    conn.execute("PRAGMA foreign_keys = OFF")
    # cek_senet
    conn.execute("INSERT INTO cek_senet(id, no, tip, tur, cari_id, sube_id, banka, sube_ad, tutar, keside_tarihi, vade, durum, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (4, 'CEK-001', 'Alinan', 'Cek', 1, None, 'Ziraat Bankası', None, 10000.0, '2026-08-01', '2026-09-25', 'Bekliyor', "Batman Çarşı Elektronik'ten alınan çek"))
    conn.execute("INSERT INTO cek_senet(id, no, tip, tur, cari_id, sube_id, banka, sube_ad, tutar, keside_tarihi, vade, durum, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (5, 'SNT-001', 'Alinan', 'Senet', 2, None, 'Garanti BBVA', None, 20000.0, '2026-08-20', '2026-09-09', 'Tahsile Verildi', "Dicle AVM'den alınan senet (bankada)"))
    conn.execute("INSERT INTO cek_senet(id, no, tip, tur, cari_id, sube_id, banka, sube_ad, tutar, keside_tarihi, vade, durum, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (6, 'CEK-002', 'Verilen', 'Cek', 5, None, 'Ziraat Bankası', None, 30000.0, '2026-09-01', '2026-09-25', 'Bekliyor', "Vestel Dist.'e verilen çek"))
    conn.execute("INSERT INTO cek_senet(id, no, tip, tur, cari_id, sube_id, banka, sube_ad, tutar, keside_tarihi, vade, durum, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (7, 'CEK-003', 'Alinan', 'Cek', 3, None, 'Ziraat Bankası', None, 12000.0, '2026-07-15', '2026-09-03', 'Karşılıksız', "Siirt Tekno'dan alınan çek (karşılıksız)"))
    conn.execute("INSERT INTO cek_senet(id, no, tip, tur, cari_id, sube_id, banka, sube_ad, tutar, keside_tarihi, vade, durum, aciklama) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)", (8, 'SNT-002', 'Alinan', 'Senet', 4, None, 'Garanti BBVA', None, 8500.0, '2026-08-05', '2026-09-05', 'Bekliyor', "Mardin Star'dan alınan senet (vadesi geçti)"))
    conn.execute("INSERT INTO cek_senet(no, tip, tur, cari_id, banka, tutar, keside_tarihi, vade, durum, aciklama, para_birimi, doviz_kur) "
                 "VALUES('CEK-004','Alinan','Cek',(SELECT id FROM cari_kart WHERE kod='BAT-001'),'İş Bankası',1000,'2026-09-02','2026-10-15','Bekliyor','USD çek (döviz takibi — K18)','USD',48.44)")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.commit()
    conn.close()


def seed_doviz():
    """Döviz Takip modülü (Faz 2 kapanışı) için örnek veriler.

    Kurlar + USD cinsinden bir fatura ve ona bağlı USD tahsilat (farklı kurdan)
    -> kur farkı ekranının ve kur farkı faturasının demosu.
    """
    conn = get_conn()
    n = conn.execute("SELECT COUNT(*) AS c FROM doviz_kur").fetchone()["c"]
    if n == 0:
        for pb, kur in (("USD", 48.44), ("EUR", 56.30), ("GBP", 65.55)):
            conn.execute(
                "INSERT INTO doviz_kur(para_birimi, kur, tarih, kaynak) "
                "VALUES(?,?,date('now','localtime'),'Manuel')", (pb, kur))

    # USD çek örneği (canlı DB'de seed_cek_senet no-op olduğundan burada tamamlanır)
    if not conn.execute("SELECT COUNT(*) k FROM cek_senet WHERE no='CEK-004'").fetchone()["k"]:
        conn.execute(
            "INSERT INTO cek_senet(no, tip, tur, cari_id, banka, tutar, keside_tarihi, vade, "
            "durum, aciklama, para_birimi, doviz_kur) "
            "VALUES('CEK-004','Alinan','Cek',(SELECT id FROM cari_kart WHERE kod='BAT-001'),"
            "'İş Bankası',1000,'2026-09-02','2026-10-15','Bekliyor',"
            "'USD çek (döviz takibi — K18)','USD',48.44)")

    nd = conn.execute("SELECT COUNT(*) AS c FROM fatura WHERE para_birimi!='TRY'").fetchone()["c"]
    if nd == 0:
        cari_row = conn.execute("SELECT id FROM cari_kart WHERE kod='BAT-001'").fetchone()
        stok_row = conn.execute("SELECT id FROM stok_kart WHERE aktif=1 LIMIT 1").fetchone()
        hesap_row = conn.execute("SELECT id FROM banka_hesap WHERE aktif=1 LIMIT 1").fetchone()
        if cari_row and stok_row and hesap_row:
            cid, sid, hid = cari_row["id"], stok_row["id"], hesap_row["id"]
            tarih, vade = "2026-09-07", "2026-10-07"
            kur0, kur1 = 48.44, 48.60          # fatura kuru vs tahsilat kuru
            ara, kdv, genel = 2000.0, 400.0, 2400.0
            cur = conn.execute(
                "INSERT INTO fatura(fatura_no, tip, cari_id, tarih, vade, durum, para_birimi, "
                "doviz_kur, ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) "
                "VALUES(?,?,?,?,?,'Onaylandı','USD',?,?,0,?,?,?)",
                ("SF-2026-002", "Satis", cid, tarih, vade, kur0, ara, kdv, genel,
                 "USD fatura — kur farkı demosu"))
            fid = cur.lastrowid
            conn.execute(
                "INSERT INTO fatura_kalem(fatura_id, stok_id, varyant_id, miktar, birim_fiyat, "
                "iskonto_orani, kdv_orani, tutar) VALUES(?,?,0,10,200,0,20,?)", (fid, sid, ara))
            cur = conn.execute(
                "INSERT INTO banka_hareket(banka_hesap_id, tarih, islem_tipi, tutar, cari_id, "
                "aciklama, belge_no, ilgili_modul, ilgili_kayit_id, para_birimi, doviz_kur) "
                "VALUES(?,?,'Havale/EFT Girişi',?,?,'USD tahsilat (farklı kur)','USD-TAHSIL',"
                "'Fatura',?,'USD',?)", (hid, tarih, genel, cid, fid, kur1))
            bhid = cur.lastrowid
            conn.execute(
                "INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, "
                "borc, alacak, para_birimi, doviz_kur, ilgili_modul, ilgili_kayit_id) "
                "VALUES(?,?,?,'Satış Faturası','SF-2026-002',?,?,0,'USD',?,'Fatura',?)",
                (cid, tarih, vade, "USD fatura — kur farkı demosu",
                 round(genel * kur0, 2), kur0, fid))
            conn.execute(
                "INSERT INTO cari_hareket(cari_id, tarih, belge_tipi, belge_no, aciklama, "
                "borc, alacak, para_birimi, doviz_kur, ilgili_modul, ilgili_kayit_id) "
                "VALUES(?,?,'Tahsilat','USD-TAHSIL','USD tahsilat (farklı kur)',0,?,'USD',?,'Banka',?)",
                (cid, tarih, round(genel * kur1, 2), kur1, bhid))

    conn.commit()
    conn.close()



def seed_servis():
    """Faz 3 — Servis & Garanti için örnek veriler (idempotent).

    - Satılan seri numaralarına garanti başlangıç/bitiş tarihi işlenir (24 ay varsayılan).
    - Farklı durumlarda servis kayıtları + kullanılan yedek parça örneği.
    """
    conn = get_conn()

    # Faz 3 — hizmet kalemi (servis işçiliği) için kategori + stok kart (idempotent).
    if not conn.execute("SELECT 1 FROM kategori WHERE ad='Hizmet'").fetchone():
        conn.execute("INSERT INTO kategori(ad, aktif) VALUES('Hizmet', 1)")
    if not conn.execute("SELECT 1 FROM stok_kart WHERE kod='HZM-SRV-ISCLK'").fetchone():
        kat = conn.execute("SELECT id FROM kategori WHERE ad='Hizmet'").fetchone()["id"]
        conn.execute(
            "INSERT INTO stok_kart(kod, ad, kategori_id, birim, kdv_orani, otv_orani, alis_fiyat, "
            "satis_fiyat, para_birimi, iskonto_orani, kritik_stok, seri_lot_takibi, varyant_takibi, "
            "aktif, tip) VALUES('HZM-SRV-ISCLK','Servis İşçilik (Hizmet)',?,'Saat',20.0,0.0,0.0,0.0,"
            "'TRY',0.0,0.0,0,0,1,'Hizmet')", (kat,))

    # Parça depo backfill (migrasyon öncesi kayıtlara Servis deposu ata — K11).
    servis_depo = conn.execute("SELECT id FROM depo WHERE tip='Servis' AND aktif=1 ORDER BY id LIMIT 1").fetchone()
    if servis_depo:
        conn.execute("UPDATE servis_parca SET depo_id=? WHERE depo_id IS NULL", (servis_depo["id"],))

    # Garanti: satılan serilere garanti tarihleri (yalnız eksikse).
    for r in conn.execute(
        "SELECT id FROM stok_seri WHERE durum='Satıldı' AND garanti_bitis IS NULL"
    ).fetchall():
        conn.execute(
            "UPDATE stok_seri SET garanti_baslangic='2026-06-01', garanti_bitis='2028-06-01' "
            "WHERE id=?", (r["id"],))

    n = conn.execute("SELECT COUNT(*) c FROM servis_kayit").fetchone()["c"]
    if n > 0:
        conn.commit()
        conn.close()
        return

    tek = conn.execute("SELECT id FROM kullanici WHERE rol='Servis' LIMIT 1").fetchone()
    tek_id = tek["id"] if tek else None

    kayitlar = [
        # no, cari_kod, cihaz, seri, ariza, aksesuar, gelis, durum, garanti, iscilik, aciklama
        ("SRV-2026-001", "BAT-001", 'Samsung 43" Crystal UHD 4K TV', "SAM43UHD00001",
         "Ekran kararması / açılmıyor", "Uzaktan kumanda, ayaklar", "2026-09-01",
         "Teslim Edildi", 1, 0, "Panel besleme kartı garanti kapsamında değiştirildi"),
        ("SRV-2026-002", "MSU-002", "Arçelik 9kg Çamaşır Makinesi", None,
         "Sıkma sırasında rulman sesi", None, "2026-09-03", "Tamir Ediliyor", 0, 450,
         "Kazan rulmanları ve kayış değişecek"),
        ("SRV-2026-003", "SRT-001", "Vestel 12000 BTU Inverter Klima", None,
         "Kompresör devreye girmiyor", "Uzaktan kumanda", "2026-09-05", "Alındı", 1, 0,
         "İlk teşhis bekleniyor"),
        ("SRV-2026-004", "BAT-001", 'Samsung 55" QLED 4K TV', "SAM55QLED0001",
         "Ekranda dikey çizgi", None, "2026-09-06", "Onay Bekliyor", 1, 0,
         "Panel değişimi için müşteri onayı bekleniyor"),
    ]
    for no, kod, cihaz, seri, ariza, aks, gelis, durum, gar, isc, acik in kayitlar:
        cari_row = conn.execute("SELECT id FROM cari_kart WHERE kod=?", (kod,)).fetchone()
        cur = conn.execute(
            "INSERT INTO servis_kayit(servis_no, cari_id, cihaz, seri_no, ariza, aksesuar, "
            "gelis_tarihi, teknisyen_id, durum, garanti_kapsami, iscilik_ucreti, aciklama) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",
            (no, cari_row["id"] if cari_row else None, cihaz, seri, ariza, aks, gelis,
             tek_id, durum, gar, isc, acik))
        if no == "SRV-2026-002":
            sid = cur.lastrowid
            depo_id = servis_depo["id"] if servis_depo else 3
            conn.execute(
                "INSERT INTO servis_parca(servis_id, stok_id, miktar, birim_fiyat, tutar, aciklama, depo_id) "
                "VALUES(?,?,?,?,?,?,?)", (sid, 7, 1, 240.0, 240.0, "Çamaşır makinesi kayışı", depo_id))

    conn.commit()
    conn.close()


def aktif_eb(conn, kaynak_kolon, kaynak_id):
    """K25 — kaynak belgenin iptalini engelleyen (GİB'e gönderilmiş/onaylanmış) e-belgeyi döndür.

    kaynak_kolon: 'kaynak_fatura_id' veya 'kaynak_irsaliye_id' (yalnızca bu ikisi).
    Dönüş: engelleyen e_belge satırı veya None.
    """
    if kaynak_kolon not in ("kaynak_fatura_id", "kaynak_irsaliye_id"):
        raise ValueError("geçersiz kaynak_kolon")
    return conn.execute(
        f"SELECT id, belge_no, tur, durum FROM e_belge "
        f"WHERE {kaynak_kolon}=? AND durum IN ('Gönderildi','Onaylandı') "
        "ORDER BY id LIMIT 1", (kaynak_id,)).fetchone()


def seed_edonusum():
    """Faz 4 — e-Dönüşüm için örnek veriler (idempotent).

    - e-Fatura mükellefi işaretleme (giden belge tipi otomatik belirleme için).
    - Entegratör meta ayarları (varsayılan: Mock sandbox).
    - e-Arşiv örneği için non-mükellef müşteriye (Siirt) onaylı satış faturası.
    - Giden e-belge örnekleri (e-Fatura onaylı, e-Arşiv onaylı, e-İrsaliye gönderildi).
    - Gelen kutusu örnekleri (mock entegratörden, dedup belge_no üzerinden).
    """
    import edonusum  # gelen kutusu aktarımı + XML üretimi (döngüsel import engellenir)

    conn = get_conn()

    # 1) e-Fatura mükellefiyeti
    for kod in ("BAT-001", "DIY-001"):
        conn.execute("UPDATE cari_kart SET e_fatura_mukellefi=1 WHERE kod=?", (kod,))

    # 2) entegratör meta ayarları
    conn.execute("INSERT OR IGNORE INTO meta(anahtar, deger) VALUES('entegrator_saglayici','Mock')")
    conn.execute("INSERT OR IGNORE INTO meta(anahtar, deger) VALUES('entegrator_api_anahtari','')")
    conn.execute("INSERT OR IGNORE INTO meta(anahtar, deger) VALUES('entegrator_test_modu','1')")

    # 3) e-Arşiv örneği için non-mükellef (Siirt) onaylı satış faturası
    if not conn.execute("SELECT 1 FROM fatura WHERE fatura_no='SF-2026-003'").fetchone():
        siirt = conn.execute("SELECT id FROM cari_kart WHERE kod='SRT-001'").fetchone()
        klima = conn.execute("SELECT id, satis_fiyat, kdv_orani FROM stok_kart WHERE kod='KLM-12000-VST-005'").fetchone()
        if siirt and klima:
            ara = round(float(klima["satis_fiyat"]), 2)
            kdv = round(ara * float(klima["kdv_orani"]) / 100, 2)
            genel = round(ara + kdv, 2)
            cur = conn.execute(
                "INSERT INTO fatura(fatura_no, tip, cari_id, tarih, vade, durum, para_birimi, doviz_kur, "
                "ara_toplam, iskonto_toplam, kdv_toplam, genel_toplam, aciklama) "
                "VALUES('SF-2026-003','Satis',?, '2026-09-05', '2026-10-05', 'Onaylandı','TRY',1,?,0,?,?,"
                "'Siirt Teknoloji Market — e-Arşiv örneği')",
                (siirt["id"], ara, kdv, genel))
            fid = cur.lastrowid
            conn.execute(
                "INSERT INTO fatura_kalem(fatura_id, stok_id, varyant_id, miktar, birim_fiyat, "
                "iskonto_orani, kdv_orani, tutar) VALUES(?,?,0,1,?,0,?,?)",
                (fid, klima["id"], klima["satis_fiyat"], klima["kdv_orani"], ara))
            conn.execute(
                "INSERT INTO cari_hareket(cari_id, tarih, vade, belge_tipi, belge_no, aciklama, "
                "borc, alacak, para_birimi, ilgili_modul, ilgili_kayit_id) "
                "VALUES(?, '2026-09-05','2026-10-05','Satış Faturası','SF-2026-003',"
                "'Siirt Teknoloji Market — e-Arşiv örneği',?,0,'TRY','Fatura',?)",
                (siirt["id"], genel, fid))

    # 4) giden e-belge örnekleri
    if conn.execute("SELECT COUNT(*) c FROM e_belge").fetchone()["c"] == 0:
        def _ekle(belge_no, tur, kaynak_tablo, kaynak_no):
            if kaynak_tablo == "fatura":
                f = conn.execute(
                    "SELECT f.*, c.vergi_no, c.unvan FROM fatura f JOIN cari_kart c ON c.id=f.cari_id "
                    "WHERE f.fatura_no=?", (kaynak_no,)).fetchone()
                if f:
                    conn.execute(
                        "INSERT INTO e_belge(belge_no, tur, kaynak_fatura_id, cari_id, alici_vkn, alici_unvan, senaryo) "
                        "VALUES(?,?,?,?,?,?, 'Temel')",
                        (belge_no, tur, f["id"], f["cari_id"], f["vergi_no"], f["unvan"]))
            else:
                i = conn.execute(
                    "SELECT ir.*, c.vergi_no, c.unvan FROM irsaliye ir JOIN cari_kart c ON c.id=ir.cari_id "
                    "WHERE ir.irsaliye_no=?", (kaynak_no,)).fetchone()
                if i:
                    conn.execute(
                        "INSERT INTO e_belge(belge_no, tur, kaynak_irsaliye_id, cari_id, alici_vkn, alici_unvan, senaryo) "
                        "VALUES(?,?,?,?,?,?, 'Temel')",
                        (belge_no, tur, i["id"], i["cari_id"], i["vergi_no"], i["unvan"]))

        _ekle("EF-2026-001", "EFatura", "fatura", "SF-2026-001")
        _ekle("EA-2026-001", "EArsiv", "fatura", "SF-2026-003")
        _ekle("EI-2026-001", "EIrsaliye", "irsaliye", "IRS-2026-001")
        conn.execute("UPDATE e_belge SET durum='Onaylandı', ettn='ETTN-2026-000001', gonderim_tarihi=datetime('now','localtime') WHERE belge_no='EF-2026-001'")
        conn.execute("UPDATE e_belge SET durum='Onaylandı', ettn='ETTN-2026-000002', gonderim_tarihi=datetime('now','localtime') WHERE belge_no='EA-2026-001'")
        conn.execute("UPDATE e_belge SET durum='Gönderildi', ettn='ETTN-2026-000003', gonderim_tarihi=datetime('now','localtime') WHERE belge_no='EI-2026-001'")

    conn.commit()
    conn.close()

    # 5) giden e-belgelerin ham XML'i (ek_dosya) + gelen kutusu (mock entegratör)
    conn2 = get_conn()
    for r in conn2.execute("SELECT id FROM e_belge").fetchall():
        edonusum._e_belge_xml_uret_yaz(conn2, r["id"])
    conn2.commit()
    conn2.close()
    ent = edonusum._entegrator()
    for b in ent.gelen_kutusu():
        edonusum._gelen_aktar(b)


HESAP_PLANI = [
    # (kod, ad, tip, ust_kod)
    ("100", "KASA", "Aktif", None),
    ("101", "ALINAN ÇEKLER", "Aktif", None),
    ("102", "BANKALAR", "Aktif", None),
    ("103", "VERİLEN ÇEKLER VE ÖDEME EMİRLERİ (-)", "Aktif", None),
    ("120", "ALICILAR", "Aktif", None),
    ("121", "ALACAK SENETLERİ", "Aktif", None),
    ("153", "TİCARİ MALLAR", "Aktif", None),
    ("191", "İNDİRİLECEK KDV", "Aktif", None),
    ("255", "DEMİRBAŞLAR", "Aktif", None),
    ("257", "BİRİKMİŞ AMORTİSMANLAR (-)", "Aktif", None),
    ("320", "SATICILAR", "Pasif", None),
    ("321", "BORÇ SENETLERİ", "Pasif", None),
    ("360", "ÖDENECEK VERGİ VE FONLAR", "Pasif", None),
    ("391", "HESAPLANAN KDV", "Pasif", None),
    ("500", "SERMAYE", "Ozkaynak", None),
    ("590", "DÖNEM NET KÂRI", "Ozkaynak", None),
    ("591", "DÖNEM NET ZARARI (-)", "Ozkaynak", None),
    ("600", "YURTİÇİ SATIŞLAR", "Gelir", None),
    ("602", "DİĞER GELİRLER", "Gelir", None),
    ("642", "FAİZ GELİRLERİ", "Gelir", None),
    ("646", "KAMBİYO KÂRLARI", "Gelir", None),
    ("679", "DİĞER OLAĞANDIŞI GELİR VE KÂRLAR", "Gelir", None),
    ("620", "SATILAN TİCARİ MALLAR MALİYETİ (-)", "Gider", None),
    ("632", "GENEL YÖNETİM GİDERLERİ (-)", "Gider", None),
    ("656", "KAMBİYO ZARARLARI (-)", "Gider", None),
    ("760", "PAZARLAMA SATIŞ DAĞITIM GİDERLERİ (-)", "Gider", None),
    ("770", "GENEL YÖNETİM GİDERLERİ (-)", "Gider", None),
]


def seed_muhasebe():
    """Faz 5 — Tekdüzen hesap planı + retroaktif otomatik fiş üretimi (idempotent)."""
    conn = get_conn()
    for kod, ad, tip, ust in HESAP_PLANI:
        conn.execute(
            "INSERT OR IGNORE INTO hesap(kod, ad, tip, ust_kod, aktif) VALUES(?,?,?,?,1)",
            (kod, ad, tip, ust))
    conn.commit()
    conn.close()
    import muhasebe  # lazy import: döngüyü önler (muhasebe -> db)
    conn2 = get_conn()
    muhasebe.toplu_uret(conn2)
    conn2.commit()
    conn2.close()


def sirket_seed(conn, yeni_id):
    """İstek 3 — yeni şirkete kendi Tekdüzen hesap planı + demirbaş kategorileri + varsayılan depo.

    Adım 5: /ayarlar/sirketler'de yeni şirket oluşturulunca çağrılır (plan §8.1). Aksi halde
    fatura/kasa/banka onay kancaları hesap_id bulamaz ve Genel Muhasebe yeni şirkette çalışmaz.
    Idempotent: aynı şirket için tekrar çağrılırsa eksik parçaları tamamlar, mevcudu bozmaz.
    """
    # 1) 27 hesaplık Tekdüzen Hesap Planı (hesap.kod composite UNIQUE(sirket_id,kod))
    if not conn.execute("SELECT 1 FROM hesap WHERE sirket_id=? LIMIT 1", (yeni_id,)).fetchone():
        for kod, ad, tip, ust in HESAP_PLANI:
            conn.execute(
                "INSERT INTO hesap(kod, ad, tip, ust_kod, aktif, sirket_id) VALUES(?,?,?,?,1,?)",
                (kod, ad, tip, ust, yeni_id))
    # 2) Demirbaş kategorileri (demirbaş kaydı kategori referansı bekler)
    if not conn.execute("SELECT 1 FROM demirbas_kategori WHERE sirket_id=? LIMIT 1",
                        (yeni_id,)).fetchone():
        for ad, omur, acik in (
            ("Bilgisayar & Ekipman", 4, "VUK: %25 — 4 yıl"),
            ("Mobilya & Demirbaş", 10, "VUK: %10 — 10 yıl"),
            ("Makine & Teçhizat", 10, "VUK: %10 — 10 yıl"),
            ("Taşıt", 5, "VUK: %20 — 5 yıl"),
            ("Diğer", 5, "VUK: %20 — 5 yıl"),
        ):
            conn.execute(
                "INSERT INTO demirbas_kategori(ad, omur_yil, aciklama, aktif, sirket_id) "
                "VALUES(?,?,?,1,?)", (ad, omur, acik, yeni_id))
    # 3) Varsayılan depo (stok/sipariş formları boş depo listesiyle açılmasın diye)
    if not conn.execute("SELECT 1 FROM depo WHERE sirket_id=? LIMIT 1", (yeni_id,)).fetchone():
        conn.execute(
            "INSERT INTO depo(kod, ad, tip, aktif, sube_id, sirket_id) "
            "VALUES('ANA','Ana Depo','Ana',1,NULL,?)", (yeni_id,))


def seed_finansal():
    """Faz 5 — Finansal Analiz: örnek bütçe hedefleri (idempotent)."""
    conn = get_conn()
    if conn.execute("SELECT COUNT(*) c FROM butce").fetchone()["c"] == 0:
        for yil, ay, tip, tutar, acik in (
            (2026, 9, "Gelir", 200000.0, "Eylül satış hedefi (örnek)"),
            (2026, 8, "Gelir", 150000.0, "Ağustos satış hedefi (örnek)"),
            (2026, 9, "Gider", 60000.0, "Eylül gider bütçesi (örnek)"),
            (2026, 8, "Gider", 55000.0, "Ağustos gider bütçesi (örnek)"),
        ):
            conn.execute(
                "INSERT INTO butce(yil, ay, tip, tutar, aciklama) VALUES(?,?,?,?,?)",
                (yil, ay, tip, tutar, acik))
    conn.commit()
    conn.close()
