#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
دریافت Chat ID از بات تلگرام
"""

import requests
import sys

def get_chat_id(bot_token):
    """دریافت Chat ID"""

    print("=" * 80)
    print("🤖 راهنمای دریافت Chat ID")
    print("=" * 80)
    print()
    print("📝 مراحل:")
    print("  1. به بات تلگرام خودت برو")
    print("  2. دکمه /start رو بزن")
    print("  3. یک پیام دلخواه بفرست (مثلا: سلام)")
    print("  4. منتظر بمون تا این اسکریپت Chat ID رو پیدا کنه...")
    print()
    print("=" * 80)

    input("⏸️  وقتی پیام رو فرستادی، Enter رو بزن...")

    try:
        url = f"https://api.telegram.org/bot{bot_token}/getUpdates"
        response = requests.get(url, timeout=10)

        if response.status_code == 200:
            data = response.json()
            updates = data.get('result', [])

            if not updates:
                print("❌ هیچ پیامی پیدا نشد!")
                print("   لطفا به بات برو و یک پیام بفرست، بعد دوباره این اسکریپت رو اجرا کن.")
                return None

            # آخرین update
            last_update = updates[-1]
            message = last_update.get('message', {})
            chat = message.get('chat', {})
            chat_id = chat.get('id')
            username = chat.get('username', 'N/A')
            first_name = chat.get('first_name', 'N/A')

            print()
            print("✅ Chat ID پیدا شد!")
            print("=" * 80)
            print(f"📋 Chat ID: {chat_id}")
            print(f"👤 نام: {first_name}")
            print(f"🔗 Username: @{username}" if username != 'N/A' else "")
            print("=" * 80)
            print()
            print("💾 این Chat ID رو ذخیره کن!")
            print()

            # ذخیره در فایل
            with open('.telegram_chat_id', 'w') as f:
                f.write(str(chat_id))

            print(f"✅ Chat ID در فایل .telegram_chat_id ذخیره شد")

            return chat_id

        else:
            print(f"❌ خطا: {response.status_code}")
            print(response.text)
            return None

    except Exception as e:
        print(f"❌ خطا: {e}")
        return None


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 get_chat_id.py <bot_token>")
        print()
        print("Example:")
        print("  python3 get_chat_id.py 8479753307:AAEOOUbyv6Jun5fZKb73dpKEsMLL8xAUub4")
        sys.exit(1)

    bot_token = sys.argv[1]
    chat_id = get_chat_id(bot_token)

    if chat_id:
        print()
        print("🚀 حالا میتونی بات رو تست کنی:")
        print(f"   python3 telegram_logger.py {bot_token} {chat_id}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
