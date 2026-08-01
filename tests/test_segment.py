from pathlib import Path

from rgbot.segment import ILAN_KODU, segmentlere_bol

FIXTURES = Path(__file__).parent / "fixtures"
KMU = (FIXTURES / "kmu_20260416.txt").read_text(encoding="utf-8")


def test_kmu_iki_segment():
    """Doğrulanmış gerçek belge: tek PDF, iki bağımsız ilan."""
    segmentler = segmentlere_bol(KMU)
    assert len(segmentler) == 2


def test_segment_sinirlari_dogru():
    a, b = segmentlere_bol(KMU)
    # A: araştırma görevlisi ilanı, kendi koduyla bitiyor
    assert a.rstrip().endswith("3795/1-1")
    assert "Sosyoloji" in a and "Fizyoterapi" not in a
    # B: öğretim üyesi ilanı, kendi koduyla bitiyor, fizyoterapi satırları burada
    assert b.rstrip().endswith("3796/1-1")
    assert "Geriatrik Fizyoterapi" in b
    assert b.lstrip().startswith("Karamanoğlu")


def test_kod_regexi_yanlis_yakalamiyor():
    """Tarih, saat, kadro sütunu, madde numarası ilan kodu DEĞİLDİR."""
    for metin in ["16.04.2026", "17:00", "1 5", "70 65 EA",
                  "Ek-38", "48 inci maddesi", "%30", "2547 sayılı"]:
        assert ILAN_KODU.search(metin) is None, metin


def test_kod_regexi_gercek_kodlari_yakaliyor():
    for kod in ["3795/1-1", "3796/1-1", "12345/2-1", "451/1-1"]:
        assert ILAN_KODU.search(kod), kod


def test_kodsuz_kuyruk_kaybolmaz():
    metin = "X" * 150 + " 3795/1-1 " + "Kodsuz ama uzun bir ilan metni. " * 10
    segmentler = segmentlere_bol(metin)
    assert len(segmentler) == 2
    assert "Kodsuz" in segmentler[1]
