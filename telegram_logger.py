#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Telegram Logger - ارسال لاگ‌ها به بات تلگرام
"""

import requests
import json
from datetime import datetime
from typing import Optional


class TelegramLogger:
    """لاگر تلگرام"""

    def __init__(self, bot_token: str, chat_id: str, enabled: bool = True):
        """
        مقداردهی اولیه

        Args:
            bot_token: توکن بات تلگرام
            chat_id: آیدی چت (عدد یا username با @)
            enabled: فعال/غیرفعال (پیش‌فرض: فعال)
        """
        self.bot_token = bot_token
        self.chat_id = chat_id
        self.enabled = enabled
        self.api_url = f"https://api.telegram.org/bot{bot_token}"

    def send_message(self, text: str, parse_mode: str = "HTML") -> bool:
        """
        ارسال پیام به تلگرام

        Args:
            text: متن پیام
            parse_mode: HTML یا Markdown

        Returns:
            True اگه موفق، False اگه ناموفق
        """
        if not self.enabled:
            return False

        try:
            url = f"{self.api_url}/sendMessage"
            payload = {
                "chat_id": self.chat_id,
                "text": text,
                "parse_mode": parse_mode,
                "disable_web_page_preview": True
            }

            response = requests.post(url, json=payload, timeout=10)

            if response.status_code == 200:
                return True
            else:
                print(f"⚠️  خطا در ارسال به تلگرام: {response.status_code} - {response.text}")
                return False

        except Exception as e:
            print(f"⚠️  خطا در ارسال به تلگرام: {e}")
            return False

    def send_startup(self, interval: int, auto_submit: bool, min_stars: int, strict_mode: bool):
        """ارسال پیام شروع"""
        text = f"""
🚀 <b>ربات کارلنسر شروع شد</b>

⏰ فاصله بررسی: {interval} ثانیه ({interval // 60} دقیقه)
📤 ارسال خودکار: {'✅ فعال' if auto_submit else '❌ غیرفعال'}
⭐ حداقل امتیاز: {'⭐' * min_stars} ({min_stars}/5)
🔒 حالت: {'🔴 Strict' if strict_mode else '🟢 Normal'}

📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(text.strip())

    def send_new_projects(self, count: int):
        """اطلاع از پروژه‌های جدید"""
        text = f"""
🆕 <b>{count} پروژه جدید پیدا شد!</b>

در حال تحلیل...
"""
        self.send_message(text.strip())

    def send_project_analyzed(self, project_id: int, title: str, stars: int, decision: str):
        """اطلاع از تحلیل پروژه"""
        emoji = "✅" if stars >= 3 else "⚠️"
        decision_emoji = {
            "Take": "✅",
            "Skip": "❌",
            "Negotiate": "🤔",
            None: "❓"
        }.get(decision, "❓")

        text = f"""
{emoji} <b>پروژه تحلیل شد</b>

📋 ID: {project_id}
📌 عنوان: {title[:50]}{"..." if len(title) > 50 else ""}

⭐ امتیاز: {'⭐' * stars} ({stars}/5)
📊 توصیه: {decision_emoji} {decision or 'نامشخص'}
"""
        self.send_message(text.strip())

    def send_project_submitted(self, project_id: int, title: str):
        """اطلاع از ارسال موفق"""
        text = f"""
✅ <b>پروپوزال ارسال شد!</b>

📋 ID: {project_id}
📌 {title[:50]}{"..." if len(title) > 50 else ""}

🔗 لینک: https://www.karlancer.com/project/{project_id}
"""
        self.send_message(text.strip())

    def send_project_rejected(self, project_id: int, title: str, reason: str):
        """اطلاع از رد پروژه"""
        text = f"""
🚫 <b>پروژه رد شد</b>

📋 ID: {project_id}
📌 {title[:50]}{"..." if len(title) > 50 else ""}

❌ دلیل: {reason}
"""
        self.send_message(text.strip())

    def send_cycle_summary(self, iteration: int, total_fetched: int, total_analyzed: int,
                          total_submitted: int, total_failed: int):
        """خلاصه چرخه"""
        text = f"""
📊 <b>خلاصه چرخه #{iteration}</b>

🔍 دریافت شده: {total_fetched}
🧠 تحلیل شده: {total_analyzed}
📤 ارسال شده: {total_submitted}
❌ خطا: {total_failed}

📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(text.strip())

    def send_error(self, error_msg: str):
        """ارسال خطا"""
        text = f"""
❌ <b>خطا رخ داد</b>

{error_msg}

📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(text.strip())

    def send_shutdown(self, total_fetched: int, total_analyzed: int,
                     total_submitted: int, total_failed: int):
        """پیام خاموش شدن"""
        text = f"""
⛔ <b>ربات متوقف شد</b>

📊 آمار نهایی:
  🔍 دریافت‌ها: {total_fetched}
  🧠 تحلیل‌ها: {total_analyzed}
  📤 ارسال‌ها: {total_submitted}
  ❌ خطاها: {total_failed}

👋 خداحافظ!
📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
        self.send_message(text.strip())

    def test_connection(self) -> bool:
        """تست اتصال به بات"""
        try:
            url = f"{self.api_url}/getMe"
            response = requests.get(url, timeout=5)

            if response.status_code == 200:
                data = response.json()
                bot_info = data.get('result', {})
                bot_name = bot_info.get('first_name', 'Unknown')
                print(f"✅ اتصال به بات موفق: {bot_name}")

                # ارسال پیام تست
                test_msg = f"""
🧪 <b>تست اتصال موفق</b>

بات: {bot_name}
Chat ID: {self.chat_id}

📅 {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""
                return self.send_message(test_msg.strip())
            else:
                print(f"❌ خطا در اتصال به بات: {response.status_code}")
                return False

        except Exception as e:
            print(f"❌ خطا در تست اتصال: {e}")
            return False


def main():
    """تست logger"""
    import sys

    if len(sys.argv) < 3:
        print("Usage: python3 telegram_logger.py <bot_token> <chat_id>")
        sys.exit(1)

    bot_token = sys.argv[1]
    chat_id = sys.argv[2]

    logger = TelegramLogger(bot_token, chat_id)

    print("🧪 تست اتصال...")
    if logger.test_connection():
        print("✅ تست موفق!")
        print("\nمثال‌های دیگر:")
        logger.send_startup(300, True, 4, False)
        logger.send_new_projects(3)
        logger.send_project_analyzed(12345, "ساخت ربات تلگرام", 4, "Take")
        logger.send_project_submitted(12345, "ساخت ربات تلگرام")
        logger.send_cycle_summary(1, 5, 3, 2, 0)
    else:
        print("❌ تست ناموفق!")
        sys.exit(1)


if __name__ == "__main__":
    main()
