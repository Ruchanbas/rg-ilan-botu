"""ilan.gov.tr API istemcisi.

Keşifle doğrulanmış gerçekler (tarayıcı Network kaydı + canlı denemeler):
- Taban adres ÇİFT api içerir: https://www.ilan.gov.tr/api/api/services/app
  (uygulama yapılandırmasındaki remoteServiceBaseUrl=".../api" üstüne
  istemci kodu bir "/api/..." daha ekliyor)
- Arama: POST Ad/AdsByFilter, gövde:
      {"keys": {"q": ["fizyoterapi"]}, "skipCount": 0, "maxResultCount": 12}
  DİKKAT: q değeri DİZİ olmak zorunda; düz metin verilirse 400 döner.
- Cevap: {"result": {"numFound": N, "ads": [...]}} — her ilan: title,
  advertiserName, slugifyTitle, addressCityName, publishStartDate,
  urlStr, isArchived, adTypeFilters[{key,value}]
- Detay: GET AdDetail/GetAdDetail?id=...&isKiwiAd=false
  (cevap şeması doğrulanmadı; bu yüzden metin_topla() şemadan bağımsız,
  JSON'daki tüm metinleri özyinelemeli toplar)
"""

from __future__ import annotations

import re
import time
from typing import Any

import requests

API = "https://www.ilan.gov.tr/api/api/services/app"
SITE = "https://www.ilan.gov.tr"
_UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/126.0.0.0 Safari/537.36")}
_TIMEOUT = 30
_DENEME = 3
_ETIKET = re.compile(r"<[^>]+>")


def _istek(session: requests.Session, metod: str, url: str, **kw):
    for i in range(_DENEME):
        try:
            r = session.request(metod, url, headers=_UA, timeout=_TIMEOUT, **kw)
            r.raise_for_status()
            return r.json()
        except Exception:
            if i == _DENEME - 1:
                raise
            time.sleep(3 * (i + 1))


def sorgula(session: requests.Session, terim: str,
            max_sonuc: int = 100) -> tuple[int, list[dict]]:
    """AdsByFilter araması. (numFound, ilanlar) döner."""
    veri = _istek(session, "POST", f"{API}/Ad/AdsByFilter", json={
        "keys": {"q": [terim]},
        "skipCount": 0,
        "maxResultCount": max_sonuc,
    })
    sonuc = (veri or {}).get("result") or {}
    return int(sonuc.get("numFound") or 0), list(sonuc.get("ads") or [])


def detay(session: requests.Session, ilan_id: str) -> dict:
    veri = _istek(session, "GET", f"{API}/AdDetail/GetAdDetail",
                  params={"id": ilan_id, "isKiwiAd": "false"})
    return (veri or {}).get("result") or {}


def metin_topla(obj: Any, _derinlik: int = 0) -> str:
    """JSON'daki tüm metin değerlerini topla, HTML etiketlerini ayıkla.

    Detay cevabının şeması belgelenmediği için alan adlarına
    güvenmiyoruz: hangi alanda olursa olsun ilan metnindeki
    'Araştırma Görevlisi' ve 'Fizyoterapi' kelimeleri buradan geçer.
    """
    if _derinlik > 8:
        return ""
    parcalar: list[str] = []
    if isinstance(obj, str):
        parcalar.append(_ETIKET.sub(" ", obj))
    elif isinstance(obj, dict):
        for v in obj.values():
            parcalar.append(metin_topla(v, _derinlik + 1))
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            parcalar.append(metin_topla(v, _derinlik + 1))
    return " ".join(p for p in parcalar if p)


def ilan_url(ilan: dict) -> str:
    u = ilan.get("urlStr") or ""
    if u.startswith("http"):
        return u
    return SITE + u if u else SITE
