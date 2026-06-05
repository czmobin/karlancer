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
import traceback
import requests
from datetime import datetime
from pathlib import Path
import anthropic
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

    def __init__(self, bearer_token: str, check_interval: int = 300, auto_submit: bool = False, min_stars: int = 4, strict_mode: bool = False, telegram_logger: TelegramLogger = None, debug: bool = False):
        """
        مقداردهی اولیه

        Args:
            bearer_token: توکن API
            check_interval: فاصله زمانی بررسی (ثانیه) - پیش‌فرض 5 دقیقه
            auto_submit: ارسال خودکار proposal (پیش‌فرض: False)
            min_stars: حداقل امتیاز ستاره برای ارسال خودکار (1-5) - پیش‌فرض: 4
            strict_mode: حالت سخت‌گیرانه برای whitelist (پیش‌فرض: False)
            telegram_logger: logger تلگرام (اختیاری)
            debug: حالت دیباگ - لاگ کامل و جزئیات بیشتر (پیش‌فرض: False)
        """
        self.bearer_token = bearer_token
        self.check_interval = check_interval
        self.auto_submit = auto_submit
        self.min_stars = min_stars
        self.strict_mode = strict_mode
        self.tg = telegram_logger  # Telegram Logger
        self.debug = debug  # حالت دیباگ

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
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/145.0.0.0 Safari/537.36',
            'referer': 'https://www.karlancer.com/',
            'sec-ch-ua': '"Not:A-Brand";v="99", "Google Chrome";v="145", "Chromium";v="145"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"'
        }

        self.ai_client = anthropic.Anthropic()
        self.ai_model = "claude-opus-4-7"

        # فایل‌ها و پوشه‌ها
        self.cache_file = "seen_projects.json"
        self.prompt_file = "karelancer_prompt.txt"
        self.input_dir = Path("claude_input")
        self.output_dir = Path("proposals")
        self.tracking_file = "continuous_tracking.json"
        self.log_file = "continuous_bot.log"
        self.debug_file = "continuous_debug.log"  # لاگ کامل دیباگ (همه چیز)

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
        except Exception as e:
            # قبلاً بی‌صدا بود؛ حالا حداقل توی فایل دیباگ ثبت میشه
            self._append_debug(f"⚠️  خطا در بارگذاری tracking ({self.tracking_file}): {e}")
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
        self._append_debug(log_msg)

    def log_success(self, message: str):
        """لاگ موفقیت"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] ✅ {message}"
        print(log_msg, flush=True)
        self._append_log(log_msg)
        self._append_debug(log_msg)

    def log_error(self, message: str):
        """لاگ خطا"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] ❌ {message}"
        print(log_msg, file=sys.stderr, flush=True)
        self._append_log(log_msg)
        self._append_debug(log_msg)

    def log_warning(self, message: str):
        """لاگ هشدار"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] ⚠️  {message}"
        print(log_msg, flush=True)
        self._append_log(log_msg)
        self._append_debug(log_msg)

    def log_debug(self, message: str):
        """لاگ دیباگ - فقط در حالت debug روی کنسول، ولی همیشه توی فایل دیباگ"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        log_msg = f"[{timestamp}] 🐞 {message}"
        if self.debug:
            print(log_msg, flush=True)
        self._append_debug(log_msg)

    def log_exception(self, context: str, exc: Exception, notify: bool = False):
        """
        لاگ کامل یک استثنا با traceback - تا دقیق معلوم بشه از چی بوده

        Args:
            context: توضیح اینکه کجا اتفاق افتاد
            exc: خود استثنا
            notify: اگه True باشه، خطا به تلگرام هم ارسال میشه
        """
        # نوع و پیام استثنا
        err_type = type(exc).__name__
        self.log_error(f"{context}: [{err_type}] {exc}")

        # traceback کامل فقط توی فایل دیباگ (تا کنسول شلوغ نشه)
        tb = traceback.format_exc()
        self._append_debug(f"---- TRACEBACK ({context}) ----\n{tb}--------")
        if self.debug:
            print(tb, file=sys.stderr, flush=True)

        # اطلاع به تلگرام برای خطاهای مهم
        if notify and self.tg:
            try:
                self.tg.send_error(f"{context}\n<code>[{err_type}] {exc}</code>")
            except Exception:
                pass

    def _append_log(self, message: str):
        """افزودن به فایل لاگ"""
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(message + '\n')
        except:
            pass

    def _append_debug(self, message: str):
        """افزودن به فایل لاگ دیباگ (همیشه فعال - حتی بدون --debug)"""
        try:
            with open(self.debug_file, 'a', encoding='utf-8') as f:
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

        self.log_debug(f"GET {self.api_url} | query='{query}' | params={params}")

        try:
            response = requests.get(
                self.api_url,
                headers=self.headers,
                params=params,
                timeout=15
            )
            response.encoding = 'utf-8'

            self.log_debug(f"پاسخ '{query}': HTTP {response.status_code} | {len(response.content)} bytes")

            # 🔴 توکن منقضی/نامعتبر - مهم‌ترین خطایی که قبلاً بی‌صدا بود
            if response.status_code in (401, 403):
                self.log_error(
                    f"احراز هویت رد شد (HTTP {response.status_code}) برای '{query}' - "
                    f"احتمالاً Bearer token منقضی شده! پاسخ: {response.text[:300]}"
                )
                if self.tg:
                    try:
                        self.tg.send_error(
                            f"🔑 توکن کارلنسر رد شد (HTTP {response.status_code})\n"
                            f"احتمالاً Bearer token منقضی شده — باید آپدیتش کنی."
                        )
                    except Exception:
                        pass
                return []

            if response.status_code != 200:
                self.log_error(
                    f"دریافت '{query}' ناموفق: HTTP {response.status_code} | پاسخ: {response.text[:300]}"
                )
                return []

            # تلاش برای پارس JSON
            try:
                data = response.json()
            except Exception as e:
                self.log_error(
                    f"پاسخ '{query}' JSON معتبر نبود: {e} | متن خام: {response.text[:300]}"
                )
                return []

            status = data.get("status")
            if status == "success":
                projects = data.get("data", {}).get("data", [])
                self.log_debug(f"'{query}': {len(projects)} پروژه در پاسخ موفق")
                return projects
            else:
                # پاسخ ۲۰۰ ولی status != success - قبلاً کاملاً بی‌صدا رد می‌شد
                self.log_warning(
                    f"دریافت '{query}': status='{status}' (موفق نبود) | "
                    f"message={data.get('message')} | پاسخ: {str(data)[:300]}"
                )
                return []

        except requests.exceptions.Timeout:
            self.log_error(f"دریافت '{query}' timeout شد (>15s)")
        except requests.exceptions.ConnectionError as e:
            self.log_error(f"خطای اتصال شبکه در دریافت '{query}': {e}")
        except Exception as e:
            self.log_exception(f"خطای ناشناخته در دریافت پروژه‌های '{query}'", e)

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

            self.log_info(f"تحلیل پروژه {project_id} با AI...")
            self.log_debug(
                f"AI request پروژه {project_id}: model={self.ai_model} | "
                f"prompt={len(system_prompt)} chars | project={len(project_text)} chars"
            )

            # ارسال به API
            try:
                response = self.ai_client.messages.create(
                    model=self.ai_model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=[{"role": "user", "content": f"این پروژه جدید از کارلنسر اومده:\n\n{project_text}"}]
                )

                # لاگ اطلاعات پاسخ AI برای دیباگ (مصرف توکن و دلیل توقف)
                stop_reason = getattr(response, "stop_reason", None)
                usage = getattr(response, "usage", None)
                self.log_debug(
                    f"AI response پروژه {project_id}: stop_reason={stop_reason} | usage={usage}"
                )

                if not response.content:
                    self.log_error(
                        f"پاسخ AI برای پروژه {project_id} خالی بود (content empty) | "
                        f"stop_reason={stop_reason}"
                    )
                    return None

                output = response.content[0].text

                if output and len(output) > 200:
                    # ذخیره
                    output_file = self.output_dir / f"project_{project_id}_analysis.txt"
                    with open(output_file, 'w', encoding='utf-8') as f:
                        f.write(f"""Project ID: {project_id}
تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
================================================================================

{output}
""")

                    self.log_success(f"تحلیل پروژه {project_id} موفق ({len(output)} chars)")
                    return output_file
                else:
                    # خروجی کوتاه - خود متن رو لاگ کن تا معلوم بشه AI چی گفته
                    self.log_warning(
                        f"خروجی تحلیل پروژه {project_id} کوتاه است "
                        f"({len(output) if output else 0} chars) | stop_reason={stop_reason}"
                    )
                    self.log_debug(f"خروجی کوتاه AI پروژه {project_id}: {repr(output)}")

            except anthropic.APIStatusError as e:
                # خطاهای HTTP از سمت Anthropic (مثلا 429 rate limit، 401 کلید نامعتبر، 529 overloaded)
                status = getattr(e, "status_code", "?")
                self.log_exception(
                    f"خطای API انتروپیک در تحلیل پروژه {project_id} (HTTP {status})",
                    e, notify=True
                )
            except anthropic.APIConnectionError as e:
                self.log_exception(
                    f"خطای اتصال به API انتروپیک در تحلیل پروژه {project_id}", e, notify=True
                )
            except Exception as e:
                self.log_exception(f"خطا در اجرای AI برای پروژه {project_id}", e, notify=True)

        except Exception as e:
            self.log_exception(f"خطا در تحلیل پروژه {project_id}", e)

        return None

    def submit_proposal(self, project_id: int, project: dict, analysis_file: Path):
        """ارسال proposal - همه پروژه‌ها ارسال میشن"""
        try:
            self.log_info(f"📤 ارسال خودکار proposal برای پروژه {project_id}...")

            # Import ProposalSubmitter
            import sys
            sys.path.insert(0, str(Path(__file__).parent))
            from submit_proposal import ProposalSubmitter

            submitter = ProposalSubmitter(self.bearer_token)

            # استخراج proposal
            proposal = submitter.extract_proposal_from_analysis(str(analysis_file))

            if not proposal:
                self.log_error(f"نمی‌توان proposal از فایل {analysis_file} استخراج کرد")
                return False

            # 🎯 تشخیص پروژه تخمی و تغییر "سلام" به "SALAM"
            if self.is_low_quality_project(project):
                self.log_warning(f"⚠️  پروژه {project_id} تخمی تشخیص داده شد - تغییر سلام به SALAM")
                # عوض کردن همه "سلام" ها با "SALAM"
                proposal = proposal.replace('سلام', 'SALAM')
                proposal = proposal.replace('سلام،', 'SALAM،')

            self.log_debug(
                f"ارسال proposal پروژه {project_id}: طول proposal={len(proposal)} chars"
            )

            # ارسال
            result = submitter.submit_proposal(
                project_id=project_id,
                description=proposal,
                analysis_file=str(analysis_file)
            )

            if result['success']:
                self.log_success(f"✅ پروژه {project_id} با موفقیت ارسال شد!")
                self.log_debug(f"پاسخ ارسال پروژه {project_id}: {str(result.get('data'))[:500]}")
                return True
            else:
                # خطای سرور موقع ارسال - متن کامل پاسخ مهمه (مثلا 'قبلاً پیشنهاد دادی')
                self.log_error(f"خطا در ارسال پروژه {project_id}: {result['error']}")
                if self.tg:
                    try:
                        self.tg.send_error(
                            f"📤 ارسال پروپوزال پروژه {project_id} ناموفق\n"
                            f"<code>{str(result['error'])[:500]}</code>"
                        )
                    except Exception:
                        pass
                return False

        except Exception as e:
            self.log_exception(f"خطا در ارسال proposal پروژه {project_id}", e, notify=True)
            return False

    def process_new_projects(self):
        """پردازش پروژه‌های جدید"""
        self.log_info("جستجوی پروژه‌های جدید...")

        queries = [
            "python", "پایتون",
            "django", "جنگو",
            "fastapi",
            "ربات", "bot",
            "backend", "بک‌اند",
            "api",
            "scraping", "اسکرپینگ",
            "automation", "اتوماسیون",
            "telegram", "تلگرام",
            "بله", "روبیکا",
        ]

        # دریافت پروژه‌ها از همه کلمات کلیدی (بدون تکرار)
        seen_ids = set()
        all_projects = []
        for query in queries:
            results = self.fetch_projects(query)
            for p in results:
                pid = p.get('id')
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_projects.append(p)

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
        self.log_info(f"🐞 حالت دیباگ: {'فعال (verbose)' if self.debug else 'غیرفعال (ولی فایل دیباگ همیشه نوشته میشه)'}")
        self.log_info(f"📄 لاگ کامل: {self.log_file} | لاگ دیباگ: {self.debug_file}")
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
                    self.log_exception(f"خطا در پردازش چرخه #{iteration}", e, notify=True)

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
    parser.add_argument('--debug', action='store_true',
                       help='حالت دیباگ: لاگ کامل با traceback و جزئیات HTTP/AI روی کنسول')

    args = parser.parse_args()

    BEARER_TOKEN = "3348607|BHYW9dGug9NfxzKnupktkJMnFJXyTP85ao9HdyATZmHBsITvVo4lEYW5R5sF7Ub6vT4yw4k0LYeKL4NB6zOIM7KQ7O2kjR1vKJEBrjf1xH3LzmkdrvezvTaanTcRXbmBiZa9MQAecuaCc00T0eo8FtXW1NIRsdiQaSoIEB84CGRFvW2LuxJrEOvtp6U1xkftJcbFy6ff8QcyYA3YPoGdduMFleQCMPKP51Zjo7jzdcHjgI0gSHArddVy1IASxLqldLAMwDge8FsASuIFe44mGmIqNbtohf4jmUgOpWeyrAPI6NMLTwOTES3FxGzjL1CQtWSxOSnSq7j9mdTYEg1bx7d3kEkHcK0BaMKtDfA96nowhRgUzCGUyxB6X6RaCJO8rSNH23djAphwEq9RU24CPYuHJHs03wj7ZbfdeUHrmAdjivlTqJ1d0zm9Ylris4UxBKNhqZTdEkZKhzpn8T3ii4IxzLFLzDHSRDNuYrDrjXWW8NxFMdCZ4Tsm73ZMdHpG0j9yzsqfuhHgCzwzuBn7kQNlVqJV"
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
        telegram_logger=telegram_logger,
        debug=args.debug
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
