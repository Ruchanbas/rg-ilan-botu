"""WhatsApp Cloud API üzerinden bildirim gönderimi.

Meta kısıtları (bunlar tasarımı belirledi):
- Bot her zaman ilk yazan taraf olduğu için serbest metin gönderilemez;
  önceden onaylanmış TEMPLATE kullanmak zorunlu.
- Template parametrelerinin içinde satır sonu, tab veya 4+ ardışık
  boşluk olamaz — mesaj reddedilir. Bu yüzden her alan ayrı parametre
  ve hepsi _temizle()'den geçiyor.
- Test numarasıyla en fazla 5 alıcıya gönderilebiliyor.

Gizli bilgiler ortam değişkeninden değil, SSM Parameter Store'dan
okunuyor; Lambda'nın ortam değişkenlerinde token durmasın diye.
"""

from __future__ import annotations

import json
import os
import re
from functools import lru_cache

import boto3
import requests

_GRAPH = "https://graph.facebook.com/v23.0"
_PARAM_ONEK = os.environ.get("RGBOT_SSM_ONEK", "/rgbot")
_SABLON = os.environ.get("RGBOT_SABLON", "fzt_ilan_bildirimi")
_SABLON_HATIRLATMA = os.environ.get("RGBOT_SABLON_HATIRLATMA",
                                    "fzt_ilan_hatirlatma")
_DIL = "tr"
_BOSLUK = re.compile(r"\s+")


@lru_cache(maxsize=1)
def _ayarlar() -> dict:
    """SSM'den token, phone_id ve alıcı listesini oku (Lambda sıcak
    kaldığı sürece önbellekte).

    SSM'e ulaşılamazsa çökmek yerine boş ayar döner: kuru mod her
    koşulda çalışsın, gerçek modda da hata net loglansın diye.
    """
    bos = {"token": "", "phone_id": "", "alicilar": []}
    try:
        ssm = boto3.client("ssm")
        r = ssm.get_parameters(
            Names=[f"{_PARAM_ONEK}/wa_token",
                   f"{_PARAM_ONEK}/wa_phone_id",
                   f"{_PARAM_ONEK}/alicilar"],
            WithDecryption=True,
        )
        d = {p["Name"].rsplit("/", 1)[-1]: p["Value"] for p in r["Parameters"]}
        try:
            alicilar = json.loads(d.get("alicilar", "[]"))
        except json.JSONDecodeError:
            print("UYARI: /rgbot/alicilar geçerli JSON değil")
            alicilar = []
        return {
            "token": d.get("wa_token", ""),
            "phone_id": d.get("wa_phone_id", ""),
            "alicilar": alicilar,
        }
    except Exception as e:
        print(f"SSM okunamadı: {e}")
        return bos


def _temizle(deger: str, azami: int = 900) -> str:
    """Meta'nın parametre kurallarına uygun hale getir."""
    s = _BOSLUK.sub(" ", str(deger or "")).strip()
    return (s[:azami - 1] + "…") if len(s) > azami else (s or "-")


def gonder(sablon: str, parametreler: list[str],
           kuru_calisma: bool = False) -> list[dict]:
    """Template mesajı tüm alıcılara gönder. Sonuç listesi döner."""
    a = _ayarlar()
    temiz = [_temizle(p) for p in parametreler]

    if kuru_calisma or not a["token"] or not a["phone_id"]:
        print(f"[KURU] sablon={sablon} alicilar={a['alicilar']} "
              f"parametreler={temiz}")
        return [{"kuru": True, "parametreler": temiz}]

    sonuclar = []
    for alici in a["alicilar"]:
        try:
            r = requests.post(
                f"{_GRAPH}/{a['phone_id']}/messages",
                headers={"Authorization": f"Bearer {a['token']}"},
                json={
                    "messaging_product": "whatsapp",
                    "to": alici,
                    "type": "template",
                    "template": {
                        "name": sablon,
                        "language": {"code": _DIL},
                        "components": [{
                            "type": "body",
                            "parameters": [
                                {"type": "text", "text": t} for t in temiz
                            ],
                        }],
                    },
                },
                timeout=20,
            )
            ok = r.status_code < 300
            if not ok:
                print(f"WhatsApp hatası ({alici}): {r.status_code} {r.text[:300]}")
            sonuclar.append({"alici": alici, "ok": ok, "kod": r.status_code})
        except Exception as e:
            print(f"WhatsApp istisnası ({alici}): {e}")
            sonuclar.append({"alici": alici, "ok": False, "hata": str(e)})
    return sonuclar


def ilan_bildir(kurum: str, birim: str, kadro: str, son_basvuru: str,
                link: str, kuru_calisma: bool = False) -> list[dict]:
    return gonder(_SABLON, [kurum, birim, kadro, son_basvuru, link],
                  kuru_calisma)


def hatirlatma_gonder(kurum: str, son_basvuru: str, link: str,
                      kuru_calisma: bool = False) -> list[dict]:
    return gonder(_SABLON_HATIRLATMA, [kurum, son_basvuru, link],
                  kuru_calisma)
