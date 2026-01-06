#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ارسال خودکار proposal به کارلنسر
نسخه بهبود یافته با auto-detect بودجه
"""

import os
import sys
import json
import re
import requests
from pathlib import Path

# تنظیم encoding
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')


class ProposalSubmitter:
    """ارسال proposal به کارلنسر"""

    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.api_url = "https://www.karlancer.com/api/bids"
        self.project_api_url = "https://www.karlancer.com/api/publics/projects"

        self.headers = {
            'accept': 'application/json',
            'accept-language': 'en-US,en;q=0.9',
            'authorization': f'Bearer {bearer_token}',
            'content-type': 'application/json',
            'origin': 'https://www.karlancer.com',
            'referer': 'https://www.karlancer.com/',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }

        self.cookies = {
            'eloquent_viewable': 'kRB3L7zZ1gj5ampde5QBLbXj9Am0xrJMZGKwnYJjlmNvg87k4Wa3qlORNyPVYEzD1oAoYNpeQrD9dq8G',
            'G_ENABLED_IDPS': 'google',
            '_ga': 'GA1.1.1605194695.1763027354',
            '_ga_3VNDP3F9HF': 'GS2.1.s1766478188$o15$g1$t1766478885$j13$l0$h0'
        }

    def get_project_info(self, project_id: int):
        """دریافت اطلاعات پروژه از API"""
        try:
            url = f"{self.project_api_url}/{project_id}"
            print(f"🔍 دریافت اطلاعات پروژه {project_id} از API...")

            response = requests.get(
                url,
                headers=self.headers,
                cookies=self.cookies,
                timeout=10
            )

            print(f"📊 API Response Status: {response.status_code}")

            if response.status_code == 200:
                data = response.json()
                print(f"📦 API Response: {json.dumps(data, ensure_ascii=False)[:200]}...")

                if data.get("status") == "success":
                    project = data.get("data")
                    if project:
                        min_budget = project.get('min_budget', 0)
                        max_budget = project.get('max_budget', 0)
                        job_duration = project.get('job_duration', 1)

                        print(f"✅ بودجه از API: {min_budget:,} - {max_budget:,} تومان")
                        print(f"✅ مدت زمان: {job_duration} روز")

                        return {
                            'min_budget': min_budget,
                            'max_budget': max_budget,
                            'job_duration': job_duration
                        }
                    else:
                        print("⚠️  فیلد 'data' خالی است")
                else:
                    print(f"⚠️  وضعیت API: {data.get('status')}")
            else:
                print(f"❌ خطای HTTP: {response.status_code}")
                print(f"Response: {response.text[:200]}")

        except Exception as e:
            print(f"❌ خطا در دریافت اطلاعات پروژه از API: {e}")
            import traceback
            traceback.print_exc()

        return None

    def extract_budget_from_analysis(self, analysis_file: str):
        """استخراج بودجه از فایل تحلیل"""
        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # جستجوی الگوهای بودجه
            patterns = [
                r'بودجه[:\s]+(\d{1,3}(?:[,،]\d{3})*)\s*(?:تا|-)\s*(\d{1,3}(?:[,،]\d{3})*)\s*تومان',
                r'Budget[:\s]+(\d{1,3}(?:[,،]\d{3})*)\s*(?:to|-)\s*(\d{1,3}(?:[,،]\d{3})*)',
                r'min_budget[:\s]+(\d+)',
            ]

            for pattern in patterns:
                match = re.search(pattern, content, re.IGNORECASE)
                if match:
                    # حذف جداکننده‌ها
                    min_budget = int(match.group(1).replace(',', '').replace('،', ''))
                    if len(match.groups()) > 1:
                        max_budget = int(match.group(2).replace(',', '').replace('،', ''))
                    else:
                        max_budget = min_budget

                    return {
                        'min_budget': min_budget,
                        'max_budget': max_budget,
                        'job_duration': 7  # پیش‌فرض
                    }

        except Exception as e:
            print(f"⚠️  خطا در استخراج بودجه از فایل: {e}")

        return None

    def create_milestones(self, project_id: int, analysis_file: str = None):
        """ساخت milestone با بودجه صحیح"""

        # روش 1: دریافت از API
        project_info = self.get_project_info(project_id)

        # بررسی اینکه بودجه معتبر باشه
        if project_info and project_info.get('min_budget', 0) > 0:
            budget = project_info['min_budget']
            duration = project_info.get('job_duration', 7)
            print(f"✅ استفاده از بودجه API: {budget:,} تومان")
        else:
            # روش 2: استخراج از فایل تحلیل
            if analysis_file:
                print("⚠️  API موفق نبود، تلاش برای استخراج از فایل تحلیل...")
                file_info = self.extract_budget_from_analysis(analysis_file)
                if file_info and file_info.get('min_budget', 0) > 0:
                    budget = file_info['min_budget']
                    duration = file_info.get('job_duration', 7)
                    print(f"✅ استفاده از بودجه فایل: {budget:,} تومان")
                else:
                    # روش 3: مقادیر پیش‌فرض - بودجه بالاتر برای جلوگیری از خطا
                    budget = 5000000  # افزایش به 5M برای جلوگیری از خطای validation
                    duration = 7
                    print(f"⚠️  استفاده از بودجه پیش‌فرض: {budget:,} تومان")
            else:
                # روش 3: مقادیر پیش‌فرض
                budget = 5000000
                duration = 7
                print(f"⚠️  استفاده از بودجه پیش‌فرض: {budget:,} تومان")

        print(f"💰 بودجه نهایی milestone: {budget:,} تومان")
        print(f"⏱️  مدت زمان: {duration} روز")

        return [
            {
                "description": "انجام کامل پروژه",
                "duration": str(duration),
                "budget": str(budget)
            }
        ]

    def submit_proposal(
        self,
        project_id: int,
        description: str,
        analysis_file: str = None,
        is_pin: bool = False,
        is_highlight: bool = False
    ):
        """ارسال proposal"""

        # ساخت milestone با بودجه صحیح
        milestones = self.create_milestones(project_id, analysis_file)

        payload = {
            "project_id": project_id,
            "bid_id": None,
            "is_pin": is_pin,
            "is_highlight": is_highlight,
            "is_multi": False,
            "description": description,
            "edit_cart_id": None,
            "milestones": milestones
        }

        try:
            print(f"📤 ارسال proposal به API...")
            print(f"📋 Project ID: {project_id}")
            print(f"💰 Budget: {milestones[0]['budget']} تومان")

            response = requests.post(
                self.api_url,
                headers=self.headers,
                cookies=self.cookies,
                json=payload,
                timeout=10
            )

            print(f"📊 Submit Response Status: {response.status_code}")

            if response.status_code in [200, 201]:
                result_data = response.json()
                print(f"✅ موفق: {json.dumps(result_data, ensure_ascii=False)[:200]}")
                return {
                    'success': True,
                    'data': result_data
                }
            else:
                error_text = response.text
                print(f"❌ خطا: {error_text}")

                # تلاش برای parse کردن JSON error
                try:
                    error_json = response.json()
                    error_msg = error_json.get('message', error_text)
                except:
                    error_msg = error_text

                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {error_msg}"
                }

        except Exception as e:
            print(f"❌ Exception در submit: {e}")
            import traceback
            traceback.print_exc()
            return {
                'success': False,
                'error': str(e)
            }

    def extract_proposal_from_analysis(self, analysis_file: str):
        """استخراج proposal از فایل تحلیل"""

        try:
            with open(analysis_file, 'r', encoding='utf-8') as f:
                content = f.read()

            # پیدا کردن بخش پروپوزال
            if "📝 پروپوزال" in content or "پروپوزال" in content:
                # پیدا کردن شروع
                start_markers = ["📝 پروپوزال", "پروپوزال:", "## پروپوزال"]
                start_idx = -1

                for marker in start_markers:
                    idx = content.find(marker)
                    if idx != -1:
                        start_idx = idx
                        break

                if start_idx == -1:
                    return None

                # پیدا کردن پایان
                end_markers = ["💰 محاسبات", "📊 مقایسه", "با تشکر،\nمبین"]
                end_idx = len(content)

                for marker in end_markers:
                    idx = content.find(marker, start_idx + 50)
                    if idx != -1 and idx < end_idx:
                        end_idx = idx

                # استخراج
                proposal = content[start_idx:end_idx].strip()

                # حذف header
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

                return '\n'.join(clean_lines).strip()

            return None

        except Exception as e:
            print(f"❌ Error extracting proposal: {e}")
            return None

    def extract_project_id(self, filename: str):
        """استخراج Project ID از نام فایل"""
        match = re.search(r'project_(\d+)', filename)
        if match:
            return int(match.group(1))
        return None


def main():
    """تست"""
    import sys

    if len(sys.argv) < 2:
        print("Usage: python submit_proposal.py <analysis_file>")
        sys.exit(1)

    analysis_file = sys.argv[1]

    BEARER_TOKEN = "2639199|WDj6UAvuCppotknYzIAvzaSBx1h9BPS151eVLgAwBL8HwQBeLGKXio5sSowHy97UrTdcIzViXQCUlX6ZA6SOy6JTGZmeuDME2dNESKGOUtBsqtpm5B3GeHCs6sJmhdxA2dUrmHQrcr7X24OcMOtfj7xpiO5sxoOiq0r9QfSMeDVsLtoXRus1rmbXlbMAmoTVzVlx5W7WHfdfpWElBtAVXuvWXWXomsMU1pMfTVhPaVZ1gkjC7NSUTpIi0SB16VfKtG7INfgosHBP8Z9ojB1g0cfQCdvRAjsxfbfwoW6zBI98D1xIKJn6mVas4jtFgBJRO5IXktQ0i77R0KANlIqlfZDPwMzklBCYR11U4SmDVrQ3diENQhCeV6F8Bcw2nQw6YB3sdJRXCRAktn6lg5cAGPL3h09RXo4KBGLYnNvgdMcTKQw9912ouaalBsE2jyJeogFI6J5uoL9MlSQfnvQlx2BFqePqAzF5vIDnJ8ck1kvpBxcJHZdkno8yhTHjrLfcU8HE0gI34pbr8NiGNR6WB5uBtXII"

    submitter = ProposalSubmitter(BEARER_TOKEN)

    # استخراج project ID
    project_id = submitter.extract_project_id(analysis_file)

    if not project_id:
        print("❌ Could not extract project ID from filename")
        sys.exit(1)

    print(f"📋 Project ID: {project_id}")

    # استخراج proposal
    proposal = submitter.extract_proposal_from_analysis(analysis_file)

    if not proposal:
        print("❌ Could not extract proposal from analysis")
        sys.exit(1)

    print(f"✅ Extracted proposal ({len(proposal)} chars)")
    print("\nProposal preview:")
    print(proposal[:200] + "...")
    print()

    # تأیید
    confirm = input("Submit this proposal? (y/N): ")

    if confirm.lower() == 'y':
        print("📤 Submitting...")
        result = submitter.submit_proposal(
            project_id=project_id,
            description=proposal,
            analysis_file=analysis_file
        )

        if result['success']:
            print("✅ Proposal submitted successfully!")
            print(f"📝 Response: {result['data']}")
        else:
            print(f"❌ Failed: {result['error']}")
    else:
        print("❌ Cancelled")


if __name__ == "__main__":
    main()
