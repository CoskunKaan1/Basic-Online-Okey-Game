# 🎮 Online Okey Oyunu (Python & PyQt5)

Python ve PyQt5 kullanılarak geliştirilmiş, gerçek zamanlı ve çok oyunculu (Client-Server mimarisine sahip) masaüstü Okey oyunu. Ağ üzerinden arkadaşlarınızla veya yerel ağda (localhost) test ederek oynayabilirsiniz.

## ✨ Özellikler

- **Gerçek Zamanlı Çok Oyunculu Deneyim:** TCP Soket programlama ve JSON tabanlı özel haberleşme protokolü ile 4 kişiye kadar gerçek zamanlı oyun desteği.
- **Modern ve Duyarlı (Responsive) Arayüz:** PyQt5 ve QSS (Qt Style Sheets) kullanılarak tasarlanmış modern, "ahşap ıstaka" görünümlü, ekran boyutuna göre dinamik ölçeklenen arayüz.
- **Gelişmiş Oyun Mekanikleri:** - Istaka üzerindeki taşları **sürükle ve bırak (Drag & Drop)** yöntemiyle kolayca yerleştirme ve takas etme.
  - Okey (Sahte Joker) yönetimi.
  - Per (grup/seri) hesaplama algoritmaları ve otomatik el doğrulama sistemi.
- **Zaman Aşımı ve Otomatik Oynama (Turn Timeout):** Sırası gelen oyuncu belirlenen süre (varsayılan 60 sn) içinde hamle yapmazsa, sunucu oyuncunun düşmemesi için otomatik olarak taş çeker ve atar.
- **Oyun İçi Sohbet:** Oyuncuların oyun esnasında birbiriyle mesajlaşabilmesi için entegre sohbet (chat) sistemi.
- **Test Başlatıcı (Launcher):** Tek bir tıkla yeni istemciler (oyuncular) oluşturmak için pratik test arayüzü (`main.py`).

## 📁 Proje Yapısı

| Dosya | Açıklama |
| :--- | :--- |
| `server.py` | Oyunun ana sunucu dosyasıdır. Bağlantıları, oyun akışını, zamanlayıcıları ve ağ yayınını yönetir. |
| `client.py` | Oyuncu arayüzüdür. Masayı, ıstakayı, sürükle-bırak işlemlerini ve sunucu iletişimini barındırır. |
| `game_logic.py` | Taş oluşturma, el dağıtma, sırayı takip etme ve elin bitmeye uygun olup olmadığını denetleyen ana oyun motorudur. |
| `protocol.py` | İstemci ve sunucu arasındaki JSON tabanlı haberleşme mesajlarını (MsgType) barındırır. |
| `main.py` | Sunucu çalışırken yerel ortamda kolayca birden fazla oyuncu başlatmak için kullanılan test başlatıcısıdır. |
| `config.py` | Port, IP adresi, oyuncu sayısı, zaman aşımı süreleri gibi temel oyun yapılandırmalarını içerir. |
| `style.qss` | Arayüzün modern ve gerçekçi görünmesini sağlayan CSS benzeri arayüz stil dosyasıdır. |

## 🛠️ Kurulum ve Gereksinimler

Projeyi çalıştırabilmek için bilgisayarınızda **Python 3.11** kurulu olmalıdır.
