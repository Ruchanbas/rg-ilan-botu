"""Telegram kanalı testleri: mesaj tonu, mükerrer engelleme, kuru mod,
ayar eksikse sessiz atlama."""
import os
from pathlib import Path
from unittest.mock import patch

from rgbot import telegram

ORNEK = [
    {"pdf_url": "https://ilan.gov.tr/1", "kurum": "X Üniversitesi",
     "durum": "KESIN", "birim": "FTR", "kadro": "ILN01",
     "son_basvuru": "11.08.2026"},
    {"pdf_url": "https://ilan.gov.tr/2", "kurum": "Y Üniversitesi",
     "durum": "SUPHELI", "birim": "Öğretim Elemanı (kontrol et)",
     "kadro": "ILN02", "son_basvuru": "12.08.2026"},
]


def _temiz(tmp_path):
    telegram._DURUM_DOSYASI = str(tmp_path / "gonderilen.json")


def test_ayar_eksikse_sessiz_atlar(tmp_path, monkeypatch):
    _temiz(tmp_path)
    monkeypatch.delenv("TELEGRAM_BOT_TOKEN", raising=False)
    monkeypatch.delenv("TELEGRAM_CHAT_IDS", raising=False)
    r = telegram.bildir(ORNEK, kuru_calisma=False)
    assert r["kanal_hazir"] is False and r["gonderilen"] == 0


def test_kuru_mod_gonderilmis_sayilir(tmp_path, monkeypatch):
    _temiz(tmp_path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "111")
    r = telegram.bildir(ORNEK, kuru_calisma=True)
    assert r["gonderilen"] == 2 and r["kanal_hazir"] is True


def test_mukerrer_engelleme(tmp_path, monkeypatch):
    _temiz(tmp_path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "111")
    telegram.bildir(ORNEK, kuru_calisma=True)
    r2 = telegram.bildir(ORNEK, kuru_calisma=True)
    assert r2["gonderilen"] == 0 and r2["atlanan"] == 2


def test_kesin_ve_supheli_ton_farkli():
    kesin = telegram._mesaj_olustur(ORNEK[0])
    supheli = telegram._mesaj_olustur(ORNEK[1])
    assert "araştırma görevlisi ilanı çıktı" in kesin
    assert "🍀" in kesin
    assert "kontrol et" in supheli  # şüpheli uyarısı
    assert "olabilecek" in supheli


def test_html_kacis():
    e = {"pdf_url": "x", "kurum": "A & B <test>", "durum": "KESIN",
         "birim": "-", "kadro": "-", "son_basvuru": "-"}
    m = telegram._mesaj_olustur(e)
    assert "&amp;" in m and "&lt;test&gt;" in m  # < > & kaçırıldı


def test_gonderim_basarisizsa_kayit_atilmaz(tmp_path, monkeypatch):
    _temiz(tmp_path)
    monkeypatch.setenv("TELEGRAM_BOT_TOKEN", "t")
    monkeypatch.setenv("TELEGRAM_CHAT_IDS", "111")

    class _Yanit:
        status_code = 500
        text = "hata"
    with patch.object(telegram.requests, "post", lambda *a, **k: _Yanit()):
        r = telegram.bildir(ORNEK, kuru_calisma=False)
    assert r["gonderilen"] == 0
    # Kayıt atılmadıysa 2. koşuda yeniden denenmeli
    with patch.object(telegram.requests, "post",
                      lambda *a, **k: type("R", (), {"status_code": 200})()):
        r2 = telegram.bildir(ORNEK, kuru_calisma=False)
    assert r2["gonderilen"] == 2
