# Telegram komutları ve süreli işlemler — DEV 0.4

## Bağlanma

Önce İstemciler, Envanter ve Ayarlar sekmelerindeki oyun ayarlarını tamamlayın.
Telegram sekmesinde token ve kendi **özel sohbet kimliğinizi** girin; bağlantıyı
kontrol edin. **Uzaktan kontrolü aç** düğmesine basın. Hazır mesajı göründükten
sonra Telegram'dan yeni komut gönderin. Uygulama ve bilgisayar açık kalmalıdır.

Başlangıçta eski güncellemeler atlanır. Yalnızca seçili özel sohbet kimliğiyle
aynı kullanıcı kimliğinden gelen, son 60 saniyelik özgün mesajlar kabul edilir.
Gruplar, iletilen/düzenlenmiş mesajlar ve başka bota hitap eden komutlar reddedilir.
Token veya sohbet değişikliği için önce uzaktan kontrolü kapatın. Aynı botu
başka bir dinleyiciyle/webhook ile eşzamanlı kullanmayın.

| Komut | İşlem |
|---|---|
| `/start` | Seçili istemcilerde balık oturumunu başlatır; bekletilmiş oturuma devam eder. |
| `/stop` | Balık botunu, geçişi ve sayacı iptal eder. İşçiler bitince durdu bildirimi verir. |
| `/karakterat` | Botu durdurur, ESC ve karakter değiştir akışını yürütür; karakter ekranında kalır. |
| `/kanal` | Botu durdurur ve kalibre edilmiş hedef kanal akışını yürütür. Elle verilen komut otomatik devam etmez. |
| `/durum`, `/istatistik` | Süre, istemci, yem, tur ve doğrulanmış balık sayımını verir. |
| `/pm yanıt metni` | Görsel entegrasyon bekleniyor bilgisini döndürür; oyuna mesaj göndermez. |
| `/help` | Komut yardımını gösterir. |

## Karakter değiştirmenin kalibrasyonu

Ayarlar > **Geçiş akışlarını düzenle** veya Oturumlar > görsel akış düzenleyicisini açın.
**ESC → Karakter değiştir → Karakter ekranı** akışını seçin ve şu adımları tanımlayın:

1. `Tuşa bas`, tuş `esc`: oyun ekranındaki ayırt edici bir şablon mevcutken ESC basar.
2. `Sol tıkla`: açılan menüdeki **Karakter değiştir** düğmesinin görseli.
3. Gerekliyse sunucunun ek onay düğmesini tıklayan ayrı adım.
4. `Görseli doğrula`: **karakter seçim ekranına özgü** görsel; bekleme süresini sunucunun çıkış sayacına göre ayarlayın (adım başına en fazla 60 saniye).

Akışı etkinleştirip kaydedin. Şablonlar gerçek oyun çözünürlüğüne/DPI değerine
uygun olmalıdır. Son doğrulama görseli başlangıç görselinden farklı olmalıdır.
Karakter ekranı doğrulanmadan **Karakter atımı başarılı** mesajı gönderilmez.
İşlem sırasında pencere kapanırsa veya görüntü eşleşmezse otomatik devam edilmez.
Sekiz istemci aynı masaüstünde sırasıyla işlenir; bir istemcide hata olursa kalanlara geçilmez.

## Kanal değişimi ve sayaç

**Kanal değiştir → Hedef kanal doğrulama** akışında kendi sunucunuzun menü,
kanal seçme ve gerekli onay adımlarını hazırlayın. Son şablon sıradan oyun
arka planı olmamalı; **hedef kanalı ayırt eden kanal yazısı/göstergesi** olmalıdır.
Kanal seçimi bu akışla belirlenir.

Ayarlar sekmesine dakika cinsinden süre yazın, işlemi seçip **Sayacı başlat**
düğmesine basın. Süre bu anda başlar; uygulama yeniden açılınca kendiliğinden
başlamaz. Süre dolunca o anda seçili pencereler alınır, tüm çalışan işçiler
durdurulur ve en fazla 30 saniye bitmeleri beklenir. Sonra geçiş yürütülür.

Kanal işleminde **devam et** seçiliyse yalnızca bütün hedefler doğrulanınca
balık oturumu yeniden başlar. **Tekrarla** seçiliyse başarıyla yeniden
başlatıldıktan sonra aynı süre tekrar kurulur. Pencere seçimi geçiş sırasında
değişmişse devam iptal edilir. Karakter işlemi seçim ekranında durur.
**F8**, `/stop` veya uygulamayı kapatmak işlemi ve sayacı iptal eder.
**Sayacı iptal et** devam eden geçişi kesmez, ancak sonraki tekrarı engeller.

## İstatistiklerin anlamı

- Telegram açık süresi: mevcut dinleyicinin süresi.
- Balık oturumu süresi: uygulama açıkken oturumların toplam geçen süresi; bekletme dahil, oturumlar arasındaki boşluk hariç.
- Kullanılan yem: tamamlanan tur başına bir yem varsayımı; yarım kalan atışları ölçmez.
- Kalan yem: mevcut sayaç tahmini; OCR/enventer sayımı değildir.
- Tamamlanan tur: balık yakalama başarısından bağımsız tur sayısı.
- Tutulan balık: Ayarlar > **Balık sayımı** alanına kalibre edilmiş başarı görseli eklenirse sayılır. Görsel olta atmadan önce yokken tur sonunda görünürse bir kez artırılır. Bu an dışında beliren/kaybolan bildirimler kaçırılabilir; sayaç doğrulanmış olayları gösterir, toplam av garantisi değildir. Görsel eksik veya okunamıyorsa sayı yerine eksik ölçüm belirtilir.

İstatistikler uygulama kapatılınca sıfırlanır. Geçiş bildiriminin altına durum
raporu eklenir; istenildiğinde `/durum` ile de alınabilir.

## PM için beklenen ekranlar

PM bildirimi/ikonunun, açık konuşma penceresinin, gönderen adının ve yazı alanının
göründüğü örnekler gereklidir. Bu sürüm komutu tanır ancak OCR, doğru konuşma
eşlemesi ve oyun içi metin gönderimi henüz etkin değildir. Yanıtlar sonradan
otomatik gönderilmek üzere kuyrukta tutulmaz.

Bu sürümün ağ ve masaüstü davranışları taklitlerle test edilmiştir. Gerçek
Telegram hesabı, Gameforge menüleri, Windows kimlik deposu ve çoklu canlı istemci
testi ayrıca yapılmalıdır.

Kaynak: [Telegram getUpdates](https://core.telegram.org/bots/api#getupdates).
