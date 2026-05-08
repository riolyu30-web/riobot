# 导入requests库用于发起HTTP网络请求
import requests

# 定义发送微信消息的测试函数
def test_send_message():
    # 定义目标接口的URL地址，根据要求访问/wx/send
    url = "http://127.0.0.1:8200/wx/send"
    
    # 构造请求体参数，对应SendMessageRequest模型
    payload = {
        # 传入必填字段text，指定要发送的文本内容
        "text": "这是一条来自测试用例的消息",
        # 传入选填字段user_id，指定接收消息的用户（选填）
        "user_id": "filehelper"
    }
    
    # 打印提示信息，表示开始发送请求
    print(f"正在向 {url} 发送请求...")
    
    # 使用try-except代码块捕获可能发生的网络异常
    try:
        # 调用requests的post方法发送JSON格式请求
        response = requests.post(url, json=payload)
        
        # 打印接口返回的HTTP状态码
        print(f"响应状态码: {response.status_code}")
        
        # 打印接口返回的JSON响应内容
        print(f"响应结果: {response.json()}")
        
    # 捕获所有的Exception异常并赋值给变量e
    except Exception as e:
        # 打印异常报错的详细信息
        print(f"请求失败，错误信息: {e}")

# 判断当前脚本是否作为主程序运行
if __name__ == "__main__":
    # 执行测试发送消息的函数
    test_send_message()
