"""arsiv/ilanlar.jsonl icindekileri tek ozet mesaji olarak Telegram'a yollar.
Elle tetiklenir. KURU=true iken hicbir mesaj gitmez, sadece loga basar."""
import json, os, pathlib, urllib.parse, urllib.request

ARSIV = pathlib.Path("arsiv/ilanlar.jsonl")
LIMIT = 3500


def kayitlar():
    if not ARSIV.exists():
        return []
    out = []
    for satir in ARSIV.read_text(encoding="utf-8").splitlines():
        satir = satir.strip()
        if satir:
            try:
                out.append(json.loads(satir))
            except json.JSONDecodeError:
                pass
    return out


def tarih(k):
    return str(k.get("yayim_tarihi") or k.get("tarih") or "")[:10]


def satir(k):
    p = f"- {tarih(k)} {k.get('kurum', '?')}"
    if k.get("birim"):
        p += f" / {k['birim']}"
    if k.get("son_basvuru"):
        p += f" (son basvuru {k['son_basvuru']})"
    if k.get("pdf_url"):
        p += f"\n  {k['pdf_url']}"
    return p


def parcala(baslik, satirlar):
    mesajlar, tampon = [], baslik
    for s in satirlar:
        if len(tampon) + len(s) + 2 > LIMIT:
            mesajlar.append(tampon)
            tampon = ""
        tampon += ("\n\n" if tampon else "") + s
    if tampon.strip():
        mesajlar.append(tampon)
    return mesajlar


def hedefler():
    ham = os.environ.get("HEDEF", "").strip() or os.environ.get("TELEGRAM_CHAT_IDS", "")
    ham = ham.strip()
    if ham.startswith("["):
        return [str(x) for x in json.loads(ham)]
    return [h.strip() for h in ham.replace(";", ",").split(",") if h.strip()]


def gonder(chat_id, metin, token):
    veri = urllib.parse.urlencode({
        "chat_id": chat_id, "text": metin, "disable_web_page_preview": "true",
    }).encode()
    istek = urllib.request.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=veri)
    with urllib.request.urlopen(istek, timeout=30) as c:
        return c.status


def main():
    baslangic = os.environ.get("BASLANGIC", "")
    kuru = os.environ.get("KURU", "true").lower() == "true"
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")

    ks = sorted([k for k in kayitlar() if tarih(k) >= baslangic], key=tarih)
    if not ks:
        print("Arsivde gonderilecek kayit yok.")
        return

    baslik = (f"Biriken ilanlar ({baslangic} sonrasi) - {len(ks)} kayit\n"
              "Basvuru sureleri dolmus olabilir, liste bilgi amacli.\n")
    for m in parcala(baslik, [satir(k) for k in ks]):
        if kuru:
            print("--- KURU CALISMA ---\n" + m)
        else:
            for h in hedefler():
                print("gonderildi:", h, gonder(h, m, token))


if __name__ == "__main__":
    main()
