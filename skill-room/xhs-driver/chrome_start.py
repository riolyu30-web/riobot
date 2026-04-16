import subprocess
import os
import sys
import time

# ================= 跨平台虚拟显示器配置 =================
# Xvfb 和 PyVirtualDisplay 只能在 Linux(Ubuntu) 下运行
if sys.platform.startswith("linux"):
    from pyvirtualdisplay import Display
    print("检测到 Linux 环境，正在启动 Xvfb 虚拟显示器...")
    display = Display(visible=0, size=(1920, 1080))
    display.start()
else:
    print(f"当前系统为 {sys.platform}，将直接使用系统原生窗口启动浏览器。")
# =======================================================

# 指定一个独立的用户数据目录，避免和日常使用的浏览器实例冲突
user_data_dir = os.path.join(os.getcwd(), "chrome-data")
print(f"用户数据目录: {user_data_dir}")

# 自动查找 Chrome 或 Edge 的安装路径 (跨平台支持)
if sys.platform.startswith("linux"):
    possible_paths = [
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
        "/usr/bin/microsoft-edge",
    ]
else:
    possible_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe"),
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    ]

chrome_path = None
for path in possible_paths:
    if os.path.exists(path):
        chrome_path = path
        break

if not chrome_path:
    print("❌ 找不到 Chrome 或 Edge 浏览器，请检查你的安装路径是否在常规目录下！")
    sys.exit(1)

print(f"找到浏览器可执行文件: {chrome_path}")

# 定义一个真实的 User-Agent 绕过检测
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

try:
    # 使用 creationflags 防止 Python 退出时子进程也被强制关闭
    DETACHED_PROCESS = 0x00000008
    
    # 使用 Popen 启动独立的浏览器进程
    process = subprocess.Popen([
        # 浏览器的可执行文件路径
        chrome_path,
        # 开放 9222 端口用于后续 CDP 协议的远程控制
        "--remote-debugging-port=9222", 
        # 指定独立的用户数据目录，隔离本地书签和历史
        f"--user-data-dir={user_data_dir}",
        
        # ================== 核心反爬/模拟真实用户参数 ==================
        
        # 禁用自动化软件特有的 “Chrome 正受到自动测试软件的控制” 黄色信息栏
        "--disable-infobars",
        # 禁用 Blink 引擎中的自动化控制特性，这是抹除 WebDriver 痕迹的关键
        "--disable-blink-features=AutomationControlled", 
        # 注入真实的 User-Agent，避免暴露爬虫身份
        f"--user-agent={USER_AGENT}",
        # 强制设置一个常见的桌面屏幕分辨率，避免无头模式下的异常视口尺寸
        "--window-size=1920,1080",
        
        # 禁用首次运行时的各种引导弹窗和气泡提示
        "--no-first-run",
        # 禁用每次启动时询问是否设置为默认浏览器的弹窗
        "--no-default-browser-check",
        # 禁用自动翻译提示弹窗
        "--disable-features=TranslateUI",
        # 禁用扩展插件的开发者模式警告弹窗
        "--disable-extensions-file-access-check",
        # 禁用崩溃恢复提示弹窗（如果上次是非正常退出，不弹恢复框）
        "--hide-crash-restore-bubble",
        # 禁用同步设置弹窗
        "--disable-sync",
        
        # 提升在某些受限环境（如 Linux 容器）下的运行稳定性
        "--no-sandbox",
        # 禁用 `/dev/shm` 的使用，防止在内存较小的服务器上发生崩溃
        "--disable-dev-shm-usage",
        
    ], creationflags=DETACHED_PROCESS)

    # 等待 2 秒检查进程是否闪退
    time.sleep(2)
    if process.poll() is not None:
        print("\n❌ 浏览器启动失败并立刻退出，可能原因：")
        print("1. 端口 9222 被占用 (请检查是否有其他后台浏览器正在运行)。")
        print(f"2. 用户数据目录 {user_data_dir} 被其他 Chrome 进程锁定。")
        print("   -> 尝试打开任务管理器，强制结束所有 chrome.exe 进程后重试。")
    else:
        print(f"\n✅ 浏览器已成功启动，正在监听 9222 端口，PID: {process.pid}")
        print("你可以继续运行 login.py 来控制该浏览器。")

except Exception as e:
    print(f"\n❌ 启动浏览器时发生异常: {e}")
