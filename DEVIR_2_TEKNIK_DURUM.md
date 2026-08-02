# Teknik Devir — Ne Kurduk, Nasıl Çalışıyor

Bu belge, yeni bir sohbette Claude'a durumu hızlı anlatman için. Kopyala
yapıştır yeter; Claude buradan devam edebilir.

## Tek cümlelik özet

ilan.gov.tr'yi günde 2 kez tarayıp Fizyoterapi ve Rehabilitasyon
araştırma görevlisi ilanı çıkınca WhatsApp'tan haber veren bir sistem
kurduk. Toplama GitHub Actions'ta, işleme/bildirim AWS'de. **Tarama,
eşleştirme ve AWS zinciri çalışıyor ve gerçek veriyle test edildi;
kalan tek iş WhatsApp bağlantısı (Meta hesap yaş kısıtı yüzünden akşama
kaldı, Ecem'in hesabıyla yapılacak).**

## Mimari

```
GitHub Actions (gunde 2 kez: 09:00 ve 18:00 TRT)
  |-- ilan.gov.tr API'sinde "fizyoterapi" + "fizik tedavi" aramasi
  |-- akademik ilanlari on eleme (universite/rektorluk + son 20 gun)
  |-- her adayin detayini cekip eslestirme
  |     (arastirma gorevlisi + fizyoterapi, "Fiziksel Tip" haric)
  |-- sonucu JSON olarak AWS Lambda'ya yolluyor (OIDC ile, statik anahtar yok)
  v
AWS Lambda "rgbot-bildirici"
  |-- DynamoDB: bu ilan daha once gonderildi mi? (mukerrer engelleme)
  |-- WhatsApp'a bildirim
  |-- CloudWatch'a metrik yaziyor
AWS Lambda "rgbot-hatirlatici" (gunluk)
  |-- son basvuruya 3 gun kalanlara hatirlatma
CloudWatch alarmlari -> mail (sistem susarsa / bozulursa haber verir)
```

## Neden bu tuhaf iki parçalı mimari?

Aslında en başta her şeyi Resmî Gazete'den ve tek başına AWS'den yapmayı
planladık. İki büyük engelle karşılaştık:

1. **Resmî Gazete tüm bulut IP'lerini engelliyor** (hem AWS hem GitHub).
   Ev bağlantısından açılıyor, buluttan açılmıyor. Bunu curl ile eş
   zamanlı test edip kanıtladık.

2. Bu yüzden kaynağı **ilan.gov.tr'ye** taşıdık (aynı ilanlar orada da
   var, üstelik düzgün bir JSON API'si var — PDF ayrıştırma derdi bitti).
   ilan.gov.tr bulut IP'lerini engellemiyor ama sertifika zincirinde bir
   eksik vardı, onu da çözdük (aşağıda).

3. Toplama kısmını GitHub Actions'a koyduk ( agir is orada, ucretsiz),
   AWS'yi de durum takibi + bildirim + alarm icin biraktik. Ikisi
   arasindaki guveni **OIDC federasyonu** ile kurduk — GitHub'a statik
   AWS anahtari koymadik, her calisma kisa omurlu kimlik uretiyor.

## Bugün çözdüğümüz üç önemli teknik sorun (portfolyoda anlatılır)

1. **Bulut IP engeli:** Resmî Gazete AWS+GitHub IP'lerini blokluyordu.
   Teşhisi tahminle değil, curl ile eş zamanlı 200-vs-timeout
   karşılaştırmasıyla yaptık. Çözüm: kaynağı ilan.gov.tr'ye taşımak +
   mimariyi toplama/işleme diye bölmek.

2. **OIDC yeni sub formatı:** 15 Temmuz 2026 sonrası açılan GitHub
   depolarında OIDC token'ının "sub" alanı değişmez ID'ler içeriyor
   (repo:sahip@123/depo@456 gibi). AWS'nin standart "repo:sahip/depo:*"
   kalıbı bununla eşleşmiyordu. Token'ın içini bastırıp gerçek formatı
   görüp güven politikasını ona göre yazdık.

3. **Sertifika zinciri:** ilan.gov.tr, "GeoTrust TLS RSA CA G1" ara
   sertifikasını sunmuyor, o yüzden Python doğrulayamıyordu. Eksik
   sertifikayı resmi adresinden indirip zincire ekledik (kodda -k /
   güvenlik kapatma YOK, düzgün çözüm).

## Kod yapısı (src/rgbot/)

- `ilanapi.py` — ilan.gov.tr API istemcisi (sertifika çözümü burada)
- `toplayici.py` — GitHub Actions'ta çalışan tarayıcı (CANLI AKIS)
- `handler.py` — AWS Lambda giriş noktaları (bildirim + hatırlatma)
- `matcher.py` — eşleştirme mantığı (filtreler, KESIN/SUPHELI)
- `normalize.py` — Türkçe metin normalizasyonu (İ/ı tuzağı çözülü)
- `durum.py` — DynamoDB (mükerrer engelleme, hatırlatma takibi)
- `whatsapp.py` — WhatsApp Cloud API gönderimi
- `tarih.py` — son başvuru tarihi çıkarma
- (`fetcher.py`, `pdftext.py`, `segment.py`, `backfill.py` — eski Resmî
  Gazete modülleri, artık kullanılmıyor ama yedek olarak duruyor)

41 test var, hepsi geçiyor. Gerçek API cevabından fixture'lar mevcut.

## Önemli sabitler (akşam lazım olacak)

- **AWS Hesap:** 552883519629
- **Bölge:** eu-central-1 (Frankfurt)
- **GitHub deposu:** Ruchanbas/rg-ilan-botu
- **OIDC Rol ARN:** arn:aws:iam::552883519629:role/rgbot-github-actions
- **GitHub secret:** AWS_ROLE_ARN (kurulu, yukarıdaki ARN'yi içeriyor)
- **Lambda (bildirim):** rgbot-bildirici
- **Lambda (hatırlatma):** rgbot-hatirlatici
- **DynamoDB tablo:** rgbot-ilanlar
- **SSM parametreleri (WhatsApp için doldurulacak):**
  - /rgbot/wa_token (SecureString — kalıcı token)
  - /rgbot/wa_phone_id (Phone number ID)
  - /rgbot/alicilar (JSON dizi, ör: ["905321234567"])

## Şu an kuru modda

`infra/terraform.tfvars` içinde `kuru_calisma = true`. Bu modda sistem
her şeyi yapıyor ama WhatsApp'a mesaj GÖNDERMİYOR, sadece logluyor.
WhatsApp bağlanıp test edilince `false` yapıp `terraform apply`
diyeceğiz.

## Maliyet

Fatura 0,00 dolar. Kullanılan her AWS servisi always-free sınırların
çok altında. S3/VPC/NAT/ECR bilinçli olarak kullanılmadı. Bütçe alarmı
kurulu (1 kuruş bile yansısa mail gelir).

## Bilinen küçük açık noktalar

- Bugün 3 ilan yakalandı, biri (İstanbul Rumeli) elle doğrulandı ve
  gerçekten fizyoterapi arş. gör. içeriyordu. Diğer ikisi (Avrasya,
  İzmir Tınaztepe) SUPHELI etiketliydi, henüz elle bakılmadı — filtrenin
  yanlış alarm oranını görmek için onlara da bakmak iyi olur.
- GitHub 60 gün commit'siz kalan depolarda zamanlanmış işleri durduruyor.
  CloudWatch alarmı bunu yakalar ama iki ayda bir küçük commit iyi olur.
