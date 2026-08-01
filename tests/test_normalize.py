from rgbot.normalize import norm


def test_turkce_buyuk_i():
    # Python'un ham lower()'ı burada "i̇" (i + birleşik nokta) üretir ve eşleşme ölür
    assert norm("FİZYOTERAPİ") == "fizyoterapi"
    assert norm("ARAŞTIRMA GÖREVLİSİ") == "arastirma gorevlisi"


def test_noktasiz_buyuk_i():
    assert norm("ILAN") == "ilan"          # I -> ı -> i
    assert norm("KADIN") == "kadin"


def test_satir_kirilmasi():
    # PDF tablolarında hücreler böyle kırılıyor — bire bir gerçek örnek
    assert norm("Araştırma\nGörevlisi") == "arastirma gorevlisi"
    assert norm("Fizyoterapi ve \nRehabilitasyon") == "fizyoterapi ve rehabilitasyon"


def test_kisaltma():
    assert norm("Arş. Gör.") == "ars. gor."
    assert norm("Arş.Gör.") == "ars.gor."


def test_sapkali():
    assert norm("zekâ") == "zeka"


def test_coklu_bosluk_tab_nbsp():
    assert norm("a\t b\u00a0 c") == "a b c"
