import json
from datetime import date
from pathlib import Path

from rgbot.ilanapi import ilan_url, metin_topla
from rgbot.matcher import Filtreler, kesinlik
from rgbot.toplayici import _son_basvuru_bul, aday_mi

ORNEK = json.loads(
    (Path(__file__).parent / "fixtures" / "ilanapi_ornekler.json")
    .read_text(encoding="utf-8"))
BUGUN = date(2026, 8, 2)


# --- Ön eleme: hangi ilanların detayı çekilir ---

def test_ihale_aday_degil():
    """Gerçek belediye ihalesi: akademik kurum değil, detayı çekilmez."""
    assert aday_mi(ORNEK["ihale_gercek"], 20, BUGUN) is False


def test_tebligat_aday_degil():
    """Gerçek mahkeme tebligatı (UYAP gürültüsünün temsilcisi)."""
    assert aday_mi(ORNEK["tebligat_gercek"], 20, BUGUN) is False


def test_universite_aday():
    assert aday_mi(ORNEK["akademik_sentetik"], 20, BUGUN) is True


def test_eski_ilan_aday_degil():
    eski = dict(ORNEK["akademik_sentetik"],
                publishStartDate="2026-05-01T00:00:00Z")
    assert aday_mi(eski, 20, BUGUN) is False


def test_arsivlenmis_aday_degil():
    ars = dict(ORNEK["akademik_sentetik"], isArchived=True)
    assert aday_mi(ars, 20, BUGUN) is False


# --- Detay metni toplama ve eşleştirme ---

def test_metin_topla_html_ayiklar():
    m = metin_topla(ORNEK["akademik_detay_sentetik"])
    assert "<p>" not in m and "<b>" not in m
    assert "Fizyoterapi" in m and "Araştırma" in m
    assert "personel@ornek.edu.tr" in m  # iç içe alanlar da toplanıyor


def test_akademik_detay_kesin_eslesir():
    metin = metin_topla(ORNEK["akademik_detay_sentetik"])
    assert kesinlik(metin) == "KESIN"


def test_tip_detay_eslesmez():
    """Fiziksel Tıp asistanlığı fizyoterapiste kapalı — mesaj gitmemeli."""
    metin = metin_topla(ORNEK["tip_detay_sentetik"])
    assert kesinlik(metin) is None


# --- Son başvuru ---

def test_son_basvuru_adtypefilters_dan():
    sb, kesin = _son_basvuru_bul(ORNEK["akademik_sentetik"], "",
                                 date(2026, 7, 30))
    assert sb == date(2026, 8, 14) and kesin is True


def test_son_basvuru_fallback_15_gun():
    sb, kesin = _son_basvuru_bul(ORNEK["ihale_gercek"], "içerikte tarih yok",
                                 date(2026, 7, 31))
    assert sb == date(2026, 8, 15) and kesin is False


# --- URL ---

def test_ilan_url_tam_adres():
    assert ilan_url(ORNEK["akademik_sentetik"]).startswith(
        "https://www.ilan.gov.tr/ilan/9999999/")


# --- Filtre dosyası arama terimleri ---

def test_filtre_arama_ham_kalir(tmp_path):
    yol = tmp_path / "f.json"
    yol.write_text('{"arama": ["Fizyoterapi", "Fizik Tedavi"]}',
                   encoding="utf-8")
    f = Filtreler.yukle(yol)
    assert f.arama == ["Fizyoterapi", "Fizik Tedavi"]  # normalize edilmedi
