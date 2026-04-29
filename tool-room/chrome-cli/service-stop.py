# 导入 asyncio 库，用于运行异步函数
import asyncio
# 从 playwright 导入异步 API 模块
from playwright.async_api import async_playwright

# 定义异步关闭远程浏览器的主函数
async def stop_remote_browser():
    # 定义 CDP 连接的 URL
    CDP_URL = "http://localhost:9222"
    # 打印提示信息
    print(f"尝试连接并关闭无头浏览器 ({CDP_URL})...")
    
    # 开启 try 块捕获异常
    try:
        # 启动 playwright 异步上下文
        async with async_playwright() as p:
            # 通过 CDP 连接到已经在运行的 Chrome 浏览器
            browser = await p.chromium.connect_over_cdp(CDP_URL)
            
            # 使用 context7 相关的底层协议：获取浏览器级别的 CDP 会话 (Browser CDP Session)
            session = await browser.new_browser_cdp_session()
            
            # 发送原生的 Browser.close 指令，优雅且彻底地终止浏览器后台进程
            await session.send("Browser.close")
            
            # 打印成功关闭的提示
            print("✅ 浏览器进程已成功关闭！")
            
    # 捕获可能的异常情况
    except Exception as e:
        # 打印错误详细信息
        print(f"❌ 无法连接到浏览器或浏览器已经关闭。\n详细信息: {e}")

# 判断是否作为主程序运行
if __name__ == "__main__":
    # 使用 asyncio 运行主异步函数
    asyncio.run(stop_remote_browser())
