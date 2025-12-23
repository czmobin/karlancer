#!/bin/bash
# اسکریپت راه‌انداز برای project_fetcher.py در لینوکس
# این اسکریپت تمام تنظیمات لازم برای نمایش صحیح فارسی را انجام می‌دهد

set -e

echo "=================================="
echo "تنظیم محیط برای اجرای در لینوکس..."
echo "=================================="
echo

# تنظیم متغیرهای محیطی برای UTF-8
export PYTHONIOENCODING=utf-8
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONUNBUFFERED=1

# بررسی نصب بودن Python 3
if ! command -v python3 &> /dev/null; then
    echo "❌ خطا: Python 3 نصب نیست"
    exit 1
fi

# بررسی نصب بودن pip
if ! command -v pip3 &> /dev/null; then
    echo "⚠️  pip3 نصب نیست. در حال نصب..."
    sudo apt-get update && sudo apt-get install -y python3-pip
fi

# بررسی و نصب کتابخانه‌های لازم
echo "📦 بررسی کتابخانه‌های لازم..."

python3 -c "import requests" 2>/dev/null || {
    echo "📥 نصب requests..."
    pip3 install requests
}

echo "✅ تمام کتابخانه‌ها نصب هستند"
echo

# اجرای برنامه
echo "🚀 اجرای project_fetcher.py..."
echo

python3 project_fetcher.py

echo
echo "✅ اجرا با موفقیت به پایان رسید"
