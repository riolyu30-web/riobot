import click as CLICK # 导入 CLICK 库用于构建命令行界面
import os # 导入操作系统接口模块
import sys # 导入系统特定的参数和函数模块
import requests # 导入requests库，用于发送HTTP请求
import threading # 导入threading库，用于多线程操作
import time # 导入time库，用于时间相关操作
import dotenv # 导入dotenv库，用于加载环境变量文件
import uuid # 导入uuid库，用于生成唯一文件名
from PIL import Image # 导入PIL库中的Image模块，用于图像处理
from ocr_manager import get_text # 导入 OCR 方法用于提取图片文字
import numpy as np # 导入 numpy 用于快速矩阵运算进行抠图

load_dotenv = dotenv.load_dotenv()
RIO_HOME = os.getenv("RIO_HOME", os.getcwd())

def _get_html_file_path(html_name: str) -> str: # 定义一个私有辅助函数，用于获取HTML文件的绝对路径

    webview_dir = os.path.join(RIO_HOME, "static", "webview") # 构造 static/webview 目录的绝对路径
    os.makedirs(webview_dir, exist_ok=True) # 确保 static/webview 目录存在，如果不存在则创建
    html_path = os.path.join(webview_dir, html_name) # 将 webview 目录路径与传入的HTML文件名进行拼接，得到文件的绝对路径
    if not html_path.endswith('.html'): # 如果文件名没有以.html结尾
        html_path += '.html' # 自动为文件名补充.html后缀
    return html_path # 返回HTML文件的绝对路径

def _get_image_file_path(prefix: str,index: int) -> str: # 定义一个私有辅助函数，用于获取图片文件的绝对路径
    image_dir = os.path.join(RIO_HOME, "static", "temp") # 构造 static/temp 目录的绝对路径
    os.makedirs(image_dir, exist_ok=True) # 确保 static/temp 目录存在，如果不存在则创建
    image_file = f'{image_dir}\\{prefix}-{index}.png' # 构造图片文件的绝对路径
    return image_file # 返回图片文件的绝对路径

def _send_request_in_background(api_url, data): # 定义一个辅助函数，用于在后台发送HTTP请求
    try: # 尝试发送HTTP请求
        requests.post(api_url, json=data) # 发送POST请求到FastAPI接口，以JSON格式传递数据
        CLICK.echo("调用API成功") # 打印HTML文件的路径，提示用户查看进度
    except requests.exceptions.ConnectionError: # 捕获连接错误
        CLICK.echo("错误: 无法连接到FastAPI服务。请确保服务正在运行 (uvicorn api:app --reload)。", err=True) # 打印连接错误信息
    except Exception as e: # 捕获其他异常
        CLICK.echo(f"调用API时发生错误: {e}", err=True) # 打印详细的错误描述

def _merge_images_to_temp(image1_path: str, image2_path: str) -> str: # 定义一个函数，接收两张图片的绝对路径并返回合并后图片的绝对路径
    img1 = Image.open(image1_path) # 使用PIL库打开第一张图片
    img2 = Image.open(image2_path) # 使用PIL库打开第二张图片
    new_width = img1.width + img2.width # 计算合并后新图片的宽度，即两张图片宽度相加
    new_height = max(img1.height, img2.height) # 计算合并后新图片的高度，取两张图片高度的最大值
    new_img = Image.new("RGBA", (new_width, new_height)) # 创建一张指定宽高的新图片，使用RGBA模式以支持透明度
    new_img.paste(img1) # 将第一张图片粘贴到新图片的左侧（默认坐标 0,0）
    new_img.paste(img2, (img1.width, 0)) # 将第二张图片粘贴到第一张图片的右侧（坐标为第一张图的宽度）
    temp_dir = os.path.join(RIO_HOME, "static","temp") # 构造 temp 文件夹的绝对路径
    os.makedirs(temp_dir, exist_ok=True) # 确保 temp 文件夹存在，如果不存在则自动创建
    file_name = f"merged_{uuid.uuid4().hex}.png" # 使用 uuid 生成一个唯一的文件名，后缀为 .png
    save_path = os.path.join(temp_dir, file_name) # 构造合并后图片的绝对保存路径
    new_img.save(save_path) # 将合并后的新图片保存到本地磁盘
    return save_path # 返回最终保存的图片绝对路径

def _is_image_empty(image_path: str) -> bool: # 定义一个函数，接收图片的绝对路径，判断图片是否为空（纯色或全透明）
    if not os.path.exists(image_path): # 检查图片路径是否存在
        return False # 如果不存在则认为不是空图片
    return True # 如果图片存在则认为是空图片

def _parse_color(color_str: str) -> tuple: # 定义一个辅助函数，用于解析颜色字符串为RGB元组
    color_str = color_str.lower().strip() # 将颜色字符串转换为小写并去除首尾空格
    if color_str in ['white', '白色']: # 判断是否为预设的白色
        return (255, 255, 255) # 返回白色的RGB值
    if color_str in ['black', '黑色']: # 判断是否为预设的黑色
        return (0, 0, 0) # 返回黑色的RGB值
    if color_str in ['red', '红色']: # 判断是否为预设的红色
        return (255, 0, 0) # 返回红色的RGB值
    if color_str in ['green', '绿色']: # 判断是否为预设的绿色
        return (0, 255, 0) # 返回绿色的RGB值
    if color_str in ['blue', '蓝色']: # 判断是否为预设的蓝色
        return (0, 0, 255) # 返回蓝色的RGB值
    if ',' in color_str: # 解析类似 255,255,255 的格式
        parts = color_str.split(',') # 按逗号分割字符串
        if len(parts) == 3: # 确保分割后有三个部分
            return tuple(int(p.strip()) for p in parts) # 将每个部分转换为整数并返回元组
    if color_str.startswith('#') and len(color_str) == 7: # 解析类似 #FFFFFF 的十六进制格式
        return (int(color_str[1:3], 16), int(color_str[3:5], 16), int(color_str[5:7], 16)) # 转换十六进制为RGB整数元组
    return (255, 255, 255) # 默认返回白色作为容错处理

def _remove_bg_to_temp(image_path: str, color_str: str, tolerance: int = 30, fg_color_str: str = None) -> str: # 定义抠图并保存到临时目录的辅助函数
    bg_color = _parse_color(color_str) # 解析目标背景颜色
    img = Image.open(image_path).convert("RGBA") # 使用PIL打开图片并转换为带有透明通道的RGBA模式
    data = np.array(img) # 将图片转换为numpy多维数组以进行快速的矩阵计算
    
    r = data[:, :, 0] # 提取所有像素的红色通道数据
    g = data[:, :, 1] # 提取所有像素的绿色通道数据
    b = data[:, :, 2] # 提取所有像素的蓝色通道数据
    
    # 生成布尔掩码，找出RGB三个通道都在目标颜色容差范围内的像素点
    mask = (np.abs(r.astype(int) - bg_color[0]) <= tolerance) & \
           (np.abs(g.astype(int) - bg_color[1]) <= tolerance) & \
           (np.abs(b.astype(int) - bg_color[2]) <= tolerance)
           
    data[:, :, 3][mask] = 0 # 将匹配到的背景像素的Alpha通道（透明度）设置为0（完全透明）
    
    if fg_color_str: # 如果指定了前景颜色
        fg_color = _parse_color(fg_color_str) # 解析前景颜色参数
        fg_mask = ~mask # 获取前景像素的掩码（背景掩码的取反）
        data[:, :, 0][fg_mask] = fg_color[0] # 将前景像素的红色通道修改为指定颜色
        data[:, :, 1][fg_mask] = fg_color[1] # 将前景像素的绿色通道修改为指定颜色
        data[:, :, 2][fg_mask] = fg_color[2] # 将前景像素的蓝色通道修改为指定颜色

    new_img = Image.fromarray(data) # 将处理后的numpy数组转换回PIL图片对象
    
    temp_dir = os.path.join(RIO_HOME, "static", "temp") # 构造临时存放目录的绝对路径
    os.makedirs(temp_dir, exist_ok=True) # 确保临时目录存在，如果不存在则创建
    file_name = f"nobg_{uuid.uuid4().hex}.png" # 使用uuid生成一个不重复的新图片文件名
    save_path = os.path.join(temp_dir, file_name) # 拼接出完整的保存绝对路径
    new_img.save(save_path) # 将抠图后的图片保存到磁盘
    return save_path # 返回图片的绝对路径

def _split_image_to_temp(image_path: str) -> list: # 定义切割图片为9宫格的辅助函数
    img = Image.open(image_path) # 使用PIL库打开图片
    width, height = img.size # 获取图片的宽度和高度
    item_width = width // 3 # 计算每个小图的宽度
    item_height = height // 3 # 计算每个小图的高度
    
    temp_dir = os.path.join(RIO_HOME, "static", "temp") # 构造临时存放目录的绝对路径
    os.makedirs(temp_dir, exist_ok=True) # 确保临时目录存在，如果不存在则创建
    
    saved_paths = [] # 初始化保存路径列表
    base_name = uuid.uuid4().hex[:8] # 生成一个短uuid作为基础文件名
    
    for i in range(3): # 遍历行
        for j in range(3): # 遍历列
            box = (j * item_width, i * item_height, (j + 1) * item_width, (i + 1) * item_height) # 计算当前小图的裁剪区域
            crop_img = img.crop(box) # 裁剪出小图
            file_name = f"split_{base_name}_{i}_{j}.png" # 构造小图的文件名
            save_path = os.path.join(temp_dir, file_name) # 构造小图的绝对保存路径
            crop_img.save(save_path) # 将小图保存到本地磁盘
            saved_paths.append(save_path) # 将保存路径添加到列表中
            
    return saved_paths # 返回所有切片的保存路径列表

@CLICK.group()
def cli():
    """图片生成命令行工具"""
    pass

@cli.command('create', context_settings=dict(ignore_unknown_options=True)) # 将下方的函数装饰为CLICK命令行命令，并设置忽略未知的命令行选项
@CLICK.option('--prompt', required=True, type=str, help='生成图片的提示词') # 添加必须的提示词选项
@CLICK.option('--image', type=str, default=None, help='参考图片的绝对路径') # 添加可选的参考图片路径选项
@CLICK.option('--html-name', type=str, default='gallery.html', help='展示图片的HTML文件名') # 添加HTML文件名的选项
@CLICK.option('--description', type=str, default='', help='图片搭配文案') # 添加可选的图片描述选项的选项
@CLICK.option('--size', type=CLICK.Choice(['1024x1024', '1024x1536', '1536x1024', '2048x2048', '2048x1152', '3840x2160', '2160x3840']), default='1536x1024', help='生成图片的尺寸')
def create(prompt, image, html_name, description, size, **kwargs): # 定义处理图片生成的CLI方法，接收选项参数以及吸收任何未知的参数
    # FastAPI 服务的URL
    api_url = "http://127.0.0.1:8200/gpt/task/create" # 定义FastAPI接口的URL地址

    # 初始化HTML文件，包含加载状态的图片
    html_path = _get_html_file_path(html_name) # 获取HTML文件的绝对路径
    prefix = time.strftime("%Y%m%d-%H%M%S", time.localtime()) # 生成当前时间的前缀，用于图片文件名的唯一性
    image_file = _get_image_file_path(prefix, 0) # 获取图片文件的绝对路径，初始索引为0
    data = {"prompt": prompt, "html_path": html_path, "description": description, "size": size, "prefix": prefix} # 构造请求数据字典

    if image: # 如果提供了图片路径
        if not os.path.isabs(image): # 检查图片路径是否为绝对路径
            image = os.path.abspath(image) # 转换为绝对路径
        if not os.path.exists(image): # 检查图片文件是否存在
            CLICK.echo(f"错误: 参考图片文件不存在: {image}", err=True) # 打印错误信息
            sys.exit(1) # 退出程序
        data["image"] = image # 将图片绝对路径添加到数据字典中

    # 启动一个新线程来发送HTTP请求，主线程立即退出
    thread = threading.Thread(target=_send_request_in_background, args=(api_url, data)) # 创建一个新线程，目标是_send_request_in_background函数，并传入参数
    thread.daemon = True # 将线程设置为守护线程，主程序退出时线程也会退出
    thread.start() # 启动线程
    CLICK.echo(f"图片生成任务已启动。请打开此HTML文件查看进度: {html_path} 图片保存路径: {image_file}") # 打印HTML文件的路径，提示用户查看进度
    time.sleep(0.5) # 给予线程足够的时间来启动HTTP请求
    sys.exit(0) # 立即退出程序，不等待后台任务完成

@cli.command('merge', help='合并两张图片') # 将下方的函数装饰为CLICK命令行命令，命令名为merge
@CLICK.argument('image1', type=str) # 添加第一个必填参数，表示第一张图片的绝对路径
@CLICK.argument('image2', type=str) # 添加第二个必填参数，表示第二张图片的绝对路径
def merge_command(image1, image2): # 定义合并图片的命令行执行函数
    if not os.path.isabs(image1): # 检查第一张图片路径是否为绝对路径
        image1 = os.path.abspath(image1) # 如果不是绝对路径则将其转换为绝对路径
    if not os.path.isabs(image2): # 检查第二张图片路径是否为绝对路径
        image2 = os.path.abspath(image2) # 如果不是绝对路径则将其转换为绝对路径
    save_path = _merge_images_to_temp(image1, image2) # 调用刚才定义的函数进行图片合并
    CLICK.echo(f"合并完成，图片保存路径: {save_path}") # 打印合并后图片的保存路径


@cli.command('check', help='检查图片是否存在') # 将下方的函数装饰为CLICK命令行命令，命令名为check-empty
@CLICK.argument('image', type=str) # 添加一个必填参数，表示图片的绝对路径
def check_empty_command(image): # 定义检查图片是否为空的命令行执行函数
    if not os.path.isabs(image): # 检查图片路径是否为绝对路径
        image = os.path.abspath(image) # 如果不是绝对路径则将其转换为绝对路径
    try: # 尝试执行检查逻辑
        if os.path.exists(image): # 如果图片存在
            CLICK.echo(f"检查结果: 图片已存在。") # 打印结果
        else: # 如果图片不为空
            CLICK.echo(f"检查结果: 图片不存在。") # 打印结果
    except Exception as e: # 捕获可能发生的异常（如文件不存在等）
        CLICK.echo(f"检查图片时发生错误: {e}", err=True) # 打印错误信息

@cli.command('ocr', help='识别图片中的文字') # 将下方的函数装饰为 CLICK 命令行命令，命令名为 ocr
@CLICK.argument('image', type=str) # 添加一个必填参数，表示图片的绝对路径
def ocr_command(image): # 定义 OCR 命令的执行函数
    if not os.path.isabs(image): # 检查图片路径是否为绝对路径
        CLICK.echo(f"错误: 请输入图片绝对路径: {image}", err=True) # 打印绝对路径要求提示
        sys.exit(1) # 退出程序并返回错误状态
    if not os.path.exists(image): # 检查图片文件是否存在
        CLICK.echo(f"错误: 图片文件不存在: {image}", err=True) # 打印文件不存在提示
        sys.exit(1) # 退出程序并返回错误状态
    try: # 尝试执行 OCR 识别
        text = get_text(image) # 调用 OCR 方法提取图片全部文字
        CLICK.echo(text) # 打印 OCR 识别结果
    except Exception as e: # 捕获识别过程中的异常
        CLICK.echo(f"OCR 识别失败: {e}", err=True) # 打印详细错误信息
        sys.exit(1) # 退出程序并返回错误状态

@cli.command('removebg', help='移除图片中指定颜色的背景使其透明') # 将下方的函数装饰为CLICK命令行命令，命令名为removebg
@CLICK.argument('image', type=str) # 添加一个必填参数，表示要处理的图片绝对路径
@CLICK.argument('color', type=str, default='white') # 添加一个可选参数，表示要扣除的背景颜色，默认为白色
@CLICK.option('--tolerance', type=int, default=30, help='颜色容差值（0-255），默认30') # 添加容差选项参数，以应对不均匀的背景颜色
@CLICK.option('--fg-color', type=str, default=None, help='将抠出的前景替换为指定颜色（如 black, white 等）') # 添加前景颜色选项参数，用于替换前景颜色
def removebg_command(image, color, tolerance, fg_color): # 定义执行抠图操作的命令行执行函数
    if not os.path.isabs(image): # 检查传入的图片路径是否为绝对路径
        image = os.path.abspath(image) # 如果不是绝对路径则将其自动转换为绝对路径
    if not os.path.exists(image): # 检查指定的图片文件在硬盘上是否存在
        CLICK.echo(f"错误: 图片文件不存在: {image}", err=True) # 打印文件不存在的错误提示信息
        sys.exit(1) # 退出程序并返回错误状态码1
    try: # 尝试执行核心的抠图逻辑操作
        save_path = _remove_bg_to_temp(image, color, tolerance, fg_color) # 调用抠图辅助函数并将结果存入临时目录
        CLICK.echo(f"抠图完成，图片保存路径: {save_path}") # 在控制台打印成功信息以及最终的保存路径
    except Exception as e: # 捕获运行过程中可能发生的任何异常情况
        CLICK.echo(f"抠图时发生错误: {e}", err=True) # 打印包含具体报错原因的详细错误信息
        sys.exit(1) # 退出程序并返回错误状态码1

@cli.command('split', help='将图片切割为9宫格') # 将下方的函数装饰为CLICK命令行命令，命令名为split
@CLICK.argument('image', type=str) # 添加一个必填参数，表示图片的绝对路径
def split_command(image): # 定义切割图片的命令行执行函数
    if not os.path.isabs(image): # 检查图片路径是否为绝对路径
        image = os.path.abspath(image) # 如果不是绝对路径则将其转换为绝对路径
    if not os.path.exists(image): # 检查图片文件是否存在
        CLICK.echo(f"错误: 图片文件不存在: {image}", err=True) # 打印文件不存在提示
        sys.exit(1) # 退出程序并返回错误状态
    try: # 尝试执行切割逻辑
        saved_paths = _split_image_to_temp(image) # 调用辅助函数切割图片
        CLICK.echo(f"切割完成，共生成 {len(saved_paths)} 张图片：") # 打印切割完成提示
        for path in saved_paths: # 遍历打印每一张图片的路径
            CLICK.echo(path) # 打印保存路径
    except Exception as e: # 捕获可能发生的异常
        CLICK.echo(f"切割图片时发生错误: {e}", err=True) # 打印错误信息
        sys.exit(1) # 退出程序并返回错误状态

if __name__ == "__main__": # 判断当前脚本是否作为主程序被直接运行
    cli() # 调用被CLICK装饰过的命令函数
