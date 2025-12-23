# 🤖 ربات مداوم کارلنسر (Continuous Bot)

## چیست؟

یک ربات کاملاً خودکار که:
- 🔍 دائماً به دنبال پروژه‌های جدید می‌گرده
- 🤖 به محض پیدا کردن، فوراً با Claude تحلیل می‌کنه
- 📝 پروپوزال رو آماده می‌کنه
- ⏰ هر چند دقیقه یک بار این کار رو تکرار می‌کنه
- 📊 آمار کامل از همه عملیات

**منتظر نمی‌مونه!** به محض پیدا کردن هر پروژه جدید، بلافاصله پردازش می‌کنه.

## ویژگی‌های کلیدی

### ✅ پردازش Real-time
- هر پروژه به محض پیدا شدن، بلافاصله تحلیل می‌شود
- نیازی به انتظار برای تمام شدن batch نیست
- سریع‌ترین زمان پاسخ به پروژه‌های جدید

### ✅ Continuous Loop
- به صورت مداوم در حال کار است
- قابل تنظیم برای هر 1، 5، 10 دقیقه یا ...
- قابل اجرا در background با `nohup` یا `screen`

### ✅ Intelligent Caching
- پروژه‌های تکراری رو نمی‌بینه
- فقط روی پروژه‌های جدید کار می‌کنه
- مصرف بهینه منابع

### ✅ Full Logging
- لاگ کامل از تمام عملیات
- ذخیره در فایل برای بررسی بعدی
- آمار لحظه‌ای از عملکرد

### ✅ Error Recovery
- در صورت خطا، متوقف نمی‌شود
- خطاها رو لاگ می‌کنه و ادامه می‌ده
- قابل اعتماد برای اجرای طولانی‌مدت

## نصب و راه‌اندازی

### پیش‌نیازها

```bash
# ۱. Python 3
python3 --version

# ۲. Claude CLI
which claude

# ۳. کتابخانه‌های Python
pip3 install requests
```

### فایل‌های مورد نیاز

```
karlancer/
├── continuous_karlancer.py    # اسکریپت اصلی
├── run_continuous_bot.sh      # راه‌انداز
├── karelancer_prompt.txt      # System prompt برای Claude
└── (پوشه‌ها به صورت خودکار ساخته می‌شوند)
```

## استفاده

### حالت ۱: اجرای مداوم (Continuous Mode)

```bash
# با تنظیمات پیش‌فرض (هر 5 دقیقه)
bash run_continuous_bot.sh

# با فاصله دلخواه (مثلاً هر 2 دقیقه = 120 ثانیه)
bash run_continuous_bot.sh 120

# یا مستقیم با Python
python3 continuous_karlancer.py --interval 300
```

خروجی نمونه:
```
🤖 Continuous Karlancer Bot
================================================================================

⚙️  تنظیمات:
  - فاصله بررسی: 300 ثانیه (5 دقیقه)
  - حالت: continuous

✅ همه چیز آماده است
================================================================================

🚀 ربات مداوم کارلنسر شروع شد
⏰ فاصله بررسی: 300 ثانیه (5 دقیقه)
📤 ارسال خودکار: غیرفعال
================================================================================

🔄 چرخه #1 - 2024-12-23 19:30:00
ℹ️  جستجوی پروژه‌های جدید...
✅ 🆕 3 پروژه جدید پیدا شد!

================================================================================
ℹ️  [1/3] پروژه 257578: توسعه ربات تلگرام
================================================================================
ℹ️  تحلیل پروژه 257578 با Claude...
✅ تحلیل پروژه 257578 موفق (2456 chars)
ℹ️  ارسال خودکار غیرفعال است - پروژه 257578 آماده ارسال دستی

================================================================================
ℹ️  [2/3] پروژه 257472: سایت فروشگاهی Django
================================================================================
ℹ️  تحلیل پروژه 257472 با Claude...
✅ تحلیل پروژه 257472 موفق (2103 chars)

...

✅ پردازش 3 پروژه تمام شد
ℹ️  📊 آمار کل: 3 دریافت، 3 تحلیل، 0 ارسال، 0 خطا
================================================================================

😴 استراحت 300 ثانیه تا چرخه بعدی...
```

### حالت ۲: اجرای یک‌باره (Once Mode)

برای تست یا اجرای دستی:

```bash
# فقط یک بار چک می‌کنه و متوقف می‌شه
bash run_continuous_bot.sh 300 once

# یا با Python
python3 continuous_karlancer.py --once
```

### حالت ۳: اجرا در Background

برای اجرای دائمی در سرور:

```bash
# با nohup (ادامه می‌ده حتی بعد از logout)
nohup bash run_continuous_bot.sh 300 > bot.log 2>&1 &

# یا با screen
screen -S karlancer-bot
bash run_continuous_bot.sh 300
# فشار Ctrl+A سپس D برای detach

# مشاهده مجدد
screen -r karlancer-bot
```

### حالت ۴: ارسال خودکار (فعلاً غیرفعال)

```bash
# زمانی که ارسال خودکار فعال شود:
python3 continuous_karlancer.py --interval 300 --auto-submit
```

⚠️ **توجه:** فعلاً ارسال خودکار غیرفعال است و باید دستی proposal ها را ارسال کنید.

## پارامترها

### --interval

فاصله زمانی بین هر چرخه بررسی (به ثانیه)

```bash
# هر 1 دقیقه (60 ثانیه)
python3 continuous_karlancer.py --interval 60

# هر 5 دقیقه (300 ثانیه) - پیش‌فرض
python3 continuous_karlancer.py --interval 300

# هر 10 دقیقه (600 ثانیه)
python3 continuous_karlancer.py --interval 600

# هر 30 دقیقه (1800 ثانیه)
python3 continuous_karlancer.py --interval 1800
```

💡 **توصیه:** برای جلوگیری از rate limiting، حداقل 5 دقیقه (300 ثانیه) تنظیم کنید.

### --once

فقط یک بار اجرا می‌شود و خارج می‌شود (بدون loop)

```bash
python3 continuous_karlancer.py --once
```

### --auto-submit

ارسال خودکار proposal ها (فعلاً غیرفعال)

```bash
python3 continuous_karlancer.py --auto-submit
```

## فایل‌ها و پوشه‌ها

### ورودی
- `karelancer_prompt.txt` - System prompt برای Claude (الزامی)

### خروجی
- `claude_input/` - فایل‌های متنی پروژه‌ها
- `proposals/` - فایل‌های تحلیل شده (proposal)
- `seen_projects.json` - Cache پروژه‌های دیده شده
- `continuous_tracking.json` - آمار و tracking عملیات
- `continuous_bot.log` - لاگ کامل عملیات

### Tracking File

فایل `continuous_tracking.json` شامل:

```json
{
  "total_fetched": 15,
  "total_analyzed": 14,
  "total_submitted": 0,
  "total_failed": 1,
  "projects": {
    "257578": {
      "title": "توسعه ربات تلگرام",
      "fetched_at": "2024-12-23T19:30:15",
      "analyzed": true,
      "submitted": false,
      "analysis_file": "proposals/project_257578_analysis.txt"
    },
    ...
  }
}
```

## Workflow کامل

```
┌─────────────────────────────────────────────────────┐
│  شروع ربات                                          │
└────────────┬────────────────────────────────────────┘
             │
             ▼
     ┌───────────────┐
     │  Wait N min   │◄──────────────┐
     └───────┬───────┘               │
             │                       │
             ▼                       │
     ┌───────────────┐               │
     │ Fetch Projects│               │
     └───────┬───────┘               │
             │                       │
             ▼                       │
     ┌───────────────┐               │
     │ Filter New    │               │
     └───────┬───────┘               │
             │                       │
             ▼                       │
    پروژه جدید وجود دارد؟           │
             │                       │
        ┌────┴────┐                  │
        NO       YES                 │
        │         │                  │
        │         ▼                  │
        │  ┌──────────────┐          │
        │  │ For each new │          │
        │  │   project:   │          │
        │  ├──────────────┤          │
        │  │ 1. Save      │          │
        │  │ 2. Analyze   │          │
        │  │ 3. Propose   │◄─ فوری!  │
        │  └──────┬───────┘          │
        │         │                  │
        └─────────┴──────────────────┘
```

## مثال‌های کاربردی

### مثال ۱: تست اولیه

```bash
# یک بار اجرا کن و ببین چه اتفاقی می‌افته
python3 continuous_karlancer.py --once
```

### مثال ۲: اجرای روزانه

```bash
# هر 10 دقیقه چک کن (در foreground)
python3 continuous_karlancer.py --interval 600
```

### مثال ۳: اجرای دائمی در سرور

```bash
# شروع در background
nohup python3 continuous_karlancer.py --interval 300 > bot.log 2>&1 &

# ذخیره PID
echo $! > bot.pid

# مشاهده لاگ
tail -f bot.log

# توقف
kill $(cat bot.pid)
```

### مثال ۴: Monitoring

```bash
# در یک terminal
python3 continuous_karlancer.py --interval 300

# در terminal دیگر - نظارت بر proposals
watch -n 5 'ls -lht proposals/ | head -10'

# یا نظارت بر آمار
watch -n 5 'cat continuous_tracking.json | jq'
```

## Systemd Service (اختیاری)

برای اجرای خودکار در startup:

### ۱. ایجاد Service File

```bash
sudo nano /etc/systemd/system/karlancer-bot.service
```

محتوا:
```ini
[Unit]
Description=Karlancer Continuous Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/karlancer
Environment="PYTHONIOENCODING=utf-8"
Environment="LANG=C.UTF-8"
Environment="LC_ALL=C.UTF-8"
ExecStart=/usr/bin/python3 /root/karlancer/continuous_karlancer.py --interval 300
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### ۲. فعال‌سازی

```bash
# reload
sudo systemctl daemon-reload

# شروع
sudo systemctl start karlancer-bot

# فعال کردن در startup
sudo systemctl enable karlancer-bot

# بررسی وضعیت
sudo systemctl status karlancer-bot

# مشاهده لاگ
sudo journalctl -u karlancer-bot -f
```

### ۳. کنترل

```bash
# توقف
sudo systemctl stop karlancer-bot

# ری‌استارت
sudo systemctl restart karlancer-bot

# غیرفعال کردن
sudo systemctl disable karlancer-bot
```

## FAQ

### چرا ارسال خودکار غیرفعال است؟

برای امنیت! شما باید اول proposal ها را بررسی کنید قبل از ارسال. در نسخه‌های بعدی این قابلیت اضافه می‌شود.

### چگونه فاصله زمانی مناسب را انتخاب کنم؟

- **سریع (1-2 دقیقه):** برای رقابتی‌ترین پروژه‌ها
- **متوسط (5 دقیقه):** توصیه می‌شود - تعادل بین سرعت و منابع
- **آهسته (10-30 دقیقه):** برای صرفه‌جویی در منابع

### چگونه ربات را متوقف کنم؟

- **Foreground:** کلید `Ctrl+C`
- **Background (nohup):** `kill $(cat bot.pid)`
- **Systemd:** `sudo systemctl stop karlancer-bot`

### فایل لاگ بزرگ شده، چه کنم؟

```bash
# پاک کردن لاگ
> continuous_bot.log

# یا استفاده از logrotate (توصیه می‌شود)
```

### چگونه می‌توانم فقط پروژه‌های خاصی را فیلتر کنم؟

فعلاً این قابلیت نیست، اما می‌توانید کد را تغییر دهید. در آینده پارامتر filter اضافه می‌شود.

### چگونه می‌توانم چند کلمه کلیدی را جستجو کنم؟

فعلاً فقط "python" جستجو می‌شود. برای تغییر، خط زیر در کد را ویرایش کنید:

```python
# در متد process_new_projects()
all_projects = self.fetch_projects("python")  # تغییر دهید
```

## Troubleshooting

### مشکل: "Claude CLI not found"

```bash
# بررسی نصب
which claude

# اگر نصب نیست، از سایت رسمی دانلود کنید
```

### مشکل: "خطا در دریافت پروژه‌ها"

- اتصال اینترنت را بررسی کنید
- Bearer token را بررسی کنید (ممکن است منقضی شده باشد)
- API endpoint کارلنسر را چک کنید

### مشکل: "تحلیل ناموفق بود"

- لاگ را بررسی کنید: `cat continuous_bot.log`
- Claude CLI را تست کنید: `echo "test" | claude -`
- حافظه سیستم را چک کنید

### مشکل: "خروجی خیلی کوتاه"

- System prompt را بررسی کنید
- فایل پروژه را چک کنید که خالی نباشد
- تنظیمات Claude را بررسی کنید

## بهبودهای آینده

- [ ] ارسال خودکار proposal با تایید دو مرحله‌ای
- [ ] فیلتر هوشمند پروژه‌ها (بودجه، مهارت‌ها، ...)
- [ ] اعلان‌های Telegram/Email
- [ ] Dashboard وب برای نظارت
- [ ] Multi-keyword search
- [ ] Rate limiting هوشمند
- [ ] Retry logic با exponential backoff
- [ ] Health check endpoint

## نکات امنیتی

⚠️ **مهم:**
- Bearer token را در فایل environment قرار دهید، نه در کد
- لاگ‌ها را در مکان امن نگه دارید
- دسترسی فایل‌ها را محدود کنید: `chmod 600 *.py`
- از VPN استفاده کنید اگر در سرور خارجی اجرا می‌کنید

## پشتیبانی

اگر مشکلی داشتید:

```bash
# جمع‌آوری اطلاعات debug
python3 continuous_karlancer.py --once > debug_output.txt 2>&1
cat continuous_bot.log > debug_log.txt
cat continuous_tracking.json > debug_tracking.txt

# فایل‌های بالا را بررسی کنید
```

---

**خلاصه:** یک بار `bash run_continuous_bot.sh` رو اجرا کنید و ربات شروع به کار می‌کند! 🚀
