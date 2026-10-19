# 部署指南（青龙面板）

本指南说明如何将本项目（`Cloud-Drive-Check-in`）部署到青龙面板并正确配置各平台签到任务。

> 核心结论：**脚本可以直接部署运行，无需预先准备任何凭证**。缺少某平台凭证时，该平台会安全"空跑"（打印提示并退出），不影响其余平台与面板稳定性。要真正完成签到，再按需补齐对应凭证即可。

---

## 一、前置条件

| 项 | 要求 | 说明 |
|----|------|------|
| 青龙面板 | 2.10+ | 面板自带 Python 3 运行环境，脚本由其内置 Python 执行 |
| Python 依赖 | `requests` | 青龙默认已安装；若缺失在 `依赖管理` 添加 |
| 可选依赖 | `curl_cffi` | 仅 deepflood / nodeseek / leaflow 的 TLS 指纹伪装需要；**不装也能运行**，但这几个站点可能被 Cloudflare 风控拦截而签到失败 |
| 通知模块 | `notify.py`（可选） | 仓库未附带；缺失时脚本自动降级为控制台打印，不崩溃。如需推送通知，请自行放入官方 `notify.py` |
| 平台凭证 | 见下表 | 缺哪个平台的凭证，哪个平台就空跑 |

---

## 二、各脚本所需凭证与获取方式

> ⚠️ **重要纠正**：阿里云盘 **不需要 Cookie**，它需要的是 `ALIYUN_REFRESH_TOKEN`（从网页端 Local Storage 取得的 refresh_token），与浏览器登录 Cookie 不同。

| 脚本 | 必需环境变量 | 类型 | 多账号分隔 | 获取方式 |
|------|-------------|------|-----------|---------|
| `aliyunpan_checkin.py` | `ALIYUN_REFRESH_TOKEN` | **refresh_token（非 cookie）** | 换行 | 登录 aliyundrive.com → F12 → Application → Local Storage → `token` → 复制其中的 `refresh_token` |
| `baiduwangpan_checkin.py` | `BAIDU_COOKIE` | Cookie | 换行 | 登录 pan.baidu.com → F12 → Network 复制完整 Cookie |
| `CDRail.py` | `CDRAIL_DATA` | JSON `{"token","app-token","Cookie"}` | 换行或 `@` | 成都地铁 App 抓包 |
| `deepflood_checkin.py` | `DEEPFLOOD_COOKIE` | Cookie | 换行 / `&` | 登录后复制 Cookie |
| `enshan_checkin.py` | `enshan_cookie` **（注意是小写！）** | Cookie | 换行 / `&&` | 登录恩山论坛后复制完整 Cookie |
| `HiFiti_checkin.py` | `HiFiTi_COOKIE`、`HIFIHI_COOKIE` | Cookie | 换行 | 两站分别抓取 Cookie |
| `ikuuu_checkin.py` | `IKUUU_EMAIL`、`IKUUU_PASSWD` | 账号 + 密码 | 两变量各换行（按行序配对） | 注册账号与密码 |
| `leaflow_checkin.py` | `LEAFLOW_COOKIE` | Cookie | 换行 / `&` | 新版控制台 console.leaflow.net 登录后复制（旧 `PHPSESSID` 站点已失效） |
| `nga_checkin.py` | `NGA_CREDENTIALS`（`UID,AccessToken`） | 复合 | 换行 | 个人设置页获取 UID 与 AccessToken |
| `nodeseek_checkin.py` | `NODESEEK_COOKIE` | Cookie | 换行 / `&` | 登录后复制 Cookie |
| `passnat_checkin.py` | `PASSNAT_SK` | sk 密钥 | 换行 | 账户后台获取 |
| `quark_signin.py` | `QUARK_COOKIE` | Cookie | 换行 | 登录 pan.quark.cn 复制 Cookie |
| `SFSU_checkin.py` | `sfsyUrl` | URL 编码 token | 换行 | 顺丰速运 App 抓包 |
| `SMZDM_checkin.py` | `SMZDM_COOKIE` | Cookie | 换行 | 登录 smzdm.com 复制 Cookie |
| `tieba_checkin.py` | `TIEBA_COOKIE` | Cookie | 换行 | 登录 tieba.baidu.com 复制 Cookie |
| `tsthb_checkin.py` | `tsthbck` | user-token | 换行 | 微信小程序抓 `sss-web.tastientech.com` 请求头中的 user-token |
| `ty_netdisk_checkin.py` | `TY_USERNAME`、`TY_PASSWORD` | 账号 + 密码 | 两变量各 `&` 配对 | 天翼云盘账号密码（RSA 已内置纯标准库实现，无需额外依赖） |

### 通用可选变量

| 变量 | 默认值 | 作用 |
|------|--------|------|
| `RANDOM_SIGNIN` | `true` | 是否在账号间加入随机延迟，降低风控 |
| `MAX_RANDOM_DELAY` | `3600` | 单次最大随机延迟（秒） |
| `PRIVACY_MODE` | `true` | 日志脱敏，不打印明文 token |
| `TIMEOUT` | `15` / `60` | 单次请求超时（秒） |
| `RETRY_TIMES` / `MAX_RETRIES` | `3` | 失败重试次数 |
| `AUTO_UPDATE_TOKEN` | `true`（阿里云盘） | 自动把轮换后的 token 写回环境变量 |

---

## 三、缺少凭证部署的影响

- 脚本**照常加载运行并正常退出**，仅该平台输出 `❌ 未找到 XXX 环境变量` 提示，相当于跳过。
- 不影响其它已配置平台、不影响青龙面板稳定性。
- 唯一"损失"：该平台当天不签到，后续补填凭证重跑即可。
- `notify.py` 缺失时通知降级为日志打印，不影响运行。

---

## 四、部署到青龙的具体步骤

1. **上传脚本**
   将仓库克隆/上传到青龙，例如 `/ql/data/scripts/Cloud-Drive-Check-in/`。
   脚本按类别位于 `scripts/netdisk/`、`scripts/forum/`、`scripts/life/`、`scripts/misc/` 下（`scripts/archive/` 为历史版本，不参与运行）。

2. **安装依赖**
   `依赖管理 → 新建依赖 → 类型：Python3 → 名称` 填写：
   ```
   requests
   ```
   建议同时添加（可选）：
   ```
   curl_cffi
   ```

3. **配置环境变量**
   `环境变量 → 新建`，按上表逐平台添加。多个账号用**换行**分隔最稳妥（脚本已兼容 `\r\n` / `\n`）。

4. **创建定时任务**
   `定时任务 → 新建`：
   - **名称**：如 `阿里云盘签到`
   - **命令**：`task /ql/data/scripts/Cloud-Drive-Check-in/scripts/netdisk/aliyunpan_checkin.py`
     （或直接 `python3 /ql/data/scripts/Cloud-Drive-Check-in/scripts/netdisk/aliyunpan_checkin.py`）
   - **定时规则**：如 `0 6 * * *`（每天 06:00）
   - 对每个要使用的脚本重复建立一条任务。

5. **手动验证**
   点击任务「运行」，打开日志查看：
   - 已配置平台出现 `✅ 签到成功` / `📅 今日已签到` → 正常；
   - 未配置平台出现 `❌ 未找到...环境变量` → 符合预期（非故障）；
   - **只要日志中没有 `Traceback (most recent call last)` 即代表部署成功**。

---

## 五、凭证格式与安全注意事项

### 格式要点

- **阿里云盘**填 `ALIYUN_REFRESH_TOKEN`，值是长字符串（通常不以 `Cookie:` 开头），**不是**整段 `Cookie: xxx`。
- **Cookie 类变量**填浏览器复制的**完整 Cookie 文本**（形如 `key1=val1; key2=val2`），不要只填单个字段。
- **多账号**用换行分隔最稳妥；部分平台支持 `&`（见上表）。
- `IKUUU_*` / `TY_*` 为账号密码配对：两个变量各填多行、行序一一对应。
- `NGA_CREDENTIALS` 每行格式：`12345678,abcdef...`（`UID,AccessToken`）。
- `CDRAIL_DATA` 每行一个 JSON：`{"token":"...","app-token":"...","Cookie":"..."}`。

### 安全注意

- refresh_token / Cookie **等同于账号密码**，泄露即他人可登录你的账号；**切勿**提交到公开仓库、粘贴到群聊或写入明文日志。
- 默认 `PRIVACY_MODE=true`（脱敏），日志不会明文打印 token；`SHOW_TOKEN_IN_NOTIFICATION` 默认 `false`，勿随意开启。
- 阿里云盘 `AUTO_UPDATE_TOKEN` 默认 `true`，脚本会把轮换后的新 token 写回青龙环境变量——需保证面板环境变量可写。
- 建议在**小号 / 子账号**上运行签到，降低主号风控风险。
- Cookie / refresh_token 有有效期，过期后签到会报「登录失败 / 失效」，需重新抓取并更新。
- 不要把分隔符（换行 / `&`）写进 token 内部；token 本身含 `&` 的（如阿里云盘）请改用换行分隔。

---

## 六、常见问题

- **某平台始终 `❌ 登录失败 / 403`**：多为 Cookie 过期或触发风控。重新抓取 Cookie；deepflood/nodeseek/leaflow 可尝试安装 `curl_cffi`。
- **`ModuleNotFoundError: No module named 'notify'`**：非致命，脚本会自动降级为日志打印；需推送时放入官方 `notify.py`。
- **天翼云盘提示 RSA 相关错误**：已内置纯标准库 RSA，正常情况下不会出现；若报 `ImportError: rsa`，无需处理（会自动回退）。
- **leaflow 持续 `Cookie 已失效 / 重试后失败`**：站点已迁移到 console.leaflow.net，请用新版控制台 Cookie（含 `leaflow_session`、`XSRF-TOKEN` 等）替换旧 `PHPSESSID`。
- **恩山论坛签到无反应**：确认环境变量名是 **小写** `enshan_cookie`，非 `ENSHAN_COOKIE`。
