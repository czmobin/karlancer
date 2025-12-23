#!/bin/bash
# debug_analyzer.sh
# اسکریپت عیب‌یابی برای analyzer

export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8

echo "🔍 Karelancer Analyzer Debugger"
echo "================================================================================"
echo

# رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

check_pass() {
    echo -e "${GREEN}✅ $1${NC}"
}

check_fail() {
    echo -e "${RED}❌ $1${NC}"
}

check_warn() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

# ۱. بررسی encoding و locale
echo "1️⃣  Encoding & Locale:"
echo "  LANG=$LANG"
echo "  LC_ALL=$LC_ALL"
echo "  PYTHONIOENCODING=$PYTHONIOENCODING"

if [ "$LANG" = "C.UTF-8" ] || [ "$LANG" = "en_US.UTF-8" ]; then
    check_pass "Locale is UTF-8"
else
    check_warn "Locale might not be UTF-8"
fi
echo

# ۲. بررسی ابزارها
echo "2️⃣  Required Tools:"

if command -v python3 &> /dev/null; then
    PYTHON_VER=$(python3 --version)
    check_pass "Python3: $PYTHON_VER"
else
    check_fail "Python3 not found"
fi

if command -v jq &> /dev/null; then
    JQ_VER=$(jq --version)
    check_pass "jq: $JQ_VER"
else
    check_fail "jq not found (install: sudo apt-get install jq)"
fi

if command -v claude &> /dev/null; then
    CLAUDE_PATH=$(which claude)
    check_pass "Claude CLI: $CLAUDE_PATH"

    # تست Claude
    echo "  Testing Claude CLI..."
    if echo "سلام - این یک تست است" | claude - 2>&1 | head -5; then
        check_pass "Claude CLI is working"
    else
        check_fail "Claude CLI test failed"
    fi
else
    check_fail "Claude CLI not found"
fi
echo

# ۳. بررسی فایل‌ها
echo "3️⃣  Required Files:"

if [ -f "karelancer_prompt.txt" ]; then
    SIZE=$(stat -f%z "karelancer_prompt.txt" 2>/dev/null || stat -c%s "karelancer_prompt.txt")
    check_pass "karelancer_prompt.txt ($SIZE bytes)"

    # چک encoding
    if file "karelancer_prompt.txt" | grep -q "UTF-8"; then
        check_pass "Prompt file is UTF-8"
    else
        check_warn "Prompt file encoding might not be UTF-8"
    fi
else
    check_fail "karelancer_prompt.txt not found"
fi

if [ -f "project_fetcher.py" ]; then
    check_pass "project_fetcher.py exists"
else
    check_fail "project_fetcher.py not found"
fi

if [ -f "submit_proposal.py" ]; then
    check_pass "submit_proposal.py exists"
else
    check_warn "submit_proposal.py not found (optional)"
fi
echo

# ۴. بررسی پوشه‌ها
echo "4️⃣  Directories:"

if [ -d "claude_input" ]; then
    COUNT=$(find claude_input -name "project_*.txt" -type f 2>/dev/null | wc -l)
    check_pass "claude_input/ ($COUNT project files)"

    if [ $COUNT -eq 0 ]; then
        check_warn "No project files in claude_input/"
        echo "       Run: python3 project_fetcher.py"
    else
        # نمایش نمونه
        echo "       Sample files:"
        find claude_input -name "project_*.txt" -type f | head -3 | while read f; do
            echo "         - $(basename "$f")"
        done
    fi
else
    check_fail "claude_input/ directory not found"
    echo "       Creating claude_input/..."
    mkdir -p claude_input
fi

if [ -d "proposals" ]; then
    COUNT=$(find proposals -name "*.txt" -type f 2>/dev/null | wc -l)
    check_pass "proposals/ ($COUNT analysis files)"
else
    check_warn "proposals/ not found (will be created)"
    mkdir -p proposals
fi

if [ -d "new_projects" ]; then
    COUNT=$(find new_projects -name "*.json" -type f 2>/dev/null | wc -l)
    check_pass "new_projects/ ($COUNT JSON files)"
else
    check_warn "new_projects/ not found (will be created when fetching)"
fi
echo

# ۵. بررسی tracking
echo "5️⃣  Tracking:"

if [ -f "analyzed_projects.json" ]; then
    if command -v jq &> /dev/null; then
        ANALYZED_COUNT=$(jq 'length' "analyzed_projects.json" 2>/dev/null || echo 0)
        check_pass "analyzed_projects.json ($ANALYZED_COUNT analyzed)"

        if [ $ANALYZED_COUNT -gt 0 ]; then
            echo "       Recent analyses:"
            jq -r 'to_entries | sort_by(.value.analyzed_at) | reverse | limit(3;.[]) | "         - ID: \(.key) at \(.value.analyzed_at)"' \
                "analyzed_projects.json" 2>/dev/null || echo "         (cannot parse)"
        fi
    else
        check_warn "analyzed_projects.json exists but jq not available"
    fi
else
    check_warn "analyzed_projects.json not found (will be created)"
fi
echo

# ۶. تست خواندن یک فایل نمونه
echo "6️⃣  Sample File Test:"

SAMPLE=$(find claude_input -name "project_*.txt" -type f 2>/dev/null | head -1)

if [ -n "$SAMPLE" ]; then
    echo "  Testing: $(basename "$SAMPLE")"

    # چک encoding
    if file "$SAMPLE" | grep -q "UTF-8"; then
        check_pass "File is UTF-8 encoded"
    else
        check_warn "File encoding might not be UTF-8: $(file "$SAMPLE")"
    fi

    # خواندن محتوا
    if CONTENT=$(cat "$SAMPLE"); then
        LENGTH=${#CONTENT}
        check_pass "File is readable ($LENGTH chars)"

        # نمایش اولین خطوط
        echo "       First 3 lines:"
        head -3 "$SAMPLE" | while read line; do
            echo "         $line"
        done

        # چک فارسی
        if echo "$CONTENT" | grep -q "[\u0600-\u06FF]"; then
            check_pass "Contains Persian text"
        else
            check_warn "No Persian text detected"
        fi
    else
        check_fail "Cannot read file"
    fi
else
    check_warn "No sample file to test"
fi
echo

# ۷. خلاصه و توصیه‌ها
echo "================================================================================"
echo "📋 Summary:"
echo

# شمارش مشکلات
ERRORS=0
WARNINGS=0

# چک ابزارها
command -v python3 &> /dev/null || ((ERRORS++))
command -v claude &> /dev/null || ((ERRORS++))
command -v jq &> /dev/null || ((ERRORS++))

# چک فایل‌ها
[ -f "karelancer_prompt.txt" ] || ((ERRORS++))
[ -d "claude_input" ] || ((ERRORS++))

# چک پروژه‌ها
PROJECT_COUNT=$(find claude_input -name "project_*.txt" -type f 2>/dev/null | wc -l)
if [ $PROJECT_COUNT -eq 0 ]; then
    ((WARNINGS++))
fi

if [ $ERRORS -eq 0 ]; then
    echo -e "${GREEN}✅ All critical checks passed!${NC}"
else
    echo -e "${RED}❌ Found $ERRORS critical issue(s)${NC}"
fi

if [ $WARNINGS -gt 0 ]; then
    echo -e "${YELLOW}⚠️  Found $WARNINGS warning(s)${NC}"
fi

echo
echo "📝 Next Steps:"
echo

if [ $PROJECT_COUNT -eq 0 ]; then
    echo "1. Fetch projects:"
    echo "   python3 project_fetcher.py"
    echo
fi

echo "2. Analyze projects:"
echo "   bash analyze_fixed.sh"
echo
echo "   Or with debug mode:"
echo "   DEBUG=1 bash analyze_fixed.sh"
echo

echo "================================================================================"
echo "✅ Debug complete!"
