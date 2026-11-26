# claude-delphi

**Eski (Legacy) Delphi VCL ve veritabanı kod tabanlarında [Claude Code](https://claude.com/claude-code) ile güvenli, hatasız ve kontrollü çalışmak için geliştirilmiş hook'lar, skill'ler, alt ajanlar ve sıfır bağımlılıklı Python araçları seti.**

[![tests](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml/badge.svg)](https://github.com/gsut/claude-delphi/actions/workflows/tests.yml)
[![license: MIT](https://img.shields.io/badge/license-MIT-blue.svg)](../../LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/)
[![Delphi 2007+](https://img.shields.io/badge/Delphi-2007%20--%2013-red.svg)](#gereksinimler)

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
| **Kodlama ve Satır Sonu Bozulması:** AI, `cp1254` / `cp1252` dosyalarını UTF-8 kaydeder veya `CRLF` yapısını `LF`'ye çevirir. | **`hooks/pascal_check.py`** — Git geçmişine kıyasla yalnızca *yeni* oluşan kodlama ve satır sonu ihlallerini yakalar. |
| **Yıkıcı Komut Satırı Düzenlemeleri:** AI; `sed -i`, `>` yönlendirmesi veya satır içi (inline) betiklerle dosyaları bozar. | **`hooks/command_guard.py` & `tools/pas_edit.py`** — Tehlikeli kabuk komutlarını engeller; yerine kodlamayı koruyan güvenli bir Pascal/DFM düzenleyici sunar. |
| **Yanlışlıkla Veritabanına Yazma:** AI, yazma yetkisi olan bir kullanıcıyla veritabanına bağlanır. | **`hooks/command_guard.py`** — CLI veritabanı araçlarını (`psql`, `sqlcmd`, `mysql`, `isql`) ve bağlantı dizelerini denetleyerek yazma yetkili kullanıcıları bloklar. |
| **Derleme Uyarılarını Gözden Kaçırma:** AI kodu derlemeden teslim eder veya 4.000 eski uyarı arasında yeni eklediği 2 uyarıyı fark etmez. | **`build/build.bat` + `summary.py`** — IDE dilinden bağımsız olarak **0 hata ve tabana (baseline) göre 0 yeni uyarı** kuralını zorunlu kılar. |
| **Kırılan DFM Bağlantıları:** AI bir alanı veya metodu "kullanılmıyor" sanıp siler ve çalışma zamanında VCL ekranını patlatır. | **`tools/dfm_field_check.py` & `dfm_field_usage.py`** — `.dfm` dosyalarındaki `DataSource` ve bileşen alan bağlarını analiz eder. |
| **Hatalı "Ölü Kod" (Dead Code) Tespiti:** Basit bir `grep` araması iç yordamları, DFM olaylarını veya `{$IF}` bloklarını kaçırır. | **`tools/pas_callers.py`** — Pascal sözdizimine duyarlı tarama yaparak bir yordamın tüm çağrılarını kanıtlarıyla gruplar. |
| **Veritabanı Yan Etkilerini Tahmin Etme:** AI, bir tetikleyicinin (trigger) veya yordamın hangi tabloları etkilediğini koddan tahmin etmeye çalışır. | **`tools/pg_fingerprint.py`** — İşlem öncesi ve sonrası tüm tablolardaki satır özetlerini (hash) karşılaştırarak veritabanı etkisini kanıtlar. |
| **Yapay Zekâ Onay Yanlılığı:** Alt ajan, ana ajanın planını sorgulamadan onaylar. | **`/review` & `/multi-review` skill'leri** — Alt ajanlara planın sonucunu göstermeden yalnızca kod değişikliğini (diff) kör olarak inceletir. |
| **Yarım Kalan veya Kapsam Dışı İşler:** AI planın bir kısmını atlar veya ilgisiz yordamlara dokunur. | **`/close-out` + `tools/diff_routines.py`** — `git diff` çıktısını Pascal yordamlarına/DFM nesnelerine eşler ve onaylı planla birebir karşılaştırır. |
| **İkili (binary) DFM'ler:** İkili kaydedilmiş eski formları AI okuyamaz; satır sonu kuralları da onları bozar. | **`hooks/session_check.py`** + **`tools/dfm_text_check.py`** — Her oturum başında uyarır ve listeler; metne çevrilene kadar `pas_edit.py` dokunmayı reddeder. |
| **Aynı Hataları Tekrarlama:** `CLAUDE.md` dosyası zamanla okunması imkânsız dev bir metne dönüşür. | **`docs/tr/hata-defteri.md`** — Her hatanın kısa bir **Kural + Otomatik Kontrol** maddesine dönüştüğü yapılandırılmış hata defteri. |

---

## 🧠 60 Saniyede Çalışma Akışı

1. **Teşhis (`/triage`):** Claude bir hipotez kurar, kanıt toplar ve koda geçici ölçüm işaretleri (`// X-MEASURE`) ekler. **Henüz hata düzeltmesi yapılmaz.**
2. **Plan ve Onay:** Ölçüm sonuçları netleştiğinde Claude, somut uygulama planını `personal/plans/<id>-plan.md` dosyasına yazar.
3. **Cerrahi Uygulama:** Claude, `pas_edit.py` aracılığıyla güvenli düzenleme yapar (aynı düzeltmeyi kopya yordamlara yapıştırmak yerine ortak bir yordamda birleştirir) ve derleme tabanına göre test eder.
4. **Kör İnceleme (`/multi-review`):** Paralel çalışan alt ajanlar (`scope-counter`, `devils-advocate`), planın sonucunu bilmeden yalnızca yapılan değişiklikleri denetler.
5. **Kapanış Denetimi (`/close-out`):** `closeout-auditor` ajanı, `git diff` ile onaylanan planın birebir örtüştüğünü doğrular. Son kontrol ve `commit` işlemi geliştiriciye aittir.

---

## 🚀 Başlarken

Gereksinimler, adım adım kurulum, `claude-delphi.json`'daki her ayar, yerelleştirme, veritabanı notları ve bilinen sınırlar:
**[kurulum.md](kurulum.md)**. İlk adımla başlayın: ikili DFM denetimi.

---

## 📦 Depo Yapısı

```text
├── hooks/
│   ├── session_check.py      # SessionStart: Projede ikili DFM varsa (Claude aracılığıyla) uyarır
│   ├── command_guard.py      # PreToolUse: sed -i, satır içi Python, yazma yetkili DB kullanıcıları ve gh yazma komutlarını engeller
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
│   └── dfm_text_check.py     # Metne çevrilmesi gereken ikili DFM'leri listeler
├── .claude/
│   ├── skills/               # Özel iş akışları: /build-check, /triage, /review, /multi-review, /close-out
│   └── agents/               # Uzman alt ajanlar: scope-counter, devils-advocate, closeout-auditor
├── docs/
│   ├── installation.md       # Gereksinimler, kurulum, ayarlar, yerelleştirme, veritabanları, sınırlar (Türkçesi: tr/kurulum.md)
│   ├── mistake-log.md        # Yöntem, şablon ve 20 başlangıç kuralı (Türkçesi: tr/hata-defteri.md)
│   ├── delphi-pitfalls.md    # Tekrarlayan 26 Delphi VCL + SQL tuzağı (Türkçesi: tr/delphi-tuzaklari.md)
│   ├── build-baseline.md     # Derleme tabanı yönetiminin ayrıntıları (Türkçesi: tr/derleme-tabani.md)
│   ├── case-study.md         # Gerçek bir hata avının adım adım hikâyesi (Türkçesi: tr/vaka.md)
│   └── tr/                   # Türkçe dokümantasyon
├── examples/                 # Hazır CLAUDE.md, settings.json, claude-delphi.json, gitattributes (.gitattributes olarak kopyalanır) ve salt okunur SQL şablonları
└── tests/                    # Windows ve Ubuntu üzerinde çalışan kapsamlı unittest paketi
```

Katkılar memnuniyetle karşılanır — bkz. [CONTRIBUTING.md](../../CONTRIBUTING.md) (İngilizce). Değişiklikler:
[CHANGELOG.md](../../CHANGELOG.md). Lisans: [MIT](../../LICENSE).