"""Lambda giriş noktaları.

Mimari notu: resmigazete.gov.tr AWS IP aralıklarını engelliyor
(Lambda'dan ConnectTimeout, GitHub runner'ından 200 OK). Bu yüzden
ağa çıkıp tarama yapan kısım GitHub Actions'a taşındı (rgbot.toplayici).
Lambda artık hazır sonucu alıp şunları yapıyor:

  bildirim_handler   : mükerrer kontrolü, WhatsApp gönderimi, metrikler
  hatirlatici_handler: son başvurusu yaklaşanları hatırlatır

Sessiz ölüm koruması: gelen payload'daki sayfa_bulundu/pdf_sayisi
CloudWatch'a metrik olarak yazılıyor. Actions hiç çalışmazsa metrik de
gelmez ve alarmlar "eksik veri = ihlal" ayarında olduğu için ateşler —
yani hem site değişikliğini hem de Actions'ın durmasını yakalar.
"""

from __future__ import annotations

import os
from datetime import date, datetime, timedelta, timezone

import boto3

from . import durum, whatsapp

_KURU = os.environ.get("RGBOT_KURU_CALISMA", "false").lower() == "true"
_AD_ALANI = "RGBot"
_TRT = timezone(timedelta(hours=3))


def _metrik(ad: str, deger: float) -> None:
    try:
        boto3.client("cloudwatch").put_metric_data(
            Namespace=_AD_ALANI,
            MetricData=[{"MetricName": ad, "Value": deger, "Unit": "Count"}],
        )
    except Exception as e:
        print(f"Metrik yazilamadi ({ad}): {e}")


def _bugun() -> date:
    return datetime.now(_TRT).date()


def bildirim_handler(event=None, context=None) -> dict:
    """GitHub Actions'tan gelen tarama sonucunu isler.

    Beklenen event:
      {"tarih": "2026-07-29", "sayfa_bulundu": true, "pdf_sayisi": 17,
       "eslesmeler": [{...}]}
    """
    event = event or {}
    tarih_str = event.get("tarih") or _bugun().isoformat()
    try:
        gun = date.fromisoformat(tarih_str)
    except ValueError:
        gun = _bugun()

    sayfa = 1 if event.get("sayfa_bulundu") else 0
    pdf_sayisi = int(event.get("pdf_sayisi") or 0)
    eslesmeler = event.get("eslesmeler") or []

    _metrik("SayfaBulundu", sayfa)
    _metrik("PdfSayisi", pdf_sayisi)
    _metrik("EslesmeSayisi", len(eslesmeler))
    print(f"{gun}: sayfa={bool(sayfa)} pdf={pdf_sayisi} "
          f"eslesme={len(eslesmeler)}")

    gonderilen, atlanan = 0, 0
    for e in eslesmeler:
        pdf_url = e.get("pdf_url", "")
        if not pdf_url:
            continue
        if durum.gorulmus_mu(pdf_url):
            atlanan += 1
            continue

        try:
            sb = date.fromisoformat(e.get("son_basvuru", ""))
        except ValueError:
            sb = gun + timedelta(days=15)
        kesin_mi = bool(e.get("kesin_tarih_mi"))
        tarih_metni = sb.strftime("%d.%m.%Y")
        if not kesin_mi:
            tarih_metni = "~" + tarih_metni

        sonuc = whatsapp.ilan_bildir(
            kurum=e.get("kurum", "-"),
            birim=e.get("birim", "-"),
            kadro=e.get("kadro", "-"),
            son_basvuru=tarih_metni,
            link=pdf_url,
            kuru_calisma=_KURU,
        )
        basarili = any(r.get("ok") or r.get("kuru") for r in sonuc)
        durum.kaydet(pdf_url, e.get("kurum", "-"), e.get("durum", "KESIN"),
                     gun, sb, kesin_mi, [], basarili)
        gonderilen += 1
        print(f"  >>> gonderildi: {e.get('kurum')} — {tarih_metni}")

    return {"tarih": gun.isoformat(), "pdf": pdf_sayisi,
            "eslesme": len(eslesmeler), "gonderilen": gonderilen,
            "atlanan": atlanan}


def hatirlatici_handler(event=None, context=None) -> dict:
    gun = _bugun()
    kayitlar = durum.hatirlatilacaklar(gun, gun_kala=3)
    for k in kayitlar:
        sb = k.get("son_basvuru", "")
        try:
            sb_metni = date.fromisoformat(sb).strftime("%d.%m.%Y")
        except ValueError:
            sb_metni = sb
        whatsapp.hatirlatma_gonder(
            kurum=k.get("kurum", "-"), son_basvuru=sb_metni,
            link=k.get("pdf_url", "-"), kuru_calisma=_KURU)
        durum.hatirlatildi_isaretle(k["pdf_url"])
        print(f"Hatirlatma: {k.get('kurum')} — {sb_metni}")
    return {"hatirlatma": len(kayitlar)}
