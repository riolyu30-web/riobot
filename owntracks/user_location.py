# 导入 requests 库，用于发起 HTTP 请求
import requests
# 导入 click 库，用于创建命令行界面工具
import click

# 注册一个 click 命令行命令
@click.command()
# 定义命令行选项 --url，并设置默认值为原来的服务器地址
@click.option('--url', default="http://localhost:8200/api/current_location", help="服务器的 API 地址")
# 定义获取 iPhone 位置的函数，接收 url 参数
def get_iphone_location(url):
    # 开始 try 块，用于捕获网络请求中可能出现的异常
    try:
        # 向指定的 url 发起 GET 请求
        response = requests.get(url)
        # 将响应的 JSON 字符串解析为 Python 字典
        data = response.json()
        
        # 判断解析出的数据中是否包含 "error" 键
        if "error" in data:
            # 若有错误，向终端输出提示信息
            click.echo(data)
        # 如果数据正常，则走 else 分支
        else:
            # 向终端输出标题栏
            click.echo("=== iPhone 最新位置 ===")
            # 格式化并输出更新时间
            click.echo(f"更新时间: {data['time']}")
            # 格式化并输出经度信息
            click.echo(f"经度: {data['lon']}")
            # 格式化并输出纬度信息
            click.echo(f"纬度: {data['lat']}")
            # 格式化并输出电量信息
            click.echo(f"电量: {data['battery']}")
            
    # 捕获所有常规异常并将其存为变量 e
    except Exception as e:
        # 向终端输出请求失败的提示以及具体的错误信息
        click.echo(f"请求失败，请检查网络或服务器: {e}")

# 检查该脚本是否被直接运行（而非被导入）
if __name__ == "__main__":
    # 触发 click 的命令解析逻辑并运行函数
    get_iphone_location()
