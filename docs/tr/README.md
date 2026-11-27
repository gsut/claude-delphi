# claude-delphi

**Eski (Legacy) Delphi VCL ve veritabanı kod tabanlarında [Claude Code](https://claude.com/claude-code) ile güvenli, hatasız ve kontrollü çalışmak için geliştirilmiş hook'lar, skill'ler, alt ajanlar ve sıfır bağımlılıklı Python araçları seti.**

[![tests](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml/badge.svg)](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Delphi 2007+](https://img.shields.io/badge/Delphi-2007%20--%2013-red.svg)](kurulum.md#gereksinimler)

🌐 **Diller:** [English](../../README.md) | Türkçe

> *Bu belge ana [`README.md`](../../README.md) dosyasının Türkçe çevirisidir; olası farklılıklarda İngilizce sürüm esas alınır.*

---

## 💡 Neden Bu Repo Var? (Token Tasarrufu Değil, Doğruluk)

Modern bir TypeScript veya Python projesinde yapay zekâ kullanmak kolaydır. Ancak yüzlerce birimden (unit), ANSI (`cp1254` / `cp1252`) karakter kodlamalarından, `CRLF` satır sonlarından, `.dfm` form bağlantılarından ve binlerce eski derleme uyarısından oluşan **15 yıllık bir Delphi VCL monolitinde** AI kullanmak mayın tarlasında yürümeye benzer.

> **Temel felsefemiz: Amaç token tasarrufu değil, çalışmanın doğruluğudur.**  
> Eski bir kod tabanında en pahalı şey uzun süren bir yapay zekâ oturumu değil; temiz derlenen, mantıklı görünen ama canlı sistemdeki müşteri verisini sessizce bozan yanlış bir düzeltmedir.

Bu depodaki her bir kural, hook ve alt ajan; gerçek bir projede aylarca süren günlük kullanım sonucunda Claude Code'u **düzeltmeden önce ölçüm yapmaya, eski dosya kodlamalarına saygı duymaya ve `git commit` öncesinde kendi işini bağımsız olarak denetlemeye** zorlamak için geliştirildi.

*(Bu çalışma yönteminin gerçek bir hata avında nasıl işlediğini okumak için: [Boş İkiz Satırlar: Eski Bir Delphi Projesinde Claude Code ile Çalışmak](https://medium.com/@gokhan.sut_29411/bo%C5%9F-i%CC%87kiz-sat%C4%B1rlar-eski-bir-delphi-projesinde-claude-code-ile-%C3%A7al%C4%B1%C5%9Fmak-09940981f2dc) veya [Vaka İncelemesi](vaka.md).)*

---

## 🛡️ Hangi Sorunları Çözer?

| Eski Delphi Tuzakları | `claude-delphi` Nasıl Önler? |
| :--- | :--- |
| **Kodlama ve Satır Sonu Bozulması:** AI, `cp1254` / `cp1252` dosyalarını UTF-8 kaydeder veya `CRLF` yapısını `LF`'ye çevirir. | **`hooks/pascal_check.py`** — Her yazmadan hemen sonra, dosyanın yazmadan önceki hâline göre *yeni* kodlama ve satır sonu ihlallerini Claude'a bildirir. |
| **Yıkıcı Komut Satırı Düzenlemeleri:** AI; `sed -i`, `>` yönlendirmesi veya satır içi (inline) betiklerle dosyaları bozar. | **`hooks/command_guard.py` & `tools/pas_edit.py`** — Bilinen tehlikeli kabuk düzenlemelerini çalışmadan önce reddeder (desen tabanlı bir tetik teli, bkz. *Sınırlar*); yerine kodlamayı koruyan güvenli bir Pascal/DFM düzenleyici sunar. |
| **Yanlışlıkla Veritabanına Yazma:** AI, yazma yetkisi olan bir kullanıcıyla veritabanına bağlanır. | **`hooks/command_guard.py`** — Yazma yetkili bir kullanıcıyı adıyla anan komutları reddeder (`psql`, `sqlcmd`, `mysql`, `isql` seçenekleri, ortam değişkenleri, bağlantı dizeleri). Asıl sınır salt okunur veritabanı kullanıcısıdır. |
| **Derleme Uyarılarını Gözden Kaçırma:** AI kodu derlemeden teslim eder veya 4.000 eski uyarı arasında yeni eklediği 2 uyarıyı fark etmez. | **`build/build.bat` + `summary.py`** — IDE dilinden bağımsız olarak **hataları ve tabana göre yeni uyarıları** raporlar (başarısız derleme her zaman hata görünür); `/build-check` "0 ve 0"ı kabul ölçütü yapar. |
| **Kırılan DFM Bağlantıları:** AI bir alanı veya metodu "kullanılmıyor" sanıp siler ve çalışma zamanında VCL ekranını patlatır. | **`tools/dfm_field_check.py` & `dfm_field_usage.py`** — `.dfm` dosyalarındaki `DataSource` ve bileşen alan bağlarını analiz eder. |
| **Hatalı "Ölü Kod" (Dead Code) Tespiti:** Basit bir `grep` araması iç yordamları, DFM olaylarını veya `{$IF}` bloklarını kaçırır. | **`tools/pas_callers.py`** — Pascal sözdizimine duyarlı tarama yaparak bir yordamın tüm çağrılarını kanıtlarıyla gruplar; aleyhine bir işaret varsa (override / message metotları, proje dışı birimler) "ölü" hükmü vermez. |
| **Veritabanı Yan Etkilerini Tahmin Etme:** AI, bir tetikleyicinin (trigger) veya yordamın hangi tabloları etkilediğini koddan tahmin etmeye çalışır. | **`tools/pg_fingerprint.py`** — İşlem öncesi ve sonrası tüm tablolardaki satır özetlerini (hash) karşılaştırarak veritabanı etkisini kanıtlar. |
| **Yapay Zekâ Onay Yanlılığı:** Alt ajan, ana ajanın planını sorgulamadan onaylar. | **`/review` & `/multi-review` skill'leri** — Kod yazılmadan önce, bağlamsız alt ajanlara yalnızca neyin değişeceği verilir, planın sonucu verilmez; kapsamı sayar, kırılma senaryosu ararlar. |
| **Yarım Kalan veya Kapsam Dışı İşler:** AI planın bir kısmını atlar veya ilgisiz yordamlara dokunur. | **`/close-out` + `tools/diff_routines.py`** — `git diff` çıktısını Pascal yordamlarına/DFM nesnelerine eşler; planda olmayanı ve planda olup değişmeyeni listeler; gerisini bağımsız bir ajan denetler. |
| **İkili (binary) DFM'ler:** İkili kaydedilmiş eski formları AI okuyamaz; satır sonu kuralları da onları bozar. | **`hooks/session_check.py`** + **`tools/dfm_text_check.py`** — Her yeni oturumun başında uyarır ve listeler; metne çevrilene kadar `pas_edit.py` dokunmayı reddeder. |
| **Aynı Hataları Tekrarlama:** `CLAUDE.md` dosyası zamanla okunması imkânsız dev bir metne dönüşür. | **`docs/tr/hata-defteri.md`** — Her hatanın kısa bir **Kural + yapıldığı görülebilen bir Kontrol** maddesine dönüştüğü yapılandırılmış hata defteri; desenle yakalanabilen hata deftere değil hook'a gider. |

---

## 🧠 60 Saniyede Çalışma Akışı

1. **Teşhis (`/triage`):** Claude bir hipotez kurar, kanıt toplar ve hipotezleri ayırt edecek bir ölçüm önerir. **Henüz kod
   yazılmaz**; geçici ölçüm satırları (`// X-MEASURE`) ancak onayınızdan sonra eklenir.
2. **Plan ve Onay:** Ölçüm sonuçları netleştiğinde Claude, somut uygulama planını bir şablondan `personal/plans/<id>-plan.md`
   dosyasına yazar (araçlar plan maddelerini ve kapsamı okur; diğer bölümleri — değişmeyen çağıranlar, kaldırılan
   çağrılar — ajanlar kullanır).
3. **Kör İnceleme (`/review` ya da `/multi-review`):** Kod yazılmadan önce bağlamsız alt ajanlar (`scope-counter`,
   `devils-advocate`) yalnızca neyin değişeceğini alır, planın sonucunu almaz; bulgular doğrulanıp kayda geçer.
4. **Cerrahi Uygulama:** Claude, `pas_edit.py` aracılığıyla güvenli düzenleme yapar (aynı düzeltmeyi kopya yordamlara yapıştırmak yerine ortak bir yordamda birleştirir) ve derleme tabanına göre derler.
5. **Kapanış Denetimi (`/close-out`):** Mekanik kontroller (`closeout_check.py`), plana karşı değişiklik haritası ve diff ile
   onaylı plan arasındaki her farkı listeleyen `closeout-auditor` ajanı. Son kontrol ve `commit` geliştiriciye aittir.

---

## 🚀 Başlarken

Gereksinimler, adım adım kurulum, `claude-delphi.json`'daki her ayar, yerelleştirme, veritabanı notları ve bilinen sınırlar:
**[kurulum.md](kurulum.md)**. İlk adımla başlayın: ikili DFM denetimi.

---

## 📦 Depo Yapısı

```text
├── hooks/
│   ├── session_check.py      # SessionStart: Projede ikili DFM varsa (Claude aracılığıyla) uyarır
│   ├── command_guard.py      # PreToolUse: sed -i, satır içi Python, yazma yetkili DB kullanıcıları, gh yazma komutları ve inceleme ajanlarının yazmasını engeller
│   └── pascal_check.py       # PostToolUse: Kodlama (CP125x), CRLF, yasaklı desenler, yorum imzaları ve ikili DFM'leri denetler
├── build/
│   ├── build.bat             # Delphi (.dproj) için MSBuild sarmalayıcısı
│   └── summary.py            # Derleme hata ve uyarılarını kaydedilmiş taban (baseline) ile karşılaştırır
├── tools/                    # Sıfır dış bağımlılıklı Python CLI araçları
│   ├── pas_edit.py           # Tek çapa (anchor) doğrulamalı ve --reverse destekli güvenli Pascal/DFM düzenleyici
│   ├── pas_callers.py        # Bir yordamın tüm referanslarını bulur (kod, {$IF}, DFM olayları, dizgeler, yorumlar)
│   ├── pascal_lex.py         # Hafif Pascal sözcüksel çözümleyici ve yordam sınır bulucu
│   ├── dfm_field_check.py    # DFM bileşen alanlarının veri kümesinde (dataset) var olup olmadığını doğrular
│   ├── dfm_field_usage.py    # Belirli veritabanı alanlarına bağlı DFM bileşenlerini listeler
│   ├── pg_fingerprint.py     # İşlem öncesi/sonrası veritabanı kayıt parmak izi çıkarıcı (PostgreSQL)
│   ├── diff_routines.py      # git diff bloklarını Pascal yordamlarına ve DFM bileşen zincirlerine eşler
│   ├── closeout_check.py     # Mekanik kapanış denetimleri: ölçüm satırı, .bak, CreateForm, form kaydı, derleme tarihi
│   └── dfm_text_check.py     # Metne çevrilmesi gereken ikili DFM'leri listeler
├── .claude/
│   ├── skills/               # Özel iş akışları: /build-check, /triage, /review, /multi-review, /close-out
│   ├── agents/               # Uzman alt ajanlar: scope-counter, devils-advocate, closeout-auditor
│   └── templates/            # plan.md (araçların okuduğu bölüm işaretleri), reviews.md (inceleme kaydı, tur başına satır)
├── docs/
│   ├── installation.md       # Gereksinimler, kurulum, ayarlar, yerelleştirme, veritabanları, sınırlar (Türkçesi: tr/kurulum.md)
│   ├── mistake-log.md        # Yöntem, şablon ve 20 başlangıç kuralı (Türkçesi: tr/hata-defteri.md)
│   ├── delphi-pitfalls.md    # Tekrarlayan 26 Delphi VCL + SQL tuzağı (Türkçesi: tr/delphi-tuzaklari.md)
│   ├── build-baseline.md     # Derleme tabanı yönetiminin ayrıntıları (Türkçesi: tr/derleme-tabani.md)
│   ├── case-study.md         # Gerçek bir hata avının adım adım hikâyesi (Türkçesi: tr/vaka.md)
│   └── tr/                   # Türkçe dokümantasyon
├── examples/                 # Hazır CLAUDE.md, settings.json, claude-delphi.json, gitattributes (.gitattributes olarak kopyalanır) ve salt okunur SQL şablonları
└── tests/                    # hook'lar, araçlar ve derleme özeti için unittest paketi (Windows ve Ubuntu)
```

Katkılar memnuniyetle karşılanır — bkz. [CONTRIBUTING.md](../../CONTRIBUTING.md) (İngilizce). Değişiklikler:
[CHANGELOG.md](../../CHANGELOG.md). Lisans: [MIT](../../LICENSE).