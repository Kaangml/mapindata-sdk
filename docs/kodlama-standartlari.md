# MapinData Kodlama Standartları

---

## Genel

| Standart | Açıklama |
|---|---|
| Okunabilirlik önceliklidir | Kod ilk okumada anlaşılabilir olmalıdır |
| Tek sorumluluk | Her sınıf ve fonksiyon tek bir işi yapmalıdır |
| Gereksiz karmaşıklıktan kaçın | Basit çözümler tercih edilmelidir |

---

## İsimlendirme

### Genel Kurallar

| Standart | Açıklama |
|---|---|
| Anlamlı isimler kullan | `data`, `tmp`, `val` gibi belirsiz isimlerden kaçınılmalı |
| Fonksiyon isimleri eylem içerir | `createUser`, `calculateTotal` gibi |

### İsimlendirme Stilleri

| Kategori | Stil | Açıklama | Örnek |
|---|---|---|---|
| Global değişken | `UPPER_SNAKE_CASE` | Tüm uygulama genelinde kullanılan sabit veya önemli değerler | `MAX_CONNECTION_COUNT` |
| Constant (const) | `UPPER_SNAKE_CASE` | Değişmeyen sabit değerler | `DEFAULT_TIMEOUT` |
| Lokal değişken | `camelCase` | Fonksiyon içinde kullanılan değişkenler | `userName` |
| Fonksiyon parametreleri | `camelCase` | Fonksiyona gelen parametreler | `orderId` |
| Boolean değişken | `camelCase` (is/has/can) | Mantıksal değerler | `isActive`, `hasPermission` |
| Liste / koleksiyon | çoğul isim | Birden fazla öğe içeren değişken | `users`, `orders` |
| Private class variable | `_camelCase` | Sadece sınıf içinde kullanılan değişken | `_connectionPool` |
| Static constant | `UPPER_SNAKE_CASE` | Sınıf seviyesinde sabit değer | `MAX_RETRY_COUNT` |
| Class / Object | `PascalCase` | Sınıf isimleri | `UserService` |
| Fonksiyon / metod | `camelCase` | Fonksiyon isimleri | `calculateTotalPrice` |

---

## Fonksiyonlar

| Standart | Açıklama |
|---|---|
| Kısa fonksiyon yaz | Uzun fonksiyonlar parçalanmalıdır |
| Az parametre kullan | 3–4 parametreden fazlası için obje kullanılmalıdır |
| Yan etkileri açık olmalı | Fonksiyon gizli durum değişikliği yapmamalı |

---

## Kod Tekrarı

Aynı kod birden fazla yerde tekrar edilmemeli.

---

## Klasör Yapısı

| Standart | Açıklama |
|---|---|
| Mantıklı klasör yapısı | Domain veya feature bazlı klasörleme (Backend / Frontend vb.) |

---

## Format

| Standart | Açıklama |
|---|---|
| Otomatik formatter kullan | Ekipte tek formatter/linter olmalıdır |
| Tutarlı girinti ve boşluk | Tüm projede aynı stil kullanılmalıdır |

---

## Yorumlar (Comments)

| Standart | Açıklama |
|---|---|
| "Neden" açıklanmalı | Kod kendini açıklayabilmelidir. Ancak fonksiyonların ve program dosyalarının başında genel bilgiler bulunmalıdır: *Created by*, *Created At*, *Subject* vb. Karmaşık iş mantığı da yorumlanmalıdır |

---

## Güvenlik & Kalite

| Kategori | Standart | Açıklama |
|---|---|---|
| Hata Yönetimi | Hatalar yutulmaz | Her hata loglanmalı veya üst katmana iletilmelidir |
| Loglama | Anlamlı log yaz | Debug ve hata analizi için yeterli bilgi içermeli |
| Güvenlik | Hassas veri kodda tutulmaz | Secret ve anahtarlar config üzerinden yönetilir |
| Test | Kritik kodlar test edilmelidir | İş mantığı testsiz bırakılmamalıdır |

---

## Git

| Standart | Açıklama |
|---|---|
| Küçük ve anlamlı commit | Commit mesajı değişikliği anlatmalıdır |
| PR zorunludur | Ana dala doğrudan push yapılmaz |
---

## Katkıda Bulunanlar

| Ad | Rol |
|---|---|
| Kaan Gümele | SDK Geliştirici |
| Mehmet Emin Taşkıranoğlu | Kodlama Standartları |