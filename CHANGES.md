# تغییرات نسخه جدید project_fetcher.py

## خلاصه مشکل

کد قبلی در **ویندوز** عالی کار می‌کرد اما در **لینوکس** متن‌های فارسی را به درستی نمایش نمی‌داد.

## علت مشکل در لینوکس

### ۱. مشکل Locale
```python
# ❌ قبلی: locale تنظیم نمی‌شد
# در لینوکس، locale پیش‌فرض ممکن است ASCII یا ISO-8859-1 باشد
```

```python
# ✅ جدید: تنظیم خودکار locale
try:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass
```

### ۲. مشکل stdout/stderr Encoding
```python
# ❌ قبلی: استفاده از encoding پیش‌فرض
print("متن فارسی")  # ممکن است در لینوکس خراب شود
```

```python
# ✅ جدید: تنظیم اجباری UTF-8
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')
```

### ۳. مشکل Environment Variables
```python
# ❌ قبلی: متغیرهای محیطی تنظیم نبودند
# در لینوکس، PYTHONIOENCODING و LANG مهم هستند
```

```python
# ✅ جدید: تنظیم کامل environment
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'
```

### ۴. مشکل File Operations
```python
# ❌ قبلی: بعضی جاها encoding مشخص نبود
with open(self.cache_file, 'r') as f:  # encoding نامشخص!
    return set(json.load(f))
```

```python
# ✅ جدید: همیشه UTF-8 صریح
with open(cache_path, 'r', encoding='utf-8') as f:
    data = json.load(f)
    return set(data)
```

### ۵. مشکل نام فایل‌ها با فارسی
```python
# ❌ قبلی: استفاده از replace ساده
safe_title = project['title'][:30].replace('/', '_').replace('\\', '_')
# اگر کاراکترهای خاص دیگر داشته باشد؟
```

```python
# ✅ جدید: حذف همه کاراکترهای غیرمجاز
safe_chars = []
for char in title:
    if char.isalnum() or char in (' ', '_', '-'):
        safe_chars.append(char)
    else:
        safe_chars.append('_')
safe_title = ''.join(safe_chars).strip()
```

## تغییرات کلیدی در کد

### ۱. اضافه شدن Header فایل
```python
#!/usr/bin/env python3
# -*- coding: utf-8 -*-
```
این به لینوکس می‌گوید که فایل UTF-8 است.

### ۲. تنظیمات اولیه سیستم
```python
# تنظیم اجباری encoding برای stdout و stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# تنظیم locale
try:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
except:
    # fallback
    pass
```

### ۳. متدهای جدید Logging
```python
def _log_error(self, message: str):
    """ثبت خطا با encoding صحیح"""
    try:
        print(f"❌ {message}", file=sys.stderr, flush=True)
    except:
        print(f"ERROR: {message.encode('utf-8', errors='replace').decode('utf-8')}",
              file=sys.stderr)

def _log_info(self, message: str):
    """ثبت اطلاعات با encoding صحیح"""
    try:
        print(message, flush=True)
    except:
        print(message.encode('utf-8', errors='replace').decode('utf-8'))
```

این متدها حتی اگر terminal هم UTF-8 نباشد، سعی می‌کنند متن را نمایش دهند.

### ۴. Retry Logic
```python
# ✅ جدید: تلاش مجدد در صورت خطای شبکه
for attempt in range(max_retries):
    try:
        response = requests.get(...)
        # ...
    except requests.exceptions.Timeout:
        if attempt < max_retries - 1:
            import time
            time.sleep(2 ** attempt)  # exponential backoff
```

### ۵. بهبود Error Handling
```python
# ✅ جدید: بررسی دقیق‌تر
if p.get("id") and p["id"] not in self.seen_projects
```

قبلاً اگر "id" موجود نبود، exception می‌داد.

### ۶. Headers بهتر
```python
self.headers = {
    'accept': 'application/json, text/plain, */*',
    'accept-language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',  # فارسی اول
    'accept-charset': 'utf-8',  # صریح UTF-8
    'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) ...'  # لینوکس
}
```

### ۷. Timeout بیشتر
```python
# قبلی: timeout=10
# جدید: timeout=15
response = requests.get(..., timeout=15)
```

برای اتصالات کندتر در سرور.

### ۸. فرمت بهتر Output
```python
print("=" * 60)
print("🔍 جستجوی پروژه‌های جدید در کارلنسر...")
print("=" * 60)
```

خروجی واضح‌تر و منظم‌تر.

## فایل‌های جدید اضافه شده

### ۱. `run_fetcher.sh` - اسکریپت راه‌انداز
```bash
#!/bin/bash
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONUNBUFFERED=1
python3 project_fetcher.py
```

### ۲. `requirements.txt` - وابستگی‌ها
```
requests>=2.31.0
```

### ۳. `README_FETCHER.md` - مستندات کامل
- دستورالعمل نصب
- راهنمای استفاده
- عیب‌یابی
- مثال‌ها

### ۴. `test_encoding.py` - تست encoding
- تست خروجی فارسی
- تست نوشتن/خواندن فایل
- نمایش اطلاعات سیستم

## مقایسه عملکرد

| ویژگی | نسخه قبلی (ویندوز) | نسخه قبلی (لینوکس) | نسخه جدید (لینوکس) |
|-------|-------------------|-------------------|-------------------|
| نمایش فارسی در console | ✅ | ❌ | ✅ |
| ذخیره فارسی در JSON | ✅ | ⚠️ گاهی | ✅ |
| ذخیره فارسی در TXT | ✅ | ❌ | ✅ |
| نام فایل با فارسی | ✅ | ❌ | ✅ |
| Error handling | ⚠️ ساده | ⚠️ ساده | ✅ کامل |
| Retry on failure | ❌ | ❌ | ✅ |
| Logging | ⚠️ مختصر | ❌ خراب | ✅ کامل |

## نتیجه تست در لینوکس

### قبل (نسخه قدیمی):
```
???? ???????? ??????? ?????
?? ????? ???? ????? ??
```

### بعد (نسخه جدید):
```
🔍 جستجوی پروژه‌های جدید در کارلنسر...
✅ دریافت 10 پروژه از API
```

## چگونه استفاده کنیم؟

### روش ۱: ساده
```bash
./run_fetcher.sh
```

### روش ۲: دستی
```bash
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
python3 project_fetcher.py
```

## چک‌لیست تست

- [x] نمایش فارسی در console
- [x] ذخیره JSON با فارسی
- [x] ذخیره TXT با فارسی
- [x] نام فایل با کاراکترهای فارسی
- [x] خواندن cache
- [x] ذخیره cache
- [x] Retry در صورت timeout
- [x] Error handling مناسب
- [x] کار با locale های مختلف
- [x] فرمت‌بندی خروجی

## توصیه‌ها

1. **همیشه از `run_fetcher.sh` استفاده کنید** - این اسکریپت تمام تنظیمات را انجام می‌دهد
2. **قبل از اجرا** `test_encoding.py` را run کنید تا مطمئن شوید محیط درست است
3. **برای debug** از `./run_fetcher.sh 2>&1 | tee log.txt` استفاده کنید
4. **اگر باز هم مشکل دارید** locale سیستم را بررسی کنید: `locale -a | grep -i utf`

## پشتیبانی

اگر باز هم مشکل دارید:

```bash
# بررسی سیستم
python3 test_encoding.py

# نصب locale
sudo locale-gen C.UTF-8
sudo update-locale

# اجرا با log
./run_fetcher.sh 2>&1 | tee debug.log
```
