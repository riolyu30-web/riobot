import asyncio
from playwright.sync_api import sync_playwright
import os
import json

# 设置环境变量，禁止 Playwright 底层的 Node.js 打印任何弃用警告（DeprecationWarning）
os.environ["NODE_NO_WARNINGS"] = "1"

_PATH = os.path.dirname(__file__)
AUTH_FILE = os.path.join(_PATH, "auth_xhs.json")

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

def get_search_suggestions(page, keyword):
    """
    输入关键词并获取搜索建议的辅助函数
    """
    # 键入 Control+A 选中输入框内的所有文本
    page.keyboard.press("Control+A")
    # 键入 Delete 删除选中的文本，清空输入框
    page.keyboard.press("Delete")
    
    # 逐个字符输入搜索词，模拟物理敲击，停顿 100 毫秒
    page.keyboard.type(keyword, delay=100)
    
    # 监听推荐接口的返回
    with page.expect_response(
        lambda response: "https://edith.xiaohongshu.com/api/sns/web/v1/search/recommend" in response.url and response.status == 200, 
        timeout=4000  # 4秒超时
    ) as response_info:
        # 解析返回的 JSON
        json_data = response_info.value.json()
        # 提取 sug_items 列表
        sug_items = json_data.get("data", {}).get("sug_items", [])
        # 提取并返回所有的 text
        return [item.get("text") for item in sug_items if "text" in item]

def connect_and_control(initial_keyword):
    with sync_playwright() as p:
        # 连接到刚刚开启的调试端口 (如果是另一台机器，把 localhost 换成对应 IP)
        browser =  p.chromium.connect_over_cdp("http://localhost:9222")
        
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

        # 使用 XPath 定位到 placeholder 为“搜索小红书”的输入框
        search_input = page.locator('//input[@placeholder="搜索小红书"]').first
        # 强制点击定位到的输入框元素，忽略可能存在的遮挡层以激活输入状态
        search_input.click(force=True)

        try:
            # 1. 获取初始关键词的搜索建议
            initial_texts = get_search_suggestions(page, initial_keyword)
            
            # 用于保存所有关联搜索建议的结果字典
            results = {}
            
            # 2. 遍历初始搜索建议，进行二次深度搜索
            for text in initial_texts:
                # 获取该词的联想搜索建议
                sub_texts = get_search_suggestions(page, text)
                # 存入结果字典
                results[text] = sub_texts
                
            # 打印最终提取的所有层级搜索建议
            if results:
                print("提取的深度搜索建议:", json.dumps(results, ensure_ascii=False, indent=2))

        # 捕获因超时未找到接口等原因抛出的异常
        except Exception as e:
            # 打印详细的错误信息，方便排查是哪个接口没有等到底
            print(f"网络错误或等待超时: {e}")

        finally:
            browser.close()  # 改为断开连接，保留远程浏览器进程


       
import click # 引入 click 库用于构建命令行接口

@click.command() # 将该函数装饰为 click 命令行命令
@click.option('--keyword', '-k', required=True, help='需要查询的小红书关键词') # 定义 keyword 参数，设定为必填项并提供帮助说明
def cli(keyword): # 定义命令行入口函数，接收 keyword 参数
    """小红书热搜关键词查询工具""" # 函数的文档字符串，作为命令行的默认帮助描述
    connect_and_control(keyword) # 调用核心逻辑函数，传入用户指定的关键词

if __name__ == "__main__": # 判断是否为主程序运行
    cli() # 执行命令行入口函数
