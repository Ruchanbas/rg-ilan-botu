"""Toplayıcı — GitHub Actions üzerinde çalışır.

Neden ayrı bir bileşen: resmigazete.gov.tr AWS IP aralıklarını
engelliyor (Lambda'dan ConnectTimeout, GitHub runner'larından sorunsuz).
Bu yüzden ağa çıkan kısım Actions'ta, durum/bildirim/alarm kısmı AWS'de.

Çıktı, bildirim Lambda'sına aynen payload olarak verilecek JSON:

    {
      "tarih": "2026-07-29",
      "sayfa_bulundu": true,
      "pdf_sayisi": 17,
      "eslesmeler": [
        {"pdf_url": "...", "kurum": "...", "durum": "KESIN",
         "birim": "...", "kadro": "...", "son_basvuru": "2026-08-13",
         "kesin_tarih_mi": false}
      ]
    }

Kullanım:
    python -m rgbot.toplayici --cikti sonuc.json
    python -m rgbot.toplayici --tarih 2026-07-29 --cikti sonuc.json
"""

from __future__ import annotations

import argparse
import json
import tempfile
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

from . import fetcher
from .fetcher import cesitli_ilanlar_url, indir, pdf_linkleri
from .matcher import Filtreler, kesinlik
from .pdftext import metin_cikar, satir_detay
from .segment import segmentlere_bol
from .tarih import son_basvuru

_TRT = timezone(timedelta(hours=3))


def _bugun() -> date:
    """Türkiye saatiyle bugün. Runner UTC çalışır, 09:00 TRT = 06:00 UTC;
    UTC tarihi kullanmak gün kaymasına yol açabilir."""
    return datetime.now(_TRT).date()


def _birim_ozet(satirlar: list[list[str]]) -> tuple[str, str]:
    if not satirlar:
        return "-", "-"
    ilk = satirlar[0]
    birim = " / ".join(h for h in ilk[:3] if h and not h.strip().isdigit())
    return birim or "-", f"{len(satirlar)} kadro satırı"


def tara(gun: date, filtreler: Filtreler | None = None) -> dict:
    f = filtreler or Filtreler.yukle()
    session = fetcher.yeni_oturum()
    sonuc = {"tarih": gun.isoformat(), "sayfa_bulundu": False,
             "pdf_sayisi": 0, "eslesmeler": []}

    url = cesitli_ilanlar_url(gun, session)
    if not url:
        print(f"{gun}: Çeşitli İlanlar sayfası yok (hafta sonu/tatil olabilir)")
        return sonuc

    sonuc["sayfa_bulundu"] = True
    linkler = pdf_linkleri(url, session)
    sonuc["pdf_sayisi"] = len(linkler)
    print(f"{gun}: {len(linkler)} PDF")

    with tempfile.TemporaryDirectory() as tmp:
        for kurum, pdf_url in linkler:
            hedef = Path(tmp) / pdf_url.rsplit("/", 1)[-1]
            try:
                indir(pdf_url, hedef, session)
                metin = metin_cikar(hedef)
            except Exception as e:
                print(f"  PDF atlandı ({pdf_url}): {e}")
                continue

            for segment in segmentlere_bol(metin):
                d = kesinlik(segment, f)
                if not d:
                    continue
                sb, kesin_mi = son_basvuru(segment, gun)
                satirlar = satir_detay(hedef, f)
                birim, kadro = _birim_ozet(satirlar)
                if d == "SUPHELI" or not satirlar:
                    birim = f"{birim} (kontrol et)"
                sonuc["eslesmeler"].append({
                    "pdf_url": pdf_url, "kurum": kurum, "durum": d,
                    "birim": birim, "kadro": kadro,
                    "son_basvuru": sb.isoformat(),
                    "kesin_tarih_mi": kesin_mi,
                })
                print(f"  >>> {d}: {kurum} — son başvuru {sb}")

    print(f"Toplam eşleşme: {len(sonuc['eslesmeler'])}")
    return sonuc


def main() -> None:
    p = argparse.ArgumentParser(description="Resmî Gazete toplayıcı")
    p.add_argument("--tarih", default=None,
                   help="YYYY-MM-DD (varsayılan: bugün, TRT)")
    p.add_argument("--cikti", default="sonuc.json", type=Path)
    a = p.parse_args()

    gun = date.fromisoformat(a.tarih) if a.tarih else _bugun()
    sonuc = tara(gun)
    a.cikti.write_text(json.dumps(sonuc, ensure_ascii=False), encoding="utf-8")
    print(f"Yazıldı: {a.cikti}")


if __name__ == "__main__":
    main()
