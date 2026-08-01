"""Segment bazında eşleştirme.

Kural: aynı SEGMENT içinde hem pozisyon (araştırma görevlisi) hem alan
(fizyoterapi) geçmeli. "Fiziksel Tıp ve Rehabilitasyon" tıp fakültesi
uzmanlık dalıdır, fizyoterapist başvuramaz — açıkça dışlanır.

Kesinlik iki seviyeli:
- KESIN   : pozisyon ve alan terimleri birbirine yakın (aynı tablo
            satırından gelme ihtimali yüksek).
- SUPHELI : ikisi de segmentte var ama uzak — örn. arş. gör. kadrosu
            Hemşirelik'in, fizyoterapi satırı öğretim üyesinin olabilir.
            Yine de GÖNDERİLİR; mesaja "PDF'e bak" notu düşülür. Yanlış
            alarm 10 saniye, kaçan ilan bir iş fırsatı kaybettirir.

Lambda aşamasında pdfplumber.extract_tables ile gerçek satır kontrolü
eklenince KESIN etiketi tablo satırından gelecek; yakınlık o zamana
kadarki yaklaşık ölçü.

Filtreler JSON'dan yüklenebilir (RGBOT_FILTRE_JSON ortam değişkeni ya da
dogrudan yol) — canlıda SSM Parameter Store'dan aynı şema okunacak,
deploy etmeden kelime değiştirilebilsin diye.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path

from .normalize import norm

# Yakınlık penceresi (normalize edilmiş karakter). Gerçek tablolarda bir
# satır ~150-250 karaktere düzleşiyor; 300 güvenli üst sınır.
_YAKINLIK = 300


@dataclass
class Filtreler:
    pozisyon: list[str] = field(default_factory=lambda: [
        "arastirma gorevlisi",
        "ars. gor.",
        "ars.gor.",
    ])
    alan: list[str] = field(default_factory=lambda: [
        "fizyoterapi",
        "fizik tedavi ve rehabilitasyon",
    ])
    disla: list[str] = field(default_factory=lambda: [
        "fiziksel tip ve rehabilitasyon",
    ])

    @classmethod
    def yukle(cls, yol: str | Path | None = None) -> "Filtreler":
        """JSON'dan yükle; yol verilmezse RGBOT_FILTRE_JSON'a bak,
        o da yoksa varsayılanları döndür."""
        yol = yol or os.environ.get("RGBOT_FILTRE_JSON")
        if not yol:
            return cls()
        veri = json.loads(Path(yol).read_text(encoding="utf-8"))
        # JSON'daki terimler de normalize edilir ki kullanıcı Türkçe
        # karakterle yazsa bile eşleşme bozulmasın.
        return cls(
            pozisyon=[norm(t) for t in veri.get("pozisyon", [])] or cls().pozisyon,
            alan=[norm(t) for t in veri.get("alan", [])] or cls().alan,
            disla=[norm(t) for t in veri.get("disla", [])],
        )


def _disla_temizle(n: str, filtreler: Filtreler) -> str:
    for d in filtreler.disla:
        n = n.replace(d, " " * len(d))  # uzunluk korunur -> yakınlık ölçümü bozulmaz
    return n


def eslesir_mi(segment: str, filtreler: Filtreler | None = None) -> bool:
    """Segment hem pozisyon hem alan içeriyor mu?"""
    f = filtreler or Filtreler()
    n = norm(segment)
    if not any(p in n for p in f.pozisyon):
        return False
    temiz = _disla_temizle(n, f)
    return any(a in temiz for a in f.alan)


def kesinlik(segment: str, filtreler: Filtreler | None = None) -> str | None:
    """None = eşleşme yok, 'KESIN' = terimler yakın, 'SUPHELI' = uzak."""
    f = filtreler or Filtreler()
    if not eslesir_mi(segment, f):
        return None
    n = _disla_temizle(norm(segment), f)

    poz_konumlar = [i for p in f.pozisyon
                    for i in _tum_konumlar(n, p)]
    alan_konumlar = [i for a in f.alan
                     for i in _tum_konumlar(n, a)]
    en_yakin = min(abs(p - a) for p in poz_konumlar for a in alan_konumlar)
    return "KESIN" if en_yakin <= _YAKINLIK else "SUPHELI"


def _tum_konumlar(metin: str, terim: str) -> list[int]:
    konumlar, i = [], metin.find(terim)
    while i != -1:
        konumlar.append(i)
        i = metin.find(terim, i + 1)
    return konumlar
