#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
cron "9 15 * * *" script-path=xxx.py,tag=匹配cron用
new Env('顺丰速运签到')
"""

# ---------------- Windows 控制台编码兼容（青龙 Linux 环境下为空操作）----------------
import sys as _sys
try:
    _sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    _sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

"""
顺丰速运自动化脚本
来源:
- https://github.com/faintout/myself-script/blob/main/sfsy.py
- https://github.com/Xx1aoy1/scripts/blob/main/sf2.py

功能: 遍历生活特权所有分组的券进行领券，完成任务领取丰蜜积分
变量名: sfsyUrl
格式: 多账号用换行分割
获取方式:
1. 顺丰APP绑定微信后，添加机器人发送"顺丰"
2. 打开小程序或APP-我的-积分，抓包以下URL之一:
   - https://mcs-mimp-web.sf-express.com/mcs-mimp/share/weChat/shareGiftReceiveRedirect
   - https://mcs-mimp-web.sf-express.com/mcs-mimp/share/app/shareRedirect
编码: 抓取URL后，使用 https://www.toolhelper.cn/EncodeDecode/Url 进行编码

"""

import hashlib
import json
import os
import random
import time
from datetime import datetime, timedelta
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
from urllib.parse import unquote

# 禁用安全请求警告
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

# ---------------- 统一通知模块加载（和其他脚本一样）----------------
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

# 全局日志变量
send_msg = ''
one_msg = ''

def Log(cont=''):
    """记录日志"""
    global send_msg, one_msg
    print(cont)
    if cont:
        one_msg += f'{cont}\n'
        send_msg += f'{cont}\n'

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
        
    Log(f"{task_name} 需要等待 {format_time_remaining(delay_seconds)}")
    
    remaining = delay_seconds
    while remaining > 0:
        if remaining <= 10 or remaining % 10 == 0:
            Log(f"{task_name} 倒计时: {format_time_remaining(remaining)}")
        
        sleep_time = 1 if remaining <= 10 else min(10, remaining)
        time.sleep(sleep_time)
        remaining -= sleep_time

inviteId = ['']

class RUN:
    def __init__(self, info, index):
        """初始化账号信息"""
        global one_msg
        one_msg = ''
        split_info = info.split('@')
        url = split_info[0]
        self.send_UID = split_info[-1] if len(split_info) > 1 and "UID_" in split_info[-1] else None
        self.index = index + 1

        self.s = requests.session()
        self.s.verify = False

        self.headers = {
            'Host': 'mcs-mimp-web.sf-express.com',
            'upgrade-insecure-requests': '1',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/98.0.4758.102 Safari/537.36 NetType/WIFI MicroMessenger/7.0.20.1781(0x6700143B) WindowsWechat(0x6309092b) XWEB/6763 Flue',
            'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9',
            'sec-fetch-site': 'none',
            'sec-fetch-mode': 'navigate',
            'sec-fetch-user': '?1',
            'sec-fetch-dest': 'document',
            'accept-language': 'zh-CN,zh',
            'platform': 'MINI_PROGRAM',
        }

        # 会员日活动相关属性
        self.member_day_black = False
        self.member_day_red_packet_drew_today = False
        self.member_day_red_packet_map = {}
        self.today = datetime.now().strftime('%Y-%m-%d')
        self.max_level = 8
        self.packet_threshold = 1 << (self.max_level - 1)

        # 账号标识默认值（登录异常时保持空串，避免后续流程属性不存在）
        self.user_id = ''
        self.phone = ''
        self.mobile = ''

        self.login_res = self.login(url)

    def get_deviceId(self, characters='abcdef0123456789'):
        """生成随机设备ID"""
        result = ''
        for char in 'xxxxxxxx-xxxx-xxxx':
            if char == 'x':
                result += random.choice(characters)
            else:
                result += char
        return result

    def login(self, sfurl):
        """登录顺丰账号"""
        try:
            ress = self.s.get(sfurl, headers=self.headers)
            self.user_id = self.s.cookies.get_dict().get('_login_user_id_', '')
            self.phone = self.s.cookies.get_dict().get('_login_mobile_', '')
            self.mobile = self.phone[:3] + "*" * 4 + self.phone[7:] if self.phone else ''
            if self.phone:
                Log(f'👤 账号{self.index}:【{self.mobile}】登陆成功')
                return True
            else:
                Log(f'❌ 账号{self.index}获取用户信息失败')
                return False
        except Exception as e:
            Log(f'❌ 登录异常: {str(e)}')
            return False

    def getSign(self):
        """生成请求签名"""
        timestamp = str(int(time.time() * 1000))
        token = 'wwesldfs29aniversaryvdld29'
        sysCode = 'MCS-MIMP-CORE'
        data = f'token={token}&timestamp={timestamp}&sysCode={sysCode}'
        signature = hashlib.md5(data.encode()).hexdigest()
        data = {
            'sysCode': sysCode,
            'timestamp': timestamp,
            'signature': signature
        }
        self.headers.update(data)
        return data

    def do_request(self, url, data=None, req_type='post', max_retries=3):
        """发送HTTP请求"""
        self.getSign()
        for retry_count in range(max_retries):
            try:
                if req_type.lower() == 'get':
                    response = self.s.get(url, headers=self.headers, timeout=30)
                elif req_type.lower() == 'post':
                    response = self.s.post(url, headers=self.headers, json=data or {}, timeout=30)
                else:
                    raise ValueError(f'Invalid req_type: {req_type}')

                response.raise_for_status()
                return response.json()

            except (requests.exceptions.RequestException, json.JSONDecodeError) as e:
                Log(f'❌ 请求失败 ({retry_count + 1}/{max_retries}): {str(e)}')
                if retry_count < max_retries - 1:
                    time.sleep(2)
                    continue
                return {'success': False, 'errorMessage': str(e)}
        return {'success': False, 'errorMessage': 'All retries failed'}

    def sign(self):
        """执行签到任务"""
        Log('🎯 开始执行签到')
        json_data = {"comeFrom": "vioin", "channelFrom": "WEIXIN"}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskSignPlusService~automaticSignFetchPackage'
        response = self.do_request(url, data=json_data)
        if response.get('success'):
            obj = response.get('obj') or {}
            count_day = obj.get('countDay', 0)
            if obj.get('integralTaskSignPackageVOList'):
                packet_name = obj["integralTaskSignPackageVOList"][0].get("packetName", "未知奖励")
                Log(f'✨ 签到成功，获得【{packet_name}】，本周累计签到【{count_day + 1}】天')
            else:
                Log(f'📝 今日已签到，本周累计签到【{count_day + 1}】天')
        else:
            Log(f'❌ 签到失败！原因：{response.get("errorMessage", "未知错误")}')

    def get_SignTaskList(self, end=False):
        """获取签到任务列表"""
        Log('🎯 开始获取签到任务列表' if not end else '💰 查询最终积分')
        json_data = {"channelType": "1", "deviceId": self.get_deviceId()}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~queryPointTaskAndSignFromES'
        response = self.do_request(url, data=json_data)
        if response.get('success') and response.get('obj'):
            obj = response.get('obj') or {}
            totalPoint = obj.get('totalPoint', '未知')
            Log(f'💰 {"执行前" if not end else "当前"}积分：【{totalPoint}】')
            if not end:
                for task in obj.get('taskTitleLevels', []):
                    self.taskId = task.get("taskId")
                    self.taskCode = task.get("taskCode")
                    self.strategyId = task.get("strategyId")
                    self.title = task.get("title", "未知任务")
                    status = task.get("status")
                    skip_title = ['用行业模板寄件下单', '去新增一个收件偏好', '参与积分活动']
                    if status == 3:
                        Log(f'✨ {self.title}-已完成')
                        continue
                    if self.title in skip_title:
                        Log(f'⏭️ {self.title}-跳过')
                        continue
                    if not self.taskCode:
                        Log(f'⏭️ {self.title}-缺少taskCode，跳过')
                        continue
                    self.doTask()
                    time.sleep(2)
                    self.receiveTask()

    def doTask(self):
        """完成签到任务"""
        Log(f'🎯 开始去完成【{self.title}】任务')
        json_data = {"taskCode": self.taskCode}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonRoutePost/memberEs/taskRecord/finishTask'
        response = self.do_request(url, data=json_data)
        Log(f'✨ 【{self.title}】任务-{"已完成" if response.get("success") else response.get("errorMessage", "失败")}')

    def receiveTask(self):
        """领取签到任务奖励"""
        Log(f'🎁 开始领取【{self.title}】任务奖励')
        json_data = {
            "strategyId": self.strategyId,
            "taskId": self.taskId,
            "taskCode": self.taskCode,
            "deviceId": self.get_deviceId()
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~integralTaskStrategyService~fetchIntegral'
        response = self.do_request(url, data=json_data)
        Log(f'✨ 【{self.title}】任务奖励-{"领取成功" if response.get("success") else response.get("errorMessage", "失败")}')

    def do_honeyTask(self):
        """完成丰蜜任务"""
        Log(f'🎯 开始完成【{self.taskType}】任务')
        json_data = {"taskCode": self.taskCode}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberEs~taskRecord~finishTask'
        response = self.do_request(url, data=json_data)
        Log(f'✨ 【{self.taskType}】任务-{"已完成" if response.get("success") else response.get("errorMessage", "失败")}')

    def receive_honeyTask(self):
        """领取丰蜜任务奖励"""
        Log(f'🎁 领取【{self.taskType}】丰蜜任务')
        self.headers.update({
            'syscode': 'MCS-MIMP-CORE',
            'channel': 'wxwdsj',
            'accept': 'application/json, text/plain, */*',
            'content-type': 'application/json;charset=UTF-8',
            'platform': 'MINI_PROGRAM'
        })
        json_data = {"taskType": self.taskType}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~receiveHoney'
        response = self.do_request(url, data=json_data)
        Log(f'✨ 收取任务【{self.taskType}】-{"成功" if response.get("success") else response.get("errorMessage", "失败")}')

    def get_coupom(self, goods):
        """领取优惠券"""
        json_data = {
            "from": "Point_Mall",
            "orderSource": "POINT_MALL_EXCHANGE",
            "goodsNo": goods['goodsNo'],
            "quantity": 1,
            "taskCode": self.taskCode
        }
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberGoods~pointMallService~createOrder'
        response = self.do_request(url, data=json_data)
        return response.get('success')

    def get_coupom_list(self):
        """获取优惠券列表"""
        json_data = {"memGrade": 2, "categoryCode": "SHTQ", "showCode": "SHTQWNTJ"}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberGoods~mallGoodsLifeService~list'
        response = self.do_request(url, data=json_data)
        if response.get('success'):
            all_goods = []
            for obj in response.get("obj", []):
                all_goods.extend(obj.get("goodsList", []))
            for goods in all_goods:
                if goods.get('exchangeTimesLimit', 0) >= 1:
                    if self.get_coupom(goods):
                        Log('✨ 成功领取券，任务结束！')
                        return
            Log('📝 所有券尝试完成，没有可用的券或全部领取失败。')
        else:
            Log(f'❌ 获取券列表失败！原因：{response.get("errorMessage", "未知错误")}')

    def get_honeyTaskListStart(self):
        """获取丰蜜任务列表"""
        Log('🍯 开始获取采蜜换大礼任务列表')
        self.headers['channel'] = 'wxwdsj'
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~taskDetail'
        response = self.do_request(url, data={})
        if response.get('success'):
            for item in (response.get('obj') or {}).get('list', []):
                self.taskType = item.get("taskType", "未知任务")
                status = item.get("status")
                if status == 3:
                    Log(f'✨ 【{self.taskType}】-已完成')
                    continue
                if "taskCode" in item:
                    self.taskCode = item["taskCode"]
                    if self.taskType == 'DAILY_VIP_TASK_TYPE':
                        self.get_coupom_list()
                    else:
                        self.do_honeyTask()
                if self.taskType == 'BEES_GAME_TASK_TYPE':
                    self.honey_damaoxian()
                time.sleep(2)

    def honey_damaoxian(self):
        """执行大冒险任务"""
        Log('>>> 执行大冒险任务')
        gameNum = 5
        for i in range(1, gameNum + 1):
            json_data = {"gatherHoney": 20}
            Log(f'>> 开始第{i}次大冒险')
            url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeGameService~gameReport'
            response = self.do_request(url, data=json_data)
            if response.get('success'):
                gameNum = (response.get('obj') or {}).get('gameNum', gameNum)
                Log(f'> 大冒险成功！剩余次数【{gameNum}】')
                time.sleep(2)
            elif response.get("errorMessage") == '容量不足':
                Log('> 需要扩容')
                self.honey_expand()
            else:
                Log(f'> 大冒险失败！【{response.get("errorMessage", "未知错误")}】')
                break

    def honey_expand(self):
        """容器扩容"""
        Log('>>> 容器扩容')
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~expand'
        response = self.do_request(url, data={})
        if response.get('success'):
            Log(f'> 成功扩容【{response.get("obj", "未知")}】容量')
        else:
            Log(f'> 扩容失败！【{response.get("errorMessage", "未知错误")}】')

    def _pick_invite(self):
        """安全地选择一个邀请用户ID（邀请列表为空或仅含自己时返回空串）"""
        candidates = [invite for invite in inviteId if invite and invite != self.user_id]
        return random.choice(candidates) if candidates else ""

    def honey_indexData(self, end=False):
        """执行采蜜换大礼任务"""
        Log('🍯 开始执行采蜜换大礼任务' if not end else '🍯 查询最终丰蜜')
        random_invite = self._pick_invite()
        self.headers['channel'] = 'wxwdsj'
        json_data = {"inviteUserId": random_invite} if random_invite else {}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~receiveExchangeIndexService~indexData'
        response = self.do_request(url, data=json_data)
        if response.get('success'):
            obj = response.get('obj') or {}
            usableHoney = obj.get('usableHoney', '未知')
            activityEndTime = obj.get('activityEndTime', '')
            if not end:
                Log(f'📅 本期活动结束时间【{activityEndTime}】')
                Log(f'🍯 执行前丰蜜：【{usableHoney}】')
                for task in obj.get('taskDetail', []):
                    self.taskType = task['type']
                    self.receive_honeyTask()
                    time.sleep(2)
            else:
                Log(f'🍯 执行后丰蜜：【{usableHoney}】')

    def member_day_index(self):
        """执行会员日活动"""
        Log('🎭 会员日活动')
        invite_user_id = self._pick_invite()
        payload = {'inviteUserId': invite_user_id} if invite_user_id else {}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayIndexService~index'
        response = self.do_request(url, data=payload)
        if response.get('success'):
            obj = response.get('obj') or {}
            lottery_num = obj.get('lotteryNum', 0)
            can_receive_invite_award = obj.get('canReceiveInviteAward', False)
            if can_receive_invite_award:
                self.member_day_receive_invite_award(invite_user_id)
            self.member_day_red_packet_status()
            Log(f'🎁 会员日可以抽奖{lottery_num}次')
            for _ in range(lottery_num):
                self.member_day_lottery()
            if self.member_day_black:
                return
            self.member_day_task_list()
            if self.member_day_black:
                return
            self.member_day_red_packet_status()
        else:
            error_message = response.get('errorMessage', '无返回')
            Log(f'📝 查询会员日失败: {error_message}')
            if '没有资格参与活动' in error_message:
                self.member_day_black = True
                Log('📝 会员日任务风控')

    def member_day_receive_invite_award(self, invite_user_id):
        """领取会员日邀请奖励"""
        payload = {'inviteUserId': invite_user_id}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayIndexService~receiveInviteAward'
        response = self.do_request(url, data=payload)
        if response.get('success'):
            product_name = response.get('obj', {}).get('productName', '空气')
            Log(f'🎁 会员日奖励: {product_name}')
        else:
            error_message = response.get('errorMessage', '无返回')
            Log(f'📝 领取会员日奖励失败: {error_message}')
            if '没有资格参与活动' in error_message:
                self.member_day_black = True
                Log('📝 会员日任务风控')

    def member_day_lottery(self):
        """会员日抽奖"""
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayLotteryService~lottery'
        response = self.do_request(url, data={})
        if response.get('success'):
            product_name = response.get('obj', {}).get('productName', '空气')
            Log(f'🎁 会员日抽奖: {product_name}')
        else:
            error_message = response.get('errorMessage', '无返回')
            Log(f'📝 会员日抽奖失败: {error_message}')
            if '没有资格参与活动' in error_message:
                self.member_day_black = True
                Log('📝 会员日任务风控')

    def member_day_task_list(self):
        """获取会员日任务列表"""
        payload = {'activityCode': 'MEMBER_DAY', 'channelType': 'MINI_PROGRAM'}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~taskList'
        response = self.do_request(url, data=payload)
        if response.get('success'):
            task_list = response.get('obj') or []
            for task in task_list:
                if task.get('status') == 1:
                    if self.member_day_black:
                        return
                    self.member_day_fetch_mix_task_reward(task)
                elif task.get('status') == 2 and task.get('taskType') not in [
                    'SEND_SUCCESS', 'INVITEFRIENDS_PARTAKE_ACTIVITY', 'OPEN_SVIP',
                    'OPEN_NEW_EXPRESS_CARD', 'OPEN_FAMILY_CARD', 'CHARGE_NEW_EXPRESS_CARD', 
                    'INTEGRAL_EXCHANGE', 'OPEN_SUPER_CARD'  # 添加购买至尊会员到跳过列表
                ]:
                    for _ in range(task.get('restFinishTime', 0) or 0):
                        if self.member_day_black:
                            return
                        self.member_day_finish_task(task)
        else:
            error_message = response.get('errorMessage', '无返回')
            Log(f'📝 查询会员日任务失败: {error_message}')
            if '没有资格参与活动' in error_message:
                self.member_day_black = True
                Log('📝 会员日任务风控')

    def member_day_finish_task(self, task):
        """完成会员日任务 - 修复版本"""
        task_name = task.get("taskName", "未知任务")
        task_type = task.get("taskType", "")
        
        # 检查任务是否应该被跳过
        skip_task_types = [
            'SEND_SUCCESS', 'INVITEFRIENDS_PARTAKE_ACTIVITY', 'OPEN_SVIP',
            'OPEN_NEW_EXPRESS_CARD', 'OPEN_FAMILY_CARD', 'CHARGE_NEW_EXPRESS_CARD', 
            'INTEGRAL_EXCHANGE', 'OPEN_SUPER_CARD'
        ]
        
        if task_type in skip_task_types:
            Log(f'⏭️ 会员日任务[{task_name}]-跳过执行（{task_type}）')
            return
        
        # 智能获取任务代码
        task_code = None
        if 'taskCode' in task:
            task_code = task['taskCode']
        elif 'taskType' in task:
            task_code = task['taskType']  # 某些任务使用taskType作为taskCode
        else:
            Log(f'📝 任务[{task_name}]缺少必要字段，跳过执行')
            Log(f'📝 任务详情: {json.dumps(task, ensure_ascii=False, indent=2)}')
            return
        
        # 执行任务
        payload = {'taskCode': task_code}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberEs~taskRecord~finishTask'
        response = self.do_request(url, data=payload)
        
        if response.get('success'):
            Log(f'📝 完成会员日任务[{task_name}]: 成功')
            self.member_day_fetch_mix_task_reward(task)
        else:
            error_message = response.get('errorMessage', '无返回')
            Log(f'📝 完成会员日任务[{task_name}]: {error_message}')
            if '没有资格参与活动' in error_message:
                self.member_day_black = True
                Log('📝 会员日任务风控')

    def member_day_fetch_mix_task_reward(self, task):
        """领取会员日任务奖励"""
        task_name = task.get("taskName", "未知任务")
        task_type = task.get('taskType')
        if not task_type:
            Log(f'📝 任务[{task_name}]缺少 taskType，跳过领奖')
            return
        payload = {'taskType': task_type, 'activityCode': 'MEMBER_DAY', 'channelType': 'MINI_PROGRAM'}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~activityTaskService~fetchMixTaskReward'
        response = self.do_request(url, data=payload)
        
        if response.get('success'):
            Log(f'🎁 领取会员日任务[{task_name}]: 成功')
        else:
            error_message = response.get('errorMessage', '失败')
            Log(f'🎁 领取会员日任务[{task_name}]: {error_message}')

    def member_day_receive_red_packet(self, hour):
        """领取会员日红包"""
        payload = {'receiveHour': hour}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayTaskService~receiveRedPacket'
        response = self.do_request(url, data=payload)
        Log(f'🎁 会员日领取{hour}点红包-{"成功" if response.get("success") else response.get("errorMessage", "失败")}')

    def member_day_red_packet_status(self):
        """查询会员日红包状态"""
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketStatus'
        response = self.do_request(url, data={})
        if response.get('success'):
            packet_list = (response.get('obj') or {}).get('packetList', [])
            self.member_day_red_packet_map = {
                packet.get('level'): packet.get('count', 0)
                for packet in packet_list if packet.get('level') is not None
            }
            for level in range(1, self.max_level):
                count = self.member_day_red_packet_map.get(level, 0)
                while count >= 2:
                    self.member_day_red_packet_merge(level)
                    count -= 2
            packet_summary = [f"[{level}]X{count}" for level, count in self.member_day_red_packet_map.items() if count > 0]
            Log(f"📝 会员日合成列表: {', '.join(packet_summary) or '无红包'}")
            if self.member_day_red_packet_map.get(self.max_level):
                Log(f"🎁 会员日已拥有[{self.max_level}级]红包X{self.member_day_red_packet_map[self.max_level]}")
                self.member_day_red_packet_draw(self.max_level)
            else:
                remaining_needed = sum(1 << (int(level) - 1) for level, count in self.member_day_red_packet_map.items() if count > 0)
                remaining = self.packet_threshold - remaining_needed
                Log(f"📝 会员日距离[{self.max_level}级]红包还差: [1级]红包X{remaining}")
        else:
            error_message = response.get('errorMessage', '无返回')
            Log(f'📝 查询会员日合成失败: {error_message}')
            if '没有资格参与活动' in error_message:
                self.member_day_black = True
                Log('📝 会员日任务风控')

    def member_day_red_packet_merge(self, level):
        """合成会员日红包"""
        payload = {'level': level, 'num': 2}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketMerge'
        response = self.do_request(url, data=payload)
        if response.get('success'):
            Log(f'🎁 会员日合成: [{level}级]红包X2 -> [{level + 1}级]红包')
            self.member_day_red_packet_map[level] = self.member_day_red_packet_map.get(level, 0) - 2
            self.member_day_red_packet_map[level + 1] = self.member_day_red_packet_map.get(level + 1, 0) + 1
        else:
            Log(f'📝 会员日合成[{level}级]红包失败: {response.get("errorMessage", "无返回")}')

    def member_day_red_packet_draw(self, level):
        """提取会员日红包"""
        payload = {'level': str(level)}
        url = 'https://mcs-mimp-web.sf-express.com/mcs-mimp/commonPost/~memberNonactivity~memberDayPacketService~redPacketDraw'
        response = self.do_request(url, data=payload)
        if response.get('success'):
            coupon_names = [item['couponName'] for item in response.get('obj', [])] or ['空气']
            Log(f"🎁 会员日提取[{level}级]红包: {', '.join(coupon_names)}")
        else:
            Log(f"📝 会员日提取[{level}级]红包失败: {response.get('errorMessage', '无返回')}")

    def main(self):
        """主执行逻辑"""
        if not self.login_res:
            return False
        time.sleep(random.uniform(1, 3))

        # 执行签到任务
        self.sign()
        # 注释掉超值福利签到（经常失败，影响体验）
        # self.superWelfare_receiveRedPacket()
        self.get_SignTaskList()
        self.get_SignTaskList(True)

        # 执行丰蜜任务
        self.get_honeyTaskListStart()
        self.honey_indexData()
        self.honey_indexData(True)

        # 检查活动截止时间
        activity_end_date = get_quarter_end_date()
        days_left = (activity_end_date - datetime.now()).days
        Log(f"⏰ 采蜜活动截止兑换还有{days_left}天，请及时进行兑换！！")

        # 会员日任务（每月26-28日）
        if 26 <= datetime.now().day <= 28:
            self.member_day_index()
        else:
            Log('⏰ 未到指定时间不执行会员日任务')

        self.sendMsg()
        return True

    def sendMsg(self, help=False):
        """发送通知（实现真正的通知功能）"""
        global one_msg
        if hadsend and one_msg:
            try:
                # 限制消息长度，避免过长
                if len(one_msg) > 4000:
                    one_msg = one_msg[-4000:]
                    one_msg = "...(消息过长，已截取后半部分)\n" + one_msg
                
                send(f'顺丰速运账号{self.index}', one_msg.strip())
                print(f'✅ 账号{self.index}通知发送完成')
            except Exception as e:
                print(f'❌ 账号{self.index}通知发送失败: {e}')

def get_quarter_end_date():
    """计算当前季度结束日期"""
    current_date = datetime.now()
    current_month = current_date.month
    current_year = current_date.year
    
    # 计算下一季度的第一个月
    quarter_index = (current_month - 1) // 3 + 1
    next_quarter_month = quarter_index * 3 + 1
    
    if next_quarter_month > 12:
        # 如果计算结果是13（即当前是第4季度），下个季度第一天是明年的1月1日
        next_quarter_first_day = datetime(current_year + 1, 1, 1)
    else:
        # 否则就在当年
        next_quarter_first_day = datetime(current_year, next_quarter_month, 1)
        
    return next_quarter_first_day - timedelta(days=1)

if __name__ == '__main__':
    """主程序入口"""
    APP_NAME = '顺丰速运'
    ENV_NAME = 'sfsyUrl'
    
    print(f"==== 顺丰速运签到开始 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
    
    # 随机延迟（整体延迟）
    if random_signin:
        delay_seconds = random.randint(0, max_random_delay)
        if delay_seconds > 0:
            signin_time = datetime.now() + timedelta(seconds=delay_seconds)
            print(f"🎲 随机模式: 延迟 {format_time_remaining(delay_seconds)} 后开始")
            print(f"⏰ 预计开始时间: {signin_time.strftime('%H:%M:%S')}")
            wait_with_countdown(delay_seconds, "顺丰签到")
    
    token = os.getenv(ENV_NAME)
    tokens = [t.strip() for t in token.split('\n') if t.strip()] if token else []
    if tokens:
        Log(f"🚚 共获取到{len(tokens)}个账号")
        for index, infos in enumerate(tokens):
            Log(f"==================================\n🚚 处理账号{index + 1}")
            try:
                RUN(infos, index).main()
            except Exception as e:
                # 单账号异常不影响后续账号
                Log(f'❌ 账号{index + 1}执行异常: {str(e)}')
                try:
                    send(f'顺丰速运账号{index + 1}执行异常', f'账号{index + 1}执行异常: {str(e)}')
                except Exception:
                    pass
            
            # 多账号间随机等待
            if index < len(tokens) - 1:  # 不是最后一个账号
                delay = random.uniform(10, 30)
                print(f"💤 随机等待 {delay:.1f} 秒后处理下一个账号...")
                time.sleep(delay)
                
        # 最终汇总通知
        if hadsend and send_msg:
            try:
                # 汇总所有账号的结果
                summary_msg = f"""🚚 顺丰速运签到汇总

📊 总计处理: {len(tokens)}个账号
📅 执行时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

详细结果请查看各账号单独通知"""
                send('顺丰速运汇总', summary_msg)
                print('✅ 汇总通知发送完成')
            except Exception as e:
                print(f'❌ 汇总通知发送失败: {e}')
    else:
        Log("❌ 未获取到sfsyUrl环境变量")
    
    print(f"==== 顺丰速运签到完成 - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} ====")
