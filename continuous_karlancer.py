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
from telegram_logger import TelegramLogger

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

    def __init__(self, bearer_token: str, check_interval: int = 300, auto_submit: bool = False, min_stars: int = 4, strict_mode: bool = False, telegram_logger: TelegramLogger = None):
        """
        مقداردهی اولیه

        Args:
            bearer_token: توکن API
            check_interval: فاصله زمانی بررسی (ثانیه) - پیش‌فرض 5 دقیقه
            auto_submit: ارسال خودکار proposal (پیش‌فرض: False)
            min_stars: حداقل امتیاز ستاره برای ارسال خودکار (1-5) - پیش‌فرض: 4
            strict_mode: حالت سخت‌گیرانه برای whitelist (پیش‌فرض: False)
            telegram_logger: logger تلگرام (اختیاری)
        """
        self.bearer_token = bearer_token
        self.check_interval = check_interval
        self.auto_submit = auto_submit
        self.min_stars = min_stars
        self.strict_mode = strict_mode
        self.tg = telegram_logger  # Telegram Logger

        # تکنولوژی‌ها و کلمات کلیدی که باید رد بشن
        self.tech_blacklist = [
            'wordpress', 'wp', 'woocommerce',
            'shopify',
            'php',  # اگر pure PHP باشه
            'magento',
            'joomla',
            'drupal',
            'react', 'vue', 'angular',  # pure frontend
            'flutter', 'react native',  # mobile development
            'ios', 'swift', 'android studio',
            '.net', 'c#',
            'java', 'spring',
        ]

        # کلمات کلیدی مثبت که باید داشته باشه
        self.tech_whitelist = [
            'python', 'django', 'fastapi', 'flask',
            'telegram', 'bot', 'ربات',
            'backend', 'api', 'rest',
            'postgresql', 'postgres', 'mongodb', 'redis',
            'celery', 'rabbitmq',
            'scraping', 'scrapy', 'beautifulsoup',
            'automation',
        ]

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

    def is_low_quality_project(self, project: dict):
        """تشخیص پروژه‌های تخمی"""
        title = project.get('title', '').lower()
        description = project.get('description', '').lower()
        min_budget = project.get('min_budget', 0)

        # چک کردن تکنولوژی‌های نامناسب
        bad_techs = ['wordpress', 'wp', 'woocommerce', 'shopify', 'php']
        for tech in bad_techs:
            if tech in title or tech in description:
                return True

        # چک کردن بودجه خیلی پایین
        if min_budget < 1_000_000:
            return True

        return False

    def should_submit_proposal(self, project: dict, analysis_file: Path):
        """همه پروژه‌ها ارسال میشن - بدون فیلتر!"""
        return True, "Send all projects"

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

    def submit_proposal(self, project_id: int, project: dict, analysis_file: Path):
        """ارسال proposal - کل محتوای Claude رو میفرسته"""
        try:
            self.log_info(f"📤 ارسال خودکار proposal برای پروژه {project_id}...")

            # خواندن کل فایل تحلیل
            with open(analysis_file, 'r', encoding='utf-8') as f:
                full_content = f.read()

            # حذف header (خطوط اول که Project ID و تاریخ هستن)
            lines = full_content.split('\n')
            clean_lines = []

            for i, line in enumerate(lines):
                # Skip first 3 lines (Project ID, date, ===)
                if i < 3:
                    continue
                clean_lines.append(line)

            proposal = '\n'.join(clean_lines).strip()

            if not proposal or len(proposal) < 50:
                self.log_error(f"محتوای تحلیل خیلی کوتاه است: {len(proposal)} chars")
                return False

            # 🎯 تشخیص پروژه تخمی و تغییر "سلام" به "SALAM"
            if self.is_low_quality_project(project):
                self.log_warning(f"⚠️  پروژه {project_id} تخمی - تغییر سلام به SALAM")
                proposal = proposal.replace('سلام', 'SALAM')
                proposal = proposal.replace('سلام،', 'SALAM،')

            # ارسال
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from submit_proposal import ProposalSubmitter

            submitter = ProposalSubmitter(self.bearer_token)
            result = submitter.submit_proposal(
                project_id=project_id,
                description=proposal,
                analysis_file=str(analysis_file)
            )

            if result['success']:
                self.log_success(f"✅ پروژه {project_id} با موفقیت ارسال شد!")
                return True
            else:
                self.log_error(f"خطا در ارسال پروژه {project_id}: {result['error']}")
                return False

        except Exception as e:
            self.log_error(f"خطا در ارسال proposal: {e}")
            import traceback
            self.log_error(traceback.format_exc())
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

        # اطلاع به تلگرام
        if self.tg:
            self.tg.send_new_projects(len(new_projects))

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
                # ۳. ارسال (همه ارسال میشن!)
                submitted, submit_reason = False, "Not submitted"
                if self.auto_submit:
                    # ارسال بدون فیلتر
                    submitted = self.submit_proposal(project_id, project, analysis_file)
                    submit_reason = "Submitted successfully" if submitted else "Submission failed"

                    # اطلاع به تلگرام
                    if submitted and self.tg:
                        self.tg.send_project_submitted(project_id, title)
                else:
                    submit_reason = "Auto-submit disabled"

                # به‌روزرسانی tracking
                self.tracking["projects"][str(project_id)] = {
                    "title": title,
                    "fetched_at": datetime.now().isoformat(),
                    "analyzed": True,
                    "submitted": submitted,
                    "submit_reason": submit_reason,
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
        self.log_info(f"🔒 حالت: {'سخت‌گیرانه (strict)' if self.strict_mode else 'عادی (normal)'}")
        self.log_info(f"🎯 فیلتر: فقط بر اساس تکنولوژی (blacklist) و بودجه (>1.5M)")
        if self.tg:
            self.log_info(f"📱 Telegram Logger: فعال")
        print("=" * 80 + "\n")

        # اطلاع شروع به تلگرام
        if self.tg:
            self.tg.send_startup(self.check_interval, self.auto_submit, 0, self.strict_mode)

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

            # اطلاع به تلگرام
            if self.tg:
                self.tg.send_shutdown(
                    self.tracking['total_fetched'],
                    self.tracking['total_analyzed'],
                    self.tracking['total_submitted'],
                    self.tracking['total_failed']
                )

            self.log_success("👋 خداحافظ!")


def main():
    """تابع اصلی"""
    import argparse

    parser = argparse.ArgumentParser(description='ربات مداوم کارلنسر - ارسال خودکار بدون rating')
    parser.add_argument('--interval', type=int, default=300,
                       help='فاصله زمانی بررسی (ثانیه) - پیش‌فرض: 300 (5 دقیقه)')
    parser.add_argument('--auto-submit', action='store_true',
                       help='ارسال خودکار proposal ها (بر اساس تکنولوژی و بودجه)')
    parser.add_argument('--strict', action='store_true',
                       help='حالت سخت‌گیرانه: whitelist فعال میشه و فقط پروژه‌های Python/Django/Bot قبول میشن')
    parser.add_argument('--telegram-chat-id', type=str,
                       help='Chat ID تلگرام برای دریافت لاگ‌ها')
    parser.add_argument('--once', action='store_true',
                       help='فقط یک بار اجرا شود (بدون loop)')

    args = parser.parse_args()

    BEARER_TOKEN = "2639199|WDj6UAvuCppotknYzIAvzaSBx1h9BPS151eVLgAwBL8HwQBeLGKXio5sSowHy97UrTdcIzViXQCUlX6ZA6SOy6JTGZmeuDME2dNESKGOUtBsqtpm5B3GeHCs6sJmhdxA2dUrmHQrcr7X24OcMOtfj7xpiO5sxoOiq0r9QfSMeDVsLtoXRus1rmbXlbMAmoTVzVlx5W7WHfdfpWElBtAVXuvWXWXomsMU1pMfTVhPaVZ1gkjC7NSUTpIi0SB16VfKtG7INfgosHBP8Z9ojB1g0cfQCdvRAjsxfbfwoW6zBI98D1xIKJn6mVas4jtFgBJRO5IXktQ0i77R0KANlIqlfZDPwMzklBCYR11U4SmDVrQ3diENQhCeV6F8Bcw2nQw6YB3sdJRXCRAktn6lg5cAGPL3h09RXo4KBGLYnNvgdMcTKQw9912ouaalBsE2jyJeogFI6J5uoL9MlSQfnvQlx2BFqePqAzF5vIDnJ8ck1kvpBxcJHZdkno8yhTHjrLfcU8HE0gI34pbr8NiGNR6WB5uBtXII"
    TELEGRAM_BOT_TOKEN = "8479753307:AAEOOUbyv6Jun5fZKb73dpKEsMLL8xAUub4"

    # خواندن Chat ID از فایل یا آرگومان
    chat_id = args.telegram_chat_id

    # اگر chat_id داده نشده، از فایل بخون
    if not chat_id and Path('.telegram_chat_id').exists():
        try:
            with open('.telegram_chat_id', 'r') as f:
                chat_id = f.read().strip()
                print(f"📱 Chat ID از فایل خوانده شد: {chat_id}")
        except Exception as e:
            print(f"⚠️  خطا در خواندن .telegram_chat_id: {e}")

    # Initialize Telegram Logger
    telegram_logger = None
    if chat_id:
        telegram_logger = TelegramLogger(
            bot_token=TELEGRAM_BOT_TOKEN,
            chat_id=chat_id,
            enabled=True
        )
        # تست اتصال
        print("🧪 تست اتصال به تلگرام...")
        if not telegram_logger.test_connection():
            print("⚠️  خطا در اتصال به بات تلگرام - ادامه بدون Telegram Logger")
            telegram_logger = None
        else:
            print("✅ Telegram Logger فعال شد!")
    else:
        print("ℹ️  Telegram Logger غیرفعال است (برای فعال‌سازی: python3 get_chat_id.py <bot_token>)")

    bot = ContinuousKarlancer(
        bearer_token=BEARER_TOKEN,
        check_interval=args.interval,
        auto_submit=args.auto_submit,
        min_stars=0,  # دیگه استفاده نمیشه - فقط برای سازگاری
        strict_mode=args.strict,
        telegram_logger=telegram_logger
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
