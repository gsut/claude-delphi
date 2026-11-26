# Hata defteri — yöntem ve başlangıç maddeleri

> Bu belge [`docs/mistake-log.md`](../mistake-log.md)'nin Türkçe çevirisidir; çelişkide İngilizce sürüm esastır.

Claude'un çalışma biçiminde yaptığı, **tekrar edebilecek** hataların listesi. Kod tabanının tuzakları burada değil, ayrı
bir "kod tuzakları" belgesinde durur (`delphi-pitfalls.md`, Türkçesi `tr/delphi-tuzaklari.md`); bu defter yapay zekânın kendi hatalarıdır.

## Neden ayrı bir defter

`CLAUDE.md`'ye her yanlıştan sonra bir cümle eklemek kısa sürede işe yaramaz hâle gelir: dosya şişer, kurallar birbirini
tekrar eder, "dikkatli ol" türü cümleler hiçbir şeyi değiştirmez. Defter bunu dört kuralla önler:

1. **Her madde kural + kontroldür.** Kontrol, yapılıp yapılmadığı görülebilen somut bir adımdır ("`grep` ile göster",
   "şu sorguyu çalıştır", "şunu sor"). "Dikkatli ol" kontrol değildir.
2. **Kısa tutulur.** Defter her oturumun başında yüklenir (`CLAUDE.md`'den `@docs/mistake-log.md`). Maddelerin
   hikâyesi — tarih, iş, ne oldu, kim buldu — ayrı bir kaynak dosyasında durur; o dosya oturum başında okunmaz.
3. **Yeni madde açmadan önce birleştirilir.** Tekrar edebilecek yeni bir hata önce var olan maddelere bakılarak işlenir:
   giriyorsa o maddenin kontrolü güçlendirilir; girmiyorsa tek kural + tek kontrol olarak eklenir. Bir kerelik
   talihsizlik eklenmez.
4. **Desenle yakalanabilen hata deftere değil hook'a girer;** adımları belli iş skill'e. Defter yalnız muhakeme
   gerektiren hatalar içindir.

Ayda bir gözden geçirilir; işe yaramadığı görülen madde silinir. Madde numaraları değişmez (başka belgeler numarayla
atıf yapar), birleştirilen maddeler köşeli parantezde eski numaralarını taşır. Yapay zekâ bir maddeyi silmeyi ya da
kontrolünü gevşetmeyi yalnız **önerir**; karar aylık gözden geçirmede geliştiricinindir. Ölçümle yanlışlığı gösterilen bir
kontrol aynı turda düzeltilir ve geliştiriciye ayrıca bildirilir.

## Madde şablonu

```
**[n] <Kural: tek cümle, emir kipi.>** <Gerekirse bir-iki cümle gerekçe.>
*Kontrol:* <yapılıp yapılmadığı görülebilen adım(lar)>.
```

## Başlangıç maddeleri

Aşağıdakiler eski bir Delphi + veritabanı projesinde aylar içinde biriken maddelerin projeye özgü olmayan kısmıdır.
Kendi defterinize alırken projenizin adlarıyla somutlaştırın.

### Teşhis ve ölçüm

**[1] Önce ölç, sonra düzelt; hipotezi ayırt edecek deneyi göster.** Koddan kurulan tutarlı bir hikâye ve "sayılar
tutuyor" hesabı kanıt değildir. Belirti kelimesi kelimesine okunur ("seçilemiyor" ≠ "görünmüyor").
*Kontrol:* teşhis koda dayanıyorsa düzeltmeden önce bir ölçüm satırı ya da tek değişkenli deneme önerilir; deneme ölçülen
değişkeni yan etkiyle değiştirmemeli, ölçülen yol kullanıcının kullandığı yol olmalı (belgeye yazılan komut, belgedeki
biçimiyle — yönlendirme ve boru dahil — denenir ve çıktısı bir sonraki adıma verilir; Windows'ta Python yönlendirilen çıktıyı
UTF-8 değil konsol kod sayfasıyla yazar). "X yüzünden yavaş" cümlesinden sonra
"bunu neyle ayırt ettim?" sorusuna sayaç ya da deney adıyla cevap yoksa önce o ölçüm konur.

**[2] Saklı bir değeri yorumlamadan önce onu kimin, ne zaman yazdığını doğrula.**
*Kontrol:* "bozuk" demeden ya da onarıma koymadan önce kolonun bütün yazanları listelenir (`grep -n "<Alan>.Value :="`,
saklı yordamlar, tetikleyiciler). Değeri okuyan ekranın açılış yolunda alanı yeniden yazan atama aranır. Satırın ne zaman
yazıldığı: PostgreSQL — satırın `xmin`'i (aynı işlemle yazılan satırlarda ortak; tarihi bilinen satırlarla karşılaştırılır);
SQL Server — tabloda varsa `rowversion` kolonu; MySQL / MariaDB ve Firebird — genel karşılık yok: değişiklik zamanı kolonu,
tetikleyici ya da binary log / trace.

**[3] Eski–yeni karşılaştırması yalnız aynı kaynaktan derlenmiş ve aynı biçimde çalıştırılmış exe ile yapılır.**
*Kontrol:* taban almadan önce hangi exe olduğu sorulur, derleme tarihi son commit'le karşılaştırılır. "Eski vermiyor / yeni
veriyor" üzerine kod değiştirmeden önce iki exe'nin aynı biçimde çalıştırıldığı sorulur (IDE'den mi, tek başına mı; aynı
parametre, veritabanı, adımlar).

**[4] Her belirti veride ayrı ölçülür.**
*Kontrol:* kapanış raporunda her belirti ayrı satırda: hangi ölçüm onu açıklıyor? Ölçümsüz kalan "koddan açıklandı, veride
doğrulanmadı" diye işaretlenir.

**[5] "Yok" ve "şu kadar" sonucunu doğrula.**
*Kontrol:* yokluk bildirilmeden önce arama harf duyarsız tekrarlanır ve aynı yöntemle var olduğu bilinen bir ad aranır
(pozitif de 0 ise yöntem bozuktur). Bir sayı raporlanmadan önce yinelenen satır olup olmadığına bakılır (`sort | uniq -d` boş dönmeli); kod
sayımında yorum satırları ayıklanır ve sonuçtan üç satır elle açılır.

**[6] Bir incelemenin (alt ajan) raporundaki iddia, kendi gözünle doğrulanmadan geliştiriciye olgu olarak sunulmaz.**
Rapor bir başka modelin çıktısıdır: yanlış da aynı güvenle gelir.
*Kontrol:* rapordan geliştiriciye taşınan her "kod şunu yapıyor" cümlesi için dosya:satır kendin açılır (çağrı yorumda mı,
dosyanın diskteki hâli ne); doğrulanmayan iddia "incelemenin bildirdiği, doğrulamadım" diye işaretlenir.

**[7] Analize kendi belgelerimizi aramadan başlanmaz.**
*Kontrol:* ilgili birim / yordam / tablo adlarıyla `grep -rn -i "<ad>" docs/*.md`; çıkan belge okunur, bulgu "belgede
vardı / yeni" diye ayrılır.

### Ekran, yol ve test

**[8] Formu, düğmeyi ve adını açılış yolundan ve DFM'den bul; koddaki addan tahmin etme.**
*Kontrol:* kullanıcının eyleminden (`OnClick` / `OnExecute`) hangi formun `Create` edildiği bulunur; adı benzeyen ikinci
form var mı bakılır. Çalışma anındaki `Caption :=` / `Visible :=` atamaları aranır. Test adımı yazarken nesnenin DFM'deki
üst zinciri (form → sekme → panel), `Caption`'ı **ve** `Visible`'ı okunur.

**[9] Test istemeden önce erişilebilirlik tablosu; test kaydında dalın gerçekten çalıştığını göster.**
*Kontrol:* değişen yordamın çağrıldığı her düğme / menü için `Visible` / `Enabled` atamaları okunur; koşul bayraklarının
anlamı adından değil atandığı yerden söylenir (`grep -n "<Bayrak> *:="`). "Aynı çıktı" ancak değişen satırın o kayıtta
çalıştığı gösterildikten sonra kabul edilir. Tetikleyici bayrağı açan yer yoksa yol "erişilemez" yazılır.

### Kapsam ve genelleme

**[10] Bir bulguyu genellemeden ya da sayı söylemeden önce bütün kaynakta ara; her yeri satırıyla göster.**
*Kontrol:*
- "Aynı kalıp X'te de var" → X'teki satır alıntılanır. "Ölü kod" → her çağrı satırı dalıyla listelenir.
- Bir kalıbın kopya sayısı söylenmeden önce bütün kaynakta desenle aranır. "Ölü" demeden önce çağrı satırının hangi
  gövdede olduğu `begin`/`end` eşleşmesiyle gösterilir: Pascal'da iç yordamlar sütun 0'dan yazılabiliyor. `tools/pas_callers.py`
  bunu yapar; kod geçişlerini, öbür `{$IF}` dallarını, DFM bağlarını, ad dizgelerini ve yorumları ayrı listeler.
- Toplu düzeltmeden önce her kopyaya ulaşan yol (DFM olay bağı ya da çağrı) gösterilir; erişim listesi düzenleme betiğinin
  girdisidir. Yolu olmayan kopyalar "ölü" diye ayrı listelenir ve bildirilir, düzeltilmez.

**[20] Bir çağrıyı kaldırmadan, daraltmadan, koşula bağlamadan ya da düzeltmenin yerini seçmeden önce çağıran tarafını ve
eski çağrının yaptığı her işi oku.**
*Kontrol:*
- Planda tablo bulunur: kaldırılan / daraltılan / koşula bağlanan her çağrı → eski çağrının yaptığı öbür işler (koşul
  **sağlanmadığında**, erken `exit`'ten önce; `Close` ya da temizlik yan etkileri) → test adımı. Bir silme "yalnız benim
  satırlarım"a daraltılınca ardından aynı tabloyu okuyan döngü ve sorgular yeniden okunur.
- Düzeltmeyi bir çağrının yanına koymadan önce yordamın bütün çağıranları listelenir; hepsi aynı eksiği taşıyorsa
  düzeltme yordamın içine gider. Bir formun olay işleyicisi değişmeden önce formu oluşturan her yer aranır.

**[11] Bir nesnenin anlamı değişecekse kapsam dört eksende sayılır:** (1) çağrılar — adın bütün yazılış biçimleriyle;
(2) konum değiştiren çağrıdan sonra aynı yordamdaki alan erişimleri; (3) DFM bağları (`DataSource` / `MasterSource` /
`DataSet`); (4) adı dizge olarak taşıyan yerler (`FindComponent`, şablon, `FieldByName('…')`).
*Kontrol:* sayı ikinci bir yöntemle (`tools/pas_callers.py`, farklı desen ya da `/review`) doğrulanır. DFM'de `DataSource` değiştiren her turdan
sonra `tools/dfm_field_check.py` çalıştırılır.

**[12] "Ne zaman bozuldu" aralığında önce kendi değişikliklerin.**
*Kontrol:* aralıktaki bütün kendi değişikliklerin dosya ve tarihleriyle listelenir (`git log --author`), sonra
başkalarınınki; önce logda o davranışın sayacı gün gün sayılır.

### Takımın sözlüğü ve iş kuralları

**[13] Takımın sözlüğünü ve iş kuralını tahmin etme.**
*Kontrol:* kararda kullanılacak bir alanın / durumun anlamından emin değilsen sorarsın; veriye bakarak iş kuralı
çıkarmazsın. Karar sorusu yazmadan önce alanın okuyanları ve eski kodun bugün ne yaptığı listelenir; soru yalnız eski
davranış korunamıyorsa sorulur.

### Veri ve düzeltmenin yeri

**[14] Kalıcı yan etki kesinleşme anına bağlanır; varsayım kodda zorlanır.**
*Kontrol:* veri değiştiren düzeltmede formun kaydet / uygula yeri bulunur, eski değer kayıttakiyle karşılaştırılır
(tıklamaya değil gerçek farka bağlanır). Yorum satırına giren varsayım ("tablo tekil", "alan dolu") aynı anda kodda da
garantiye alınır (`LIMIT 1`, kısıt, koşul).

**[15] Türetilmiş kolonu besleyen kaynak türetme çağrısından ÖNCE düzeltilir.**
*Kontrol:* düzeltilecek alanı kimin okuduğu ve okumanın düzeltmeden önce mi sonra mı olduğu kod sırasıyla doğrulanır.

### Delphi ve bileşen davranışı

**[16] VCL / bileşende masum görünen okuma, kopyalama, kilit ve geçici değişiklik yan etki taşır.**
*Kontrol:*
- Geçici değiştirilen durum (`Filtered`, `Enabled`, global): önceki değer saklanıp `try … finally` ile geri yüklenir
  (varsayılan hâline değil, bulunduğu hâline).
- Boş bir veri kümesinde `Edit` çağrısı `Insert` yapar (`Data.DB` `TDataSet.Edit`); "yalnız düzenliyorum" sanılan kod satır
  ekleyebilir.
- Kilit (`BeginUpdate`, `DisableControls`) eklemeden önce bileşen kaynağında hangi koşullarda kullanıldığı aranır.
- Izgaranın `OnGetCellParams`'ında verilen hücre kilidi (`Params.ReadOnly`) `EditMode = True` çağrısında da verilir: EhLib
  düzenleme iznini tam öyle soruyor (`TAxisBarEh.CanModify`). `if EditMode then Exit` yalnız renk ve metin için. Test
  adımına "kilitli hücreye çift tıkla, yazmayı dene" girer.

**[17] Derlemenin yakaladığı iki tuzak.** Delphi yorumunda `{ }` iç içe olmaz (içinde `{` geçen yorum `//` ile); anonim
metot iç içe yordamı, `var` / `out` parametreyi ve `Result`'ı yakalayamaz (E2555). Ayrıntı: `delphi-tuzaklari.md` §26.
*Kontrol:* `/build-check`.

### Dosyaya ve belgeye yazma

**[18] Pascal'a yazma kuralları — çoğunu araç denetliyor.**
- Hook reddeder / bildirir: gömülü Python, korunan dosyada `sed -i`, yeni tek LF, yanlış kodlamayla kaydedilmiş dosya.
- Pascal / DFM dosyaları `tools/pas_edit.py` ile değişir: kod sayfasını ve CRLF'i korur, tam bir kez geçmeyen çapayı
  reddeder, aramayı tek bir yordamla sınırlayabilir (kopya yordamlar aynı çapayı taşır) ve `additions_only` ile var olan bir
  satırı silecek ya da değiştirecek düzenlemeyi reddeder.
- *Elle kontrol:* geliştiricinin diskte düzelttiği dosya yeniden yazılmadan önce diskteki sürümü okunur. Düzenlemeden sonra
  `git diff --ignore-cr-at-eol -- <dosya>` yalnız istenen satırları gösterir; yazılan metin `grep` ile doğrulanır.

**[19] Kapanış: düzeltme kodda etkin mi, belgeler güncel mi.**
*Kontrol:* düzeltme satırı bugünkü kaynakta `grep` ile gösterilir; konuyu anan öbür belgeler `grep -ln` ile bulunur ve her
biri raporda "güncellendi / etkilenmedi" diye yazılır (`/close-out`).
