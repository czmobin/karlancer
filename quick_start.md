# راهنمای سریع - Karelancer Automation

## مشکل شما

```bash
./analyze.sh
⚠️ Analysis failed
```

## راه‌حل فوری

### گام ۱: عیب‌یابی (۳۰ ثانیه)

```bash
bash debug_analyzer.sh
```

این برنامه به شما می‌گوید دقیقاً چه مشکلی وجود دارد.

### گام ۲: استفاده از نسخه جدید

به جای `analyze.sh` از `analyze_fixed.sh` استفاده کنید:

```bash
# ❌ قدیمی (مشکل دارد)
./analyze.sh

# ✅ جدید (کار می‌کند)
bash analyze_fixed.sh
```

### گام ۳: اگر هنوز مشکل دارید

با debug اجرا کنید:

```bash
DEBUG=1 bash analyze_fixed.sh
```

## چه تغییراتی ایجاد شد؟

### فایل‌های جدید:

1. **analyze_fixed.sh** - نسخه بهبود یافته analyzer با:
   - ✅ پشتیبانی کامل UTF-8
   - ✅ Error handling پیشرفته
   - ✅ Logging کامل
   - ✅ Debug mode
   - ✅ Timeout برای Claude
   - ✅ بررسی‌های دقیق

2. **debug_analyzer.sh** - ابزار عیب‌یابی که:
   - بررسی می‌کند تمام ابزارها نصب هستند
   - بررسی می‌کند فایل‌ها و پوشه‌ها موجودند
   - تست می‌کند Claude کار می‌کند
   - مشکلات را شناسایی می‌کند

3. **ANALYZER_FIX.md** - راهنمای کامل و جامع

## دستورات مهم

```bash
# ۱. بررسی سیستم
bash debug_analyzer.sh

# ۲. دریافت پروژه‌های جدید
python3 project_fetcher.py
# یا
./run_fetcher.sh

# ۳. تحلیل پروژه‌ها
bash analyze_fixed.sh

# ۴. تحلیل با debug (برای مشاهده جزئیات)
DEBUG=1 bash analyze_fixed.sh

# ۵. مشاهده نتایج
ls -lh proposals/
cat proposals/project_*_analysis.txt

# ۶. بررسی لاگ
cat analyzer.log
```

## علت مشکل در analyze.sh قدیمی

1. ❌ Environment variables برای UTF-8 تنظیم نبودند
2. ❌ Error handling ضعیف بود
3. ❌ Timeout نداشت
4. ❌ Debug mode نداشت
5. ❌ بررسی‌های لازم نمی‌کرد

## Workflow کامل

```bash
# هر روز یک بار:

# ۱. دریافت پروژه‌های جدید
python3 project_fetcher.py

# ۲. تحلیل پروژه‌ها
bash analyze_fixed.sh

# ۳. مشاهده نتایج
ls -lh proposals/

# ۴. ارسال proposal (دستی)
python3 submit_proposal.py proposals/project_XXXXX_analysis.txt
```

## نکته مهم

اگر هنوز `claude_input/` خالی است:
```bash
# اول پروژه‌ها را دریافت کنید
python3 project_fetcher.py

# سپس تحلیل کنید
bash analyze_fixed.sh
```

## پشتیبانی

اگر مشکل ادامه دارد:

```bash
# لاگ کامل بگیرید
bash debug_analyzer.sh > debug.log 2>&1
DEBUG=1 bash analyze_fixed.sh > analyze.log 2>&1

# فایل‌های debug.log و analyze.log را بررسی کنید
```

---

**خلاصه:** به جای `analyze.sh` از `analyze_fixed.sh` استفاده کنید!
