import requests
from openai import OpenAI
import base64
import mimetypes
import os
import time # 导入时间模块用于生成唯一文件名
import json # 导入JSON模块用于解析响应数据

from PIL import Image
import io
from dotenv import load_dotenv
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

def download_images(response_text: str, prefix: str = "jiekou", out_dir: str = "./static/temp") -> list[str]: # 定义下载图片到本地的辅助函数
    if not response_text: # 如果响应文本为空则直接返回空列表
        return [] # 返回空列表
    try: # 开始尝试解析JSON并下载
        data = json.loads(response_text) if isinstance(response_text, str) else response_text # 如果输入是字符串则解析JSON，否则直接使用
        raw_images = data.get("images", []) # 获取响应中的图片数据列表
        image_urls = [] # 初始化图片URL列表
        for img in raw_images: # 遍历原始图片数据
            if isinstance(img, str): # 如果元素是字符串（直接是URL）
                image_urls.append(img) # 直接添加到URL列表
            elif isinstance(img, dict) and img.get("url"): # 如果是字典且包含url键
                image_urls.append(img.get("url")) # 提取url并添加到列表
        if not os.path.exists(out_dir): # 如果输出目录不存在
            os.makedirs(out_dir) # 递归创建输出目录
        saved_paths = [] # 初始化保存路径列表
        for i, url in enumerate(image_urls): # 遍历图片链接列表
            try: # 尝试下载单张图片
                res = requests.get(url) # 发送GET请求获取图片内容
                res.raise_for_status() # 检查请求是否成功
                filename = f"{prefix}-{i}.png" # 构造本地文件名
                file_path = os.path.join(out_dir, filename) # 拼接完整文件路径
                with open(file_path, "wb") as f: # 以二进制写模式打开文件
                    f.write(res.content) # 写入图片二进制数据
                saved_paths.append(file_path.replace("\\", "/")) # 将路径存入列表并统一使用正斜杠
            except Exception as e: # 捕获单张图片下载异常
                print(f"Failed to download {url}: {e}") # 打印下载失败信息
        return saved_paths # 返回成功保存的所有图片路径列表
    except Exception as e: # 捕获整体处理异常
        print(f"Error in download_images: {e}") # 打印处理错误信息
        return [] # 返回空列表

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




def jiekou_chat_json(system_prompt: str, user_prompt: str,model: str = "claude-sonnet-4-5-20250929",output_file_path: str = "frames.json") -> None:
    client = OpenAI(
        base_url="https://api.jiekou.ai/openai",
        api_key=JIEKOU_API_KEY,
    )
    try:
    
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            max_tokens=64000,
        )

        content = response.choices[0].message.content
        print(content)

        # Extract JSON content if wrapped in markdown code block
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        json_str = json_match.group(1) if json_match else content

        with open(output_file_path, 'w', encoding='utf-8') as f:
            f.write(json_str)
    except Exception as e:
        print(f"Error: {e}")

def jiekou_chat(system_prompt: str, user_prompt: str,model: str = "claude-sonnet-4-5-20250929") -> None:
    client = OpenAI(
        base_url="https://api.jiekou.ai/openai",
        api_key=JIEKOU_API_KEY,
    )
    try:
    
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            max_tokens=64000,
        )

        return response

    except Exception as e:
        print(f"Error: {e}")

def jiekou_chat_image(system_prompt: str, user_prompt: str,images: list[str] = [],model: str = "claude-sonnet-4-5-20250929") -> str:
    client = OpenAI(
        base_url="https://api.jiekou.ai/openai",
        api_key=JIEKOU_API_KEY,
    )
    try:
        # 编码图片为Base64
        encoded_images = [encode_base64(img) for img in images]

        # 构造多模态消息内容
        content = []
        for base64_img in encoded_images:
            content.append({
                "type": "image_url",
                "image_url": {
                    "url": base64_img
                }
            })
        
        content.append({
            "type": "text",
            "text": system_prompt
        })
        print(content)
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": content},
            ],
            stream=False,
            max_tokens=64000,
        )

        return response

    except Exception as e:
        print(f"Error: {e}")

def jiekou_banaan_pro(prompt: str, images: list[dict], n: int = 1, size: str = "1024x1024", quality: str = "1k", response_format: str = "url", mask: str = None) -> list[str]: # 更新返回类型为路径列表
    url = "https://api.jiekou.ai/v3/nano-banana-pro-light-i2i"
    
    payload = {
        "n": n,
        "images": images,
        "prompt": prompt,
        "quality": quality,
        "response_format": response_format
    }
    
    if size:
        payload["size"] = size
        
    if mask:
        payload["mask"] = mask

    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {JIEKOU_API_KEY}"
    }

    proxies = {"http": None, "https": None} # 禁用代理
    try:
        response = requests.post(url, json=payload, headers=headers, proxies=proxies) # 忽略代理进行请求
        response.raise_for_status()
        print(response.text)
        return download_images(response.text, prefix="banana") # 调用辅助函数下载图片并返回本地路径列表
    except Exception as e: # 捕获所有可能的异常
        print(f"Error calling jiekou_banaan_pro: {e}") # 打印错误信息
        return None # 发生错误时返回空值

def jiekou_gpt_image(prompt: str, prefix: str, n: int = 1, size: str = "1536x1024", quality: str = "low", background: str = "auto", moderation: str = "auto", output_format: str = "png") -> list[str]: # 定义生成GPT图片的接口函数并返回路径列表
    url = "https://api.jiekou.ai/v3/gpt-image-2-text-to-image" # 设置接口请求的URL地址
    payload = { # 构造请求的载荷数据字典
        "n": n, # 设置生成图片的数量
        "size": size, # 设置图片的尺寸规格
        "prompt": prompt, # 设置生成图片的提示词
        "quality": quality, # 设置生成图片的质量级别
        "background": background, # 设置背景处理模式
        "moderation": moderation, # 设置内容审核模式
        "output_format": output_format # 设置输出图片的格式
    } # 结束载荷字典的定义
    headers = { # 构造请求的头部信息字典
        "Content-Type": "application/json", # 指定请求内容类型为JSON格式
        "Authorization": f"Bearer {JIEKOU_API_KEY}" # 设置API授权令牌
    } # 结束头部字典的定义
    proxies = {"http": None, "https": None} # 禁用代理以避免网络连接错误
    try: # 开始尝试执行网络请求
        response = requests.post(url, json=payload, headers=headers, proxies=proxies) # 发送POST请求并获取响应，同时绕过系统代理
        response.raise_for_status() # 如果响应状态码不是200则抛出异常
        print(response.text) # 在控制台打印接口返回的原始文本
        return download_images(response.text, prefix=prefix) # 解析响应并下载图片到本地，返回路径列表
    except Exception as e: # 捕获请求过程中的异常
        print(f"Error calling jiekou_gpt_image: {e}") # 打印详细的错误描述
        return None # 发生错误时返回空值

def jiekou_gpt_image_edit(image_path: str, prompt: str, prefix: str, mask_path: str = None, n: int = 1, size: str = "1536x1024", quality: str = "low", background: str = "auto", output_format: str = "png") -> list[str]: # 定义编辑GPT图片的接口函数并返回路径列表
    url = "https://api.jiekou.ai/v3/gpt-image-2-edit" # 设置编辑图片的接口URL
    payload = { # 初始化请求载荷字典
        "n": n, # 设置生成的图片数量
        "prompt": prompt, # 设置修改图片的提示词
        "image": encode_base64(image_path), # 调用encode_base64编码主图文件
        "size": size, # 设置生成的图片尺寸
        "quality": quality, # 设置生成的图片质量
        "background": background, # 设置图片的背景模式
        "output_format": output_format # 设置最终输出的文件格式
    } # 结束基本载荷字典的定义
    if mask_path: # 判断是否提供了蒙版文件路径
        payload["mask"] = encode_base64(mask_path) # 编码蒙版图片并添加到载荷中
    headers = { # 构造HTTP请求头字典
        "Content-Type": "application/json", # 设置请求体格式为JSON
        "Authorization": f"Bearer {JIEKOU_API_KEY}" # 配置API访问授权令牌
    } # 结束请求头字典的定义
    proxies = {"http": None, "https": None} # 显式禁用网络代理
    try: # 进入网络请求尝试块
        response = requests.post(url, json=payload, headers=headers, proxies=proxies) # 发起POST异步请求，禁用代理设置
        response.raise_for_status() # 验证HTTP响应状态是否正常
        print(response.text) # 在终端打印接口返回的原始数据
        return download_images(response.text, prefix=prefix) # 调用辅助函数将返回的图片保存至本地并返回路径
    except Exception as e: # 捕获所有可能的运行异常
        print(f"Error calling jiekou_gpt_image_edit: {e}") # 输出详细的错误调用日志
        return None # 遇到错误时统一返回空值

def jiekou_sd2(prompt: str, image: str = None, ratio: str = None, duration: int = 5, seed: int = -1, fast: bool = False, watermark: bool = True, last_image: str = None, resolution: str = None, web_search: bool = False, generate_audio: bool = False, reference_audios: list = None, reference_images: list = None, reference_videos: list = None, return_last_frame: bool = False) -> str: # 定义 Seedance 2.0 异步生成接口
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


