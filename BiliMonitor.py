from nakuru.entities.components import *
import time
import threading
import requests
import json
try:
    from util.plugin_dev.api.v1.config import *
    from util.plugin_dev.api.v1.bot import (
        PluginMetadata,
        PluginType,
        AstrMessageEvent,
        CommandResult,
        RegisteredPlatform
    )
except ImportError:
    flag_not_support = True
    print("bilimonitor: 导入接口失败。请升级到 AstrBot 最新版本。")

class Main:
    """
    初始化函数, 可以选择直接pass
    """
    # 屏蔽词列表
    BLOCKED_WORDS = ["下单", "元", "链"]
    def __init__(self) -> None:
        self.myThread = None # 线程对象，如果要使用线程，需要在此处定义。在run处定义会被释放掉
        self.last_dynamic = {} # 最新动态字典，键为b站uid，值为动态id
        print("BiliMonitor插件, 发送 订阅+b站uid 即可订阅up主的动态。")
        if os.path.exists("bili_monitor.json"): # 如果有保存的数据
            with open("bili_monitor.json", "r") as f: # 读取数据
                self.subs = json.load(f) # 保存到订阅字典
                print("读取到订阅数据：")
                for uid in self.subs: # 遍历所有订阅的up主
                    print(f"up: {uid} -> 群号:{self.subs[uid]}") # 打印订阅信息
                for uid in self.subs: # 遍历所有订阅的up主
                    self.last_dynamic[uid] = self.get_last_dynamic(uid) # 获取最新动态id并保存
        else: # 如果没有保存的数据
            self.subs = {} # 创建订阅字典

    def run(self, ame: AstrMessageEvent):
        message = ame.message_str
        message_obj = ame.message_obj
        
        if self.myThread is None: # 如果没有启动线程
            self.myThread = threading.Thread(target=self.monitor_thread, args=(ame.platform,)) # 创建线程对象并传入qq平台对象
            self.myThread.start() # 启动线程
        
        if message.startswith("订阅"):
            if len(message) == 2:
                return CommandResult(True, True, [Plain("请输入b站uid！")], "bili_monitor")
            uid = message[3:] # 获取b站uid
            if uid.isdigit(): # 判断是否是数字
                try:
                    group_id = message_obj.group_id # 获取qq群号
                except BaseException:
                    group_id = message_obj.sender.user_id
                if uid not in self.subs: # 如果没有订阅过这个up主
                    
                    self.last_dynamic[uid] = self.get_last_dynamic(uid) # 获取最新动态id并保存
                    dynamic = self.get_dynamic_info(self.last_dynamic[uid], uid) # 获取最新动态信息
                    if dynamic['name'] == "": # 如果获取失败
                        return CommandResult(True, True, [Plain(f"获取 uid: {uid} 动态信息失败！")], "bili_monitor")
                    msg = [Plain(f"订阅成功！你将收到{dynamic['name']}的最新动态~\n===============\n附上上一条最新动态：\n{dynamic['text']}")] # 创建消息列表并添加文本内容
                    if dynamic['pic']: # 如果有图片内容
                        msg.append(Image.fromURL(dynamic['pic'])) # 添加图片内容
                    self.subs[uid] = [group_id] # 创建订阅列表并添加群号
                    self.save_data() # 保存数据
                    return CommandResult(
                        True, True, msg, "bili_monitor"
                    )
                else: # 如果已经订阅过这个up主
                    if group_id not in self.subs[uid]: # 如果这个群没有订阅过
                        
                        dynamic = self.get_dynamic_info(self.last_dynamic[uid], uid) # 获取最新动态信息
                        msg = [Plain(f"订阅成功！你将收到{dynamic['name']}的最新动态~\n===============\n附上上一条最新动态：\n{dynamic['text']}")] #
                        if dynamic['pic']: # 如果有图片内容
                            msg.append(Image.fromURL(dynamic['pic'])) # 添加图片内容
                        self.subs[uid].append(group_id) # 添加群号到订阅列表
                        self.save_data() # 保存数据
                        return CommandResult(
                            True, True, msg, "bili_monitor"
                        )
                    else: # 如果这个群已经订阅过
                        return CommandResult(True, True, [Plain(f"你群已经订阅过{uid}了~")], "bili_monitor")
            else: # 如果不是数字
                return CommandResult(True, True, [Plain("请输入正确的b站uid！")], "bili_monitor")

        elif message.startswith("取消订阅"):
            us_uid = message[5:] # 获取b站uid
            if not us_uid.isdigit(): # 判断是否是数字
                return CommandResult(True, True, [Plain("请输入正确的b站uid！")], "bili_monitor")
            group_id = message_obj.group_id
            if us_uid in self.subs and group_id in self.subs[us_uid]:
                self.subs[us_uid].remove(group_id)
                if len(self.subs[us_uid]) == 0:
                    del self.subs[us_uid]
                self.save_data()
                return CommandResult(True, True, [Plain("取消订阅成功！")], "bili_monitor")
            else:
                return CommandResult(True, True, [Plain("你群没有订阅过这个up主！")], "bili_monitor")

        elif message == "查看订阅":
            group_id = message_obj.group_id
            text = "你群订阅的up主有："
            for uid in self.subs:
                if group_id in self.subs[uid]:
                    text += f"\n{uid}"
            return CommandResult(True, True, [Plain(text)], "bili_monitor")
        
        else:
            return CommandResult(False, False, None, "bili_monitor")

    """
    帮助函数，当用户输入 plugin v 插件名称 时，会调用此函数，返回帮助信息
    返回参数要求(必填)：dict{
        "name": str, # 插件名称
        "desc": str, # 插件简短描述
        "help": str, # 插件帮助信息
        "version": str, # 插件版本
        "author": str, # 插件作者
    }
    """        
    def info(self):
        return {
            "name": "bili_monitor",
            "desc": "B站动态监控插件",
            "help": "B站动态监控插件，发送 订阅+b站uid 即可订阅up主的动态，发送 启动监控 即可开启监控线程",
            "version": "v1.0.0 beta",
            "author": "Bing & Soulter"
        }
    
    def save_data(self):
        with open("bili_monitor.json", "w") as f:
            json.dump(self.subs, f)

    async def monitor_thread(self, platform: RegisteredPlatform):
        while True:
            for uid in self.subs: # 遍历所有订阅的up主
                try:
                    new_dynamic = self.get_last_dynamic(uid) # 获取最新动态id
                    if new_dynamic != self.last_dynamic[uid]: # 如果有更新
                        dynamic = self.get_dynamic_info(new_dynamic, uid) # 获取最新动态信息
                        msg = [Plain(f"{dynamic['name']}有新动态啦！\n{dynamic['text']}")] # 创建消息列表并添加文本内容
                        if dynamic['pic']!='': # 如果有图片内容
                            msg.append(Image.fromURL(dynamic['pic'])) # 添加图片内容
                        for group_id in self.subs[uid]: # 遍历所有订阅的群号
                            await platform.platform_instance.send(int(group_id), msg) # 发送消息到群里
                        self.last_dynamic[uid] = new_dynamic # 更新最新动态id
                except Exception as e:
                    print(uid, str(e))
            time.sleep(600) # 睡眠10分钟

    def get_last_dynamic(self, uid):
        # 获取最新动态id的函数
        url = f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}" # 拼接请求url
        response = requests.get(url) # 发送get请求
        data = response.json() # 解析json数据
        if data['code'] == 0: # 如果请求成功
            cards = data['data']['cards'] # 获取动态列表
            if cards: # 如果有动态
                return cards[0]['desc']['dynamic_id'] # 返回最新动态id
            else: # 如果没有动态
                return 0 # 返回0
        else: # 如果请求失败
            return -1 # 返回-1
            
    def get_dynamic_info(self, dynamic_id, uid):
            # 获取动态信息的函数
            url = f"https://api.vc.bilibili.com/dynamic_svr/v1/dynamic_svr/space_history?host_uid={uid}" # 拼接请求url
            response = requests.get(url) # 发送get请求
            data = response.json() # 解析json数据
            pic = ''
            if data['code'] == 0: # 如果请求成功
                cards = data['data']['cards'] # 获取动态列表
                if cards: # 如果有动态
                    try:
                        card = json.loads(cards[0]['card'])
                        # 屏蔽词检测
                        if any(blocked_word in card['item']['content'] for blocked_word in self.BLOCKED_WORDS):
                            return {"text": "该动态包含屏蔽词，不予转发", "pic": "", "name": ""}
                        if 'type' not in cards[0]['desc']:
                            card = json.loads(cards[0]['card'])
                            res = json.dumps(card, indent=4, ensure_ascii=False)
                            return {"text": res, "pic": "", "name": ""} # 返回失败信息字典
                        typ = cards[0]['desc']['type'] # 获取动态类型
                        card = json.loads(cards[0]['card']) # 获取动态信息
                        ts = cards[0]['desc']['timestamp'] # 获取动态时间戳
                        date = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(ts)) # 格式化时间戳
                        # 根据不同的动态类型，获取不同的动态信息，最终得到的是文本和图片
                        if typ == 1: # 转发动态
                            name = card['user']['uname'] if 'user' in card else '未知用户'  # 获取转发者的用户名
                            face = card['user']['face'] if 'user' in card else ''  # 获取转发者的头像
                            text = card['item']['content']  # 获取转发者的评论文本
                            pic = ''  # 初始化图片变量

                            if 'origin' in card:
                                ori = json.loads(card['origin'])
                                text += "\n【转发了动态】\n"
                                # 检查原始动态是否包含视频特有的字段
                                if 'aid' in ori or 'cid' in ori:  # 如果原始动态是视频动态
                                    video_title = ori.get('title', '未知标题')
                                    video_desc = ori.get('desc', '无简介')
                                    video_pic = ori.get('pic', '')  # 视频封面
                                    text += f"视频标题: {video_title}\n视频简介: {video_desc}"
                                    pic = video_pic  # 设置视频封面为图片
                                elif 'desc' in ori:  # 如果是其他类型的动态
                                    text += ori.get('desc', '原始内容不可见')
                                    pic = ori.get('pic', '')  # 尝试获取图片
                            name = card['user']['uname']  # 获取up主名称
                        elif typ == 2: # 图文动态
                            text = card['item']['description'] # 获取文本
                            pic = card['item']['pictures'][0]['img_src'] # 获取图片
                            name = card['user']['name'] # 获取up主名称
                        elif typ == 4: #ok
                            text = card['item']['content'] # 获取文本
                            name = card['user']['uname'] # 获取up主名称
                        elif typ == 8: # 视频动态
                            # 没有item
                            text = card['dynamic'] if 'dynamic' in card else '无附加文本'  # 获取动态附加的文本
                            bvid = card['bvid'] if 'bvid' in card else ''
                            video_url = f"https://www.bilibili.com/video/{bvid}" if bvid else ''
                            video_title = card['title'] if 'title' in card else '未知标题'  # 获取视频标题
                            video_desc = card['desc'] if 'desc' in card else '无简介'  # 获取视频简介
                            pic = card['pic'] if 'pic' in card else ''  # 获取视频封面
                            name = card['owner']['name'] if 'owner' in card and 'name' in card['owner'] else '未知up主'  # 获取up主名称
                            return {
                                "text": f"发布时间: {date}\n视频动态内容: {text}\n视频标题: {video_title}\n视频简介: {video_desc}\n视频链接: {video_url}",
                                "pic": pic,
                                "name": name
                            }
                        elif typ == 64: # 专栏动态
                            text = card['item']['title'] # 获取文本
                            pic = card['item']['image_urls'][0] # 获取图片
                            name = card['item']['author']['name'] # 获取up主名称
                        elif typ == 2048: # 音频动态
                            text = card['item']['intro'] # 获取文本
                            pic = card['item']['cover'] # 获取图片
                            name = card['item']['author']['name'] # 获取up主名称
                        else: # 其他动态
                            text = f"暂不支持此类型动态 {card}" # 获取文本
                            pic = "" # 获取图片
                            name = str(uid) # 获取up主名称

                        return {"text": f"时间: {date}\n内容: {text}", "pic": pic, "name": name} # 返回动态信息字典
                    except Exception as e:
                        print(str(e))
                        card = json.loads(cards[0]['card'])
                        
                        res = json.dumps(card, indent=4, ensure_ascii=False)
                        print(res)
                        return {"text": res, "pic": "", "name": ""} # 返回失败信息字典
                        
            else: # 如果请求失败
                return {"text": "获取动态信息失败！", "pic": "", "name": ""} # 返回失败信息字典