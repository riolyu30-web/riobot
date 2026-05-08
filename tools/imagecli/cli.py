import click as CLICK # 导入 CLICK 库用于构建命令行界面
import os # 导入操作系统接口模块
import sys # 导入系统特定的参数和函数模块
import requests # 导入requests库，用于发送HTTP请求
import threading # 导入threading库，用于多线程操作
import time # 导入time库，用于时间相关操作
import dotenv # 导入dotenv库，用于加载环境变量文件
import uuid # 导入uuid库，用于生成唯一文件名
from PIL import Image # 导入PIL库中的Image模块，用于图像处理

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

if __name__ == "__main__": # 判断当前脚本是否作为主程序被直接运行
    cli() # 调用被CLICK装饰过的命令函数
