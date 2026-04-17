import os
import time
import subprocess

def trigger_narrator_mode(wait_time=300):
    """
    开启讲述人模式以暴露微信UI结构
    在 Windows 系统中，开启或关闭讲述人（Narrator）的快捷键是同一个：
    Win + Ctrl + Enter (也就是：Windows徽标键 + Ctrl键 + 回车键)
    """
    import ctypes
    # 1. 打开讲述人
    print("正在启动 Windows 讲述人...")
    try:
        # 尝试普通方式启动
        subprocess.Popen(["narrator.exe"])
    except OSError as e:
        if e.winerror == 740:
            print("需要管理员权限，正在请求提升权限启动讲述人...")
            # 使用 ShellExecuteW 请求管理员权限启动
            ctypes.windll.shell32.ShellExecuteW(None, "runas", "narrator.exe", "", None, 1)
        else:
            raise

    # 根据项目 Weixin4.0.md 中的说明，讲述人需要在微信登录前运行，并保持一段时间
    # 打印等待一分钟的提示信息
    print("等待 60 秒 (1分钟)，打开微信...")

    time.sleep(wait_time)
    # 2. 强制关闭讲述人
    print("正在关闭讲述人...")
    # os.system 会返回命令的退出状态码，如果为 0 说明成功
    result = os.system("taskkill /F /IM Narrator.exe")
    if result != 0:
        print("普通权限关闭失败，正在尝试使用管理员权限关闭...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "taskkill.exe", "/F /IM Narrator.exe", None, 0)

# 运行测试
if __name__ == "__main__":
    # 实际使用时可以设置成 300 秒 (5分钟)
    trigger_narrator_mode() 