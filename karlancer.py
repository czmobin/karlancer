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
# Claude CLI helper (rate-limit aware)
# ---------------------------------------------------------------------------

def run_claude(model: str, prompt: str, timeout: int = 300, log_fn=None) -> subprocess.CompletedProcess | None:
    while True:
        try:
            result = subprocess.run(
                ['claude', '-p', '--model', model],
                input=prompt, capture_output=True, text=True,
                timeout=timeout, encoding='utf-8',
            )
        except subprocess.TimeoutExpired:
            if log_fn:
                log_fn(f"Timeout Claude CLI ({timeout}s)")
            return None
        except Exception as e:
            if log_fn:
                log_fn(f"خطا در اجرای Claude: {e}")
            return None

        err = result.stderr.lower()
        if result.returncode != 0 and ('rate limit' in err or '429' in err or 'too many' in err or 'overloaded' in err):
            wait = 60
            m = re.search(r'(\d+)\s*(?:second|ثانیه|sec)', output)
            if m:
                wait = int(m.group(1)) + 5
            else:
                m = re.search(r'(\d+)\s*(?:minute|دقیقه|min)', output)
                if m:
                    wait = int(m.group(1)) * 60 + 5
            ts = datetime.now().strftime('%H:%M:%S')
            print(f"[{ts}] ⏳ Claude rate limit — خواب {wait} ثانیه...", flush=True)
            if log_fn:
                log_fn(f"Claude rate limit — خواب {wait} ثانیه")
            time.sleep(wait)
            continue

        return result


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
# Chat Manager
# ---------------------------------------------------------------------------

class ChatManager:

    ROOMS_API = "https://www.karlancer.com/api/rooms/"
    MESSAGES_API_TPL = "https://www.karlancer.com/api/rooms/{}/messages-pg"
    SEND_API = "https://www.karlancer.com/api/messages"
    MY_USER_ID = 100660

    GITHUB_API = "https://api.github.com"

    def __init__(self, headers: dict, submit_headers: dict, cookies: dict,
                 model: str = "sonnet", tg: TelegramLogger = None,
                 github_token: str = ""):
        self.headers = headers
        self.submit_headers = submit_headers
        self.cookies = cookies
        self.model = model
        self.tg = tg
        self.github_token = github_token
        self.github_user = "czmobin"

        self.chats_dir = Path("chats")
        self.chats_dir.mkdir(exist_ok=True)
        self.chat_prompt = self._load_chat_prompt()
        self.deploy_prompt = self._load_deploy_prompt()

    def _load_chat_prompt(self) -> str:
        path = Path("chat_prompt.txt")
        if path.exists():
            return path.read_text(encoding='utf-8')
        return ""

    def _load_deploy_prompt(self) -> str:
        path = Path("deploy_prompt.txt")
        if path.exists():
            return path.read_text(encoding='utf-8')
        return ""

    # -- logging (standalone) ---------------------------------------------------

    def _log(self, level: str, msg: str):
        ts = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        icons = {"info": "INFO", "success": "OK", "warning": "WARN", "error": "ERR"}
        tag = icons.get(level, "---")
        line = f"[{ts}] [{tag}] [chat] {msg}"
        print(line, flush=True)
        try:
            with open("karlancer.log", 'a', encoding='utf-8') as f:
                f.write(line + '\n')
        except Exception:
            pass

    # -- API helpers ------------------------------------------------------------

    def _fetch_rooms(self, pages: int = 2) -> list:
        rooms = []
        for page in range(1, pages + 1):
            try:
                resp = requests.get(
                    self.ROOMS_API, headers=self.headers, cookies=self.cookies,
                    params={"page": page}, timeout=15,
                )
                if resp.status_code == 200:
                    data = resp.json().get("data", {}).get("data", [])
                    rooms.extend(data)
            except Exception as e:
                self._log("error", f"دریافت اتاق‌ها صفحه {page}: {e}")
        return rooms

    def _fetch_messages(self, room_id: int) -> tuple:
        try:
            resp = requests.get(
                self.MESSAGES_API_TPL.format(room_id),
                headers=self.headers, cookies=self.cookies,
                params={"page": 1}, timeout=15,
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                messages = data.get("messages", {}).get("data", [])
                projects = data.get("workdiary_projects", [])
                return messages, projects
        except Exception as e:
            self._log("error", f"دریافت پیام‌های اتاق {room_id}: {e}")
        return [], []

    def _send_message(self, room_id: int, receptor_id: int, message: str) -> bool:
        try:
            resp = requests.post(
                self.SEND_API, headers=self.submit_headers, cookies=self.cookies,
                json={"receptor_id": receptor_id, "room_id": room_id,
                      "message": message, "file": ""},
                timeout=10,
            )
            return resp.status_code in (200, 201)
        except Exception as e:
            self._log("error", f"ارسال پیام به اتاق {room_id}: {e}")
            return False

    # -- state persistence ------------------------------------------------------

    def _room_dir(self, room_id: int) -> Path:
        d = self.chats_dir / str(room_id)
        d.mkdir(exist_ok=True)
        return d

    def _load_state(self, room_dir: Path) -> dict:
        sf = room_dir / "state.json"
        if sf.exists():
            try:
                with open(sf, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return {"last_responded_msg_id": 0, "status": "active"}

    def _save_state(self, room_dir: Path, state: dict):
        with open(room_dir / "state.json", 'w', encoding='utf-8') as f:
            json.dump(state, f, ensure_ascii=False, indent=2)

    # -- context building -------------------------------------------------------

    def _get_project_context(self, projects: list) -> str:
        if not projects:
            return ""
        project = projects[0]
        pid = project.get("project_id")
        title = project.get("title", "")
        input_file = Path(f"claude_input/project_{pid}.txt")
        if input_file.exists():
            return f"اطلاعات پروژه:\n{input_file.read_text(encoding='utf-8')}"
        return f"پروژه: {title}" if title else ""

    def _get_proposal_context(self, projects: list) -> str:
        if not projects:
            return ""
        pid = projects[0].get("project_id")
        analysis_file = Path(f"proposals/project_{pid}_analysis.txt")
        if analysis_file.exists():
            content = analysis_file.read_text(encoding='utf-8')
            marker = "پروپوزال"
            idx = content.find(marker)
            if idx != -1:
                proposal = content[idx:idx + 2000]
                return f"پروپوزال ارسال‌شده:\n{proposal}"
        return ""

    def _format_conversation(self, messages: list) -> str:
        lines = []
        for msg in reversed(messages):
            role = "من" if msg["sender_id"] == self.MY_USER_ID else "کارفرما"
            text = msg.get("message") or ""
            if msg.get("file"):
                fname = msg["file"].get("name", "فایل")
                text += f" [فایل: {fname}]"
            lines.append(f"{role}: {text}")
        return "\n".join(lines)

    # -- GitHub repo management -------------------------------------------------

    def _slugify(self, text: str, max_len: int = 40) -> str:
        text = re.sub(r'[^\x00-\x7F]', '', text)   # فقط ASCII
        text = re.sub(r'[^\w\s-]', '', text)
        text = re.sub(r'[\s_]+', '-', text.strip())
        return text[:max_len].strip('-').lower() or 'project'

    def _create_repo(self, project_title: str, project_desc: str) -> str | None:
        if not self.github_token:
            self._log("warning", "GITHUB_TOKEN نیست — ریپو ساخته نشد")
            return None

        slug = self._slugify(project_title)
        repo_name = f"kar-{slug}" if slug != 'project' else f"kar-{abs(hash(project_title)) % 100000}"
        gh_headers = {
            "Authorization": f"token {self.github_token}",
            "Accept": "application/vnd.github.v3+json",
        }

        try:
            resp = requests.post(
                f"{self.GITHUB_API}/user/repos", headers=gh_headers,
                json={"name": repo_name, "private": True,
                      "description": project_desc[:200], "auto_init": True},
                timeout=15,
            )
            if resp.status_code == 201:
                self._log("success", f"ریپو ساخته شد: {repo_name}")
                return repo_name
            elif resp.status_code == 422:
                self._log("info", f"ریپو {repo_name} قبلا وجود داره")
                return repo_name
            else:
                self._log("error", f"ساخت ریپو: HTTP {resp.status_code} {resp.text[:200]}")
        except Exception as e:
            self._log("error", f"ساخت ریپو: {e}")
        return None

    def _generate_initial_code(self, repo_name: str, project_ctx: str,
                               room_dir: Path) -> bool:
        repo_path = room_dir / "repo"
        if repo_path.exists():
            return True

        prompt = (
            "بر اساس توضیحات پروژه زیر، یک ساختار اولیه پروژه پایتون بساز.\n"
            "فقط فایل‌های کد رو بنویس، هر فایل رو با === filename === مشخص کن.\n"
            "ساختار ساده و MVP باشه. README.md فارسی بنویس.\n\n"
            f"{project_ctx}"
        )

        result = run_claude(self.model, prompt, timeout=180,
                            log_fn=lambda msg: self._log("error", msg))
        if not result or result.returncode != 0:
            self._log("error", "تولید کد اولیه ناموفق")
            return False

        raw = result.stdout.strip()

        try:
            repo_path.mkdir(parents=True, exist_ok=True)
            current_file = None
            current_content = []

            for line in raw.split('\n'):
                if line.strip().startswith('=== ') and line.strip().endswith(' ==='):
                    if current_file:
                        fpath = repo_path / current_file
                        fpath.parent.mkdir(parents=True, exist_ok=True)
                        fpath.write_text('\n'.join(current_content), encoding='utf-8')
                    current_file = line.strip().strip('= ').strip()
                    current_content = []
                elif line.strip().startswith('```'):
                    continue
                else:
                    current_content.append(line)

            if current_file:
                fpath = repo_path / current_file
                fpath.parent.mkdir(parents=True, exist_ok=True)
                fpath.write_text('\n'.join(current_content), encoding='utf-8')

            if not any(repo_path.iterdir()):
                (repo_path / "main.py").write_text("# MVP\n", encoding='utf-8')
                (repo_path / "README.md").write_text("# پروژه\n", encoding='utf-8')

            self._log("success", f"کد اولیه تولید شد: {repo_path}")
            return True
        except Exception as e:
            self._log("error", f"ذخیره کد اولیه: {e}")
            return False

    def _push_to_repo(self, repo_name: str, room_dir: Path) -> bool:
        repo_path = room_dir / "repo"
        if not repo_path.exists():
            return False

        repo_url = f"git@github.com:{self.github_user}/{repo_name}.git"

        try:
            cmds = [
                ['git', 'init'],
                ['git', 'checkout', '-b', 'main'],
                ['git', 'add', '.'],
                ['git', 'commit', '-m', 'Initial MVP'],
                ['git', 'remote', 'add', 'origin', repo_url],
                ['git', 'push', '-u', 'origin', 'main', '--force'],
            ]
            for cmd in cmds:
                r = subprocess.run(cmd, cwd=repo_path, capture_output=True,
                                   text=True, timeout=30)
                if r.returncode != 0 and 'already exists' not in r.stderr:
                    if cmd[1] not in ('remote',):
                        self._log("error", f"git {cmd[1]}: {r.stderr[:200]}")
                        return False

            self._log("success", f"کد به {repo_name} پوش شد")
            return True
        except Exception as e:
            self._log("error", f"پوش به ریپو: {e}")
            return False

    def _setup_repo_for_room(self, room_id: int, state: dict,
                              room_dir: Path, projects: list,
                              project_ctx: str) -> str | None:
        if state.get("repo_name"):
            return state["repo_name"]

        if not projects:
            return None

        title = projects[0].get("title", f"project-{room_id}")
        desc = project_ctx[:200] if project_ctx else title

        repo_name = self._create_repo(title, desc)
        if not repo_name:
            return None

        if self._generate_initial_code(repo_name, project_ctx, room_dir):
            self._push_to_repo(repo_name, room_dir)

        state["repo_name"] = repo_name
        return repo_name

    # -- SSH deploy -------------------------------------------------------------

    def _ssh_deploy(self, ip: str, user: str, password: str, repo_name: str) -> str | None:
        try:
            import paramiko
        except ImportError:
            self._log("error", "paramiko نصب نیست: pip install paramiko")
            return None

        repo_url = f"https://github.com/{self.github_user}/{repo_name}.git"
        deploy_dir = f"/root/{repo_name}"
        commands = [
            f"rm -rf {deploy_dir}",
            f"git clone {repo_url} {deploy_dir}",
            f"cd {deploy_dir} && pip3 install -r requirements.txt -q 2>/dev/null || true",
            f"ls {deploy_dir}",
        ]

        try:
            ssh = paramiko.SSHClient()
            ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            ssh.connect(ip, username=user, password=password, timeout=30)

            output_lines = []
            for cmd in commands:
                _, stdout, stderr = ssh.exec_command(cmd, timeout=60)
                out = stdout.read().decode('utf-8', errors='replace').strip()
                err = stderr.read().decode('utf-8', errors='replace').strip()
                if out:
                    output_lines.append(out)
                if err and 'warning' not in err.lower():
                    self._log("warning", f"SSH cmd stderr: {err[:200]}")
            ssh.close()
            self._log("success", f"دپلوی موفق روی {ip}:{deploy_dir}")
            return deploy_dir
        except Exception as e:
            self._log("error", f"خطای SSH deploy: {e}")
            return None

    # -- response generation ----------------------------------------------------

    def _generate_response(self, project_ctx: str, proposal_ctx: str,
                           conversation: str, phase: str = "chat") -> tuple:
        system = self.deploy_prompt if phase == "deploy" else self.chat_prompt
        parts = [system]
        if project_ctx:
            parts.append(project_ctx)
        if proposal_ctx and phase != "deploy":
            parts.append(proposal_ctx)
        parts.append(f"مکالمه تا الان:\n{conversation}")
        parts.append("پاسخ من:")

        prompt = "\n\n".join(parts)

        result = run_claude(self.model, prompt, timeout=120,
                            log_fn=lambda msg: self._log("error", msg))
        if result and result.returncode == 0:
            raw = result.stdout.strip()
            lines = [
                l for l in raw.split('\n')
                if not any(x in l.lower() for x in
                           ['trust', 'folder', 'security', '────'])
            ]
            cleaned = '\n'.join(lines).strip()

            approved = False
            if "[APPROVED]" in cleaned:
                cleaned = cleaned.replace("[APPROVED]", "").strip()
                approved = True

            # استخراج اطلاعات سرور
            server_info = None
            m = re.search(r'\[SERVER:\s*ip=(\S+)\s+user=(\S+)\s+pass=(.+?)\]', cleaned)
            if m:
                server_info = {"ip": m.group(1), "user": m.group(2), "pass": m.group(3).strip()}
                cleaned = re.sub(r'\[SERVER:[^\]]+\]', '', cleaned).strip()

            done = False
            if "[DONE]" in cleaned:
                cleaned = cleaned.replace("[DONE]", "").strip()
                done = True

            return cleaned or None, approved, server_info, done
        return None, False, None, False

    # -- main loop entry --------------------------------------------------------

    def check_and_respond(self) -> int:
        self._log("info", "بررسی پیام‌های جدید...")
        rooms = self._fetch_rooms(pages=2)
        if not rooms:
            self._log("info", "هیچ اتاقی دریافت نشد")
            return 0

        responded = 0
        for room in rooms:
            try:
                responded += self._process_room(room)
            except Exception as e:
                self._log("error", f"خطا در پردازش اتاق {room.get('id')}: {e}")

        self._log("info", f"بررسی تمام شد. {responded} پاسخ ارسال شد.")
        return responded

    def _process_room(self, room: dict) -> int:
        if room.get("is_archived"):
            return 0

        room_id = room["id"]
        guest = room.get("guest_name", "?")
        room_dir = self._room_dir(room_id)
        state = self._load_state(room_dir)
        status = state.get("status", "")

        # اتاق‌های تمام‌شده
        if status == "done":
            return 0

        last_msg = room.get("last_message", "") or ""
        if last_msg.startswith("پیشنهاد بر روی پروژه"):
            return 0
        if "فریلنسر دیگری را روی پروژه" in last_msg or "از حالت تمام وقت خارج شده" in last_msg:
            if status != "done":
                state["status"] = "done"
                self._save_state(room_dir, state)
                self._log("info", f"اتاق {room_id} ({guest}): کارفرما دیگری رو استخدام کرد — بسته شد")
            return 0

        messages, projects = self._fetch_messages(room_id)
        if not messages:
            return 0

        # --- تشخیص استخدام (workdiary) ---
        active_wd = [p for p in projects if p.get("status") == "accepted"]
        if active_wd and status not in ("hired", "deploying", "deployed", "done"):
            project_title = active_wd[0].get("title", "")
            wd_id = active_wd[0].get("id", "")
            state["status"] = "hired"
            state["workdiary_id"] = wd_id
            state["workdiary_title"] = project_title
            self._save_state(room_dir, state)
            self._log("success", f"اتاق {room_id} ({guest}): استخدام — {project_title}")
            if self.tg:
                self.tg.send_message(
                    f"<b>🎉 استخدام شدی!</b>\n"
                    f"کارفرما: {guest}\nپروژه: {project_title}\nمیزکار: {wd_id}"
                )
            status = "hired"

        newest = messages[0]
        if newest["sender_id"] == self.MY_USER_ID:
            return 0
        if newest["id"] <= state.get("last_responded_msg_id", 0):
            return 0

        project_ctx = self._get_project_context(projects)
        proposal_ctx = self._get_proposal_context(projects)
        conversation = self._format_conversation(messages)

        # --- فاز pre-hire: چت عادی ---
        if status not in ("hired", "deploying", "deployed"):
            is_first_contact = not state.get("repo_name")
            repo_name = self._setup_repo_for_room(
                room_id, state, room_dir, projects, project_ctx
            )
            if is_first_contact and repo_name:
                receptor_id = room.get("user_id")
                self._send_message(room_id, receptor_id, repo_name)
                self._log("info", f"اتاق {room_id}: ریپو ارسال شد: {repo_name}")
                self._save_state(room_dir, state)
                time.sleep(1)

            response, approved, _, _ = self._generate_response(
                project_ctx, proposal_ctx, conversation, phase="chat"
            )
            if not response:
                self._log("warning", f"اتاق {room_id}: پاسخی تولید نشد")
                return 0

            receptor_id = room.get("user_id")
            if self._send_message(room_id, receptor_id, response):
                state["last_responded_msg_id"] = newest["id"]
                if approved:
                    state["status"] = "approved"
                    self._log("success", f"اتاق {room_id} ({guest}): تایید اولیه!")
                    if self.tg:
                        self.tg.send_message(
                            f"<b>تایید اولیه!</b>\nکارفرما: {guest}\nاتاق: {room_id}"
                        )
                self._save_state(room_dir, state)
                self._log_conversation(room_dir, newest, response)
                time.sleep(3)
                return 1
            return 0

        # --- فاز post-hire: دپلوی ---
        response, _, server_info, done = self._generate_response(
            project_ctx, "", conversation, phase="deploy"
        )
        if not response:
            return 0

        receptor_id = room.get("user_id")

        # اگه Claude اطلاعات سرور استخراج کرد → دپلوی کن
        if server_info and status == "hired":
            self._log("info", f"اتاق {room_id}: اطلاعات سرور دریافت شد، شروع دپلوی...")
            state["status"] = "deploying"
            state["server"] = server_info
            self._save_state(room_dir, state)

            repo_name = state.get("repo_name") or self._setup_repo_for_room(
                room_id, state, room_dir, projects, project_ctx
            )
            deploy_path = None
            if repo_name:
                deploy_path = self._ssh_deploy(
                    server_info["ip"], server_info["user"], server_info["pass"], repo_name
                )

            if deploy_path:
                state["status"] = "deployed"
                state["deploy_path"] = deploy_path
                self._save_state(room_dir, state)
                deploy_msg = (
                    f"کد رو روی سرور شما نصب کردم. مسیر: {deploy_path}\n"
                    f"لطفاً سرور رو بررسی کنید و بگید همه چیز درسته؟"
                )
                self._send_message(room_id, receptor_id, deploy_msg)
                self._log("success", f"اتاق {room_id}: دپلوی موفق — {deploy_path}")
                if self.tg:
                    self.tg.send_message(
                        f"<b>🚀 دپلوی موفق!</b>\nکارفرما: {guest}\nسرور: {server_info['ip']}\nمسیر: {deploy_path}"
                    )
            else:
                self._send_message(room_id, receptor_id, response)
                self._log("warning", f"اتاق {room_id}: دپلوی ناموفق")
            state["last_responded_msg_id"] = newest["id"]
            self._save_state(room_dir, state)
            self._log_conversation(room_dir, newest, response)
            return 1

        if done:
            state["status"] = "done"
            self._log("success", f"اتاق {room_id} ({guest}): تمام — پروژه بسته شد")
            if self.tg:
                self.tg.send_message(f"<b>✅ پروژه تمام شد!</b>\nکارفرما: {guest}")

        if self._send_message(room_id, receptor_id, response):
            state["last_responded_msg_id"] = newest["id"]
            self._save_state(room_dir, state)
            self._log_conversation(room_dir, newest, response)
            time.sleep(3)
            return 1
        return 0

    def _log_conversation(self, room_dir: Path, newest: dict, response: str):
        log_file = room_dir / "conversation.txt"
        with open(log_file, 'a', encoding='utf-8') as f:
            f.write(
                f"\n--- {datetime.now().isoformat()} ---\n"
                f"کارفرما: {newest.get('message') or ''}\n"
                f"من: {response}\n"
            )


# ---------------------------------------------------------------------------
# Karlancer Bot
# ---------------------------------------------------------------------------

class Karlancer:

    SEARCH_API = "https://www.karlancer.com/api/publics/search/projects"
    PROJECT_API = "https://www.karlancer.com/api/publics/projects"
    BIDS_API = "https://www.karlancer.com/api/bids"

    def __init__(self, bearer_token: str, check_interval: int = 300, model: str = "sonnet", tg: TelegramLogger = None, github_token: str = ""):
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
        self.bid_project_ids = set()

        self.chat_manager = ChatManager(
            headers=self.headers, submit_headers=self.submit_headers,
            cookies=self.cookies, model=self.model, tg=self.tg,
            github_token=github_token,
        )

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

    # -- bid check -----------------------------------------------------------

    def _fetch_bid_project_ids(self, full: bool = False) -> set:
        ids = set()
        max_pages = 999 if full else 3
        page = 1
        while page <= max_pages:
            try:
                resp = requests.get(
                    f"{self.BIDS_API}/?page={page}",
                    headers=self.headers, cookies=self.cookies, timeout=15,
                )
                if resp.status_code != 200:
                    break
                data = resp.json().get("data", {})
                bids = data.get("data", [])
                if not bids:
                    break
                for bid in bids:
                    pid = bid.get("project_id")
                    if pid:
                        ids.add(pid)
                if page >= data.get("last_page", 1):
                    break
                page += 1
            except Exception as e:
                self.log_error(f"خطا در دریافت bidها (صفحه {page}): {e}")
                break
        return ids

    def refresh_bid_cache(self):
        if not self.bid_project_ids:
            self.bid_project_ids = self._fetch_bid_project_ids(full=True)
            self.log_info(f"📋 {len(self.bid_project_ids)} bid موجود بارگذاری شد (کامل)")
        else:
            new_ids = self._fetch_bid_project_ids(full=False)
            self.bid_project_ids.update(new_ids)
            self.log_info(f"📋 بروزرسانی bidها — مجموع: {len(self.bid_project_ids)}")

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

        all_projects.sort(key=lambda p: p.get('id', 0), reverse=True)
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

        result = run_claude(self.model, combined, timeout=300, log_fn=self.log_error)
        if result is None:
            self.log_error(f"تحلیل پروژه {project_id} ناموفق")
        elif result.returncode == 0:
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

        return None

    # -- extract proposal ----------------------------------------------------

    def extract_proposal(self, analysis_file: Path) -> str | None:
        try:
            content = analysis_file.read_text(encoding='utf-8')

            # حذف هدر فایل تحلیل (Project ID, تاریخ, خط جداکننده)
            header_end = content.find('=' * 40)
            body = content[header_end:].lstrip('= \n') if header_end != -1 else content

            # پیدا کردن شروع پروپوزال — همیشه با سلام، یا SALAM شروع میشه
            start_idx = -1
            for marker in ["سلام،", "SALAM"]:
                idx = body.find(marker)
                if idx != -1 and (start_idx == -1 or idx < start_idx):
                    start_idx = idx

            if start_idx == -1:
                self.log_warning("شروع پروپوزال (سلام/SALAM) پیدا نشد — کل تحلیل ارسال میشه")
                return body.strip() or None

            # پیدا کردن پایان پروپوزال — بعد از امضا
            end_markers = ["Senior Python Backend Developer", "# محاسبات", "## محاسبات",
                           "💰 محاسبات", "[PRICE:", "\n# "]
            end_idx = len(body)
            for marker in end_markers:
                idx = body.find(marker, start_idx + 50)
                if idx != -1 and idx < end_idx:
                    # اگه marker پایان بعد از امضاست، اون رو include کن
                    if marker == "Senior Python Backend Developer":
                        end_idx = idx + len(marker)
                    else:
                        end_idx = idx
                    break

            result = body[start_idx:end_idx].strip()
            return result or None

        except Exception as e:
            self.log_error(f"خطا در استخراج پروپوزال: {e}")
            return None

    # -- submit --------------------------------------------------------------

    def submit_proposal(self, project_id: int, project: dict, analysis_file: Path) -> bool:
        # چک کن قبلا bid فرستادی یا نه
        if project_id in self.bid_project_ids:
            self.log_warning(f"پروژه {project_id} قبلاً bid داره — رد شد")
            return False

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

        # قیمت و مدت از خروجی Claude — اگه نبود fallback به حداقل
        analysis_text = ""
        try:
            analysis_text = analysis_file.read_text(encoding='utf-8')
        except Exception:
            pass

        price_match = re.search(r'\[PRICE:\s*(\d+)\]', analysis_text)
        dur_match = re.search(r'\[DURATION:\s*(\d+)\]', analysis_text)
        budget = max(2_500_000, int(price_match.group(1))) if price_match else 2_500_000
        duration = int(dur_match.group(1)) if dur_match else (project.get('job_duration') or 7)

        if not price_match:
            self.log_warning(f"پروژه {project_id}: [PRICE] در تحلیل نبود — از حداقل ۲٬۵۰۰٬۰۰۰ استفاده شد")

        # ساخت milestones: پیش‌پرداخت + فازهای تحویل
        prepay = int(budget * 0.3)
        remaining = budget - prepay
        milestones = [{"description": "پیش پرداخت", "duration": "1", "budget": str(prepay)}]
        if duration > 7:
            half = remaining // 2
            d1 = max(1, duration // 2)
            d2 = max(1, duration - d1)
            milestones.append({"description": "تحویل مرحله اول", "duration": str(d1), "budget": str(half)})
            milestones.append({"description": "تحویل نهایی", "duration": str(d2), "budget": str(remaining - half)})
        else:
            milestones.append({"description": "تحویل کامل پروژه", "duration": str(max(1, duration - 1)), "budget": str(remaining)})

        self.log_info(f"📤 ارسال پروپوزال پروژه {project_id} (بودجه: {budget:,} تومان، {duration} روز، {len(milestones)} مرحله)")

        payload = {
            "project_id": project_id,
            "bid_id": None,
            "is_pin": False,
            "is_highlight": False,
            "is_multi": False,
            "description": proposal,
            "edit_cart_id": None,
            "milestones": milestones,
        }

        try:
            resp = requests.post(self.BIDS_API, headers=self.submit_headers, cookies=self.cookies, json=payload, timeout=10)
            if resp.status_code in [200, 201]:
                self.log_success(f"پروژه {project_id} با موفقیت ارسال شد!")
                return True
            elif resp.status_code == 409:
                self.log_warning(f"پروژه {project_id} قبلاً پیشنهاد ثبت شده — رد شد")
                return True
            else:
                self.log_error(f"خطا در ارسال پروژه {project_id}: HTTP {resp.status_code}: {resp.text}")
                return False
        except Exception as e:
            self.log_error(f"خطا در ارسال پروپوزال: {e}")
            return False

    # -- relevance filter ----------------------------------------------------

    SKIP_KEYWORDS = [
        'ادمین', 'تولید محتوا', 'اینستاگرام', 'مدیریت پیج', 'مدیریت شبکه',
        'سئو', 'گرافیک', 'لوگو', 'تدوین', 'موشن', 'انیمیشن',
        'تبلیغات', 'کمپین', 'بازاریابی', 'مارکتینگ', 'دیجیتال مارکتینگ',
        'ترجمه', 'مترجم', 'تایپ', 'نویسندگی', 'نگارش', 'مقاله', 'ویراستاری',
        'فتوشاپ', 'ایلوستریتور', 'کورل', 'افتر افکت', 'پریمیر',
        'حسابداری', 'منشی', 'دستیار مجازی', 'پاسخگویی',
        'طراحی لوگو', 'طراحی بنر', 'طراحی پوستر', 'طراحی لباس',
        'دکوراسیون', 'معماری', 'عمران', 'سازه', 'تیزر',
        'کپی رایتینگ', 'بلاگ', 'شبکه اجتماعی', 'پاورپوینت',
        'اکسل', 'ورد', 'صدا', 'دوبله', 'گویندگی',
    ]

    TECH_SKILLS = {
        'python', 'پایتون', 'django', 'fastapi', 'flask',
        'javascript', 'جاوا اسکریپت', 'typescript', 'react', 'react js', 'next js', 'vue', 'angular', 'node',
        'php', 'پی اچ پی', 'laravel',
        'java', 'c#', 'c++', 'go', 'rust', 'swift', 'kotlin',
        'android', 'اندروید', 'ios', 'flutter', 'react native',
        'backend', 'front end', 'فرانت اند', 'بک اند',
        'html5', 'css', 'برنامه نویسی', 'برنامه نویسی وب', 'کدنویسی',
        'ربات', 'ساخت ربات', 'طراحی ربات',
        'هوش مصنوعی', 'ماشین لرنینگ', 'بینایی ماشین', 'متخصص هوش مصنوعی',
        'ساخت اپلیکیشن', 'طراحی اپلیکیشن موبایل',
        'api', 'docker', 'devops', 'linux', 'git',
        'sql', 'postgresql', 'mongodb', 'redis', 'mysql',
        'تحلیل داده', 'data', 'scraping', 'اسکریپینگ',
        'آردوینو', 'میکروکنترلر', 'arduino', 'stm32', 'arm', 'avr', 'الکترونیک',
        'telegram', 'bot', 'chatbot',
        'wordpress', 'وردپرس', 'ووکامرس',
        'طراحی سایت', 'طراحی وب', 'برنامه نویسی php',
        'unity', 'unity3d', 'game development', 'بازی سازی',
        'matlab', 'matlab programming', 'متلب',
        'crm', 'مدیریت ارتباط با مشتری',
    }

    FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')

    def _is_too_old(self, project: dict) -> bool:
        past = project.get('past_time') or ''
        normalized = past.translate(self.FA_DIGITS)
        if 'هفته' in normalized or 'ماه' in normalized or 'سال' in normalized:
            return True
        m = re.search(r'(\d+)\s*روز', normalized)
        if m and int(m.group(1)) >= 5:
            return True
        return False

    def _is_relevant(self, project: dict) -> bool:
        if self._is_too_old(project):
            return False

        skills = project.get('skills', [])
        if skills:
            skill_names = {s.get('name', '').lower() for s in skills}
            has_tech = any(ts in name for name in skill_names for ts in self.TECH_SKILLS)
            if has_tech:
                return True
            return False

        title = project.get('title', '')
        desc = project.get('description', '')
        text = f"{title} {desc}"
        if any(kw in text for kw in self.SKIP_KEYWORDS):
            return False

        return True

    # -- process -------------------------------------------------------------

    def process_new_projects(self):
        self.log_info("جستجوی پروژه‌های جدید...")
        self.refresh_bid_cache()

        all_projects = self.fetch_projects()
        if not all_projects:
            self.log_info("هیچ پروژه‌ای دریافت نشد")
            return

        new_projects = [
            p for p in all_projects
            if p.get('id') and p['id'] not in self.seen_projects
            and p['id'] not in self.bid_project_ids
            and self._is_relevant(p)
        ]
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

    # -- single project ------------------------------------------------------

    def _resolve_project_slug(self, raw: str) -> str:
        if 'karlancer.com/' in raw:
            parts = raw.rstrip('/').split('/')
            return parts[-1]
        return raw

    def process_single_project(self, raw_id: str):
        slug = self._resolve_project_slug(raw_id)
        self.log_info(f"پردازش تکی پروژه {slug}...")
        self.refresh_bid_cache()

        try:
            resp = requests.get(
                f"{self.PROJECT_API}/{slug}",
                headers=self.headers, cookies=self.cookies, timeout=15,
            )
            resp.encoding = 'utf-8'
            if resp.status_code != 200:
                self.log_error(f"دریافت پروژه ناموفق: HTTP {resp.status_code}")
                return
            project = resp.json().get("data", resp.json())
        except Exception as e:
            self.log_error(f"خطا در دریافت پروژه: {e}")
            return

        project_id = project.get('id')
        title = project.get('title', 'بدون عنوان')
        print("=" * 80)
        self.log_info(f"پروژه {project_id}: {title}")
        print("=" * 80)

        saved = self.save_project(project)
        if not saved:
            return

        analysis_file = self.analyze_project(project_id)
        if not analysis_file:
            return

        submitted = self.submit_proposal(project_id, project, analysis_file)
        if submitted:
            self.seen_projects.add(project_id)
            self._save_cache()
            if self.tg:
                self.tg.send_project_submitted(project_id, title)
        print("=" * 80)

    # -- main loop -----------------------------------------------------------

    def run(self, once: bool = False, chat_only: bool = False):
        self.log_success("🚀 ربات کارلنسر شروع شد")
        self.log_info(f"⏰ فاصله بررسی: {self.check_interval} ثانیه ({self.check_interval // 60} دقیقه)")
        self.log_info(f"🧠 مدل: {self.model}")
        if chat_only:
            self.log_info("💬 حالت فقط چت فعال است")
        if self.tg:
            self.log_info("📱 Telegram Logger: فعال")
            self.tg.send_startup(self.check_interval)
        print("=" * 80 + "\n")

        if once:
            if not chat_only:
                self.process_new_projects()
            self.chat_manager.check_and_respond()
            return

        iteration = 0
        try:
            while True:
                iteration += 1
                self.log_info(f"🔄 چرخه #{iteration} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

                if not chat_only:
                    try:
                        self.process_new_projects()
                    except Exception as e:
                        self.log_error(f"خطا در پردازش پروژه‌ها: {e}")

                try:
                    self.chat_manager.check_and_respond()
                except Exception as e:
                    self.log_error(f"خطا در پردازش چت‌ها: {e}")

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
    parser.add_argument('--chat-only', action='store_true',
                        help='فقط چت‌ها رو بررسی کن (بدون ارسال پروپوزال)')
    parser.add_argument('--project', type=str,
                        help='پردازش یک پروژه خاص (URL، slug یا ID عددی)')
    parser.add_argument('--no-proxy', action='store_true',
                        help='بدون پروکسی (اتصال مستقیم)')
    parser.add_argument('--setup-telegram', action='store_true',
                        help='دریافت Chat ID تلگرام')
    args = parser.parse_args()

    if args.no_proxy:
        for key in ('all_proxy', 'ALL_PROXY', 'http_proxy', 'HTTP_PROXY',
                     'https_proxy', 'HTTPS_PROXY', 'ftp_proxy', 'FTP_PROXY'):
            os.environ.pop(key, None)
        print("🔌 پروکسی غیرفعال شد — اتصال مستقیم")

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

    github_token = os.environ.get("GITHUB_TOKEN", "")
    if github_token:
        print("🐙 GitHub Token: فعال")

    bot = Karlancer(bearer_token=bearer, check_interval=args.interval, model=args.model, tg=tg, github_token=github_token)

    if args.project:
        bot.process_single_project(args.project)
        return

    bot.run(once=args.once, chat_only=args.chat_only)


if __name__ == "__main__":
    main()
