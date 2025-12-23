"""
ارسال خودکار proposal به کارلنسر
"""

import os
import json
import requests
from pathlib import Path

class ProposalSubmitter:
    """ارسال proposal به کارلنسر"""
    
    def __init__(self, bearer_token: str):
        self.bearer_token = bearer_token
        self.api_url = "https://www.karlancer.com/api/bids"
        
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
    
    def submit_proposal(
        self,
        project_id: int,
        description: str,
        milestones: list = None,
        is_pin: bool = False,
        is_highlight: bool = False
    ):
        """ارسال proposal"""
        
        # Milestones پیش‌فرض
        if milestones is None:
            milestones = [
                {
                    "description": "پیش پرداخت",
                    "duration": "1",
                    "budget": "1000000"
                }
            ]
        
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
            response = requests.post(
                self.api_url,
                headers=self.headers,
                cookies=self.cookies,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                return {
                    'success': True,
                    'data': response.json()
                }
            else:
                return {
                    'success': False,
                    'error': f"HTTP {response.status_code}: {response.text}"
                }
        
        except Exception as e:
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
            # معمولاً بین "📝 پروپوزال" و بخش بعدی
            
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
                
                # پیدا کردن پایان (بخش بعدی)
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
        import re
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
        result = submitter.submit_proposal(project_id, proposal)
        
        if result['success']:
            print("✅ Proposal submitted successfully!")
        else:
            print(f"❌ Failed: {result['error']}")
    else:
        print("❌ Cancelled")

if __name__ == "__main__":
    main()