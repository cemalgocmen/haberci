İNDİRİM BOTU - kurulum (bir kerelik, ~15 dakika)

ÖNEMLİ: GitHub'da YENİ bir **Public** (herkese açık) depo açın. Public depoda
Actions dakikaları ücretsiz ve sınırsızdır; Private depoda bu bot ücretsiz kotayı aşar.
Kanal/kelime listeniz herkese açık görünür, ama bot token'ınız ve kimliğiniz görünmez
(onları "secret" olarak saklayacağız).

A) TELEGRAM BOTU OLUŞTURMA
 1. Telegram'da @BotFather'ı bulun, /newbot yazın, bir ad ve sonu "bot" ile biten
    bir kullanıcı adı seçin. Size bir TOKEN verir (123456:ABC...). Saklayın.
 2. Yeni botunuzu arayıp açın ve /start yazın (bunu yapmazsanız bot size mesaj atamaz).
 3. @userinfobot'a herhangi bir mesaj yazın; size "Id: 123456789" gibi bir sayı verir.
    Bu sizin CHAT_ID'nizdir.

B) GITHUB
 1. Yeni public depo oluşturun (ör. indirim-botu).
 2. Bu klasörün içindekileri yükleyin: bot.py, kanallar.txt, kelimeler.txt, README.txt
    ve .github/workflows/tara.yml. ".github" klasörü sürükle-bırakta atlanabilir;
    atlanırsa Add file > Create new file ile adı ".github/workflows/tara.yml" yazıp
    içeriği yapıştırın.
 3. Depoda Settings > Secrets and variables > Actions > New repository secret:
      Ad: BOT_TOKEN   Değer: BotFather'ın verdiği token
      Ad: CHAT_ID     Değer: userinfobot'un verdiği sayı
 4. Actions sekmesi > "Telegram indirim takibi" > Run workflow > "Test mesajı gönder"
    kutusunu işaretleyip çalıştırın. Telegram'da "✅ İndirim botu çalışıyor" gelmeli.
 5. Bundan sonra kendi kendine her ~5 dakikada bir çalışır.

TELEGRAM'DAN YÖNETİM (dosya düzenlemeye gerek yok)
 Botunuza şu komutları yazın (yalnızca sizin CHAT_ID'nizden gelenler işlenir):
   /liste                         istek ve kanalları numaralı gösterir
   /ekle fissler düdüklü          istek ekler
   /sil 2                         2 numaralı isteği siler (veya /sil fissler düdüklü)
   /degistir 2 philips airfryer   2 numaralı isteği değiştirir
   /kanal t.me/kanaladi           kanal ekler (okunabiliyorsa onaylar, okunamıyorsa uyarır)
   /kanalsil 1                    1 numaralı kanalı siler (veya /kanalsil kanaladi)
   /yardim                        komut özeti
 Komutlar bot her çalıştığında işlenir; yanıt yaklaşık 5-10 dakika içinde gelir (anlık değil).
 Değişiklikler depodaki kelimeler.txt ve kanallar.txt dosyalarına kendiliğinden yazılır;
 isterseniz bu dosyaları GitHub'dan elle de düzenleyebilirsiniz.

ELLE DÜZENLEME (isteğe bağlı)
 - Kanal eklemek: depoda kanallar.txt > kalem simgesi > yeni satıra t.me/kanaladi > Commit.
 - Aranacak ürün eklemek: kelimeler.txt'ye satır ekleyin.
     fissler düdüklü          -> ikisi de geçmeli
     "dyson v15"              -> tam ifade
     airfryer -kılıf          -> "kılıf" geçmemeli
 - Bir satırı silmek ya da başına # koymak onu devre dışı bırakır.

BİLMENİZ GEREKENLER
 - Bir kanalın ilk taramasında eski paylaşımlar için bildirim GELMEZ; yalnızca o andan sonraki yeni paylaşımlar kontrol edilir.
 - Yalnızca herkese açık kanalları (t.me/s/kanaladi sayfası açılıyorsa) okuyabilir. Gruplar ve özel kanallar okunamaz.
 - GitHub zamanlayıcısı 5 dakikada bir çalıştırmaya çalışır; yoğun saatlerde birkaç dakika gecikebilir.
 - Yalnızca yazıyı okur; afiş/resim içindeki yazıyı okuyamaz.
 - Depoda 60 gün hiç etkinlik olmazsa GitHub zamanlayıcıyı durdurabilir; Actions sekmesinden yeniden etkinleştirin.
 - Bir kanal okunamazsa bot size bir kere uyarı mesajı atar.
