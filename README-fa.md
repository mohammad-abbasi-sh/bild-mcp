# bild-mcp 📰

mcp-name: io.github.mohammad-abbasi-sh/bild-mcp

سرور MCP غیررسمی و **فقط-خواندنی** برای **[BILD](https://www.bild.de)** — بزرگ‌ترین روزنامهٔ زرد و برند خبری دیجیتال آلمان (۸۰٫۲۲ میلیون بازدید در اکتبر ۲۰۲۶، رتبهٔ ۲۱ آلمان بر اساس SEMrush) — از طریق فیدهای رسمی RSS (فید اصلی و یک فید برای هر بخش) و صفحه‌های مقاله، که متن کامل آن‌ها از پاراگراف‌های `<article>` رندرشده در سمت سرور خوانده می‌شود (صفحه‌های BILD هیچ `articleBody` در JSON-LD ندارند). تیترهای برتر، اخبار هر بخش (politik, sport, unterhaltung, digital, auto, reise, geld)، جست‌وجوی کلیدواژه، داستان‌های ویدیویی، داستان‌های BILDplus و متن کامل مقالات. بدون کلید، بدون لاگین.

> ساختهٔ محمد عباسی در چارچوب «کارخانهٔ MCP آلمان» (خط لولهٔ سبک سپهر). وابسته به BILD یا اکسل اشپرینگر نیست.

## برای ایجنت‌های هوش مصنوعی

به پیکربندی کلاینت MCP اضافه کنید (stdio):

```json
{
  "mcpServers": {
    "bild": {
      "command": "uvx",
      "args": ["bild-mcp==0.1.0"]
    }
  }
}
```

یا به‌صورت محلی اجرا کنید: `python -m bild_mcp.server` (نیازمند `mcp<2` و `httpx`).

## ابزارها

| ابزار | توضیح |
|------|-------|
| `bild_headlines` | تیترهای برتر BILD (فید رسمی RSS صفحهٔ اصلی، حدود ۹۹ مورد)، جدیدترین اول — `limit` از ۱ تا ۱۵۰. هر مورد شامل تیتر، لینک مقاله برای `bild_get_article`، تیزر، پرچم BILDplus (`premium`)، فهرست دسته‌ها، آدرس تصویر، پرچم `has_video` و زمان انتشار است |
| `bild_section_news` | تازه‌ترین اخبار BILD در یک بخش، از فید رسمی RSS همان بخش — `section`: "politik" ،"sport" ،"unterhaltung" ،"digital" ،"auto" ،"reise" یا "geld"، `limit` از ۱ تا ۱۵۰ |
| `bild_search_news` | جست‌وجوی اخبار BILD با کلیدواژه (تیتر + تیزر) در فید اصلی و هر هفت فید بخش (حدود ۸۰۰ مورد) — `query` (مثلاً "Bayern")، `limit` از ۱ تا ۱۵۰ |
| `bild_videos` | تازه‌ترین داستان‌های BILD با ویدیوی داخلی (موردهایی که در فیدشان جریان ویدیوی HLS دارند)، در همهٔ فیدها — `limit` از ۱ تا ۱۵۰ |
| `bild_premium_news` | تازه‌ترین داستان‌های BILDplus (پشت پی‌وال BILDplus — پرچم `<bild:premium>` در فید)، در همهٔ فیدها — `limit` از ۱ تا ۱۵۰ |
| `bild_get_article` | متن کامل یک صفحهٔ مقالهٔ BILD (پاراگراف‌های `<article>` رندرشده در سمت سرور) — `url`: آدرس مقالهٔ www.bild.de (/<بخش>/<slug>-<شناسهٔ ۳۲رقمی هگز>). مقاله‌های BILDplus مقدار `paywalled: true` برمی‌گردانند و فقط تیزر دوپاراگرافی را به‌عنوان متن می‌دهند — متن کامل نیازمند اشتراک BILDplus است. آدرس‌های فید، صفحهٔ اصلی و لینک‌های خارجی رد می‌شوند |
| `bild_health` | بررسی دسترس‌پذیری فید اصلی (ok / blocked / error) — یک درخواست مؤدبانه |

نمونهٔ خروجی (`bild_headlines` با `limit` برابر ۲):

```json
{"feed_title": "BILD - Home", "total_results": 99, "count": 2,
 "items": [
  {"title": "Minister stellen neue Zahlen vor - Jede Woche werden vier Frauen durch häusliche Gewalt getötet",
   "link": "https://www.bild.de/leben-wissen/neue-bka-zahlen-vorgestellt-drastischer-anstieg-bei-gewalt-gegen-frauen-6b032922816dfbaedcce8a5c",
   "description": "Alle Delikte zeigen, besonders in drei Feldern. BILD erklärt die dramatischen Zahlen.",
   "published": "2026-11-24T10:17:46+00:00", "premium": false,
   "categories": ["Leben & Wissen", "Kriminalstatistik", "Initiative BILD gegen Gewalt an Frauen", "Gewalt", "Polizei", "Häusliche Gewalt", "Team First", "sexueller Missbrauch"],
   "image_url": "https://images.bild.de/6b032922816dfbaedcce8a5c/87ee9a4fc504d7c00d4c2bb29a696909,2dd42395?w=1280",
   "has_video": false},
  ...]}
```

نکته‌ها:
- سرور **فیدهای رسمی RSS** را می‌خواند (فید اصلی ۹۹ مورد؛ فید هر بخش ۱۰۰ مورد: politik/sport/unterhaltung/digital/auto/reise/geld — بررسی زنده در ۲۰۲۶-۱۱-۲۴). جست‌وجو، ویدیوها و پرمیوم به‌صورت سمت-کلاینت روی فیدهای گرفته‌شده اجرا می‌شوند (حدود ۸۰۰ مورد).
- لینک‌های مقالهٔ BILD **پسوند `.html` ندارند** (به شناسهٔ ۳۲رقمی هگز ختم می‌شوند) — پس هیچ فیلتر پسوندی اعمال نمی‌شود و هر مورد فید همان‌طور که هست برگردانده می‌شود. چند مورد فید صفحه‌های تبلیغاتی/خدماتی‌اند (مثلاً `/bild-plus/` یا `/gewinner-verlierer-.../`) — صفحه‌های واقعی bild.de که در فید آمده‌اند و همان‌طور برگردانده می‌شوند.
- فیدها یک **پرچم `<bild:premium>`** دارند (فید اصلی: ۱۲ مورد از ۹۹ پرمیوم)، چند مقدار **`<category>`** برای هر مورد، یک تصویر `media:content` (روی images.bild.de، در هر ۹۹ مورد فید اصلی موجود است) و در داستان‌های ویدیویی یک جریان HLS (`application/x-mpegURL`، ۱۶ مورد از ۹۹ مورد فید اصلی) — که به‌صورت `has_video` نشان داده می‌شود. جریان‌های HLS داخل `<media:group>` قرار دارند، پس تجزیه‌کننده همهٔ فرزندان را می‌گردد. فیلد نویسنده وجود ندارد.
- مقدارهای `pubDate` در فیدها با **CET/CEST** نوشته می‌شوند (مثلاً `11:17:46 CET`) — کتابخانهٔ `email.utils` این منطقه‌های زمانی را نمی‌شناسد، پس پیش از تجزیه به آفست عددی تبدیل می‌شوند (11:17:46 CET ← 10:17:46 UTC).
- **متن مقاله، صادقانه:** صفحه‌های BILD هیچ `articleBody` در JSON-LD ندارند — متن از پاراگراف‌های `<article>` رندرشده در سمت سرور می‌آید (۷۳۲ کلمه در نمونهٔ یک مقالهٔ رایگان). بلوک ناوبری و تیزر تکراری "+++ ..." بیرون از `<article>` قرار دارند، پس هرگز به متن نمی‌رسند؛ پاراگراف‌های یکسان به‌هرحال یکتاسازی می‌شوند. حذف می‌شوند: خط منبع "LIVE ... Quelle:"، قطعه‌های بایلاین (نام نویسنده‌ها که به‌صورت پاراگراف‌های تک‌توکنی رندر شده‌اند)، خط بازخورد "Haben Sie eine Meinung zu diesem Artikel?" و خط پاصفحه "Mobile Ansicht ...".
- **پی‌وال، صادقانه:** مقاله‌های BILDplus فقط یک تیزر دوپاراگرافی را در `<article>` نشان می‌دهند (۵۵ کلمه در نمونه). سیگنال پی‌وال، `isAccessibleForFree` در بلوک JSON-LD NewsArticle است (در صفحه‌های BILDplus برابر false و در صفحه‌های رایگان برابر true)، و `"contentAccessBlocked":true` جاسازی‌شده در صفحه، جایگزین آن است. صفحهٔ پولی `paywalled: true` برمی‌گرداند و فقط تیزر را می‌دهد — هرگز متن ساخته‌شده. پرچم `<bild:premium>` در فید همان سیگنال در سطح فید است.
- فقط بخش‌های فهرست‌شده فید دارند — wirtschaft در سایت زنده 404 می‌دهد؛ هیچ ابزار wirtschaft وجود ندارد. فیدهای بخش در `/feed/<section>.xml` قرار دارند.
- داده‌ها: فیدهای عمومی RSS و صفحه‌های مقالهٔ BILD — بدون کلید، بدون لاگین، فقط خواندنی.

## توسعه

```bash
python3 -m venv .venv && .venv/bin/pip install "mcp<2" httpx pytest
.venv/bin/pip install -e .
.venv/bin/python -m pytest tests/ -q
```

- `tests/test_domain.py` — آفلاین؛ فیدهای واقعی ذخیره‌شدهٔ اصلی، politik و sport و دو صفحهٔ مقالهٔ واقعی (یک مقالهٔ رایگان و یک مقالهٔ BILDplus) را تجزیه می‌کند
- `tests/test_live.py` — درخواست‌های زندهٔ محتاطانه به www.bild.de

تست‌ها: ۲۷ از ۲۷ سبز (۲۰ آفلاین + ۷ زنده، ۲۰۲۶-۱۱-۲۴).

## مجوز

[PolyForm Noncommercial 1.0.0](https://polyformproject.org/licenses/noncommercial/1.0.0/) — رایگان برای استفادهٔ شخصی و غیرتجاری؛ استفادهٔ تجاری نیازمند مجوز جداگانه است (به LICENSE مراجعه کنید).

---

ساختهٔ [محمد عباسی](https://github.com/mohammad-abbasi-sh) — [آلمانی‌باما](https://almanibama.ir) · [mabbasi.ir](https://mabbasi.ir)
