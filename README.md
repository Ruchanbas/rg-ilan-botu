# rg-ilan-botu

Resmî Gazete'de **Fizyoterapi ve Rehabilitasyon araştırma görevlisi** ilanı
yayımlandığında WhatsApp'tan haber veren sistem. Bu repo 1. ve 2. gün işini
kapsıyor: parser + geriye dönük tarama aracı. AWS ve WhatsApp katmanı sonraki
adım (bkz. plan belgesi: `rg-ilan-botu-plan.md`).

## Kurulum

Proje klasöründe:

**Windows (PowerShell):**
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install -e .
python -m pytest            # 25 passed görmelisin
```

**Mac / Linux:**
```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt && pip install -e .
python -m pytest            # 25 passed görmelisin
```

`pip install -e .` paketi kayıt eder; sonrasında `rgbot-backfill` komutu
her klasörden çalışır, PYTHONPATH ayarı gerekmez.

## Ne yapıyor

```
PDF metni ──► segmentlere_bol ──► her segment için eslesir_mi + kesinlik
                (ilan kodundan          (pozisyon + alan aynı ilanda mı,
                 keser: 3795/1-1)        Fiziksel Tıp dışlanır)
```

Kritik tasarım kararı — **segment bazlı arama**: bir PDF'in içinde birden
fazla bağımsız ilan olabiliyor (`tests/fixtures/kmu_20260416.txt` gerçek
örnek: aynı dosyada hem arş.gör. ilanı hem fizyoterapi satırları içeren
öğretim üyesi ilanı). Belge bütününde arasaydık bu dosya yanlış alarm
verirdi; segmentli halde doğru şekilde 0 eşleşme veriyor. İkisi de testte
kanıtlı: `test_segmentasyonsuz_yanlis_alarm_verirdi` /
`test_segmentli_dogru_sonuc_sifir_eslesme`.

## Geriye dönük tarama (2. gün — sıradaki iş)

```bash
rgbot-backfill --baslangic 2025-08-01 --bitis 2026-08-01 --cikti tarama/
```

- İstekler arası 1 sn bekler; ~250 iş günü birkaç saat sürer.
- Kesilirse aynı komutla devam eder (inen PDF'leri atlar).
- Çıktı: `tarama/rapor.csv` (her PDF bir satır) ve `tarama/eslesmeler.jsonl`
  (eşleşen segmentler + tablo satırı detayları).

Bu koşu üç şeyi verir: ilanın gerçek çıkma sıklığı, filtrenin yanlış alarm
oranı, regression testine koyulacak gerçek pozitif örnekler.
`eslesmeler.jsonl`'deki iyi örnekleri `tests/fixtures/` altına kopyalayıp
test yaz — golden set büyüsün.

## Filtre değiştirme (deploy gerektirmez)

`filtre.json`:

```json
{
  "pozisyon": ["Araştırma Görevlisi", "Arş. Gör.", "Arş.Gör.", "Öğretim Görevlisi"],
  "alan": ["Fizyoterapi", "Fizik Tedavi ve Rehabilitasyon"],
  "disla": ["Fiziksel Tıp ve Rehabilitasyon"]
}
```

```bash
RGBOT_FILTRE_JSON=filtre.json rgbot-backfill ...
```

Ecem'in tezi bitince "Öğretim Görevlisi" satırını eklemek yetiyor —
`test_filtre_json_yukleme` bu senaryoyu şimdiden test ediyor. Canlıda aynı
JSON SSM Parameter Store'dan okunacak.

## Neyin doğrulandığı / neyin ilk koşuda doğrulanacağı

Doğrulandı (testli):
- Türkçe normalizasyon (İ/ı tuzağı, satır kırılması, kısaltmalar)
- Segmentasyon: gerçek çift ilanlı belgede 2 doğru segment; kod regex'i
  tarih/saat/sütun/madde numaralarına çarpmıyor
- Eşleştirme: pozitif, iki yönlü negatif, Fiziksel Tıp dışlaması,
  Fizik Tedavi kapsaması, KESIN/SUPHELI ayrımı
- Son başvuru: ilandan okuma + 15 gün fallback

İlk gerçek koşuda doğrulanacak (konteynerden resmigazete.gov.tr'ye ağ
erişimi olmadığı için lokalde koşulmalı):
- `fetcher.py` — fihrist keşfi, cp1254 çözümü, numara yoklama fallback'i
- `pdftext.py` — pdfplumber'ın gerçek RG PDF'lerindeki satır kırma davranışı
  (fixture web tabanlı metin çıkarımından geldi; pdfplumber çıktısı farklı
  kırılabilir, normalizasyon bunu tolere edecek şekilde yazıldı ama gerçek
  veriyle görmek şart)

Önerilen ilk komut (tek gün, ~1 dk):

```bash
rgbot-backfill --baslangic 2026-07-29 --bitis 2026-07-29 --cikti dene/
```

29 Temmuz'da 7 üniversite ilanı vardı — `dene/rapor.csv`'de 17 satır
görmelisin, eşleşme çıkması şart değil.

## Sıradaki adımlar (plandaki 3-5. günler)

1. Backfill sonuçlarına göre filtre ince ayarı
2. Terraform: EventBridge + Lambda (container) + S3 + DynamoDB + SSM + SNS
3. WhatsApp Cloud API: test numarası, kalıcı token, utility template onayı
4. Sessiz ölüm alarmları (SayfaBulundu/PdfSayisi metrikleri)
5. Hatırlatıcı Lambda (son başvuruya 3 gün kala)

## Dizin

```
src/rgbot/
  normalize.py   Türkçe duyarlı normalizasyon (her şeyin temeli)
  segment.py     ilan kodundan bölme
  matcher.py     filtreler + eşleştirme + kesinlik
  tarih.py       son başvuru çıkarımı
  pdftext.py     pdfplumber metin/tablo katmanı
  fetcher.py     fihrist keşfi + indirme (cp1254!)
  backfill.py    geriye dönük tarama CLI
tests/           25 test + gerçek belge fixture'ı
```
