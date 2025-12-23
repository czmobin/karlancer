#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Continuous Karlancer Bot
دریافت، تحلیل و ارسال خودکار پروپوزال‌ها به صورت مداوم
"""

import os
import sys
import json
import time
import subprocess
import requests
from datetime import datetime
from pathlib import Path

# تنظیم encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

# تنظیم environment
os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'


class ContinuousKarlancer:
    """ربات مداوم کارلنسر"""

    def __init__(self, bearer_token: str, check_interval: int = 300, auto_submit: bool = False):
        """
        مقداردهی اولیه

        Args:
            bearer_token: توکن API
            check_interval: فاصله زمانی بررسی (ثانیه) - پیش‌فرض 5 دقیقه
            auto_submit: ارسال خودکار proposal (پیش‌فرض: False)
        """
        self.bearer_token = bearer_token
        self.check_interval = check_interval
        self.auto_submit = auto_submit

        self.api_url = "https://www.karlancer.com/api/publics/search/projects"
        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'fa-IR,fa;q=0.9',
            'accept-charset': 'utf-8',
            'authorization': f'Bearer {bearer_token}',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36'
        }

        # فایل‌ها و پوشه‌ها
        self.cache_file = "seen_projects.json"
        self.prompt_file = "karelancer_prompt.txt"
        self.input_dir = Path("claude_input")
        self.output_dir = Path("proposals")
        self.tracking_file = "continuous_tracking.json"
        self.log_file = "continuous_bot.log"

        # ایجاد پوشه‌ها
        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        # بارگذاری cache
        self.seen_projects = self._load_cache()
        self.tracking = self._load_tracking()

    def _load_cache(self):
        """بارگذاری cache پروژه‌های دیده شده"""
        try:
            if Path(self.cache_file).exists():
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except Exception as e:
            self.log_error(f"خطا در بارگذاری cache: {e}")
        return set()

    def _save_cache(self):
        """ذخیره cache"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(list(self.seen_projects), f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_error(f"خطا در ذخیره cache: {e}")

    def _load_tracking(self):
        """بارگذاری tracking"""
        try:
            if Path(self.tracking_file).exists():
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except:
            pass
        return {
            "total_fetched": 0,
            "total_analyzed": 0,
            "total_submitted": 0,
            "total_failed": 0,
            "projects": {}
        }

    def _save_tracking(self):
        """ذخیره tracking"""
        try:
            with open(self.tracking_file, 'w', encoding='utf-8') as f:
                json.dump(self.tracking, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_error(f"خطا در ذخیره tracking: {e}")

    def log_info(self, message: str):
        """لاگ اطلاعات"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] ℹ️  {message}"
        print(log_msg, flush=True)
        self._append_log(log_msg)

    def log_success(self, message: str):
        """لاگ موفقیت"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] ✅ {message}"
        print(log_msg, flush=True)
        self._append_log(log_msg)

    def log_error(self, message: str):
        """لاگ خطا"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] ❌ {message}"
        print(log_msg, file=sys.stderr, flush=True)
        self._append_log(log_msg)

    def log_warning(self, message: str):
        """لاگ هشدار"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] ⚠️  {message}"
        print(log_msg, flush=True)
        self._append_log(log_msg)

    def _append_log(self, message: str):
        """افزودن به فایل لاگ"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except:
            pass

    def fetch_projects(self, query: str = "python"):
        """دریافت پروژه‌های جدید"""
        params = {
            'q': query,
            'order': 'newest',
            'logged_in': '1'
        }

        try:
            response = requests.get(
                self.api_url,
                headers=self.headers,
                params=params,
                timeout=15
            )
            response.encoding = 'utf-8'

            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    return data.get("data", {}).get("data", [])
        except Exception as e:
            self.log_error(f"خطا در دریافت پروژه‌ها: {e}")

        return []

    def save_project(self, project: dict):
        """ذخیره پروژه"""
        try:
            project_id = project.get('id')
            filename = self.input_dir / f"project_{project_id}.txt"

            # فرمت‌بندی
            title = project.get('title', 'بدون عنوان')
            description = project.get('description', '')
            min_budget = project.get('min_budget', 0)
            max_budget = project.get('max_budget', 0)
            duration = project.get('job_duration', 'نامشخص')
            url = project.get('url', '')

            skills = project.get('skills', [])
            skills_text = ', '.join([s.get('name', '') for s in skills]) if skills else 'مشخص نشده'

            text = f"""عنوان: {title}

توضیحات:
{description}

بودجه: {min_budget:,} تا {max_budget:,} تومان
زمان: {duration} روز
امتیاز کارفرما: {project.get('rate', 'N/A')}
شهر: {project.get('country', 'نامشخص')}

مهارت‌های مورد نیاز:
{skills_text}

لینک پروژه: https://www.karlancer.com/{url}
"""

            with open(filename, 'w', encoding='utf-8') as f:
                f.write(text)

            return filename
        except Exception as e:
            self.log_error(f"خطا در ذخیره پروژه {project.get('id')}: {e}")
            return None

    def analyze_project(self, project_id: int):
        """تحلیل یک پروژه با Claude"""
        try:
            project_file = self.input_dir / f"project_{project_id}.txt"

            if not project_file.exists():
                self.log_error(f"فایل پروژه {project_id} یافت نشد")
                return None

            # بارگذاری prompt
            if not Path(self.prompt_file).exists():
                self.log_error("فایل prompt یافت نشد")
                return None

            with open(self.prompt_file, 'r', encoding='utf-8') as f:
                system_prompt = f.read()

            with open(project_file, 'r', encoding='utf-8') as f:
                project_text = f.read()

            # ترکیب
            combined = f"""{system_prompt}

================================================================================

این پروژه جدید از کارلنسر اومده:

{project_text}"""

            # ذخیره temp
            temp_file = f"temp_{project_id}.txt"
            with open(temp_file, 'w', encoding='utf-8') as f:
                f.write(combined)

            self.log_info(f"تحلیل پروژه {project_id} با Claude...")

            # اجرای Claude
            try:
                result = subprocess.run(
                    ['claude', temp_file],
                    capture_output=True,
                    text=True,
                    timeout=300,
                    encoding='utf-8'
                )

                if result.returncode == 0:
                    output = result.stdout

                    # فیلتر noise
                    clean_output = '\n'.join([
                        line for line in output.split('\n')
                        if not any(x in line.lower() for x in ['trust', 'folder', 'security', '────'])
                    ])

                    if len(clean_output) > 200:
                        # ذخیره
                        output_file = self.output_dir / f"project_{project_id}_analysis.txt"
                        with open(output_file, 'w', encoding='utf-8') as f:
                            f.write(f"""Project ID: {project_id}
تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

{clean_output}
""")

                        self.log_success(f"تحلیل پروژه {project_id} موفق ({len(clean_output)} chars)")
                        return output_file
                    else:
                        self.log_warning(f"خروجی تحلیل پروژه {project_id} کوتاه است")
                else:
                    self.log_error(f"خطای Claude برای پروژه {project_id}: {result.stderr}")

            except subprocess.TimeoutExpired:
                self.log_error(f"Timeout در تحلیل پروژه {project_id}")
            except Exception as e:
                self.log_error(f"خطا در اجرای Claude: {e}")
            finally:
                # حذف temp
                if Path(temp_file).exists():
                    Path(temp_file).unlink()

        except Exception as e:
            self.log_error(f"خطا در تحلیل پروژه {project_id}: {e}")

        return None

    def submit_proposal(self, project_id: int, analysis_file: Path):
        """ارسال proposal (اختیاری)"""
        if not self.auto_submit:
            self.log_info(f"ارسال خودکار غیرفعال است - پروژه {project_id} آماده ارسال دستی")
            return False

        try:
            self.log_info(f"ارسال proposal برای پروژه {project_id}...")

            # اینجا کد submit_proposal.py رو صدا می‌زنیم
            # فعلاً فقط لاگ می‌کنیم
            self.log_warning("ارسال خودکار هنوز پیاده‌سازی نشده - لطفاً دستی ارسال کنید")
            return False

        except Exception as e:
            self.log_error(f"خطا در ارسال proposal: {e}")
            return False

    def process_new_projects(self):
        """پردازش پروژه‌های جدید"""
        self.log_info("جستجوی پروژه‌های جدید...")

        # دریافت پروژه‌ها
        all_projects = self.fetch_projects()

        if not all_projects:
            self.log_info("هیچ پروژه‌ای دریافت نشد")
            return

        # فیلتر جدیدها
        new_projects = [
            p for p in all_projects
            if p.get('id') and p['id'] not in self.seen_projects
        ]

        if not new_projects:
            self.log_info(f"تمام {len(all_projects)} پروژه قبلاً دیده شده‌اند")
            return

        self.log_success(f"🆕 {len(new_projects)} پروژه جدید پیدا شد!")

        # پردازش هر پروژه
        for idx, project in enumerate(new_projects, 1):
            project_id = project['id']
            title = project.get('title', 'بدون عنوان')

            print("\n" + "=" * 80)
            self.log_info(f"[{idx}/{len(new_projects)}] پروژه {project_id}: {title}")
            print("=" * 80)

            # ۱. ذخیره پروژه
            saved_file = self.save_project(project)
            if not saved_file:
                self.tracking["total_failed"] += 1
                continue

            # ۲. تحلیل پروژه
            analysis_file = self.analyze_project(project_id)

            if analysis_file:
                # ۳. ارسال (اختیاری)
                submitted = self.submit_proposal(project_id, analysis_file)

                # به‌روزرسانی tracking
                self.tracking["projects"][str(project_id)] = {
                    "title": title,
                    "fetched_at": datetime.now().isoformat(),
                    "analyzed": True,
                    "submitted": submitted,
                    "analysis_file": str(analysis_file)
                }
                self.tracking["total_analyzed"] += 1

                if submitted:
                    self.tracking["total_submitted"] += 1
            else:
                self.tracking["total_failed"] += 1
                self.tracking["projects"][str(project_id)] = {
                    "title": title,
                    "fetched_at": datetime.now().isoformat(),
                    "analyzed": False,
                    "submitted": False,
                    "error": "Analysis failed"
                }

            # اضافه به cache
            self.seen_projects.add(project_id)
            self.tracking["total_fetched"] += 1

            # ذخیره
            self._save_cache()
            self._save_tracking()

            # وقفه بین پروژه‌ها
            if idx < len(new_projects):
                time.sleep(2)

        print("\n" + "=" * 80)
        self.log_success(f"✅ پردازش {len(new_projects)} پروژه تمام شد")
        self.log_info(f"📊 آمار کل: {self.tracking['total_fetched']} دریافت، "
                     f"{self.tracking['total_analyzed']} تحلیل، "
                     f"{self.tracking['total_submitted']} ارسال، "
                     f"{self.tracking['total_failed']} خطا")
        print("=" * 80 + "\n")

    def run_continuous(self):
        """اجرای مداوم"""
        self.log_success("🚀 ربات مداوم کارلنسر شروع شد")
        self.log_info(f"⏰ فاصله بررسی: {self.check_interval} ثانیه ({self.check_interval // 60} دقیقه)")
        self.log_info(f"📤 ارسال خودکار: {'فعال' if self.auto_submit else 'غیرفعال'}")
        print("=" * 80 + "\n")

        iteration = 0

        try:
            while True:
                iteration += 1
                self.log_info(f"🔄 چرخه #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                try:
                    self.process_new_projects()
                except Exception as e:
                    self.log_error(f"خطا در پردازش: {e}")

                # انتظار برای چرخه بعدی
                self.log_info(f"😴 استراحت {self.check_interval} ثانیه تا چرخه بعدی...")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n")
            self.log_warning("⛔ متوقف شد توسط کاربر (Ctrl+C)")
            self.log_info("📊 آمار نهایی:")
            self.log_info(f"  - کل دریافت‌ها: {self.tracking['total_fetched']}")
            self.log_info(f"  - کل تحلیل‌ها: {self.tracking['total_analyzed']}")
            self.log_info(f"  - کل ارسال‌ها: {self.tracking['total_submitted']}")
            self.log_info(f"  - کل خطاها: {self.tracking['total_failed']}")
            self.log_success("👋 خداحافظ!")


def main():
    """تابع اصلی"""
    import argparse

    parser = argparse.ArgumentParser(description='ربات مداوم کارلنسر')
    parser.add_argument('--interval', type=int, default=300,
                       help='فاصله زمانی بررسی (ثانیه) - پیش‌فرض: 300 (5 دقیقه)')
    parser.add_argument('--auto-submit', action='store_true',
                       help='ارسال خودکار proposal ها')
    parser.add_argument('--once', action='store_true',
                       help='فقط یک بار اجرا شود (بدون loop)')

    args = parser.parse_args()

    BEARER_TOKEN = "2639199|WDj6UAvuCppotknYzIAvzaSBx1h9BPS151eVLgAwBL8HwQBeLGKXio5sSowHy97UrTdcIzViXQCUlX6ZA6SOy6JTGZmeuDME2dNESKGOUtBsqtpm5B3GeHCs6sJmhdxA2dUrmHQrcr7X24OcMOtfj7xpiO5sxoOiq0r9QfSMeDVsLtoXRus1rmbXlbMAmoTVzVlx5W7WHfdfpWElBtAVXuvWXWXomsMU1pMfTVhPaVZ1gkjC7NSUTpIi0SB16VfKtG7INfgosHBP8Z9ojB1g0cfQCdvRAjsxfbfwoW6zBI98D1xIKJn6mVas4jtFgBJRO5IXktQ0i77R0KANlIqlfZDPwMzklBCYR11U4SmDVrQ3diENQhCeV6F8Bcw2nQw6YB3sdJRXCRAktn6lg5cAGPL3h09RXo4KBGLYnNvgdMcTKQw9912ouaalBsE2jyJeogFI6J5uoL9MlSQfnvQlx2BFqePqAzF5vIDnJ8ck1kvpBxcJHZdkno8yhTHjrLfcU8HE0gI34pbr8NiGNR6WB5uBtXII"

    bot = ContinuousKarlancer(
        bearer_token=BEARER_TOKEN,
        check_interval=args.interval,
        auto_submit=args.auto_submit
    )

    if args.once:
        # فقط یک بار
        bot.log_info("🔍 اجرای یک‌باره...")
        bot.process_new_projects()
    else:
        # مداوم
        bot.run_continuous()


if __name__ == "__main__":
    main()
