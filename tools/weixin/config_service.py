"""微信机器人配置服务
1、用户需要先扫描二维码创建登录凭证。
2、用户需要在登录后，发送任意消息，触发欢迎消息的发送。
3、用户需要在收到欢迎消息后，发送四个英文字母，作为机器人的正式名称。
4、机器人名称将被正式保存，服务会终止运行。
"""

import asyncio
from pathlib import Path # 导入 Path 类
from datetime import datetime # 导入 datetime 模块
import os # 导入 os 模块
import argparse # 导入 argparse 模块
from wechatbot import WeChatBot # 重新添加 WeChatBot 导入
# 引入 webbrowser 库用于打开系统默认浏览器
import webbrowser

CRED_PATH = Path(__file__).parent / "config" 




async def main(robot_name: str = None):

        # 定义处理二维码链接的回调函数
    def handle_qr(url):
        # 打印二维码链接到控制台
        print(f"\nScan this URL in WeChat:\n{url}\n")
        # 弹出系统默认浏览器并打开该链接
        webbrowser.open(url)
# 生成带时间戳的文件名
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    cred_path = CRED_PATH / f"{timestamp}.json"
    bot = WeChatBot(
        on_qr_url=handle_qr,
        on_error=lambda err: print(f"Error: {err}"),
        cred_path=cred_path, # 传递自定义凭据文件路径
    )

    creds = await bot.login() # 传递自定义凭据文件路径
    print(f"Logged in: {creds.account_id} ({creds.user_id})")

    welcome_message_sent = False # 添加标志，用于跟踪欢迎消息是否已发送


    @bot.on_message
    async def handle(msg):
        nonlocal welcome_message_sent # 声明 welcome_message_sent 为 nonlocal
        print(f"[{msg.user_id}: {msg.text}")
        await bot.send_typing(msg.user_id)
        if not welcome_message_sent: # 如果欢迎消息尚未发送
            welcome_message_sent = True # 设置标志为 True，确保只发送一次
            # 登录成功后，尝试自动关闭扫码的浏览器页面
            try:
                import pyautogui
                pyautogui.hotkey('ctrl', 'w') # 模拟按下 Ctrl+W 关闭当前浏览器标签页
                print("尝试关闭浏览器页面成功")
            except Exception as e:
                print(f"关闭浏览器页面失败: {e}")

            if robot_name: # 如果命令行提供了机器人名称
                old_cred_path = cred_path # 获取当前凭据文件路径
                new_cred_path = CRED_PATH /  f"{robot_name}.json"  # 新的凭据文件完整路径

                if old_cred_path.exists(): # 如果旧凭据文件存在
                    os.replace(old_cred_path, new_cred_path) # 重命名凭据文件，如果存在则覆盖
                    await bot.reply(msg, f"成功链接，机器人正式命名为: {robot_name}")                    
                    print(f"成功链接，机器人名为: {robot_name}")
                else:
                    os.remove(cred_path) # 删除旧的凭据文件
                    await bot.reply(msg, f"链接失败，请重新尝试") # 打印文件未找到信息
                bot.stop() # 停止机器人服务
       
    print("Listening for messages (Ctrl+C to stop)")
    try:
        await bot.start()
    except KeyboardInterrupt:
        bot.stop()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="微信机器人配置服务") # 创建 ArgumentParser 对象
    parser.add_argument("robot_name", nargs="?", help="机器人的名称") # 添加 robot_name 参数
    args = parser.parse_args() # 解析命令行参数

    if args.robot_name is None: # 如果没有在命令行提供 robot_name
        args.robot_name = input("请输入机器人的名称: ") # 提示用户输入机器人名称

    asyncio.run(main(robot_name=args.robot_name)) # 将解析或输入到的 robot_name 传递给 main 函数
