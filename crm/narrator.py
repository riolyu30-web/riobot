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
    # 初始化剩余等待时间，初始值为传入的总等待时间
    remaining_time = wait_time
    # 当剩余等待时间大于 0 时持续执行倒计时循环
    while remaining_time > 0:
        # 打印当前剩余的等待时间并提示打开微信
        print(f"倒计时 {remaining_time} 秒，请保持讲述人运行并打开微信...")
        # 计算本次需要休眠的时间，如果剩余时间大于等于 30 秒则休眠 30 秒，否则休眠剩余时间
        sleep_time = 30 if remaining_time >= 30 else remaining_time
        # 暂停执行计算出的休眠时间
        time.sleep(sleep_time)
        # 剩余时间减去本次已经休眠的时间
        remaining_time -= sleep_time
    # 2. 强制关闭讲述人
    print("正在关闭讲述人...")
    # os.system 会返回命令的退出状态码，如果为 0 说明成功
    result = os.system("taskkill /F /IM Narrator.exe")
    if result != 0:
        print("正在尝试使用管理员权限关闭...")
        ctypes.windll.shell32.ShellExecuteW(None, "runas", "taskkill.exe", "/F /IM Narrator.exe", None, 0)

# 运行测试
if __name__ == "__main__":
    # 实际使用时可以设置成 300 秒 (5分钟)
    trigger_narrator_mode() 