# Delphi + veritabanı: tekrar eden tuzaklar

> Bu belge [`docs/delphi-pitfalls.md`](../delphi-pitfalls.md)'nin Türkçe çevirisidir; çelişkide İngilizce sürüm esastır.

Eski bir Delphi VCL + veritabanı (UniDAC / FireDAC / ADO benzeri `TDataSet` bileşenleri) kod tabanında, yapay zekâyla
çalışırken teşhisi defalarca uzatan desenler. Hepsi gerçek vakalardan çıkarıldı; her maddede belirti, kök neden, nasıl
yakalanacağı ve çözüm kalıbı var. Yeni bir talepte önce buraya bakmak, dört-beş hipotezi denemeden elemeyi sağlar.

Kendi projenizde bu belgeyi başlangıç kabul edin ve vakalarınızla büyütün.

---

## 1. Düz SQL yazıldı, açık veri kümesi görmedi

**Belirti.** Veri veritabanında doğru, ama ekranda ya da raporda yok.

**Kök neden.** Tablo bileşeni istemci tamponunu tutar. Ayrı bir sorguyla yazılan `insert` / `update`, o tablo üzerinde
**zaten açık** bir veri kümesine bildirilmez; küme yalnız kapanıp açılınca ya da `Refresh` ile haberdar olur.

**Yakalama.** Sunucunun cümle istatistiklerinde o tabloya `SELECT` düşüyor mu; hiç yoksa küme açılmamıştır. PostgreSQL:
`pg_stat_statements`; SQL Server: Query Store ya da `sys.dm_exec_query_stats` + `sys.dm_exec_sql_text`; MySQL / MariaDB:
`performance_schema.events_statements_summary_by_digest`; Firebird: `MON$STATEMENTS` (yalnız o an çalışanlar) ya da trace.

**Çözüm kalıbı.** Yazan kodun hemen ardından `Close; Open; First;`. `First` önemli: rapor bantları çoğu kez **cari
satıra** bakar, imleç EOF'taysa koşul tutmaz.

## 2. İstemci süzgeci kapalı bırakıldı → kayıtlar birbirine karıştı

**Belirti.** Temiz bir kayıtta "zaten yapılmış" türü bir uyarı; başka bir kaydın verisi varmış gibi davranılıyor.

**Kök neden.** Sunucu tarafı süzgeç yok: tablo bütünüyle çekilip `OnFilterRecord` ile istemcide ayıklanıyor.
`Filtered := False` yapıldığı anda tamponda **bütün kiracıların** satırları görünür.

**Çözüm kalıbı.** Süzmeyi sunucuya taşı (bileşenin `FilterSQL` / `Params` / master-detail bağı); istemci süzgeci olduğu
yerde kalabilir. Süzgeci geçici değiştiren her yer `try … finally` ile bulduğu hâline döner.

## 3. SQL yazıldı, akış sonradan üzerine yazdı

**Belirti.** Hata ayıklarken değer **doğru oluyor, sonra tekrar bozuluyor**.

**Kök neden.** Aynı tabloya akışın ilerleyen adımlarında başka bir cümle dokunuyor ("önce hepsini sıfırla, sonra doldur";
doldurma yalnız bir tarafı kapsıyor).

**Yakalama.** Tabloya yazan **bütün** cümleleri çalıştırılmış hâlleriyle dök:
PostgreSQL:
`select calls, rows, query from pg_stat_statements where query ~* '(update|insert into|delete from)\s+<tablo>'`.
SQL Server: Query Store / cümle metnine süzülmüş `sys.dm_exec_query_stats`; MySQL / MariaDB:
`performance_schema.events_statements_summary_by_digest` (`DIGEST_TEXT`); Firebird: tabloya bir trace oturumu.
Satırın `id`'si değişmişse satır silinip yeniden kurulmuş, değişmemişse üzerine yazılmıştır.

**Ders.** Bir tabloya yazmadan önce sorulacak soru: *bu akışta benden sonra bu tabloya kim dokunuyor?*

## 4. Bayrak ya da global `try…finally` olmadan değiştiriliyor

**Belirti.** Bir işlemden sonra ekranın bir kısmı "donuyor"; ya da sonraki yazımlar yanlış kayda gidiyor.

**Kök neden.** `Bayrak := True; … Bayrak := False;` (ya da `Eski := Global; Global := X; … Global := Eski;`) ikilisinin
arasında `exit` ya da exception var; değer takılı kalıyor. Bir süzgecin anahtarı olan global (ör. "cari dönem numarası")
geçici değiştirilip geri alınmazsa, ardından gelen her kayıt yazımı yanlış satıra gider.

**İkinci kusur: iç içe kullanım.** Düz `Boolean` ile iç blok bayrağı sıfırlayınca dış bloğun koruması çöker.

**Çözüm kalıbı.** Sayaç + `try…finally` (`BeginUpdate/EndUpdate` semantiği); geçici global değişikliği tek bir ortak
yordama alıp geri yüklemeyi `finally`'ye koymak. Aynı kalıp birden çok kopyadaysa tek yordama indir (madde 16).

## 5. Tek yönlü güncelleme (mandal)

**Belirti.** Bir göstergenin "dolu" hâli bir kez görününce bir daha temizlenmiyor.

**Kök neden.** Olay yordamı yalnız "var" durumunu yazıyor; "yok" durumunu geri yazan `else` yok; ya da `else if` zinciri
yüzünden yalnız ilk koşul güncelleniyor.

**Çözüm kalıbı.** Her gösterge kendi verisine göre **bağımsız ve iki yönlü** yazılır.

## 6. Bileşen hatayı yutuyor — ama loga yazıyor

Yardımcı "SQL çalıştır" yordamları çoğu kez `except` içinde hatayı loga yazıp devam eder. Bir cümle hiçbir şey yapmamış
görünüyorsa **önce loga bak**. Yeni yazılan kodda hata yutulacaksa en az loga yazılır.

## 7. `KeyFields = 'id'` + `StrictUpdate = False`

Her `Post` ve `RefreshRecord` sunucuya `UPDATE … WHERE id = N` olarak gider. `id` kolonunda indeks yoksa her yazma tam
tablo taraması olur. `StrictUpdate = False` "1 yerine N satır etkilendi" uyarısını yutar ve mükerrer `id`'yi aylarca
gizleyebilir.

## 8. İstemci tarafında tekrar = sabit maliyet

`TField.Value := …` ataması `DataEvent(deFieldChange)` tetikler, bağlı bütün kontroller kendini yeniler; bir ekranda
atama başına yüzlerce milisaniye ölçülebilir. Bir sunucu gidiş-dönüşü de sabit bir maliyettir; satır satır dönen döngü
bununla çarpılır. **Çözüm:** döngüyü toplu SQL'e çevirmek; ya da pahalı alıcıyı bulup yalnız onu susturmak (madde 13).

## 9. Saklı yordam mantığının Delphi'de ikinci kopyası

Hızlı çözüm için bir yordamın son adımları Delphi'ye kopyalandığında, yordam değişince kopya sessizce geride kalır.
Yeni bir kopya açmadan önce: saklı yordamın kendisinde çözmek gerçekten mümkün değil mi?

## 10. Ölçtüğün yolu iyileştirmek, kullanıcının kullandığı yolu değil

**Belirti.** Performans düzeltmesinden sonra ölçüm harika, kullanıcı "daha iyi ama hâlâ yavaş" diyor — kısmi düzeltmenin
imzası.

**Kural.**
- Ölçümü **kullanıcının bastığı tuştan** başlat, kendi bulduğun yordamdan değil.
- O işlemi tetikleyen **bütün** giriş noktalarını çıkar: düğme, ızgara olayı, klavye kısayolu, veri kümesi olayı
  (`OnNewRecord`, `OnCalcFields`, `AfterEdit`).
- Düzelttikten sonra **testçinin senaryosunu birebir** çalıştır.

## 11. Bir arayüz özelliğine aynı değeri yazmak bedava değildir

Sık çalışan bir yordamdan (`OnDataChange`, `OnCalcFields`, `OnGetCellParams`) denetim özelliğine (`ImageIndex`,
`Caption`, `Color`, `Enabled`, `Visible`, `Hint`) koşulsuz yazmak her seferinde yeniden çizim demektir. Önce karşılaştır:
`if X.ImageIndex <> Yeni then X.ImageIndex := Yeni;`. Gözle görülen titreme / yanıp sönme belirti listesine yazılır: her
sönme bir gereksiz yeniden çizimdir.

## 12. Hiç çalıştırılmamış bir yolda şablon ve veri de şüphelidir

Bir özellik sahada **hiç çalışmadıysa**, o yolun üzerindeki her şey doğrulanmamıştır: kod kadar rapor şablonu, varsayılan
ayar ve tablo içeriği de. "Bu yol daha önce çalıştı mı?" teşhisin ilk sorusudur; cevap hayırsa kodu okumadan önce aynı
ailenin çalışan sürümüyle karşılaştır.

## 13. `DisableControls`'u bir olay işleyicisinin içinden çağırma

Bağlı bir kontrolün olayı (`OnColExit`, `OnKeyDown`, `OnExit`) sürerken `DisableControls / EnableControls` çağrılırsa,
`EnableControls` ızgaraya topluca "veri seti değişti" gönderir; ızgara kendi işleminin ortasında yenilenir, yarım kalan
klavye hareketi düşer. Hız için bildirim bastırmak gerekiyorsa asıl pahalı alıcıyı sustur. Performans düzeltmesinden sonra
ekranın **klavye akışını** da sına.

## 14. Delphi'nin "ilk satır"ı SQL'de "bütün satırlar"a dönüşür

`Locate`, `FieldByName` (ilk kayıt), `RecordCount > 0` ile yapılan arama "en fazla bir satır" semantiğidir. Mantığı SQL'e
taşırken bunu **koda** yaz: `LATERAL (... ORDER BY ... LIMIT 1)` ya da tekilliği garanti eden kısıt. Toplama yapan
sorguda beklenmedik tekrar her zaman önce JOIN yelpazelenmesi olarak sınanır.

## 15. Boş veri kümesinde `Edit` = `Insert`

`TDataSet.Edit` boş bir kümede `Insert` çağırır. "Yalnız düzenliyorum" sanılan kod — ya da kümeye bağlı bir DB denetimine
yazan kullanıcı — süzgeç ya da master-detail yüzünden küme o an boşsa yeni satır ekler. Beklenmedik "boş ikiz" satırların
kaynağı çoğu kez budur. Yakalama: kümenin `BeforeInsert`'üne geçici bir ölçüm uyarısı (kim, hangi durumda ekliyor).
Hikâyenin tamamı: [vaka](vaka.md).

## 16. Kopyalanmış kodda düzeltme yalnız bir kopyaya gider

Bir hatayı düzeltirken aynı mantığın başka kopyalarını ara: yordam adı, tablo adı, kilit satırı. Kopya varsa düzeltmeyi
kopyalara taşıma; tek yordama indir ve diğerlerini ona bağla. `tools/pas_callers.py` yeni yordamın bütün kullanımlarını listeler
(bütün kopyaların artık onu çağırdığını göstermek için); `tools/pas_edit.py` `routine` ile tek bir kopyayı, öbürlerinin aynı
satırlarına dokunmadan düzenler.

## 17. Arka sekmedeki denetime `SetFocus`

Denetim önde olmayan bir sekmede ya da henüz gösterilmemiş formdaysa `SetFocus` "Cannot focus a disabled or invisible
window" fırlatır. `if X.CanFocus then X.SetFocus;` — `CanFocus` denetimin ve bütün üst öğelerinin görünür ve etkin
olduğuna bakar.

## 18. Kiracı koşulunun unutulması

Kiracı / dosya bazlı tablolarda bir cümlenin **yalnız açık kayda** dokunduğu, koşulu yazılmadıkça garanti değildir.
Kopyalanan kayıtlar aynı iç kimlikleri taşıdığı için "kayıt içinde tekil" alanlar kayıtlar arasında tekil değildir.
**Yakalama:** UPDATE / DELETE yazan her cümlede `where` kısmında kiracı koşulu var mı; `UPDATE … FROM`'da hedef tablonun
kiracısı koşulda mı, yoksa yalnız kaynak tarafında mı?

## 19. Parantezsiz `or` + sona eklenen kiracı koşulu

Kiracı koşulu dizge olarak cümlenin sonuna ekleniyorsa (`' and TenantId = ...'`), `where a or b` + ek SQL'de
`a or (b and TenantId = X)` olur: `a`'yı sağlayan satırlar **bütün kiracılarda** güncellenir ya da silinir. Kod okurken
koşul "var" görünür; hata yalnız öncelikte. `or` içeren her cümlede koşul parantez içinde mi?

## 20. Ekran kontrolü veriden ayarlanmıyor, yalnız tıklamayla değişiyor

Bir kontrolün `OnChange`'i bir alanı yazıyor ama açılışta kontrolün kendisi o alandan ayarlanmıyorsa, ekranda bir şey
yazar, program başka bir şeye göre çalışır. Alanın okunduğu yerde kontrolün değeri de atanır (atamada olay geçici kapalı).

## 21. `FieldByName('X').Value = ''`: NULL alanda hep False

`Value` Variant döner; alan NULL ise `Value = ''` False, `Value <> ''` True olur. Boş metinle NULL'ın ikisi de "değer yok"
anlamına geliyorsa kod NULL'ı "dolu" sayar. Tipli alan erişimi ve `AsString` NULL'ı `''` verir; aynı kolon iki yerde farklı
okunursa iki yer farklı karar verir.

## 22. Ad yanıltır; grep sonucunu tam oku

Bir ayar kolonunu anlamına göre değil, onu dolduran kodun yaptığına göre okuyun. "Bu bayrak hiç True olmuyor" demeden önce
bütün atama satırlarını okuyun; tek bir kaçan satır "ölü" hükmünü yanlış yapar.
