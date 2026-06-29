"""Echo bot example — receives messages and replies with 'Echo: <text>'."""

# 引入 asyncio 库用于异步编程
import asyncio
# 引入 os 库用于文件路径操作和创建目录
import os
# 引入 pathlib 中的 Path 用于路径操作
from pathlib import Path
# 引入 time 库用于生成时间戳
import time
# 引入 re 库用于正则表达式匹配
import re
# 引入 webbrowser 库用于打开系统默认浏览器
import webbrowser
# 从 wechatbot 模块引入 WeChatBot 类
from wechatbot import WeChatBot

# 定义媒体文件保存的目录名称
MEDIA_DIR = "static\\media"
# 确保目录存在，如果不存在则自动创建
os.makedirs(MEDIA_DIR, exist_ok=True)
CRED_PATH = Path(__file__).parent / "config" / "rio.json"
# 定义异步的 main 函数作为程序入口
async def main():
    # 定义处理二维码链接的回调函数
    def handle_qr(url):
        # 打印二维码链接到控制台
        print(f"\nScan this URL in WeChat:\n{url}\n")
        # 弹出系统默认浏览器并打开该链接
        webbrowser.open(url)

    # 实例化 WeChatBot 对象
    bot = WeChatBot(
        # 设置当需要扫描二维码登录时的回调函数，使用 handle_qr 处理
        on_qr_url=handle_qr,
        # 设置发生错误时的回调函数，打印错误信息
        on_error=lambda err: print(f"Error: {err}"),
        cred_path=CRED_PATH, # 传递自定义凭据文件路径
    )

    # 尝试登录并获取登录凭证
    creds = await bot.login()
    # 打印登录成功的账户信息
    print(f"Logged in: {creds.account_id} ({creds.user_id})")

    # 初始化处理消息的计数器
    count = 0
    
    # 定义一个字典，用于暂存用户的媒体消息，键为 user_id，值为消息列表
    pending_media = {}

    # 注册消息处理装饰器
    @bot.on_message
    # 定义处理接收到的消息的异步函数
    async def handle(msg):
        # 声明使用外层函数的 count 变量
        nonlocal count
        # 消息计数器加 1
        count += 1
        
        # 判断消息中是否包含图片或视频
        if msg.images or msg.videos:
            # 获取发送者的用户 ID
            user_id = msg.user_id
            # 如果该用户还没有暂存列表，则初始化一个空列表
            if user_id not in pending_media:
                # 为该用户创建一个空列表用于暂存媒体消息
                pending_media[user_id] = []
            # 将当前的媒体消息追加到用户的暂存列表中
            pending_media[user_id].append(msg)
            
            # 在控制台打印暂存媒体信息
            print(f"[{count}] {user_id}: Queued media message")
                        
        # 如果不是图片或视频消息
        else:
            # 获取用户的文本内容并去除首尾空白字符
            text = (msg.text or "").strip()
            # 获取发送者的用户 ID
            user_id = msg.user_id
            
            # 判断文本内容是否以英文字母或数字开头，并且该用户有暂存的媒体消息
            if text and re.match(r"^[a-zA-Z0-9]", text) and pending_media.get(user_id):
                # 将该有效文本作为文件夹名称和文件名前缀
                prefix = text
                # 拼接新的子目录路径
                target_dir = os.path.join(MEDIA_DIR, prefix)
                # 确保该子目录存在，如果不存在则自动创建
                os.makedirs(target_dir, exist_ok=True)
                
                # 获取用户暂存的媒体消息列表
                media_msgs = pending_media[user_id]
                # 记录成功下载的文件数量
                success_count = 0
                
                # 向用户发送正在输入的提示状态
                await bot.send_typing(user_id)
                
                # 遍历暂存的所有媒体消息
                for media_msg in media_msgs:
                    # 尝试下载图片或视频媒体数据
                    downloaded = await bot.download(media_msg)
                    # 如果成功下载到媒体数据
                    if downloaded:
                        # 根据文件类型决定后缀名，图片用 .jpg，视频用 .mp4
                        ext = ".jpg" if downloaded.type == "image" else ".mp4"
                        # 使用前缀、当前时间戳(精确到毫秒)和成功计数组合作为新文件名
                        filename = f"{int(time.time() * 1000)}_{success_count}{ext}"
                        # 拼接完整的本地文件保存路径，将其放入新创建的子目录中
                        file_path = os.path.join(target_dir, filename)
                        
                        # 以二进制写模式打开文件
                        with open(file_path, "wb") as f:
                            # 将下载的字节数据写入文件
                            f.write(downloaded.data)
                        
                        # 在控制台打印已接收到媒体文件及保存路径
                        print(f"[{count}] {user_id}: Saved {downloaded.type} -> {file_path}")
                        # 成功下载数量加 1
                        success_count += 1
                        # 为防止文件名重复，稍微暂停一下改变时间戳
                        await asyncio.sleep(0.01)
                    # 如果下载失败（未获取到下载数据）
                    else:
                        # 在控制台打印下载失败的信息
                        print(f"[{count}] {user_id}: Failed to download queued media")
                        
                # 清空该用户的暂存列表
                pending_media[user_id] = []
                # 回复用户下载完成的信息
                await bot.reply(msg, f"下载完成，共保存了 {success_count} 个文件。")
                
            # 如果不满足下载条件，则作为普通的 echo 回复
            else:
                # 打印接收到的普通文本消息
                print(f"[{count}] {msg.user_id}: {msg.text}")
                # 向用户发送正在输入的提示状态
                await bot.send_typing(msg.user_id)
                # 模拟处理延迟，暂停 0.5 秒
                await asyncio.sleep(0.5)
                # 回复用户收到文本消息的 echo 结果
                await bot.reply(msg, f"Echo: {msg.text}")

    # 打印提示信息，说明开始监听消息
    print("Listening for messages (Ctrl+C to stop)")
    # 使用 try-except 块捕获中断信号
    try:
        # 启动机器人并保持运行状态
        await bot.start()
    # 当用户按下 Ctrl+C 触发 KeyboardInterrupt 时
    except KeyboardInterrupt:
        # 停止机器人的运行
        bot.stop()
    # 打印程序结束及处理的总消息数量
    print(f"Stopped. Processed {count} messages.")

# 如果当前脚本是直接执行而不是被引入的
if __name__ == "__main__":
    # 使用 asyncio.run 运行主函数
    asyncio.run(main())
