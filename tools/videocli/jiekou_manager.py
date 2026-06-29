import requests
from openai import OpenAI
import base64
import mimetypes
from dotenv import load_dotenv
import os
load_dotenv()
JIEKOU_API_KEY = os.getenv("JIEKOU_API_KEY")

def encode_base64(file_path):
        # 如果输入已经是Base64格式（以data:image开头），直接返回
    if file_path.startswith("data:image"):
        return file_path
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError("不支持或无法识别的图像格式")
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"
def download_media(media_list: list[dict], prefix: str = "jiekou", out_dir: str = "./static/temp", media_type: str = "image") -> list[str]: # 定义下载媒体文件到本地的辅助函数
    if not media_list: # 如果媒体列表为空则直接返回空列表
        return [] # 返回空列表
    if not os.path.exists(out_dir): # 如果输出目录不存在
        os.makedirs(out_dir) # 递归创建输出目录
    saved_paths = [] # 初始化保存路径列表
    for i, media_item in enumerate(media_list): # 遍历媒体文件列表
        url = media_item.get(f"{media_type}_url") # 获取媒体文件的URL
        if not url: # 如果URL不存在则跳过
            continue # 继续下一个媒体文件
        try: # 尝试下载单个媒体文件
            res = requests.get(url) # 发送GET请求获取媒体内容
            res.raise_for_status() # 检查请求是否成功
            file_extension = mimetypes.guess_extension(res.headers.get("Content-Type", "").split(';')[0]) # 根据Content-Type猜测文件扩展名
            if not file_extension: # 如果无法猜测扩展名
                file_extension = ".bin" # 默认使用.bin扩展名
            filename = f"{prefix}-{i}{file_extension}" # 构造本地文件名
            file_path = os.path.join(out_dir, filename) # 拼接完整文件路径
            with open(file_path, "wb") as f: # 以二进制写模式打开文件
                f.write(res.content) # 写入媒体二进制数据
            saved_paths.append(file_path.replace("\\", "/")) # 将路径存入列表并统一使用正斜杠
        except Exception as e: # 捕获单个媒体文件下载异常
            print(f"Failed to download {url}: {e}") # 打印下载失败信息
    return saved_paths # 返回成功保存的所有媒体文件路径列表

    
def jiekou_sd2(prompt: str, image: str = None, ratio: str = None, duration: int = 6, seed: int = -1, fast: bool = False, watermark: bool = True, last_image: str = None, resolution: str = None, web_search: bool = False, generate_audio: bool = False, reference_audios: list = None, reference_images: list = None, reference_videos: list = None, return_last_frame: bool = False) -> str: # 定义 Seedance 2.0 异步生成接口
    url = "https://api.jiekou.ai/v3/async/seedance-2.0" # 设置接口请求的 URL 地址
    payload = { # 构造请求的载荷数据字典
        "fast": fast, # 是否开启快速生成模式
        "seed": seed, # 设置生成随机种子
        "prompt": prompt, # 设置生成视频的提示词
        "duration": duration, # 设置生成视频的时长
        "watermark": watermark, # 是否添加水印
        "web_search": web_search, # 是否开启联网搜索增强
        "generate_audio": generate_audio, # 是否同步生成音频
        "return_last_frame": return_last_frame # 是否返回最后一帧图片
    } # 结束基础载荷字典定义
    if image: # 如果提供了初始图片
        payload["image"] = encode_base64(image) # 编码并添加初始图片
    if ratio: # 如果指定了画面比例
        payload["ratio"] = ratio # 添加画面比例参数
    if last_image: # 如果提供了结束图片
        payload["last_image"] = encode_base64(last_image) # 编码并添加结束图片
    if resolution: # 如果指定了分辨率
        payload["resolution"] = resolution # 添加分辨率参数
    if reference_audios: # 如果提供了参考音频列表
        payload["reference_audios"] = [encode_base64(audio) for audio in reference_audios] # 编码并添加参考音频参数
    if reference_images: # 如果提供了参考图片列表
        payload["reference_images"] = [encode_base64(image) for image in reference_images] # 编码并添加参考图片参数
    if reference_videos: # 如果提供了参考视频列表
        payload["reference_videos"] = [encode_base64(video) for video in reference_videos] # 编码并添加参考视频参数
    headers = { # 构造请求的头部信息字典
        "Content-Type": "application/json", # 指定请求内容类型为 JSON 格式
        "Authorization": f"Bearer {JIEKOU_API_KEY}" # 设置 API 授权令牌
    } # 结束头部字典定义
    proxies = {"http": None, "https": None} # 禁用代理以避免网络连接错误
    try: # 开始尝试执行网络请求
        response = requests.post(url, json=payload, headers=headers, proxies=proxies) # 发送 POST 请求并获取响应
        response.raise_for_status() # 检查响应状态码是否正常
        return response.json().get("task_id") # 解析响应 JSON 并返回任务 ID
    except Exception as e: # 捕获请求过程中的异常
        print(f"Error calling jiekou_sd2: {e}") # 打印详细的错误描述
        return None # 发生错误时返回空值

def jiekou_query_task_status(task_id: str, out_dir: str = "./static/temp", prefix: str = "jiekou") -> dict: # 定义查询任务状态的接口函数
    url = f"https://api.jiekou.ai/v3/async/task-result?task_id={task_id}" # 设置接口请求的 URL 地址，并带上 task_id 参数
    headers = { # 构造请求的头部信息字典
        "Content-Type": "application/json", # 指定请求内容类型为 JSON 格式
        "Authorization": f"Bearer {JIEKOU_API_KEY}" # 设置 API 授权令牌
    } # 结束头部字典定义
    proxies = {"http": None, "https": None} # 禁用代理以避免网络连接错误
    try: # 开始尝试执行网络请求
        response = requests.get(url, headers=headers, proxies=proxies) # 发送 GET 请求并获取响应
        response.raise_for_status() # 检查响应状态码是否正常
        result = response.json() # 解析响应 JSON
        task_info = result.get("task", {}) # 获取任务信息，如果不存在则返回空字典
        task_status = task_info.get("status") # 获取任务状态
        downloaded_paths = [] # 初始化下载路径列表
        if task_status == "TASK_STATUS_SUCCEED": # 如果任务成功
            images = result.get("images", []) # 获取图片列表
            videos = result.get("videos", []) # 获取视频列表
            audios = result.get("audios", []) # 获取音频列表
            if images: # 如果有图片
                downloaded_paths = download_media(images, prefix=prefix, out_dir=out_dir, media_type="image")# 下载图片
            if videos: # 如果有视频
                downloaded_paths = download_media(videos, prefix=prefix, out_dir=out_dir, media_type="video")# 下载视频
            if audios: # 如果有音频
                downloaded_paths = download_media(audios, prefix=prefix, out_dir=out_dir, media_type="audio")# 下载音频
        result["downloaded_paths"] = downloaded_paths # 将下载路径添加到结果中
        return result # 返回包含任务状态和下载路径的结果
    except Exception as e: # 捕获请求过程中的异常
        print(f"Error calling jiekou_query_task_status: {e}") # 打印详细的错误描述
        return {"task": {"status": "FAILED", "reason": str(e)}} # 发生错误时返回失败状态和错误信息

def jiekou_sd_video_edit(video_path: str, prompt: str, duration: int = 5, resolution: str = None, watermark: bool = True, reference_images: list = None, reference_audios: list = None) -> str: # 定义 Seedance 视频编辑异步生成接口
    url = "https://api.jiekou.ai/v3/async/seedance-video-edit" # 设置接口请求的 URL 地址
    payload = { # 构造请求的载荷数据字典
        "video": encode_base64(video_path), # 编码并添加视频文件
        "prompt": prompt, # 设置生成视频的提示词
        "duration": duration, # 设置生成视频的时长
        "watermark": watermark # 是否添加水印
    } # 结束基础载荷字典定义
    if resolution: # 如果指定了分辨率
        payload["resolution"] = resolution # 添加分辨率参数
    if reference_images: # 如果提供了参考图片列表
        payload["reference_images"] = [encode_base64(image) for image in reference_images] # 编码并添加参考图片参数
    if reference_audios: # 如果提供了参考音频列表
        payload["reference_audios"] = [encode_base64(audio) for audio in reference_audios] # 编码并添加参考音频参数
    headers = { # 构造请求的头部信息字典
        "Content-Type": "application/json", # 指定请求内容类型为 JSON 格式
        "Authorization": f"Bearer {JIEKOU_API_KEY}" # 设置 API 授权令牌
    } # 结束头部字典定义
    proxies = {"http": None, "https": None} # 禁用代理以避免网络连接错误
    try: # 开始尝试执行网络请求
        response = requests.post(url, json=payload, headers=headers, proxies=proxies) # 发送 POST 请求并获取响应
        response.raise_for_status() # 检查响应状态码是否正常
        return response.json().get("task_id") # 解析响应 JSON 并返回任务 ID
    except Exception as e: # 捕获请求过程中的异常
        print(f"Error calling jiekou_sd_video_edit: {e}") # 打印详细的错误描述
        return None # 发生错误时返回空值


