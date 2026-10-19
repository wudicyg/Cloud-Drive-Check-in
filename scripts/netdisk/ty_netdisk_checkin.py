#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
cron "1 16 * * *" script-path=xxx.py,tag=匹配cron用
new Env('天翼云盘签到')
"""

# ---------------- Windows 控制台编码兼容（青龙 Linux 环境下为空操作）----------------
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass


import time
import re
import json
import base64
import hashlib
import urllib.parse
import hmac
import os
import requests
import random
from datetime import datetime, timedelta

# ---------------- RSA 加密支持 ----------------
# 优先使用 rsa 库；青龙等环境未安装 rsa 时自动回退到纯标准库实现（无额外依赖）
try:
    import rsa as _rsa_lib
except ImportError:
    _rsa_lib = None

def _der_read_len(data, i):
    """读取 ASN.1 DER 长度字段，返回 (长度, 新偏移)"""
    b = data[i]
    i += 1
    if b < 0x80:
        return b, i
    nbytes = b & 0x7F
    length = 0
    for _ in range(nbytes):
        length = (length << 8) | data[i]
        i += 1
    return length, i

def _parse_spki(der):
    """解析 X.509 SubjectPublicKeyInfo，返回 (n, e)"""
    i = 0
    assert der[i] == 0x30, "非法的公钥结构(外层非SEQUENCE)"
    i += 1
    _, i = _der_read_len(der, i)
    assert der[i] == 0x30, "非法的公钥结构(缺少算法标识)"
    alen, i = _der_read_len(der, i + 1)
    i += alen
    assert der[i] == 0x03, "非法的公钥结构(缺少BIT STRING)"
    blen, i = _der_read_len(der, i + 1)
    i += 1  # 跳过未使用位数字节
    inner = der[i:i + blen - 1]
    assert inner[0] == 0x30, "非法的公钥结构(RSAPublicKey非SEQUENCE)"
    j = 1
    _, j = _der_read_len(inner, j)
    assert inner[j] == 0x02, "非法的公钥结构(缺少模数)"
    nlen, j = _der_read_len(inner, j + 1)
    n = int.from_bytes(inner[j:j + nlen], "big")
    j += nlen
    assert inner[j] == 0x02, "非法的公钥结构(缺少公指数)"
    elen, j = _der_read_len(inner, j + 1)
    e = int.from_bytes(inner[j:j + elen], "big")
    return n, e

def _stdlib_rsa_encrypt(j_rsakey, plaintext):
    """纯标准库实现 PKCS#1 v1.5 加密（与 rsa.encrypt 行为一致）"""
    n, e = _parse_spki(base64.b64decode(j_rsakey))
    k = (n.bit_length() + 7) // 8
    msg = plaintext if isinstance(plaintext, bytes) else plaintext.encode()
    ps_len = k - len(msg) - 3
    if ps_len < 8:
        raise ValueError("明文过长，无法用该公钥加密")
    ps = bytearray()
    while len(ps) < ps_len:
        ps.extend(b for b in os.urandom(ps_len) if b != 0)
    em = b"\x00\x02" + bytes(ps[:ps_len]) + b"\x00" + msg
    c = pow(int.from_bytes(em, "big"), e, n)
    return base64.b64encode(c.to_bytes(k, "big")).decode()

# ---------------- 统一通知模块加载 ----------------
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
        print(f"📢 {title}")
        print(f"📄 {content}")

# 常量定义
BI_RM = list("0123456789abcdefghijklmnopqrstuvwxyz")
B64MAP = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/"

class TianYiYunPan:
    def __init__(self, username, password, index):
        self.username = username
        self.password = password
        self.index = index
        self.session = requests.Session()
        
    def int2char(self, a):
        return BI_RM[a]

    def b64tohex(self, a):
        d = ""
        e = 0
        c = 0
        for i in range(len(a)):
            if list(a)[i] != "=":
                v = B64MAP.index(list(a)[i])
                if 0 == e:
                    e = 1
                    d += self.int2char(v >> 2)
                    c = 3 & v
                elif 1 == e:
                    e = 2
                    d += self.int2char(c << 2 | v >> 4)
                    c = 15 & v
                elif 2 == e:
                    e = 3
                    d += self.int2char(c)
                    d += self.int2char(v >> 2)
                    c = 3 & v
                else:
                    e = 0
                    d += self.int2char(c << 2 | v >> 4)
                    d += self.int2char(15 & v)
        if e == 1:
            d += self.int2char(c << 2)
        return d

    def rsa_encode(self, j_rsakey, string):
        # 优先使用 rsa 库；未安装或加载失败时使用纯标准库回退实现
        if _rsa_lib is not None:
            try:
                rsa_key = f"-----BEGIN PUBLIC KEY-----\n{j_rsakey}\n-----END PUBLIC KEY-----"
                pubkey = _rsa_lib.PublicKey.load_pkcs1_openssl_pem(rsa_key.encode())
                result = self.b64tohex((base64.b64encode(_rsa_lib.encrypt(f'{string}'.encode(), pubkey))).decode())
                return result
            except Exception as e:
                print(f"⚠️ rsa 库加密失败，改用标准库实现: {e}")
        return self.b64tohex(_stdlib_rsa_encrypt(j_rsakey, f'{string}'))

    def login(self):
        """登录天翼云盘：兼容 2026 新版 wap 登录页"""
        try:
            import json
            import urllib.parse

            print(f"👤 账号{self.index}: 开始登录 {self.username}")

            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 12; Mobile) AppleWebKit/537.36 Chrome/120.0 Mobile Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
                "Accept-Language": "zh-CN,zh;q=0.9",
            }
            self.session.headers.update(headers)

            def add_param(url, key, value):
                if key + "=" in url:
                    return url
                sep = "&" if "?" in url else "?"
                return url + sep + key + "=" + urllib.parse.quote(str(value))

            def parse_json_or_jsonp(resp_text):
                txt = resp_text.strip()
                if txt.startswith("callbackMsg("):
                    txt = txt[len("callbackMsg("):]
                    if txt.endswith(");"):
                        txt = txt[:-2]
                    elif txt.endswith(")"):
                        txt = txt[:-1]
                return json.loads(txt)

            urlToken = "https://m.cloud.189.cn/udb/udb_login.jsp?pageId=1&pageKey=default&clientType=wap&redirectURL=https://m.cloud.189.cn/zhuanti/2021/shakeLottery/index.html"
            r = self.session.get(urlToken, headers=headers, timeout=15)

            match = re.search(r"https?://[^\s'\"]+", r.text)
            if not match:
                raise Exception("获取登录URL失败")

            auto_url = match.group()
            r = self.session.get(auto_url, headers={**headers, "Referer": urlToken}, timeout=15)

            if "/index.html" in r.url:
                login_page_url = r.url.replace("/index.html", "/login.html")
            else:
                login_page_url = r.url

            login_page_url = add_param(login_page_url, "protocol", "https")
            login_page_url = add_param(login_page_url, "showback", "true")

            r = self.session.get(
                login_page_url,
                headers={**headers, "Referer": auto_url},
                timeout=15
            )

            if "j_rsaKey" not in r.text:
                with open("/tmp/189_login_page_error.html", "w", encoding="utf-8") as f:
                    f.write(r.text)
                raise Exception("获取账号密码登录页失败，页面已保存到 /tmp/189_login_page_error.html")

            key_match = re.search(r'id=["\']j_rsaKey["\'][^>]*value=["\']([^"\']+)["\']', r.text)
            if not key_match:
                raise Exception("提取 j_rsaKey 失败")

            j_rsakey = key_match.group(1)

            query = urllib.parse.urlsplit(r.url).query
            conf_url = "https://open.e.189.cn/api/logbox/oauth2/wap/appConf.do?" + query

            rc = self.session.post(
                conf_url,
                headers={**headers, "Referer": r.url},
                timeout=15
            )

            conf = rc.json()
            if str(conf.get("result")) != "0":
                raise Exception(f"appConf 获取失败: {conf.get('msg', conf)}")

            data_conf = conf.get("data") or {}

            appKey = data_conf.get("appKey", "cloud")
            accountType = data_conf.get("accountType", "02")
            paramId = data_conf.get("paramId", "")
            lt = data_conf.get("lt", "")
            reqId = data_conf.get("reqId", "")
            state = data_conf.get("state", "")
            isOauth2 = str(data_conf.get("isOauth2", True)).lower()
            returnUrl = urllib.parse.quote(data_conf.get("returnUrl", ""), safe="")

            if not paramId or not lt or not reqId or not returnUrl:
                raise Exception("appConf 关键参数不完整")

            self.session.headers.update({"lt": lt})

            username_plain = self.username
            if str(data_conf.get("hasAt", "false")).lower() == "true" and "@" not in username_plain:
                username_plain = username_plain + "@189.cn"

            username_encrypted = self.rsa_encode(j_rsakey, username_plain)
            password_encrypted = self.rsa_encode(j_rsakey, self.password)

            login_url = "https://open.e.189.cn/api/logbox/oauth2/loginSubmit.do"

            params = {
                "apptype": "wap",
                "appKey": appKey,
                "accountType": accountType,
                "dynamicCheck": "false",
                "userName": "{RSA}" + username_encrypted,
                "epd": "{RSA}" + password_encrypted,
                "version": "v2.0",
                "returnUrl": returnUrl,
                "isConfigurable": "true",
                "isOauth2": isOauth2,
                "state": state,
                "paramId": paramId,
                "lt": lt,
                "REQID": reqId,
                "callbackMsg": "callbackMsg",
            }

            r = self.session.get(
                login_url,
                params=params,
                headers={
                    **headers,
                    "Referer": r.url,
                    "Accept": "*/*",
                },
                timeout=15
            )

            try:
                result = r.json()
            except Exception:
                result = parse_json_or_jsonp(r.text)

            if str(result.get("result")) == "0":
                print(f"✅ 账号{self.index}: 登录成功")
                redirect_url = result.get("toUrl")
                if redirect_url:
                    self.session.get(redirect_url, headers=headers, timeout=15)
                return True

            msg = result.get("msg") or result.get("message") or result
            print(f"❌ 账号{self.index}: 登录失败 - {msg}")
            return False

        except Exception as e:
            print(f"❌ 账号{self.index}: 登录异常 - {str(e)}")
            return False

    def sign_in(self):
        """执行签到"""
        try:
            print(f"🎯 账号{self.index}: 开始签到")
            
            rand = str(round(time.time() * 1000))
            sign_url = f'https://api.cloud.189.cn/mkt/userSign.action?rand={rand}&clientType=TELEANDROID&version=8.6.3&model=SM-G930K'
            
            headers = {
                'User-Agent': 'Mozilla/5.0 (Linux; Android 5.1.1; SM-G930K Build/NRD90M; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/74.0.3729.136 Mobile Safari/537.36 Ecloud/8.6.3 Android/22 clientId/355325117317828 clientModel/SM-G930K imsi/460071114317824 clientChannelId/qq proVersion/1.0.6',
                "Referer": "https://m.cloud.189.cn/zhuanti/2016/sign/index.jsp?albumBackupOpened=1",
                "Host": "m.cloud.189.cn",
                "Accept-Encoding": "gzip, deflate",
            }
            
            response = self.session.get(sign_url, headers=headers, timeout=15)
            result = response.json()
            
            netdiskBonus = result.get('netdiskBonus', 0)
            isSign = result.get('isSign', 'true')
            
            if isSign == "false":
                status_msg = f"✅ 签到成功，获得 {netdiskBonus}M 空间"
                print(f"✅ 账号{self.index}: {status_msg}")
            else:
                status_msg = f"📅 今日已签到，获得 {netdiskBonus}M 空间"
                print(f"📅 账号{self.index}: {status_msg}")
            
            return status_msg
            
        except Exception as e:
            error_msg = f"签到异常: {str(e)}"
            print(f"❌ 账号{self.index}: {error_msg}")
            return error_msg

    def main(self):
        """主执行函数"""
        try:
            print(f"\n==== 账号{self.index} 开始执行 ====")
            print(f"🕐 开始时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
            
            # 登录
            if not self.login():
                error_msg = f"❌ 账号{self.index}: {self.username}\n登录失败，无法完成签到"
                print(error_msg)
                return error_msg, False
            
            # 签到
            sign_result = self.sign_in()
            
            # 格式化结果
            result_msg = f"""☁️ 天翼云盘签到结果

👤 账号信息: {self.username}
📊 签到状态: {sign_result}
🕐 完成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"""

            print(f"\n🎉 === 最终签到结果 ===")
            print(result_msg)
            print(f"==== 账号{self.index} 签到完成 ====\n")
            
            # 判断是否成功
            is_success = "签到成功" in sign_result or "已签到" in sign_result
            return result_msg, is_success
            
        except Exception as e:
            error_msg = f"❌ 账号{self.index}: 执行异常 - {str(e)}"
            print(error_msg)
            return error_msg, False

def main():
    """主程序入口"""
    print(f"==== 天翼云盘签到开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
    
    # 获取环境变量（先检测环境变量，再随机延迟）
    ty_username_env = os.getenv("TY_USERNAME", "")
    ty_password_env = os.getenv("TY_PASSWORD", "")
    
    if not ty_username_env or not ty_password_env:
        error_msg = "❌ 未找到TY_USERNAME或TY_PASSWORD环境变量"
        print(error_msg)
        notify_user("天翼云盘签到失败", error_msg)
        return
    
    # 随机延迟（环境变量确认无误后再等待）
    if random_signin:
        delay_seconds = random.randint(0, max_random_delay)
        if delay_seconds > 0:
            signin_time = datetime.now() + timedelta(seconds=delay_seconds)
            print(f"🎲 随机模式: 延迟 {format_time_remaining(delay_seconds)} 后开始")
            print(f"⏰ 预计开始时间: {signin_time.strftime('%H:%M:%S')}")
            wait_with_countdown(delay_seconds, "天翼云盘签到")
    
    # 解析多账号
    usernames = [u.strip() for u in ty_username_env.split('&') if u.strip()]
    passwords = [p.strip() for p in ty_password_env.split('&') if p.strip()]
    
    if len(usernames) != len(passwords):
        error_msg = "❌ 用户名和密码数量不匹配"
        print(error_msg)
        notify_user("天翼云盘签到失败", error_msg)
        return
    
    print(f"📝 共发现 {len(usernames)} 个账号")
    
    success_accounts = 0
    all_results = []
    
    for index, (username, password) in enumerate(zip(usernames, passwords)):
        try:
            # 账号间随机等待
            if index > 0:
                delay = random.uniform(10, 30)
                print(f"💤 随机等待 {delay:.1f} 秒后处理下一个账号...")
                time.sleep(delay)
            
            # 执行签到
            tianyi = TianYiYunPan(username, password, index + 1)
            result_msg, is_success = tianyi.main()
            all_results.append(result_msg)
            
            if is_success:
                success_accounts += 1
            
            # 发送单个账号通知
            title = f"天翼云盘账号{index + 1}签到{'成功' if is_success else '失败'}"
            notify_user(title, result_msg)
            
        except Exception as e:
            error_msg = f"❌ 账号{index + 1}: 处理异常 - {str(e)}"
            print(error_msg)
            all_results.append(error_msg)
            notify_user(f"天翼云盘账号{index + 1}签到失败", error_msg)
    
    # 发送汇总通知
    if len(usernames) > 1:
        summary_msg = f"""☁️ 天翼云盘签到汇总

📊 总计处理: {len(usernames)}个账号
✅ 成功账号: {success_accounts}个
❌ 失败账号: {len(usernames) - success_accounts}个
📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

详细结果请查看各账号单独通知"""
        notify_user('天翼云盘签到汇总', summary_msg)
        print(f"\n📊 === 汇总统计 ===")
        print(summary_msg)
    
    print(f"\n==== 天翼云盘签到完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")

if __name__ == "__main__":
    main()
