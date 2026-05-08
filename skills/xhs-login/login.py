import asyncio
from playwright.sync_api import sync_playwright
import os

_PATH = os.path.dirname(__file__)
AUTH_FILE = os.path.join(_PATH, "auth_xhs.json")
# 设置环境变量，禁止 Playwright 底层的 Node.js 打印任何弃用警告（DeprecationWarning）
os.environ["NODE_NO_WARNINGS"] = "1"
# 定义一段用于注入页面的 JavaScript 脚本，主要用于反爬和欺骗页面可见性
STEALTH_SCRIPT = """
    // 隐藏 webdriver 标记，防止被检测为自动化控制
    Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
    // 伪装正常 Chrome 的运行时特征
    window.chrome = { runtime: {} };
    // 伪装正常的插件列表，避免插件为空暴露无头特征
    Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3] });
    // 伪装正常的系统语言设置
    Object.defineProperty(navigator, 'languages', { get: () => ['zh-CN', 'zh', 'en'] });
    
    // 欺骗页面可见性 API：让页面永远认为自己处于激活和可见状态，防止后台节流导致二维码不渲染
    Object.defineProperty(document, 'hidden', { value: false });
    Object.defineProperty(document, 'visibilityState', { value: 'visible' });
    // 拦截并阻止页面上的 visibilitychange 事件向上传递
    document.addEventListener('visibilitychange', e => e.stopImmediatePropagation(), true);
"""

def connect_and_control():
    with sync_playwright() as p:

        # 连接到刚刚开启的调试端口 (如果是另一台机器，把 localhost 换成对应 IP)
        browser = p.chromium.connect_over_cdp("http://localhost:9222")
        
        # 获取现有的上下文（连接 CDP 时，默认会有一个 default context）
        context = browser.contexts[0]
        
        # 在上下文的每一个新页面加载前注入我们的隐身和保活脚本
        context.add_init_script(STEALTH_SCRIPT)
        
        # 获取当前打开的第一个标签页，或者新建一个标签页
        if context.pages:
            page = context.pages[0]
        else:
            page = context.new_page()
        # 开始你的远程控制逻辑
        page.goto("https://www.xiaohongshu.com/explore")
        qr_image_path = os.path.join(_PATH, "qrcode.png")        
        try:
            qr_locator = page.locator('//div[@class="code-area"]')
            qr_locator.wait_for(state="visible", timeout=3000)
            # 仅截取当前可视区域（第一屏），取消 full_page 参数
            qr_locator.screenshot(path=qr_image_path)
            print(f'登陆请扫码{qr_image_path}')
        except:
            #page.screenshot(path=qr_image_path)
            print(f"已成功登陆")
       
if __name__ == "__main__":
   connect_and_control()
