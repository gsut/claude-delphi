# claude-delphi

[![tests](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml/badge.svg)](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../../LICENSE)

> Bu belge [`README.md`](../../README.md)'nin Türkçe çevirisidir; çelişkide İngilizce sürüm esastır.

Eski bir **Delphi VCL + veritabanı** kod tabanında [Claude Code](https://claude.com/claude-code) ile güvenli çalışmak için
hook'lar, skill'ler, ajanlar, küçük araçlar ve bir çalışma yöntemi.

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
| Aynı yanlışı oturumdan oturuma tekrarlar; `CLAUDE.md` şişer | `docs/mistake-log.md`: kısa, her madde **kural + kontrol** |

## İçerik

```
hooks/
  command_guard.py         PreToolUse (Bash): gömülü Python, korunan dosyada sed -i / yönlendirme, yazma yetkili DB kullanıcısı
  pascal_check.py          PostToolUse: yeni tek LF, yanlış kodlama, projeye özel yasak ifadeler, çift imza
build/
  build.bat, summary.py    komut satırı derlemesi + uyarı tabanı farkı
tools/
  pas_edit.py              Pascal / DFM dosyalarında güvenli değiştirme: kod sayfası + CRLF korunur, çapa tam bir kez geçmeli,
                           istenirse yalnız adı verilen yordamın içinde, istenirse "yalnız ekleme" denetimi
  pas_callers.py           bir yordamın bütün geçişleri: kod (içinde bulunduğu yordamla), öbür {$IF} dalları, DFM bağları,
                           ad dizgeleri, yorumlar; kanıtlı ölü kod kararı
  pascal_lex.py            araçların kullandığı küçük Pascal çözümleyicisi (iç yordamlar, {$IF} dalları)
  dfm_field_check.py       DataSource'a bağlı kontrolün alanı veri kümesinde var mı
  dfm_field_usage.py       verilen alan adları hangi DFM denetimlerine bağlı
  pg_fingerprint.py        bir kaydın bütün tablolardaki satırlarının parmak izi, önce / sonra farkı
.claude/
  skills/                  build-check, triage, review, multi-review, close-out
  agents/                  scope-counter, devils-advocate (multi-review için)
docs/
  mistake-log.md           yöntem, şablon ve 19 başlangıç maddesi            (Türkçesi: tr/hata-defteri.md)
  delphi-pitfalls.md       22 tekrar eden Delphi + veritabanı tuzağı          (Türkçesi: tr/delphi-tuzaklari.md)
  build-baseline.md        derleme denetiminin ayrıntısı ve tuzakları         (Türkçesi: tr/derleme-tabani.md)
  case-study.md            adım adım gerçek bir vaka: boş ikiz satırlar       (Türkçesi: tr/vaka.md)
  tr/                      Türkçe çeviriler
tests/                     hook'lar, derleme özeti ve araçlar için unittest takımı
examples/
  CLAUDE.md                ekip kuralları şablonu
  settings.json            hook bağlantıları + Git yazma komutlarını engelleyen izinler
  claude-delphi.json       hook ayarları (kod sayfası, uzantılar, yasak ifadeler, DB kullanıcıları, işaretler)
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

1. `hooks/*.py` → projenizin `.claude/hooks/` dizinine; `tools/` → projede bir `tools/` dizinine (`pas_edit.py`,
   `pas_callers.py` ve `pascal_lex.py` birlikte durmalı; hook mesajları `tools/pas_edit.py`'yi gösterir).
2. `examples/settings.json` → `.claude/settings.json` (varsa birleştirin). `python` yolda olmalı.
3. `examples/claude-delphi.json` → `.claude/claude-delphi.json`; aşağıdaki *Yerelleştirme* bölümüne göre düzenleyin.
4. `.claude/skills/` ve `.claude/agents/` → projenizin `.claude/` dizinine.
5. `build/` → proje içinde bir dizine; `build.bat`'ta (ya da ortam değişkeniyle) `DELPHI_RSVARS`, `DELPHI_DPROJ`,
   `DELPHI_CONFIG`, `DELPHI_PLATFORM`. `.bat` dosyası CRLF kalmalı. İlk çalıştırma: `build.bat baseline`.
6. `examples/CLAUDE.md` → proje köküne; köşeli parantezli yerleri doldurun. `docs/mistake-log.md`'yi kendi defterinizin
   başlangıcı yapın ve `CLAUDE.md`'den `@` ile yükleyin.

Hook'lar yeni ihlali eskisinden Git'e bakarak ayırır; proje bir Git deposu olmalı.

## Testler

```
python -m unittest discover -s tests -v
```

Yalnız standart kütüphane (pytest gerekmez); `git` yolda olmalı. Testler Pascal örneklerini çalışma anında üretir, kod sayfası
ve CRLF denetimi Git'in depoyu nasıl çıkardığına bağlı kalmaz. CI, Windows ve Ubuntu'da çalıştırır (`.github/workflows/tests.yml`).

Yöntemin iş başında nasıl göründüğü için: [vaka](vaka.md).

## Yerelleştirme

Claude'un okuduğu her şey (skill'ler, ajanlar, hook mesajları) İngilizcedir ve **çevrilmez**: Claude İngilizce talimatı her
dilde aynı iyi izler, talimatların çevrilmiş kopyaları zamanla birbirinden ayrışır. Yerel bir ekibin ayarlaması gereken
metin değil, yapılandırmadır:

| Ne | Nerede |
|---|---|
| Cevap ve raporların dili | `CLAUDE.md`'de tek satır: "Communicate with the developer in Turkish." |
| Kaynak kod sayfası | `claude-delphi.json` → `source_encoding`: `cp1254` (Türkçe), `cp1252`, `cp1250`, `cp1251` ... |
| Yorum imzasındaki tarih biçimi | `date_format` (strftime, ör. `%d.%m.%Y`) ve `signature_pattern` (`{date}` yer tutucusu; boş = denetim kapalı) |
| Koddaki işaretler | `measure_marker` (varsayılan `X-MEASURE`), `dead_code_marker` (varsayılan `DEAD-CODE`); Türkçe ekip `X-OLCUM` / `OLU-KOD` seçebilir |
| Yerelleştirilmiş derleyici / MSBuild çıktısı | bir şey yapmaya gerek yok: `build/summary.py` mesajı koddan (`E`, `F`, `W`, `H`, `MSB`) sınıflar; IDE dili değişince yeni taban alınır |
| DFM'deki ASCII dışı karakterler | DFM'ler bunları ayarlı kod sayfasının `#nnn` kaçışlarıyla saklar; araçlar DFM'yi Latin-1 okur ve yalnız ASCII özellik adlarını karşılaştırır; `pas_edit.py` DFM'ye ASCII dışı karakter yazmayı reddeder |

İnsanın okuduğu belgeler (README, `docs/`) İngilizcedir; çeviriler `docs/<dil>/` altında durur. Çelişkide İngilizce sürüm
esastır.

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

- **Önce hipotez, sonra onay, sonra düzeltme.** Yapay zekâ "sebep şu, kanıtım bu, şu ölçüm ayırt eder" der ve durur.
- **Önce ölç.** Geçici ölçüm satırları işaretli eklenir, iş bitince silinir.
- **Cerrahi değişiklik, ama kopyalar birleştirilir.**
- **Ölü kod silinmez, kanıtla işaretlenir** (`// DEAD-CODE: <kanıt>`); silme ayrı bir karardır.
- **Git ve veritabanı yapay zekâ için salt okunur.**
- **Kör ikinci okuma.** Yapısal değişiklikte bağımsız bir ajana planın sonucu değil, yalnız ne değişeceği verilir; ajanın
  bulguları kaynakta doğrulanmadan geliştiriciye olgu olarak sunulmaz.
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

## Katkı

Bkz. [CONTRIBUTING.md](../../CONTRIBUTING.md) (İngilizce): yeni tuzaklar, hata defteri maddeleri, çeviriler ve başka
ortamlardan raporlar memnuniyetle karşılanır. Değişiklikler: [CHANGELOG.md](../../CHANGELOG.md).

## Lisans

[MIT](../../LICENSE)
