# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## معرفی پروژه

ربات خودکار پلتفرم کارلنسر (karlancer.com). به صورت مداوم پروژه‌های جدید رو از API دریافت می‌کنه، با Claude CLI تحلیل و پروپوزال فارسی تولید می‌کنه و فورا ارسال می‌کنه. نوتیفیکیشن‌ها از طریق بات تلگرام ارسال میشه.

همه کد توی یک فایل `karlancer.py` هست. زبان کدبیس پایتون هست و متون کاربری فارسی. علاوه بر ارسال پروپوزال، ربات چت‌های کارفرماها رو هم مدیریت می‌کنه و تا رسیدن به تایید اولیه باهاشون صحبت می‌کنه.

## متغیرهای محیطی

توکن‌ها توی فایل `.env` هستن (git-ignored):

```
KARELANCER_BEARER=...
TELEGRAM_BOT_TOKEN=...
GITHUB_TOKEN=...
```

## اجرا

```bash
# نصب وابستگی‌ها
pip3 install -r requirements.txt

# اجرای مداوم (پیش‌فرض هر ۵ دقیقه)
python3 karlancer.py

# با interval دلخواه
python3 karlancer.py --interval 120

# یک‌بار اجرا (بدون loop)
python3 karlancer.py --once

# فقط چت‌ها (بدون ارسال پروپوزال)
python3 karlancer.py --chat-only

# تنظیم تلگرام (یک‌بار)
python3 karlancer.py --setup-telegram
```

## ساختار فایل‌ها

```
karlancer.py              # کل ربات (fetch + analyze + submit + chat + telegram)
karelancer_prompt.txt     # سیستم پرامپت پروپوزال
chat_prompt.txt           # سیستم پرامپت چت با کارفرما
.env                      # توکن‌ها (git-ignored)
requirements.txt          # وابستگی‌ها
```

## معماری

همه چیز توی `karlancer.py` هست — سه کلاس اصلی:

- **`Karlancer`** — ربات اصلی. لوپ: دریافت از API ← ذخیره روی دیسک ← فراخوانی `claude <tempfile>` ← استخراج پروپوزال از خروجی ← ارسال به `/api/bids` ← نوتیفیکیشن تلگرام. فیلتری وجود نداره؛ هر پروژه‌ای تحلیل بشه حتما ارسال میشه.
- **`ChatManager`** — مدیریت چت با کارفرماها. هر ۵ دقیقه اتاق‌ها رو چک می‌کنه، پیام‌های جدید کارفرما رو با Claude تحلیل و پاسخ تولید می‌کنه و ارسال می‌کنه. تا رسیدن به تایید اولیه ادامه میده. State هر اتاق در `chats/{room_id}/state.json`.
- **`TelegramLogger`** — ارسال نوتیفیکیشن‌های HTML به تلگرام (شروع، پروژه جدید، ارسال، خطا، خاموشی).

### جریان داده

1. `karlancer.com/api/publics/search/projects` ← فیلتر با `seen_projects.json` ← `claude_input/project_<ID>.txt`
2. `karelancer_prompt.txt` + متن پروژه ← `claude <tempfile>` (تایم‌اوت ۳۰۰ ثانیه) ← `proposals/project_<ID>_analysis.txt`
3. استخراج بخش پروپوزال (مارکر `📝 پروپوزال`) ← تشخیص بودجه (API ← regex ← پیش‌فرض) ← POST به `/api/bids`

### جریان چت

1. `karlancer.com/api/rooms/?page=N` ← لیست اتاق‌های فعال
2. `karlancer.com/api/rooms/{ID}/messages-pg?page=1` ← پیام‌های هر اتاق
3. اگر پیام جدید از کارفرما: `chat_prompt.txt` + اطلاعات پروژه + مکالمه ← `claude -p` ← پاسخ
4. ارسال پاسخ به `karlancer.com/api/messages` ← ذخیره state در `chats/{room_id}/`
5. اگر کارفرما تایید اولیه داد ← وضعیت "approved" ← نوتیفیکیشن تلگرام

### فایل‌های State (خارج از git)

- `seen_projects.json` — مجموعه ID پروژه‌های پردازش‌شده (دداپ)
- `tracking.json` — آمار تجمیعی و جزئیات هر پروژه
- `.telegram_chat_id` — چت آیدی تلگرام
- `claude_input/` — پروژه‌های دریافتی
- `proposals/` — خروجی تحلیل‌ها
- `chats/` — فولدرهای چت هر کارفرما (هر اتاق یک فولدر جدا)

## نکات کلیدی

- **همیشه ارسال میشه:** هر پروژه‌ای که تحلیل بشه حتما پروپوزالش ارسال میشه. حالت "فقط تحلیل" وجود نداره.
- **پروژه بی‌کیفیت:** اگه بودجه زیر ۱ میلیون باشه یا تکنولوژی نامناسب (wordpress/php) داشته باشه، `سلام` به `SALAM` تغییر می‌کنه تا قبل ارسال بررسی بشه.
- **UTF-8:** تمام I/O فارسی هست. `sys.stdout.reconfigure(encoding='utf-8')` و `LANG=C.UTF-8` فورس میشه.
- **Claude CLI:** تحلیل با `claude <tempfile>` به صورت subprocess اجرا میشه. خروجی از نویز CLI فیلتر میشه.
- **پروپوزال‌ها** با `سلام،` شروع و با `با تشکر،\nمبین اقایی\nSenior Python Backend Developer` تموم میشن.
- **سیستم پرامپت** (`karelancer_prompt.txt`) موقع رد پروژه همیشه بودجه کم رو مقصر می‌دونه، هیچ‌وقت نمیگه «تخصص من نیست».
