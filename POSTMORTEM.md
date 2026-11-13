# Postmortem: ilan.gov.tr erişim kesintisi ve botun kapatılması

Durum: kapatıldı, 12 Kasım 2026. Bütün saatler UTC'dir. Satır numaraları [`acd5150`](https://github.com/Ruchanbas/rg-ilan-botu/commit/acd5150afce0a6d00df7cacae2a8748f7f715893) commit'ine göredir. Actions logları GitHub'da 90 gün saklandığı için aşağıdaki run linkleri bir süre sonra açılmayacaktır.

## Özet

24 Eylül 2026'da ilan.gov.tr'nin arama servisi, GitHub Actions'tan gelen isteklere 403 dönmeye başladı. Toplayıcı bu hatayı loglayıp boş bir sonuç ürettiği için 46 gün boyunca bütün zamanlanmış çalışmalar başarılı (yeşil) göründü ve hiçbir ilan toplanmadı. Bu durumu yakalamak için kurulan CloudWatch alarmı, planlı sessiz mod nedeniyle metrik alamıyordu ve bu yüzden kesintiyi ayırt edemedi. Kesinti 9 Kasım'da fark edildi. Kaynak erişimi bilerek kapattığı ve kurum izin vermediği için bot geri açılmadı, kapatıldı.

## Etki

- **Süre:** İlk 403, 24 Eylül 07:16'da görüldü ([run #572](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/35968738531)). Kesinti 9 Kasım'da fark edildi (46 gün) [DOĞRULA: fark edilme anının kaydı yok, geliştiricinin beyanı]. Workflow'lar 12 Kasım'da kapatıldı.
- **Etkilenen çalışmalar:** 24 Eylül 07:16 ile 9 Kasım sonu arasında 214 zamanlanmış çalışma başarılı bitti. Bunların hepsinin logunda iki arama terimi için de 403 var. Aynı aralıkta 1 çalışma başka bir adımda hata verdi ([run #679](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/39043398300), "Eksik ara sertifikayi ekle" adımı), 1 çalışma da iptal edildi ([run #748](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/41123228208)) [DOĞRULA: iptal nedeni]. 12 Kasım'a kadar sayılınca toplam 222 zamanlanmış ve 1 elle tetiklenmiş çalışma başarılı göründü. Bu çalışmaların hiçbiri veri çekemedi.
- **Kullanıcı:** Botun tek kullanıcısı vardı. 28 Ağustos'tan 9 Kasım'a kadar sessiz mod açıktı ve bu sürede zaten bildirim gönderilmiyordu, eşleşmeler yalnızca arşive yazılıyordu. Arşive eklenen son kayıt 22 Eylül tarihli ([`c640fc4`](https://github.com/Ruchanbas/rg-ilan-botu/commit/c640fc49ffff28b4c411efd1bbfac167a91d1a7e)). Arşivde toplam 16 kayıt var.
- **Kaçan ilan:** Bilmiyoruz. Kesinti boyunca arama hiç sonuç döndürmediği için bu sürede eşleşen bir ilan yayımlanıp yayımlanmadığını sistemin kendi kayıtlarından çıkarmak mümkün değil. Bu dönem elle de kontrol edilmedi [DOĞRULA].

## Zaman çizelgesi

| Tarih (UTC) | Olay | Kanıt |
| --- | --- | --- |
| 2026-08-01 21:22 | İlk commit: toplama GitHub Actions'ta, bildirim, durum ve metrik AWS Lambda'da, kaynak resmigazete.gov.tr | [`6a3f7b8`](https://github.com/Ruchanbas/rg-ilan-botu/commit/6a3f7b80d51d9f87dd3390ba40ea8f46ca8b472a) |
| 2026-08-01 22:26 | Kaynak ilan.gov.tr arama API'sine taşındı | [`120ecfa`](https://github.com/Ruchanbas/rg-ilan-botu/commit/120ecfaa6ce74349c3b790bf82793447cd7372c1) |
| 2026-08-01 23:27 | GitHub'dan AWS'ye OIDC ile erişim (statik anahtar yok) | [`39507ff`](https://github.com/Ruchanbas/rg-ilan-botu/commit/39507ff00e83b10b2e4860f8913a7ba8578a0e14) |
| 2026-08-02 21:16 | Telegram bildirim kanalı eklendi | [`fbda768`](https://github.com/Ruchanbas/rg-ilan-botu/commit/fbda7685aa305668c52552e3bdeff0722c1398ab) |
| 2026-08-08 06:38 | Tarama sıklığı günde 2'den saatte 1'e çıkarıldı | [`b6a27b3`](https://github.com/Ruchanbas/rg-ilan-botu/commit/b6a27b3a508e5977ae7a3df8ec20795cf9fb4a08) |
| 2026-08-28 08:46 | Sessiz mod eklendi (1 Aralık'a kadar): bildirim yok, AWS adımı atlanıyor, eşleşmeler arşive yazılıyor | [`1205334`](https://github.com/Ruchanbas/rg-ilan-botu/commit/1205334e1b4acb565eb4ad4357dedc56f486736c) |
| 2026-09-22 09:04 | Arşive eklenen son kayıt | [`c640fc4`](https://github.com/Ruchanbas/rg-ilan-botu/commit/c640fc49ffff28b4c411efd1bbfac167a91d1a7e) |
| 2026-09-24 01:08 | Son başarılı sorgu: iki terim için `numFound=9`, 5 eşleşme | [run #571](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/35941571581) |
| 2026-09-24 07:16 | İlk 403: `AdsByFilter` iki terim için de 403 dönüyor, ana sayfa 200 dönüyor, çalışma yeşil | [run #572](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/35968738531) |
| 2026-11-09 15:46 | Sessiz modun bitiş tarihi 9 Kasım'a çekildi | [`d434dec`](https://github.com/Ruchanbas/rg-ilan-botu/commit/d434decd87bbc2c348d73fff82b857fb8bd0be46) |
| 2026-11-09 16:00 | Arşiv gönderim aracındaki tarih filtresi hatası düzeltildi (kuru çalıştırmada bulundu) | [PR #1](https://github.com/Ruchanbas/rg-ilan-botu/pull/1) |
| 2026-11-09 16:15 | Sessiz moddan sonraki ilk AWS çağrısı: Lambda `sayfa_bulundu=false`, `pdf_sayisi=0` aldı ve 200 döndü | [run #787](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/42652877556) |
| 2026-11-09 | Kesinti fark edildi | [DOĞRULA] |
| [DOĞRULA: tarih] | Basın İlan Kurumu'ndan izin istendi. Kurum, portal içeriğinin izinsiz işlenemeyeceğini ve özel entegrasyon yapılamayacağını yazılı olarak bildirdi | e-posta (yayımlanmadı) |
| 2026-11-12 | Üç workflow da GitHub'da devre dışı bırakıldı. YAML dosyaları değiştirilmedi | Actions ayarları |

## Kök neden

ilan.gov.tr'nin arama uç noktası (`/api/api/services/app/Ad/AdsByFilter`), 24 Eylül 07:16'dan itibaren GitHub Actions runner'larından gelen isteklere `403 Forbidden` dönmeye başladı. Aynı çalışmada sitenin ana sayfası 200 döndü ([tarama.yml:42](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/.github/workflows/tarama.yml#L42)). Erişim yalnızca bu uç noktada kesildi ve sonradan hiç geri gelmedi: 572 numaralı çalışmadan sonraki hiçbir çalışmada başarılı sorgu yok. Engelin yalnızca runner IP'lerine mi, yoksa bütün otomatik erişime mi uygulandığı test edilmedi [DOĞRULA].

## Neden 6 hafta fark edilmedi

Sistemde "sessizlik" üç farklı şey anlamına gelebiliyordu: o gün ilan yoktu, sessiz mod açıktı ya da kaynağa ulaşılamadı. Çıktılarda bu üç durum birbirinden ayırt edilemiyordu.

**1. Hata yutuluyordu.** [toplayici.py:100-106](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/toplayici.py#L100-L106) satırlarında her arama terimi kendi `try/except Exception` bloğu içinde çağrılıyor. Hata olunca yalnızca `print` yapılıp `continue` ile devam ediliyor. İki terim de başarısız olunca `tara()` geçerli görünen bir sonuç döndürüyor (`sayfa_bulundu: false`, `pdf_sayisi: 0`, `eslesmeler: []`). [toplayici.py:165-168](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/toplayici.py#L165-L168) bu sonucu dosyaya yazıp sıfır çıkış koduyla bitiriyor. Workflow'da `sayfa_bulundu` değerini kontrol eden bir adım yok, bu yüzden çalışma yeşil kalıyordu. Bunun yanında [ilanapi.py:57-67](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/ilanapi.py#L57-L67) 403'ü de geçici hata gibi üç kez yeniden deniyordu.

**2. Sağlık kontrolü yanlış uç noktayı ölçüyordu.** [tarama.yml:42](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/.github/workflows/tarama.yml#L42) sitenin ana sayfasına istek atıp durum kodunu yalnızca yazdırıyordu. Kesinti boyunca ana sayfa 200 döndü, kullanılan arama uç noktası ise 403 döndü. Bu kontrol, durum kodu 200 dışında bir şey olsaydı bile çalışmayı durdurmayacaktı.

**3. Alarm, planlı sessizliği arızadan ayıramıyordu.** Bu senaryo için iki alarm tanımlıydı ([main.tf:279-309](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/infra/main.tf#L279-L309)): `SayfaBulundu` metriği 3 gün üst üste 1'in altında kalırsa ve `PdfSayisi` metriği 7 gün üst üste 1'in altında kalırsa. İkisinde de eksik veri ihlal sayılıyordu (`treat_missing_data = "breaching"`). Ancak bu metrikleri yalnızca bildirim Lambda'sı yazıyordu ([handler.py:63-65](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/handler.py#L63-L65)). Lambda'yı çağıran adım da sessiz modda atlanıyordu ([tarama.yml:80-94](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/.github/workflows/tarama.yml#L80-L94)). Sonuç olarak:

- 28 Ağustos'tan itibaren hiç metrik gitmedi. Yapılandırmaya göre iki alarm da kesintiden haftalar önce, yaklaşık 31 Ağustos ve 4 Eylül'de, alarm durumuna geçmiş olmalı [DOĞRULA: alarmların main.tf'teki haliyle kurulu olduğu, SNS e-posta aboneliğinin onaylandığı ve bu tarihlerde alarm e-postası gelip gelmediği].
- CloudWatch yalnızca durum değiştiğinde bildirim gönderir. Zaten alarm durumunda olan bir alarm, 24 Eylül'de gerçek arıza başladığında yeni bir bildirim üretmez.
- 9 Kasım'da metrikler yeniden gelmeye başladığında değerler sıfırdı ([run #787](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/42652877556)). Alarm yine durum değiştirmedi.
- Üçüncü alarm ([main.tf:265-277](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/infra/main.tf#L265-L277)) Lambda hatalarını ölçüyordu. Lambda çağrılmadığı için hata da üretmedi.

Kısacası: önceden beklenen bir alarm, hiç alarm olmamasıyla aynı sonucu verdi.

**4. Bildirimlerin gelmemesi bir işaret değildi.** Sessiz modda zaten hiç mesaj beklenmiyordu. Bu yüzden 46 gün boyunca hiç mesaj gelmemesi, kullanıcı tarafında da bir şeylerin ters gittiğini göstermedi.

## Neden engeli aşmadım

403 geçici bir hata değildi. Ana sayfa açıkken yalnızca veri uç noktası kapanmıştı ve erişim bir daha geri gelmedi. Basın İlan Kurumu'na izin ve resmi bir erişim yolu olup olmadığını sordum. Kurum yazılı cevabında, İlan Portalı Yönetmeliği ve portalın kullanım koşulları gereği içeriğin izinsiz kopyalanmasına, derlenmesine ve işlenmesine izin verilmediğini, özel bir entegrasyonla veri paylaşımının da mümkün olmadığını bildirdi. Bu yüzden 403'ten sonra erişimi geri kazanmaya yönelik hiçbir değişiklik yapılmadı ve bot kapatıldı.

İki konuyu açıkça kaydediyorum. Birincisi, kullanılan arama API'si resmi olarak yayımlanmış bir API değildi. Uç noktalar sitenin kendi arayüzü incelenerek bulunmuştu ([kesif.yml](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/.github/workflows/kesif.yml), [ilanapi.py:1-16](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/ilanapi.py#L1-L16)). İkincisi, istemci ilk sürümden beri bir masaüstü tarayıcısının User-Agent değerini gönderiyordu ([ilanapi.py:30-32](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/ilanapi.py#L30-L32)). Kullanım koşulları kod yazılmadan önce kontrol edilmedi.

## Ne iyi gitti

- **Statik AWS anahtarı yoktu.** GitHub Actions, AWS'ye OIDC ile kısa ömürlü kimlikle bağlanıyordu ([main.tf:324-367](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/infra/main.tf#L324-L367)). Repo secret'larında AWS ile ilgili tek değer rol ARN'i; erişim anahtarı yok.
- **Kuru çalıştırma bir hatayı mesaj gitmeden yakaladı.** Arşiv gönderim workflow'u varsayılan olarak kuru çalışıyor ([arsiv-gonder.yml:9-12](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/.github/workflows/arsiv-gonder.yml#L9-L12)). 9 Kasım'daki kuru çalıştırma "gönderilecek kayıt yok" sonucunu verdi. Hata [PR #1](https://github.com/Ruchanbas/rg-ilan-botu/pull/1) ile düzeltildi ve sonraki kuru çalıştırma 16 kaydın tamamını listeledi. Bu sırada kullanıcıya hiç mesaj gitmedi.
- **Ham çıktılar saklanıyordu.** Her çalışmanın logu ve `sonuc.json` çıktısı ([tarama.yml:96-105](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/.github/workflows/tarama.yml#L96-L105)) saklandığı için bu zaman çizelgesi tahmine dayanmadan, kayıtlardan çıkarılabildi.

## Dersler ve sonraki sürüme taşınanlar

1. **Kaynak çağrısı başarısız olursa çalışma kırmızı bitmeli.** "Veri çekilemedi" durumu, "veri boş geldi" durumundan ayrı bir sonuç olmalı ve sıfır olmayan bir çıkış koduyla bitmeli.
2. **Çekilen ilan sayısı her çalışmada metrik olarak yazılmalı.** Art arda N gün sıfır gelirse alarm üretmeli.
3. **İzleme, bildirim modundan bağımsız olmalı.** Bildirimleri susturmak metrikleri ve alarmları susturmamalı. Önceden kırmızı olması beklenen bir alarm, alarm değildir.
4. **Her kaynak için ayrı sağlık kontrolü olmalı.** Bu kontrol, sitenin ana sayfasını değil, gerçekten kullanılan uç noktayı ölçmeli.
5. **4xx hatalar yeniden denenmemeli.** Yalnızca geçici hatalar (zaman aşımı, 5xx) yeniden denenmeli.
6. **Kaynak değiştirilebilir bir arayüz olmalı.** Toplama, eşleştirme ve bildirim, tek bir kaynağın veri şekline bağlı olmamalı.
7. **Kod yazmadan önce veri kaynağının kullanım şartları kontrol edilmeli.** İstemci de kendini olduğu gibi tanıtmalı.

## Mimari geçmiş

| Dönem | Toplama nerede | Kaynak | Neden değişti | Kanıt |
| --- | --- | --- | --- | --- |
| Repo öncesi [DOĞRULA: tarih] | AWS Lambda | resmigazete.gov.tr | Lambda'dan `ConnectTimeout`: site AWS IP aralıklarını engelliyordu | [handler.py:3-5](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/handler.py#L3-L5) (kod yorumu) |
| 1 Ağu 21:22 – 22:26 | GitHub Actions; bildirim, durum ve metrik Lambda'da | resmigazete.gov.tr | Runner'lardan da erişilemedi [DOĞRULA: bu tarihlerin Actions logları silinmiş durumda] | [`6a3f7b8`](https://github.com/Ruchanbas/rg-ilan-botu/commit/6a3f7b80d51d9f87dd3390ba40ea8f46ca8b472a), [toplayici.py:3-6](https://github.com/Ruchanbas/rg-ilan-botu/blob/acd5150afce0a6d00df7cacae2a8748f7f715893/src/rgbot/toplayici.py#L3-L6) (kod yorumu) |
| 1 Ağu 22:26 – 24 Eyl 07:16 | GitHub Actions; Lambda + Telegram | ilan.gov.tr arama API'si | 403; kurum izin vermedi | [`120ecfa`](https://github.com/Ruchanbas/rg-ilan-botu/commit/120ecfaa6ce74349c3b790bf82793447cd7372c1), [run #572](https://github.com/Ruchanbas/rg-ilan-botu/actions/runs/35968738531) |

Bundan sonraki adım ayrı bir proje olacak: Java/Spring ile yazılacak ve veri kaynağını değiştirilebilir bir bileşen olarak ele alacak. Bu repo o proje için şartname görevi görüyor. Eşleştirme kuralları, Türkçe metin normalizasyonu, testler ve yukarıdaki dersler oraya taşınacak.
