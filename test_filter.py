#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
اسکریپت تست فیلترینگ - برای دیباگ
"""

import sys
import re
from pathlib import Path

def test_tech_filter():
    """تست فیلتر تکنولوژی"""

    # نمونه پروژه‌های مختلف
    test_projects = [
        {
            "title": "ساخت ربات تلگرام",
            "description": "نیاز به یک ربات تلگرام با پایتون دارم",
            "skills": [{"name": "Python"}, {"name": "Telegram"}],
            "min_budget": 3000000
        },
        {
            "title": "طراحی سایت وردپرس",
            "description": "سایت فروشگاهی با وردپرس",
            "skills": [{"name": "WordPress"}, {"name": "PHP"}],
            "min_budget": 2000000
        },
        {
            "title": "API با Django",
            "description": "نیاز به REST API با Django و PostgreSQL",
            "skills": [{"name": "Django"}, {"name": "Python"}],
            "min_budget": 5000000
        },
        {
            "title": "طراحی رابط کاربری",
            "description": "طراحی UI با React",
            "skills": [{"name": "React"}, {"name": "JavaScript"}],
            "min_budget": 2000000
        },
    ]

    tech_blacklist = [
        'wordpress', 'wp', 'woocommerce',
        'shopify', 'php', 'magento',
        'react', 'vue', 'angular',
        'flutter', 'react native',
    ]

    tech_whitelist = [
        'python', 'django', 'fastapi', 'flask',
        'telegram', 'bot', 'ربات',
        'backend', 'api', 'rest',
        'postgresql', 'postgres', 'mongodb', 'redis',
    ]

    print("=" * 80)
    print("🧪 تست فیلتر تکنولوژی")
    print("=" * 80)

    for i, project in enumerate(test_projects, 1):
        title = project.get('title', '').lower()
        description = project.get('description', '').lower()
        skills = [s.get('name', '').lower() for s in project.get('skills', [])]

        combined_text = f"{title} {description} {' '.join(skills)}"

        print(f"\n{i}. {project['title']}")
        print(f"   بودجه: {project['min_budget']:,} تومان")

        # بررسی blacklist
        found_blacklist = None
        for tech in tech_blacklist:
            if tech.lower() in combined_text:
                found_blacklist = tech
                break

        # بررسی whitelist
        found_whitelist = []
        for tech in tech_whitelist:
            if tech.lower() in combined_text:
                found_whitelist.append(tech)

        if found_blacklist:
            print(f"   ❌ رد شد - تکنولوژی ممنوعه: {found_blacklist}")
        elif not found_whitelist:
            print(f"   ❌ رد شد - هیچ تکنولوژی مرتبطی نیست")
        elif project['min_budget'] < 1_500_000:
            print(f"   ❌ رد شد - بودجه کم")
        else:
            print(f"   ✅ قبول - تکنولوژی‌های مرتبط: {', '.join(found_whitelist)}")


def test_recommendation_parser(analysis_file=None):
    """تست parser امتیاز توصیه"""

    # نمونه‌های مختلف فرمت
    sample_outputs = [
        """
### 🎯 توصیه

⭐⭐⭐⭐⭐ Must take

این پروژه عالی است.
""",
        """
## توصیه

⭐⭐⭐ Consider

بودجه مناسب نیست.
""",
        """
🎯 توصیه: ⭐⭐ Skip

این پروژه مناسب نیست.
""",
    ]

    print("\n" + "=" * 80)
    print("🧪 تست Parser امتیاز توصیه")
    print("=" * 80)

    # اگر فایل داده شده، اونو تست کن
    if analysis_file and Path(analysis_file).exists():
        print(f"\n📄 تست فایل: {analysis_file}")
        with open(analysis_file, 'r', encoding='utf-8') as f:
            content = f.read()

        recommendation_section = re.search(
            r'(?:🎯|###)\s*توصیه.*?(?=(?:###|📝|💰|$))',
            content,
            re.DOTALL | re.IGNORECASE
        )

        if recommendation_section:
            section_text = recommendation_section.group(0)
            stars = section_text.count('⭐')

            decision = None
            if re.search(r'\b(skip|رد کن|نزن)\b', section_text, re.IGNORECASE):
                decision = "Skip"
            elif re.search(r'\b(take|قبول کن|بزن)\b', section_text, re.IGNORECASE):
                decision = "Take"

            print(f"   ⭐ ستاره‌ها: {stars}")
            print(f"   📊 تصمیم: {decision}")
            print(f"   📝 متن:\n{section_text[:300]}...")
        else:
            print("   ❌ بخش توصیه پیدا نشد!")
            print("\n🔍 محتوای فایل:")
            print(content[:500] + "...")

    # تست نمونه‌ها
    else:
        for i, sample in enumerate(sample_outputs, 1):
            print(f"\n{i}. نمونه {i}:")

            recommendation_section = re.search(
                r'(?:🎯|###)\s*توصیه.*?(?=(?:###|📝|💰|$))',
                sample,
                re.DOTALL | re.IGNORECASE
            )

            if recommendation_section:
                section_text = recommendation_section.group(0)
                stars = section_text.count('⭐')
                print(f"   ستاره‌ها: {stars}")
                print(f"   متن: {section_text.strip()}")
            else:
                print("   ❌ پیدا نشد")


def main():
    if len(sys.argv) > 1:
        # اگر فایل تحلیل داده شده
        test_recommendation_parser(sys.argv[1])
    else:
        # تست همه چیز
        test_tech_filter()
        test_recommendation_parser()

    print("\n" + "=" * 80)
    print("✅ تست تمام شد")
    print("=" * 80)


if __name__ == "__main__":
    main()
