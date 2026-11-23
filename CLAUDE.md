# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## معرفی پروژه

ربات خودکار پلتفرم کارلنسر (karlancer.com). کل چرخه فریلنسینگ رو اتوماتیک می‌کنه:
دریافت پروژه ← تحلیل ← پروپوزال ← چت با کارفرما ← استخدام ← دپلوی روی سرور ← تحویل

همه کد توی یک فایل `karlancer.py` هست. زبان کدبیس پایتون، متون کاربری فارسی.

## متغیرهای محیطی

```
KARELANCER_BEARER=...   # Bearer token
TELEGRAM_BOT_TOKEN=...  # اختیاری، نوتیفیکیشن
GITHUB_TOKEN=...        # برای ساخت ریپو (scope: repo)
```

## اجرا

```bash
pip3 install -r requirements.txt

python3 karlancer.py                      # لوپ کامل (هر ۵ دقیقه)
python3 karlancer.py --interval 120       # با interval دلخواه
python3 karlancer.py --no-proxy           # بدون پروکسی
python3 karlancer.py --once               # یک‌بار
python3 karlancer.py --chat-only          # فقط چت، بدون پروپوزال
python3 karlancer.py --project <url/slug> # یک پروژه خاص
python3 karlancer.py --setup-telegram     # تنظیم تلگرام
```

## ساختار فایل‌ها

```
karlancer.py           # کل ربات
karelancer_prompt.txt  # پرامپت تحلیل + پروپوزال
chat_prompt.txt        # پرامپت چت pre-hire
deploy_prompt.txt      # پرامپت post-hire (سرور + دپلوی)
.env                   # توکن‌ها (git-ignored)
requirements.txt       # وابستگی‌ها
```

## معماری — سه کلاس

### `run_claude(model, prompt, timeout, log_fn)` — تابع سطح ماژول
همه فراخوانی‌های Claude CLI ازش استفاده می‌کنن.
- اگه `returncode != 0` و `stderr` حاوی `rate limit / 429 / overloaded` بود → sleep و retry
- زمان sleep از پیام استخراج میشه (ثانیه/دقیقه)، پیش‌فرض ۶۰ ثانیه

---

### `TelegramLogger`
ارسال نوتیفیکیشن HTML به تلگرام: شروع، پروژه جدید، ارسال موفق، خطا، استخدام، دپلوی

---

### `ChatManager`
مدیریت کامل چت با کارفرماها. State هر اتاق در `chats/{room_id}/state.json`

**فیلدهای state:**
- `status`: `""` / `"approved"` / `"hired"` / `"deploying"` / `"deployed"` / `"done"`
- `last_responded_msg_id`: آخرین پیامی که جواب دادیم
- `repo_name`: نام ریپوی GitHub ساخته‌شده
- `workdiary_id` / `workdiary_title`: مشخصات میزکار
- `server`: `{ip, user, pass}` اطلاعات سرور کارفرما
- `deploy_path`: مسیر دپلوی روی سرور

**flow چت:**

```
پیام جدید
  ↓
workdiary_projects accepted? → hired (نوتیف تلگرام)
  ↓
status == hired/deploying/deployed → deploy_prompt.txt
  ↓ [SERVER: ip=X user=Y pass=Z] در پاسخ Claude
SSH deploy → send "کد نصب شد، تست کنید"
  ↓ [DONE] در پاسخ Claude
status = done
```

**pre-hire flow:**
```
پیام جدید
  ↓
ریپو GitHub نداره? → _setup_repo_for_room → _create_repo + _generate_initial_code + _push_to_repo
  ↓
_generate_response (chat_prompt) → [APPROVED]? → approved
```

**متدهای اصلی:**
- `check_and_respond()` — حلقه اصلی، اتاق‌ها رو بررسی میکنه
- `_process_room(room)` — پردازش یک اتاق
- `_generate_response(ctx, proposal, conv, phase)` — Claude، برمیگردونه `(text, approved, server_info, done)`
- `_ssh_deploy(ip, user, pass, repo_name)` — SSH → git clone → pip install
- `_setup_repo_for_room(...)` — اگه ریپو نداره بسازه و کد اولیه push کنه

---

### `Karlancer`
ربات اصلی پروپوزال

**فیلتر پروژه‌ها (`_is_relevant`):**
1. پروژه‌های بیشتر از ۵ روز → رد
2. مهارت‌های فنی دارن → قبول (TECH_SKILLS whitelist)
3. مهارت‌های غیرفنی همه → رد
4. بدون مهارت → چک SKIP_KEYWORDS روی عنوان + توضیحات

**بررسی bid قبلی (`refresh_bid_cache`):**
- اولین بار: همه صفحات `/api/bids` فچ میشه
- بعدی: فقط ۳ صفحه اخیر (incremental)

**milestones (`submit_proposal`):**
- `≤7 روز`: پیش‌پرداخت (۳۰٪) + تحویل کامل (۷۰٪)
- `>7 روز`: پیش‌پرداخت (۳۰٪) + مرحله اول (۳۵٪) + تحویل نهایی (۳۵٪)
- HTTP 409 = قبلاً فرستادی → warn، ادامه (به seen_projects اضافه میشه)

**جریان داده:**
```
fetch_projects (11 کوئری × 2 صفحه، newest-first، dedup)
  ↓ _is_relevant + seen_projects + bid_project_ids
save_project → claude <tempfile> → extract_proposal
  ↓
submit_proposal → POST /api/bids
```

## نکات مهم

- **همیشه ارسال میشه:** فیلتری وجود نداره پس از تحلیل. هر پروژه تحلیل‌شده ارسال میشه.
- **بی‌کیفیت:** بودجه < ۱M یا وردپرس/PHP → `سلام` به `SALAM`
- **سرور:** اگه پروژه نیاز به سرور داره پروپوزال بگوید (هزینه ~۱ تا ۱.۸ میلیون ماهانه)
- **rate limit:** `run_claude` لوپ میزنه تا Claude آزاد بشه
- **پروکسی:** socks5h، `--no-proxy` برای اتصال مستقیم
- **UTF-8:** همه I/O فارسی

## فایل‌های State (خارج از git)

```
seen_projects.json    # پروژه‌های پردازش‌شده
tracking.json         # آمار
.telegram_chat_id     # چت آیدی تلگرام
claude_input/         # ورودی تحلیل
proposals/            # خروجی تحلیل
chats/{room_id}/      # state هر اتاق
  state.json
  conversation.txt
  repo/               # کد MVP دپلوی‌شده
```

## هزینه سرور (پارس‌پک، آلمان)

| RAM | SSD  | قیمت ماهانه |
|-----|------|------------|
| 4GB | 60GB | ~۱.۷۵M     |
| 2GB | 50GB | ~۱.۴۵M     |

ایران ارزان‌تره ولی ترافیک محدودتر (200GB).
