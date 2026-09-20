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
