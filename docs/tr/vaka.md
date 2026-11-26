# Vaka: boş ikiz satırlar

> Bu belge [`docs/case-study.md`](../case-study.md)'nin Türkçe çevirisidir; çelişkide İngilizce sürüm esastır.

Eski bir Delphi VCL + PostgreSQL uygulamasından gerçek bir vaka, adlar çıkarılarak anlatıldı. Bu deponun yöntemini iş
başında gösteriyor — yapay zekânın yanıldığı yerler ve onları neyin yakaladığı dahil.

## Ortam

Uygulama bir tabloda **belge ve dönem başına bir özet satırı** tutuyor. Birçok ekran onu okuyor; raporlar dönemler boyunca
topluyor; birkaç SQL cümlesi "o" satırı `LIMIT 1` ile okuyor ya da `UPDATE … FROM` içinde birleştiriyor.

Ekranda özet, master-detail bağlı bir `TDataSet`: master, hangi belgenin açık olduğunu gösteren bir "yönetim" kümesi;
detail o belgenin satırlarını gösteriyor ve istemcide cari döneme süzülüyor (`OnFilterRecord`). `OnNewRecord` birkaç
varsayılan dolduruyor (bir vergi oranı, "hesaba girer" işareti, global değişkenlerden belge anahtarı ve dönem numarası).

## Belirti

Başka bir iş sırasında salt okunur bir sorgu, tablonun (belge, dönem) üzerinde **tekil olmadığını** gösterdi: 17 tekrar
grubu, 9'unda satırların değerleri farklı. O belgelerde her `LIMIT 1` okuması ve her `UPDATE … FROM` satırlardan birini
rastgele alıyordu.

## Adım 1 — kaynağı bilmeden temizleme

Akla ilk gelen tekillik kısıtı ve bir temizlik betiğiydi. Geliştirici durdurdu: *"Önce boş satırları neyin ürettiğini
bulalım. Hatayı oluşmadan çözelim."* Kaynağı bilinmeyen temizlik bir sonraki temizliği takvime koymaktır.

## Adım 2 — satırları kimin yazdığını veriye söylet

Fazla satırlar kolon kolon karşılaştırıldığında **hepsinde tam olarak `OnNewRecord` varsayılanları vardı, başka hiçbir şey
yoktu**. Bu, SQL yollarını eledi (hiçbiri bu varsayılanları yazmıyor) ve istemciyi gösterdi: bir şey özet kümesi boş
görünürken `Append` / `Insert` çağırıyordu.

Aralarında "kitap" belgelerine (gerçek proje değil, tekrar kullanılan özel belgeler) ait satırlar vardı; bu bir sonraki ipucuydu.

## Adım 3 — koddan hipotez, sonra deney

Kod okuması bir hikâye kurdu: kitap açan bir menü komutu **master imlecini** kitaba taşıyor; iş bitince "durumu geri yükle"
yordamı global değişkenleri geri koyuyor ama imleci koymuyor. Detail küme artık yanlış master satırını izliyor; sonraki bir
"özet onaylı mı?" denetimi kümeyi boş bulup satır ekliyor.

Koddan kurulan hikâye kanıt değildir; sıradaki adım geliştiricinin yaptığı tek değişkenli bir deneydi:

1. tablodaki en büyük satır kimliğini not et;
2. A belgesini aç;
3. menüden B kitabını aç, kapat;
4. daha büyük kimlikli satırlara bak.

Sonuç: B kitabı için bir yeni satır; A belgesinin dönem numarasıyla ve A'dan kopyalanmış iki değerle. Hipotez tuttu.

## Adım 4 — plan ve onu değiştiren inceleme

İlk plan: özet kümesindeki yedi `Append` çağrısını, master yanlış belgedeyken eklemeyi reddeden tek bir korumalı yordamdan
geçirmek.

Birçok ekranın kullandığı bir kümenin davranışı değiştiği için plan `/review`'dan geçti: bağımsız bir ajana yalnız
değişikliğin tarifi verildi (hipotez de sonuç da değil), kapsamı dört eksende saydı. Planın kaçırdığı bir şeyle döndü:

> **Boş** bir kümede `TDataSet.Edit`, `Insert` çağırır (`Data.DB`).

Kodda o küme üzerinde yaklaşık 62 koşulsuz `Edit` ve ona bağlı veri denetimleri vardı. Yedi `Append`'i korumak, aynı satırı
üretmenin onlarca yolunu açık bırakırdı. Yapay zekâ bunu geliştiriciye götürmeden önce `Data.DB.pas`'ı açıp doğruladı (ajan
iddiası doğrulanmadan olgu diye sunulmaz) ve plan yeni hâliyle yeniden onaylandı:

1. **Kaynağı düzelt:** geri yükleme yordamı master imlecini de açık belgeye taşır; iki menü komutu gövdesini `try … finally`
   içine alır, erken çıkışta ve hatada da geri yükleme çalışır.
2. **Kalanı ölç:** özet kümesinin `BeforeInsert`'üne, şüpheli durumda (açık belge yok, kitap, imleç başka belgede ya da o belge
   ve dönem için satır veritabanında zaten var) uyarı yazan (engellemeyen) bir işleyici. `BeforeInsert` her yolu görür —
   `Append`, `Insert`, boş kümede `Edit` ve veri denetimleri.
3. **Var olan veriyi onarım aracında temizle,** program açılışında değil: belgesiz satırlar, etkin olmayan kitapların satırları ve
   dolu bir kardeşi olan boş ikizler. Önce yerel veritabanında salt okunur sayım.

## Adım 5 — takipte çıkanlar

Maddeyi kapatmak "bildirildi, kapsam dışı" notlarına da bakmak demekti:

- **Önceki dönemi okumak** beş kopyada, global dönem numarasını geçici olarak N-1 yapıp süzgeci yenileyerek, bir alan okuyup
  geri alarak yapılıyordu — `try … finally` olmadan. Arada bir hata çıkarsa sonraki bütün yazımlar önceki döneme giderdi.
  Kopyalar `finally`'de geri yükleyen tek yordamda birleşti ([tuzak 4](delphi-tuzaklari.md), [16](delphi-tuzaklari.md)). İki
  kopya başka bir "gerçek dönem" değişkeni kullanıyordu, çünkü başka bir ekran global olanı yeniden numaralıyor; bunu da
  inceleme buldu.
- Birleştirmenin hiçbir şeyi değiştirmediğini göstermek için iki deneme belgesinin bütün satırlarının **parmak izi** etkilenen
  ekranlar çalıştırılmadan önce ve sonra alındı (`tools/pg_fingerprint.py`): yalnız cari dönemin özet satırı değişti, önceki
  dönemin satırı değişmedi — dönem numarası doğru geri dönmüştü.
- Kalan bir yetim satır, loglar ve satırların `xmin`'i üzerinden, belgenin cari dönemini güncellemeyen eski bir "son dönemi
  sil" sürümüne bağlandı; birkaç gün önce eklenen bir koruma bunu zaten önlüyor, onarım aracı artık son dönemden büyük
  numaralı satırları siliyor.

## Yapay zekânın bu çalışmadaki yanlışları

- Aynı serinin ilişkili bir maddesinde, koddan eksik dönemin Ocak'a düşeceğini öngördü. Ölçüm, fiyatın aslında bir arama
  imlecinin kaldığı satırdan geldiğini gösterdi. Öngörü geri çekildi, madde yeniden yazıldı.
- Bir yordamın çağıranlarını 8 saydı; çağıran aracı sonradan 9 buldu — önceki `grep` çıktısı `head` ile kesilmişti.
- Bu deponun düzenleme aracını yazarken başarısız bir testi önce diff aracının kusuru sandı; gerçek sebep, daha girintili bir
  satırın içinde eşleşen bir çapaydı. Araç artık tam satır çapalarını yalnız satır başında eşler.

Her biri aynı turda hata defterine kural + kontrol olarak ya da bir araca girdi.

## Farkı yaratan

| Adım | Uygulama |
|---|---|
| Önce kısıt eklememek | temizlemeden önce kaynağı bul ([hata defteri](hata-defteri.md) [1]) |
| Fazla satırlardaki varsayılanlar | kimin yazdığını veriye söylet ([2]) |
| Kimliklerle menü deneyi | hikâye yerine tek değişkenli deney ([1]) |
| `Edit` = `Insert` | kapsamı dört eksende sayan kör inceleme ([11]); ajan iddiasını doğrulamak ([6]) |
| `BeforeInsert` uyarısı | kalan yolları tahmin etmek yerine ölçmek |
| Temizliğin onarım aracında olması | kalıcı yan etki açık bir eyleme bağlı, program açılışına değil ([14]) |
| Önce / sonra parmak izi | bir yeniden düzenlemenin hiçbir şeyi değiştirmediğini göstermek ([1]) |
