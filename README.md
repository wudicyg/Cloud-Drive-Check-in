# 签到脚本库（Check-in Scripts）

> 面向青龙面板的 Python 签到脚本合集，覆盖网盘、论坛社区、生活出行等平台的自动签到。

中文 | [English](README_EN.md)

## 项目简介

本仓库收集并维护一组用于青龙面板的 Python 签到脚本，统一风格、容错加固，便于直接部署使用。每个脚本独立运行，通过环境变量配置账号，支持多账号与随机延迟。

## 功能特性

- 🎯 **多平台覆盖** — 网盘、论坛社区、生活出行、电商等
- 🔧 **统一配置** — 各脚本均通过环境变量读取账号，格式一致
- 🛡️ **容错加固** — 单账号异常隔离、接口失效自动切换、可选依赖优雅回退
- 📝 **文档齐全** — 每个平台的凭证获取与格式说明见下文与 [DEPLOY.md](./DEPLOY.md)

## 目录结构

```
Cloud-Drive-Check-in/
├── LICENSE                  # 开源许可证
├── README.md                # 中文说明
├── README_EN.md             # 英文说明
├── DEPLOY.md                # 部署与配置指南
└── scripts/                 # 全部签到脚本（按类别分目录）
    ├── netdisk/             # 网盘类
    │   ├── aliyunpan_checkin.py
    │   ├── baiduwangpan_checkin.py
    │   ├── quark_checkin.py
    │   └── ty_netdisk_checkin.py
    ├── forum/               # 论坛 / 社区类
    │   ├── enshan_checkin.py
    │   ├── nodeseek_checkin.py
    │   ├── ikuuu_checkin.py
    │   ├── nga_checkin.py
    │   ├── hifiti_checkin.py
    │   ├── leaflow_checkin.py
    │   └── tieba_checkin.py
    ├── life/                # 生活 / 出行 / 电商类
    │   ├── cdrail_checkin.py
    │   ├── sfsu_checkin.py
    │   ├── tsthb_checkin.py
    │   └── passnat_checkin.py
    ├── misc/                # 其它
    │   ├── deepflood_checkin.py
    │   └── smzdm_checkin.py
    └── archive/             # 历史版本存档（仅供参考，不参与运行）
```

## 快速开始

> 📌 部署流程、各平台凭证获取方式、格式与安全注意事项，详见 **[DEPLOY.md](./DEPLOY.md)**。

### 环境要求

- 青龙面板 2.10+（面板基于 Node.js，脚本为 Python 3，由面板内置 Python 环境执行）
- 所有脚本仅依赖 `requests`（青龙默认自带），无需额外安装
- 可选依赖：`curl_cffi`（nodeseek / deepflood / leaflow 的 TLS 指纹伪装，未安装时自动回退普通 requests）

### 可选依赖安装（青龙面板 → 依赖管理 → 新建 Python3 依赖）

```
curl_cffi
```

> 说明：不安装 `curl_cffi` 时脚本仍可正常运行；但对启用了 Cloudflare TLS 指纹校验的站点
> （如 deepflood），普通 requests 可能被拦截，签到会失败并提示风控。

### 安装步骤

1. **获取仓库**
   ```bash
   # 方式一：Git 克隆
   git clone https://github.com/wudicyg/Cloud-Drive-Check-in.git

   # 方式二：青龙面板「订阅管理」中添加订阅
   # 订阅地址：https://github.com/wudicyg/Cloud-Drive-Check-in.git
   ```
2. **（可选）配置通知**
   通知通过青龙内置的 `notify.py` 实现，支持 Server 酱、Push+、钉钉、Bark、Telegram 等。
   相关环境变量（如 `TG_BOT_TOKEN`、`PUSH_KEY`、`DD_BOT_TOKEN`、`BARK_PUSH` 等）按青龙文档配置即可，未配置时脚本仅打印日志、不推送。
3. **配置环境变量**
   各平台所需变量见下方「平台配置」表格，在青龙「环境变量」中逐平台添加。
4. **创建定时任务**
   对每个要使用的脚本新建定时任务，命令指向对应文件，例如：
   `task /ql/data/scripts/Cloud-Drive-Check-in/scripts/netdisk/aliyunpan_checkin.py`

### 平台配置

#### 🏔️ 恩山论坛

| 变量名            | 说明           | 是否必需 | 示例值           | 备注         |
| ----------------- | -------------- | -------- | ---------------- | ------------ |
| `enshan_cookie` | 恩山论坛 Cookie | **必需** | `完整的Cookie字符串` | 单账号 Cookie（变量名小写） |

#### 📱 NodeSeek

| 变量名              | 说明               | 是否必需 | 示例值                      | 备注               |
| ------------------- | ------------------ | -------- | --------------------------- | ------------------ |
| `NODESEEK_COOKIE` | NodeSeek 网站 Cookie | **必需** | `cookie1&cookie2&cookie3` | 多账号用 `&` 分隔 |
| `NS_RANDOM`       | 签到随机参数       | 可选     | `true`                    | 默认值，通常无需修改 |

#### ☁️ 夸克网盘

| 变量名           | 说明           | 是否必需 | 示例值                | 备注                        |
| ---------------- | -------------- | -------- | --------------------- | --------------------------- |
| `QUARK_COOKIE` | 夸克网盘 Cookie | **必需** | `cookie1&&cookie2`  | 多账号用 `&&` 或换行分隔 |

#### 🚇 成都地铁

| 变量名          | 说明                                    | 是否必需 | 示例值                                               | 备注                                                                  |
| --------------- | --------------------------------------- | -------- | ---------------------------------------------------- | --------------------------------------------------------------------- |
| `CDRAIL_DATA` | 成都地铁请求数据（从抓包 headers 提取） | **必需** | `{"token":"xxx","app-token":"yyy","Cookie":"zzz"}` | 支持 `JSON` 或 `token=...&app-token=...&cookie=...`；多账号用换行或 `@` 分隔 |

`CDRAIL_DATA` 需要包含的字段（建议直接从抓包请求头复制/提取）：

| 字段                         | 是否必需 | 说明                                    |
| ---------------------------- | -------- | --------------------------------------- |
| `token`                    | **必需** | 请求头里的 `token`                    |
| `app-token`                | **必需** | 请求头里的 `app-token`                |
| `Cookie` / `cookie`      | **必需** | 登录后的 Cookie（脚本会自动兼容大小写） |
| `deviceId` / `device-id` | 建议     | 设备标识；推荐用你自己抓包到的设备 ID   |

```bash
# JSON 单账号（推荐）
export CDRAIL_DATA='{"token":"xxx","app-token":"yyy","Cookie":"zzz","deviceId":"xxx-xxx"}'

# querystring 单账号
export CDRAIL_DATA='token=xxx&app-token=yyy&cookie=zzz&deviceId=xxx-xxx'

# 多账号：换行 或 @ 分割
export CDRAIL_DATA='{"token":"t1","app-token":"a1","Cookie":"c1","deviceId":"d1"}
{"token":"t2","app-token":"a2","Cookie":"c2","deviceId":"d2"}'
```

可选变量：

| 变量名          | 说明                 | 默认值 | 备注             |
| --------------- | -------------------- | ------ | ---------------- |
| `TIMEOUT`     | 单次请求超时（秒）   | `15` | 网络较慢时可调大 |
| `MAX_RETRIES` | 5xx 错误自动重试次数 | `3`  | 指数退避重试     |

#### 📦 顺丰速运

| 变量名      | 说明            | 是否必需 | 示例值                  | 备注                 |
| ----------- | --------------- | -------- | ----------------------- | -------------------- |
| `sfsyUrl` | 顺丰速运登录 URL | **必需** | `https://mcs-mimp...` | 抓包获取，多账号换行 |

#### 百度贴吧

| 变量名           | 说明           | 是否必需 | 示例值                            | 备注                           |
| ---------------- | -------------- | -------- | --------------------------------- | ------------------------------ |
| `TIEBA_COOKIE` | 百度贴吧 Cookie | **必需** | `BDUSS=xxxxxx; STOKEN=xxxxx...` | 完整的 Cookie 字符串，多账号换行 |

#### ☁️ 阿里云盘

| 变量名                   | 说明                  | 是否必需 | 示例值                      | 备注                            |
| ------------------------ | --------------------- | -------- | --------------------------- | ------------------------------- |
| `ALIYUN_REFRESH_TOKEN` | 阿里云盘 refresh_token | **必需** | `crsh166bdfde4751a4c0...` | 多账号用换行分隔                 |
| `AUTO_UPDATE_TOKEN`    | 自动更新 Token         | 可选     | `true`                    | 默认 `true`，自动维护 token    |
| `PRIVACY_MODE`         | 隐私保护模式          | 可选     | `true`                    | 默认 `true`，脱敏显示敏感信息 |

#### 🛒 什么值得买

| 变量名           | 说明             | 是否必需 | 示例值                                  | 备注                       |
| ---------------- | ---------------- | -------- | --------------------------------------- | -------------------------- |
| `SMZDM_COOKIE` | 什么值得买 Cookie | **必需** | `__ckguid==xxxxx; device_id=xxxxx...` | 完整 Cookie，多账号换行分隔 |

#### 🍔 塔斯汀汉堡

| 变量名           | 说明                | 是否必需 | 示例值  | 备注                         |
| ---------------- | ------------------- | -------- | ------- | ---------------------------- |
| `tsthbck` | 塔斯汀汉堡 user-token | **必需** | `xxxxx` | 微信小程序抓包获取，多账号换行分隔 |

#### 🎶 HiFiTi / HiFiHi

| 变量名           | 说明             | 是否必需 | 示例值  | 备注               |
| ---------------- | ---------------- | -------- | ------- | ------------------ |
| `HiFiTi_COOKIE` | HiFiTi 的 Cookie | 可选     | `xxxxx` | 支持多账号，换行分隔 |
| `HIFIHI_COOKIE` | HiFiHi 的 Cookie | 可选     | `xxxxx` | 支持多账号，换行分隔 |

#### ☁️ 百度网盘

| 变量名           | 说明       | 示例                         |
| ---------------- | ---------- | ---------------------------- |
| `BAIDU_COOKIE` | 网站 Cookie | `BDUSS=xxx; STOKEN=xxx...` |
| `PRIVACY_MODE` | 隐私模式   | `true`                     |

#### 📡 ikuuu

| 变量名           | 说明     | 示例                 |
| ---------------- | -------- | -------------------- |
| `IKUUU_EMAIL`  | 登录邮箱 | `user@example.com` |
| `IKUUU_PASSWD` | 登录密码 | `password123`      |
| `IKUUU_BASE`   | 自定义站点地址 | `https://ikuuu.nl` | 可选，默认按 `ikuuu.nl` → `ikuuu.de` → `ikuuu.la` 顺序自动探测可用域名 |

> 说明：ikuuu 域名会不定期更换，脚本会自动探测候选域名，单个域名失效时自动切换。

#### ☁️ 天翼云盘

| 变量名          | 说明       | 示例                        | 备注       |
| --------------- | ---------- | --------------------------- | ---------- |
| `TY_USERNAME` | 登录手机号 | `13812345678\n13987654321` | 多账号换行 |
| `TY_PASSWORD` | 登录密码   | `password1\npassword2`     |            |

#### 🎮 NGA 论坛

| 变量名              | 说明            | 示例                   |
| ------------------- | --------------- | ---------------------- |
| `NGA_CREDENTIALS` | UID,AccessToken | `12345678,abcdef...` |
| `NGA_UA`          | 自定义 User-Agent | `Nga_Official/90409` | 可选，默认 `Nga_Official/90409` |

#### 📱 deepflood

| 变量名 | 说明 | 是否必需 | 示例值 | 备注 |
|--------|------|----------|--------|------|
| `DEEPFLOOD_COOKIE` | DEEPFLOOD 网站 Cookie | **必需** | `cookie1&cookie2&cookie3` | 多账号用 `&` 分隔 |
| `DF_RANDOM` / `NS_RANDOM` | 签到随机参数 | 可选 | `true` | 默认值，通常无需修改；两个变量名均兼容 |

#### ☁️ leaflow

| 变量名             | 说明              | 是否必需 | 示例值     | 备注               |
| ------------------ | ----------------- | -------- | ---------- | ------------------ |
| `LEAFLOW_COOKIE` | leaflow 网站 Cookie | **必需** | `cookie` | 多账号用换行分隔 |
| `LEAFLOW_BASE` | 自定义站点地址    | 可选     | `https://checkin.leaflow.net` | 默认按 `checkin.leaflow.net` → `console.leaflow.net` 顺序自动尝试 |

> ⚠️ **leaflow 已改版**：旧签到站 `checkin.leaflow.net` 现在会跳转到新版控制台 `console.leaflow.net`。
> 若持续提示「Cookie 已失效/重试后失败」，请重新登录 leaflow，从浏览器开发者工具复制**新版控制台的 Cookie**
> （需包含登录会话字段，如 `leaflow_session`、`XSRF-TOKEN` 等）后重试。

#### 🌐 PassNAT

| 变量名           | 说明             | 是否必需 | 示例值      | 备注               |
| ---------------- | ---------------- | -------- | ----------- | ------------------ |
| `PASSNAT_SK` | PassNAT 接口密钥 | **必需** | `sk_xxxxx` | 多账号用换行分隔 |

#### ⏰ 随机化配置（所有脚本共用）

| 变量名               | 说明               | 是否必需 | 示例值   | 备注                            |
| -------------------- | ------------------ | -------- | -------- | ------------------------------- |
| `RANDOM_SIGNIN`    | 启用随机签到       | 可选     | `true` | `true` 启用，`false` 禁用     |
| `MAX_RANDOM_DELAY` | 随机延迟窗口（秒） | 可选     | `3600` | `3600`=1小时，`1800`=30分钟 |

## 凭证获取方式

#### 恩山论坛 Cookie
1. 浏览器访问 [恩山论坛](https://www.right.com.cn/FORUM/) 并登录
2. F12 开发者工具 → Network → 刷新页面
3. 找到请求头中的 `Cookie` 完整复制

#### NodeSeek Cookie
1. 浏览器访问 [nodeseek.com](https://www.nodeseek.com) 并登录
2. F12 开发者工具 → Network → 刷新页面
3. 找到请求头中的 `Cookie` 完整复制

#### Deepflood Cookie
1. 浏览器访问 [deepflood.com](https://www.deepflood.com) 并登录
2. F12 开发者工具 → Network → 刷新页面
3. 找到请求头中的 `Cookie` 完整复制

#### 夸克网盘 Cookie
1. 浏览器访问 [夸克网盘](https://pan.quark.cn/) 并登录
2. F12 开发者工具 → Network → 刷新页面
3. 找到请求头中的 `Cookie` 完整复制

#### 顺丰速运 sfsyUrl
1. 顺丰 APP 绑定微信后，添加机器人发送「顺丰」
2. 打开小程序或 APP-我的-积分，抓包以下 URL 之一:
   - `https://mcs-mimp-web.sf-express.com/mcs-mimp/share/weChat/shareGiftReceiveRedirect`
   - `https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/shareRedirect`
3. 抓取 URL 后，使用 [URL 编码工具](https://www.toolhelper.cn/EncodeDecode/Url) 进行编码

#### 百度贴吧 Cookie
1. 浏览器访问 [tieba.baidu.com](https://tieba.baidu.com) 并登录
2. F12 开发者工具 → Network → 刷新页面
3. 找到请求头中的完整 `Cookie` 复制
4. 确保包含 `BDUSS` 参数

#### 阿里云盘 refresh_token
1. 浏览器访问 [阿里云盘网页版](https://www.aliyundrive.com/) 并登录
2. 按 `F12` 打开开发者工具 → `Application` 标签页
3. 左侧找到 `Local Storage` → `https://www.aliyundrive.com`
4. 找到 `token` 项，复制 `refresh_token` 的值

#### 什么值得买 Cookie
1. 浏览器访问 [什么值得买](https://www.smzdm.com/) 并登录
2. 按 `F12` 打开开发者工具 → `Network` 标签页
3. 刷新页面，找到任意请求的 `Request Headers`
4. 复制完整的 `Cookie` 值

#### 百度网盘 Cookie
1. 访问 [百度网盘](https://pan.baidu.com/) 登录
2. F12 → Network → 复制 Cookie

#### Ikuuu 配置
1. 在青龙面板中添加环境变量 `IKUUU_EMAIL`（邮箱地址）
2. 在青龙面板中添加环境变量 `IKUUU_PASSWD`（对应密码）
3. 多账号用英文逗号分隔: `email1,email2`，密码顺序与邮箱顺序对应

#### 天翼云盘配置
1. 浏览器访问 [天翼云盘](https://e.dlife.cn/index.do) 并登录，关闭设备锁
2. 在青龙面板中添加环境变量 `TY_USERNAME`（手机号）
3. 在青龙面板中添加环境变量 `TY_PASSWORD`（对应密码）

#### leaflow 配置
1. 浏览器访问新版控制台 [console.leaflow.net](https://console.leaflow.net/) 并登录
2. 按 F12 打开开发者工具 → Network → 刷新页面
3. 复制任意已登录请求的完整 `Cookie`（新版控制台使用 `leaflow_session`、`XSRF-TOKEN` 等会话 Cookie；旧站基于 `PHPSESSID` 的获取方式已失效）
4. 填入环境变量 `LEAFLOW_COOKIE`
5. 如访问不稳定，可用 `LEAFLOW_BASE` 自定义站点地址

#### PassNAT 接口密钥
1. 浏览器访问 [PassNAT](https://www.passnat.com/) 并登录
2. 进入 **个人中心** → **接口密钥** 页面
3. 点击 **生成密钥** 或复制已有的密钥
4. 将获取到的 `SK_xxxxx` 格式的密钥填入环境变量
5. 多账号用户可生成多个密钥，换行分隔填写

#### NGA 论坛配置
1. 安装抓包工具并开启 HTTPS 解密，安装并信任证书（Android：HTTP Canary、HttpToolkit、mitmproxy、Charles；iOS：Stream、Charles）
2. 将手机的网络代理指向抓包工具（或使用工具的本机 VPN/代理模式）
3. 打开 NGA 官方 App，确保已登录；在 App 内随便执行一个操作（进入首页/签到等）触发请求
4. 在抓包记录中找到对以下地址的 POST 请求： `https://ngabbs.com/nuke.php`
5. 打开该请求的请求体（Content-Type 一般是 `application/x-www-form-urlencoded`），复制以下参数的值：`access_uid`=你的 UID；`access_token`=一串长字符串
6. 将上述两者按「UID,AccessToken」格式填写为环境变量 `NGA_CREDENTIALS`
   单账号示例：`123456,abcdefg`
   多账号用换行分隔：
   ```
   123456,abcdefg
   234567,hijklmn
   ```

## 配置示例

```bash
# 随机化配置（可选）
RANDOM_SIGNIN=true
MAX_RANDOM_DELAY=3600
```

## 许可证

本项目基于 [MIT License](LICENSE) 开源协议发布。
