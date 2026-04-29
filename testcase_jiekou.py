import requests # 导入 requests 库，用于发送 HTTP 请求
import os       # 导入 os 库，用于访问环境变量

# API 端点 URL
url = "https://api.jiekou.ai/v3/gpt-image-2-text-to-image"

# 从环境变量中获取 API 密钥
api_key = 'sk_JO4KTxWC2GgpqdryjagccF-DXLVS4sBp3aAUhb_366c'

# 检查 API 密钥是否存在
if not api_key:
    print("错误：API_KEY 环境变量未设置。") # 如果 API 密钥未设置，则打印错误消息
    exit(1) # 退出程序

# 请求头
headers = {
    "Content-Type": "application/json", # 设置内容类型为 JSON
    "Authorization": f"Bearer {api_key}" # 设置授权头，包含 API 密钥
}

# 请求体
data = {
    "n": 1,             # 生成图片的数量
    "size": "1024x1024", # 图片尺寸
    "quality": "medium", # 图片质量
    "background": "auto", # 背景设置
    "moderation": "auto", # 审核设置
    "output_format": "png", # 输出格式
    "prompt": "与中国联通公司开小会的图片"
}

try:
    # 发送 POST 请求，设置超时时间（例如 60 秒）
    response = requests.post(url, headers=headers, json=data, timeout=600) # 发送 POST 请求，并传递 URL、请求头、JSON 数据和超时时间
    response.raise_for_status() # 检查请求是否成功，如果状态码表示错误，则抛出异常

    # 打印响应
    print("请求成功！") # 打印成功消息
    print("状态码:", response.status_code) # 打印 HTTP 状态码
    print("响应体:", response.json()) # 打印 JSON 格式的响应体

except requests.exceptions.RequestException as e:
    print(f"请求失败: {e}") # 如果请求失败，则打印错误信息
    if response is not None:
        print("状态码:", response.status_code) # 打印 HTTP 状态码
        print("响应体:", response.text) # 打印响应体内容
