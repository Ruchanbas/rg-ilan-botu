"""Lambda layer paketleyici.

Neden ayrı bir script: Lambda Linux'ta çalışıyor, sen Windows'tasın.
Normal `pip install` Windows'a özel dosyalar indirir ve Lambda'da
patlar. Bu script pip'e "bana Linux/x86_64 için derlenmiş sürümleri
indir" diyor (--platform manylinux2014_x86_64 --only-binary=:all:),
böylece Docker'a gerek kalmıyor.

Kullanım (proje kökünden):
    python infra/layer_yap.py

Çıktı: infra/build/layer.zip
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

KOK = Path(__file__).resolve().parent
BUILD = KOK / "build"
HEDEF = BUILD / "python"          # Lambda layer'da bu klasör adı zorunlu
ZIP = BUILD / "layer.zip"

PAKETLER = [
    "requests>=2.31",
    "beautifulsoup4>=4.12",
    "pdfplumber>=0.11",
]

# Lambda python3.12 çalışma zamanı boto3'ü zaten içerir, eklemiyoruz.
PLATFORM = "manylinux2014_x86_64"
PY_SURUM = "3.12"


def main() -> None:
    if HEDEF.exists():
        shutil.rmtree(HEDEF)
    HEDEF.mkdir(parents=True, exist_ok=True)

    komut = [
        sys.executable, "-m", "pip", "install",
        "--platform", PLATFORM,
        "--target", str(HEDEF),
        "--implementation", "cp",
        "--python-version", PY_SURUM,
        "--only-binary=:all:",
        "--upgrade",
        *PAKETLER,
    ]
    print("Bağımlılıklar indiriliyor (Linux uyumlu)...")
    subprocess.run(komut, check=True)

    # Gereksiz dosyaları at — layer 250 MB sınırına yaklaşmasın
    for desen in ("**/__pycache__", "**/*.dist-info", "**/tests"):
        for yol in HEDEF.glob(desen):
            if yol.is_dir():
                shutil.rmtree(yol, ignore_errors=True)

    if ZIP.exists():
        ZIP.unlink()
    print("Zipleniyor...")
    with zipfile.ZipFile(ZIP, "w", zipfile.ZIP_DEFLATED) as z:
        for dosya in HEDEF.rglob("*"):
            if dosya.is_file():
                z.write(dosya, dosya.relative_to(BUILD))

    mb = ZIP.stat().st_size / 1_048_576
    print(f"Hazır: {ZIP}  ({mb:.1f} MB)")
    if mb > 45:
        print("UYARI: 50 MB'ı aşarsa doğrudan yükleme başarısız olur.")


if __name__ == "__main__":
    main()
