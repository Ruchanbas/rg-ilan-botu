"""PDF'ten metin ve tablo satırı çıkarma (pdfplumber).

metin_cikar  -> segmentasyon + eşleştirme için ham metin
satir_detay  -> eşleşen ilanlarda birim/adet/ALES gibi alanları veren
                tablo satırları. Önce varsayılan (çizgi tabanlı) tablo
                algılama, tutmazsa metin hizalamalı strateji denenir.
                İkisi de tutmazsa boş liste döner — çağıran taraf ilanı
                SUPHELI işaretleyip yine de gönderir.
"""

from __future__ import annotations

from pathlib import Path

import pdfplumber

from .matcher import Filtreler, _disla_temizle
from .normalize import norm

_METIN_STRATEJI = {"vertical_strategy": "text", "horizontal_strategy": "text"}


def metin_cikar(pdf_yolu: str | Path) -> str:
    parcalar: list[str] = []
    with pdfplumber.open(pdf_yolu) as pdf:
        for sayfa in pdf.pages:
            parcalar.append(sayfa.extract_text() or "")
    return "\n".join(parcalar)


def satir_detay(pdf_yolu: str | Path,
                filtreler: Filtreler | None = None) -> list[list[str]]:
    """Hem pozisyon hem alan içeren tablo satırlarını döndürür."""
    f = filtreler or Filtreler()
    bulunan: list[list[str]] = []

    with pdfplumber.open(pdf_yolu) as pdf:
        for sayfa in pdf.pages:
            tablolar = sayfa.extract_tables() or []
            if not tablolar:
                tablolar = sayfa.extract_tables(_METIN_STRATEJI) or []
            for tablo in tablolar:
                for satir in tablo:
                    hucreler = [h for h in satir if h]
                    n = _disla_temizle(norm(" ".join(hucreler)), f)
                    if (any(p in n for p in f.pozisyon)
                            and any(a in n for a in f.alan)):
                        bulunan.append(hucreler)
    return bulunan
