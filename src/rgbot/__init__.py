"""rgbot — Resmî Gazete FTR araştırma görevlisi ilan takibi."""

from .matcher import Filtreler, eslesir_mi, kesinlik
from .normalize import norm
from .segment import segmentlere_bol
from .tarih import son_basvuru

__version__ = "0.1.0"
__all__ = ["norm", "segmentlere_bol", "eslesir_mi", "kesinlik",
           "son_basvuru", "Filtreler"]
