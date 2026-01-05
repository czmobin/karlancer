#!/bin/bash
# راه‌اندازی سریع Telegram Logger

BOT_TOKEN="8479753307:AAEOOUbyv6Jun5fZKb73dpKEsMLL8xAUub4"
BOT_USERNAME="karlancerr_bot"

echo "════════════════════════════════════════════════════════════════"
echo "📱 راه‌اندازی Telegram Logger برای ربات کارلنسر"
echo "════════════════════════════════════════════════════════════════"
echo ""
echo "📝 مراحل:"
echo "  1. به این لینک برو و /start رو بزن:"
echo "     https://t.me/$BOT_USERNAME"
echo ""
echo "  2. یک پیام دلخواه بفرست (مثلا: سلام)"
echo ""
echo "  3. وقتی پیام رو فرستادی، Enter رو بزن..."
echo ""
read -p "⏸️  آماده‌ای؟ [Enter] " dummy

echo ""
echo "🔍 در حال دریافت Chat ID..."
echo ""

# دریافت updates از بات
RESPONSE=$(curl -s "https://api.telegram.org/bot$BOT_TOKEN/getUpdates")

# استخراج Chat ID
CHAT_ID=$(echo $RESPONSE | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    if data.get('ok') and data.get('result'):
        updates = data['result']
        if updates:
            chat_id = updates[-1]['message']['chat']['id']
            print(chat_id)
        else:
            print('NO_MESSAGES')
    else:
        print('ERROR')
except:
    print('ERROR')
")

if [ "$CHAT_ID" = "NO_MESSAGES" ]; then
    echo "❌ هیچ پیامی پیدا نشد!"
    echo "   لطفا به بات برو، /start رو بزن و یک پیام بفرست"
    echo "   بعد دوباره این اسکریپت رو اجرا کن"
    exit 1
elif [ "$CHAT_ID" = "ERROR" ]; then
    echo "❌ خطا در دریافت اطلاعات از بات"
    exit 1
elif [ -z "$CHAT_ID" ]; then
    echo "❌ نمی‌تونم Chat ID رو پیدا کنم"
    echo "   لطفا دستی از این لینک بگیر:"
    echo "   https://api.telegram.org/bot$BOT_TOKEN/getUpdates"
    exit 1
else
    echo "✅ Chat ID پیدا شد: $CHAT_ID"
    echo ""

    # ذخیره در فایل
    echo "$CHAT_ID" > .telegram_chat_id
    echo "💾 Chat ID در فایل .telegram_chat_id ذخیره شد"
    echo ""

    # تست ارسال پیام
    echo "🧪 تست ارسال پیام..."

    TEST_MESSAGE="🧪 تست اتصال موفق!

✅ ربات کارلنسر آماده است
📱 Chat ID: $CHAT_ID

الان میتونی ربات رو اجرا کنی:
python3 continuous_karlancer.py --auto-submit --min-stars 2"

    curl -s -X POST "https://api.telegram.org/bot$BOT_TOKEN/sendMessage" \
        -d "chat_id=$CHAT_ID" \
        -d "text=$TEST_MESSAGE" \
        -d "parse_mode=HTML" > /dev/null

    echo ""
    echo "════════════════════════════════════════════════════════════════"
    echo "✅ راه‌اندازی موفق!"
    echo "════════════════════════════════════════════════════════════════"
    echo ""
    echo "📱 یک پیام تست به تلگرامت فرستادم - چک کن!"
    echo ""
    echo "🚀 حالا میتونی ربات رو اجرا کنی:"
    echo "   python3 continuous_karlancer.py --auto-submit --min-stars 2"
    echo ""
    echo "💡 از این به بعد، دیگه نیازی به --telegram-chat-id نیست!"
    echo "   Chat ID خودکار از فایل .telegram_chat_id خونده میشه"
    echo ""
fi
