#!/bin/bash
# run_continuous.sh
# اجرای مداوم

INTERVAL=${1:-60}  # پیش‌فرض 60 ثانیه

echo "🔄 Continuous mode (every ${INTERVAL}s)"
echo "Press Ctrl+C to stop"
echo ""

while true; do
    echo "[$(date '+%H:%M:%S')] 🔍 Checking for new projects..."
    
    # دریافت
    python3 fetch_projects.py
    
    # تحلیل
    ./analyze.sh
    
    echo ""
    echo "[$(date '+%H:%M:%S')] ⏱️  Sleeping for ${INTERVAL}s..."
    echo ""
    
    sleep "$INTERVAL"
done