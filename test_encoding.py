#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
تست encoding و نمایش فارسی
"""

import sys
import json
from pathlib import Path

def test_basic_output():
    """تست خروجی ساده"""
    print("=" * 60)
    print("🧪 تست ۱: خروجی ساده فارسی")
    print("=" * 60)
    print()

    print("سلام! این یک متن فارسی است")
    print("✅ موفقیت‌آمیز")
    print("❌ خطا")
    print("💰 بودجه: ۱۰,۰۰۰,۰۰۰ تومان")
    print()

def test_file_write():
    """تست نوشتن فایل"""
    print("=" * 60)
    print("🧪 تست ۲: نوشتن فایل با فارسی")
    print("=" * 60)
    print()

    test_dir = Path("test_output")
    test_dir.mkdir(exist_ok=True)

    # تست JSON
    data = {
        "عنوان": "پروژه تست",
        "توضیحات": "این یک پروژه آزمایشی است",
        "بودجه": 5000000,
        "مهارت‌ها": ["Python", "Django", "فارسی"]
    }

    json_file = test_dir / "test.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"✅ فایل JSON ذخیره شد: {json_file}")

    # تست متن
    text = """عنوان: پروژه تست

توضیحات:
این یک متن طولانی با حروف فارسی است که باید
به درستی در فایل ذخیره شود.

بودجه: ۵,۰۰۰,۰۰۰ تومان
امتیاز: ⭐⭐⭐⭐⭐
"""

    txt_file = test_dir / "test.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(text)

    print(f"✅ فایل متنی ذخیره شد: {txt_file}")
    print()

def test_file_read():
    """تست خواندن فایل"""
    print("=" * 60)
    print("🧪 تست ۳: خواندن فایل")
    print("=" * 60)
    print()

    test_dir = Path("test_output")

    # خواندن JSON
    json_file = test_dir / "test.json"
    if json_file.exists():
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)

        print("📄 محتوای JSON:")
        print(json.dumps(data, ensure_ascii=False, indent=2))
        print()

    # خواندن متن
    txt_file = test_dir / "test.txt"
    if txt_file.exists():
        with open(txt_file, 'r', encoding='utf-8') as f:
            content = f.read()

        print("📄 محتوای فایل متنی:")
        print(content)
        print()

def test_system_info():
    """نمایش اطلاعات سیستم"""
    print("=" * 60)
    print("🧪 تست ۴: اطلاعات سیستم")
    print("=" * 60)
    print()

    import locale
    import os

    print(f"Python version: {sys.version}")
    print(f"Default encoding: {sys.getdefaultencoding()}")
    print(f"stdout encoding: {sys.stdout.encoding}")
    print(f"stderr encoding: {sys.stderr.encoding}")
    print()

    try:
        loc = locale.getlocale()
        print(f"Locale: {loc}")
    except:
        print("Locale: نامشخص")

    print()
    print("Environment variables:")
    for var in ['LANG', 'LC_ALL', 'PYTHONIOENCODING']:
        val = os.environ.get(var, 'تنظیم نشده')
        print(f"  {var}: {val}")
    print()

def main():
    """اجرای تمام تست‌ها"""

    # تنظیم encoding
    if sys.stdout.encoding != 'utf-8':
        sys.stdout.reconfigure(encoding='utf-8')
    if sys.stderr.encoding != 'utf-8':
        sys.stderr.reconfigure(encoding='utf-8')

    print()
    print("🚀 شروع تست‌های encoding")
    print()

    test_basic_output()
    test_file_write()
    test_file_read()
    test_system_info()

    print("=" * 60)
    print("✅ تمام تست‌ها با موفقیت انجام شد")
    print("=" * 60)
    print()
    print("اگر این پیام را می‌بینید، یعنی encoding به درستی کار می‌کند!")
    print()

if __name__ == "__main__":
    main()
