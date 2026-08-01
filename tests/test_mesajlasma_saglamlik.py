"""Mesajlaşma sağlamlığı: gönderim onaylanmadan 'gönderildi' sayılmamalı.

Üç kusurun regresyonunu engeller: (1) SSM boşsa sessizce gönderilmiş
sayma, (2) WhatsApp hata dönerse DynamoDB'ye yazıp tekrar denemeyi
engelleme, (3) hatırlatmayı onaysız işaretleme.
"""
from unittest.mock import patch

from rgbot import handler, durum, whatsapp

PAYLOAD = {
    "tarih": "2026-08-02", "sayfa_bulundu": True, "pdf_sayisi": 17,
    "eslesmeler": [{
        "pdf_url": "https://x/1.pdf", "kurum": "ÖRNEK ÜNİV", "durum": "KESIN",
        "birim": "FTR", "kadro": "ILN01", "son_basvuru": "2026-08-14",
        "kesin_tarih_mi": True}]}


class _Yanit:
    def __init__(self, kod, metin="x"):
        self.status_code = kod
        self.text = metin


def _kos(ayarlar, post_fn):
    kayitlar = []
    with patch.object(handler, "_KURU", False), \
         patch.object(whatsapp, "_ayarlar", lambda: ayarlar), \
         patch.object(whatsapp.requests, "post", post_fn), \
         patch.object(durum, "gorulmus_mu", lambda u: False), \
         patch.object(durum, "kaydet", lambda *a, **k: kayitlar.append(a[0])), \
         patch.object(handler, "_metrik", lambda a, d: None):
        r = handler.bildirim_handler(PAYLOAD)
    return r, kayitlar


def test_ssm_bos_kayit_atilmaz():
    r, kayitlar = _kos({"token": "", "phone_id": "", "alicilar": []},
                       lambda *a, **k: _Yanit(200))
    assert r["gonderilen"] == 0 and kayitlar == []


def test_whatsapp_hatasi_kayit_atilmaz():
    r, kayitlar = _kos({"token": "T", "phone_id": "P", "alicilar": ["905"]},
                       lambda *a, **k: _Yanit(500, "sunucu hatasi"))
    assert r["gonderilen"] == 0 and kayitlar == []


def test_basarili_gonderim_kaydedilir():
    r, kayitlar = _kos({"token": "T", "phone_id": "P", "alicilar": ["905"]},
                       lambda *a, **k: _Yanit(200))
    assert r["gonderilen"] == 1 and len(kayitlar) == 1


def test_kuru_mod_kaydeder():
    """Kuru mod test/gözlem için başarı sayılır, kayıt oluşur."""
    kayitlar = []
    with patch.object(handler, "_KURU", True), \
         patch.object(durum, "gorulmus_mu", lambda u: False), \
         patch.object(durum, "kaydet", lambda *a, **k: kayitlar.append(a[0])), \
         patch.object(handler, "_metrik", lambda a, d: None):
        r = handler.bildirim_handler(PAYLOAD)
    assert r["gonderilen"] == 1 and len(kayitlar) == 1
