"""DynamoDB durum yönetimi.

Tek amaç: aynı ilan için Ecem'e iki kez mesaj gitmesin. Anahtar olarak
PDF URL'ini kullanıyoruz — tarih ve sıra numarası içerdiği için doğal
olarak benzersiz.

TTL: kayıtlar 1 yıl sonra otomatik siliniyor (DynamoDB'nin ttl özelliği).
Depolama zaten bedava ama tablo sonsuza kadar şişmesin.
"""

from __future__ import annotations

import os
import time
from datetime import date

import boto3

TABLO = os.environ.get("RGBOT_TABLO", "rgbot-ilanlar")
_TTL_GUN = 365


def _tablo():
    return boto3.resource("dynamodb").Table(TABLO)


def gorulmus_mu(pdf_url: str) -> bool:
    try:
        r = _tablo().get_item(Key={"pdf_url": pdf_url})
        return "Item" in r
    except Exception:
        # Tablo okunamıyorsa "görülmemiş" say: mükerrer mesaj riski,
        # kaçırma riskinden iyidir.
        return False


def kaydet(pdf_url: str, kurum: str, durum: str, gun: date,
           son_basvuru_tarihi: date, kesin_tarih_mi: bool,
           satirlar: list[list[str]], gonderildi: bool) -> None:
    _tablo().put_item(Item={
        "pdf_url": pdf_url,
        "kurum": kurum,
        "durum": durum,
        "yayim_tarihi": gun.isoformat(),
        "son_basvuru": son_basvuru_tarihi.isoformat(),
        "kesin_tarih_mi": kesin_tarih_mi,
        "satirlar": satirlar,
        "gonderildi": gonderildi,
        "hatirlatildi": False,
        "ttl": int(time.time()) + _TTL_GUN * 86400,
    })


def isaretle_gorulmus(pdf_url: str, gun: date) -> None:
    """Eşleşmeyen PDF'ler için hafif kayıt — tekrar indirilip
    işlenmesin diye."""
    _tablo().put_item(Item={
        "pdf_url": pdf_url,
        "durum": "ESLESME_YOK",
        "yayim_tarihi": gun.isoformat(),
        "ttl": int(time.time()) + 90 * 86400,
    })


def hatirlatilacaklar(bugun: date, gun_kala: int = 3) -> list[dict]:
    """Son başvurusuna `gun_kala` gün kalan, henüz hatırlatılmamış
    ilanlar. Tablo küçük olduğu için scan yeterli ve ucuz."""
    from boto3.dynamodb.conditions import Attr
    hedef = (bugun.toordinal() + gun_kala)
    hedef_tarih = date.fromordinal(hedef).isoformat()
    r = _tablo().scan(
        FilterExpression=Attr("son_basvuru").eq(hedef_tarih)
        & Attr("gonderildi").eq(True)
        & Attr("hatirlatildi").eq(False)
    )
    return r.get("Items", [])


def hatirlatildi_isaretle(pdf_url: str) -> None:
    _tablo().update_item(
        Key={"pdf_url": pdf_url},
        UpdateExpression="SET hatirlatildi = :d",
        ExpressionAttributeValues={":d": True},
    )
