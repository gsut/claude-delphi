# Komut satırı derlemesi ve uyarı tabanı

> Bu belge [`docs/build-baseline.md`](../build-baseline.md)'nin Türkçe çevirisidir; çelişkide İngilizce sürüm esastır.

## Neden

Yapay zekâ bir Pascal değişikliğini teslim etmeden önce derlendiğini ve **yeni** uyarı getirmediğini kendisi doğrulamalı.
Eski projelerde binlerce uyarı ve ipucu vardır; "uyarı yok" ölçütü anlamsızdır. Ölçüt: **hata 0 ve tabana göre yeni uyarı /
ipucu 0.** Yeni uyarı çıkarsa ya giderilir ya raporda gerekçesiyle söylenir.

Derleme geliştiricinin çalışmasıyla çakışmaz: ayrı exe, ayrı dcu, ayrı log (`build\out\`, `build\log\`).

## Yapı

```
build\
  build.bat        msbuild sarmalayıcı (rsvars + yapılandırma + çıktı yönlendirme + özet)
  summary.py       log özeti: hatalar, tabana göre YENİ uyarılar (dilden bağımsız)
  out\exe\         Claude'un exe'si (çalıştırılmaz)
  out\dcu\
  log\last.log     son derlemenin tam msbuild çıktısı
  log\baseline.txt uyarı tabanı (anahtar: dosya + kod + mesaj; satır no yok)
```

Depoya girenler: `build.bat`, `summary.py`, `log\baseline.txt`. `out\` ve `log\last.log` `.gitignore`'a.

## Kullanım

```
cmd //c "build\build.bat"            derle + tabanla karşılaştır
cmd //c "build\build.bat" baseline   derle + uyarıları taban yap
```

Çıktı örneği:

```
msbuild exit code: 0  errors: 0  warnings: 2221  hints: 4851
new warnings/hints vs baseline: 0
in baseline but no longer present: 52
```

**Taban ne zaman yenilenir:** geliştiricinin commit'inden sonraki ilk derlemede (son commit değiştiyse ve çalışma ağacında
yapay zekânın kendi değişikliği yokken) ya da geliştirici istediğinde. Kendi değişikliği diskteyken taban alınmaz: yeni
uyarıları tabana gömer.

## Yerelleştirilmiş derleyici

Almanca, Fransızca, Japonca Delphi (ve yerelleştirilmiş MSBuild) mesaj türünü kendi dilinde yazar ("Warnung",
"avertissement", ...). Bu yüzden `summary.py` kelimeye hiç bakmaz; türü koddan alır: `E`/`F` hata, `W` uyarı, `H` ipucu,
MSBuild `MSBnnnn` kodları. Taban anahtarları mesaj metnini içerir; IDE dili değiştikten sonra yeni taban alınır.

## Kurulumda görülen tuzaklar

- `.bat` dosyası **CRLF** olmalı; LF ile `cmd` satır başlarını yutar (`'d' is not recognized`).
- Proje ya da yol adında ASCII dışı karakter varsa betikte `chcp 65001` şart; yoksa `MSB1009: Proje dosyası yok`.
- `msbuild /clp:Summary` uyarıları özet bölümünde ikinci kez yazar; sayım iki katı çıkar. Betikte özet kapalı.
- Kütüphane yolları IDE'nin `%APPDATA%\Embarcadero\BDS\<sürüm>\EnvOptions.proj`'undan gelir; IDE'de yol değişirse komut
  satırı derlemesi de değişir.
- Komut satırı derlemesi dosyaları diskten okur. IDE ise açık veri modülünün bellek kopyasıyla derleyebilir; veri modülü
  dışarıdan değiştiyse IDE'de proje kapatılıp açılmalı (raporda söylenir).

## Git'te fark okuma

Depo LF saklayıp çalışma ağacı CRLF kullanıyorsa (otomatik çeviri), betikle yeniden yazılan bir Pascal dosyası `git diff`'te
bütünüyle değişmiş görünür. Gerçek fark için `git diff --ignore-cr-at-eol` (ve `--stat`).

## Eski sürümle karşılaştırma (Git yalnız okuma)

Çalışma ağacı değiştirilmez (`checkout` / `stash` ayarlarla engelli). Eski kaynak gerekiyorsa:

```
mkdir -p build/old && git archive <rev> <yol>/Birim.pas | tar -x -C build/old
mkdir -p build/old_source && git archive <rev> <dizin> | tar -x -C build/old_source
```

`git show <rev>:<yol>` yalnız ekranda okumak içindir: `hooks/command_guard.py` `.pas` dosyasına kabuk yönlendirmesini
reddeder. İki dizin de `.gitignore`'a girer.
