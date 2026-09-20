# Gameforge TR geliştirme notları

İnceleme: 20 Eylül 2026. Temel: hetzpvp/Mt2-Fishbot, `981c4d3`.
Yerel çalışma dalı: `work/gameforge-tr-foundation`. Uzak repoya gönderim yapılmadı.

## Yapılan ilk değişiklik

`WindowManager.activate_window` daha önce pencere odağını üç denemede
doğrulayamadığında normal dönüyor, çağıran kod tuş/tıklama gönderebiliyordu.
Artık seçili pencere yoksa, kapanmışsa veya odak doğrulanamıyorsa
`WindowActivationError` ile o işlem dizisi kesiliyor. Başlangıç sırasında
dışarı taşan bu hata, balık botunun durumunu da durdurulmuş olarak güncelliyor.

Bu, tüm uygulama için eksiksiz odak koruması değildir: doğrulamadan sonra
kullanıcı veya başka bir program odağı değiştirebilir. Uzun işlem dizilerinde
girişten hemen önce tekrar doğrulama ve sayfa geçişi durumunun ancak başarılı
işlemden sonra güncellenmesi sonraki inceleme konularıdır.

Doğrulama komutu:

```bash
python -m unittest discover -s tests -p test_window_manager.py -v
```

Testler Win32 API taklidiyle çalışır; gerçek Windows, Gameforge istemcisi,
yakalama başarısı veya VM uyumluluğu test edilmiş değildir. Mevcut `releases/`
dosyaları bu değişiklikleri içermez. Bu çalışma yeni bir EXE dağıtımı değildir.

## Mevcut özellikler ve açık kalan işler

| Alan | Repodaki durum | Geliştirme hedefi |
|---|---|---|
| Balık tutma | Yeni mini oyun ve klasik mod | Gameforge TR üzerinde referans ölçüm |
| Çoklu pencere | 8 pencereye kadar tasarım, ortak giriş kilidi | Önce 2 istemcinin odak/giriş yarışlarını doğrulama |
| Envanter | Sayfa geçişi, sakla/aç/at seçenekleri | Algılama hatasında eşya işlemini durdurma; profil kalibrasyonu |
| Yem | Tuş başına sayaç | Görsel stok doğrulama; sonra NPC'den yenileme |
| Yapboz | Çözücü ve arayüz mevcut | Balık ve yapboz işlerinin yönetimi, çözümün ölçülmesi |
| Otomatik pişirme | İncelenen ana akışta yok | Ateş/envanter ekranını doğrulayarak işlem dizisi |
| Bağlantı kopması | Pencere yokluğu kontrolü var | Pencere açıkken bağlantı kopmasını ayrıca algılama |
| Yeniden giriş | Tam akış doğrulanmadı | İstemci ekranlarına göre durum makinesi; sınırlı tekrar |
| İzleme | Durum ve tur sayaçları var | Süre, hata, giriş bekleme süresi; gerçek av sonucunu ayrı ölçme |
| Telegram | İncelenen ana akışta yok | İsteğe bağlı bildirim; varsayılan olarak dışarı mesaj gönderme yok |

Yapboz kodunun bulunması balık ve yapbozun kesintisiz birlikte çalıştığını
göstermez: `FishingBot.start()` içindeki etkinleştirme yolu doğrudan yapboz
botuna geçiyor. Öncelikle bu iki iş arasında açık bir geçiş düzeni gerekir.

## 32 GB bilgisayar için ölçüm planı

Başlangıç denemesi: tek VM, iki istemci; VM için 4–6 GB RAM ve 2–4 vCPU
birer deneme ayarıdır, doğrulanmış sistem gereksinimi değildir. Ana sistem için
en az 8 GB çalışma payı bırakılarak gerçek bellek, CPU ve grafik yükü ölçülür.
İşlemci, sanal GPU/3D desteği, açık masaüstü oturumu ve istemcinin VM'de
çalışabilmesi ayrıca doğrulanmalıdır. 32 GB RAM'den kesin VM/karakter sayısı
çıkarılamaz.

Her VM'de iki bot aynı fare/klavyeyi sırayla kullanır. Ayrı VM'ler ayrı
masaüstleri sağlar; VM sayısının artması başarı oranını otomatik artırmaz.
Mini oyun sırasında kaçırılan fırsatlar ve kilit bekleme süreleri ölçülmelidir.
VM uyumluluğu için koruma atlatma bu çalışmanın bir parçası değildir.

## Başlangıç görselleri

Resmî wiki balık mini oyununu ve örnek görselleri sağlıyor. Başlangıç için
kullanıcı videosu zorunlu değil. Yerel testte çözünürlük/ölçek veya istemci
görünümü farklı çıkarsa o ekrandan kısa bir kayıt gerekir.

## Kaynaklar ve iddiaların sınırları

- Repo: https://github.com/hetzpvp/Mt2-Fishbot
- Yazarın forum paylaşımı: https://www.elitepvpers.com/forum/amp.php?t=5333734
  (ilk sayfa incelendi; eski sürüm geri bildirimleri güncel başarı ölçümü değildir).
- Resmî balıkçılık açıklaması:
  https://tr-wiki.metin2.gameforge.com/index.php/Bal%C4%B1k%C3%A7%C4%B1l%C4%B1k
- K34: https://m2balikbotu.com/ — pişirme, yeniden giriş, Telegram ve
  çoklu pencere özellikleri satıcının beyanıdır; bağımsız test yapılmadı.

Kök dizinde projeye ait genel bir LICENSE dosyası bulunmadı. Kaynağın görünür
olması, sınırsız yeniden dağıtım veya ticari kullanım lisansı demek değildir.
Üçüncü taraf Interception bileşeninin ayrı lisans belgeleri vardır.
Yayınlama veya ticari dağıtım öncesinde proje lisansı netleştirilmelidir.

Görüntü işleme veya VM kullanımı tespit edilememe, ban olmama ya da hesaplar
arasında ilişki kurulamama garantisi sağlamaz. Satıcıların gelir ve güvenlik
iddiaları ölçülmüş sonuç olarak kullanılmamıştır.
