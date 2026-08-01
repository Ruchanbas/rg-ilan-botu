"""Geriye dönük tarama (lokal CLI).

Amaç: sistemi canlıya almadan önce gerçek veriyle üç soruyu cevaplamak —
1. FTR araştırma görevlisi ilanı gerçekte hangi sıklıkta çıkıyor?
2. Filtre kaç yanlış alarm veriyor?
3. Regression testleri için gerçek pozitif örnekler hangileri?

Kullanım:
    python -m rgbot.backfill --baslangic 2025-08-01 --bitis 2026-08-01 \\
        --cikti tarama/

Çıktılar (cikti/ altında):
    pdf/                 indirilen tüm PDF'ler (yeniden çalıştırmada atlanır)
    rapor.csv            her PDF için 1 satır: tarih, kurum, durum
    eslesmeler.jsonl     eşleşen segmentler + satır detayları

Nazik tarama: istekler arası 1 sn bekler. ~250 iş günü * ~10 PDF birkaç
saat sürer; kesip tekrar başlatılabilir, kaldığı yerden devam eder.
"""

from __future__ import annotations

import argparse
import csv
import json
import time
from datetime import date, timedelta
from pathlib import Path

import requests

from . import fetcher
from .fetcher import cesitli_ilanlar_url, indir, pdf_linkleri
from .matcher import Filtreler, kesinlik
from .pdftext import metin_cikar, satir_detay
from .segment import segmentlere_bol
from .tarih import son_basvuru

_BEKLE = 1.0  # saniye / istek


def tara(baslangic: date, bitis: date, cikti: Path,
         filtreler: Filtreler | None = None) -> None:
    f = filtreler or Filtreler.yukle()
    pdf_klasor = cikti / "pdf"
    pdf_klasor.mkdir(parents=True, exist_ok=True)
    rapor_yolu = cikti / "rapor.csv"
    esles_yolu = cikti / "eslesmeler.jsonl"

    yeni_rapor = not rapor_yolu.exists()
    session = fetcher.yeni_oturum()

    with open(rapor_yolu, "a", newline="", encoding="utf-8") as rf, \
         open(esles_yolu, "a", encoding="utf-8") as ef:
        rapor = csv.writer(rf)
        if yeni_rapor:
            rapor.writerow(["tarih", "kurum", "pdf_url", "durum",
                            "son_basvuru", "kesin_tarih_mi"])

        gun = baslangic
        while gun <= bitis:
            try:
                _gun_isle(gun, session, f, pdf_klasor, rapor, ef)
            except Exception as e:
                # Tek bir günün ağ/SSL hatası tüm taramayı öldürmesin.
                # Rapora yaz, oturumu tazele, bir sonraki güne geç.
                print(f"{gun}  GUN_HATASI: {e}")
                rapor.writerow([gun, "", "", f"GUN_HATASI:{e}", "", ""])
                rf.flush()
                session = fetcher.yeni_oturum()
                time.sleep(5)
            gun += timedelta(days=1)


def _gun_isle(gun, session, f, pdf_klasor, rapor, ef):
    url = cesitli_ilanlar_url(gun, session)
    time.sleep(_BEKLE)
    if url is None:
        print(f"{gun}  sayı yok / ilan bölümü yok")
        return

    linkler = pdf_linkleri(url, session)
    time.sleep(_BEKLE)
    print(f"{gun}  {len(linkler)} PDF")

    for kurum, pdf_url in linkler:
        hedef = pdf_klasor / pdf_url.rsplit("/", 1)[-1]
        if not hedef.exists():
            try:
                indir(pdf_url, hedef, session)
            except Exception as e:  # tek PDF taramayı durdurmasın
                rapor.writerow([gun, kurum, pdf_url, f"INDIRME_HATASI:{e}", "", ""])
                continue
            time.sleep(_BEKLE)

        try:
            metin = metin_cikar(hedef)
        except Exception as e:
            rapor.writerow([gun, kurum, pdf_url, f"PDF_HATASI:{e}", "", ""])
            continue

        durumlar = [kesinlik(s, f) for s in segmentlere_bol(metin)]
        eslesen = [(s, d) for s, d in zip(segmentlere_bol(metin), durumlar) if d]

        if not eslesen:
            rapor.writerow([gun, kurum, pdf_url, "ESLESME_YOK", "", ""])
            continue

        for segment, durum in eslesen:
            sb, kesin_mi = son_basvuru(segment, gun)
            satirlar = satir_detay(hedef, f) if durum else []
            rapor.writerow([gun, kurum, pdf_url, durum, sb.isoformat(), kesin_mi])
            ef.write(json.dumps({
                "tarih": gun.isoformat(),
                "kurum": kurum,
                "pdf_url": pdf_url,
                "durum": durum,
                "son_basvuru": sb.isoformat(),
                "kesin_tarih_mi": kesin_mi,
                "satirlar": satirlar,
                "segment_ozet": segment[:600],
            }, ensure_ascii=False) + "\n")
            ef.flush()
            print(f"    >>> {durum}: {kurum} (son başvuru {sb})")


def main() -> None:
    p = argparse.ArgumentParser(description="Resmî Gazete geriye dönük tarama")
    p.add_argument("--baslangic", required=True, type=date.fromisoformat)
    p.add_argument("--bitis", required=True, type=date.fromisoformat)
    p.add_argument("--cikti", default="tarama", type=Path)
    a = p.parse_args()
    tara(a.baslangic, a.bitis, a.cikti)


if __name__ == "__main__":
    main()
