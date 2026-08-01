"""Türkçe duyarlı metin normalizasyonu.

Neden var:
- Python'da "İ".lower() Türkçe için bozuktur (i + birleşik nokta üretir,
  hiçbir aramayla eşleşmez). Önce Türkçe harfleri elle indiriyoruz.
- PDF'ten çıkan metinde tablo hücreleri satır ortasından kırılır
  ("Araştırma\nGörevlisi"). Tüm boşluk türlerini tek boşluğa düzlüyoruz.
- Aramayı ASCII düzleminde yapıyoruz ki "FİZYOTERAPİ", "Fizyoterapi",
  "fizyoterapi" hepsi aynı anahtara insin.
"""

from __future__ import annotations

import re
import unicodedata

# Türkçe büyük harf -> küçük harf (str.lower çağrılmadan ÖNCE uygulanmalı)
_TR = str.maketrans({
    "İ": "i", "I": "ı",
    "Ş": "ş", "Ğ": "ğ", "Ü": "ü", "Ö": "ö", "Ç": "ç",
})

# Küçük Türkçe/şapkalı harf -> ASCII karşılığı
_ASCII = str.maketrans({
    "ı": "i", "ş": "s", "ğ": "g", "ü": "u", "ö": "o", "ç": "c",
    "â": "a", "î": "i", "û": "u",
})

_BOSLUK = re.compile(r"\s+")


def norm(s: str) -> str:
    """Türkçe duyarlı küçültme + ASCII katlama + boşluk düzleme.

    >>> norm("ARAŞTIRMA GÖREVLİSİ")
    'arastirma gorevlisi'
    >>> norm("Araştırma\\nGörevlisi")
    'arastirma gorevlisi'
    >>> norm("FİZYOTERAPİ VE REHABİLİTASYON")
    'fizyoterapi ve rehabilitasyon'
    >>> norm("Arş. Gör.")
    'ars. gor.'
    """
    s = unicodedata.normalize("NFC", s)
    s = s.translate(_TR)      # İ->i, I->ı  (lower'dan önce!)
    s = s.lower()             # kalan büyükler
    s = s.translate(_ASCII)   # ş->s, ö->o ...
    return _BOSLUK.sub(" ", s).strip()
