#!/bin/bash
# run_continuous_bot.sh
# اجرای ربات مداوم کارلنسر

# تنظیمات encoding
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8

# رنگ‌ها
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

echo -e "${GREEN}🤖 Continuous Karlancer Bot${NC}"
echo "================================================================================"
echo

# پارامترها
INTERVAL=${1:-300}  # پیش‌فرض 5 دقیقه
MODE=${2:-continuous}  # continuous یا once

# نمایش تنظیمات
echo -e "${CYAN}⚙️  تنظیمات:${NC}"
echo "  - فاصله بررسی: $INTERVAL ثانیه ($((INTERVAL / 60)) دقیقه)"
echo "  - حالت: $MODE"
echo

# بررسی Python
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}❌ Python3 یافت نشد${NC}"
    exit 1
fi

# بررسی Claude CLI
if ! command -v claude &> /dev/null; then
    echo -e "${RED}❌ Claude CLI یافت نشد${NC}"
    echo "  نصب: https://claude.ai/download"
    exit 1
fi

# بررسی فایل prompt
if [ ! -f "karelancer_prompt.txt" ]; then
    echo -e "${RED}❌ karelancer_prompt.txt یافت نشد${NC}"
    exit 1
fi

echo -e "${GREEN}✅ همه چیز آماده است${NC}"
echo "================================================================================"
echo

# اجرا
if [ "$MODE" = "once" ]; then
    echo -e "${YELLOW}🔍 اجرای یک‌باره...${NC}"
    python3 continuous_karlancer.py --interval "$INTERVAL" --once
else
    echo -e "${YELLOW}🔄 شروع حالت مداوم...${NC}"
    echo -e "${CYAN}💡 برای توقف: Ctrl+C${NC}"
    echo
    python3 continuous_karlancer.py --interval "$INTERVAL"
fi
