# 🚀 شروع سریع - ربات مداوم

## در 30 ثانیه!

```bash
# ۱. اجرای ربات (هر 5 دقیقه چک می‌کنه)
bash run_continuous_bot.sh

# ۲. برای توقف: Ctrl+C
```

همین! ✅

---

## چه اتفاقی می‌افتد؟

```
🔍 جستجوی پروژه‌های جدید...
✅ 3 پروژه جدید پیدا شد!

📋 پروژه 257578: توسعه ربات تلگرام
  → تحلیل با Claude...
  → ✅ ذخیره در proposals/project_257578_analysis.txt

📋 پروژه 257472: سایت Django
  → تحلیل با Claude...
  → ✅ ذخیره در proposals/project_257472_analysis.txt

😴 استراحت 5 دقیقه تا چرخه بعدی...
```

## تنظیمات سریع

### فاصله زمانی

```bash
# هر 2 دقیقه (120 ثانیه)
bash run_continuous_bot.sh 120

# هر 10 دقیقه (600 ثانیه)
bash run_continuous_bot.sh 600
```

### فقط یک بار (تست)

```bash
bash run_continuous_bot.sh 300 once
```

### اجرا در Background

```bash
# شروع
nohup bash run_continuous_bot.sh 300 > bot.log 2>&1 &

# ذخیره PID
echo $! > bot.pid

# مشاهده
tail -f bot.log

# توقف
kill $(cat bot.pid)
```

## فایل‌های خروجی

```
proposals/                        ← فایل‌های تحلیل شده (proposal)
├── project_257578_analysis.txt
├── project_257472_analysis.txt
└── ...

continuous_bot.log                ← لاگ کامل
continuous_tracking.json          ← آمار و وضعیت
```

## مشاهده نتایج

```bash
# لیست proposal ها
ls -lht proposals/

# خواندن یکی
cat proposals/project_257578_analysis.txt

# آمار
cat continuous_tracking.json | jq
```

## مشکلات رایج

### "Claude CLI not found"
```bash
which claude  # باید مسیر نشان بدهد
```

### "karelancer_prompt.txt not found"
```bash
ls karelancer_prompt.txt  # باید وجود داشته باشد
```

### چک کامل
```bash
bash debug_analyzer.sh
```

## دستورات مفید

```bash
# اجرا
bash run_continuous_bot.sh

# اجرا در background
nohup bash run_continuous_bot.sh > bot.log 2>&1 &

# مشاهده لاگ
tail -f continuous_bot.log

# آمار
cat continuous_tracking.json | jq

# لیست proposal ها
ls -lht proposals/ | head -10

# توقف (اگر در foreground)
Ctrl+C

# توقف (اگر در background)
kill $(cat bot.pid)
```

## Workflow روزانه

```bash
# صبح: شروع ربات
bash run_continuous_bot.sh 300 &

# در طول روز: ربات کار می‌کنه

# عصر: بررسی proposal ها
ls -lht proposals/
cat proposals/project_*_analysis.txt

# ارسال دستی proposal های خوب
python3 submit_proposal.py proposals/project_XXXXX_analysis.txt

# شب: توقف (اختیاری)
Ctrl+C
```

## نکات طلایی

💡 **بهترین فاصله:** 5 دقیقه (300 ثانیه)
💡 **همیشه background:** از `nohup` یا `screen` استفاده کنید
💡 **چک روزانه:** proposal ها رو بررسی و ارسال کنید
💡 **Monitoring:** هر چند ساعت لاگ رو چک کنید

---

برای اطلاعات بیشتر: `CONTINUOUS_BOT.md`
