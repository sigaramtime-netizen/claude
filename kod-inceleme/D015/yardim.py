# -*- coding: utf-8 -*-
"""D015-B — Yardım Merkezi (v1.46.0).

`GET /yardim`: 12 konu kartı + `?q` sunucu-taraflı filtre. İçerik `docs/`
özetleriyle tutarlı, her kart ilgili ekrana bağlanır.
"""
from core import route, render_template

KONULAR = [
    {"ikon": "📦", "baslik": "Stok Kartı Açma",
     "ozet": "Ürün/hizmet kartı, barkod, KDV ve fiyat tanımlama.",
     "adimlar": ["Stok → Yeni Stok Kartı", "Kod + ad + birim girin", "＋ Kategori/＋ Birim ile yerinde tanım ekleyin"],
     "url": "/stok/yeni", "kaynak": ""},
    {"ikon": "👥", "baslik": "Cari Hesap Açma",
     "ozet": "Müşteri/tedarikçi kartı, grup, kredi limiti ve para birimi.",
     "adimlar": ["Cari → Yeni Cari", "Tipi seçin (Müşteri/Tedarikçi/HerIkisi)", "＋ Grup ile yerinde grup ekleyin"],
     "url": "/cari/yeni", "kaynak": ""},
    {"ikon": "🧾", "baslik": "Satış Faturası Kesme",
     "ozet": "Siparişten irsaliyeye, irsaliyeden faturaya satış zinciri.",
     "adimlar": ["Sipariş → İrsaliye → Fatura akışını izleyin", "Satır/belge KDV modunu seçin", "Onaylayın: cari + stok + yevmiye otomatik"],
     "url": "/fatura/yeni?tip=Satis", "kaynak": ""},
    {"ikon": "💰", "baslik": "Tahsilat / Ödeme",
     "ozet": "Müşteriden tahsilat, tedarikçiye ödeme (Nakit/Kart/Havale/Çek).",
     "adimlar": ["Cari kart → 💰 Tahsilat / 💸 Ödeme", "Satırları bölüştürün, kuru sabitleyin", "Makbuzu yazdırın"],
     "url": "/cari", "kaynak": ""},
    {"ikon": "🏪", "baslik": "POS Hızlı Satış",
     "ozet": "Barkodla sepete ekleme, bölünebilir ödeme, otomatik fatura.",
     "adimlar": ["Terminal seçin", "Barkod okutun / arayın", "Ödemeyi bölüştürüp tamamlayın"],
     "url": "/pos", "kaynak": ""},
    {"ikon": "🔧", "baslik": "Servis Kaydı",
     "ozet": "Cihaz kabul, arıza/aksesuar, parça ve işçilik, fiş çıktısı.",
     "adimlar": ["Servis → Yeni Kayıt", "Parça + işçilik girin", "Fişi yazdırıp teslim edin"],
     "url": "/servis/yeni", "kaynak": ""},
    {"ikon": "🏦", "baslik": "Kasa / Banka / Çek-Senet",
     "ozet": "Nakit ve havale hareketleri, çek/senet portföyü ve fişler.",
     "adimlar": ["Kasa/Banka → Hareket", "Cari seçerseniz cari otomatik işler", "Fişi yazdırın"],
     "url": "/kasa", "kaynak": ""},
    {"ikon": "📥", "baslik": "Toplu İçe Aktarma",
     "ozet": "Stok/Cari/Kategori/Birim/Marka CSV aktarımı (şablon → önizleme → onay).",
     "adimlar": ["Listeden ⬇ Şablon indirin", "📥 İçe Aktar ile yükleyip önizleyin", "✅ Onayla: mevcutlar atlanır"],
     "url": "/stok/ice-aktar", "kaynak": ""},
    {"ikon": "📊", "baslik": "Raporlar & Kartoteks",
     "ozet": "Stok/cari kartoteks, finansal analiz, beyanname hazırlık.",
     "adimlar": ["Kartoteks → Stok/Cari", "Finansal → oran ve grafikler", "Çıktıları yazdırın"],
     "url": "/kartoteks/stok", "kaynak": "F5a-finansal-analiz-ozet.md"},
    {"ikon": "🏷️", "baslik": "Demirbaş & Amortisman",
     "ozet": "Sabit kıymet kaydı, VUK amortisman cetveli, zimmet.",
     "adimlar": ["Demirbaş → kart açın", "Amortisman üretin", "Cetveli yazdırın"],
     "url": "/demirbas", "kaynak": "F5b-demirbas-ozet.md"},
    {"ikon": "🗂️", "baslik": "Tanımlar (Kategori/Birim/Döviz/Grup/Marka)",
     "ozet": "Tanım ekleme, düzeltme ve pasifleştirme (silme yok).",
     "adimlar": ["Ayarlar → Tanımlar", "Düzenle ile yazım hatası düzeltin", "Kullanılanı silmeyin, pasifleştirin"],
     "url": "/ayarlar/tanimlar", "kaynak": "D007-kullanici-bildirimleri-ozet.md"},
    {"ikon": "💾", "baslik": "Yedekleme & Güvenlik",
     "ozet": "Uygulama içi yedek alma, geri yükleme ve sistem bilgisi.",
     "adimlar": ["Ayarlar → Yedekler → Yedek Al", "Geri yüklemeden önce otomatik güvenlik yedeği alınır", "Sistem Bilgisi'nden sağlığı izleyin"],
     "url": "/sistem/bilgi", "kaynak": "FINAL-KABUL-PROD-CHECKLIST.md"},
]


@route(r"/yardim", roles=())
def yardim_merkezi(req):
    q = (req.q("q") or "").strip().lower()
    if q:
        konular = [k for k in KONULAR
                   if q in k["baslik"].lower() or q in k["ozet"].lower()
                   or any(q in a.lower() for a in k["adimlar"])]
    else:
        konular = KONULAR
    return render_template("yardim/merkez.html", konular=konular, q=req.q("q") or "",
                           toplam=len(KONULAR))


def register():
    pass
