# Kurulum Rehberi — GitHub Actions + AWS (kaynak: ilan.gov.tr)

## Mimari ve neden böyle

resmigazete.gov.tr hem AWS hem GitHub/Azure IP'lerini engelliyor —
Lambda'dan da runner'dan da bağlantı zaman aşımına uğruyor, ev IP'sinden
200 dönüyor. Kaynak bu yüzden, aynı ilanları yayımlayan Basın İlan Kurumu
portalı **ilan.gov.tr'nin JSON API'sine** taşındı. Actions'tan erişim
canlı doğrulandı ve PDF ayrıştırma derdi tamamen kalktı.

Akış: GitHub Actions günde iki kez (09:00 ve 18:00 TRT) ilan.gov.tr
API'sinde "fizyoterapi" araması yapar, akademik ilanları ön eler,
detaylarını çekip eşleştiriciden geçirir (araştırma görevlisi +
fizyoterapi, "Fiziksel Tıp" hariç), sonucu OIDC ile (depoda statik AWS
anahtarı yok) `rgbot-bildirici` Lambda'sına gönderir. Lambda DynamoDB'de
mükerrer kontrolü yapar, WhatsApp'a bildirir, CloudWatch metrikleri
yazar. `rgbot-hatirlatici` son başvuruya 3 gün kala hatırlatır.

API ayrıntıları (keşifle doğrulandı): POST
`www.ilan.gov.tr/api/api/services/app/Ad/AdsByFilter` (çift "api" bilinçli),
gövde `{"keys":{"q":["fizyoterapi"]},"skipCount":0,"maxResultCount":100}`
— `q` dizi olmak zorunda. Detay: `AdDetail/GetAdDetail?id=..&isKiwiAd=false`.

Not: ilan.gov.tr robots.txt ile otomatik erişimi kısıtlıyor. Günde 2
koşu, 2 arama, en fazla 20 detay isteği düzeyindeki kişisel kullanım
orantılı kabul edildi. Nezakete dikkat: sorgu sayısını artırma,
sıklaştırma.

## AWS tarafında değişiklik gerekmiyor

Payload şeması korundu; daha önce `terraform apply` ile kurduğun her şey
aynen çalışıyor. Metriklerden `PdfSayisi` artık "sorguların toplam
numFound'u" anlamına geliyor (isim tarihsel, alarm tanımları bozulmasın
diye korundu) — API şekli bozulursa sıfıra düşer ve sessiz ölüm alarmı
çalar.

---

## Adım 1 — Kodu güncelle ve push et

Yeni zip'i mevcut klasörün üstüne açtıktan sonra:

```bash
git add .
git commit -m "Kaynak ilan.gov.tr API'sine tasindi"
git push
```

## Adım 2 — İlk test

1. Depoda **Actions** sekmesi → **ilan taramasi**
2. **Run workflow** → **Run workflow** (parametre yok)
3. Çalışmayı aç, adımları izle

Beklenen: "ilan.gov.tr taramasi" adımında `'fizyoterapi': numFound=...`
satırları ve aday/eşleşme sayıları; "Sonucu AWS'ye gönder" adımında
`{"tarih": ..., "gonderilen": N, "atlanan": M}`.

**numFound > 0 ve Lambda cevabı geldiyse sistem uçtan uca çalışıyor.**
Eşleşme 0 olabilir — o an açık FTR araştırma görevlisi ilanı yok
demektir. İlk koşuda son 20 günün aktif ilanları taranır; halihazırda
açık başvuru varsa ilk mesajlar bu koşuda düşer.

Bu noktada `kuru_calisma = true` olduğu için mesaj GİTMEZ, sadece
loglanır. WhatsApp'ı bağlayınca gerçek mesaja geçeceğiz.

## Adım 3 — WhatsApp

1. `developers.facebook.com` → **My Apps** → **Create App** → **Other**
   → **Business**
2. **WhatsApp** ürününü ekle, **Test Business Account** yeterli
3. **API Setup** ekranında:
   - **Phone number ID**'yi not al (telefon numarası değil, ID)
   - **Manage phone number list** → kendi numaranı ekle, SMS ile doğrula
   - Ecem'in numarasını şimdi ekleme; önce sende çalışsın
   - 5 numara sınırı var, eklendikten sonra silinemiyor

### Kalıcı token

Paneldeki token 24 saatte ölüyor:

1. `business.facebook.com/settings` → **Users** → **System Users** →
   **Add** → rol **Admin**
2. Kullanıcıya tıkla → **Add Assets** → **Apps** → uygulaman →
   **Full control**
3. **Generate New Token** → uygulaman → süre **Never**
4. İzinler: `whatsapp_business_messaging` ve `whatsapp_business_management`
5. **Generate Token** → kopyala, bir daha gösterilmiyor

### Template'ler

**WhatsApp Manager** → **Message Templates** → **Create Template**

**1)** Name `fzt_ilan_bildirimi`, Category **Utility**, Language **Turkish**

```
Yeni fizyoterapi araştırma görevlisi ilanı.

Kurum: {{1}}
Birim: {{2}}
İlan No: {{3}}
Son başvuru: {{4}}
İlan: {{5}}
```

**2)** Name `fzt_ilan_hatirlatma`, Category **Utility**, Language **Turkish**

```
Hatırlatma: başvuru süresi doluyor.

Kurum: {{1}}
Son başvuru: {{2}}
İlan: {{3}}
```

## Adım 4 — Bilgileri AWS'ye yaz

```bash
aws ssm put-parameter --name /rgbot/wa_token --type SecureString \
  --value "BURAYA_TOKEN" --overwrite --region eu-central-1

aws ssm put-parameter --name /rgbot/wa_phone_id --type String \
  --value "BURAYA_PHONE_NUMBER_ID" --overwrite --region eu-central-1

aws ssm put-parameter --name /rgbot/alicilar --type String \
  --value '["905XXXXXXXXX"]' --overwrite --region eu-central-1
```

Numara: başında `+` yok, ülke koduyla → `905321234567`. Sonra: `history -c`

## Adım 5 — Kuru modu kapat

`infra/terraform.tfvars` içinde `kuru_calisma = false` yap, sonra:

```bash
cd infra && ../terraform apply
```

## Adım 6 — Bir hafta gözlem, sonra Ecem

Sistem her gün 09:00 ve 18:00'de kendi çalışır. Bir hafta sadece sana
mesaj gelsin, yanlış alarm var mı gör. Sonra Meta panelinden Ecem'in
numarasını ekleyip:

```bash
aws ssm put-parameter --name /rgbot/alicilar --type String \
  --value '["905XXXXXXXXX","905YYYYYYYYY"]' --overwrite --region eu-central-1
```

Deploy gerekmez, Lambda SSM'den okuyor.

---

## Filtre değiştirme

`filtre.json`'u düzenle, commit'le, push'la. Alanlar:
- `arama`: ilan.gov.tr'ye gönderilen arama terimleri (ham Türkçe)
- `pozisyon` / `alan` / `disla`: detay metninde eşleştirme (normalize edilir)

Ecem'in tezi bitince öğretim görevlisi ilanlarını da yakalamak için
`pozisyon` listesine `"Öğretim Görevlisi"` ekle. Bu senaryo
`test_filtre_json_yukleme` testiyle kapsanıyor.

---

## GitHub 60 gün kuralı

GitHub, 60 gün commit yapılmayan depolarda zamanlanmış workflow'ları
otomatik durduruyor. İki koruma: (1) CloudWatch alarmı metrik gelmeyince
ateşler → mail, (2) iki ayda bir küçük bir commit at ya da Actions'tan
"Enable workflow" ile tekrar aç.

---

## Maliyet

| Servis | Kullanım | Sınır |
|---|---|---|
| GitHub Actions | ~60 dk/ay | 2000 dk/ay (özel depo) |
| Lambda | ~90 çağrı/ay | 1.000.000 |
| DynamoDB | birkaç yazma/gün | 25 GB |
| CloudWatch alarm | 3 | 10 |
| SNS | birkaç mail/ay | 1.000.000 |

S3 yok, VPC yok, NAT yok, ECR yok. Beklenen fatura: **0,00 dolar.**

---

## Portfolyo notu

En değerli kısım kısıtla mücadele: birincil kaynak (Resmî Gazete) tüm
bulut IP'lerini engelledi; teşhis kanıta dayandırıldı (curl ile eş
zamanlı 200 ve timeout karşılaştırması), mimari toplama/işleme diye ikiye
bölündü, sonra kaynak aynı verinin sunulduğu bir JSON API'sine taşınarak
sistem hem çalışır hale getirildi hem sadeleşti. Aradaki güven OIDC
federasyonuyla kuruldu (statik anahtar yok), sessiz ölüm alarmı hem
kaynaktaki değişimi hem toplayıcının durmasını yakalıyor.
