#!/bin/bash
# analyze.sh
# تحلیل پروژه‌های کارلنسر با Claude - Linux

set -e

echo "🤖 Karelancer Analyzer"
echo "================================================================================"

# رنگ‌ها
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
GRAY='\033[0;37m'
NC='\033[0m' # No Color

# فایل‌ها
PROMPT_FILE="karelancer_prompt.txt"
TRACKING_FILE="analyzed_projects.json"
INPUT_DIR="claude_input"
OUTPUT_DIR="proposals"

# چک فایل prompt
if [ ! -f "$PROMPT_FILE" ]; then
    echo -e "${RED}❌ $PROMPT_FILE not found${NC}"
    exit 1
fi

# چک پوشه input
if [ ! -d "$INPUT_DIR" ]; then
    echo -e "${RED}❌ $INPUT_DIR directory not found${NC}"
    echo -e "${YELLOW}Run: python3 fetch_projects.py${NC}"
    exit 1
fi

# ساخت پوشه output
mkdir -p "$OUTPUT_DIR"

# بارگذاری tracking
declare -A ANALYZED
if [ -f "$TRACKING_FILE" ]; then
    echo -e "${GRAY}📋 Loading tracking...${NC}"
    # خواندن project IDs که تحلیل شده‌اند
    if command -v jq &> /dev/null; then
        ANALYZED_LIST=$(jq -r 'keys[]' "$TRACKING_FILE" 2>/dev/null || echo "")
    else
        ANALYZED_LIST=""
    fi
else
    ANALYZED_LIST=""
fi

# خواندن System Prompt
SYSTEM_PROMPT=$(cat "$PROMPT_FILE")

# دریافت پروژه‌ها
PROJECT_FILES=$(find "$INPUT_DIR" -name "*.txt" -type f | sort -r)

if [ -z "$PROJECT_FILES" ]; then
    echo -e "${RED}❌ No projects found${NC}"
    exit 1
fi

# شمارش
TOTAL=$(echo "$PROJECT_FILES" | wc -l)
ANALYZED_COUNT=$(echo "$ANALYZED_LIST" | grep -c . || echo 0)

echo -e "${NC}📂 Total projects: $TOTAL${NC}"
echo -e "${GREEN}✅ Already analyzed: $ANALYZED_COUNT${NC}"

# فیلتر پروژه‌های جدید
NEW_PROJECTS=""
for file in $PROJECT_FILES; do
    # استخراج Project ID
    if [[ $(basename "$file") =~ project_([0-9]+) ]]; then
        PROJECT_ID="${BASH_REMATCH[1]}"
        
        # چک کن تحلیل شده یا نه
        if ! echo "$ANALYZED_LIST" | grep -q "^$PROJECT_ID$"; then
            NEW_PROJECTS="$NEW_PROJECTS$file\n"
        fi
    fi
done

NEW_COUNT=$(echo -e "$NEW_PROJECTS" | grep -c . || echo 0)

echo -e "${YELLOW}🆕 New to analyze: $NEW_COUNT${NC}"
echo ""

if [ "$NEW_COUNT" -eq 0 ]; then
    echo -e "${GREEN}✨ All projects already analyzed!${NC}"
    exit 0
fi

# تحلیل
COUNT=0
SUCCESSFUL=0

echo -e "$NEW_PROJECTS" | while IFS= read -r file; do
    [ -z "$file" ] && continue
    
    COUNT=$((COUNT + 1))
    
    # استخراج Project ID
    if [[ $(basename "$file") =~ project_([0-9]+) ]]; then
        PROJECT_ID="${BASH_REMATCH[1]}"
    else
        continue
    fi
    
    echo "================================================================================"
    echo -e "${YELLOW}[$COUNT/$NEW_COUNT] 📋 ID: $PROJECT_ID${NC}"
    echo "File: $(basename "$file")"
    echo "================================================================================"
    
    # خواندن پروژه
    PROJECT_TEXT=$(cat "$file")
    
    # ترکیب
    COMBINED="$SYSTEM_PROMPT

================================================================================

این پروژه جدید از کارلنسر اومده:

$PROJECT_TEXT"
    
    # فایل موقت
    TEMP_FILE="temp_${PROJECT_ID}.txt"
    echo "$COMBINED" > "$TEMP_FILE"
    
    echo -e "${CYAN}⏳ Analyzing with Claude...${NC}"
    echo ""
    
    # اجرای Claude
    START_TIME=$(date +%s)
    
    if OUTPUT=$(claude "$TEMP_FILE" 2>&1); then
        END_TIME=$(date +%s)
        DURATION=$((END_TIME - START_TIME))
        
        # فیلتر noise
        CLEAN_OUTPUT=$(echo "$OUTPUT" | grep -v -E "trust|folder|security|────|Enter to|Do you trust" || echo "$OUTPUT")
        
        # چک موفقیت
        if [ ${#CLEAN_OUTPUT} -gt 200 ]; then
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
            
            echo "$CLEAN_OUTPUT"
            echo ""
            echo -e "${GREEN}💾 Saved: $OUT_FILE${NC}"
            echo -e "${GRAY}⏱️  Duration: ${DURATION}s${NC}"
            
            # به‌روزرسانی tracking
            if command -v jq &> /dev/null; then
                TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
                
                # خواندن tracking فعلی
                if [ -f "$TRACKING_FILE" ]; then
                    CURRENT=$(cat "$TRACKING_FILE")
                else
                    CURRENT="{}"
                fi
                
                # اضافه کردن رکورد جدید
                echo "$CURRENT" | jq --arg id "$PROJECT_ID" \
                    --arg file "$(basename "$file")" \
                    --arg time "$TIMESTAMP" \
                    --arg dur "$DURATION" \
                    --arg out "$OUT_FILE" \
                    '. + {($id): {filename: $file, analyzed_at: $time, duration: ($dur|tonumber), output_file: $out}}' \
                    > "$TRACKING_FILE"
            fi
            
            SUCCESSFUL=$((SUCCESSFUL + 1))
        else
            echo -e "${YELLOW}⚠️  Analysis failed (output too short)${NC}"
        fi
    else
        echo -e "${RED}❌ Claude error${NC}"
    fi
    
    # حذف temp
    rm -f "$TEMP_FILE"
    
    echo ""
    sleep 2
done

echo "================================================================================"
echo -e "${GREEN}✅ Successfully analyzed: $SUCCESSFUL / $NEW_COUNT${NC}"
echo -e "${GRAY}💾 Tracking: $TRACKING_FILE${NC}"
echo -e "${CYAN}📁 Results: $OUTPUT_DIR${NC}"
echo -e "${GREEN}🎉 Done!${NC}"