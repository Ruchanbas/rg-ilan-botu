from datetime import date
from pathlib import Path

from rgbot.matcher import Filtreler, eslesir_mi, kesinlik
from rgbot.segment import segmentlere_bol
from rgbot.tarih import son_basvuru

FIXTURES = Path(__file__).parent / "fixtures"
KMU = (FIXTURES / "kmu_20260416.txt").read_text(encoding="utf-8")
POZITIF = (FIXTURES / "pozitif_sentetik.txt").read_text(encoding="utf-8")


# --- Tasarımın varlık sebebi: segmentasyon olmadan yanlış alarm kaçınılmaz ---

def test_segmentasyonsuz_yanlis_alarm_verirdi():
    """Belgenin tamamına bakılsaydı: arş.gör. ilan A'dan, fizyoterapi
    ilan B'den gelir ve YANLIŞ eşleşme doğardı. Bu test o tuzağın
    gerçekliğini kanıtlıyor."""
    assert eslesir_mi(KMU) is True  # tuzak gerçek


def test_segmentli_dogru_sonuc_sifir_eslesme():
    """Aynı belge segmentlere bölününce: A'da fizyoterapi yok, B'de
    arş.gör. yok -> 0 eşleşme. Ecem'e mesaj GİTMEZ. Doğru davranış."""
    sonuclar = [eslesir_mi(s) for s in segmentlere_bol(KMU)]
    assert sonuclar == [False, False]


# --- Pozitif yol ---

def test_pozitif_ilan_eslesir():
    segmentler = segmentlere_bol(POZITIF)
    assert len(segmentler) == 1
    assert eslesir_mi(segmentler[0]) is True


def test_pozitif_ilan_kesin():
    """FTR satırında pozisyon ve alan yan yana -> KESIN."""
    (segment,) = segmentlere_bol(POZITIF)
    assert kesinlik(segment) == "KESIN"


def test_pozitif_ilan_tuzak_satira_ragmen():
    """Aynı segmentte 'Fiziksel Tıp' tuzak satırı var; dışlama onu
    görmezden gelir ama gerçek FTR satırı eşleşmeyi korur."""
    (segment,) = segmentlere_bol(POZITIF)
    assert "Fiziksel Tıp" in segment
    assert eslesir_mi(segment) is True


def test_pozitif_son_basvuru_ilandan_okunur():
    (segment,) = segmentlere_bol(POZITIF)
    tarih, kesin = son_basvuru(segment, date(2026, 8, 3))
    assert tarih == date(2026, 8, 17)
    assert kesin is True


# --- Dışlama ve kapsama sınırları ---

TIP_ARS_GOR = """Örnek Üniversitesi Rektörlüğünden:
Tıp Fakültesi Dahili Tıp Bilimleri Fiziksel Tıp ve Rehabilitasyon
Anabilim Dalına Araştırma Görevlisi alınacaktır. Uzmanlık eğitimi
kapsamında değerlendirilecektir. ALES puanı aranmaz.
İlan olunur. 9999/1-1"""


def test_fiziksel_tip_ars_gor_eslesmez():
    """Tıp fakültesi FTR asistanlığı fizyoterapiste kapalı — mesaj gitmemeli."""
    assert eslesir_mi(TIP_ARS_GOR) is False


def test_fizik_tedavi_ve_rehabilitasyon_eslesir():
    """Alanın eski/alternatif adı kapsanıyor."""
    metin = ("Sağlık Bilimleri Enstitüsü Fizik Tedavi ve Rehabilitasyon "
             "Anabilim Dalı Araştırma Görevlisi 1 5 tezli yüksek lisans "
             "yapıyor olmak. İlan olunur. 8888/1-1")
    assert eslesir_mi(metin) is True


def test_ars_gor_kisaltmasi_eslesir():
    metin = ("Fizyoterapi ve Rehabilitasyon Bölümü Arş. Gör. kadrosu, "
             "1 adet, 5. derece. Detaylar üniversite sitesinde. "
             "İlan olunur. 7777/1-1")
    assert eslesir_mi(metin) is True


def test_sadece_pozisyon_eslesmez():
    """KMU segment A'nın minyatürü: arş.gör. var, alan yok."""
    metin = ("Sosyoloji Bölümü Araştırma Görevlisi alınacaktır. "
             "Yüksek lisans yapıyor olmak şarttır. " * 3)
    assert eslesir_mi(metin) is False


def test_sadece_alan_eslesmez():
    """KMU segment B'nin minyatürü: fizyoterapi var, arş.gör. yok."""
    metin = ("Fizyoterapi ve Rehabilitasyon Bölümü Doktor Öğretim Üyesi "
             "alınacaktır. Doktora yapmış olmak şarttır. " * 3)
    assert eslesir_mi(metin) is False


# --- Kesinlik derecelendirme ---

def test_uzak_terimler_supheli():
    """Arş.gör. kadrosu başka bölümün, fizyoterapi satırı öğretim
    üyesinin olduğu karma segment: gönderilir ama SUPHELI."""
    metin = ("Hemşirelik Bölümü Araştırma Görevlisi 1 5 tezli yüksek "
             "lisans yapıyor olmak. "
             + "Diğer kadrolara ilişkin genel şartlar aşağıdadır. " * 20
             + "Fizyoterapi ve Rehabilitasyon Bölümü Doktor Öğretim Üyesi "
               "1 3 doktora yapmış olmak. İlan olunur. 6666/1-1")
    assert kesinlik(metin) == "SUPHELI"


def test_eslesmeyende_kesinlik_none():
    assert kesinlik("Alakasız bir metin. " * 20) is None


# --- Filtre yükleme ---

def test_filtre_json_yukleme(tmp_path):
    yol = tmp_path / "filtre.json"
    yol.write_text(
        '{"pozisyon": ["Öğretim Görevlisi"], "alan": ["Fizyoterapi"], "disla": []}',
        encoding="utf-8")
    f = Filtreler.yukle(yol)
    # 1 sene sonraki senaryo: öğr.gör. filtresi tek JSON değişikliğiyle
    assert eslesir_mi(
        "Fizyoterapi programına Öğretim Görevlisi alınacaktır. " * 3, f) is True
    assert eslesir_mi(
        "Fizyoterapi programına Araştırma Görevlisi alınacaktır. " * 3, f) is False
