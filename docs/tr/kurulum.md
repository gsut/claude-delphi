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

Kurulumdan sonra paket izlemeye devam eder: SessionStart hook'u (`session_check.py`) her yeni oturumun başında (devam ettirilen oturumda değil) yeni bir ikili DFM
belirdiyse Claude'a söyler, Claude da ilk cevabında size bildirir; `pas_edit.py` ikili DFM'yi düzenlemeyi reddeder;
`pascal_check.py` değişen dosyalar arasında ikili DFM görürse bildirir.

## Kurulum

Aşağıdaki yollar proje köküne göredir (`.dpr`'nin bulunduğu dizin; bir Git deposu olmalı).

1. `hooks/*.py`'nin **tamamı** → projenizin `.claude/hooks/` dizinine (hook'lar `hook_common.py`'yi kendi dizinlerinden içe
   aktarır); `tools/` dizininin **tamamı** → projede bir `tools/` dizinine. Araçlar birbirini içe aktarır:
   `pas_edit` → `pascal_lex`, `dfm_text_check`; `pas_callers` → `pascal_lex`, `dfm_text_check`; `diff_routines` → `pascal_lex`;
   `closeout_check` → `diff_routines`. Tek dosya kopyalamak diğerlerini `ModuleNotFoundError` ile bozar; tek tek
   güncellenen kopyalar da birbirinden kopar: güncellerken dizinin tamamını yeniden kopyalayın. Hook mesajları
   `tools/pas_edit.py` ve `tools/dfm_text_check.py`'yi gösterir.
2. `examples/settings.json` → `.claude/settings.json` (varsa birleştirin). Üç hook'u bağlar: `session_check.py`
   (SessionStart), `command_guard.py` (PreToolUse, Bash ve PowerShell) ve `pascal_check.py` (Write / Edit'te PreToolUse ile
   dosyanın anlık görüntüsü, PostToolUse ile rapor). Claude Code'un **PowerShell** aracını da kapatır: `Bash(...)` yasak
   kuralları (git, gh) ona uygulanmaz, Windows'ta onları atlatırdı. O kuralı kaldırırsanız diye hook'lar PowerShell
   komutlarını da denetler. `python` yolda olmalı.
3. `examples/claude-delphi.json` → `.claude/claude-delphi.json`; aşağıdaki tabloya ve *Yerelleştirme* bölümüne göre düzenleyin.
4. `.claude/skills/`, `.claude/agents/` ve `.claude/templates/` (plan dosyası ve inceleme kaydı şablonları) → projenizin
   `.claude/` dizinine.
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
    reddedilmeli. Sonra `scope-counter` ajanını "`echo $(git log --oneline -1)` komutunu bir kez çalıştır, çıktıyı ya da
    hatayı aynen bildir" göreviyle başlatmasını isteyin. Ajan hook'un reddini bildirmeli ("Read-only agent
    'scope-counter': command substitution ..."); aynı komutu Claude kendisi çalıştırınca geçmeli. Yalnız okuyan bir komut
    kullanın: ajanın kendi talimatı yazmayı yasakladığı için `touch` ile hook'a hiç sorulmadan reddeder ve test bir şey
    kanıtlamaz. Ajan commit satırını yazdırırsa Claude Code sürümünüz hook'lara `agent_type` göndermiyordur
    (2.1.332'de geldiği ölçüldü); o zaman yalnız skill'lerdeki `git status` / plan özeti kontrolü kalır. Windows'ta son
    olarak Claude'dan PowerShell aracıyla `Get-Date` çalıştırmasını isteyin: yasak kuralı reddetmeli (PowerShell'e izin
    verdiyseniz bunun yerine `'x' | Set-Content probe.pas` isteyin: hook reddetmeli). Bu testleri Claude Code ya da Python
    güncellendikten, `.claude/settings.json` ya da `.claude/claude-delphi.json` düzenlendikten sonra tekrarlayın.

`pas_edit.py`, `diff_routines.py` ve `closeout_check.py` `.claude/claude-delphi.json`'ı `$CLAUDE_PROJECT_DIR`'dan, yoksa bulunduğu dizinden
yukarı çıkarak bulur; `pas_callers.py`, DFM araçları ve `dfm_text_check.py` `--root` alır (varsayılan: bulunulan dizin), onları
proje kökünden çalıştırın.

| `claude-delphi.json` ayarı | Anlamı |
|---|---|
| `source_encoding`, `pascal_extensions`, `protected_extensions` | hook'ların ve araçların Pascal saydığı / `sed -i` ve yönlendirmeden koruduğu kod sayfası ve dosya türleri |
| `write_db_users` | yazma yetkili veritabanı kullanıcıları; bunlardan biriyle bağlanan komut reddedilir |
| `scripts_dir` | tek kullanımlık betiklerin yazıldığı (Write) ve yoluyla çalıştırıldığı dizin; gömülü Python yerine |
| `forbidden_patterns` | değişen Pascal dosyasına eklendiğinde bildirilen projeye özgü desenler, ör. `{"pattern": "BoolToStr\\s*\\([^)]*,\\s*True\\s*\\)", "message": "use BoolToStr(x)"}`; varsayılan boş |
| `signature_pattern`, `date_format` | yorum imzası denetimi (*Yerelleştirme*); desen boşsa kapalı |
| `measure_marker` | geçici ölçüm satırlarının işareti; `/triage` ve `closeout_check.py` okur (kalan satırları bildirir); hook'lar okumaz |
| `dead_code_marker` | `CLAUDE.md`'nizde anılan ölü kod işareti; yalnız Claude ve ekip için bir kural — hiçbir skill, hook ya da araç okumaz |
| `forbid_inline_python`, `forbid_gh_write` | gömülü Python ve GitHub CLI yazma kurallarını kapatır (varsayılan açık) |
| `warn_binary_dfm` | SessionStart'taki ikili DFM uyarısı (varsayılan açık) |
| `build_log` | `build.bat`'ın yazdığı günlük, proje köküne göre (varsayılan `build/log/last.log`); `closeout_check.py` son değişiklikten yeni olduğunu denetler |
| `readonly_agents` | Bash komutlarına `command_guard.py` 6. kuralı uygulanan alt ajanlar (komut ikamesi, yönlendirme, yazan program ve seçenek yok; bir tetik teli, güvenlik sınırı değil); varsayılan üç inceleme ajanı. `.claude/agents/` içindeki adlarla aynı tutun (bir test denetler) |

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
| Koddaki işaretler | `measure_marker` (varsayılan `X-MEASURE`; `/triage` ve `closeout_check.py` okur), `dead_code_marker` (varsayılan `DEAD-CODE`; yalnız `CLAUDE.md`'nizde anılır); Türkçe ekip `X-OLCUM` / `OLU-KOD` seçebilir. Kodda gerçekten kullanılanı yazın: koddan farklı bir işaret `closeout_check.py`'nin kalan satırları kaçırmasına yol açar |
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

**Güvenlik parçalarının kapsamadıkları** (bağımsız bir incelemeden; bulunup düzeltilebilen düzeltildi):
- `command_guard.py` komut metnine uygulanan desenlerdir — yalnız inceleme ajanları için değil, ana oturum için de
  alışkanlığa karşı bir tetik teli. Yakalamadıkları: kendi başına yazan programlar (`cp`, `mv`, `dos2unix`, `iconv -o`,
  `git checkout -- dosya`, bir betik dosyası), iç içe kabuk (`cmd /c "..."`, `powershell -Command`), başka
  yorumlayıcıların satır içi kodu, değişkende tutulan hedefler.
- Veritabanı kuralı kullanıcı adını ancak komutta yazılıysa görür. Örtük kimlikle bağlantılar (Windows kimlik doğrulaması
  `sqlcmd -E`, işletim sistemi kullanıcı adı, önceden ayarlanmış `PGUSER`, `.pgpass`, servis dosyası, betik içindeki
  bağlantı dizesi) geçer; SQL metni hiç incelenmez. Sınır, salt okunur veritabanı kullanıcısı ve yazma kimliği taşımayan
  bir ortamdır.
- `python` yolda değilse ya da hook zaman aşımına uğrarsa Claude Code komutu denetimsiz çalıştırabilir (burada
  doğrulanmadı). Python ya da Claude Code güncellendikten sonra 11. adımdaki duman testlerini tekrarlayın.
- `pascal_check.py` yazmadan sonra bildirir (PostToolUse); yazmayı önlemez. Bash komutundan sonra `git status`'un
  listelediği ve son 10 dakikada değişmiş Pascal dosyalarını görür: yok sayılan dosyalar, depo dışındaki dosyalar ve
  zaman damgası korunmuş dosyalar denetlenmez. LF saklayan ve hiçbir dönüşüm yapmayan bir depoda commit'teki hâl CRLF
  sayılır; çalışma kopyası LF olan bir dosya Bash'ten sonra bütünüyle bildirilir (Write / Edit dosyanın hemen önceki
  hâliyle karşılaştırır).
- "Git salt okunur", `settings.json`'da Bash aracı için yasaklanan komut önekleri listesidir, bir mekanizma değil:
  listede olmayan alt komutlar reddedilmez.
- İnceleme ajanları Write / Edit kullanamaz (`tools` satırı, bir test denetler). Bash komutlarını 6. kural ancak Claude Code
  hook'lara `agent_type` gönderdikçe sınırlar (2.1.332'de görüldü; belgelenmiş bir güvence değil — duman testi gösterir)
  ve 6. kural bir veritabanı istemcisini durdurmaz: salt okunur kullanıcı durdurur.
- Skill'ler talimattır. Tur sınırları, "denetim sürerken dosya değişmez", ajanlara söylenenler ve inceleme kaydındaki
  sayılar modelin onlara uymasına bağlıdır. `closeout_check.py` inceleme kaydının biçimini ve bugün tarihli bir kapanış
  satırını (gece yarısından sonra kapanan iş yeni satır ister), derleme günlüğünün kaynaklardan yeni olduğunu denetler —
  denetimin yapıldığını ya da derlemenin başarılı olduğunu değil.

**Araçların görmedikleri:**
- `pascal_lex.py` bir çözümleyici değildir: include dosyaları açılmaz, yordam sınırlarını yalnız ilk `{$IF}` dalı verir,
  yordam içindeki yerel tipler derinlik sayımıyla atlanır, çok satırlı `'''` dizgileri ve gövdesi include dosyasındaki
  yordam ParseError verir.
- `pas_callers.py` adla, tip bilgisi olmadan, `--root` ve `.dpr` birimlerinde arar; başka projeler, paketler ve kök
  dışındaki arama yolu aranmaz. Ayırt edemediğini bildiği durumda "dead" yerine "NO VERDICT" verir (aracın yardımına
  bakın); "dead" hükmü yine de denetlenecek bir kanıttır, ispat değil.
- `diff_routines.py --plan` yordamlara ve DFM nesnelerine plan durumu verir. Birim düzeyindeki değişiklikler (uses,
  sabitler, tipler, sınıf bildirimleri) ve Pascal dışı dosyalar (`.sql`, `.dproj`, `.rc`) durum almaz; onları yalnız
  Kapsam listesi ("adı geçen ama değişmeyen") ve kapanış ajanı kapsar.
- `dfm_field_check.py` yalnız DataSource'unu kalıcı alanlı bir veri kümesine çözebildiği bağları denetler ve kaçını
  atladığını söyler: 700 birimlik gerçek bir projede 2.419 denetlenene karşı 1.716 bağlı kontrol atlandı.
- Depo kökü başına tek proje varsayılır (tek `.dpr`, tek `.dproj`, kaynaklar kök altında). `build.bat` tek `.dproj`
  derler; proje grupları ve paket çıktı dizinleri (`.bpl` / `.dcp`) yönlendirilmez (bir pakette doğrulanmadı).
- Kaynak kod sayfası: bütün proje için tek bir tek baytlık kod sayfası ya da UTF-8. Karışık projeler, UTF-16 kaynaklar ve
  çok baytlı ANSI sayfaları (ör. cp932; ikinci bayt `{` ya da `}` olabilir) lexer ve araçlarca desteklenmez.
- SessionStart denetimi yalnız yeni oturumda çalışır (devam ettirilende değil) ve yalnız `.dfm`'ye bakar; ikili `.fmx` /
  `.lfm`'ye bakmaz.

## Katkı ve lisans

Bkz. [CONTRIBUTING.md](../../CONTRIBUTING.md) (İngilizce): yeni tuzaklar, hata defteri maddeleri, çeviriler ve başka
ortamlardan raporlar memnuniyetle karşılanır. Değişiklikler: [CHANGELOG.md](../../CHANGELOG.md). Lisans: [MIT](../../LICENSE).
