# Check-in Scripts

> A collection of Python check-in scripts for the QingLong panel, covering cloud drives, forums, life/services and more.

[English] | [中文](README.md)

## Introduction

This repository collects and maintains a set of Python check-in scripts for the QingLong panel. They share a consistent style and hardened error handling, and can be deployed directly. Each script runs independently, reads accounts from environment variables, and supports multiple accounts with randomized delays.

## Features

- 🎯 **Multi-platform** — cloud drives, forums/communities, life/services, e-commerce, etc.
- 🔧 **Unified config** — every script reads accounts from environment variables with a consistent format
- 🛡️ **Hardened** — per-account error isolation, automatic fallback on endpoint failure, graceful degradation for optional dependencies
- 📝 **Documented** — credential acquisition and format for each platform are described below and in [DEPLOY.md](./DEPLOY.md)

## Directory Structure

```
Cloud-Drive-Check-in/
├── LICENSE                  # Open-source license
├── README.md                # Chinese documentation
├── README_EN.md             # English documentation
├── DEPLOY.md                # Deployment & configuration guide
└── scripts/                 # All check-in scripts (categorized)
    ├── netdisk/             # Cloud drives
    │   ├── aliyunpan_checkin.py
    │   ├── baiduwangpan_checkin.py
    │   ├── quark_checkin.py
    │   └── ty_netdisk_checkin.py
    ├── forum/               # Forums / communities
    │   ├── enshan_checkin.py
    │   ├── nodeseek_checkin.py
    │   ├── ikuuu_checkin.py
    │   ├── nga_checkin.py
    │   ├── hifiti_checkin.py
    │   ├── leaflow_checkin.py
    │   └── tieba_checkin.py
    ├── life/                # Life / travel / e-commerce
    │   ├── cdrail_checkin.py
    │   ├── sfsu_checkin.py
    │   ├── tsthb_checkin.py
    │   └── passnat_checkin.py
    ├── misc/                # Others
    │   ├── deepflood_checkin.py
    │   └── smzdm_checkin.py
    └── archive/             # Legacy versions (reference only, not scheduled)
```

## Quick Start

> 📌 Deployment flow, per-platform credential acquisition, formats and security notes: see **[DEPLOY.md](./DEPLOY.md)**.

### Requirements

- QingLong Panel 2.10+ (the panel itself is Node.js based; scripts run on the panel's built-in Python 3)
- All scripts only require `requests` (bundled with QingLong); no extra setup needed
- Optional dependency: `curl_cffi` (TLS impersonation for nodeseek / deepflood / leaflow; falls back to plain `requests` when missing)

### Optional dependency (QingLong Panel → Dependencies → Add Python3 dependency)

```
curl_cffi
```

> Note: without `curl_cffi` the scripts still run; however, sites with Cloudflare TLS
> fingerprint checks (e.g. deepflood) may reject plain requests and the check-in will fail.

### Installation

1. **Get the repository**
   ```bash
   # Option A: Git clone
   git clone https://github.com/wudicyg/Cloud-Drive-Check-in.git

   # Option B: QingLong Panel "Subscription" — add subscription
   # URL: https://github.com/wudicyg/Cloud-Drive-Check-in.git
   ```
2. **(Optional) Configure notifications**
   Notifications use QingLong's built-in `notify.py`, supporting ServerChan, Push+, DingTalk, Bark, Telegram, etc.
   Related environment variables (e.g. `TG_BOT_TOKEN`, `PUSH_KEY`, `DD_BOT_TOKEN`, `BARK_PUSH`) are configured per the QingLong documentation. When not configured, scripts only print logs and do not push.
3. **Configure environment variables**
   Add the variables for each platform (see the "Platform Configuration" tables below) in QingLong's environment variable page.
4. **Create scheduled tasks**
   Create a cron task for each script you want to use, pointing the command at the file, e.g.:
   `task /ql/data/scripts/Cloud-Drive-Check-in/scripts/netdisk/aliyunpan_checkin.py`

### Platform Configuration

#### 🏔️ Enshan Forum

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `enshan_cookie` | Enshan forum cookie | **Required** | `full cookie string` | Single account cookie (note: lowercase name) |

#### 📱 NodeSeek

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `NODESEEK_COOKIE` | NodeSeek website cookie | **Required** | `cookie1&cookie2&cookie3` | Separate multiple accounts with `&` |
| `NS_RANDOM` | Random sign-in param | Optional | `true` | Default; usually no change needed |

#### ☁️ Quark Drive

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `QUARK_COOKIE` | Quark Drive cookie | **Required** | `cookie1&&cookie2` | Separate multiple accounts with `&&` or newline |

#### 🚇 Chengdu Metro

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `CDRAIL_DATA` | Chengdu Metro request data (from captured headers) | **Required** | `{"token":"xxx","app-token":"yyy","Cookie":"zzz"}` | JSON or `token=...&app-token=...&cookie=...`; multiple accounts with newline or `@` |

`CDRAIL_DATA` fields (recommended to copy directly from captured request headers):

| Field | Required | Notes |
|-------|----------|-------|
| `token` | **Required** | `token` from request header |
| `app-token` | **Required** | `app-token` from request header |
| `Cookie` / `cookie` | **Required** | Logged-in cookie (case handled automatically) |
| `deviceId` / `device-id` | Suggested | Device id; prefer your own captured value |

```bash
# JSON single account (recommended)
export CDRAIL_DATA='{"token":"xxx","app-token":"yyy","Cookie":"zzz","deviceId":"xxx-xxx"}'

# querystring single account
export CDRAIL_DATA='token=xxx&app-token=yyy&cookie=zzz&deviceId=xxx-xxx'

# multiple accounts: newline or @ separated
export CDRAIL_DATA='{"token":"t1","app-token":"a1","Cookie":"c1","deviceId":"d1"}
{"token":"t2","app-token":"a2","Cookie":"c2","deviceId":"d2"}'
```

Optional variables:

| Variable | Description | Default | Notes |
|--------|-------------|---------|-------|
| `TIMEOUT` | Per-request timeout (s) | `15` | Increase if network is slow |
| `MAX_RETRIES` | 5xx auto-retry count | `3` | Exponential backoff |

#### 📦 SF Express

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `sfsyUrl` | SF Express login URL | **Required** | `https://mcs-mimp...` | Capture from traffic; newline for multiple |

#### Baidu Tieba

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `TIEBA_COOKIE` | Baidu Tieba cookie | **Required** | `BDUSS=xxxxxx; STOKEN=xxxxx...` | Full cookie string; newline for multiple |

#### ☁️ Aliyun Drive

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `ALIYUN_REFRESH_TOKEN` | Aliyun Drive refresh_token | **Required** | `crsh166bdfde4751a4c0...` | Newline for multiple accounts |
| `AUTO_UPDATE_TOKEN` | Auto-update token | Optional | `true` | Default `true`, maintains token automatically |
| `PRIVACY_MODE` | Privacy mode | Optional | `true` | Default `true`, masks sensitive info |

#### 🛒 SMZDM

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `SMZDM_COOKIE` | SMZDM cookie | **Required** | `__ckguid==xxxxx; device_id=xxxxx...` | Full cookie; newline for multiple |

#### 🍔 Tastientech (TSTHB)

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `tsthbck` | Tastientech user-token | **Required** | `xxxxx` | Capture from WeChat mini-program; newline for multiple |

#### 🎶 HiFiTi / HiFiHi

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `HiFiTi_COOKIE` | HiFiTi cookie | Optional | `xxxxx` | Multiple accounts, newline separated |
| `HIFIHI_COOKIE` | HiFiHi cookie | Optional | `xxxxx` | Multiple accounts, newline separated |

#### ☁️ Baidu Netdisk

| Variable | Description | Example |
|--------|-------------|---------|
| `BAIDU_COOKIE` | Website cookie | `BDUSS=xxx; STOKEN=xxx...` |
| `PRIVACY_MODE` | Privacy mode | `true` |

#### 📡 ikuuu

| Variable | Description | Example |
|--------|-------------|---------|
| `IKUUU_EMAIL` | Login email | `user@example.com` |
| `IKUUU_PASSWD` | Login password | `password123` |
| `IKUUU_BASE` | Custom site URL | `https://ikuuu.nl` | Optional; default probes `ikuuu.nl` → `ikuuu.de` → `ikuuu.la` in order |

> Note: ikuuu domains change from time to time; the script probes candidate domains automatically and switches when one fails.

#### ☁️ Tianyi Cloud Drive

| Variable | Description | Example | Notes |
|--------|-------------|---------|-------|
| `TY_USERNAME` | Login phone number | `13812345678\n13987654321` | Newline for multiple |
| `TY_PASSWORD` | Login password | `password1\npassword2` | |

#### 🎮 NGA Forum

| Variable | Description | Example |
|--------|-------------|---------|
| `NGA_CREDENTIALS` | UID,AccessToken | `12345678,abcdef...` |
| `NGA_UA` | Custom User-Agent | `Nga_Official/90409` | Optional, default `Nga_Official/90409` |

#### 📱 deepflood

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `DEEPFLOOD_COOKIE` | DEEPFLOOD website cookie | **Required** | `cookie1&cookie2&cookie3` | Separate multiple accounts with `&` |
| `DF_RANDOM` / `NS_RANDOM` | Random sign-in param | Optional | `true` | Default; both names accepted |

#### ☁️ leaflow

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `LEAFLOW_COOKIE` | leaflow website cookie | **Required** | `cookie` | Newline for multiple |
| `LEAFLOW_BASE` | Custom site URL | Optional | `https://checkin.leaflow.net` | Default tries `checkin.leaflow.net` then `console.leaflow.net` |

> ⚠️ **leaflow has migrated**: the old check-in site `checkin.leaflow.net` now redirects to the
> new console at `console.leaflow.net`. If you keep seeing "Cookie expired / all retries failed",
> log in again and copy the **new console cookie** from your browser dev tools.

#### 🌐 PassNAT

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `PASSNAT_SK` | PassNAT API key | **Required** | `sk_xxxxx` | Newline for multiple |

#### ⏰ Randomization (shared by all scripts)

| Variable | Description | Required | Example | Notes |
|--------|-------------|----------|---------|-------|
| `RANDOM_SIGNIN` | Enable randomized sign-in | Optional | `true` | `true` enables, `false` disables |
| `MAX_RANDOM_DELAY` | Random delay window (s) | Optional | `3600` | `3600`=1h, `1800`=30m |

## Credential Acquisition

#### Enshan Forum Cookie
1. Visit [Enshan Forum](https://www.right.com.cn/FORUM/) and sign in
2. F12 → Network → refresh the page
3. Copy the full `Cookie` from the request headers

#### NodeSeek Cookie
1. Visit [nodeseek.com](https://www.nodeseek.com) and sign in
2. F12 → Network → refresh
3. Copy the full `Cookie` from request headers

#### Deepflood Cookie
1. Visit [deepflood.com](https://www.deepflood.com) and sign in
2. F12 → Network → refresh
3. Copy the full `Cookie` from request headers

#### Quark Drive Cookie
1. Visit [Quark Drive](https://pan.quark.cn/) and sign in
2. F12 → Network → refresh
3. Copy the full `Cookie` from request headers

#### SF Express sfsyUrl
1. Bind WeChat in SF app, then add the bot and send "顺丰"
2. Open the mini-program or app → Me → Points, capture one of these URLs:
   - `https://mcs-mimp-web.sf-express.com/mcs-mimp/share/weChat/shareGiftReceiveRedirect`
   - `https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/shareRedirect`
3. URL-encode the captured URL with a tool such as [URL Encoder](https://www.toolhelper.cn/EncodeDecode/Url)

#### Baidu Tieba Cookie
1. Visit [tieba.baidu.com](https://tieba.baidu.com) and sign in
2. F12 → Network → refresh
3. Copy the full `Cookie`, ensure it contains `BDUSS`

#### Aliyun Drive refresh_token
1. Visit [Aliyun Drive Web](https://www.aliyundrive.com/) and sign in
2. F12 → `Application` tab
3. Local Storage → `https://www.aliyundrive.com`
4. Find `token`, copy the `refresh_token` value

#### SMZDM Cookie
1. Visit [SMZDM](https://www.smzdm.com/) and sign in
2. F12 → `Network` tab
3. Refresh, find any request's `Request Headers`
4. Copy the full `Cookie` value

#### Baidu Netdisk Cookie
1. Visit [Baidu Netdisk](https://pan.baidu.com/) and sign in
2. F12 → Network → copy Cookie

#### ikuuu Configuration
1. Add env `IKUUU_EMAIL` (email) in QingLong
2. Add env `IKUUU_PASSWD` (password)
3. Multiple accounts comma-separated: `email1,email2`; password order matches email order

#### Tianyi Cloud Drive Configuration
1. Visit [Tianyi Cloud Drive](https://e.dlife.cn/index.do) and sign in, disable device lock
2. Add env `TY_USERNAME` (phone number)
3. Add env `TY_PASSWORD` (password)

#### leaflow Configuration
1. Visit the new console [console.leaflow.net](https://console.leaflow.net/) and sign in
2. F12 → Network → refresh
3. Copy the full `Cookie` from any authenticated request (new console uses `leaflow_session`, `XSRF-TOKEN`, etc.; the old `PHPSESSID` method is retired)
4. Set `LEAFLOW_COOKIE`
5. Use `LEAFLOW_BASE` for a custom site URL if needed

#### PassNAT API Key
1. Visit [PassNAT](https://www.passnat.com/) and sign in
2. Profile → API Key
3. Generate or copy an existing key
4. Set `PASSNAT_SK` (format `SK_xxxxx`); newline for multiple

#### NGA Forum Configuration
1. Install a traffic capture tool with HTTPS decryption (Android: HTTP Canary, HttpToolkit, mitmproxy, Charles; iOS: Stream, Charles) and trust its CA
2. Point the phone's proxy to the capture tool (or use its VPN/proxy mode)
3. Open the NGA app (logged in) and trigger a request (e.g. open home / check-in)
4. Find the POST request to `https://ngabbs.com/nuke.php`
5. In its request body (`application/x-www-form-urlencoded`), copy: `access_uid`=your UID; `access_token`=long string
6. Set `NGA_CREDENTIALS` as `UID,AccessToken`
   Single: `123456,abcdefg`
   Multiple (newline):
   ```
   123456,abcdefg
   234567,hijklmn
   ```

## Configuration Example

```bash
# Randomization (optional)
RANDOM_SIGNIN=true
MAX_RANDOM_DELAY=3600
```

## License

Released under the [MIT License](LICENSE).
