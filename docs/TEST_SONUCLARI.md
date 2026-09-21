# DEV 0.4 doğrulama kaydı

20 Eylül 2026 — Linux / Python 3.12.

- 58 test geçti, 7 üst-proje yapboz testi masaüstü bağımlılıkları eksik olduğu için atlandı.
- Komut yetkisi: başka kullanıcı/grup, iletilmiş/düzenlenmiş mesaj, eski mesaj ve başka bota hitap eden komut reddi test edildi.
- Açılış güncellemeleri atlandı; aynı update_id ikinci kez çalıştırılmadı (taklit Telegram API).
- Sayaç tek tetikleme, iptal, geçersiz süre; işçi bitişini bekleme ve durma zaman aşımı doğrulandı.
- Geçiş iptalinden sonra yeniden başlatma yapılmaması ve başarısız görselde başarı bildirimi çıkmaması test edildi.
- Başarı görseli aynı turda en fazla bir kez sayılır; eksik şablonda sayım eksik olarak işaretlenir.
- Qt önizlemede Telegram komut paneli ve Ayarlar zamanlayıcısı açıldı, ekran görüntüleri incelendi.
- Python derleme ve git boşluk denetimi geçti.

Gerçek Telegram mesajı gönderilmedi. Windows kimlik deposu, Gameforge karakter/kanal menüsü, gerçek balık sayımı ve çoklu istemci testi yapılmadı. `/pm` oyun içi gönderimi ekran örneklerini bekliyor.

---

# DEV 0.3 doğrulama kaydı

20 Eylül 2026 — Linux / Python 3.12.

- 40 test geçti; 7 üst-proje yapboz testi masaüstü bağımlılıkları eksik olduğu için atlandı.
- Telegram API istekleri taklit edilerek token/alıcı doğrulaması, zaman aşımı, hata gizleme ve özel sohbet seçimi test edildi.
- Kimlik deposu taklit edilerek token’ın JSON dosyasına sızmaması ve kayıt hatasında düz metne dönülmemesi doğrulandı.
- Qt çevrimdışı önizlemede 5 sekme, 8 istemci, gizli token alanı, hatalı giriş ve boş oturum kontrolleri doğrulandı.
- Ana ekran ve Telegram ekranı görüntüleri incelendi.
- Gerçek Telegram mesajı gönderilmedi; Windows kimlik deposu/EXE ve canlı oyun testi yapılmadı.

---

# DEV 0.2 doğrulama kaydı

20 Eylül 2026 — Linux / Python 3.12.

- 30 test geçti; 7 üst-proje yapboz testi masaüstü bağımlılıkları eksik olduğu için atlandı.
- Sekiz iş parçacığı, kişi başına 30 işlem: çakışmasız 240 işlem; FIFO sırası ve zaman aşımı kontrol edildi.
- Gerçek balık döngüsü yapay görüntüyle çalıştı: 1 tur, 1 tıklama, 0 kalan yem, tek kapanış bildirimi. İşletim sistemine giriş gönderilmedi.
- Qt arayüzü çevrimdışı açıldı; 8 satır, 4 sekme, boş oturum kontrolleri ve ayar kaydı doğrulandı.
- Python derleme ve git boşluk kontrolleri geçti.
- QA bağımlılıkları: PySide6 6.11.2, OpenCV 4.14.0, NumPy 2.2.6, psutil 7.2.2.

Bu sonuçlar Gameforge uyumluluğu, sekiz canlı istemci performansı, Windows kurulum/EXE veya uzun süreli av testi değildir.
