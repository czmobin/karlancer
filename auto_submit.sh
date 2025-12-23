#!/bin/bash
# auto_submit.sh
# تحلیل + ارسال خودکار proposal

set -e

echo "🤖 Karelancer Auto-Submitter"
echo "================================================================================"

# Step 1: دریافت پروژه‌ها
echo "📥 Step 1: Fetching projects..."
python3 fetch_projects.py
echo ""

# Step 2: تحلیل
echo "🧠 Step 2: Analyzing..."
./analyze.sh
echo ""

# Step 3: ارسال (اختیاری)
echo "📤 Step 3: Submitting proposals..."

# پیدا کردن تحلیل‌های جدید
NEW_ANALYSES=$(find proposals -name "*_analysis.txt" -mmin -10 | sort)

if [ -z "$NEW_ANALYSES" ]; then
    echo "No new analyses found"
    exit 0
fi

COUNT=$(echo "$NEW_ANALYSES" | wc -l)
echo "Found $COUNT new analysis/analyses"
echo ""

# ارسال هر کدام
for analysis in $NEW_ANALYSES; do
    echo "================================================================================	"
    echo "📋 $(basename "$analysis")"
    echo "================================================================================"
    
    # نمایش preview
    echo "Preview:"
    head -n 20 "$analysis"
    echo "..."
    echo ""
    
    # سوال تأیید
    read -p "Submit this proposal? (y/N/s=skip all): " CONFIRM
    
    case "$CONFIRM" in
        y|Y)
            echo "📤 Submitting..."
            python3 submit_proposal.py "$analysis"
            echo ""
            ;;
        s|S)
            echo "⏭️  Skipping all remaining"
            break
            ;;
        *)
            echo "⏭️  Skipped"
            echo ""
            ;;
    esac
    
    sleep 1
done

echo ""
echo "✅ All done!"