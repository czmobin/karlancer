# 🤖 ربات کاملاً خودکار کارلنسر (Auto-Submit)

## ⚠️ هشدار مهم

این ربات **کاملاً خودکار** است و **بدون هیچ تاییدی** proposal ها را ارسال می‌کند!

```
✅ پروژه پیدا می‌کند
✅ تحلیل می‌کند
⚠️  خودکار ارسال می‌کند (بدون تایید!)
```

**مسئولیت استفاده کاملاً با شماست!**

## استفاده

### روش ۱: اجرای ساده (توصیه می‌شود برای تست)

```bash
# اجرا
bash auto_karlancer.sh

# سوال می‌کنه: آیا مطمئن هستید؟
# باید دقیقاً 'yes' تایپ کنید
```

خروجی:
```
⚠️  ⚠️  ⚠️  هشدار ⚠️  ⚠️  ⚠️
================================================================================
این ربات به صورت خودکار و بدون تایید:
  1. پروژه‌های جدید را پیدا می‌کند
  2. با Claude تحلیل می‌کند
  3. خودکار proposal را ارسال می‌کند (بدون تایید!)
  4. این کار را تا ابد ادامه می‌دهد

مسئولیت استفاده کاملاً با شماست!
================================================================================

⚙️  تنظیمات:
  - فاصله بررسی: 300 ثانیه (5 دقیقه)
  - حالت: continuous
  - ارسال خودکار: فعال ✅

آیا مطمئن هستید؟ (yes/NO): yes

✅ شروع ربات خودکار...
```

### روش ۲: با فاصله زمانی دلخواه

```bash
# هر 2 دقیقه (120 ثانیه)
bash auto_karlancer.sh 120

# هر 10 دقیقه (600 ثانیه)
bash auto_karlancer.sh 600
```

### روش ۳: فقط یک بار (تست)

```bash
bash auto_karlancer.sh 300 once
```

### روش ۴: اجرا در Background

```bash
# شروع در background
nohup bash auto_karlancer.sh 300 > auto_bot.log 2>&1 &

# ذخیره PID
echo $! > auto_bot.pid

# مشاهده لاگ
tail -f auto_bot.log
tail -f continuous_bot.log

# توقف
kill $(cat auto_bot.pid)
```

### روش ۵: استفاده مستقیم از Python

```bash
# حالت مداوم
python3 continuous_karlancer.py --auto-submit --interval 300

# فقط یک بار
python3 continuous_karlancer.py --auto-submit --once
```

## نمونه خروجی

```
🚀 ربات مداوم کارلنسر شروع شد
⏰ فاصله بررسی: 300 ثانیه (5 دقیقه)
📤 ارسال خودکار: فعال ✅  ← فعال!
================================================================================

🔄 چرخه #1 - 2024-12-23 20:00:00
ℹ️  جستجوی پروژه‌های جدید...
✅ 🆕 2 پروژه جدید پیدا شد!

================================================================================
ℹ️  [1/2] پروژه 257000: توسعه API با Django
================================================================================
ℹ️  تحلیل پروژه 257000 با Claude...
✅ تحلیل پروژه 257000 موفق (2456 chars)
ℹ️  📤 ارسال خودکار proposal برای پروژه 257000...
💰 بودجه milestone: 5,000,000 تومان
⏱️  مدت زمان: 10 روز
✅ ✅ پروژه 257000 با موفقیت ارسال شد!  ← ارسال شد!

================================================================================
ℹ️  [2/2] پروژه 257001: ربات تلگرام
================================================================================
ℹ️  تحلیل پروژه 257001 با Claude...
✅ تحلیل پروژه 257001 موفق (1890 chars)
ℹ️  📤 ارسال خودکار proposal برای پروژه 257001...
💰 بودجه milestone: 3,000,000 تومان
⏱️  مدت زمان: 7 روز
✅ ✅ پروژه 257001 با موفقیت ارسال شد!  ← ارسال شد!

✅ پردازش 2 پروژه تمام شد
ℹ️  📊 آمار کل: 2 دریافت، 2 تحلیل، 2 ارسال ✅، 0 خطا

😴 استراحت 300 ثانیه تا چرخه بعدی...

🔄 چرخه #2 - 2024-12-23 20:05:00
...
```

## Workflow

```
START
  ↓
Fetch new projects
  ↓
Found 2 new projects
  ↓
Project #1:
  → Save
  → Analyze with Claude
  → ⚠️  AUTO SUBMIT (no confirmation!)  ← خودکار!
  → ✅ Submitted
  ↓
Project #2:
  → Save
  → Analyze
  → ⚠️  AUTO SUBMIT
  → ✅ Submitted
  ↓
Wait 5 minutes...
  ↓
Loop forever
```

## فایل‌های خروجی

```
claude_input/              ← فایل‌های متنی پروژه‌ها
proposals/                 ← تحلیل‌های Claude
continuous_bot.log         ← لاگ کامل عملیات
continuous_tracking.json   ← آمار و tracking
```

### مثال continuous_tracking.json

```json
{
  "total_fetched": 50,
  "total_analyzed": 48,
  "total_submitted": 45,  ← تعداد ارسال‌های موفق
  "total_failed": 3,
  "projects": {
    "257000": {
      "title": "توسعه API",
      "fetched_at": "2024-12-23T20:00:15",
      "analyzed": true,
      "submitted": true,  ← ارسال شده!
      "analysis_file": "proposals/project_257000_analysis.txt"
    },
    ...
  }
}
```

## Systemd Service (اجرای دائمی)

برای اینکه ربات همیشه در حال کار باشد (حتی بعد از restart):

### ۱. ایجاد Service File

```bash
sudo nano /etc/systemd/system/auto-karlancer.service
```

محتوا:
```ini
[Unit]
Description=Karlancer Auto-Submit Bot
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/karlancer
Environment="PYTHONIOENCODING=utf-8"
Environment="LANG=C.UTF-8"
Environment="LC_ALL=C.UTF-8"
ExecStart=/usr/bin/python3 /root/karlancer/continuous_karlancer.py --auto-submit --interval 300
Restart=always
RestartSec=30
StandardOutput=append:/root/karlancer/auto_bot.log
StandardError=append:/root/karlancer/auto_bot.log

[Install]
WantedBy=multi-user.target
```

### ۲. فعال‌سازی

```bash
# reload systemd
sudo systemctl daemon-reload

# شروع
sudo systemctl start auto-karlancer

# فعال کردن در startup
sudo systemctl enable auto-karlancer

# بررسی وضعیت
sudo systemctl status auto-karlancer

# مشاهده لاگ
sudo journalctl -u auto-karlancer -f
# یا
tail -f /root/karlancer/auto_bot.log
```

### ۳. کنترل

```bash
# توقف
sudo systemctl stop auto-karlancer

# ری‌استارت
sudo systemctl restart auto-karlancer

# غیرفعال کردن
sudo systemctl disable auto-karlancer
```

## تنظیمات پیشرفته

### تغییر فاصله زمانی

```bash
# در service file:
ExecStart=... --interval 600  # هر 10 دقیقه

# یا در اجرای دستی:
bash auto_karlancer.sh 600
```

### غیرفعال کردن auto-submit موقت

```bash
# بدون --auto-submit
python3 continuous_karlancer.py --interval 300

# فقط تحلیل می‌کنه، ارسال نمی‌کنه
```

## Monitoring

### نظارت بر عملکرد

```bash
# لاگ زنده
tail -f continuous_bot.log

# آمار
cat continuous_tracking.json | jq

# تعداد proposal های ارسال شده
cat continuous_tracking.json | jq '.total_submitted'

# لیست پروژه‌های ارسال شده
cat continuous_tracking.json | jq '.projects | to_entries[] | select(.value.submitted == true) | .key'

# proposal های جدید
ls -lht proposals/ | head -10
```

### Dashboard ساده

```bash
# در یک terminal
watch -n 5 'echo "📊 آمار ربات:"; echo ""; cat continuous_tracking.json | jq "{fetched: .total_fetched, analyzed: .total_analyzed, submitted: .total_submitted, failed: .total_failed}"'
```

## توقف اضطراری

### روش ۱: اگر در foreground اجرا کردید

```bash
Ctrl+C
```

### روش ۲: اگر در background اجرا کردید

```bash
# پیدا کردن process
ps aux | grep continuous_karlancer

# kill کردن
kill <PID>

# یا اگر PID ذخیره کردید
kill $(cat auto_bot.pid)
```

### روش ۳: اگر با systemd اجرا کردید

```bash
sudo systemctl stop auto-karlancer
```

### روش ۴: Kill همه

```bash
pkill -f continuous_karlancer
```

## FAQ

### چگونه مطمئن شوم proposal ها ارسال می‌شوند؟

بررسی کنید:
1. لاگ: `tail -f continuous_bot.log` - باید "✅ پروژه XXX با موفقیت ارسال شد" ببینید
2. Tracking: `cat continuous_tracking.json | jq '.total_submitted'` - باید عدد افزایش پیدا کند
3. سایت کارلنسر: چک کنید proposal های ارسالی خودتان را

### چه اتفاقی می‌افتد اگر Claude خطا بدهد؟

ربات:
1. خطا را لاگ می‌کنه
2. اون پروژه رو skip می‌کنه
3. به پروژه بعدی می‌رهد
4. ادامه می‌ده (متوقف نمی‌شه)

### چه اتفاقی می‌افتد اگر submit fail بشه؟

ربات:
1. خطا را لاگ می‌کنه (با error message کامل)
2. پروژه رو به عنوان `submitted: false` علامت می‌زنه
3. ادامه می‌ده

### چگونه می‌توانم خاص proposal ها را ببینم؟

```bash
# لیست proposal ها
ls -lht proposals/

# خواندن یک proposal
cat proposals/project_257000_analysis.txt

# proposal های اخیر (10 تا)
find proposals/ -name "*.txt" -mmin -60 | head -10
```

### چطور می‌توانم فقط پروژه‌های خاصی را submit کنم؟

فعلاً این قابلیت نیست، اما می‌توانید:
1. بدون `--auto-submit` اجرا کنید
2. خودتان proposal ها را بررسی کنید
3. دستی با `submit_proposal.py` ارسال کنید

### آیا می‌توانم چند instance همزمان اجرا کنم؟

⚠️ **توصیه نمی‌شود!** چون:
- ممکنه duplicate proposal بفرسته
- cache conflict ایجاد بشه

اگر حتماً می‌خواید، از پوشه‌های جداگانه استفاده کنید.

### چقدر منابع (CPU/Memory) مصرف می‌کند?

معمولاً بسیار کم:
- CPU: < 5% (فقط موقع تحلیل با Claude)
- Memory: < 100MB
- Network: کم (فقط API calls)

### چطور می‌تونم اطمینان حاصل کنم که کار می‌کنه؟

```bash
# ۱. چک کردن process
ps aux | grep continuous_karlancer

# ۲. چک کردن لاگ
tail -f continuous_bot.log

# ۳. چک کردن tracking
cat continuous_tracking.json | jq

# ۴. چک کردن proposal های جدید
ls -lt proposals/ | head -5
```

## نکات امنیتی

### ⚠️ مهم

1. **Bearer Token**: در فایل محرمانه نگه دارید
2. **Log Files**: حاوی اطلاعات حساس هستند
3. **Proposals**: قبل از استفاده در production، تست کنید
4. **Rate Limiting**: فاصله کمتر از 2 دقیقه توصیه نمی‌شود

### توصیه‌ها

```bash
# محدود کردن دسترسی
chmod 600 continuous_karlancer.py
chmod 600 submit_proposal.py
chmod 600 continuous_bot.log

# استفاده از .env برای token
# (فعلاً پیاده‌سازی نشده)
```

## Troubleshooting

### ربات متوقف شد

```bash
# بررسی لاگ
tail -100 continuous_bot.log

# بررسی systemd
sudo systemctl status auto-karlancer
sudo journalctl -u auto-karlancer -n 100
```

### Proposal ها ارسال نمی‌شوند

```bash
# بررسی --auto-submit فعال باشد
ps aux | grep continuous_karlancer | grep auto-submit

# تست دستی
python3 submit_proposal.py proposals/project_XXX_analysis.txt
```

### خطای "Could not extract proposal"

یعنی Claude proposal ننوشته. بررسی کنید:
1. `karelancer_prompt.txt` درست باشد
2. Claude CLI کار کند
3. فایل analysis معتبر باشد

## خلاصه

**یک بار اجرا کنید و برید:**

```bash
# ساده‌ترین روش
bash auto_karlancer.sh

# یا برای دائمی
sudo systemctl start auto-karlancer
```

ربات به صورت خودکار و دائمی:
- پروژه‌های جدید را پیدا می‌کند ✅
- تحلیل می‌کند ✅
- **خودکار ارسال می‌کند ✅** (بدون تایید!)

---

⚠️ **یادتان باشد: مسئولیت استفاده کاملاً با شماست!**
