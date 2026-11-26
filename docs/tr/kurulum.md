# Kurulum ve yapılandırma

> Bu belge [`docs/installation.md`](../installation.md)'nin Türkçe çevirisidir; çelişkide İngilizce sürüm esastır.
> README'ye dön: [README](README.md)

## Gereksinimler

Pip paketi yok: her şey Python'un standart kütüphanesiyle çalışır.

| Gereksinim | Kim kullanıyor | Not |
|---|---|---|
| **Python 3.11+**, `python` adıyla yolda | hook'lar, araçlar, `summary.py`, testler | CI, Windows ve Ubuntu'da 3.11 ve 3.13 ile çalışır; daha eski 3.x sürümleri çalışabilir ama denenmedi. `settings.json` `python -I …` çağırır; Linux / macOS'ta komut `python3` ise orada değiştirin. |
| **Git**, yolda | `pascal_check.py` (yeni ihlali eskisinden ayırır), testler | Proje bir Git deposu olmalı. |
| **Claude Code**, skill, alt ajan ve SessionStart hook'u destekleyen bir sürüm | hook'lar, `.claude/skills/`, `.claude/agents/` | `/multi-review` iki alt ajanı paralel başlatır. |
| **Delphi 2007 ve sonrası** (`.dproj`, `msbuild`, `rsvars.bat`) | yalnız `build/` | Lisans komut satırı derleyicisini kapsamalı; Community Edition doğrulanmadı. |
| **psql** (PostgreSQL istemcisi) + salt okunur kullanıcı | yalnız `pg_fingerprint.py` | Başka veritabanında kullanılmaz. |
| **Windows + Git Bash** | önerilen ortam | Her şey burada yazıldı ve kullanıldı; `build.bat` yalnız Windows. Hook'lar ve araçlar Linux'ta da çalışmalı (CI'da Ubuntu var), ama gerçek bir Linux Delphi ortamında denenmedi. |

## Başlamadan önce: ikili DFM'ler

Claude, hook'lar ve araçlar yalnız **metin** DFM'leri okuyup düzenleyebilir. İkili bir DFM (çok eski projeler ya da IDE'de
"Text DFM" kapalıysa) onlar için okunamaz; 9. adımdaki `.gitattributes` kuralı da onu bozar. Önce denetleyin:

```
python tools/dfm_text_check.py --root <proje dizini>
```

Araç bütün ikili DFM'leri listeler, varsa 1 ile çıkar. Başka bir şeye geçmeden onları çevirin: IDE'de formu açın, sağ tıklayın
> **Text DFM**, kaydedin; ya da Delphi'nin komut satırı çeviricisi `bin\convert.exe -i -t <dosya.dfm>` (sürümünüzün
seçeneklerini görmek için `convert.exe`'yi argümansız çalıştırın). Araç hiçbir dosyayı değiştirmez.

Kurulumdan sonra paket izlemeye devam eder: SessionStart hook'u (`session_check.py`) her oturum başında yeni bir ikili DFM
belirdiyse Claude'a söyler, Claude da ilk cevabında size bildirir; `pas_edit.py` ikili DFM'yi düzenlemeyi reddeder;
`pascal_check.py` değişen dosyalar arasında ikili DFM görürse bildirir.

## Kurulum

Aşağıdaki yollar proje köküne göredir (`.dpr`'nin bulunduğu dizin; bir Git deposu olmalı).

1. `hooks/*.py` → projenizin `.claude/hooks/` dizinine; `tools/` → projede bir `tools/` dizinine (`pas_edit.py`,
   `pas_callers.py`, `diff_routines.py`, `dfm_text_check.py` ve `pascal_lex.py` birlikte durmalı; hook mesajları
   `tools/pas_edit.py` ve `tools/dfm_text_check.py`'yi gösterir).
2. `examples/settings.json` → `.claude/settings.json` (varsa birleştirin). Üç hook'u bağlar: `session_check.py`
   (SessionStart), `command_guard.py` (PreToolUse) ve `pascal_check.py` (PostToolUse). `python` yolda olmalı.
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
9. Satır sonları: `examples/gitattributes`'ı proje köküne `.gitattributes` olarak kopyalayın (yalnız yukarıdaki ikili DFM
   denetiminden sonra). Delphi kaynakları depoda LF tutulur, her makinenin `core.autocrlf` ayarından bağımsız olarak her zaman
   CRLF çıkar. Var olan bir depoda bir kez `git add --renormalize .` çalıştırıp ayrı bir commit yapın (çok dosyaya dokunabilir;
   önce ekibe haber verin). `pascal_check.py` yine gerekir: çalışma dosyasına yazılan tek LF bir sonraki commit'e kadar diskte
   kalır, derleyici ve IDE de diskteki dosyayı okur.
10. Claude'a salt okunur bir veritabanı kullanıcısı verin (`examples/readonly-user.postgresql.sql`; diğer veritabanları
    *Veritabanları* bölümünde) ve yazma yetkili kullanıcıları `write_db_users`'a yazın.
11. Yeni bir Claude Code oturumu açıp hook'ları deneyin: Claude'dan `sed -i "s/a/b/" <bir birim>.pas` çalıştırmasını isteyin —
    reddedilmeli.

`pas_edit.py` ve `diff_routines.py` `.claude/claude-delphi.json`'ı `$CLAUDE_PROJECT_DIR`'dan, yoksa bulunduğu dizinden
yukarı çıkarak bulur; `pas_callers.py`, DFM araçları ve `dfm_text_check.py` `--root` alır (varsayılan: bulunulan dizin), onları
proje kökünden çalıştırın.

| `claude-delphi.json` ayarı | Anlamı |
|---|---|
| `source_encoding`, `pascal_extensions`, `protected_extensions` | hook'ların ve araçların Pascal saydığı / `sed -i` ve yönlendirmeden koruduğu kod sayfası ve dosya türleri |
| `write_db_users` | yazma yetkili veritabanı kullanıcıları; bunlardan biriyle bağlanan komut reddedilir |
| `scripts_dir` | tek kullanımlık betiklerin yazıldığı (Write) ve yoluyla çalıştırıldığı dizin; gömülü Python yerine |
| `forbidden_patterns` | değişen Pascal dosyasına eklendiğinde bildirilen projeye özgü desenler, ör. `{"pattern": "BoolToStr\\s*\\([^)]*,\\s*True\\s*\\)", "message": "use BoolToStr(x)"}`; varsayılan boş |
| `signature_pattern`, `date_format` | yorum imzası denetimi (*Yerelleştirme*); desen boşsa kapalı |
| `measure_marker`, `dead_code_marker` | skill'lerin ve `CLAUDE.md`'nizin kullandığı işaretler; hook'lar okumaz |
| `forbid_inline_python`, `forbid_gh_write` | gömülü Python ve GitHub CLI yazma kurallarını kapatır (varsayılan açık) |
| `warn_binary_dfm` | SessionStart'taki ikili DFM uyarısı (varsayılan açık) |

## Testler

```
python -m unittest discover -s tests -v
```

Yalnız standart kütüphane (pytest gerekmez); `git` yolda olmalı. Testler Pascal örneklerini çalışma anında üretir ve kendi Git
ayarlarını verir; kod sayfası ve satır sonu denetimi Git'in depoyu nasıl çıkardığına bağlı kalmaz. CI, Windows ve Ubuntu'da
çalıştırır (`.github/workflows/tests.yml`).

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
| DFM'deki ASCII dışı karakterler | metin DFM'ler bunları ayarlı kod sayfasının `#nnn` kaçışlarıyla saklar; araçlar DFM'yi Latin-1 okur ve yalnız ASCII özellik adlarını karşılaştırır; `pas_edit.py` DFM'ye ASCII dışı karakter yazmayı reddeder |

İnsanın okuduğu belgeler (README, `docs/`) İngilizcedir; çeviriler `docs/<dil>/` altında durur. Çelişkide İngilizce sürüm
esastır. Çeviri katkıları memnuniyetle karşılanır.

## Veritabanları

Paket belirli bir veritabanına bağlı değildir:

| Parça | Veritabanı bağımlılığı |
|---|---|
| `pascal_check.py`, `session_check.py`, `build/`, DFM araçları, skill'ler, ajanlar | yok |
| `command_guard.py` yazma yetkili kullanıcı kuralı | yok — kullanıcı adını `psql`, `sqlcmd`, `mysql` / `mariadb`, Firebird `isql` seçeneklerinde, ortam değişkenlerinde (`PGUSER`, `MYSQL_USER`, `ISC_USER`, `SQLCMDUSER`), bağlantı dizelerinde (`User ID=`, `UID=`, `user=`) ve URL'lerde (`ad:şifre@sunucu`) yakalar |
| `tools/pg_fingerprint.py` | **PostgreSQL** (`public` şeması) — örnek; başka veritabanı için fikir taşınır: her satır için kimlik + kimliksiz içeriğin özeti |
| `examples/readonly-user.postgresql.sql` | **PostgreSQL** — diğerlerinde: SQL Server `db_datareader` rolü, MySQL / MariaDB `GRANT SELECT`, Firebird tablo başına `GRANT SELECT` / salt okunur rol |
| `docs/` içindeki teşhis ipuçları | PostgreSQL örnekleri, yanlarında SQL Server, MySQL / MariaDB ve Firebird karşılıkları |

Veritabanı hangisi olursa olsun Claude'a **salt okunur bir kullanıcı** verin, yazma yetkili kullanıcıları `write_db_users`'a yazın.

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
- İkili DFM'ler bulunur ve bildirilir; okunmaz, çevrilmez. Önce metne çevirin (yukarıya bakın).
- `pascal_check.py` bütünüyle UTF-8 kaydedilmiş dosyayı yakalar; ANSI dosyaya eklenmiş birkaç UTF-8 satırı yakalamaz.
- `pas_edit.py` uygulanmış spec'i hatırlamaz: aynı "yalnız ekleme" spec'i iki kez uygulanırsa satırlar iki kez eklenir.
- `pascal_check.py`'nin yerleşik `date_format` varsayılanı `%d.%m.%Y`, örnek ayarlar `%Y-%m-%d` kullanır; açıkça verin.

## Katkı ve lisans

Bkz. [CONTRIBUTING.md](../../CONTRIBUTING.md) (İngilizce): yeni tuzaklar, hata defteri maddeleri, çeviriler ve başka
ortamlardan raporlar memnuniyetle karşılanır. Değişiklikler: [CHANGELOG.md](../../CHANGELOG.md). Lisans: [MIT](../../LICENSE).
