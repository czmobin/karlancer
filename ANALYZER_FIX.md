# رفع مشکل Analyzer در لینوکس

## مشکل گزارش شده

```bash
./analyze.sh
⚠️ Analysis failed
```

تمام پروژه‌ها با خطای "Analysis failed" مواجه می‌شدند.

## علل احتمالی مشکل

### ۱. مشکل Encoding و UTF-8
```bash
# ❌ در اسکریپت قبلی environment variables تنظیم نبودند
# این باعث می‌شد فایل‌های فارسی درست خوانده نشوند
```

### ۲. Error Handling ضعیف
```bash
# ❌ خطاهای دقیق نمایش داده نمی‌شدند
# فقط "Analysis failed" نمایش داده می‌شد بدون جزئیات
```

### ۳. مشکل در خروجی Claude
```bash
# ❌ فیلتر کردن noise از خروجی Claude کامل نبود
# ❌ بررسی طول خروجی درست نبود
```

### ۴. مشکل Timeout
```bash
# ❌ timeout برای Claude تنظیم نشده بود
# اگر Claude hang می‌کرد، اسکریپت هم می‌ایستاد
```

### ۵. مشکل File Handling
```bash
# ❌ چک نمی‌شد که فایل readable باشد
# ❌ temp files درست پاک نمی‌شدند
```

## راه‌حل: analyze_fixed.sh

یک نسخه کاملاً بازنویسی شده با این بهبودها:

### ✅ ۱. تنظیمات Encoding کامل

```bash
# تنظیم environment variables
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8

# استفاده از strict mode
set -euo pipefail
```

### ✅ ۲. Logging پیشرفته

```bash
# توابع logging با رنگ و ذخیره در فایل
log_error()   # خطاها
log_success() # موفقیت‌ها
log_info()    # اطلاعات
log_warning() # هشدارها
log_debug()   # debug (فقط با DEBUG=1)
```

### ✅ ۳. بررسی‌های دقیق‌تر

```bash
# بررسی نصب بودن jq
if ! command -v jq &> /dev/null; then
    # نصب خودکار
fi

# بررسی Claude CLI
if ! command -v claude &> /dev/null; then
    log_error "Claude CLI not found"
    exit 1
fi

# بررسی readable بودن فایل
if [ ! -r "$file" ]; then
    log_error "Cannot read file"
    continue
fi
```

### ✅ ۴. Timeout و Error Handling

```bash
# اجرا با timeout 300 ثانیه (5 دقیقه)
if timeout 300 claude "$TEMP_FILE" > "output_${PROJECT_ID}.tmp" 2>&1; then
    # موفقیت
else
    EXIT_CODE=$?
    log_error "Claude failed (exit code: $EXIT_CODE)"
    # نمایش error message
fi
```

### ✅ ۵. بهبود File Handling

```bash
# ذخیره خروجی در فایل موقت
claude "$TEMP_FILE" > "output_${PROJECT_ID}.tmp" 2>&1

# سپس خواندن و پردازش
OUTPUT=$(cat "output_${PROJECT_ID}.tmp")

# پاکسازی در پایان
rm -f "$TEMP_FILE" "output_${PROJECT_ID}.tmp"
```

### ✅ ۶. فیلتر بهتر Noise

```bash
# فیلتر کردن پیام‌های اضافی Claude
CLEAN_OUTPUT=$(echo "$OUTPUT" | \
    grep -v -E "trust|folder|security|Enter to|Do you trust|^─+$|^\s*$" | \
    grep -v "^$" || echo "$OUTPUT")
```

### ✅ ۷. Debug Mode

```bash
# فعال‌سازی با:
DEBUG=1 bash analyze_fixed.sh

# نمایش اطلاعات اضافی:
log_debug "Processing: $file"
log_debug "Project text loaded (${#PROJECT_TEXT} chars)"
log_debug "Claude output: $OUTPUT_LENGTH chars"
```

## ابزار Debug: debug_analyzer.sh

اسکریپت عیب‌یابی کامل که موارد زیر را بررسی می‌کند:

### ۱. Encoding & Locale
- بررسی LANG, LC_ALL, PYTHONIOENCODING
- اطمینان از UTF-8

### ۲. ابزارهای مورد نیاز
- Python3
- jq
- Claude CLI
- تست کارکرد Claude

### ۳. فایل‌های مورد نیاز
- karelancer_prompt.txt
- project_fetcher.py
- بررسی encoding فایل‌ها

### ۴. پوشه‌ها
- claude_input/
- proposals/
- new_projects/
- شمارش فایل‌های موجود

### ۵. Tracking
- analyzed_projects.json
- لیست پروژه‌های تحلیل شده

### ۶. تست نمونه
- خواندن یک فایل project
- بررسی encoding
- چک وجود متن فارسی

## راهنمای استفاده

### مرحله ۱: عیب‌یابی

```bash
# اجرای debug برای شناسایی مشکلات
bash debug_analyzer.sh
```

خروجی نمونه:
```
🔍 Karelancer Analyzer Debugger
================================================================================

1️⃣  Encoding & Locale:
  LANG=C.UTF-8
  LC_ALL=C.UTF-8
✅ Locale is UTF-8

2️⃣  Required Tools:
✅ Python3: Python 3.11.14
✅ jq: jq-1.6
✅ Claude CLI: /opt/node22/bin/claude

3️⃣  Required Files:
✅ karelancer_prompt.txt (9527 bytes)
✅ Prompt file is UTF-8

4️⃣  Directories:
❌ claude_input/ directory not found
⚠️  No project files in claude_input/
     Run: python3 project_fetcher.py
```

### مرحله ۲: دریافت پروژه‌ها (اگر نیاز است)

```bash
# اگر claude_input/ خالی است
python3 project_fetcher.py
```

یا با اسکریپت راه‌انداز:
```bash
./run_fetcher.sh
```

### مرحله ۳: تحلیل پروژه‌ها

```bash
# حالت عادی
bash analyze_fixed.sh

# با debug برای مشاهده جزئیات
DEBUG=1 bash analyze_fixed.sh
```

### مرحله ۴: بررسی نتایج

```bash
# مشاهده فایل‌های تحلیل شده
ls -lh proposals/

# خواندن یک نمونه
cat proposals/project_257578_analysis.txt

# بررسی tracking
cat analyzed_projects.json | jq

# مشاهده لاگ
cat analyzer.log
```

## مقایسه نسخه قدیم و جدید

| ویژگی | analyze.sh (قدیمی) | analyze_fixed.sh (جدید) |
|-------|-------------------|------------------------|
| Encoding | ❌ تنظیم نشده | ✅ کامل (UTF-8) |
| Error handling | ⚠️ ساده | ✅ پیشرفته |
| Logging | ⚠️ محدود | ✅ کامل + فایل log |
| Debug mode | ❌ ندارد | ✅ دارد |
| Timeout | ❌ ندارد | ✅ 300s |
| File checks | ⚠️ ناقص | ✅ کامل |
| Error messages | ❌ مبهم | ✅ واضح |
| Temp cleanup | ⚠️ گاهی | ✅ همیشه |
| Exit codes | ⚠️ ناقص | ✅ کامل |
| Progress info | ⚠️ کم | ✅ دقیق |

## حل مشکلات رایج

### مشکل ۱: "Claude CLI not found"

```bash
# بررسی نصب بودن
which claude

# اگر نصب نیست:
# از سایت رسمی دانلود کنید
# یا از npm نصب کنید (اگر موجود باشد)
```

### مشکل ۲: "jq not found"

```bash
# Ubuntu/Debian:
sudo apt-get update && sudo apt-get install -y jq

# CentOS/RHEL:
sudo yum install -y jq

# macOS:
brew install jq
```

### مشکل ۳: "No project files"

```bash
# دریافت پروژه‌ها
python3 project_fetcher.py

# یا:
./run_fetcher.sh
```

### مشکل ۴: "Analysis failed - output too short"

این معمولاً به این معانی است:
- Claude خطا داده
- Token limit رسیده
- Connection timeout

راه‌حل:
```bash
# با debug اجرا کنید
DEBUG=1 bash analyze_fixed.sh

# لاگ را بررسی کنید
cat analyzer.log

# خروجی temp را نگه دارید (کامنت کنید rm -f)
```

### مشکل ۵: "Locale not UTF-8"

```bash
# نصب locale
sudo locale-gen C.UTF-8
sudo update-locale

# یا manually تنظیم
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
```

## نکات مهم

### ۱. استفاده از analyze_fixed.sh به جای analyze.sh

```bash
# ❌ قدیمی
./analyze.sh

# ✅ جدید
bash analyze_fixed.sh
```

### ۲. Debug Mode برای عیب‌یابی

```bash
DEBUG=1 bash analyze_fixed.sh 2>&1 | tee debug.log
```

### ۳. بررسی Logs

```bash
# لاگ analyzer
cat analyzer.log

# لاگ‌های سیستم (اگر نیاز است)
tail -f /var/log/syslog | grep claude
```

### ۴. Monitoring تحلیل

```bash
# در ترمینال دیگری
watch -n 2 'ls -lh proposals/ | tail -5'

# یا
watch -n 2 'jq "length" analyzed_projects.json'
```

## Workflow کامل

```bash
# ۱. عیب‌یابی
bash debug_analyzer.sh

# ۲. دریافت پروژه‌ها (اگر نیاز است)
python3 project_fetcher.py

# ۳. تحلیل
bash analyze_fixed.sh

# یا با debug
DEBUG=1 bash analyze_fixed.sh

# ۴. بررسی نتایج
ls -lh proposals/
cat proposals/project_*_analysis.txt | less
```

## Cron Job (اختیاری)

برای اجرای خودکار هر ساعت:

```bash
# ویرایش crontab
crontab -e

# اضافه کردن:
0 * * * * cd /path/to/karlancer && python3 project_fetcher.py && bash analyze_fixed.sh
```

## پشتیبانی

اگر باز هم مشکل دارید:

```bash
# ۱. اجرای debug
bash debug_analyzer.sh > debug_output.txt 2>&1

# ۲. اجرای analyzer با debug
DEBUG=1 bash analyze_fixed.sh > analyzer_output.txt 2>&1

# ۳. ارسال فایل‌های لاگ:
# - debug_output.txt
# - analyzer_output.txt
# - analyzer.log
```

## خلاصه تغییرات

تمام مشکلات encoding، error handling، logging و timeout در نسخه جدید حل شده است:

✅ **analyze_fixed.sh** - اسکریپت اصلی بهبود یافته
✅ **debug_analyzer.sh** - ابزار عیب‌یابی کامل
✅ **ANALYZER_FIX.md** - این راهنما

برای استفاده:
1. `bash debug_analyzer.sh` - بررسی سیستم
2. `python3 project_fetcher.py` - دریافت پروژه‌ها
3. `bash analyze_fixed.sh` - تحلیل پروژه‌ها
