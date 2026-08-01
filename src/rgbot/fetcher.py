"""Resmî Gazete keşif ve indirme.

İki doğrulanmış gerçek üstüne kurulu:

1. Çeşitli İlanlar sayfasının numarası SABİT DEĞİL. Yargı ilanı olmayan
   günlerde -4 yerine -3 olabiliyor. O yüzden asla URL kurup atlamıyoruz;
   önce fihrist sayfasından "Çeşitli İlânlar" bağlantısını buluyoruz,
   fihrist cevap vermezse -2..-6 aralığını yoklayıp içeriğinde
   "ÇEŞİTLİ İLÂNLAR" geçen sayfayı seçiyoruz.

2. İlan sayfaları windows-1254 kodlu eski HTML. requests'in tahminine
   bırakılırsa Türkçe karakterler çöp oluyor; decode elle yapılır.
"""

from __future__ import annotations

import ssl
import time
from datetime import date
from pathlib import Path

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from .normalize import norm

BASE = "https://www.resmigazete.gov.tr"
_UA = {"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                      "AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/126.0.0.0 Safari/537.36")}
_TIMEOUT = 30
_DENEME = 3

# resmigazete.gov.tr eski bir sunucu yapılandırmasıyla "legacy renegotiation"
# istiyor. OpenSSL 3 / Python 3.12+ bunu varsayılan olarak reddediyor
# (SSLEOFError: UNEXPECTED_EOF_WHILE_READING). ssl.OP_LEGACY_SERVER_CONNECT
# bayrağı bu belirli siteyle uyumluluk için gerekli — şifreleme gücünü
# düşürmüyor, sadece eski el sıkışma uzantısına izin veriyor.
_OP_LEGACY_SERVER_CONNECT = 0x4


class _LegacyRenegotiationAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.options |= _OP_LEGACY_SERVER_CONNECT
        kwargs["ssl_context"] = ctx
        return super().init_poolmanager(*args, **kwargs)


def yeni_oturum() -> requests.Session:
    """resmigazete.gov.tr ile uyumlu, legacy-renegotiation açık oturum."""
    s = requests.Session()
    s.mount("https://", _LegacyRenegotiationAdapter())
    return s


def _get(session: requests.Session, url: str, **kw) -> requests.Response | None:
    """3 denemeli GET. 404 normaldir (o gün sayı yok), None döner."""
    for i in range(_DENEME):
        try:
            r = session.get(url, headers=_UA, timeout=_TIMEOUT, **kw)
            if r.status_code == 404:
                return None
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == _DENEME - 1:
                raise
            time.sleep(3 * (i + 1))
    return None


def cesitli_ilanlar_url(tarih: date, session: requests.Session | None = None) -> str | None:
    """O günün Çeşitli İlanlar sayfasını bul. Yoksa None (tatil/mükerrer)."""
    s = session or yeni_oturum()

    # 1. yol: fihrist
    r = _get(s, f"{BASE}/fihrist", params={"tarih": tarih.isoformat()})
    if r is not None:
        soup = BeautifulSoup(r.text, "html.parser")
        for a in soup.find_all("a", href=True):
            if "cesitli ilan" in norm(a.get_text()):
                href = a["href"]
                return href if href.startswith("http") else BASE + href

    # 2. yol: numara yoklama (-2..-6), sayfa başlığından doğrulama
    for n in range(2, 7):
        url = (f"{BASE}/ilanlar/eskiilanlar/{tarih.year}/{tarih.month:02d}/"
               f"{tarih:%Y%m%d}-{n}.htm")
        r = _get(s, url)
        if r is None:
            continue
        icerik = norm(r.content.decode("cp1254", errors="replace")[:4000])
        if "cesitli ilan" in icerik:
            return url
    return None


def pdf_linkleri(sayfa_url: str, session: requests.Session | None = None
                 ) -> list[tuple[str, str]]:
    """Çeşitli İlanlar sayfasındaki (kurum_adi, pdf_url) çiftleri.

    Kurum filtresi UYGULANMAZ: "üniversite" kelime filtresi İzmir Yüksek
    Teknoloji Enstitüsü gibi kurumları kaçırır. Ayıklama eşleştiriciye
    bırakılır; alakasız PDF indirmek ucuzdur, kaçan ilan pahalıdır.
    """
    s = session or yeni_oturum()
    r = _get(s, sayfa_url)
    if r is None:
        return []
    html = r.content.decode("cp1254", errors="replace")
    soup = BeautifulSoup(html, "html.parser")

    sonuc: list[tuple[str, str]] = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if not href.lower().endswith(".pdf"):
            continue
        tam = href if href.startswith("http") else _mutlak(sayfa_url, href)
        kurum = " ".join(a.get_text().split()) or tam.rsplit("/", 1)[-1]
        sonuc.append((kurum, tam))
    return sonuc


def indir(pdf_url: str, hedef: Path, session: requests.Session | None = None) -> Path:
    s = session or yeni_oturum()
    r = _get(s, pdf_url)
    if r is None:
        raise FileNotFoundError(pdf_url)
    hedef.parent.mkdir(parents=True, exist_ok=True)
    hedef.write_bytes(r.content)
    return hedef


def _mutlak(taban_url: str, href: str) -> str:
    if href.startswith("/"):
        return BASE + href
    return taban_url.rsplit("/", 1)[0] + "/" + href
