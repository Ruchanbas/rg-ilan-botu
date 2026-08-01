"""Son başvuru tarihi çıkarma.

Öncelik ilanın kendi yazdığı tarihte ("Son Başvuru Tarihi : 30.04.2026").
Yazmıyorsa mevzuat kuralı: yayım tarihi + 15 gün. Bu hesap yaklaşıktır —
15. gün hafta sonuna/tatile denk gelirse süre bir sonraki iş gününe
kayar ve biz tatil takvimi tutmuyoruz. Bu yüzden hesaplanan tarih
(kesin=False) mesajda "~" ile gösterilmeli.
"""

from __future__ import annotations

import re
from datetime import date, timedelta

from .normalize import norm

# norm() sonrası arandığı için desen ASCII/küçük harf.
_TARIH = re.compile(
    r"son basvuru tarihi\s*:?\s*(\d{1,2})[./](\d{1,2})[./](\d{4})"
)


def son_basvuru(metin: str, yayim_tarihi: date) -> tuple[date, bool]:
    """(tarih, kesin_mi) döndürür."""
    m = _TARIH.search(norm(metin))
    if m:
        gun, ay, yil = int(m.group(1)), int(m.group(2)), int(m.group(3))
        try:
            return date(yil, ay, gun), True
        except ValueError:
            pass  # PDF'te bozuk tarih -> hesaba düş
    return yayim_tarihi + timedelta(days=15), False
