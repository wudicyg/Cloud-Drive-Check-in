# -*- coding: utf-8 -*-    
"""    
cron "34 18 * * *" script-path=leaflow_checkin.py,tag=匹配cron用    
new Env('leaflow签到')    
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
from datetime import datetime, timedelta    
  
  
try:    
    from zoneinfo import ZoneInfo    
    SH_TZ = ZoneInfo("Asia/Shanghai")    
except Exception:    
    SH_TZ = None    
  
  
try:    
    from curl_cffi import requests    
    USE_CURL_CFFI = True    
except ImportError:    
    import requests    
    USE_CURL_CFFI = False    
  
  
# ---------------- 可选通知模块 ----------------    
hadsend = False    
notify_error = None  
try:    
    from notify import send    
    hadsend = True    
    print("✅ 通知模块加载成功")  
except Exception as e:    
    notify_error = str(e)  
    print(f"⚠️ 通知模块加载失败: {e}")  
    def send(title, content):    
        pass    
  
  
# ---------------- 配置项 ----------------
# 支持的环境变量:
#   LEAFLOW_BASE        单个站点地址（可选，覆盖默认候选列表首位）
#   LEAFLOW_COOKIE      Cookie，多账号换行或 & 分隔
# 说明: 旧版签到站 checkin.leaflow.net 已迁移至 console.leaflow.net（需新版 Cookie）
#       BASE_CANDIDATES 按顺序尝试，直到获得确定性结果
BASE_CANDIDATES = [
    os.getenv("LEAFLOW_BASE", "https://checkin.leaflow.net").rstrip("/"),
    "https://console.leaflow.net",
]
BASE = BASE_CANDIDATES[0]
TIMEOUT = int(os.getenv("TIMEOUT", "60"))
RETRY_TIMES = int(os.getenv("RETRY_TIMES", "3"))
RETRY_DELAY = int(os.getenv("RETRY_DELAY", "5"))
RANDOM_SIGNIN = os.getenv("RANDOM_SIGNIN", "true").lower() == "true"
MAX_RANDOM_DELAY = int(os.getenv("MAX_RANDOM_DELAY", "3600"))
NOTIFY_ON_ALREADY = os.getenv("NOTIFY_ON_ALREADY", "true").lower() == "true"  # 已签到是否通知
DEBUG_MODE = os.getenv("DEBUG_MODE", "false").lower() == "true"  # 🆕 调试模式
  
  
HTTP_PROXY = os.getenv("HTTP_PROXY") or os.getenv("http_proxy")    
HTTPS_PROXY = os.getenv("HTTPS_PROXY") or os.getenv("https_proxy")    
PROXIES = None    
if HTTP_PROXY or HTTPS_PROXY:    
    PROXIES = {"http": HTTP_PROXY or HTTPS_PROXY, "https": HTTPS_PROXY or HTTP_PROXY}    
  
  
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36"    
  
  
def now_sh():    
    return datetime.now(tz=SH_TZ) if SH_TZ else datetime.now()    
  
  
def build_session(cookie: str):    
    s = requests.Session()    
    s.headers.update({    
        "User-Agent": UA,    
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",    
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",    
        "Connection": "keep-alive",    
        "Cookie": cookie.strip(),    
    })    
    if PROXIES:    
        s.proxies.update(PROXIES)    
    return s    
  
  
def extract_csrf(html: str) -> dict:    
    data = {}    
    for m in re.finditer(r'<input[^>]+type=["\']hidden["\'][^>]*>', html, re.I):    
        tag = m.group(0)    
        name_match = re.search(r'name=["\']([^"\']+)["\']', tag)    
        value_match = re.search(r'value=["\']([^"\']*)["\']', tag)    
        if name_match:    
            data[name_match.group(1)] = value_match.group(1) if value_match else ""    
    return data    
  
  
def extract_reward(html: str) -> float:
    """
    🔧 修复版本：优先匹配今日签到奖励，避免误取历史记录
    """
    if not html:    
        return 0    
        
    # 清理脚本和样式标签
    text_cleaned = re.sub(r'<script[^>]*>.*?</script>', '', html, flags=re.DOTALL | re.I)    
    text_cleaned = re.sub(r'<style[^>]*>.*?</style>', '', text_cleaned, flags=re.DOTALL | re.I)    
    
    # 🆕 移除签到历史区域（避免误匹配历史金额）
    text_cleaned = re.sub(
        r'<div[^>]*class=["\'][^"\']*history[^"\']*["\'][^>]*>.*?</div>',
        '',
        text_cleaned,
        flags=re.DOTALL | re.I
    )
    text_cleaned = re.sub(
        r'签到历史.*?(?=<div|$)',
        '',
        text_cleaned,
        flags=re.DOTALL | re.I
    )
    
    if DEBUG_MODE:
        print(f"[DEBUG] 清理后的HTML片段: {text_cleaned[:300]}...")
    
    # 🆕 优先级1：明确匹配"今日/今天/本次/签到成功"相关的奖励
    priority_patterns = [
        r'今日.*?获得.*?([\d.]+)\s*元',
        r'今天.*?获得.*?([\d.]+)\s*元',
        r'本次.*?获得.*?([\d.]+)\s*元',
        r'签到成功.*?获得.*?([\d.]+)\s*元',
        r'今日签到.*?([\d.]+)\s*元',
        r'恭喜.*?获得.*?([\d.]+)\s*元',
        r'成功.*?奖励.*?([\d.]+)\s*元',
    ]
    
    for pattern in priority_patterns:
        match = re.search(pattern, text_cleaned, re.I)
        if match:
            try:
                amount = float(match.group(1))
                if 0.01 <= amount <= 10:
                    if DEBUG_MODE:
                        print(f"[DEBUG] 优先级匹配成功: {pattern} -> {amount} 元")
                    return amount
            except (ValueError, IndexError):
                continue
    
    # 🆕 优先级2：通用模式（从前往后找第一个，而非最大值）
    general_patterns = [    
        r'\+\s*([\d.]+)\s*元',    
        r'([\d.]+)\s*元',    
        r'获得.*?([\d.]+)\s*元',    
        r'奖励.*?([\d.]+)\s*元',    
        r'领取.*?([\d.]+)\s*元',    
    ]    
    
    for pattern in general_patterns:
        match = re.search(pattern, text_cleaned, re.I)  # 🔄 改为 search（找第一个）
        if match:
            try:
                amount = float(match.group(1))
                if 0.01 <= amount <= 10:
                    if DEBUG_MODE:
                        print(f"[DEBUG] 通用模式匹配: {pattern} -> {amount} 元")
                    return amount
            except (ValueError, IndexError):
                continue
    
    if DEBUG_MODE:
        print("[DEBUG] 未匹配到任何金额")
    return 0    
  
  
def parse_result(html: str) -> tuple[str, str, float]:    
    if not html:    
        return "unknown", "页面内容为空", 0    
        
    amount = extract_reward(html)    
        
    already_patterns = [    
        r'今日已签到',    
        r'已连续签到',    
        r'明天再来',    
        r'已签到',    
        r'already\s+checked',    
    ]    
        
    for pattern in already_patterns:    
        if re.search(pattern, html, re.I):    
            if amount > 0:    
                return "already", f"今日已签到（今日获得 {amount} 元）", amount    
            return "already", "今日已签到", 0    
        
    success_patterns = [    
        r'签到成功',    
        r'获得奖励',    
        r'领取成功',    
        r'恭喜',    
        r'check-?in\s+success',    
    ]    
        
    for pattern in success_patterns:    
        if re.search(pattern, html, re.I):    
            if amount > 0:    
                return "success", f"签到成功，获得 {amount} 元", amount    
            return "success", "签到成功", 0    
        
    invalid_patterns = [    
        r'请登录',    
        r'please\s+log\s*in',    
        r'未登录',    
        r'session\s+expired',    
    ]    
        
    for pattern in invalid_patterns:    
        if re.search(pattern, html, re.I):    
            return "invalid", "登录失效，请更新 Cookie", 0    
        
    if "error" in html.lower() or "错误" in html:    
        return "fail", "页面返回错误", 0    
        
    return "unknown", "未识别到明确状态", 0    
  
  
def sign_once_impl(cookie: str, base: str) -> tuple[str, str, float]:    
    s = build_session(cookie)    
        
    try:    
        kwargs = {"timeout": TIMEOUT, "allow_redirects": True}    
        if USE_CURL_CFFI:    
            kwargs["impersonate"] = "chrome120"            
            
        r1 = s.get(f"{base}/", **kwargs)            
            
        if "login" in r1.url.lower():    
            return "invalid", "被重定向到登录页，Cookie 已失效", 0            
            
        if r1.status_code == 403:    
            return "error", "403 Forbidden（触发风控）", 0            
            
        if r1.status_code != 200:    
            return "error", f"首页返回 {r1.status_code}", 0            
            
        html1 = r1.text or ""            
            
        if any(x in html1 for x in ["请登录", "未登录"]):    
            return "invalid", "页面提示未登录", 0            
            
        form_data = {"checkin": ""}            
        form_data.update(extract_csrf(html1))            
            
        headers_post = {            
            "Content-Type": "application/x-www-form-urlencoded",            
            "Origin": base,            
            "Referer": f"{base}/",            
        }            
            
        r2 = s.post(f"{base}/index.php", data=form_data, headers=headers_post, **kwargs)            
            
        if r2.status_code == 403:    
            return "error", "POST 被拒绝 403", 0    
            
        html2 = r2.text or ""

        if DEBUG_MODE:
            # 保存HTML到临时文件用于调试
            debug_file = f"debug_response_{int(time.time())}.html"
            with open(debug_file, "w", encoding="utf-8") as f:
                f.write(html2)
            print(f"[DEBUG] 响应已保存到: {debug_file}")
        
        status, msg, amount = parse_result(html2)    
            
        if status == "unknown" or (status == "success" and amount == 0):    
            time.sleep(1)    
            r3 = s.get(f"{base}/", **kwargs)    
            status2, msg2, amount2 = parse_result(r3.text or "")    
            if status2 != "unknown":    
                return status2, msg2, amount2    
            
        return status, msg, amount    
            
    except requests.exceptions.Timeout:    
        return "error", f"请求超时（{TIMEOUT}秒）", 0    
    except requests.exceptions.ConnectionError as e:    
        return "error", f"连接失败: {str(e)[:80]}", 0    
    except Exception as e:    
        return "error", f"{e.__class__.__name__}: {str(e)[:100]}", 0    


def sign_with_retry(cookie: str, account_name: str) -> tuple[str, str, float]:    
    """对每个候选站点分别重试，获取签到结果"""
    last_status, last_msg, last_amount = "error", "未执行", 0
    for base in BASE_CANDIDATES:
        print(f"  🌐 尝试站点: {base}")
        for attempt in range(1, RETRY_TIMES + 1):
            if attempt > 1:
                print(f"  🔄 第 {attempt}/{RETRY_TIMES} 次重试...")
                time.sleep(RETRY_DELAY)
            
            status, msg, amount = sign_once_impl(cookie, base)
            last_status, last_msg, last_amount = status, msg, amount
            
            if status in ("success", "already", "invalid"):
                return status, msg, amount
            
            if attempt < RETRY_TIMES:
                print(f"  ⚠️ {msg}，{RETRY_DELAY}秒后重试...")
        
    return last_status, f"{last_msg}（所有站点重试后失败）", 0    
  
  
def format_time_remaining(seconds: int) -> str:    
    if seconds <= 0:    
        return "立即执行"    
    h = seconds // 3600    
    m = (seconds % 3600) // 60    
    s = seconds % 60    
    if h > 0:    
        return f"{h}小时{m}分{s}秒"    
    if m > 0:    
        return f"{m}分{s}秒"    
    return f"{s}秒"    
  
  
def wait_with_countdown(delay_seconds: int, tag: str):    
    if delay_seconds <= 0:    
        return    
    print(f"{tag} 需要等待 {format_time_remaining(delay_seconds)}")    
    remaining = delay_seconds    
    while remaining > 0:    
        if remaining <= 10 or remaining % 10 == 0:    
            print(f"{tag} 倒计时: {format_time_remaining(remaining)}")    
        step = 1 if remaining <= 10 else min(10, remaining)    
        time.sleep(step)    
        remaining -= step    
  
  
def safe_send_notify(title, content):  
    """安全的通知发送（带日志）"""  
    if not hadsend:  
        print(f"📢 [通知] {title}: {content}")  
        print("   (通知模块未加载，仅控制台显示)")  
        return False  
      
    try:  
        print(f"📤 正在推送通知: {title}")  
        send(title, content)  
        print("✅ 通知推送成功")  
        return True  
    except Exception as e:  
        print(f"❌ 通知推送失败: {e}")  
        return False  
  
  
def main():    
    print(f"{'='*50}")
    print(f"  Leaflow 签到脚本 v2.1（站点迁移适配版）")
    print(f"  适配内容: 旧站 checkin.leaflow.net 已迁移 console.leaflow.net")
    print(f"           支持多候选站点自动切换 + Cookie 失效清晰提示")
    if DEBUG_MODE:
        print(f"  🐛 调试模式: 已启用")
    print(f"{'='*50}\n")
    
    cookies_env = os.getenv("LEAFLOW_COOKIE", "").strip()    
    if not cookies_env:    
        print("❌ 未设置 LEAFLOW_COOKIE 环境变量")    
        sys.exit(1)    
        
    raw_list = []    
    for seg in cookies_env.replace("\r", "\n").split("\n"):    
        raw_list.extend(seg.split("&"))    
    cookie_list = [c.strip() for c in raw_list if c.strip()]    
        
    print(f"共发现 {len(cookie_list)} 个 Cookie")    
    print(f"随机签到: {'启用' if RANDOM_SIGNIN else '禁用'}")    
    if RANDOM_SIGNIN:    
        print(f"随机签到时间窗口: {MAX_RANDOM_DELAY // 60} 分钟")    
        
    if len(cookie_list) == 0:    
        print("Cookie 列表为空")    
        sys.exit(1)    
        
    schedule = []    
    base_time = now_sh()    
    for i, ck in enumerate(cookie_list, 1):    
        delay = random.randint(0, MAX_RANDOM_DELAY) if RANDOM_SIGNIN else 0    
        at = base_time + timedelta(seconds=delay)    
        schedule.append({    
            "idx": i,    
            "cookie": ck,    
            "delay": delay,    
            "time": at,    
            "name": f"账号{i}"    
        })    
    schedule.sort(key=lambda x: x["delay"])    
        
    if RANDOM_SIGNIN:
        print("\n==== 签到执行顺序 ====")    
        for it in schedule:    
            print(f"{it['name']}: 预计 {it['time'].strftime('%H:%M:%S')} 执行")    
        
    print("\n==== 开始执行签到任务 ====\n")    
        
    success_count = 0    
    already_count = 0    
    fail_count = 0    
    total_amount = 0.0    
        
    for it in schedule:    
        name = it["name"]    
            
        if it["delay"] > 0:    
            wait_with_countdown(it["delay"], name)    
            
        print(f"\n==== {name} 开始签到 ====")    
        print(f"当前时间: {datetime.now().strftime('%H:%M:%S')}")    
            
        status, msg, amount = sign_with_retry(it["cookie"], name)    
            
        if status == "success":    
            success_count += 1    
            if amount > 0:    
                total_amount += amount    
                print(f"✅ {name} {msg}")    
                print(f"💰 本次获得: {amount} 元")    
            else:    
                print(f"✅ {name} {msg}")    
                
            safe_send_notify("Leaflow 签到成功", f"{name}：{msg}")  
            
        elif status == "already":    
            already_count += 1    
            if amount > 0:    
                total_amount += amount    
                print(f"ℹ️ {name} {msg}")    
            else:    
                print(f"ℹ️ {name} 今日已签到")    
              
            if NOTIFY_ON_ALREADY:  
                safe_send_notify("Leaflow 签到提醒", f"{name}：{msg}")  
            
        else:    
            fail_count += 1    
            print(f"❌ {name} 签到失败: {msg}")    
            safe_send_notify("Leaflow 签到失败", f"{name}：{status} - {msg}")  
            
        if it["idx"] < len(cookie_list):    
            time.sleep(random.uniform(2, 5))    
        
    print(f"\n{'='*50}")    
    print(f"  所有账号签到完成")    
    print(f"  ✅ 成功: {success_count} | ℹ️ 已签: {already_count} | ❌ 失败: {fail_count}")    
        
    if total_amount > 0:    
        print(f"  💰 今日总计获得: {total_amount} 元")    
        
    print(f"  完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")    
    print(f"{'='*50}\n")    
        
    if len(cookie_list) > 1:    
        summary = f"签到完成\n成功: {success_count} | 已签: {already_count} | 失败: {fail_count}"    
        if total_amount > 0:    
            summary += f"\n今日共获得: {total_amount} 元"    
        safe_send_notify("Leaflow 签到汇总", summary)  
    
  
  
if __name__ == "__main__":    
    main()
