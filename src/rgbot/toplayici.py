"""Toplayıcı — GitHub Actions üzerinde çalışır (kaynak: ilan.gov.tr API).

Tarihçe: ilk sürüm Resmî Gazete HTML/PDF'lerini tarıyordu; RG hem AWS
hem GitHub/Azure IP'lerini engellediği için kaynak ilan.gov.tr'nin JSON
API'sine taşındı (Actions'tan 200 dönüyor, canlı doğrulandı). Aynı
ilanlar mevzuat gereği iki mecrada da yayımlanıyor, veri kaybı yok.

Akış:
  1. Filtredeki her arama terimi için AdsByFilter sorgusu (q dizisi!)
  2. Ön eleme: akademik kurum mu (üniversite/rektörlük/enstitü/fakülte)
     + son N gün içinde mi + arşivlenmemiş mi
  3. Adayların detayını çek, TÜM metni topla, mevcut eşleştiriciden
     geçir (arş. gör. + fizyoterapi, Fiziksel Tıp dışlanır)
  4. Lambda'nın beklediği payload'ı üret (şema değişmedi — AWS tarafına
     dokunmak gerekmiyor)

Metrik anlamları (CloudWatch):
  SayfaBulundu : API cevap verdi mi (kaynak canlı mı)
  PdfSayisi    : sorguların toplam numFound'u — API şekli bozulursa
                 sıfıra düşer, "sessiz ölüm" alarmı bunu yakalar.
                 (İsim tarihsel; RG döneminden kalma, alarm tanımları
                 değişmesin diye korunuyor.)

Kullanım:
    python -m rgbot.toplayici --cikti sonuc.json
"""

from __future__ import annotations

import argparse
import json
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import requests

from . import ilanapi
from .matcher import Filtreler, kesinlik
from .normalize import norm
from .tarih import son_basvuru

_TRT = timezone(timedelta(hours=3))
_KURUM_IPUCLARI = ["universite", "rektorlug", "enstitu", "fakulte",
                   "yuksekokul", "akademik"]
_SB_ANAHTAR = ["son basvuru", "basvuru bitis", "son müracaat", "son muracaat"]
_AZAMI_DETAY = 20  # tek koşuda en fazla bu kadar detay çekilir (nezaket)


def _bugun() -> date:
    return datetime.now(_TRT).date()


def _yayim_tarihi(ilan: dict) -> date | None:
    ham = (ilan.get("publishStartDate") or "")[:10]
    try:
        return date.fromisoformat(ham)
    except ValueError:
        return None


def aday_mi(ilan: dict, gun_esigi: int, bugun: date) -> bool:
    """Detayı çekmeye değer mi? (akademik kurum + güncel + arşiv değil)"""
    if ilan.get("isArchived"):
        return False
    yt = _yayim_tarihi(ilan)
    if yt is None or (bugun - yt).days > gun_esigi:
        return False
    kimlik = norm(" ".join(str(ilan.get(a) or "") for a in
                           ("advertiserName", "slugifyTitle", "title")))
    return any(ip in kimlik for ip in _KURUM_IPUCLARI)


def _son_basvuru_bul(ilan: dict, detay_metni: str,
                     yayim: date) -> tuple[date, bool]:
    """Önce adTypeFilters'taki 'Son Başvuru' benzeri alan, sonra detay
    metnindeki tarih deseni, en son yayım+15 tahmini."""
    import re
    for cift in ilan.get("adTypeFilters") or []:
        if any(a in norm(str(cift.get("key", ""))) for a in _SB_ANAHTAR):
            m = re.search(r"(\d{1,2})[./](\d{1,2})[./](\d{4})",
                          str(cift.get("value", "")))
            if m:
                try:
                    return date(int(m[3]), int(m[2]), int(m[1])), True
                except ValueError:
                    pass
    return son_basvuru(detay_metni, yayim)


def tara(filtreler: Filtreler | None = None, gun_esigi: int = 20) -> dict:
    f = filtreler or Filtreler.yukle()
    bugun = _bugun()
    session = requests.Session()
    sonuc = {"tarih": bugun.isoformat(), "sayfa_bulundu": False,
             "pdf_sayisi": 0, "eslesmeler": []}

    # 1) Arama
    havuz: dict[str, dict] = {}
    toplam_bulunan = 0
    for terim in f.arama:
        try:
            num, ilanlar = ilanapi.sorgula(session, terim)
        except Exception as e:
            print(f"Sorgu başarısız ({terim}): {e}")
            continue
        sonuc["sayfa_bulundu"] = True
        toplam_bulunan += num
        for i in ilanlar:
            anahtar = str(i.get("adNo") or i.get("id") or ilanapi.ilan_url(i))
            havuz.setdefault(anahtar, i)
        print(f"'{terim}': numFound={num}, alınan={len(ilanlar)}")

    sonuc["pdf_sayisi"] = toplam_bulunan
    adaylar = [i for i in havuz.values() if aday_mi(i, gun_esigi, bugun)]
    adaylar.sort(key=lambda i: _yayim_tarihi(i) or date.min, reverse=True)
    adaylar = adaylar[:_AZAMI_DETAY]
    print(f"Havuz: {len(havuz)} ilan, akademik+güncel aday: {len(adaylar)}")

    # 2) Detay + eşleştirme
    for ilan in adaylar:
        url = ilanapi.ilan_url(ilan)
        baslik = str(ilan.get("title") or "-")
        kurum = str(ilan.get("advertiserName") or "-")
        try:
            d = ilanapi.detay(session, str(ilan.get("id")))
            metin = ilanapi.metin_topla(d)
        except Exception as e:
            print(f"  detay alınamadı ({url}): {e}")
            metin = ""

        tam_metin = f"{baslik} {ilanapi.metin_topla(ilan)} {metin}"
        durum = kesinlik(tam_metin, f)
        if not durum:
            continue
        if not metin:
            durum = "SUPHELI"  # detay okunamadıysa temkinli işaretle

        yayim = _yayim_tarihi(ilan) or bugun
        sb, kesin_mi = _son_basvuru_bul(ilan, tam_metin, yayim)
        sehir = str(ilan.get("addressCityName") or "").title()
        sonuc["eslesmeler"].append({
            "pdf_url": url,
            "kurum": kurum,
            "durum": durum,
            "birim": (f"{baslik} — {sehir}" if sehir else baslik)[:250]
                     + (" (kontrol et)" if durum == "SUPHELI" else ""),
            "kadro": str(ilan.get("adNo") or "-"),
            "son_basvuru": sb.isoformat(),
            "kesin_tarih_mi": kesin_mi,
        })
        print(f"  >>> {durum}: {kurum} — {baslik[:60]} (son başvuru {sb})")

    print(f"Toplam eşleşme: {len(sonuc['eslesmeler'])}")
    return sonuc


def main() -> None:
    p = argparse.ArgumentParser(description="ilan.gov.tr toplayıcı")
    p.add_argument("--cikti", default="sonuc.json", type=Path)
    p.add_argument("--gun-esigi", default=20, type=int,
                   help="Bu kadar günden eski ilanlar atlanır")
    p.add_argument("--telegram-kuru", action="store_true",
                   help="Telegram'a gerçek mesaj atma, sadece logla")
    a = p.parse_args()
    sonuc = tara(gun_esigi=a.gun_esigi)
    a.cikti.write_text(json.dumps(sonuc, ensure_ascii=False),
                       encoding="utf-8")
    print(f"Yazıldı: {a.cikti}")

    # Telegram kanalı (WhatsApp'tan bağımsız, yanında ikinci kanal).
    # Token/chat_id ortam değişkeninde yoksa sessizce atlanır — yani
    # Telegram kurulmadıysa sistem yine çalışır, sadece bu kanal susar.
    from . import telegram
    tg = telegram.bildir(sonuc.get("eslesmeler", []),
                         kuru_calisma=a.telegram_kuru)
    if tg["kanal_hazir"]:
        print(f"Telegram: gönderilen={tg['gonderilen']} "
              f"atlanan={tg['atlanan']}")


if __name__ == "__main__":
    main()
