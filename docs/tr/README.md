# claude-delphi

[![tests](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml/badge.svg)](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../../LICENSE)

> Bu belge [`README.md`](../../README.md)'nin Türkçe çevirisidir; çelişkide İngilizce sürüm esastır.

Eski bir **Delphi VCL + veritabanı** kod tabanında [Claude Code](https://claude.com/claude-code)'dan **doğru** iş almak için
hook'lar, skill'ler, ajanlar, küçük araçlar ve bir çalışma yöntemi.

> **Amaç token tasarrufu değil, çalışmanın doğruluğudur.** Bu depodaki her parça yapay zekânın işini doğru yapmak için
> var: teşhisi, değişikliği ve raporu. Adımların çoğu bilerek token ve zaman harcar: düzeltmeden önce ölçüm, değişikliği
> planın sonucunu bilmeden okuyan bağımsız bir ajan, ikinci bir yöntemle tekrarlanan sayım, tek satırlık bir değişiklikten
> sonra bile kapanış denetimi. Eski bir kod tabanında pahalı olan uzun bir oturum değildir; derlenen, akla yatkın görünen ve
> müşterinin verisine ulaşan yanlış bir düzeltmedir. Daha ucuz bir oturumla daha güvenilir bir sonuç arasında seçim
> gerektiğinde bu depo güvenilir sonucu seçer. Bir adım ancak ölçüm onun hiçbir şey yakalamadığını gösterirse bırakılır;
> yalnız token kazanmak için asla.

Gerçek bir projede (yüzlerce birim, binlerce derleme uyarısı, ANSI kod sayfalı kaynaklar, çok kiracılı veritabanı) aylarca
günlük kullanılarak biriktirildi. Projeye özgü olan her şey çıkarıldı; kalan, başka Delphi projelerine uyarlanabilecek çekirdek.

> **Durum:** örnek ve yöntem olarak paylaşılıyor; destek verilmiyor. Claude Code'un hook / skill biçimi değişebilir; mekanik
> kısım eskiyebilir, yöntem eskimez.

## Neyi çözüyor

| Sorun | Bu depodaki karşılığı |
|---|---|
| `cp1252` / `cp1254` kaynağı UTF-8 kaydeder, CRLF'i LF'ye çevirir | `hooks/pascal_check.py` (Git'teki hâle göre yalnız **yeni** ihlali bildirir) |
| `sed -i`, `>` yönlendirmesi, komut satırına gömülü betikle dosya bozar | `hooks/command_guard.py` (çalışmadan önce reddeder) ve `tools/pas_edit.py` (doğru yolu) |
| Yazma yetkili kullanıcıyla veritabanına bağlanır | `hooks/command_guard.py` + salt okunur kullanıcı kuralı |
| Değişikliği derlemeden teslim eder; binlerce eski uyarı arasında yenisini göremez | `build/build.bat` + `summary.py`: **hata 0 ve tabana göre yeni uyarı 0**, dilden bağımsız |
| DFM'deki alan bağlarını göremez (alanı silip ekranı kırar, bağlı kodu "ölü" sanar) | `tools/dfm_field_check.py`, `tools/dfm_field_usage.py` |
| İç yordamı, DFM olayını ya da yoruma alınmış çağrıyı kaçıran bir grep'ten sonra kodu "ölü" sanar | `tools/pas_callers.py` (geçişler türüne göre ayrı, içinde bulunduğu yordamla) |
| "Bu işlem başka neye dokundu?" sorusunu koddan tahmin eder | `tools/pg_fingerprint.py` (önce / sonra parmak izi; PostgreSQL) |
| Koddan güzel bir hikâye kurup ölçmeden düzeltir | `/triage`: hipotez + kanıt + ayırt edici ölçüm, **kod yok** |
| Kendi planını doğrulayan bir alt ajandan "onay" alır | `/review`, `/multi-review`: ajana sonuç değil yalnız değişiklik verilir, kapsam dört eksende sayılır |
| Plan yarım uygulanmışken ya da plan dışı bir yere dokunulmuşken işe "bitti" der | `/close-out` 2b adımı: `tools/diff_routines.py` farkı plana göre yordamlara / DFM nesnelerine eşler, ardından `closeout-auditor` ajanı plan ↔ fark karşılaştırması yapar ve kırılma arar; commit'ten önce |
| Aynı yanlışı oturumdan oturuma tekrarlar; `CLAUDE.md` şişer | `docs/mistake-log.md`: kısa, her madde **kural + kontrol** |

## İçerik

```
hooks/
  command_guard.py         PreToolUse (Bash): gömülü Python, korunan dosyada sed -i / yönlendirme, yazma yetkili DB kullanıcısı,
                           GitHub'a yazan gh komutları (gh salt okunur kalır)
  pascal_check.py          PostToolUse: yeni tek LF, yanlış kodlama, projeye özel yasak ifadeler, çift imza
build/
  build.bat, summary.py    komut satırı derlemesi + uyarı tabanı farkı
tools/
  pas_edit.py              Pascal / DFM dosyalarında güvenli değiştirme: kod sayfası + CRLF korunur, çapa tam bir kez geçmeli,
                           istenirse yalnız adı verilen yordamın içinde, istenirse "yalnız ekleme" denetimi; --reverse
                           uygulanmış bir spec'i geri alır (ör. geçici ölçüm satırlarını siler)
  pas_callers.py           bir yordamın bütün geçişleri: kod (içinde bulunduğu yordamla), öbür {$IF} dalları, DFM bağları,
                           ad dizgeleri, yorumlar; kanıtlı ölü kod kararı
  pascal_lex.py            araçların kullandığı küçük Pascal çözümleyicisi (iç yordamlar, {$IF} dalları)
  dfm_field_check.py       DataSource'a bağlı kontrolün alanı veri kümesinde var mı
  dfm_field_usage.py       verilen alan adları hangi DFM denetimlerine bağlı
  pg_fingerprint.py        bir kaydın bütün tablolardaki (public şeması) satırlarının parmak izi, önce / sonra farkı
  diff_routines.py         değişiklik haritası: her fark parçası yordamına (Pascal) ya da nesne zincirine (DFM) eşlenir,
                           planda adı geçmeyenler işaretlenir; çalışma ağacı, tek commit ya da aralık
.claude/
  skills/                  build-check, triage, review, multi-review, close-out
  agents/                  scope-counter, devils-advocate (multi-review için), closeout-auditor (close-out için)
docs/
  mistake-log.md           yöntem, şablon ve 20 başlangıç maddesi            (Türkçesi: tr/hata-defteri.md)
  delphi-pitfalls.md       26 tekrar eden Delphi + veritabanı tuzağı          (Türkçesi: tr/delphi-tuzaklari.md)
  build-baseline.md        derleme denetiminin ayrıntısı ve tuzakları         (Türkçesi: tr/derleme-tabani.md)
  case-study.md            adım adım gerçek bir vaka: boş ikiz satırlar       (Türkçesi: tr/vaka.md)
  tr/                      Türkçe çeviriler
tests/                     hook'lar, derleme özeti ve araçlar için unittest takımı
examples/
  CLAUDE.md                ekip kuralları şablonu
  settings.json            hook bağlantıları + Git yazma komutlarını engelleyen izinler
  claude-delphi.json       hook'ların, araçların ve skill'lerin okuduğu ayarlar (kod sayfası, uzantılar, yasak ifadeler, DB kullanıcıları, işaretler)
  readonly-user.postgresql.sql   Claude için salt okunur veritabanı kullanıcısı (PostgreSQL)
```

## Gereksinimler

Pip paketi yok: her şey Python'un standart kütüphanesiyle çalışır.

| Gereksinim | Kim kullanıyor | Not |
|---|---|---|
| **Python 3.11+**, `python` adıyla yolda | hook'lar, araçlar, `summary.py`, testler | CI, Windows ve Ubuntu'da 3.11 ve 3.13 ile çalışır; daha eski 3.x sürümleri çalışabilir ama denenmedi. `settings.json` `python -I …` çağırır; Linux / macOS'ta komut `python3` ise orada değiştirin. |
| **Git**, yolda | `pascal_check.py` (yeni ihlali eskisinden ayırır), testler | Proje bir Git deposu olmalı. |
| **Claude Code**, skill ve alt ajan destekleyen bir sürüm | hook'lar, `.claude/skills/`, `.claude/agents/` | `/multi-review` iki alt ajanı paralel başlatır. |
| **Delphi 2007 ve sonrası** (`.dproj`, `msbuild`, `rsvars.bat`) | yalnız `build/` | Lisans komut satırı derleyicisini kapsamalı; Community Edition doğrulanmadı. |
| **psql** (PostgreSQL istemcisi) + salt okunur kullanıcı | yalnız `pg_fingerprint.py` | Başka veritabanında kullanılmaz. |
| **Windows + Git Bash** | önerilen ortam | Her şey burada yazıldı ve kullanıldı; `build.bat` yalnız Windows. Hook'lar ve araçlar Linux'ta da çalışmalı (CI'da Ubuntu var), ama gerçek bir Linux Delphi ortamında denenmedi. |

## Kurulum

Aşağıdaki yollar proje köküne göredir (`.dpr`'nin bulunduğu dizin; bir Git deposu olmalı).

1. `hooks/*.py` → projenizin `.claude/hooks/` dizinine; `tools/` → projede bir `tools/` dizinine (`pas_edit.py`,
   `pas_callers.py`, `diff_routines.py` ve `pascal_lex.py` birlikte durmalı; hook mesajları `tools/pas_edit.py`'yi gösterir).
2. `examples/settings.json` → `.claude/settings.json` (varsa birleştirin). `python` yolda olmalı.
3. `examples/claude-delphi.json` → `.claude/claude-delphi.json`; aşağıdaki tabloya ve *Yerelleştirme* bölümüne göre düzenleyin.
4. `.claude/skills/` ve `.claude/agents/` → projenizin `.claude/` dizinine.
5. `build/` → proje kökünde `build\` olarak (derleme skill'i `build\build.bat`'ı çağırır; varsayılan olarak
   `..\Project.dproj`'u derler). `build.bat`'ta (ya da ortam değişkeniyle) `DELPHI_RSVARS`, `DELPHI_DPROJ`, `DELPHI_CONFIG`,
   `DELPHI_PLATFORM`. `.bat` dosyası CRLF kalmalı. İlk çalıştırma: `build.bat baseline`.
6. `examples/CLAUDE.md` → proje köküne; `<…>` yerlerini doldurun. `docs/mistake-log.md` ve `docs/delphi-pitfalls.md`'yi
   projede bir `docs/` dizinine kopyalayın: `CLAUDE.md` hata defterini `@docs/mistake-log.md` ile yükler, defter de kendi
   defterinizin başlangıcı olur. `CLAUDE.md`'nin andığı ama henüz sizde olmayan belgeler (ekran akış haritası, tablo → kod
   dizini, defterin hikâye dosyası) siz yazana kadar atlanır.
7. Depoya girmeyen bir kişisel dizin açın (ör. `personal/`): onaylanan planlar (`personal/plans/<id>-plan.md`, kapanış
   denetimi buradan okur), `pas_edit.py` spec'leri, açık işler listesi, log kopyaları. Kişisel ayarlar (yorum imzasındaki baş
   harfler, bu dizinin yolu) `CLAUDE.local.md`'ye.
8. `.gitignore`'a: `__pycache__/`, `build/out/`, `build/log/last.log`, `build/old/`, `build/old_source/`,
   `CLAUDE.local.md`, `.claude/settings.local.json` ve kişisel dizin. (İzlenmeyen dosyalar `tools/diff_routines.py`'nin
   değişiklik haritasında da görünür.)
9. Claude'a salt okunur bir veritabanı kullanıcısı verin (`examples/readonly-user.postgresql.sql`; diğer veritabanları
   *Veritabanları* bölümünde) ve yazma yetkili kullanıcıları `write_db_users`'a yazın.
10. Yeni bir Claude Code oturumu açıp hook'ları deneyin: Claude'dan `sed -i "s/a/b/" <bir birim>.pas` çalıştırmasını isteyin —
    reddedilmeli.

`pas_edit.py` ve `diff_routines.py` `.claude/claude-delphi.json`'ı `$CLAUDE_PROJECT_DIR`'dan, yoksa bulunduğu dizinden
yukarı çıkarak bulur; `pas_callers.py` ve DFM araçları `--root` alır (varsayılan: bulunulan dizin), onları proje kökünden
çalıştırın.

| `claude-delphi.json` ayarı | Anlamı |
|---|---|
| `source_encoding`, `pascal_extensions`, `protected_extensions` | hook'ların ve araçların Pascal saydığı / `sed -i` ve yönlendirmeden koruduğu kod sayfası ve dosya türleri |
| `write_db_users` | yazma yetkili veritabanı kullanıcıları; bunlardan biriyle bağlanan komut reddedilir |
| `scripts_dir` | tek kullanımlık betiklerin yazıldığı (Write) ve yoluyla çalıştırıldığı dizin; gömülü Python yerine |
| `forbidden_patterns` | değişen Pascal dosyasına eklendiğinde bildirilen projeye özgü desenler, ör. `{"pattern": "BoolToStr\\s*\\([^)]*,\\s*True\\s*\\)", "message": "use BoolToStr(x)"}`; varsayılan boş |
| `signature_pattern`, `date_format` | yorum imzası denetimi (*Yerelleştirme*); desen boşsa kapalı |
| `measure_marker`, `dead_code_marker` | skill'lerin ve `CLAUDE.md`'nizin kullandığı işaretler; hook'lar okumaz |
| `forbid_inline_python`, `forbid_gh_write` | gömülü Python ve GitHub CLI yazma kurallarını kapatır (varsayılan açık) |

## Testler

```
python -m unittest discover -s tests -v
```

Yalnız standart kütüphane (pytest gerekmez); `git` yolda olmalı. Testler Pascal örneklerini çalışma anında üretir, kod sayfası
ve CRLF denetimi Git'in depoyu nasıl çıkardığına bağlı kalmaz. CI, Windows ve Ubuntu'da çalıştırır (`.github/workflows/tests.yml`).

## Yerelleştirme

Claude'un okuduğu her şey (skill'ler, ajanlar, hook mesajları) İngilizcedir ve **çevrilmez**: Claude İngilizce talimatı her
dilde aynı iyi izler, talimatların çevrilmiş kopyaları zamanla birbirinden ayrışır. Yerel bir ekibin ayarlaması gereken
metin değil, yapılandırmadır:

| Ne | Nerede |
|---|---|
| Cevap ve raporların dili | `CLAUDE.md`'de tek satır: "Communicate with the developer in Turkish." |
| Kaynak kod sayfası | `claude-delphi.json` → `source_encoding`: `cp1254` (Türkçe), `cp1252`, `cp1250`, `cp1251` ... — tek baytlı kod sayfaları; çok baytlılar (ör. `cp932` Japonca) denenmedi, `pas_callers.py` tek bayt varsayar |
| Yorum imzasındaki tarih biçimi | `date_format` (strftime, ör. `%d.%m.%Y`) ve `signature_pattern` (`{date}` yer tutucusu; boş = denetim kapalı) |
| Koddaki işaretler | `measure_marker` (varsayılan `X-MEASURE`), `dead_code_marker` (varsayılan `DEAD-CODE`); skill'ler okur ve `CLAUDE.md`'nizde anılır, hook'lar okumaz; Türkçe ekip `X-OLCUM` / `OLU-KOD` seçebilir |
| Yerelleştirilmiş derleyici / MSBuild çıktısı | bir şey yapmaya gerek yok: `build/summary.py` mesajı koddan (`E`, `F`, `W`, `H`, `MSB`) sınıflar; IDE dili değişince yeni taban alınır |
| DFM'deki ASCII dışı karakterler | DFM'ler bunları ayarlı kod sayfasının `#nnn` kaçışlarıyla saklar; araçlar DFM'yi Latin-1 okur ve yalnız ASCII özellik adlarını karşılaştırır; `pas_edit.py` DFM'ye ASCII dışı karakter yazmayı reddeder |

İnsanın okuduğu belgeler (README, `docs/`) İngilizcedir; çeviriler `docs/<dil>/` altında durur. Çelişkide İngilizce sürüm
esastır. Çeviri katkıları memnuniyetle karşılanır.

## Veritabanları

Paket belirli bir veritabanına bağlı değildir:

| Parça | Veritabanı bağımlılığı |
|---|---|
| `pascal_check.py`, `build/`, DFM araçları, skill'ler, ajanlar | yok |
| `command_guard.py` yazma yetkili kullanıcı kuralı | yok — kullanıcı adını `psql`, `sqlcmd`, `mysql` / `mariadb`, Firebird `isql` seçeneklerinde, ortam değişkenlerinde (`PGUSER`, `MYSQL_USER`, `ISC_USER`, `SQLCMDUSER`), bağlantı dizelerinde (`User ID=`, `UID=`, `user=`) ve URL'lerde (`ad:şifre@sunucu`) yakalar |
| `tools/pg_fingerprint.py` | **PostgreSQL** — örnek; başka veritabanı için fikir taşınır: her satır için kimlik + kimliksiz içeriğin özeti |
| `examples/readonly-user.postgresql.sql` | **PostgreSQL** — diğerlerinde: SQL Server `db_datareader` rolü, MySQL / MariaDB `GRANT SELECT`, Firebird tablo başına `GRANT SELECT` / salt okunur rol |
| `docs/` içindeki teşhis ipuçları | PostgreSQL örnekleri, yanlarında SQL Server, MySQL / MariaDB ve Firebird karşılıkları |

Veritabanı hangisi olursa olsun Claude'a **salt okunur bir kullanıcı** verin, yazma yetkili kullanıcıları `write_db_users`'a yazın.

## Yöntem (kısaca)

Yöntemin iş başında nasıl göründüğü için: [vaka](vaka.md) — ya da hikâyeyi Medium'da okuyun:
[Boş İkiz Satırlar: Eski Bir Delphi Projesinde Claude Code ile Çalışmak](https://medium.com/@gokhan.sut_29411/bo%C5%9F-i%CC%87kiz-sat%C4%B1rlar-eski-bir-delphi-projesinde-claude-code-ile-%C3%A7al%C4%B1%C5%9Fmak-09940981f2dc).

- **Önce hipotez, sonra onay, sonra düzeltme.** Yapay zekâ "sebep şu, kanıtım bu, şu ölçüm ayırt eder" der ve durur.
- **Önce ölç.** Geçici ölçüm satırları işaretli eklenir, iş bitince silinir.
- **Cerrahi değişiklik, ama kopyalar birleştirilir.** Komşu koda dokunulmaz; aynı düzeltmeyi bir yordamın her kopyasına
  eklemek yerine kopyalar ortak bir yordamda birleştirilir.
- **Ölü kod silinmez, kanıtla işaretlenir** (`// DEAD-CODE: <kanıt>`); silme ayrı bir karardır.
- **Git ve veritabanı yapay zekâ için salt okunur.** Commit, dağıtım ve veri değiştiren betikler geliştiricinindir.
- **Kör ikinci okuma.** Yapısal değişiklikte bağımsız bir ajana planın sonucu değil, yalnız ne değişeceği verilir; ajanın
  bulguları kaynakta doğrulanmadan geliştiriciye olgu olarak sunulmaz.
- **Commit'ten önce bağımsız denetim.** Onaylanan plan koddan önce dosyaya yazılır; kapanışta işi yapmamış bir ajan onu
  farkla karşılaştırır.
- **Her işin sonunda:** nasıl yapıldı, asıl hata neydi, yapay zekânın kendi yanlışı neydi. Tekrar edebilecek yanlış aynı
  turda hata defterine; desenle yakalanabilen yanlış hook'a.

## Sınırlar

- Windows + Git Bash ortamında yazıldı ve kullanıldı.
- Derleme denetimi yalnız Delphi 13 / Win32'de denendi. `.dproj` projesi gerekir (Delphi 2007 ve sonrası); daha eski
  projeler (`.dof` / `.cfg`) `dcc32`'yi doğrudan çağırmalı. Başka Delphi sürümünde `DELPHI_RSVARS` verilir
  (ör. 12 Athens `Studio\23.0`, 11 Alexandria `Studio\22.0`).
- Delphi yükseltmesinden sonra ilk derlemede yeni taban alınır (`build.bat baseline`): yeni derleyici yeni uyarılar ve
  değişmiş mesaj metinleri getirir.
- Doğrulanmadı: Delphi Community Edition'ın lisansı komut satırı derleyicisini kapsıyor mu. Kapsamıyorsa `build.bat` çalışmaz;
  hook'lar ve araçlar yine çalışır.
- `pg_fingerprint.py` ve salt okunur kullanıcı betiği PostgreSQL örnekleridir (bkz. *Veritabanları*).
- DFM araçları metin DFM'leri okur (ikili DFM'ler desteklenmez).
- `pascal_check.py` bütünüyle UTF-8 kaydedilmiş dosyayı yakalar; ANSI dosyaya eklenmiş birkaç UTF-8 satırı yakalamaz.
- `pas_edit.py` uygulanmış spec'i hatırlamaz: aynı "yalnız ekleme" spec'i iki kez uygulanırsa satırlar iki kez eklenir.
- `pascal_check.py`'nin yerleşik `date_format` varsayılanı `%d.%m.%Y`, örnek ayarlar `%Y-%m-%d` kullanır; açıkça verin.

## Katkı

Bkz. [CONTRIBUTING.md](../../CONTRIBUTING.md) (İngilizce): yeni tuzaklar, hata defteri maddeleri, çeviriler ve başka
ortamlardan raporlar memnuniyetle karşılanır. Değişiklikler: [CHANGELOG.md](../../CHANGELOG.md).

## Lisans

[MIT](../../LICENSE)
