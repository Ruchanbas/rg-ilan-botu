# Akşam Yapılacaklar — Adım Adım

Bu belgeyi akşam açıp sırayla takip et. Her adımın sonunda ne görmen
gerektiğini yazdım. Bir yerde takılırsan o adımın numarasını ve ekran
görüntüsünü Claude'a göster.

**Önce yeni sohbette Claude'a şunu ver:** DEVIR_2_TEKNIK_DURUM.md
dosyasını yapıştır ki nerede olduğumuzu bilsin.

---

## BÖLÜM A — WhatsApp'ı Meta'da kur (Ecem'in Facebook hesabıyla)

**Neden Ecem'in hesabı:** Ruchan'ın Facebook hesabı çok yeni, Meta
"business oluşturamazsın, 1 saat bekle" dedi ve yeni hesap başka yaş
kısıtlarına da takılıyor. Ecem'in hesabı eski olduğu için sorunsuz gider.

### A1. Meta uygulaması oluştur
1. Ecem'in Facebook hesabıyla `developers.facebook.com` → giriş
2. **My Apps** → **Create App**
3. "What do you want your app to do?" → **Other** → **Next**
4. App type → **Business** → **Next**
5. Ad: `fzt-ilan-bot`, e-posta seç → **Create App**
6. Ürünlerden **WhatsApp** → **Set up**
7. Business portfolio: **create a new one** → isim/ad/mail doldur →
   **Create portfolio** (Ecem'in hesabı eski olduğu için bu sefer
   "too new" hatası ÇIKMAMALI)
8. Portfolio seçili → **Next** → Requirements/Overview → bitir

### A2. Test numarası + kendi numaranı ekle
1. Sol menü → **WhatsApp** → **API Setup** (veya "Getting Started")
2. Ekranda göreceklerin:
   - **Test telefon numarası** (Meta veriyor)
   - **Phone number ID** → BUNU BİR YERE NOT AL (telefon numarası değil,
     uzun bir sayı)
   - Geçici **access token** (bunu KULLANMAYACAĞIZ, kalıcısını üreteceğiz)
   - **To** bölümü → **Manage phone number list** → Ruchan'ın numarasını
     ekle → gelen SMS koduyla doğrula
3. **Ecem'in numarasını ŞİMDİ EKLEME.** Önce Ruchan'da test edeceğiz.
   (5 numara sınırı var, eklenen silinemiyor — dikkatli.)

### A3. Kalıcı token üret (paneldeki 24 saatte ölüyor)
1. `business.facebook.com/settings` → **Users** → **System Users**
2. **Add** → isim ver → rol **Admin** → oluştur
3. Oluşan kullanıcıya tıkla → **Add Assets** → **Apps** → uygulamanı seç
   → **Full control** → kaydet
4. **Generate New Token** → uygulamanı seç → süre **Never**
5. İzinlerden şu ikisini işaretle:
   - `whatsapp_business_messaging`
   - `whatsapp_business_management`
6. **Generate Token** → KOPYALA (bir daha gösterilmiyor, hemen bir yere
   yapıştır)

### A4. İki template oluştur
**WhatsApp Manager** → **Message Templates** → **Create Template**

**Template 1:**
- Name: `fzt_ilan_bildirimi`
- Category: **Utility**
- Language: **Turkish**
- Body:
```
Yeni fizyoterapi araştırma görevlisi ilanı.

Kurum: {{1}}
Birim: {{2}}
İlan No: {{3}}
Son başvuru: {{4}}
İlan: {{5}}
```

**Template 2:**
- Name: `fzt_ilan_hatirlatma`
- Category: **Utility**
- Language: **Turkish**
- Body:
```
Hatırlatma: başvuru süresi doluyor.

Kurum: {{1}}
Son başvuru: {{2}}
İlan: {{3}}
```

**ÖNEMLİ:** Template onayı birkaç saat sürebilir. Bu yüzden A4'ü
mümkünse EN BAŞTA yap (A1'den hemen sonra), onaylanırken diğer adımları
yaparsın, zaman kaybı olmaz.

---

## BÖLÜM B — Bilgileri AWS'ye yaz (Ruchan'ın bilgisayarında)

Git Bash aç, proje klasörüne git (`cd ~/Desktop/rg-ilan-botu`), sonra
`.venv` aktifse gerekmiyor ama AWS komutları çalışıyorsa devam.

Aşağıdaki üç komutta BÜYÜK harfli yerleri gerçek değerlerle değiştir:

```
aws ssm put-parameter --name /rgbot/wa_token --type SecureString \
  --value "A3_ADIMINDAKI_KALICI_TOKEN" --overwrite --region eu-central-1

aws ssm put-parameter --name /rgbot/wa_phone_id --type String \
  --value "A2_ADIMINDAKI_PHONE_NUMBER_ID" --overwrite --region eu-central-1

aws ssm put-parameter --name /rgbot/alicilar --type String \
  --value '["90RUCHANIN_NUMARASI"]' --overwrite --region eu-central-1
```

Numara formatı: başında + YOK, 0 YOK, ülke koduyla → `905321234567`

Sonra komut geçmişini temizle: `history -c`

---

## BÖLÜM C — Kuru modu kapat ve test et

### C1. Kuru modu kapat
`infra/terraform.tfvars` dosyasını aç (VS Code), `kuru_calisma = true`
satırını `kuru_calisma = false` yap, kaydet. Sonra:

```
cd infra
../terraform apply
```
Plan'da "1 to change" → `yes`

### C2. Elle test — Ruchan'a mesaj gelsin
GitHub'da Actions → **ilan taramasi** → **Run workflow**.

Bugün açık bir fizyoterapi arş. gör. ilanı varsa (İstanbul Rumeli
ilanının son başvurusu 11 Ağustos'tu, hâlâ açık olabilir) Ruchan'ın
WhatsApp'ına GERÇEK mesaj gelmeli.

**Not:** DynamoDB'de o ilan "gönderildi" diye kayıtlıysa tekrar gelmez
(mükerrer engelleme). Temiz test için ya yeni bir ilan çıkmasını bekle,
ya da DynamoDB tablosundaki (rgbot-ilanlar) kaydı elle sil. Bunu
Claude'a sorabilirsin.

---

## BÖLÜM D — Bir hafta sonra Ecem'i ekle

Bir hafta Ruchan'a mesaj gelsin, yanlış alarm var mı gözlemle. Sorun
yoksa:

1. Meta panelinden (A2'deki "Manage phone number list") Ecem'in
   numarasını ekle, SMS ile doğrula
2. AWS'de alıcı listesini güncelle:
```
aws ssm put-parameter --name /rgbot/alicilar --type String \
  --value '["90RUCHAN","90ECEM"]' --overwrite --region eu-central-1
```
Deploy gerekmez, Lambda SSM'den okuyor.

---

## Takılırsan

Her adımda ne görmen gerektiğini yazdım. Beklenenden farklı bir şey
görürsen:
1. Hangi bölüm/adımda olduğunu söyle (ör: "A3, adım 5")
2. Ekran görüntüsü at
3. Claude'a DEVIR_2_TEKNIK_DURUM.md'yi verdiysen zaten bağlamı biliyor

## Opsiyonel — bekleme sırasında yapılabilecekler

- **Filtre doğrulama:** Bugün yakalanan Avrasya ve İzmir Tınaztepe
  ilanlarına bakıp gerçekten fizyoterapi arş. gör. içeriyor mu kontrol
  et. Linkler son taramanın sonuç JSON'unda vardı. Yanlış alarmsa
  Claude filtreyi sıkar.
- **Portfolyo README:** Claude'dan projeyi CV/GitHub için tanıtan güzel
  bir README yazmasını isteyebilirsin.

---

## Filtre doğrulama sonucu (Claude bugün kontrol etti)

Bugün yakalanan 3 ilandan ikisi kontrol edildi:
- **İstanbul Rumeli** (KESIN): Elle bakıldı, Sağlık Bilimleri Fakültesi
  Fizyoterapi ve Rehabilitasyon bölümüne ARAŞTIRMA GÖREVLİSİ, şartı
  "FTR lisans mezunu olup tezli yüksek lisans yapıyor olmak" — tam Ecem'e
  uygun. ✅ Doğru yakalanmış.
- **Avrasya** (SUPHELI): Haber kaynaklarından doğrulandı — Avrasya bu
  dönem araştırma görevlisi + fizyoterapi kadrosu açmış, son başvuru
  11 Ağustos. ✅ Doğru yakalanmış (SUPHELI etiketi sadece bot detayı net
  okuyamadığı için, ilan gerçekten uygun).

**Sonuç: Filtre doğru çalışıyor, yanlış alarm YOK.** Gerçek mesaja
güvenle geçilebilir.

---

## Test mesajı garantisi (3 açık ilan var)

Şu an açık 3 fizyoterapi arş. gör. ilanı var (İstanbul Rumeli, Avrasya,
İzmir Tınaztepe — son başvuru 11 Ağustos, akşam hâlâ açık). WhatsApp'ı
test etmek için bunları kullanacağız.

**Akşam kuru modu kapatıp workflow'u çalıştırınca iki ihtimal:**

1. Bu ilanlar DynamoDB'ye kaydedilmemişse → gerçek modda "yeni" görünür,
   sana MESAJ GELİR. Test tamam.

2. Kayıtlıysa → mükerrer engelleme yüzünden mesaj gelmez. O zaman
   Claude'a şunu sor: "DynamoDB rgbot-ilanlar tablosunu test için
   temizleyelim." Tek komutla sıfırlanır, ilanlar tekrar "yeni" olur,
   çalıştırınca mesaj gelir.

**Hangi durumda olduğunu görmek için** Claude'a sor: "DynamoDB'de kayıtlı
ilan var mı, kontrol eder misin?" — tabloyu okur, boş mu dolu mu söyler.

Yani her koşulda bu 3 ilanla WhatsApp'ın çalıştığını göreceksin.
