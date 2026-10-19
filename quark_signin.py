"""
cron "13 18 * * *" script-path=xxx.py,tag=匹配cron用
new Env('夸克签到')
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
import sys
import time
import random
import requests
from datetime import datetime, timedelta

# ---------------- 统一通知模块加载（和NodeSeek一样）----------------
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
    print("✅ 已加载notify.py通知模块")
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")

# 随机延迟配置
max_random_delay = int(os.getenv("MAX_RANDOM_DELAY", "3600"))
random_signin = os.getenv("RANDOM_SIGNIN", "true").lower() == "true"

#推送函数（修改为使用notify.py）
def Push(contents):
    """修改推送函数使用notify.py（保持原始调用方式）"""
    if hadsend:
        try:
            send('夸克签到', contents)
            print('✅ notify.py推送成功')
        except Exception as e:
            print(f'❌ notify.py推送失败: {e}')
    else:
        print(f'📢 夸克签到')
        print(f'📄 {contents}')

def format_time_remaining(seconds):
    """格式化时间显示"""
    if seconds <= 0:
        return "立即执行"
    
    hours = seconds // 3600
    minutes = (seconds % 3600) // 60
    secs = seconds % 60
    
    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    elif minutes > 0:
        return f"{minutes}分{secs}秒"
    else:
        return f"{secs}秒"

def wait_with_countdown(delay_seconds):
    """带倒计时的等待"""
    if delay_seconds <= 0:
        return
        
    print(f"夸克签到需要等待 {format_time_remaining(delay_seconds)}")
    
    remaining = delay_seconds
    while remaining > 0:
        if remaining <= 10 or remaining % 10 == 0:
            print(f"倒计时: {format_time_remaining(remaining)}")
        
        sleep_time = 1 if remaining <= 10 else min(10, remaining)
        time.sleep(sleep_time)
        remaining -= sleep_time

# 获取环境变量
def get_env():
    # 判断 QUARK_COOKIE是否存在于环境变量
    if "QUARK_COOKIE" in os.environ:
        # 读取系统变量以 \n 或 && 分割变量
        cookie_list = re.split('\n|&&',os.environ.get('QUARK_COOKIE') ) #os.environ.get('QUARK_COOKIE')
    else:
        # 标准日志输出
        print('❌未添加QUARK_COOKIE变量')
        # 脚本退出
        sys.exit(0)

    return cookie_list

class Quark:
    def __init__(self, cookie):
        self.cookie = cookie

    def _get_json(self, url, headers, params=None, method="get", payload=None):
        """带超时与容错的 JSON 请求"""
        try:
            if method == "get":
                response = requests.get(url=url, headers=headers, params=params, timeout=15)
            else:
                response = requests.post(url=url, headers=headers, params=params, json=payload, timeout=15)
            return response.json()
        except Exception as e:
            print(f"⚠️  请求失败: {url} -> {e}")
            return None

    def get_growth_info(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/info"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        headers = {
            "content-type": "application/json",
            "cookie": self.cookie
        }
        response = self._get_json(url, headers, querystring)
        if response and response.get("data"):
            return response["data"]
        else:
            return False

    def get_growth_sign(self):
        url = "https://drive-m.quark.cn/1/clouddrive/capacity/growth/sign"
        querystring = {"pr": "ucpro", "fr": "pc", "uc_param_str": ""}
        payload = {"sign_cyclic": True}
        headers = {
            "content-type": "application/json",
            "cookie": self.cookie
        }
        response = self._get_json(url, headers, querystring, method="post", payload=payload)
        if response and response.get("data"):
            return True, response["data"]["sign_daily_reward"]
        else:
            return False, (response or {}).get("message", "请求失败或无响应")

    def get_account_info(self):
        url = "https://pan.quark.cn/account/info"
        querystring = {"fr": "pc", "platform": "pc"}
        headers = {
            "content-type": "application/json",
            "cookie": self.cookie
        }
        response = self._get_json(url, headers, querystring)
        if response and response.get("data"):
            return response["data"]
        else:
            return False

    def do_sign(self):
        msg = ""
        # 验证账号
        account_info = self.get_account_info()
        if not account_info:
            msg = f"\n❌该账号登录失败，cookie无效"
        else:
            log = f" 昵称: {account_info.get('nickname', '未知')}"
            msg += log + "\n"
            # 每日领空间
            growth_info = self.get_growth_info()
            if growth_info:
                cap_sign = growth_info.get("cap_sign") or {}
                if cap_sign.get("sign_daily"):
                    log = f"✅ 执行签到: 今日已签到+{int((cap_sign.get('sign_daily_reward') or 0) / 1024 / 1024)}MB，连签进度({cap_sign.get('sign_progress', 0)}/{cap_sign.get('sign_target', 0)})"
                    msg += log + "\n"
                else:
                    sign, sign_return = self.get_growth_sign()
                    if sign:
                        log = f"✅ 执行签到: 今日签到+{int((sign_return or 0) / 1024 / 1024)}MB，连签进度({cap_sign.get('sign_progress', 0) + 1}/{cap_sign.get('sign_target', 0)})"
                        msg += log + "\n"
                    else:
                        msg += f"✅ 执行签到: {sign_return}\n"

        return msg

def main():
    msg = ""
    global QUARK_COOKIE
    
    QUARK_COOKIE = get_env()

    print("✅检测到共", len(QUARK_COOKIE), "个夸克账号\n")

    i = 0
    while i < len(QUARK_COOKIE):
        # 开始任务
        log = f"🙍🏻‍♂️ 第{i + 1}个账号"
        msg += log
        # 登录（单账号异常不中断整体流程）
        try:
            log = Quark(QUARK_COOKIE[i]).do_sign()
        except Exception as e:
            log = f"\n❌ 账号{i + 1}执行异常: {e}"
            print(log)
        msg += log + "\n"
        
        # 多账号间随机等待
        if i < len(QUARK_COOKIE) - 1:  # 不是最后一个账号
            delay = random.uniform(3, 8)
            print(f"随机等待 {delay:.1f} 秒后处理下一个账号...")
            time.sleep(delay)

        i += 1

    print(msg)
    
    # 统一推送（只推送一次，包含所有账号结果）
    Push(contents=msg[:-1])

    return msg[:-1]

if __name__ == "__main__":
    print(f"==== 夸克网盘签到开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
    
    # 随机延迟（可选）
    if random_signin:
        delay_seconds = random.randint(0, max_random_delay)
        if delay_seconds > 0:
            signin_time = datetime.now() + timedelta(seconds=delay_seconds)
            print(f"随机模式: 延迟 {format_time_remaining(delay_seconds)} 后签到")
            print(f"预计签到时间: {signin_time.strftime('%H:%M:%S')}")
            wait_with_countdown(delay_seconds)
    
    print("----------夸克网盘开始尝试签到----------")
    main()
    print("----------夸克网盘签到执行完毕----------")
    print(f"==== 夸克签到完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
