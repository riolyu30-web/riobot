import json
import os
from fastapi import FastAPI, Request, UploadFile, File
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
# 导入CORS中间件用于处理跨域请求
from fastapi.middleware.cors import CORSMiddleware
from tools.imagecli.api import router as image_cli_router # 导入 imagecli 的路由
from tools.weixin.api import router as weixin_router # 导入 weixin 的路由
from tools.videocli.api import router as video_cli_router # 导入 video-cli  的路由

# 导入 glob 模块用于查找匹配特定规则的文件路径
import glob
from pydantic import BaseModel
# 导入 datetime 模块，用于获取当前日期和时间
from datetime import datetime
import shutil
# 定义一个请求体模型，用于接收需要删除的文件绝对路径
class DeleteFileRequest(BaseModel):
    # 必须提供一个字符串类型的 file_path 参数
    file_path: str

# 初始化FastAPI应用
app = FastAPI()


# 添加CORS中间件配置
app.add_middleware(
    CORSMiddleware,
    # 允许的源地址列表
    allow_origins=["*"],  # 在生产环境中应该指定具体的域名
    # 允许携带凭证
    allow_credentials=True,
    # 允许的HTTP方法
    allow_methods=["*"],
    # 允许的请求头
    allow_headers=["*"],
)

app.include_router(image_cli_router, prefix="/gpt") # 包含 image-cli 的路由，并设置前缀
app.include_router(weixin_router, prefix="/wx") # 包含 weixin 的路由，并设置前缀
app.include_router(video_cli_router, prefix="/vi") # 包含 video-cli 的路由，并设置前缀



# 定义一个 GET 接口，用于根据传入的目录名获取其下所有的 HTML 文件
@app.get("/list/html")
# 接收名为 directory 的查询参数，默认值为 webview
def get_html_files(directory: str = "webview"):
    # 构建基础的 static 目录绝对路径
    base_dir = os.path.abspath("static")
    # 构建目标查询目录的绝对路径
    target_dir = os.path.join(base_dir, directory)
    # 构建 glob 需要的匹配表达式，匹配该目录下及其子目录的所有 .html 文件
    search_pattern = os.path.join(target_dir, "**", "*.html")
    # 使用 glob.glob 进行递归查找，返回所有符合条件的绝对路径列表
    html_files = glob.glob(search_pattern, recursive=True)
    
    # 初始化一个用于存储文件信息的空列表
    result = []
    # 遍历每一个找到的文件绝对路径
    for file_path in html_files:
        # 提取文件路径中的文件名（包含扩展名），赋值给 name 变量
        name = os.path.basename(file_path)
        # 获取该文件相对于 static 目录的相对路径，以便前端拼接 URL
        rel_path = os.path.relpath(file_path, base_dir)
        # 将 Windows 系统的反斜杠替换为正斜杠，确保 URL 的正确性
        rel_path = rel_path.replace("\\", "/")
        # 将包含文件名、绝对路径和相对路径的字典追加到结果列表中
        result.append({"name": name, "absolute_path": file_path, "relative_path": rel_path})
        
    # 将包含所有文件信息的字典作为 JSON 格式返回给前端
    return {"files": result}

# 定义一个 GET 接口，用于按层级获取目录下的文件和子目录
@app.get("/list/dir")
def get_dir_contents(directory: str = ""):
    base_dir = os.path.abspath("static")
    # 如果传入的目录名是 static，则将其视为空路径（代表 static 根目录）
    if directory == "static":
        directory = ""
    # 构建目标查询目录的绝对路径
    target_dir = os.path.abspath(os.path.join(base_dir, directory))
    
    # 安全检查：防止路径穿越
    if not target_dir.startswith(base_dir):
        return {"files": [], "dirs": []}
        
    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return {"files": [], "dirs": []}
        
    dirs = []
    files = []
    
    # 定义支持的媒体和文件扩展名（图片、视频、普通文件、语音）
    SUPPORTED_EXTS = (
        # IMAGE
        ".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp",
        # VIDEO
        ".mp4", ".mov", ".avi", ".mkv", ".webm",
        # FILE
        ".html", ".txt", ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".zip", ".rar", ".7z", ".json", ".xml", ".csv", ".md",
        # VOICE
        ".mp3", ".wav", ".m4a", ".ogg", ".silk", ".flac"
    )

    for item in os.listdir(target_dir):
        item_path = os.path.join(target_dir, item)
        rel_path = os.path.relpath(item_path, base_dir).replace("\\", "/")
        
        # 如果是目录，则添加到子目录列表中
        if os.path.isdir(item_path):
            # 将目录的名称、相对路径和绝对路径作为字典追加到 dirs 列表中
            dirs.append({
                "name": item,
                "relative_path": rel_path,
                "absolute_path": item_path
            })
        # 如果是文件，并且扩展名在支持的列表中（忽略大小写），则添加到文件列表中
        elif os.path.isfile(item_path) and item.lower().endswith(SUPPORTED_EXTS):
            # 将文件的名称、相对路径和绝对路径作为字典追加到 files 列表中
            files.append({
                "name": item,
                "relative_path": rel_path,
                "absolute_path": item_path
            })
            
    return {"dirs": dirs, "files": files}

# 定义一个 DELETE 接口，用于接收绝对路径并删除对应文件
@app.delete("/del/file")
def delete_file(request: DeleteFileRequest):
    # 获取传入的文件绝对路径
    file_path = request.file_path
    # 检查该文件是否存在
    if os.path.exists(file_path):
        try:
            # 尝试删除文件
            os.remove(file_path)
            # 删除成功后返回成功信息
            return {"success": True, "message": "文件删除成功"}
        except Exception as e:
            # 捕获删除过程中的异常并返回错误信息
            return {"success": False, "message": f"删除失败: {str(e)}"}
    else:
        # 如果文件不存在，则返回错误信息
        return {"success": False, "message": "文件不存在"}


@app.post("/up")
# 定义一个异步函数来处理文件上传请求，路径为 /up
async def upload_file(file: UploadFile = File(...)):

    # 分离文件名和后缀
    name, ext = os.path.splitext(file.filename)
    # 获取当前时间戳
    timestamp = int(datetime.now().timestamp())
    
    # 构建新的文件名
    new_filename = f"{name}_{timestamp}{ext}"
    
    # 构建完整的保存路径，指定为 static/temp 目录
    save_path = os.path.join(os.path.abspath("static/temp"), new_filename)
    
    try:
        # 以二进制写入模式打开文件
        with open(save_path, "wb") as buffer:
            # 将上传的文件内容复制到新文件中
            shutil.copyfileobj(file.file, buffer)
        
        # 返回上传文件的绝对路径
        return {"success": True, "message": "文件上传成功", "path": save_path}
    except Exception as e:
        # 如果上传过程中发生异常，返回错误信息
        return {"success": False, "message": f"文件上传失败: {str(e)}"}
# 将 "static" 目录挂载到应用程序的根路径 "/"
# 当访问根路径时，FastAPI 会在 "static" 目录中查找文件
# html=True 表示如果请求的是一个目录，它会自动查找并返回该目录下的 index.html 文件
app.mount("/", StaticFiles(directory="static", html=True), name="static")

# 判断是否为主程序运行
if __name__ == "__main__":
    # 导入 uvicorn 库
    import uvicorn
    # 导入 webbrowser 库用于自动打开系统默认浏览器
    import webbrowser
    # 导入 threading 模块中的 Timer 类，用于实现延时操作
    from threading import Timer

    # 定义一个打开浏览器的内部函数
    def open_browser():
        # 调用 webbrowser.open 方法自动打开目标地址
        webbrowser.open("http://localhost:8200")

    # 创建一个定时器，在 1.5 秒后执行 open_browser 函数，以便让服务先启动
    Timer(1.5, open_browser).start()

    # 启动服务，监听所有IP，端口8200，开启热更新(reload=True)
    uvicorn.run("main_api:app", host="0.0.0.0", port=8200)
