# api.py
from fastapi import APIRouter, BackgroundTasks
from typing import Optional, List # 导入Optional和List类型提示
import os # 导入操作系统接口模块
from pydantic import BaseModel # 导入BaseModel用于请求体定义
from PIL import Image # 导入PIL库用于图片处理
# import shutil # 导入高级文件操作模块，不再需要 shutil
from .jiekou_manager import jiekou_gpt_image, jiekou_gpt_image_edit # 从jiekou_manager导入图片生成和编辑接口
from .image_html_utils import initialize_image_html_with_loading, append_image_to_html # 从image_html_utils导入HTML初始化和图片追加函数
import time # 导入时间模块，用于生成时间戳前缀

router = APIRouter() # 创建APIRouter实例

class MergeImagesRequest(BaseModel): # 定义图片合并请求的数据模型
    image_paths: List[str] # 图片绝对路径列表，必需

class ImageRequest(BaseModel): # 定义图片请求的数据模型
    prompt: str # 提示词，必需
    html_path: str # HTML文件名，必需
    description: str = "" # 可选的图片描述，默认为空字符串
    image: Optional[str] = None # 可选的图片绝对路径字符串
    size: str = "1536x1024" # 尺寸选项，默认"1536x1024"
    prefix: str = "gpt" # 图片前缀，默认"gpt"



def _run_image_generation_task(prompt: str, html_path: str, image_path: Optional[str] = None, description: str = "", size: str = "1536x1024", prefix: str = "gpt") -> None:
    try: # 尝试执行图片生成逻辑
        initialize_image_html_with_loading(html_path) # 初始化HTML文件，确保文件存在并包含加载提示
        result_paths = [] # 初始化结果路径列表
        if image_path: # 判断是否传入了参考图片路径
            print("后台任务：检测到参考图片，正在调用 jiekou_gpt_image_edit 接口...") # 打印后台任务提示信息
            result_paths = jiekou_gpt_image_edit(image_path=image_path, prompt=prompt, size=size, prefix=prefix) # 传入绝对路径和提示词调用编辑接口
        else: # 如果没有传入参考图片路径
            print("后台任务：未提供参考图片，正在调用 jiekou_gpt_image 接口...") # 打印后台任务提示信息
            result_paths = jiekou_gpt_image(prompt=prompt, size=size, prefix=prefix) # 仅传入提示词调用目标行所在的生成接口
            
        if result_paths: # 检查接口是否成功返回了图片路径列表
            for path in result_paths: # 遍历返回的每一个图片路径
                abs_path = os.path.abspath(path) # 将相对路径转换为绝对路径               
                append_image_to_html(html_path, abs_path, prompt,description) # 调用函数，传入HTML路径、图片绝对路径和提示词，更新HTML文件
                print(f"图片下载完成，图片路径：{abs_path}") # 打印图片下载完成信息
        else: # 如果接口返回为空或None
            print("后台任务：图片生成失败，未能获取到图片路径。") # 打印错误提示信息
    except Exception as e: # 捕获后台任务执行过程中的异常 
        print(f"后台任务发生错误: {e}") # 打印详细的错误描述


@router.post("/task/create") # 定义一个POST接口，路径为 /task/create
async def append_image(
    request: ImageRequest, # 接收ImageRequest模型作为请求体
    background_tasks: BackgroundTasks # 注入BackgroundTasks依赖
):
   
    background_tasks.add_task(_run_image_generation_task, request.prompt, request.html_path, request.image, request.description, request.size, request.prefix) # 将图片生成任务添加到后台


    return None # 返回HTML文件路径


@router.post("/sync/create") # 定义一个POST接口，路径为 /sync/create
async def generate_image_sync( # 定义异步函数处理同步生成请求
    request: ImageRequest # 接收ImageRequest模型作为请求体参数
): # 函数签名结束
    try: # 开始捕获可能发生的异常
        result_paths = [] # 初始化存放生成图片相对路径的列表
        prefix = time.strftime("%Y%m%d-%H%M%S", time.localtime())
        if request.image: # 判断请求体中是否包含参考图片路径
            result_paths = jiekou_gpt_image_edit(image_path=request.image, prompt=request.prompt, size=request.size, prefix=prefix) # 包含则调用图片编辑接口并获取返回的路径列表
        else: # 如果请求体中没有提供参考图片路径
            result_paths = jiekou_gpt_image(prompt=request.prompt, size=request.size, prefix=prefix) # 直接调用文生图接口并获取返回的路径列表
            
        absolute_paths = [] # 初始化存放图片绝对路径的列表
        if result_paths: # 判断接口是否成功返回了图片路径
            for path in result_paths: # 遍历返回的每一个相对路径
                abs_path = os.path.abspath(path) # 将相对路径转换为系统的绝对路径
                absolute_paths.append(abs_path) # 将转换后的绝对路径添加到列表中
            return {"status": "success", "image_paths": absolute_paths} # 生成成功后，返回包含状态和所有绝对路径的字典
        else: # 如果接口调用完成但没有返回任何路径
            return {"status": "error", "message": "图片生成失败，未能获取到图片路径。"} # 返回失败的状态和提示信息
    except Exception as e: # 捕获整个生成过程中发生的任何未预期异常
        return {"status": "error", "message": f"同步生成过程发生错误: {str(e)}"} # 返回错误状态和具体的异常详情


@router.post("/sync/merge") # 定义一个POST接口，路径为 /sync/merge
async def merge_images_sync( # 定义异步函数处理合并图片请求
    request: MergeImagesRequest # 接收MergeImagesRequest模型作为请求体参数
): # 函数签名结束
    try: # 开始捕获可能发生的异常
        if not request.image_paths: # 判断图片路径列表是否为空
            return {"status": "error", "message": "图片路径列表不能为空"} # 如果为空则返回错误信息
            
        images = [] # 初始化用于存放打开图片对象的列表
        for path in request.image_paths: # 遍历传入的每一个图片绝对路径
            if os.path.exists(path): # 检查该路径对应的文件是否存在
                images.append(Image.open(path)) # 如果存在则使用PIL打开图片并加入列表
            else: # 如果文件不存在
                return {"status": "error", "message": f"图片文件不存在: {path}"} # 返回文件不存在的错误信息
                
        if not images: # 检查成功打开的图片列表是否为空
            return {"status": "error", "message": "未能成功读取任何图片"} # 返回读取失败的错误信息
            
        # 横向拼接逻辑：计算合并后图片的总宽度和最大高度
        widths, heights = zip(*(i.size for i in images)) # 提取所有图片的宽和高
        total_width = sum(widths) # 将所有图片的宽度相加作为新图片的总宽度
        max_height = max(heights) # 取所有图片高度的最大值作为新图片的高度
        
        # 创建一张全新的RGB模式空白图片
        merged_image = Image.new('RGB', (total_width, max_height)) # 默认背景为黑色
        
        x_offset = 0 # 初始化X轴的偏移量
        for im in images: # 遍历所有已打开的图片
            merged_image.paste(im, (x_offset, 0)) # 将单张图片粘贴到新图片的指定X轴位置
            x_offset += im.size[0] # 更新X轴偏移量，增加当前图片的宽度
            
        timestamp = time.strftime("%Y%m%d-%H%M%S", time.localtime()) # 生成当前的时间戳字符串
        output_filename = f"merged_{timestamp}.png" # 拼接合并后图片的最终文件名
        
        output_dir = os.path.abspath("static/temp") # 获取保存目录的绝对路径
        if not os.path.exists(output_dir): # 判断该目录是否存在
            os.makedirs(output_dir) # 如果不存在则递归创建
            
        output_path = os.path.join(output_dir, output_filename) # 拼接图片的完整绝对路径
        merged_image.save(output_path) # 将合并好的图片保存到本地硬盘
        
        return {"status": "success", "image_path": output_path} # 返回包含成功状态和图片绝对路径的字典
    except Exception as e: # 捕获合并过程中的任何异常
        return {"status": "error", "message": f"图片合并过程发生错误: {str(e)}"} # 返回错误状态及详细异常信息


