# Telegram Kanalı Kurulumu (WhatsApp'ın yedeği)

Neden: WhatsApp Meta'ya bağımlı (template onayı, hesap askıya alma
riski). Telegram bu kısıtların hiçbirine tabi değil — TCF botundaki gibi
bol emojili, samimi mesaj atıyor. İki kanal paralel çalışır, biri çökse
öbürü devam eder.

## Zaten yapıldı
- BotFather'dan bot oluşturuldu: @ecem_ilan_bot
- Token alındı (GÜVENLİK: eski token sohbete yapıştırıldığı için
  /revoke ile yenilendi — yeni token kullanılacak)

## Adım 1 — Chat ID'leri al

Bot kime mesaj atacak, onların "chat ID"si lazım.

1. Telegram'da @ecem_ilan_bot'a bir "selam" yaz (Ruchan). Bot sana mesaj
   atabilsin diye bu ŞART — bot, kendisiyle konuşmayı başlatmamış
   kimseye mesaj atamaz.
2. Ecem de aynı bota bir "selam" yazsın (ona da gitsin istiyorsak).
3. Tarayıcıda şu adresi aç (YENİ_TOKEN yerine revoke sonrası aldığın
   token'ı koy):
   https://api.telegram.org/botYENI_TOKEN/getUpdates
4. Açılan sayfada her mesaj için "chat":{"id":123456789 gibi bir sayı
   göreceksin. Ruchan'ın ve Ecem'in ID'lerini not al (iki farklı sayı).

## Adım 2 — GitHub secret olarak ekle

GitHub'da depo → Settings → Secrets and variables → Actions →
New repository secret. İKİ secret ekle:

1. Name: TELEGRAM_BOT_TOKEN
   Value: revoke sonrası aldığın yeni token

2. Name: TELEGRAM_CHAT_IDS
   Value: chat ID'ler, virgülle ayrılmış → 123456789,987654321
   (sadece Ruchan için tek ID de olur: 123456789)

Neden GitHub secret (AWS değil): Telegram gönderimi GitHub Actions'ta
çalışıyor (WhatsApp Lambda'da). İki kanal birbirinden bağımsız.

## Adım 3 — Workflow'u güncelle

.github/workflows/tarama.yml dosyasını yeni haliyle değiştir (zip'te
güncel hali var, ya da Claude'dan iste). Yeni workflow:
- Telegram secret'larını taramaya geçiriyor
- Telegram mükerrer durum dosyasını koşular arası saklıyor (cache)

Push et.

## Adım 4 — Test

Actions → ilan taramasi → Run workflow.

"ilan.gov.tr taramasi" adımında artık şunu da göreceksin:
  Telegram: gönderilen=N atlanan=M

Ve @ecem_ilan_bot'tan Telegram'a GERÇEK mesaj gelmeli (kuru mod yok,
Telegram'da template onayı olmadığı için direkt gönderiyor).

**Not — mükerrer:** İlk testte 3 açık ilan varsa 3 mesaj gelir. İkinci
çalıştırmada gelmez (mükerrer engelleme). Yeni test için cache'i
temizlemek gerekirse Claude'a sor.

## Mesaj tonu (TCF botu gibi)

KESIN ilan:
  🎓 Sana göre bir fizyoterapi araştırma görevlisi ilanı çıktı! 🎉
  ... Başarılar, senin için tutuyorum 🍀

SUPHELI ilan (içinde başka kadrolar da varsa):
  🎓 Sana uygun olabilecek bir fizyoterapi ilanı buldum 🌸
  ... Not: Bu ilanda başka kadrolar da var, sana uygun olanı kontrol et 💛

Tonu değiştirmek istersen src/rgbot/telegram.py içindeki
_mesaj_olustur fonksiyonunu düzenle, commit et.

## İki kanal birlikte

Artık her ilan HEM WhatsApp'tan (Meta onaylı, resmî) HEM Telegram'dan
(samimi) gidiyor. WhatsApp henüz kurulmadıysa (template onayı
bekliyorsa) Telegram tek başına çalışır. Telegram kurulmadıysa WhatsApp
tek başına çalışır. Biri olmadan diğeri aksamaz.
