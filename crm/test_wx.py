import requests # 导入 requests 库，用于发送 HTTP 请求
import json # 导入 json 库，用于处理 JSON 格式的数据

BASE_URL = "http://127.0.0.1:8201/wx" # 定义接口的基础 URL 地址，请根据实际服务端口和路由前缀修改

def test_send_messages(): # 定义测试发送消息接口的函数
    url = f"{BASE_URL}/send_messages" # 拼接完整的请求 URL
    payload = { # 定义请求体数据字典
        "friend": "韬馨AI产品项目", # 目标好友名称或群聊备注
        "messages": ["你好", "这是通过API发送的测试消息"] # 要发送的消息列表
    } # 请求体数据定义结束
    headers = {"Content-Type": "application/json"} # 定义请求头，指定内容类型为 JSON
    try: # 开始捕获可能发生的异常
        response = requests.post(url, json=payload, headers=headers) # 发送 POST 请求并接收响应
        print(f"发送消息接口响应状态码: {response.status_code}") # 打印响应状态码
        print(f"发送消息接口响应内容: {response.text}") # 打印响应的具体内容文本
    except Exception as e: # 捕获发生的异常对象 e
        print(f"发送消息接口请求失败: {e}") # 打印错误信息

def test_get_messages(): # 定义测试获取消息接口的函数
    url = f"{BASE_URL}/get_messages" # 拼接完整的请求 URL
    params = { # 定义 GET 请求的查询参数字典
        "friend": "韬馨AI产品项目", # 目标好友名称或群聊备注
        "number": 10, # 需要获取的消息数量
        "with_sender": True # 是否区分发送者
    } # 查询参数字典定义结束
    try: # 开始捕获可能发生的异常
        response = requests.get(url, params=params) # 发送 GET 请求并接收响应
        print(f"获取消息接口响应状态码: {response.status_code}") # 打印响应状态码
        print(f"获取消息接口响应内容: {response.text}") # 打印响应的具体内容文本
    except Exception as e: # 捕获发生的异常对象 e
        print(f"获取消息接口请求失败: {e}") # 打印错误信息

def test_add_friend(): # 定义测试添加好友接口的函数
    url = f"{BASE_URL}/add_friend" # 拼接完整的请求 URL
    payload = { # 定义请求体数据字典
        "number": "13751790235", # 需要添加的微信号或手机号 (请替换为真实号码)
        "greetings": "你好，我是通过API添加的", # 发送的打招呼内容
        "remark": "API测试好友" # 给好友设置的备注信息
    } # 请求体数据定义结束
    headers = {"Content-Type": "application/json"} # 定义请求头，指定内容类型为 JSON
    try: # 开始捕获可能发生的异常
        response = requests.post(url, json=payload, headers=headers) # 发送 POST 请求并接收响应
        print(f"添加好友接口响应状态码: {response.status_code}") # 打印响应状态码
        print(f"添加好友接口响应内容: {response.text}") # 打印响应的具体内容文本
    except Exception as e: # 捕获发生的异常对象 e
        print(f"添加好友接口请求失败: {e}") # 打印错误信息

        

def test_check_new_messages(): # 定义测试检查新消息接口的函数
    url = f"{BASE_URL}/check_new_messages" # 拼接完整的请求 URL
    params = { # 定义 GET 请求的查询参数字典
        "with_sender": True # 是否区分发送者
    } # 查询参数字典定义结束
    try: # 开始捕获可能发生的异常
        response = requests.get(url, params=params) # 发送 GET 请求并接收响应
        print(f"检查新消息接口响应状态码: {response.status_code}") # 打印响应状态码
        # 为了更好地展示返回的 JSON 结构，使用 json.dumps 格式化输出
        print(f"检查新消息接口响应内容: {json.dumps(response.json(), ensure_ascii=False, indent=2)}") # 打印格式化后的响应内容
    except Exception as e: # 捕获发生的异常对象 e
        print(f"检查新消息接口请求失败: {e}") # 打印错误信息

if __name__ == "__main__": # 判断是否作为主程序运行
    print("--- 开始测试发送消息接口 ---") # 打印测试开始提示语
    #test_send_messages() # 调用测试发送消息接口的函数
    
    print("\n--- 开始测试获取消息接口 ---") # 打印测试开始提示语
    #test_get_messages() # 调用测试获取消息接口的函数
    
    print("\n--- 开始测试检查新消息接口 ---") # 打印测试开始提示语
    test_check_new_messages() # 调用测试检查新消息接口的函数
    
    # 为了防止误触发加好友操作，默认将其注释掉，需要时可以解除注释并修改手机号
    # print("\n--- 开始测试添加好友接口 ---") # 打印测试开始提示语
    #test_add_friend() # 调用测试添加好友接口的函数

'''
# 以下为您原有的本地调用测试代码备份：

from pyweixin import Messages
# Messages.send_messages_to_friend(friend='韬馨AI产品项目',messages=['你好','发消息测试'])

#from pyweixin import Messages
#print(Messages.dump_chat_history(friend='韬馨AI产品项目',number=20,capture_alia=True))

from pyweixin.WeChatAuto import Monitor
from pyweixin.Config import GlobalConfig

# 可选：配置一些全局参数，比如不全屏
GlobalConfig.is_maximize = False

# 1. 定义一个回调函数，专门用来处理读到的数据
def handle_new_messages(friend, messages):
    print(f"=====================================")
    print(f"收到来自【{friend}】的新消息！")
    for msg in messages:
        print(f"消息内容: {msg}")
    print(f"=====================================")
    
    # 提示：在这里你可以把 messages 存入数据库，或者调用其他 AI 接口生成回复，
    # 如果想回消息，可以继续调用: 
    # from pyweixin.WeChatAuto import Messages
    # Messages.send_messages(friend=friend, messages=["好的，我收到了"], close_weixin=False)


# 2. 启动全局巡逻小红点模式
# duration='30min' 表示这个保安会巡逻30分钟
# interval=5 表示每隔5秒去左上角看一眼有没有小红点
# print("启动小红点巡逻...")
# Monitor.patrol_new_messages(
#     duration='30min', 
#     callback=handle_new_messages, 
#     interval=5.0,
#     close_weixin=False
# )
'''

from pyweixin import Moments
Moments.dump_friend_posts(friend='陈惠琳',number=10,save_detail=True)