# Demirware Fish Bot Metin2 — DEV 0.2

Bu, boristei / hetzpvp Mt2-Fishbot (`981c4d3`) üzerinden geliştirilmiş bir
Windows kaynak sürümüdür. Hazır, Gameforge üzerinde doğrulanmış bir EXE değildir.
Ana istemci hedefi Gameforge Türkiye; sekiz pencere kapasitesi vardır.

## Kurulum

1. Paketi yazılabilir bir klasöre çıkar; ZIP içinden çalıştırma.
2. Python 3.12 **64 bit** ve Python Launcher kurulu olmalı.
3. `Kur.cmd` dosyasını çalıştır. Bağımlılıklar internetten kurulur.
4. `Baslat.cmd` dosyasını çalıştır.
5. İlk denemeyi **tek istemciyle** yap. İstemciler sekmesinden oyun penceresini
   seç; Ayarlar'dan yem tuşlarını, Envanter'den sayfa 1–4 konumlarını tanımla.
   Envanter görünür olmalı. Yeni Gameforge mini oyunu için klasik mod kapalı kalmalı.
6. Önce başlangıçtaki sakla seçeneklerini kullan. Pencere/sayfa kalibrasyonunu
   doğruladıktan sonra balık açma/atma seçeneklerini yapılandır.
7. İki istemcide ölçüm al, ardından dört ve sekize çık. Aynı pencereyi iki
   satıra atamak engellenir. Her VM'nin kendi programı ve ayarları olur.

Program oyun istemcisi açmaz veya hesap oluşturmaz; açık oyun pencerelerini yönetir.
Bu paket oyun giriş kimlik bilgilerini saklamaz. VM kurulum/uyumluluğu doğrulanmadı.

İstersen `ExeOlustur.cmd` ile **Windows üzerinde** EXE oluşturabilirsin. Çıktı
`dist/DemirwareFishBotMetin2-Dev/` klasörüdür; klasörün tamamı gerekir. Bu derleme Linux
çalışma ortamında çalıştırılmamıştır. `requirements-windows.txt` sürüm
aralıkları kullanır; tamamen sabitlenmiş bir üretim bağımlılık kilidi değildir.

## Kullanılabilen yeni özellikler

- Sekiz istemci için FIFO giriş sırası; bir istemci diğerinin sırasını alamaz.
- Ekran yakalama da pencere odağı ve ortak kilitle korunur; üst üste pencereler
  sırayla öne getirilir. Küçültülmüş pencere geri yüklenir.
- İstemci başına bekletme/durdurma; F5 toplu beklet/devam, F8 toplu durdurma.
- Eski işçiler bitmeden yeniden başlatmayı engelleyen oturum yaşam döngüsü.
- Oturum süresi sınırı, sınırlı otomasyon denemeleri, başlangıçları aralama.
- Tur/saat, hata, otomasyondan dönüş, kuyruk beklemesi, CPU/RAM göstergeleri.
- UTF-8 CSV raporu; dönen yerel olay kaydı (`logs/session.jsonl`).
- Gerçek profil kaydetme/yükleme, doğrulama ve dosyayı atomik kaydetme.
- Görsel akış editörü; oyundan alan seçip PNG şablonu oluşturma.
- Kayıp veya belirsiz görselde işlem yapmayan otomasyon yürütücüsü.
- Eksik mini oyun görüntüsünü otomatik olarak 'yem bitti' kabul etmeme.
- Planlı balık → yapboz → balık geçişi (ön koşullar aşağıda).

Tur sayısı balık yakalama sayısı değildir; yem miktarı da görsel/OCR ile
sayılmış stok değildir. Ekran görüntüsünün kapanması bir turun bittiğini gösterir.
Gerçek başarı oranı ve saatlik gelir bu sürümde hesaplanmaz.

## Görsel otomasyonlar

Oturum merkezi → Görsel akışları düzenle. İlgili akışı seç, ekrandaki ayırt
edici düğme/simgeyi yakala. Adımları ekle, sırala; **son adım mutlaka sonucu
doğrulayan görsel kontrolü olmalı**. Görseller aynı çözünürlük, ölçek ve arayüzde
alınmalı. Akışlar kalibre edilmeden etkinleştirilmez; bu pakette Gameforge
ekranları için doğrulanmış hazır akış veya hazır görsel seti bulunmaz.

| Akış | Ne zaman devreye girer? | Son doğrulama neyi göstermeli? |
|---|---|---|
| Yem yenileme | Yem tahmini sıfıra ulaşınca | Kullanılacak hızlı erişim tuşlarında beklenen yem stoku |
| Envanter / pişirme | Envanter doluluğunda bot durunca | İşlemin tamamlandığı ve envanterin kullanılabilir olduğu durum |
| Yeniden giriş | Mini oyun art arda algılanamayınca | Hazır karakter ve balık tutulabilecek ekran |
| Yapbozu aç | Belirlenen tur sayısında | Kalibre edilmiş yapboz tahtası |
| Yapbozdan balığa dön | Yapboz çözücü normal bitince | Balık tutmaya hazır ekran |

Tıklama, sağ tıklama, izinli tuşlar, iki görsel arasında sürükleme ve görsel
bekleme desteklenir. Her işlem öncesinde görsel aranır. Aynı derecede uygun
iki eşleşme bulunursa işlem yapılmaz. Adım zaman aşımında sonraki adıma geçilmez.
Pişirme/yem alma akışı **genel bir harita navigasyonu veya hazır NPC rotası
değildir**; kullanıcının bulunduğu yerde gerekli ekran adımlarıyla tanımlanır.
Yeniden giriş akışı launcher/şifre/CAPTCHA/2FA çözmez; ekranda tanımlanmış,
kimlik bilgisi gerektirmeyen adımlarla sınırlıdır.

Doğrulanmış yem yenileme akışından sonra sayaç ayarlanmış kapasiteye döner;
son görseli yalnızca genel oyun ekranı olarak seçmek stok doğrulaması sağlamaz.
Profil dışa aktarma görsel dosyalarını içine gömmez; başka bilgisayara taşırken
şablon dosyalarını da taşı ve görsel yollarını editörden yeniden seç.

Otomatik yapboz için aç/kapat akışlarını, Yapboz ekranındaki tahta alanını ve
onay konumunu tanımla. Çözüm tablosu önce hazırlanır; hazır değilken balık
oturumu başlatılmaz. Oturum merkezinde tur aralığını belirle. Yapboz zaman
aşımında devam işlemi iptal edilir. İlk testleri elle gözeterek yap.

## Doğrulanan ve doğrulanmayan

Python birim testleri: sekiz eşzamanlı işçi, sıra adaleti, iç içe kilit,
kilit zaman aşımı, kayıt/profil bütünlüğü, görsel belirsizliği, akış iptali,
yeniden deneme bütçesi, sıfır yem, oturum kapanışı ve odak hataları.
Qt arayüzü Linux'ta çevrimdışı açılıp görüntülendi. Windows API testleri
ve oturum testlerinin oyun sınırları taklit edildi.

Gerçek Gameforge istemcisi, sekiz canlı oyun penceresi, anti-cheat uyumluluğu,
VM, Windows kurulumu/EXE ve uzun süreli av burada test edilmedi. K34'ten
daha hızlı veya daha yüksek başarı oranına sahip olduğu ölçülmüş değildir.
Telegram/telefon kontrolü bu sürüme dahil değildir. Gelişmiş ayar ve bazı
üst projeden kalan diyaloglar İngilizcedir.

Kodların görünür olduğu üst projede genel bir LICENSE bulunmadı. Orijinal
yazar bilgileri korunmuştur; bu paket ticari dağıtım hakkı beyan etmez.
Kaynak: https://github.com/hetzpvp/Mt2-Fishbot
