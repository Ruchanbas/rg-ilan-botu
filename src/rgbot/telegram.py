"""Telegram bildirimi — WhatsApp'ın yanında ikinci kanal.

Neden ikinci kanal: WhatsApp Meta'ya bağımlı (template onayı, kategori
kısıtı, hesap askıya alma riski). Telegram bu kısıtların hiçbirine tabi
değil — istediğimiz tonda, bol emojili, TCF botundaki gibi samimi mesaj
atabiliyoruz. İki kanal paralel çalışır; biri çökse öbürü devam eder.

Neden GitHub Actions tarafında (Lambda değil): toplayıcı zaten Actions'ta
çalışıp eşleşmeleri buluyor. Telegram'ı da buraya koyunca Lambda sade
kalıyor ve iki kanal birbirinden tamamen bağımsız oluyor.

Gizli bilgiler ortam değişkeninden okunuyor (GitHub secret olarak
verilecek): TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_IDS (virgülle ayrılmış).
Mükerrer engelleme: gönderilen ilanları küçük bir durum dosyasında
tutuyoruz (telegram_gonderilenler.json) — Actions'ta bu dosya artifact
olarak saklanıp bir sonraki koşuda geri yükleniyor. AWS/DynamoDB'den
bağımsız olsun diye ayrı tutuldu.
"""

from __future__ import annotations

import html
import json
import os
from pathlib import Path

import requests

_API = "https://api.telegram.org"
_TIMEOUT = 20
_DURUM_DOSYASI = "telegram_gonderilenler.json"


def _ayarlar() -> tuple[str, list[str]]:
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "").strip()
    ham = os.environ.get("TELEGRAM_CHAT_IDS", "").strip()
    chat_ids = [c.strip() for c in ham.split(",") if c.strip()]
    return token, chat_ids


def _gonderilenler_yukle() -> set[str]:
    p = Path(_DURUM_DOSYASI)
    if p.exists():
        try:
            return set(json.loads(p.read_text(encoding="utf-8")))
        except Exception:
            return set()
    return set()


def _gonderilenler_kaydet(gonderilenler: set[str]) -> None:
    Path(_DURUM_DOSYASI).write_text(
        json.dumps(sorted(gonderilenler), ensure_ascii=False, indent=1),
        encoding="utf-8")


def _e(s: str) -> str:
    """HTML parse modu için kaçış (ilan başlıklarında < > & olabilir)."""
    return html.escape(str(s or "-"))


def _mesaj_olustur(e: dict) -> str:
    """TCF botundaki sıcak, emojili ton. Telegram HTML parse modu."""
    durum = e.get("durum", "KESIN")
    if durum == "SUPHELI":
        bas = "🎓 Sana uygun olabilecek bir fizyoterapi ilanı buldum 🌸"
        alt = "\n\n<i>Not: Bu ilanda başka kadrolar da var, sana uygun " \
              "olanı bir kontrol et 💛</i>"
    else:
        bas = "🎓 Sana göre bir fizyoterapi araştırma görevlisi ilanı çıktı! 🎉"
        alt = "\n\nBaşarılar, senin için tutuyorum 🍀"

    return (
        f"<b>{bas}</b>\n\n"
        f"🏛️ <b>Kurum:</b> {_e(e.get('kurum'))}\n"
        f"📍 <b>Birim:</b> {_e(e.get('birim'))}\n"
        f"🔖 <b>İlan No:</b> {_e(e.get('kadro'))}\n"
        f"📅 <b>Son başvuru:</b> {_e(e.get('son_basvuru'))}\n"
        f"🔗 <b>İlan:</b> {_e(e.get('pdf_url'))}"
        f"{alt}"
    )


def _hatirlatma_olustur(e: dict) -> str:
    return (
        "<b>⏰ Başvuru süresi yaklaşıyor 🌸</b>\n\n"
        "Daha önce ilettiğim ilanın son başvuru tarihi yaklaştı:\n\n"
        f"🏛️ <b>Kurum:</b> {_e(e.get('kurum'))}\n"
        f"📅 <b>Son başvuru:</b> {_e(e.get('son_basvuru'))}\n"
        f"🔗 <b>İlan:</b> {_e(e.get('pdf_url'))}\n\n"
        "Kaçırmak istemezsin diye hatırlatmak istedim 💛"
    )


def _gonder(token: str, chat_id: str, metin: str) -> bool:
    try:
        r = requests.post(
            f"{_API}/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": metin,
                  "parse_mode": "HTML",
                  "disable_web_page_preview": False},
            timeout=_TIMEOUT,
        )
        if r.status_code >= 300:
            print(f"Telegram hatası ({chat_id}): {r.status_code} {r.text[:200]}")
            return False
        return True
    except Exception as ex:
        print(f"Telegram istisnası ({chat_id}): {ex}")
        return False


def bildir(eslesmeler: list[dict], kuru_calisma: bool = False) -> dict:
    """Eşleşmeleri Telegram'a gönder. Mükerrer engelleme dahil.

    Dönüş: {"gonderilen": N, "atlanan": M, "kanal_hazir": bool}
    """
    token, chat_ids = _ayarlar()
    if not token or not chat_ids:
        if not kuru_calisma:
            print("Telegram ayarı eksik (token/chat_id) — kanal atlandı")
        return {"gonderilen": 0, "atlanan": 0, "kanal_hazir": False}

    gonderilenler = _gonderilenler_yukle()
    gonderilen, atlanan = 0, 0

    for e in eslesmeler:
        anahtar = str(e.get("pdf_url") or e.get("kadro") or "")
        if not anahtar:
            continue
        if anahtar in gonderilenler:
            atlanan += 1
            continue

        metin = _mesaj_olustur(e)
        if kuru_calisma:
            print(f"[TELEGRAM KURU] {chat_ids}:\n{metin}\n")
            gonderilenler.add(anahtar)
            gonderilen += 1
            continue

        basari = False
        for cid in chat_ids:
            if _gonder(token, cid, metin):
                basari = True
        if basari:
            gonderilenler.add(anahtar)
            gonderilen += 1
            print(f"  >>> Telegram gönderildi: {e.get('kurum')}")
        else:
            print(f"  !!! Telegram gönderilemedi (tekrar denenecek): "
                  f"{e.get('kurum')}")

    _gonderilenler_kaydet(gonderilenler)
    return {"gonderilen": gonderilen, "atlanan": atlanan, "kanal_hazir": True}
