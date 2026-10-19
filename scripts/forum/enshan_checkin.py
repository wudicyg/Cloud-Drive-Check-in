"""
cron "39 12 * * *" script-path=xxx.py,tag=匹配cron用
new Env('恩山论坛签到')
"""

# ---------------- Windows 控制台编码兼容（青龙 Linux 环境下为空操作）----------------
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


import os
import re
import requests
import random
import time
from datetime import datetime, timedelta

# ---------------- 统一通知模块加载 ----------------
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
    print("✅ 已加载notify.py通知模块")
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")

# 配置项
enshan_cookie = os.environ.get('enshan_cookie', '')
max_random_delay = int(os.getenv("MAX_RANDOM_DELAY", "3600"))
random_signin = os.getenv("RANDOM_SIGNIN", "true").lower() == "true"
privacy_mode = os.getenv("PRIVACY_MODE", "true").lower() == "true"

# 恩山论坛配置
# 注意：right.com.cn 的路径大小写会影响可访问性；站点实际使用的是 /forum
BASE_URL = 'https://www.right.com.cn/forum'

# 积分页（用户信息）可能存在不同参数形式；按顺序尝试
CREDIT_URLS = [
    f'{BASE_URL}/home.php?mod=spacecp&ac=credit',
    f'{BASE_URL}/home.php?mod=spacecp&ac=credit&showcredit=1',
    # 兼容历史配置（部分环境里曾误写为 /FORUM）
    'https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit',
    'https://www.right.com.cn/FORUM/home.php?mod=spacecp&ac=credit&showcredit=1',
]

CHECKIN_URL = f'{BASE_URL}/k_misign-sign.html'

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    # 不手动声明 Accept-Encoding：交给 requests 自动协商（gzip/deflate），
    # 避免服务端返回 br 而运行环境缺少 brotli 导致响应内容无法解码
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
    'Cache-Control': 'max-age=0'
}

def mask_username(username):
    """用户名脱敏处理"""
    if not username:
        return username

    if privacy_mode:
        if len(username) <= 2:
            return '*' * len(username)
        elif len(username) <= 4:
            return username[0] + '*' * (len(username) - 2) + username[-1]
        else:
            return username[0] + '*' * 3 + username[-1]
    return username

def format_time_remaining(seconds):
    """格式化时间显示"""
    if seconds <= 0:
        return "立即执行"
    hours, minutes = divmod(seconds, 3600)
    minutes, secs = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"

def wait_with_countdown(delay_seconds, task_name):
    """带倒计时的随机延迟等待"""
    if delay_seconds <= 0:
        return
    print(f"{task_name} 需要等待 {format_time_remaining(delay_seconds)}")
    remaining = delay_seconds
    while remaining > 0:
        if remaining <= 10 or remaining % 10 == 0:
            print(f"{task_name} 倒计时: {format_time_remaining(remaining)}")
        sleep_time = 1 if remaining <= 10 else min(10, remaining)
        time.sleep(sleep_time)
        remaining -= sleep_time

def notify_user(title, content):
    """统一通知函数"""
    if hadsend:
        try:
            send(title, content)
            print(f"✅ 通知发送完成: {title}")
        except Exception as e:
            print(f"❌ 通知发送失败: {e}")
    else:
        print(f"📢 {title}\n📄 {content}")

def parse_cookies(cookie_str):
    """解析Cookie字符串，支持多账号"""
    if not cookie_str:
        return []

    # 先按换行符分割
    lines = cookie_str.strip().split('\n')
    cookies = []

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # 再按&&分割
        parts = line.split('&&')
        for part in parts:
            part = part.strip()
            if part:
                cookies.append(part)

    # 去重并过滤空值
    unique_cookies = []
    for cookie in cookies:
        if cookie and cookie not in unique_cookies:
            unique_cookies.append(cookie)

    return unique_cookies

def extract_number(text):
    """从文本中提取数字"""
    if not text:
        return 0
    try:
        # 移除所有非数字字符，只保留数字
        number_str = re.sub(r'[^\d]', '', str(text))
        return int(number_str) if number_str else 0
    except (ValueError, TypeError):
        return 0

def extract_first(text, patterns, default=None, flags=0):
    """按顺序尝试正则，返回第一个匹配到的 group(1)（strip后）。"""
    for pattern in patterns:
        match = re.search(pattern, text, flags)
        if match:
            value = match.group(1)
            return value.strip() if isinstance(value, str) else value
    return default

class EnShanSigner:
    name = "恩山论坛"

    def __init__(self, cookie: str, index: int = 1):
        self.cookie = cookie
        self.index = index
        self.session = requests.Session()
        self.session.headers.update(HEADERS)
        self.session.headers['Cookie'] = cookie

        # 用户信息
        self.user_name = None
        self.user_group = None
        self.coin_before = None
        self.point_before = None
        self.contribution = None
        self.coin_after = None
        self.point_after = None
        self.formhash = None
        self.uid = None
        self.sign_in_page_url = f"{BASE_URL}/erling_qd-sign_in.html"
        self.sign_url = f"{BASE_URL}/plugin.php?id=erling_qd:action&action=sign"

    def _sync_cookie_header(self):
        self.session.headers['Cookie'] = self.cookie

    @staticmethod
    def _rotl8(x, r):
        x &= 0xFF
        r &= 7
        return ((x << r) & 0xFF) | (x >> (8 - r))

    @staticmethod
    def _rotr8(x, r):
        x &= 0xFF
        r &= 7
        return (x >> r) | ((x << (8 - r)) & 0xFF)

    @staticmethod
    def _extract_oo(html):
        match = re.search(r"oo\s*=\s*\[([^\]]+)\]", html)
        if not match:
            return None
        tokens = re.findall(r"0x[0-9a-fA-F]+|\d+", match.group(1))
        if not tokens:
            return None
        values = []
        for token in tokens:
            if token.lower().startswith("0x"):
                values.append(int(token, 16))
            else:
                values.append(int(token))
        return values

    @staticmethod
    def _extract_wi(html):
        match = re.search(r'setTimeout\("\w+\((\d+)\)"', html)
        if match:
            return int(match.group(1))
        match = re.search(r"\b\w+\((\d+)\)", html)
        if match:
            return int(match.group(1))
        return None

    @staticmethod
    def _extract_loop1_params(html):
        pattern = (
            r"qo\s*=\s*(\d+);\s*do\{.*?oo\[qo\]=\(-oo\[qo\]\)&0xff;.*?"
            r"oo\[qo\]=\(\(\(oo\[qo\]>>(\d+)\)\|\(\(oo\[qo\]<<(\d+)\)&0xff\)\)\-(\d+)\)&0xff;.*?"
            r"\}\s*while\(--qo>=2\);"
        )
        match = re.search(pattern, html, re.S)
        if not match:
            return None
        return {
            "start": int(match.group(1)),
            "shift_r": int(match.group(2)),
            "shift_l": int(match.group(3)),
            "sub": int(match.group(4)),
        }

    @staticmethod
    def _extract_loop2_start(html):
        match = re.search(
            r"qo\s*=\s*(\d+);\s*do\s*\{[^}]*?oo\[qo\]\s*=\s*\(oo\[qo\]\s*-\s*oo\[qo\s*-\s*1\]\)\s*&\s*0xff;[^}]*?\}\s*while\s*\(\s*--\s*qo\s*>=\s*3\s*\)",
            html,
            re.S,
        )
        if not match:
            return None
        return int(match.group(1))

    @staticmethod
    def _extract_loop3_params(html):
        block_match = re.search(
            r"qo\s*=\s*1;\s*for\s*\(.*?\)\s*\{(.*?)\}\s*po\s*=",
            html,
            re.S,
        )
        if not block_match:
            return None
        block = block_match.group(1)

        upper_match = re.search(r"qo\s*>\s*(\d+)\)\s*break", block)
        if not upper_match:
            return None
        upper = int(upper_match.group(1))

        assign_match = re.search(r"oo\[qo\]\s*=\s*(.+?);", block, re.S)
        if not assign_match:
            return None
        expr = assign_match.group(1)

        add_nums = re.findall(r"\+\s*(\d+)", expr)
        if len(add_nums) < 2:
            return None
        add1 = int(add_nums[0])
        add2 = int(add_nums[1])

        shift_nums = re.findall(r"<<\s*(\d+)|>>\s*(\d+)", expr)
        shifts = []
        for left, right in shift_nums:
            if left:
                shifts.append(int(left))
            if right:
                shifts.append(int(right))
        if len(shifts) < 2:
            return None
        rot_l = shifts[0]
        return {
            "upper": upper,
            "add1": add1,
            "add2": add2,
            "rot_l": rot_l,
        }

    @staticmethod
    def _extract_mod_skip(html):
        match = re.search(r"qo\s*%\s*(\d+)", html)
        if not match:
            return 7
        return int(match.group(1))

    def _decode_po(self, oo_hex, wi, params):
        oo = [b & 0xFF for b in oo_hex]
        if len(oo) < 6:
            return ""

        last_index = len(oo) - 1
        loop1_start = params["loop1_start"]
        loop2_start = params["loop2_start"]
        loop3_upper = params["loop3_upper"]
        shift_r = params["shift_r"]
        shift_l = params["shift_l"]
        sub = params["sub"]
        add1 = params["add1"]
        add2 = params["add2"]
        rot_l = params["rot_l"]
        mod_skip = params["mod_skip"]

        qo = min(loop1_start, last_index - 1)
        while True:
            oo[qo] = (-oo[qo]) & 0xFF
            if (shift_r + shift_l) == 8:
                oo[qo] = (self._rotr8(oo[qo], shift_r) - sub) & 0xFF
            else:
                oo[qo] = (((oo[qo] >> shift_r) | ((oo[qo] << shift_l) & 0xFF)) - sub) & 0xFF
            qo -= 1
            if qo < 2:
                break

        qo = min(loop2_start, last_index - 2)
        while True:
            oo[qo] = (oo[qo] - oo[qo - 1]) & 0xFF
            qo -= 1
            if qo < 3:
                break

        for qo in range(1, min(loop3_upper, last_index - 1) + 1):
            x = (oo[qo] + add1) & 0xFF
            x = (x + add2) & 0xFF
            oo[qo] = self._rotl8(x, rot_l)

        po_chars = []
        for qo in range(1, last_index):
            if qo % mod_skip != 0:
                po_chars.append(chr((oo[qo] ^ (wi & 0xFF)) & 0xFF))
        return "".join(po_chars)

    @staticmethod
    def _extract_cookie_kv(decoded_js):
        match = re.search(r"document\.cookie=['\"]([^'\"]+)['\"]", decoded_js)
        if not match:
            return None
        cookie_str = match.group(1).strip()
        if not cookie_str:
            return None
        return cookie_str.split(';', 1)[0].strip()

    @staticmethod
    def _upsert_cookie(base_cookies, new_cookie_kv):
        if not new_cookie_kv or '=' not in new_cookie_kv:
            return base_cookies
        new_key, new_value = new_cookie_kv.split('=', 1)
        new_key = new_key.strip()
        new_value = new_value.strip()

        parts = []
        replaced = False
        for raw in base_cookies.split(';'):
            part = raw.strip()
            if not part or '=' not in part:
                continue
            key, value = part.split('=', 1)
            key = key.strip()
            if key == new_key:
                parts.append(f"{new_key}={new_value}")
                replaced = True
            else:
                parts.append(f"{key}={value.strip()}")
        if not replaced:
            parts.append(f"{new_key}={new_value}")
        return '; '.join(parts)

    @staticmethod
    def _extract_formhash(html):
        patterns = [
            r'name="formhash"\s+value="([0-9a-fA-F]+)"',
            r"member\.php\?mod=logging(?:&amp;|&)action=logout(?:&amp;|&)formhash=([0-9a-fA-F]+)",
        ]
        return extract_first(html, patterns=patterns, default=None, flags=re.S)

    def _get_clearance_headers(self):
        return {
            'User-Agent': HEADERS['User-Agent'],
            'Accept': (
                'text/html,application/xhtml+xml,application/xml;q=0.9,'
                'image/avif,image/webp,image/apng,*/*;q=0.8'
            ),
            'Pragma': 'no-cache',
            'Cache-Control': 'no-cache',
            'Accept-Language': 'zh-CN,zh;q=0.9',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Site': 'same-origin',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-User': '?1',
            'Sec-Fetch-Dest': 'document',
            'Referer': self.sign_in_page_url,
            'Cookie': self.cookie,
        }

    def _merge_response_cookies(self, response):
        for name, value in response.cookies.items():
            self.cookie = self._upsert_cookie(self.cookie, f"{name}={value}")
        self._sync_cookie_header()

    def _refresh_clearance_cookie(self):
        try:
            response = self.session.get(
                self.sign_in_page_url,
                headers=self._get_clearance_headers(),
                timeout=30,
                allow_redirects=True
            )
        except Exception as e:
            return False, f"获取签到页失败: {e}"

        self._merge_response_cookies(response)

        if "oo" not in response.text:
            formhash = self._extract_formhash(response.text)
            if formhash:
                self.formhash = formhash
                return True, "已刷新签到参数"
            return False, "签到页未提取到formhash"

        oo = self._extract_oo(response.text)
        wi = self._extract_wi(response.text)
        loop1 = self._extract_loop1_params(response.text)
        loop2_start = self._extract_loop2_start(response.text)
        loop3 = self._extract_loop3_params(response.text)
        if not oo or wi is None or not loop1 or loop2_start is None or not loop3:
            return False, "WAF挑战参数提取失败"

        params = {
            "loop1_start": loop1["start"],
            "loop2_start": loop2_start,
            "loop3_upper": loop3["upper"],
            "shift_r": loop1["shift_r"],
            "shift_l": loop1["shift_l"],
            "sub": loop1["sub"],
            "add1": loop3["add1"],
            "add2": loop3["add2"],
            "rot_l": loop3["rot_l"],
            "mod_skip": self._extract_mod_skip(response.text),
        }
        decoded_js = self._decode_po(oo, wi, params)
        cookie_kv = self._extract_cookie_kv(decoded_js)
        if not cookie_kv:
            return False, "WAF解码后未找到cookie"

        self.cookie = self._upsert_cookie(self.cookie, cookie_kv)
        self._sync_cookie_header()

        try:
            follow = self.session.get(
                self.sign_in_page_url,
                headers=self._get_clearance_headers(),
                timeout=30,
                allow_redirects=True
            )
        except Exception as e:
            return False, f"WAF通过后重试签到页失败: {e}"

        self._merge_response_cookies(follow)
        formhash = self._extract_formhash(follow.text)
        if formhash:
            self.formhash = formhash
            return True, "已刷新WAF Cookie和formhash"
        return False, "WAF通过后未提取到formhash"

    def daily_login(self):
        """每日登录 - 获取formhash和uid"""
        try:
            print("🔐 正在登录获取参数...")
            clearance_ok, clearance_msg = self._refresh_clearance_cookie()
            if clearance_ok and self.formhash:
                print(f"✅ 获取formhash成功: {self.formhash}")
                return True, "登录成功"

            print(f"⚠️ 签到页参数获取失败，回退forum页: {clearance_msg}")
            url = f"{BASE_URL}/forum.php"
            response = self.session.get(url, timeout=20)
            print(f"🔍 登录响应状态码: {response.status_code}")
            if response.status_code != 200:
                return False, f"登录失败，状态码: {response.status_code}"

            self._merge_response_cookies(response)
            self.formhash = self._extract_formhash(response.text)
            if self.formhash:
                print(f"✅ 获取formhash成功: {self.formhash}")
                uid_match = re.search(r"discuz_uid\s*=\s*'(\d+)'", response.text)
                if uid_match:
                    self.uid = uid_match.group(1)
                    print(f"✅ 获取uid成功: {self.uid}")
                return True, "登录成功"
            return False, "未找到formhash参数"

        except Exception as e:
            return False, f"登录过程发生错误: {e}"

    def get_user_info(self, is_after=False):
        """获取用户信息和积分"""
        try:
            print(f"👤 正在获取{'签到后' if is_after else '签到前'}用户信息...")

            # 添加随机延迟
            time.sleep(random.uniform(2, 5))

            # 部分情况下积分页会返回 521（源站/WAF/路径大小写导致），这里做重试并尝试多个候选URL
            response = None
            last_status = None
            for url in CREDIT_URLS:
                for attempt in range(1, 4):
                    headers = {
                        **HEADERS,
                        'Referer': f'{BASE_URL}/forum.php',
                    }
                    resp = self.session.get(url=url, headers=headers, timeout=20, allow_redirects=True)
                    last_status = resp.status_code
                    if resp.status_code == 200 and resp.text:
                        response = resp
                        break

                    # 521/5xx/429 等临时性错误：短暂退避后重试
                    if resp.status_code in (429, 521) or 500 <= resp.status_code < 600:
                        time.sleep(1.5 * attempt + random.uniform(0, 0.8))
                        continue

                    # 其他状态码通常不是临时问题，换下一个URL
                    break
                if response is not None:
                    break

            if response is None:
                error_msg = f"获取用户信息失败，状态码: {last_status}"
                print(f"🔍 用户信息响应状态码: {last_status}")
                print(f"❌ {error_msg}")
                return False, error_msg

            print(f"🔍 用户信息响应状态码: {response.status_code}")

            if response.status_code == 200:
                # 提取积分信息
                # 页面结构可能随主题变化，使用多套模式兜底
                coin = extract_first(
                    response.text,
                    patterns=[
                        r"恩山币\s*[:：]\s*</em>\s*([^<&\s]+)",
                        r"恩山币\s*[:：]\s*([^<\s]+)\s*币",
                        r"恩山币\s*[:：]\s*([^<\s]+)",
                    ],
                    default="0",
                    flags=re.S,
                )
                point = extract_first(
                    response.text,
                    patterns=[
                        r"积分\s*[:：]\s*</em>\s*([^<&\s]+)",
                        r"<em>\s*积分\s*[:：]\s*</em>\s*([^<\s]+)",
                        r"积分\s*[:：]\s*([^<\s]+)",
                    ],
                    default="0",
                    flags=re.S,
                )

                if is_after:
                    self.coin_after = coin
                    self.point_after = point
                    print(f"💰 签到后 - 恩山币: {coin}, 积分: {point}")
                else:
                    self.coin_before = coin
                    self.point_before = point
                    print(f"💰 签到前 - 恩山币: {coin}, 积分: {point}")

                # 只在第一次获取用户名等信息
                if not is_after:
                    self.user_name = extract_first(
                        response.text,
                        patterns=[
                            r'访问我的空间">([^<]+)</a>',
                            r'class="vwmy"[^>]*>([^<]+)</a>',
                            r'欢迎您回来\s*,\s*([^<\n]+)',
                            r'用户名[：:]\s*([^<\n]+)',
                        ],
                        default="未知用户",
                        flags=re.S,
                    )

                    self.user_group = extract_first(
                        response.text,
                        patterns=[
                            r'用户组\s*[:：]\s*([^<\n]+)</',
                            r'用户组\s*[:：]\s*([^<\n]+)',
                        ],
                        default="未知等级",
                        flags=re.S,
                    )

                    self.contribution = extract_first(
                        response.text,
                        patterns=[
                            r'贡献\s*[:：]\s*</em>\s*([^<\s]+)\s*分',
                            r'贡献\s*[:：]\s*(\d+)',
                        ],
                        default="0",
                        flags=re.S,
                    )

                    print(f"👤 用户: {mask_username(self.user_name)}")
                    print(f"🏅 等级: {self.user_group}")
                    print(f"🎯 贡献: {self.contribution}")

                return True, "用户信息获取成功"
            else:
                error_msg = f"获取用户信息失败，状态码: {response.status_code}"
                print(f"❌ {error_msg}")
                return False, error_msg

        except Exception as e:
            error_msg = f"获取用户信息异常: {str(e)}"
            print(f"❌ {error_msg}")
            return False, error_msg

    def perform_checkin(self):
        """执行签到"""
        try:
            print("📝 正在执行签到...")

            if not self.formhash:
                login_ok, login_msg = self.daily_login()
                if not login_ok:
                    return False, f"请先执行登录获取formhash: {login_msg}"

            # 签到前再刷新一次，降低WAF过期导致的失败
            self._refresh_clearance_cookie()

            headers = {
                "User-Agent": HEADERS["User-Agent"],
                "Accept": "application/json, text/javascript, */*; q=0.01",
                "Accept-Language": "zh-CN,zh;q=0.9",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "X-Requested-With": "XMLHttpRequest",
                "Origin": "https://www.right.com.cn",
                "Referer": self.sign_in_page_url,
                "Cookie": self.cookie,
                "Sec-Fetch-Dest": "empty",
                "Sec-Fetch-Mode": "cors",
                "Sec-Fetch-Site": "same-origin",
                "Pragma": "no-cache",
                "Cache-Control": "no-cache",
            }

            data = {"formhash": self.formhash}

            response = self.session.post(self.sign_url, headers=headers, data=data, timeout=30)
            print(f"🔍 签到响应状态码: {response.status_code}")
            response.raise_for_status()

            try:
                result = response.json()
            except ValueError:
                result = {"message": response.text}

            if isinstance(result, dict):
                message = str(result.get("message", "")).strip()
                status = result.get("status")
                success = result.get("success")

                if success is True or status in (1, "1", "success", True):
                    return True, message or "签到成功"
                if "已签到" in message or "已经签到" in message:
                    return True, message
                if "成功" in message:
                    return True, message
                if message:
                    return False, f"签到失败: {message}"
            return True, "签到请求已提交"

        except Exception as e:
            return False, f"签到异常: {str(e)}"

    def main(self):
        """主执行函数"""
        print(f"\n==== 恩山论坛账号{self.index} 开始签到 ====")

        if not self.cookie.strip():
            error_msg = """账号配置错误

❌ 错误原因: Cookie为空

🔧 解决方法:
1. 在青龙面板中添加环境变量enshan_cookie
2. 多账号用换行分隔或&&分隔
3. Cookie需要包含完整的登录信息

💡 提示: 请确保Cookie有效且格式正确"""
            print(f"❌ {error_msg}")
            return error_msg, False

        # 1. 获取签到前用户信息
        login_success, login_msg = self.daily_login()
        if not login_success:
            return f"登录失败: {login_msg}", False
        user_success, user_msg = self.get_user_info(is_after=False)
        if not user_success:
            print(f"⚠️ 获取用户信息失败: {user_msg}")

        # 2. 随机等待
        time.sleep(random.uniform(2, 5))

        # 3. 执行签到
        signin_success, signin_msg = self.perform_checkin()

        # 4. 获取签到后用户信息
        time.sleep(random.uniform(2, 4))
        after_success, after_msg = self.get_user_info(is_after=True)

        # 5. 通过积分变化判断签到是否真的成功
        gain_info = ""
        if after_success and self.coin_before and self.coin_after:
            try:
                # 修复：清理数据，移除"币"等文字，只保留数字
                coin_before = extract_number(self.coin_before)
                coin_after = extract_number(self.coin_after)
                point_before = extract_number(self.point_before)
                point_after = extract_number(self.point_after)

                coin_gain = coin_after - coin_before
                point_gain = point_after - point_before

                print(f"📊 积分变化: 恩山币 {coin_before}→{coin_after} (+{coin_gain}), 积分 {point_before}→{point_after} (+{point_gain})")

                if coin_gain > 0 or point_gain > 0:
                    signin_success = True
                    signin_msg = f"签到成功，获得 {coin_gain} 恩山币，{point_gain} 积分"
                    gain_info = f"\n🎁 本次收益: +{coin_gain} 恩山币, +{point_gain} 积分"
                    print(f"✅ 通过积分变化确认签到成功: +{coin_gain} 恩山币, +{point_gain} 积分")
                elif coin_gain == 0 and point_gain == 0:
                    # 积分没变化，可能已经签到过了
                    signin_success = True
                    signin_msg = "今日已签到（积分无变化）"
                    print("📅 积分无变化，今日已签到")
                else:
                    print("⚠️ 积分变化异常，但仍认为签到成功")
                    signin_success = True

            except Exception as e:
                print(f"⚠️ 积分变化计算异常: {e}")
                # 如果积分计算失败，使用原始签到结果
                print("🔄 使用原始签到结果")

        # 6. 组合结果消息
        final_msg = f"""🌟 恩山论坛签到结果

    👤 用户: {mask_username(self.user_name) or '未知用户'}
    🏅 等级: {self.user_group or '未知等级'}
    💰 恩山币: {self.coin_before or '未知'} → {self.coin_after or self.coin_before or '未知'}
    📊 积分: {self.point_before or '未知'} → {self.point_after or self.point_before or '未知'}
    🎯 贡献: {self.contribution or '0'} 分{gain_info}

    📝 签到: {signin_msg}
    ⏰ 时间: {datetime.now().strftime('%m-%d %H:%M')}"""

        print(f"{'✅ 任务完成' if signin_success else '❌ 任务失败'}")
        return final_msg, signin_success

def main():
    """主程序入口"""
    print(f"==== 恩山论坛签到开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")

    # 显示配置状态
    print(f"🔒 隐私保护模式: {'已启用' if privacy_mode else '已禁用'}")

    # 获取Cookie配置（先检测环境变量，再随机延迟）
    if not enshan_cookie:
        error_msg = """❌ 未找到enshan_cookie环境变量

🔧 配置方法:
1. enshan_cookie: 恩山论坛Cookie
2. 多账号用换行分隔或&&分隔
3. Cookie需要包含完整的登录信息

示例:
单账号: enshan_cookie=完整的Cookie字符串
多账号: enshan_cookie=cookie1&&cookie2 或换行分隔

💡 提示: 登录恩山论坛后，F12复制完整Cookie"""

        print(error_msg)
        notify_user("恩山论坛签到失败", error_msg)
        return

    # 使用Cookie解析函数
    cookies = parse_cookies(enshan_cookie)

    if not cookies:
        error_msg = """❌ Cookie解析失败

🔧 可能原因:
1. Cookie格式不正确
2. Cookie为空或只包含空白字符
3. 分隔符使用错误

💡 请检查enshan_cookie环境变量的值"""

        print(error_msg)
        notify_user("恩山论坛签到失败", error_msg)
        return

    # 随机延迟（环境变量确认无误后再等待）
    if random_signin:
        delay_seconds = random.randint(0, max_random_delay)
        if delay_seconds > 0:
            signin_time = datetime.now() + timedelta(seconds=delay_seconds)
            print(f"🎲 随机延迟: {format_time_remaining(delay_seconds)}")
            print(f"⏰ 预计签到时间: {signin_time.strftime('%H:%M:%S')}")
            wait_with_countdown(delay_seconds, "恩山论坛签到")

    print(f"📝 共发现 {len(cookies)} 个账号")

    success_count = 0
    total_count = len(cookies)
    results = []

    for index, cookie in enumerate(cookies):
        try:
            # 账号间随机等待
            if index > 0:
                delay = random.uniform(10, 20)
                print(f"⏱️  随机等待 {delay:.1f} 秒后处理下一个账号...")
                time.sleep(delay)

            # 执行签到
            signer = EnShanSigner(cookie, index + 1)
            result_msg, is_success = signer.main()

            if is_success:
                success_count += 1

            results.append({
                'index': index + 1,
                'success': is_success,
                'message': result_msg,
                'username': mask_username(signer.user_name) if signer.user_name else f"账号{index + 1}"
            })

            # 发送单个账号通知
            status = "成功" if is_success else "失败"
            title = f"恩山论坛账号{index + 1}签到{status}"
            notify_user(title, result_msg)

        except Exception as e:
            error_msg = f"账号{index + 1}: 执行异常 - {str(e)}"
            print(f"❌ {error_msg}")
            notify_user(f"恩山论坛账号{index + 1}签到失败", error_msg)

    # 发送汇总通知
    if total_count > 1:
        summary_msg = f"""📊 恩山论坛签到汇总

📈 总计: {total_count}个账号
✅ 成功: {success_count}个
❌ 失败: {total_count - success_count}个
📊 成功率: {success_count/total_count*100:.1f}%
⏰ 完成时间: {datetime.now().strftime('%m-%d %H:%M')}"""

        # 添加详细结果（最多显示5个账号的详情）
        if len(results) <= 5:
            summary_msg += "\n\n📋 详细结果:"
            for result in results:
                status_icon = "✅" if result['success'] else "❌"
                summary_msg += f"\n{status_icon} {result['username']}"

        notify_user("恩山论坛签到汇总", summary_msg)

    print(f"\n==== 恩山论坛签到完成 - 成功{success_count}/{total_count} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")

def handler(event, context):
    """云函数入口"""
    main()

if __name__ == "__main__":
    main()
