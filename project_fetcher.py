#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
دریافت و ذخیره پروژه‌های جدید از کارلنسر
نسخه بهبود یافته برای لینوکس با پشتیبانی کامل از فارسی
"""

import os
import sys
import json
import locale
import requests
from datetime import datetime
from pathlib import Path

# تنظیم اجباری encoding برای stdout و stderr
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# تنظیم locale برای لینوکس
try:
    locale.setlocale(locale.LC_ALL, 'C.UTF-8')
except:
    try:
        locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
    except:
        pass


class ProjectFetcher:
    """دریافت پروژه‌های جدید از کارلنسر"""

    def __init__(self, bearer_token: str):
        """
        مقداردهی اولیه

        Args:
            bearer_token: توکن احراز هویت API
        """
        self.bearer_token = bearer_token
        self.api_url = "https://www.karlancer.com/api/publics/search/projects"

        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'fa-IR,fa;q=0.9,en-US;q=0.8,en;q=0.7',
            'accept-charset': 'utf-8',
            'authorization': f'Bearer {bearer_token}',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }

        self.cookies = {
            'eloquent_viewable': 'kRB3L7zZ1gj5ampde5QBLbXj9Am0xrJMZGKwnYJjlmNvg87k4Wa3qlORNyPVYEzD1oAoYNpeQrD9dq8G',
            '_ga': 'GA1.1.1605194695.1763027354'
        }

        # Cache
        self.cache_file = "seen_projects.json"
        self.seen_projects = self._load_cache()

    def _load_cache(self):
        """بارگذاری لیست پروژه‌های دیده شده از cache"""
        try:
            cache_path = Path(self.cache_file)
            if cache_path.exists():
                with open(cache_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return set(data)
        except Exception as e:
            self._log_error(f"خطا در بارگذاری cache: {e}")
        return set()

    def _save_cache(self):
        """ذخیره لیست پروژه‌های دیده شده در cache"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.seen_projects), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self._log_error(f"خطا در ذخیره cache: {e}")

    def _log_error(self, message: str):
        """ثبت خطا با encoding صحیح"""
        try:
            print(f"❌ {message}", file=sys.stderr, flush=True)
        except:
            # اگر حتی با UTF-8 هم مشکل داشت، به صورت ASCII
            print(f"ERROR: {message.encode('utf-8', errors='replace').decode('utf-8')}", file=sys.stderr)

    def _log_info(self, message: str):
        """ثبت اطلاعات با encoding صحیح"""
        try:
            print(message, flush=True)
        except:
            print(message.encode('utf-8', errors='replace').decode('utf-8'))

    def get_projects(self, query: str = "python", max_retries: int = 3):
        """
        دریافت پروژه‌ها از API

        Args:
            query: کلمه کلیدی جستجو
            max_retries: تعداد تلاش مجدد در صورت خطا

        Returns:
            list: لیست پروژه‌ها
        """
        params = {
            'q': query,
            'order': 'newest',
            'logged_in': '1'
        }

        for attempt in range(max_retries):
            try:
                response = requests.get(
                    self.api_url,
                    headers=self.headers,
                    cookies=self.cookies,
                    params=params,
                    timeout=15
                )

                response.encoding = 'utf-8'

                if response.status_code == 200:
                    data = response.json()

                    if data.get("status") == "success":
                        projects = data.get("data", {}).get("data", [])
                        self._log_info(f"✅ دریافت {len(projects)} پروژه از API")
                        return projects
                    else:
                        self._log_error(f"پاسخ ناموفق از API: {data.get('message', 'نامشخص')}")
                else:
                    self._log_error(f"خطای HTTP {response.status_code}")

            except requests.exceptions.Timeout:
                self._log_error(f"Timeout (تلاش {attempt + 1}/{max_retries})")
                if attempt < max_retries - 1:
                    import time
                    time.sleep(2 ** attempt)
            except requests.exceptions.RequestException as e:
                self._log_error(f"خطای شبکه: {e}")
            except json.JSONDecodeError:
                self._log_error("خطا در تجزیه JSON")
            except Exception as e:
                self._log_error(f"خطای غیرمنتظره: {e}")

        return []

    def get_new_projects(self, query: str = "python"):
        """
        دریافت فقط پروژه‌های جدید (که قبلاً دیده نشده‌اند)

        Args:
            query: کلمه کلیدی جستجو

        Returns:
            list: لیست پروژه‌های جدید
        """
        all_projects = self.get_projects(query)

        new_projects = [
            p for p in all_projects
            if p.get("id") and p["id"] not in self.seen_projects
        ]

        # اضافه کردن به cache
        for p in new_projects:
            if p.get("id"):
                self.seen_projects.add(p["id"])

        self._save_cache()
        return new_projects

    def save_project_json(self, project: dict):
        """
        ذخیره یک پروژه در فایل JSON جداگانه

        Args:
            project: دیکشنری اطلاعات پروژه

        Returns:
            Path: مسیر فایل ذخیره شده
        """
        try:
            # ساخت پوشه
            output_dir = Path("new_projects")
            output_dir.mkdir(exist_ok=True)

            # نام امن برای فایل (حذف کاراکترهای غیرمجاز)
            project_id = project.get('id', 'unknown')
            title = project.get('title', 'untitled')[:30]

            # حذف کاراکترهای غیرمجاز از نام فایل
            safe_chars = []
            for char in title:
                if char.isalnum() or char in (' ', '_', '-'):
                    safe_chars.append(char)
                else:
                    safe_chars.append('_')
            safe_title = ''.join(safe_chars).strip()

            if not safe_title:
                safe_title = "project"

            filename = output_dir / f"project_{project_id}_{safe_title}.json"

            # ذخیره با UTF-8
            with open(filename, 'w', encoding='utf-8') as f:
                json.dump(project, f, ensure_ascii=False, indent=2)

            return filename

        except Exception as e:
            self._log_error(f"خطا در ذخیره JSON: {e}")
            return None

    def format_for_claude(self, project: dict):
        """
        فرمت‌بندی پروژه برای ارسال به Claude

        Args:
            project: دیکشنری اطلاعات پروژه

        Returns:
            str: متن فرمت شده
        """
        try:
            # استخراج اطلاعات با مقادیر پیش‌فرض
            title = project.get('title', 'بدون عنوان')
            description = project.get('description', 'توضیحات موجود نیست')
            min_budget = project.get('min_budget', 0)
            max_budget = project.get('max_budget', 0)
            duration = project.get('job_duration', 'نامشخص')
            rate = project.get('rate', 'N/A')
            country = project.get('country', 'نامشخص')
            url = project.get('url', '')

            # استخراج مهارت‌ها
            skills = project.get('skills', [])
            if skills:
                skills_text = ', '.join([s.get('name', '') for s in skills if s.get('name')])
            else:
                skills_text = 'مشخص نشده'

            # فرمت‌بندی بودجه با جداکننده هزارگان
            try:
                budget_text = f"{min_budget:,} تا {max_budget:,} تومان"
            except:
                budget_text = f"{min_budget} تا {max_budget} تومان"

            text = f"""عنوان: {title}

توضیحات:
{description}

بودجه: {budget_text}
زمان: {duration} روز
امتیاز کارفرما: {rate}
شهر: {country}

مهارت‌های مورد نیاز:
{skills_text}

لینک پروژه: https://www.karlancer.com/{url}
"""
            return text

        except Exception as e:
            self._log_error(f"خطا در فرمت‌بندی: {e}")
            return f"خطا در فرمت‌بندی پروژه {project.get('id', 'unknown')}"

    def save_for_claude(self, project: dict):
        """
        ذخیره پروژه به فرمت متنی برای Claude

        Args:
            project: دیکشنری اطلاعات پروژه

        Returns:
            Path: مسیر فایل ذخیره شده
        """
        try:
            output_dir = Path("claude_input")
            output_dir.mkdir(exist_ok=True)

            project_id = project.get('id', 'unknown')
            filename = output_dir / f"project_{project_id}.txt"

            text = self.format_for_claude(project)

            # ذخیره با UTF-8 و newline مناسب
            with open(filename, 'w', encoding='utf-8', newline='\n') as f:
                f.write(text)

            return filename

        except Exception as e:
            self._log_error(f"خطا در ذخیره فایل Claude: {e}")
            return None


def main():
    """تابع اصلی برنامه"""

    # تنظیم متغیرهای محیطی برای لینوکس
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['LANG'] = 'C.UTF-8'
    os.environ['LC_ALL'] = 'C.UTF-8'

    BEARER_TOKEN = "3348607|BHYW9dGug9NfxzKnupktkJMnFJXyTP85ao9HdyATZmHBsITvVo4lEYW5R5sF7Ub6vT4yw4k0LYeKL4NB6zOIM7KQ7O2kjR1vKJEBrjf1xH3LzmkdrvezvTaanTcRXbmBiZa9MQAecuaCc00T0eo8FtXW1NIRsdiQaSoIEB84CGRFvW2LuxJrEOvtp6U1xkftJcbFy6ff8QcyYA3YPoGdduMFleQCMPKP51Zjo7jzdcHjgI0gSHArddVy1IASxLqldLAMwDge8FsASuIFe44mGmIqNbtohf4jmUgOpWeyrAPI6NMLTwOTES3FxGzjL1CQtWSxOSnSq7j9mdTYEg1bx7d3kEkHcK0BaMKtDfA96nowhRgUzCGUyxB6X6RaCJO8rSNH23djAphwEq9RU24CPYuHJHs03wj7ZbfdeUHrmAdjivlTqJ1d0zm9Ylris4UxBKNhqZTdEkZKhzpn8T3ii4IxzLFLzDHSRDNuYrDrjXWW8NxFMdCZ4Tsm73ZMdHpG0j9yzsqfuhHgCzwzuBn7kQNlVqJV"

    fetcher = ProjectFetcher(BEARER_TOKEN)

    print("=" * 60)
    print("🔍 جستجوی پروژه‌های جدید در کارلنسر...")
    print("=" * 60)
    print()

    new_projects = fetcher.get_new_projects("python")

    if new_projects:
        print(f"✅ تعداد {len(new_projects)} پروژه جدید پیدا شد!")
        print()

        for idx, project in enumerate(new_projects, 1):
            print(f"{'─' * 60}")
            print(f"📋 پروژه #{idx}: {project.get('title', 'بدون عنوان')}")

            try:
                min_budget = project.get('min_budget', 0)
                max_budget = project.get('max_budget', 0)
                print(f"💰 بودجه: {min_budget:,} - {max_budget:,} تومان")
            except:
                print(f"💰 بودجه: {project.get('min_budget', 0)} - {project.get('max_budget', 0)} تومان")

            print(f"⏱️  مدت زمان: {project.get('job_duration', 'نامشخص')} روز")

            # ذخیره JSON
            json_file = fetcher.save_project_json(project)
            if json_file:
                print(f"💾 فایل JSON: {json_file}")

            # ذخیره برای Claude
            txt_file = fetcher.save_for_claude(project)
            if txt_file:
                print(f"📝 فایل متنی: {txt_file}")

            print()
    else:
        print("✅ پروژه جدیدی یافت نشد")
        print()

    print("=" * 60)
    print("✅ پایان عملیات")
    print("=" * 60)


if __name__ == "__main__":
    main()
