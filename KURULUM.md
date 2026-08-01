# Kurulum Rehberi — GitHub Actions + AWS

## Neden bu mimari

resmigazete.gov.tr **AWS IP aralıklarını engelliyor**. Lambda'dan
`ConnectTimeout` alıyoruz, GitHub runner'ından ve ev bağlantısından
200 OK dönüyor. Kanıt: aynı anda ev IP'si 0.68 sn'de 200, AWS Frankfurt
20 sn timeout.

Çözüm, sorumlulukları ayırmak:

```
GitHub Actions (günde 2 kez, ücretsiz)
  └─ siteyi tarar, PDF'leri okur, eşleşmeleri bulur
        │  OIDC ile kimlik (statik anahtar YOK)
        ▼
AWS Lambda "rgbot-bildirici"
  ├─ DynamoDB: mükerrer kontrolü
  ├─ WhatsApp: bildirim
  └─ CloudWatch: metrik + alarm

AWS Lambda "rgbot-hatirlatici" (EventBridge, günlük)
  └─ son başvurusuna 3 gün kalanları hatırlatır
```

Yan fayda: Actions durursa metrik gelmez, alarmlar "eksik veri = ihlal"
ayarında olduğu için ateşler. Yani hem site değişikliğini hem de
Actions'ın susmasını aynı alarm yakalar.

---

## Adım 1 — GitHub deposu

1. github.com → **New repository** → ad: `rg-ilan-botu` → **Private**
   (istersen public, kod zaten sır içermiyor) → Create
2. Proje klasöründe Git Bash:

```bash
git init
git add .
git commit -m "Resmi Gazete FTR arastirma gorevlisi ilan botu"
git branch -M main
git remote add origin https://github.com/KULLANICI_ADIN/rg-ilan-botu.git
git push -u origin main
```

`.gitignore` zip'te var: `.venv`, `terraform.exe`, `build/`, `*.tfstate`
gibi şeyler yüklenmez.

---

## Adım 2 — Terraform ayarı

`infra/terraform.tfvars` dosyasını güncelle:

```bash
printf 'alarm_email  = "ruchanbas.priv@gmail.com"\ngithub_repo  = "KULLANICI_ADIN/rg-ilan-botu"\nkuru_calisma = true\n' > infra/terraform.tfvars
cat infra/terraform.tfvars
```

`github_repo` **birebir doğru olmalı** — sadece o depo AWS'ye
bağlanabilecek.

---

## Adım 3 — Altyapıyı güncelle

```bash
cd infra
../terraform apply
```

Plan'da `rgbot-tarayici` silinip `rgbot-bildirici` oluşacak, GitHub OIDC
kaynakları eklenecek. `yes` de.

Bitince çıktıdaki **`github_rol_arn`** değerini kopyala:

```bash
../terraform output github_rol_arn
```

---

## Adım 4 — GitHub'a rol ARN'ini tanıt

1. GitHub'da depona git → **Settings** → **Secrets and variables** →
   **Actions**
2. **New repository secret**
3. Name: `AWS_ROLE_ARN`
4. Secret: 3. adımdaki `arn:aws:iam::...:role/rgbot-github-actions`
5. **Add secret**

---

## Adım 5 — İlk test

1. Depoda **Actions** sekmesi → **Resmî Gazete taraması**
2. **Run workflow** → tarih kutusuna `2026-07-29` yaz → **Run workflow**
3. Çalışmayı aç, adımları izle

Beklenen: "Resmî Gazete'yi tara" adımında `2026-07-29: 17 PDF`, ardından
"Sonucu AWS'ye gönder" adımında `{"tarih": "2026-07-29", "pdf": 17, ...}`

**`pdf: 17` görürsen sistem uçtan uca çalışıyor demektir.**

---

## Adım 6 — WhatsApp

1. `developers.facebook.com` → **My Apps** → **Create App** → **Other**
   → **Business**
2. **WhatsApp** ürününü ekle, **Test Business Account** yeterli
3. **API Setup** ekranında:
   - **Phone number ID**'yi not al (telefon numarası değil, ID)
   - **Manage phone number list** → kendi numaranı ekle, SMS ile doğrula
   - **Ecem'in numarasını şimdi ekleme**, önce sende çalışsın
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
Kadro: {{3}}
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

---

## Adım 7 — Bilgileri AWS'ye yaz

```bash
aws ssm put-parameter --name /rgbot/wa_token --type SecureString \
  --value "BURAYA_TOKEN" --overwrite --region eu-central-1

aws ssm put-parameter --name /rgbot/wa_phone_id --type String \
  --value "BURAYA_PHONE_NUMBER_ID" --overwrite --region eu-central-1

aws ssm put-parameter --name /rgbot/alicilar --type String \
  --value '["905XXXXXXXXX"]' --overwrite --region eu-central-1
```

Numara: başında `+` yok, ülke koduyla → `905321234567`

Sonra: `history -c`

---

## Adım 8 — Kuru modu kapat

```bash
printf 'alarm_email  = "ruchanbas.priv@gmail.com"\ngithub_repo  = "KULLANICI_ADIN/rg-ilan-botu"\nkuru_calisma = false\n' > infra/terraform.tfvars
cd infra && ../terraform apply
```

---

## Adım 9 — Bir hafta gözlem, sonra Ecem

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

`filtre.json` dosyasını düzenle, commit'le, push'la. Ecem'in tezi
bitince öğretim görevlisi ilanlarını da yakalamak için `pozisyon`
listesine `"Öğretim Görevlisi"` ekle. Bu senaryo `test_filtre_json_yukleme`
testiyle zaten kapsanıyor.

---

## Önemli uyarı — GitHub 60 gün kuralı

GitHub, **60 gün commit yapılmayan depolarda zamanlanmış workflow'ları
otomatik durduruyor.** Bot sessizce susar.

İki koruma var:
1. CloudWatch alarmı bunu yakalar (metrik gelmeyince ateşler) → mail
2. İki ayda bir küçük bir commit at, ya da Actions sekmesinden
   "Enable workflow" ile tekrar aç

---

## Maliyet

| Servis | Kullanım | Sınır |
|---|---|---|
| GitHub Actions | ~60 dk/ay | 2000 dk/ay (özel depo), public sınırsız |
| Lambda | ~90 çağrı/ay | 1.000.000 |
| DynamoDB | birkaç yazma/gün | 25 GB |
| CloudWatch alarm | 3 | 10 |
| SNS | birkaç mail/ay | 1.000.000 |

S3 yok, VPC yok, NAT yok, ECR yok. Beklenen fatura: **0,00 dolar.**

---

## Portfolyo notu

Bu proje anlatılırken en değerli kısım şu: veri kaynağı bulut
sağlayıcı IP'lerini engelliyordu, mimari buna göre bölündü — toplama
GitHub runner'larında, durum/bildirim/gözlemlenebilirlik AWS'de,
aradaki güven OIDC federasyonuyla kuruldu (depoda statik AWS anahtarı
yok). Buna ek olarak "sessiz ölüm" alarmı hem kaynak sitedeki değişimi
hem de toplayıcının durmasını yakalıyor.

M�lakatta "neden Lambda'yı VPC'ye koymadın" sorusunun cevabı da hazır:
NAT Gateway ayda ~32 dolar ve bu iş için gereksiz.
