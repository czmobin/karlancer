#!/bin/bash
# analyze.sh - نسخه بهبود یافته با پشتیبانی کامل از UTF-8
# تحلیل پروژه‌های کارلنسر با Claude

# تنظیمات encoding برای لینوکس
export LANG=C.UTF-8
export LC_ALL=C.UTF-8
export PYTHONIOENCODING=utf-8

set -euo pipefail

# رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m'

# فایل‌ها و پوشه‌ها
PROMPT_FILE="karelancer_prompt.txt"
TRACKING_FILE="analyzed_projects.json"
INPUT_DIR="claude_input"
OUTPUT_DIR="proposals"
LOG_FILE="analyzer.log"

# Debug mode (uncomment برای فعال‌سازی)
# DEBUG=1

log_debug() {
    if [ "${DEBUG:-0}" = "1" ]; then
        echo -e "${GRAY}[DEBUG] $1${NC}" | tee -a "$LOG_FILE"
    fi
}

log_error() {
    echo -e "${RED}❌ $1${NC}" | tee -a "$LOG_FILE"
}

log_success() {
    echo -e "${GREEN}✅ $1${NC}" | tee -a "$LOG_FILE"
}

log_info() {
    echo -e "${CYAN}ℹ️  $1${NC}" | tee -a "$LOG_FILE"
}

log_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}" | tee -a "$LOG_FILE"
}

# شروع
echo "🤖 Karelancer Analyzer"
echo "================================================================================"
echo "$(date '+%Y-%m-%d %H:%M:%S')" > "$LOG_FILE"

# بررسی نصب بودن jq
if ! command -v jq &> /dev/null; then
    log_warning "jq is not installed. Installing..."
    if command -v apt-get &> /dev/null; then
        sudo apt-get update && sudo apt-get install -y jq
    elif command -v yum &> /dev/null; then
        sudo yum install -y jq
    else
        log_error "Cannot install jq. Please install it manually."
        exit 1
    fi
fi

# بررسی Claude CLI
if ! command -v claude &> /dev/null; then
    log_error "Claude CLI not found. Please install it first."
    log_info "Visit: https://claude.ai/download"
    exit 1
fi

log_debug "Claude CLI: $(which claude)"

# چک فایل prompt
if [ ! -f "$PROMPT_FILE" ]; then
    log_error "$PROMPT_FILE not found"
    exit 1
fi

log_debug "Prompt file: $PROMPT_FILE"

# چک پوشه input
if [ ! -d "$INPUT_DIR" ]; then
    log_error "$INPUT_DIR directory not found"
    log_info "Run: python3 project_fetcher.py to fetch projects first"
    exit 1
fi

# ساخت پوشه output
mkdir -p "$OUTPUT_DIR"

# بارگذاری tracking
declare -A ANALYZED
ANALYZED_LIST=""

if [ -f "$TRACKING_FILE" ]; then
    log_debug "Loading tracking from $TRACKING_FILE"
    ANALYZED_LIST=$(jq -r 'keys[]' "$TRACKING_FILE" 2>/dev/null || echo "")
    log_debug "Found $(echo "$ANALYZED_LIST" | grep -c . || echo 0) analyzed projects"
else
    log_debug "No tracking file found, starting fresh"
    echo "{}" > "$TRACKING_FILE"
fi

# خواندن System Prompt
SYSTEM_PROMPT=$(cat "$PROMPT_FILE")
log_debug "System prompt loaded (${#SYSTEM_PROMPT} chars)"

# دریافت پروژه‌ها
PROJECT_FILES=$(find "$INPUT_DIR" -name "project_*.txt" -type f | sort -r)

if [ -z "$PROJECT_FILES" ]; then
    log_error "No project files found in $INPUT_DIR"
    log_info "Run: python3 project_fetcher.py to fetch projects first"
    exit 1
fi

# شمارش
TOTAL=$(echo "$PROJECT_FILES" | wc -l)
ANALYZED_COUNT=$(echo "$ANALYZED_LIST" | grep -c . || echo 0)

echo -e "${NC}📂 Total projects: $TOTAL${NC}"
echo -e "${GREEN}✅ Already analyzed: $ANALYZED_COUNT${NC}"

# فیلتر پروژه‌های جدید
NEW_PROJECTS=()
while IFS= read -r file; do
    [ -z "$file" ] && continue

    # استخراج Project ID
    if [[ $(basename "$file") =~ project_([0-9]+) ]]; then
        PROJECT_ID="${BASH_REMATCH[1]}"

        # چک کن تحلیل شده یا نه
        if ! echo "$ANALYZED_LIST" | grep -q "^$PROJECT_ID$"; then
            NEW_PROJECTS+=("$file")
        fi
    fi
done <<< "$PROJECT_FILES"

NEW_COUNT=${#NEW_PROJECTS[@]}

echo -e "${YELLOW}🆕 New to analyze: $NEW_COUNT${NC}"
echo ""

if [ "$NEW_COUNT" -eq 0 ]; then
    log_success "All projects already analyzed!"
    exit 0
fi

# تحلیل
COUNT=0
SUCCESSFUL=0
FAILED=0

for file in "${NEW_PROJECTS[@]}"; do
    COUNT=$((COUNT + 1))

    # استخراج Project ID
    if [[ $(basename "$file") =~ project_([0-9]+) ]]; then
        PROJECT_ID="${BASH_REMATCH[1]}"
    else
        log_warning "Cannot extract ID from: $file"
        continue
    fi

    echo "================================================================================"
    echo -e "${YELLOW}[$COUNT/$NEW_COUNT] 📋 ID: $PROJECT_ID${NC}"
    echo "File: $(basename "$file")"
    log_debug "Processing: $file"

    # بررسی فایل خوانا باشد
    if [ ! -r "$file" ]; then
        log_error "Cannot read file: $file"
        FAILED=$((FAILED + 1))
        continue
    fi

    # خواندن پروژه با UTF-8
    if ! PROJECT_TEXT=$(cat "$file"); then
        log_error "Failed to read project file"
        FAILED=$((FAILED + 1))
        continue
    fi

    log_debug "Project text loaded (${#PROJECT_TEXT} chars)"

    # ترکیب prompt و پروژه
    COMBINED="$SYSTEM_PROMPT

================================================================================

این پروژه جدید از کارلنسر اومده:

$PROJECT_TEXT"

    # فایل موقت با encoding صحیح
    TEMP_FILE="temp_${PROJECT_ID}.txt"
    echo "$COMBINED" > "$TEMP_FILE"

    log_debug "Temp file created: $TEMP_FILE ($(stat -f%z "$TEMP_FILE" 2>/dev/null || stat -c%s "$TEMP_FILE") bytes)"

    echo -e "${CYAN}⏳ Analyzing with Claude...${NC}"

    # اجرای Claude با timeout و error handling
    START_TIME=$(date +%s)

    # اجرای Claude و ذخیره خروجی
    if timeout 300 claude "$TEMP_FILE" > "output_${PROJECT_ID}.tmp" 2>&1; then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))

        # خواندن خروجی
        OUTPUT=$(cat "output_${PROJECT_ID}.tmp")

        # فیلتر noise و پیام‌های اضافی
        CLEAN_OUTPUT=$(echo "$OUTPUT" | \
            grep -v -E "trust|folder|security|Enter to|Do you trust|^─+$|^\s*$" | \
            grep -v "^$" || echo "$OUTPUT")

        OUTPUT_LENGTH=${#CLEAN_OUTPUT}
        log_debug "Claude output: $OUTPUT_LENGTH chars (cleaned)"

        # چک موفقیت - خروجی باید حداقل 200 کاراکتر باشد
        if [ "$OUTPUT_LENGTH" -gt 200 ]; then
            # ذخیره
            OUT_FILE="$OUTPUT_DIR/project_${PROJECT_ID}_analysis.txt"

            cat > "$OUT_FILE" << EOF
Project ID: $PROJECT_ID
File: $(basename "$file")
تاریخ: $(date '+%Y-%m-%d %H:%M:%S')
مدت تحلیل: ${DURATION}s
================================================================================

$CLEAN_OUTPUT
EOF

            log_success "Analysis completed"
            echo -e "${GREEN}💾 Saved: $OUT_FILE${NC}"
            echo -e "${GRAY}⏱️  Duration: ${DURATION}s${NC}"
            echo -e "${GRAY}📏 Length: $OUTPUT_LENGTH chars${NC}"

            # به‌روزرسانی tracking
            TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')

            # خواندن tracking فعلی
            CURRENT=$(cat "$TRACKING_FILE")

            # اضافه کردن رکورد جدید
            echo "$CURRENT" | jq --arg id "$PROJECT_ID" \
                --arg file "$(basename "$file")" \
                --arg time "$TIMESTAMP" \
                --arg dur "$DURATION" \
                --arg out "$OUT_FILE" \
                '. + {($id): {filename: $file, analyzed_at: $time, duration: ($dur|tonumber), output_file: $out}}' \
                > "${TRACKING_FILE}.tmp"

            mv "${TRACKING_FILE}.tmp" "$TRACKING_FILE"

            SUCCESSFUL=$((SUCCESSFUL + 1))
        else
            log_warning "Analysis failed - output too short ($OUTPUT_LENGTH chars)"
            log_debug "Output: ${CLEAN_OUTPUT:0:200}..."
            FAILED=$((FAILED + 1))
        fi
    else
        EXIT_CODE=$?
        log_error "Claude command failed (exit code: $EXIT_CODE)"

        if [ -f "output_${PROJECT_ID}.tmp" ]; then
            ERROR_MSG=$(cat "output_${PROJECT_ID}.tmp" | head -20)
            log_debug "Error output: $ERROR_MSG"
        fi

        FAILED=$((FAILED + 1))
    fi

    # حذف temp files
    rm -f "$TEMP_FILE" "output_${PROJECT_ID}.tmp"

    echo ""

    # وقفه بین درخواست‌ها
    if [ $COUNT -lt $NEW_COUNT ]; then
        log_debug "Waiting 2 seconds before next request..."
        sleep 2
    fi
done

echo "================================================================================"
log_success "Successfully analyzed: $SUCCESSFUL / $NEW_COUNT"
if [ $FAILED -gt 0 ]; then
    log_warning "Failed: $FAILED / $NEW_COUNT"
fi
echo -e "${GRAY}💾 Tracking: $TRACKING_FILE${NC}"
echo -e "${CYAN}📁 Results: $OUTPUT_DIR${NC}"
echo -e "${GRAY}📋 Log: $LOG_FILE${NC}"
echo -e "${GREEN}🎉 Done!${NC}"
