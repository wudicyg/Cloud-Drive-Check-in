#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cron "0 9 * * *" script-path=CDRail.py,tag=成都地铁签到
new Env('成都地铁签到')

环境变量:
- CDRAIL_DATA: 账号数据
  - 支持 JSON: {"token":"...","app-token":"...","Cookie":"..."}
  - 支持 querystring: token=...&app-token=...&cookie=...
  - 多账号: 换行 或 @ 分割

抓包说明:
- 签到接口 URL: https://app.cdmetro.chengdurail.cn/platform/users/user/sign-in-integral
- 从该请求的 headers 中提取: token / app-token / Cookie / deviceId(建议)

依赖:
- requests
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
import json
import random
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from datetime import datetime, timedelta

# ---------------- 统一通知模块加载 ----------------
hadsend = False
send = None
try:
    from notify import send
    hadsend = True
except ImportError:
    print("⚠️  未加载通知模块，跳过通知功能")

# ---------------- 基础配置 ----------------
SCRIPT_NAME = "成都地铁签到"
ENV_NAME = "CDRAIL_DATA"

timeout = int(os.getenv("TIMEOUT", "15"))
max_retries = int(os.getenv("MAX_RETRIES", "3"))

# 随机延迟（与仓库内其它脚本保持一致）
max_random_delay = int(os.getenv("MAX_RANDOM_DELAY", "3600"))
random_signin = os.getenv("RANDOM_SIGNIN", "true").lower() == "true"

privacy_mode = os.getenv("PRIVACY_MODE", "true").lower() == "true"

DEFAULT_HEADERS = {
    "system-version": "16.4.1",
    "Connection": "keep-alive",
    "system": "iOS",
    "Accept-Encoding": "gzip, deflate, br",
    "app-version": "3.5.6",
    "device-id": "00000000-0000-0000-0000-000000000000",
    "deviceId": "00000000-0000-0000-0000-000000000000",
    "source": "CD-METRO-APP",
    "User-Agent": "CDMetro/3.5.6 (iPhone; iOS 16.4.1; Scale/3.00)",
    "vendor": "iPhone15,3",
    "language": "zh-Hans",
    "Host": "app.cdmetro.chengdurail.cn",
    "Accept-Language": "zh-Hans-US;q=1, en-US;q=0.9",
    "Accept": "*/*",
    "user": "external",
}


def push(contents: str):
    if hadsend:
        try:
            send(SCRIPT_NAME, contents)
            print("✅ notify.py推送成功")
        except Exception as e:
            print(f"❌ notify.py推送失败: {e}")
    else:
        print(f"📢 {SCRIPT_NAME}\n{contents}")


def mask_text(text: str, head: int = 4, tail: int = 4) -> str:
    if not privacy_mode or not text:
        return text
    if len(text) <= head + tail:
        return "*" * len(text)
    return text[:head] + "*" * (len(text) - head - tail) + text[-tail:]


def format_time_remaining(seconds: int) -> str:
    if seconds <= 0:
        return "立即执行"
    hours, minutes = divmod(seconds, 3600)
    minutes, secs = divmod(minutes, 60)
    if hours > 0:
        return f"{hours}小时{minutes}分{secs}秒"
    if minutes > 0:
        return f"{minutes}分{secs}秒"
    return f"{secs}秒"


def wait_with_countdown(delay_seconds: int):
    if delay_seconds <= 0:
        return
    remaining = delay_seconds
    while remaining > 0:
        if remaining <= 10 or remaining % 10 == 0:
            print(f"倒计时: {format_time_remaining(remaining)}")
        sleep_time = 1 if remaining <= 10 else min(10, remaining)
        time.sleep(sleep_time)
        remaining -= sleep_time


def build_session() -> requests.Session:
    session = requests.Session()
    retries = Retry(
        total=max_retries,
        backoff_factor=1,
        status_forcelist=[500, 502, 503, 504],
        allowed_methods=["GET", "POST"],
    )
    adapter = HTTPAdapter(max_retries=retries)
    session.mount("http://", adapter)
    session.mount("https://", adapter)
    return session


def parse_accounts(env_value: str):
    if not env_value:
        return []

    env_value = env_value.strip()

    def _parse_one(raw: str):
        """解析单个账号：JSON 或 querystring"""
        if raw.startswith("{") and raw.endswith("}"):
            return json.loads(raw)  # 解析失败直接抛出，由调用方报错
        data = {}
        for part in raw.split("&"):
            if "=" not in part:
                continue
            k, v = part.split("=", 1)
            data[k.strip()] = v.strip()
        if not data:
            raise ValueError("querystring 格式为空或无效")
        return data

    # 整个值是单个 JSON 对象（不按分隔符拆）
    if env_value.startswith("{") and env_value.endswith("}"):
        try:
            return [json.loads(env_value)]
        except json.JSONDecodeError as e:
            print(f"❌ 单账号 JSON 解析失败: {e}")
            return []

    accounts = []
    raw_list = [x.strip() for x in re.split(r"[\n@]", env_value) if x.strip()]
    for raw in raw_list:
        try:
            accounts.append(_parse_one(raw))
        except Exception as e:
            print(f"❌ 账号解析失败: {raw[:20]}... {e}")
    return accounts


def build_headers(account_data: dict) -> dict:
    headers = DEFAULT_HEADERS.copy()

    # 允许用户传入完整 headers；同时兼容 cookie/token/app-token 等关键字段写法
    for k, v in (account_data or {}).items():
        if v is None:
            continue
        headers[k] = v
        lk = str(k).lower()
        if lk == "cookie":
            headers["Cookie"] = v
        elif lk == "token":
            headers["token"] = v
        elif lk in ("app-token", "apptoken", "app_token"):
            headers["app-token"] = v
        elif lk in ("deviceid", "device-id", "device_id"):
            # 默认 headers 同时存在 deviceId / device-id，通常两者需保持一致
            headers["deviceId"] = v
            headers["device-id"] = v

    return headers


def cdrail_signin(session: requests.Session, headers: dict):
    if not headers.get("token") or not headers.get("app-token"):
        missing = []
        if not headers.get("token"):
            missing.append("token")
        if not headers.get("app-token"):
            missing.append("app-token")
        return "invalid", f"缺少字段: {', '.join(missing)}"

    url = "https://app.cdmetro.chengdurail.cn/platform/users/user/sign-in-integral"
    try:
        resp = session.get(url, headers=headers, timeout=timeout)
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        return "error", f"请求异常: {e}"

    code = data.get("code")
    msg = data.get("msg") or data.get("message") or "无消息"

    if str(code) in ["0", "200", "000000"]:
        inc = None
        if isinstance(data.get("data"), dict):
            inc = data["data"].get("integralIncrement")
        if inc is not None:
            return "success", f"{msg} (+{inc})"
        return "success", msg

    if "已签到" in str(msg) or "重复签到" in str(msg) or str(code) in ["1102"]:
        return "already", msg

    return "fail", f"{msg} (Code: {code})"


def main():
    env_val = os.getenv(ENV_NAME, "")
    accounts = parse_accounts(env_val)

    if not accounts:
        print(f"❌ 未检测到账号，请设置环境变量 {ENV_NAME}")
        print('示例: export CDRAIL_DATA=\'{"token":"xxx","app-token":"yyy","Cookie":"zzz"}\'')
        sys.exit(0)

    print(f"✅ 检测到 {len(accounts)} 个账号")

    if random_signin and max_random_delay > 0:
        delay_seconds = random.randint(0, max_random_delay)
        if delay_seconds > 0:
            signin_time = datetime.now() + timedelta(seconds=delay_seconds)
            print(f"随机模式: 延迟 {format_time_remaining(delay_seconds)} 后签到")
            print(f"预计签到时间: {signin_time.strftime('%H:%M:%S')}")
            wait_with_countdown(delay_seconds)

    msg_lines = []
    success_count = 0

    for idx, account_data in enumerate(accounts, start=1):
        try:
            headers = build_headers(account_data)
            token_preview = mask_text(str(headers.get("token", "")), 6, 6)
            print(f"\n==== 开始第{idx}个账号签到 ====")
            if token_preview:
                print(f"Token: {token_preview}")

            session = build_session()
            status, info = cdrail_signin(session, headers)
            session.close()

            if status in ("success", "already"):
                success_count += 1
                prefix = "✅" if status == "success" else "🟡"
                msg_lines.append(f"{prefix} 账号{idx}: {info}")
            else:
                msg_lines.append(f"❌ 账号{idx}: {info}")
        except Exception as e:
            msg_lines.append(f"❌ 账号{idx}: 执行异常 - {e}")
            print(f"❌ 账号{idx}: 执行异常 - {e}")

        if idx < len(accounts):
            time.sleep(random.uniform(3, 8))

    msg_lines.append(f"\n统计: 共{len(accounts)}个, 成功{success_count}个")
    content = "\n".join(msg_lines)

    print("\n" + content)
    push(content)


if __name__ == "__main__":
    print(f"==== {SCRIPT_NAME}开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
    main()
