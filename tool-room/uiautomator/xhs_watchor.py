import uiautomator2 as u2
import time

# 1. 连接手机
# 如果你只连了一台手机，直接留空即可；也可以填入设备序列号或 WiFi IP
d = u2.connect() 
print("设备信息：", d.info)

# 2. 启动 App
# 假设我们要打开系统“设置”。不同手机设置的包名可能不同，一般是 com.android.settings
# 你可以通过 uiautodev 网页看到包名
app_package = "com.xingin.xhs"
print(f"正在启动 App: {app_package}")
d.app_start(app_package)

# 等待 App 启动加载（稍微等 2 秒）
time.sleep(2)

# 3. 查找元素并点击
# 方法 A：通过文字点击（最直观）
# 找屏幕上包含“发现”或者“搜索”字样的按钮点击
if d(textContains="发现").exists:
    print("找到了包含'发现'的按钮，点击它！")
    d(textContains="发现").click()
else:
    print("没找到目标按钮，可能是因为需要向下滑动？")

# 4. 其他常用操作演示
# 滑动屏幕：从下往上滑（通常用于看下面的内容）
d.swipe_ext("up") 

# 按返回键
d.press("back")

# 按 Home 键回桌面
d.press("home")

print("脚本执行完毕！")