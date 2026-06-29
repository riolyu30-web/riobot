import os # 导入os模块，用于获取环境变量
import requests # 导入requests库，用于发送HTTP请求
import json # 导入json库，用于处理JSON数据
import time # 导入time模块，用于生成时间戳
from .supabase_manager import SupabaseManager # 导入SupabaseManager，用于文件上传
supabase_manager = SupabaseManager() # 实例化SupabaseManager
from dotenv import load_dotenv
load_dotenv()
def dashscope_happy_create(prompt: str, first_frame_image: str, resolution: str = "720P", ratio: str = "16:9", duration: int = 6): # 定义dashscope_happy_create函数，用于创建视频
    api_key = os.getenv("DASHSCOPE_API_KEY") # 从环境变量中获取DASHSCOPE_API_KEY
    print(api_key)
    if not api_key: # 如果API密钥不存在
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置") # 抛出错误

    url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/video-generation/video-synthesis" # 定义API请求URL
    headers = { # 定义请求头
        "X-DashScope-Async": "enable", # 启用异步模式
        "Authorization": f"Bearer {api_key}", # 设置授权头，包含API密钥
        "Content-Type": "application/json" # 设置内容类型为JSON
    }

    media_list = [] # 初始化媒体列表
    # 处理 first_frame_image
    if first_frame_image.startswith("http://") or first_frame_image.startswith("https://"): # 如果是URL
        media_list.append({"type": "reference_image", "url": first_frame_image}) # 直接添加到媒体列表
    else: # 如果是本地文件路径
        try: # 尝试上传文件
            # 假设上传到名为 'dashscope-images' 的 bucket
            public_url = supabase_manager.upload_file("dashscope", first_frame_image) # 上传文件并获取公共URL
            print(public_url) # 打印公共URL，用于调试
            media_list.append({"type": "reference_image", "url": public_url}) # 将公共URL添加到媒体列表
        except Exception as e: # 捕获上传异常
            print(f"上传文件 {first_frame_image} 到 Supabase 失败: {e}") # 打印错误信息
            return {"error": f"文件上传失败: {first_frame_image} - {str(e)}"} # 返回错误信息

    payload = { # 定义请求体
        "model": "happyhorse-1.0-r2v", # 指定模型
        "input": { # 输入参数
            "prompt": prompt, # 提示词
            "media": media_list # 媒体列表
        },
        "parameters": { # 参数
            "resolution": resolution, # 分辨率
            "ratio": ratio, # 比例
            "duration": duration # 持续时间
        }
    }

    try: # 尝试发送请求
        response = requests.post(url, headers=headers, data=json.dumps(payload)) # 发送POST请求
        response.raise_for_status() # 检查请求是否成功，如果失败则抛出HTTPError
        return response.json() # 返回JSON响应
    except requests.exceptions.RequestException as e: # 捕获请求异常
        print(f"请求失败: {e}") # 打印错误信息
        return {"error": str(e)} # 返回错误信息

def get_dashscope_task_status(task_id: str): # 定义get_dashscope_task_status函数，用于获取任务状态
    api_key = os.getenv("DASHSCOPE_API_KEY") # 从环境变量中获取DASHSCOPE_API_KEY
    if not api_key: # 如果API密钥不存在
        raise ValueError("DASHSCOPE_API_KEY 环境变量未设置") # 抛出错误

    url = f"https://dashscope.aliyuncs.com/api/v1/tasks/{task_id}" # 定义API请求URL，包含任务ID
    headers = { # 定义请求头
        "Authorization": f"Bearer {api_key}" # 设置授权头，包含API密钥
    }

    try: # 尝试发送请求
        response = requests.get(url, headers=headers) # 发送GET请求
        response.raise_for_status() # 检查请求是否成功，如果失败则抛出HTTPError
        
        result = response.json() # 解析JSON响应
        task_status = result.get("output", {}).get("task_status") # 获取任务状态
        result["downloaded_paths"] = [] # 初始化下载路径列表
        print(result) # 打印原始响应
        if task_status == "SUCCEEDED": # 如果任务成功
            video_url = result.get("output", {}).get("video_url") # 获取视频URL
            if video_url: # 如果视频URL存在
                local_video_path = download_video(video_url) # 下载视频到本地
                result["downloaded_paths"].append(local_video_path) # 将本地视频路径添加到结果中
        return result # 返回处理后的结果
    except requests.exceptions.RequestException as e: # 捕获请求异常
        print(f"获取任务状态失败: {e}") # 打印错误信息
        return {"error": str(e)} # 返回错误信息

def download_video(video_url: str, prefix: str = "hh", out_dir: str = "./static/temp") -> str: # 定义下载视频的辅助函数
    if not video_url: # 如果视频URL为空
        return "" # 返回空字符串
    if not os.path.exists(out_dir): # 如果输出目录不存在
        os.makedirs(out_dir) # 递归创建输出目录
    
    try: # 尝试下载视频
        response = requests.get(video_url, stream=True) # 发送GET请求获取视频内容，使用stream模式
        response.raise_for_status() # 检查请求是否成功
        
        timestamp = int(time.time() * 1000) # 获取当前毫秒级时间戳
        filename = f"{prefix}-{timestamp}.mp4" # 构造本地文件名
        file_path = os.path.join(out_dir, filename) # 拼接完整文件路径
        
        with open(file_path, "wb") as f: # 以二进制写模式打开文件
            for chunk in response.iter_content(chunk_size=8192): # 迭代获取文件内容块
                f.write(chunk) # 写入文件块
        return file_path.replace("\\", "/") # 返回成功保存的视频路径，并统一使用正斜杠
    except requests.exceptions.RequestException as e: # 捕获请求异常
        print(f"下载视频 {video_url} 失败: {e}") # 打印下载失败信息
        return "" # 返回空字符串

