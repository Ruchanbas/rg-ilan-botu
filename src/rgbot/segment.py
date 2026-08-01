"""PDF metnini ayrı ilanlara bölme.

Bir Resmî Gazete PDF'inin içinde birden fazla bağımsız ilan olabilir
(doğrulanmış örnek: 20260416-4-11.pdf — aynı üniversitenin hem araştırma
görevlisi hem öğretim üyesi ilanı tek dosyada). Doküman bazında arama
yapılırsa "arş. gör." bir ilandan, "fizyoterapi" öbüründen gelir ve
yanlış alarm doğar. Çözüm: her ilan bir Basın İlan Kurumu koduyla biter
("3795/1-1" gibi), metni bu kodlardan kesiyoruz.
"""

from __future__ import annotations

import re

# Örnekler: 3795/1-1, 12345/2-1
# Tarih (16.04.2026), saat (17:00), kadro sütunları (1 5), madde no (Ek-38)
# gibi kalıplara ÇARPMAMALI — testlerde doğrulanıyor.
ILAN_KODU = re.compile(r"\b\d{3,6}/\d{1,3}-\d{1,3}\b")

# Bundan kısa parçalar ilan değildir (sayfa artığı, boş kuyruk vs.)
_MIN_UZUNLUK = 100


def segmentlere_bol(metin: str) -> list[str]:
    """Metni ilan kodlarından keserek segment listesi döndürür.

    Her segment kendi bitiş kodunu içerir. Koddan sonra kalan kuyruk
    (varsa ve yeterince uzunsa) son segment olarak eklenir — kod
    basılmamış nadir ilanlar kaybolmasın diye.
    """
    parcalar: list[str] = []
    son = 0
    for m in ILAN_KODU.finditer(metin):
        parcalar.append(metin[son:m.end()])
        son = m.end()
    kuyruk = metin[son:]
    if kuyruk.strip():
        parcalar.append(kuyruk)
    return [p for p in parcalar if len(p.strip()) >= _MIN_UZUNLUK]
