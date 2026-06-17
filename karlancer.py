#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ربات خودکار کارلنسر
دریافت، تحلیل و ارسال خودکار پروپوزال به صورت مداوم
"""

import os
import sys
import json
import re
import time
import subprocess
import argparse
import requests
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

os.environ['PYTHONIOENCODING'] = 'utf-8'
os.environ['LANG'] = 'C.UTF-8'
os.environ['LC_ALL'] = 'C.UTF-8'

# socks:// -> socks5h:// برای سازگاری requests با PySocks
for key in ('all_proxy', 'ALL_PROXY'):
    val = os.environ.get(key, '')
    if val.startswith('socks://'):
        os.environ[key] = val.replace('socks://', 'socks5h://', 1)


# ---------------------------------------------------------------------------
# Telegram Logger
# ---------------------------------------------------------------------------

class TelegramLogger:

    def __init__(self, bot_token: str, chat_id: str):
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        try:
            response = requests.post(
                f"{self.api_url}/sendMessage",
                json={
                    "chat_id": self.chat_id,
                    "text": text,
                    "parse_mode": parse_mode,
                    "disable_web_page_preview": True,
                },
                timeout=10,
            )
            if response.status_code == 200:
                return True
            print(f"⚠️  خطا در ارسال به تلگرام: {response.status_code}")
            return False
        except Exception as e:
            print(f"⚠️  خطا در ارسال به تلگرام: {e}")
            return False

    def test_connection(self) -> bool:
        try:
            response = requests.get(f"{self.api_url}/getMe", timeout=5)
            if response.status_code == 200:
                bot_name = response.json().get('result', {}).get('first_name', 'Unknown')
                print(f"✅ اتصال به بات موفق: {bot_name}")
                return self.send_message(
                    f"🧪 <b>تست اتصال موفق</b>\n\nبات: {bot_name}\n"
                    f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
            return False
        except Exception:
            return False

    def send_startup(self, interval: int):
        self.send_message(
            f"🚀 <b>ربات کارلنسر شروع شد</b>\n\n"
            f"⏰ فاصله بررسی: {interval} ثانیه ({interval // 60} دقیقه)\n"
            f"📤 ارسال خودکار: ✅ فعال\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def send_new_projects(self, count: int):
        self.send_message(f"🆕 <b>{count} پروژه جدید پیدا شد!</b>\n\nدر حال تحلیل و ارسال...")

    def send_project_submitted(self, project_id: int, title: str):
        self.send_message(
            f"✅ <b>پروپوزال ارسال شد!</b>\n\n"
            f"📋 ID: {project_id}\n"
            f"📌 {title[:50]}{'...' if len(title) > 50 else ''}\n\n"
            f"🔗 لینک: https://www.karlancer.com/project/{project_id}"
        )

    def send_error(self, error_msg: str):
        self.send_message(
            f"❌ <b>خطا رخ داد</b>\n\n{error_msg}\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )

    def send_shutdown(self, stats: dict):
        self.send_message(
            f"⛔ <b>ربات متوقف شد</b>\n\n"
            f"📊 آمار نهایی:\n"
            f"  🔍 دریافت: {stats['total_fetched']}\n"
            f"  🧠 تحلیل: {stats['total_analyzed']}\n"
            f"  📤 ارسال: {stats['total_submitted']}\n"
            f"  ❌ خطا: {stats['total_failed']}\n\n"
            f"📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        )


# ---------------------------------------------------------------------------
# Karlancer Bot
# ---------------------------------------------------------------------------

class Karlancer:

    SEARCH_API = "https://www.karlancer.com/api/publics/search/projects"
    PROJECT_API = "https://www.karlancer.com/api/publics/projects"
    BIDS_API = "https://www.karlancer.com/api/bids"

    def __init__(self, bearer_token: str, check_interval: int = 300, model: str = "sonnet", tg: TelegramLogger = None):
        self.bearer_token = bearer_token
        self.check_interval = check_interval
        self.model = model
        self.tg = tg

        self.headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.5',
            'authorization': f'Bearer {bearer_token}',
            'referer': 'https://www.karlancer.com/',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0',
        }
        self.submit_headers = {
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'en-US,en;q=0.5',
            'authorization': f'Bearer {bearer_token}',
            'content-type': 'application/json',
            'origin': 'https://www.karlancer.com',
            'referer': 'https://www.karlancer.com/',
            'user-agent': 'Mozilla/5.0 (X11; Linux x86_64; rv:130.0) Gecko/20100101 Firefox/130.0',
        }
        self.cookies = {
            'G_ENABLED_IDPS': 'google',
            'eloquent_viewable': 'lrRwPM0DaeQAEN9JRMwKyGaVoj5pQY78mXOnjDq7ebEX6BL1EbD3qrA4deZgW0xzlkPdGBZpmJL3g7Yy',
            '_ga': 'GA1.1.111872314.1781367982',
        }

        self.prompt_file = "karelancer_prompt.txt"
        self.cache_file = "seen_projects.json"
        self.tracking_file = "tracking.json"
        self.log_file = "karlancer.log"
        self.input_dir = Path("claude_input")
        self.output_dir = Path("proposals")

        self.input_dir.mkdir(exist_ok=True)
        self.output_dir.mkdir(exist_ok=True)

        self.seen_projects = self._load_json_set(self.cache_file)
        self.tracking = self._load_tracking()

    # -- persistence ---------------------------------------------------------

    def _load_json_set(self, path: str) -> set:
        try:
            if Path(path).exists():
                with open(path, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except Exception:
            pass
        return set()

    def _save_cache(self):
        with open(self.cache_file, 'w', encoding='utf-8') as f:
            json.dump(list(self.seen_projects), f, ensure_ascii=False, indent=2)

    def _load_tracking(self) -> dict:
        try:
            if Path(self.tracking_file).exists():
                with open(self.tracking_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception:
            pass
        return {"total_fetched": 0, "total_analyzed": 0, "total_submitted": 0, "total_failed": 0, "projects": {}}

    def _save_tracking(self):
        with open(self.tracking_file, 'w', encoding='utf-8') as f:
            json.dump(self.tracking, f, ensure_ascii=False, indent=2)

    # -- logging -------------------------------------------------------------

    def _log(self, icon: str, message: str, file=None):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        line = f"[{ts}] {icon} {message}"
        print(line, file=file or sys.stdout, flush=True)
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass

    def log_info(self, msg):    self._log("ℹ️ ", msg)
    def log_success(self, msg): self._log("✅", msg)
    def log_warning(self, msg): self._log("⚠️ ", msg)
    def log_error(self, msg):   self._log("❌", msg, file=sys.stderr)

    SEARCH_QUERIES = [
        'python', 'django', 'fastapi', 'ربات', 'تلگرام', 'bot',
        'backend', 'api', 'scraping', 'automation', 'اتوماسیون',
    ]

    # -- fetch ---------------------------------------------------------------

    def _fetch_page(self, query: str, page: int = 1) -> tuple[list, int]:
        try:
            params = {'order': 'newest', 'logged_in': '1', 'page': str(page)}
            if query:
                params['q'] = query
            resp = requests.get(
                self.SEARCH_API, headers=self.headers, cookies=self.cookies,
                params=params, timeout=15,
            )
            resp.encoding = 'utf-8'
            if resp.status_code == 200:
                data = resp.json()
                if data.get("status") == "success":
                    page_data = data.get("data", {})
                    return page_data.get("data", []), page_data.get("last_page", 1)
        except Exception as e:
            self.log_error(f"خطا در دریافت پروژه‌ها (q={query}, page={page}): {e}")
        return [], 1

    def fetch_projects(self) -> list:
        seen_ids = set()
        all_projects = []

        for query in self.SEARCH_QUERIES:
            projects, last_page = self._fetch_page(query, page=1)
            for p in projects:
                pid = p.get('id')
                if pid and pid not in seen_ids:
                    seen_ids.add(pid)
                    all_projects.append(p)

            # صفحه ۲ هم بگیر اگه وجود داره
            if last_page >= 2:
                projects2, _ = self._fetch_page(query, page=2)
                for p in projects2:
                    pid = p.get('id')
                    if pid and pid not in seen_ids:
                        seen_ids.add(pid)
                        all_projects.append(p)

        self.log_info(f"مجموع {len(all_projects)} پروژه یکتا از {len(self.SEARCH_QUERIES)} کوئری دریافت شد")
        return all_projects

    # -- save project --------------------------------------------------------

    def save_project(self, project: dict) -> Path | None:
        try:
            pid = project['id']
            path = self.input_dir / f"project_{pid}.txt"

            skills = project.get('skills', [])
            skills_text = ', '.join(s.get('name', '') for s in skills) if skills else 'مشخص نشده'

            text = (
                f"عنوان: {project.get('title', 'بدون عنوان')}\n\n"
                f"توضیحات:\n{project.get('description', '')}\n\n"
                f"بودجه: {project.get('min_budget', 0):,} تا {project.get('max_budget', 0):,} تومان\n"
                f"زمان: {project.get('job_duration', 'نامشخص')} روز\n"
                f"امتیاز کارفرما: {project.get('rate', 'N/A')}\n"
                f"شهر: {project.get('country', 'نامشخص')}\n\n"
                f"مهارت‌های مورد نیاز:\n{skills_text}\n\n"
                f"لینک پروژه: https://www.karlancer.com/{project.get('url', '')}\n"
            )

            with open(path, 'w', encoding='utf-8') as f:
                f.write(text)
            return path
        except Exception as e:
            self.log_error(f"خطا در ذخیره پروژه {project.get('id')}: {e}")
            return None

    # -- analyze -------------------------------------------------------------

    def analyze_project(self, project_id: int) -> Path | None:
        project_file = self.input_dir / f"project_{project_id}.txt"
        if not project_file.exists():
            self.log_error(f"فایل پروژه {project_id} یافت نشد")
            return None

        prompt_path = Path(self.prompt_file)
        if not prompt_path.exists():
            self.log_error("فایل prompt یافت نشد")
            return None

        system_prompt = prompt_path.read_text(encoding='utf-8')
        project_text = project_file.read_text(encoding='utf-8')

        combined = f"{system_prompt}\n\n{'=' * 80}\n\nاین پروژه جدید از کارلنسر اومده:\n\n{project_text}"

        self.log_info(f"تحلیل پروژه {project_id} با Claude ({self.model})...")

        try:
            result = subprocess.run(
                ['claude', '-p', '--model', self.model],
                input=combined,
                capture_output=True, text=True, timeout=300, encoding='utf-8',
            )

            if result.returncode == 0:
                clean_output = '\n'.join(
                    line for line in result.stdout.split('\n')
                    if not any(x in line.lower() for x in ['trust', 'folder', 'security', '────'])
                )

                if len(clean_output) > 200:
                    output_file = self.output_dir / f"project_{project_id}_analysis.txt"
                    output_file.write_text(
                        f"Project ID: {project_id}\n"
                        f"تاریخ: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
                        f"{'=' * 80}\n\n{clean_output}\n",
                        encoding='utf-8',
                    )
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

        return None

    # -- extract proposal ----------------------------------------------------

    def extract_proposal(self, analysis_file: Path) -> str | None:
        try:
            content = analysis_file.read_text(encoding='utf-8')

            # حذف هدر فایل تحلیل (Project ID, تاریخ, خط جداکننده)
            header_end = content.find('=' * 40)
            if header_end != -1:
                body = content[header_end:].lstrip('= \n')
            else:
                body = content

            # اول سعی کن بخش پروپوزال رو پیدا کنی
            start_markers = ["📝 پروپوزال", "پروپوزال:", "## پروپوزال"]
            start_idx = -1
            for marker in start_markers:
                idx = body.find(marker)
                if idx != -1:
                    start_idx = idx
                    break

            if start_idx != -1:
                end_markers = ["💰 محاسبات", "📊 مقایسه", "با تشکر،\nمبین"]
                end_idx = len(body)
                for marker in end_markers:
                    idx = body.find(marker, start_idx + 50)
                    if idx != -1 and idx < end_idx:
                        end_idx = idx

                proposal = body[start_idx:end_idx].strip()
                lines = proposal.split('\n')
                clean_lines = []
                skip_next = False
                for line in lines:
                    if any(m in line for m in ["📝 پروپوزال", "پروپوزال:", "##", "===", "---"]):
                        skip_next = True
                        continue
                    if skip_next and line.strip() == "":
                        skip_next = False
                        continue
                    clean_lines.append(line)
                result = '\n'.join(clean_lines).strip()
                if result:
                    return result

            # اگه بخش پروپوزال پیدا نشد، کل متن تحلیل رو بفرست
            self.log_warning("بخش پروپوزال پیدا نشد — کل تحلیل ارسال میشه")
            return body.strip() or None

        except Exception as e:
            self.log_error(f"خطا در استخراج پروپوزال: {e}")
            return None

    # -- submit --------------------------------------------------------------

    def submit_proposal(self, project_id: int, project: dict, analysis_file: Path) -> bool:
        proposal = self.extract_proposal(analysis_file)
        if not proposal:
            self.log_error(f"نمی‌توان پروپوزال پروژه {project_id} رو استخراج کرد")
            return False

        # فلگ پروژه‌های بی‌کیفیت
        title = project.get('title', '').lower()
        desc = project.get('description', '').lower()
        min_budget = project.get('min_budget', 0)
        bad_techs = ['wordpress', 'wp', 'woocommerce', 'shopify', 'php']
        is_low_quality = min_budget < 1_000_000 or any(t in title or t in desc for t in bad_techs)

        if is_low_quality:
            self.log_warning(f"پروژه {project_id} بی‌کیفیت - تغییر سلام به SALAM")
            proposal = proposal.replace('سلام', 'SALAM')

        # بودجه و مدت مستقیم از بازه کارفرما
        budget = project.get('min_budget', 2_500_000)
        duration = project.get('job_duration', 7)

        self.log_info(f"📤 ارسال پروپوزال پروژه {project_id} (بودجه: {budget:,} تومان، {duration} روز)")

        payload = {
            "project_id": project_id,
            "bid_id": None,
            "is_pin": False,
            "is_highlight": False,
            "is_multi": False,
            "description": proposal,
            "edit_cart_id": None,
            "milestones": [{"description": "انجام کامل پروژه", "duration": str(duration), "budget": str(budget)}],
        }

        try:
            resp = requests.post(self.BIDS_API, headers=self.submit_headers, cookies=self.cookies, json=payload, timeout=10)
            if resp.status_code in [200, 201]:
                self.log_success(f"پروژه {project_id} با موفقیت ارسال شد!")
                return True
            else:
                self.log_error(f"خطا در ارسال پروژه {project_id}: HTTP {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            self.log_error(f"خطا در ارسال پروپوزال: {e}")
            return False

    # -- process -------------------------------------------------------------

    def process_new_projects(self):
        self.log_info("جستجوی پروژه‌های جدید...")

        all_projects = self.fetch_projects()
        if not all_projects:
            self.log_info("هیچ پروژه‌ای دریافت نشد")
            return

        new_projects = [p for p in all_projects if p.get('id') and p['id'] not in self.seen_projects]
        if not new_projects:
            self.log_info(f"تمام {len(all_projects)} پروژه قبلاً دیده شده‌اند")
            return

        self.log_success(f"🆕 {len(new_projects)} پروژه جدید پیدا شد!")

        if self.tg:
            self.tg.send_new_projects(len(new_projects))

        for idx, project in enumerate(new_projects, 1):
            project_id = project['id']
            title = project.get('title', 'بدون عنوان')

            print("\n" + "=" * 80)
            self.log_info(f"[{idx}/{len(new_projects)}] پروژه {project_id}: {title}")
            print("=" * 80)

            saved = self.save_project(project)
            if not saved:
                self.tracking["total_failed"] += 1
                self._persist(project_id)
                continue

            analysis_file = self.analyze_project(project_id)
            if not analysis_file:
                self.tracking["total_failed"] += 1
                self.tracking["projects"][str(project_id)] = {
                    "title": title, "fetched_at": datetime.now().isoformat(),
                    "analyzed": False, "submitted": False, "error": "Analysis failed",
                }
                self._persist(project_id)
                continue

            self.tracking["total_analyzed"] += 1

            submitted = self.submit_proposal(project_id, project, analysis_file)
            if submitted:
                self.tracking["total_submitted"] += 1
                if self.tg:
                    self.tg.send_project_submitted(project_id, title)
            else:
                self.tracking["total_failed"] += 1

            self.tracking["projects"][str(project_id)] = {
                "title": title, "fetched_at": datetime.now().isoformat(),
                "analyzed": True, "submitted": submitted,
                "analysis_file": str(analysis_file),
            }
            self._persist(project_id)

            if idx < len(new_projects):
                time.sleep(2)

        print("\n" + "=" * 80)
        self.log_success(f"پردازش {len(new_projects)} پروژه تمام شد")
        self._print_stats()
        print("=" * 80 + "\n")

    def _persist(self, project_id: int):
        self.seen_projects.add(project_id)
        self.tracking["total_fetched"] += 1
        self._save_cache()
        self._save_tracking()

    def _print_stats(self):
        t = self.tracking
        self.log_info(
            f"📊 آمار: {t['total_fetched']} دریافت، "
            f"{t['total_analyzed']} تحلیل، "
            f"{t['total_submitted']} ارسال، "
            f"{t['total_failed']} خطا"
        )

    # -- main loop -----------------------------------------------------------

    def run(self, once: bool = False):
        self.log_success("🚀 ربات کارلنسر شروع شد")
        self.log_info(f"⏰ فاصله بررسی: {self.check_interval} ثانیه ({self.check_interval // 60} دقیقه)")
        self.log_info(f"🧠 مدل: {self.model}")
        if self.tg:
            self.log_info("📱 Telegram Logger: فعال")
            self.tg.send_startup(self.check_interval)
        print("=" * 80 + "\n")

        if once:
            self.process_new_projects()
            return

        iteration = 0
        try:
            while True:
                iteration += 1
                self.log_info(f"🔄 چرخه #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                try:
                    self.process_new_projects()
                except Exception as e:
                    self.log_error(f"خطا در پردازش: {e}")

                self.log_info(f"😴 استراحت {self.check_interval} ثانیه تا چرخه بعدی...")
                time.sleep(self.check_interval)

        except KeyboardInterrupt:
            print("\n")
            self.log_warning("⛔ متوقف شد توسط کاربر (Ctrl+C)")
            self._print_stats()
            if self.tg:
                self.tg.send_shutdown(self.tracking)
            self.log_success("👋 خداحافظ!")


# ---------------------------------------------------------------------------
# Setup Telegram (جایگزین get_chat_id.py)
# ---------------------------------------------------------------------------

def setup_telegram():
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    if not bot_token:
        print("❌ TELEGRAM_BOT_TOKEN در .env تنظیم نشده")
        sys.exit(1)

    print("=" * 80)
    print("📱 راهنمای دریافت Chat ID")
    print("=" * 80)
    print("\n📝 مراحل:")
    print("  1. به بات تلگرام خودت برو")
    print("  2. دکمه /start رو بزن")
    print("  3. یک پیام دلخواه بفرست (مثلا: سلام)")
    print()
    input("⏸️  وقتی پیام رو فرستادی، Enter رو بزن...")

    try:
        resp = requests.get(f"https://api.telegram.org/bot{bot_token}/getUpdates", timeout=10)
        if resp.status_code != 200:
            print(f"❌ خطا: {resp.status_code}")
            sys.exit(1)

        updates = resp.json().get('result', [])
        if not updates:
            print("❌ هیچ پیامی پیدا نشد! لطفا به بات پیام بفرست و دوباره امتحان کن.")
            sys.exit(1)

        chat = updates[-1].get('message', {}).get('chat', {})
        chat_id = chat.get('id')
        print(f"\n✅ Chat ID پیدا شد: {chat_id}")
        print(f"👤 نام: {chat.get('first_name', 'N/A')}")

        with open('.telegram_chat_id', 'w') as f:
            f.write(str(chat_id))
        print("💾 Chat ID در فایل .telegram_chat_id ذخیره شد")

    except Exception as e:
        print(f"❌ خطا: {e}")
        sys.exit(1)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description='ربات خودکار کارلنسر')
    parser.add_argument('--interval', type=int, default=300,
                        help='فاصله زمانی بررسی بر حسب ثانیه (پیش‌فرض: 300)')
    parser.add_argument('--model', type=str, default='sonnet',
                        help='مدل Claude برای تحلیل (پیش‌فرض: sonnet)')
    parser.add_argument('--once', action='store_true',
                        help='فقط یک بار اجرا بشه (بدون loop)')
    parser.add_argument('--telegram-chat-id', type=str,
                        help='Chat ID تلگرام')
    parser.add_argument('--setup-telegram', action='store_true',
                        help='دریافت Chat ID تلگرام')
    args = parser.parse_args()

    if args.setup_telegram:
        setup_telegram()
        return

    bearer = os.environ.get("KARELANCER_BEARER")
    if not bearer:
        print("❌ KARELANCER_BEARER در .env تنظیم نشده")
        sys.exit(1)

    # تلگرام
    tg = None
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = args.telegram_chat_id

    if not chat_id and Path('.telegram_chat_id').exists():
        try:
            chat_id = Path('.telegram_chat_id').read_text().strip()
            print(f"📱 Chat ID از فایل خوانده شد: {chat_id}")
        except Exception:
            pass

    if chat_id and bot_token:
        tg = TelegramLogger(bot_token, chat_id)
        print("🧪 تست اتصال به تلگرام...")
        if not tg.test_connection():
            print("⚠️  خطا در اتصال - ادامه بدون Telegram")
            tg = None
        else:
            print("✅ Telegram Logger فعال شد!")
    else:
        print("ℹ️  Telegram Logger غیرفعال (برای فعال‌سازی: python3 karlancer.py --setup-telegram)")

    bot = Karlancer(bearer_token=bearer, check_interval=args.interval, model=args.model, tg=tg)
    bot.run(once=args.once)


if __name__ == "__main__":
    main()
