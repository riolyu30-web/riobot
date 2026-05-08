import asyncio
from playwright.async_api import async_playwright
from nanobot.config.loader import get_config_path
import os
import click

_PATH = os.path.dirname(__file__)
# 定义保存登录状态的文件名
AUTH_FILE = get_config_path().parent / "auth_xhs.json"

async def _wait_for_scan_and_save(page, context, browser, playwright_manager, qr_image_path):
    """后台异步任务：持续等待用户扫码并保存状态"""
    try:
        # 监听特定的 API 接口调用，设置一个合理的超时时间（例如 120 秒）
        async with page.expect_response(
            lambda response: "api/sns/web/v2/user/me" in response.url and response.status == 200, 
            timeout=120000  # 120秒超时，超时后抛出异常并关闭浏览器
        ) as response_info:
            # 这里什么都不做，只需等待用户扫码触发接口
            pass
        
        print("扫码成功，等待状态保存...", flush=True)
        # 拿到响应后，额外等待一小段时间确保 Cookie 和 State 写入完成
        await page.wait_for_timeout(2000)

        await context.storage_state(path=AUTH_FILE)
        print(f"登录状态已保存到 {AUTH_FILE}，下次运行无需再次扫码！", flush=True)

    except Exception as e:
        print(f"未能找到二维码、截图失败或扫码超时: {e}", flush=True)
        debug_img_path = os.path.join(_PATH, "debug_fullpage.png")
        await page.screenshot(path=debug_img_path, full_page=True)
        print(f"已保存全屏截图用于排查，请查看: {debug_img_path}", flush=True)

    finally:
        if qr_image_path and os.path.exists(qr_image_path):
            os.remove(qr_image_path)
        # 无论成功失败，最后统一清理资源并断开连接
        await page.close()
        await context.close()
        await browser.disconnect()  # 改为断开连接，保留远程浏览器进程
        await playwright_manager.stop()


async def get_login_qrcode():
    """
    异步获取登录二维码的主方法。
    返回: (qr_image_path, background_task)
    主程序拿到 qr_image_path 后可以立刻往下走（比如把图片发给用户），
    background_task 会在后台异步等待用户扫码。
    """
    playwright_manager = await async_playwright().start()
    # 1. 连接到远程启动的浏览器 (请确保浏览器已带 --remote-debugging-port=9222 参数启动)
    CDP_URL = "http://localhost:9222"
    print(f"正在连接到远程浏览器: {CDP_URL}...", flush=True)
    browser = await playwright_manager.chromium.connect_over_cdp(CDP_URL)
    
    # 定义一个真实的 User-Agent
    USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    
    # 判断是否已经有保存的登录状态文件
    if os.path.exists(AUTH_FILE):
        print("找到已保存的登录状态，尝试直接使用...", flush=True)
        context = await browser.new_context(
            storage_state=AUTH_FILE,
            viewport={'width': 1920, 'height': 1080},
            user_agent=USER_AGENT
        )
    else:
        print("没有找到登录状态，需要重新登录...", flush=True)
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent=USER_AGENT
        )
        
    # 抹除 webdriver 特征
    await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
    page = await context.new_page()
    await page.goto("https://www.xiaohongshu.com/explore")
    
    qr_image_path = os.path.join(_PATH, "qrcode.png")

    try:
        print("等待登录二维码出现...", flush=True)
        qr_locator = page.locator('//div[@class="code-area"]')
        await qr_locator.wait_for(state="visible", timeout=15000)  # 等待最多 15 秒
        
        # 截图保存二维码区域
        await qr_locator.screenshot(path=qr_image_path)
        print(f"二维码已截图保存到: {qr_image_path}", flush=True)
        print("请在手机端扫码登录...", flush=True)
        
        # 创建后台异步任务，不阻塞当前函数的返回
        bg_task = asyncio.create_task(_wait_for_scan_and_save(page, context, browser, playwright_manager, qr_image_path))
        
        return qr_image_path, bg_task

    except Exception as e:
        debug_img_path = os.path.join(_PATH, "fullpage.png")
        await page.screenshot(path=debug_img_path, full_page=True)
        print(f"发生异常，请核对全屏截图: {debug_img_path}", flush=True)
        await page.close()
        await context.close()
        await browser.disconnect()  # 改为断开连接
        await playwright_manager.stop()
        return None, None


@click.command()
def login_and_save_state():
    """
    小红书自动化登录工具，获取二维码并保存登录状态。
    """
    async def run_cli():
        qr_path, bg_task = await get_login_qrcode()
        if bg_task:
            # 如果是作为 CLI 命令行工具直接运行，必须阻塞等待后台任务完成，
            # 否则 Python 进程一旦退出，浏览器就会被强制销毁。
            await bg_task
            
    asyncio.run(run_cli())


if __name__ == "__main__":
    login_and_save_state()