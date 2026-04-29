import click as CLICK
# 导入 CLICK 库用于构建命令行界面
import html2text
# 导入 html2text 库用于将 HTML 转换为纯文本
import json
# 导入 json 库用于将数据序列化为 JSON 字符串
from playwright.sync_api import sync_playwright
# 从 playwright 库导入同步 API
from bs4 import BeautifulSoup
# 导入 BeautifulSoup 用于解析 HTML
from minify_html import minify
# 导入 minify_html 用于压缩 HTML
import sys
# 导入 sys 模块用于系统相关操作
import re
# 导入 re 模块用于正则表达式
from typing import List
# 导入 List 类型提示
from urllib.parse import urljoin
# 导入 urljoin 用于处理 URL
import os
# 导入 os 模块用于环境变量和文件路径操作
from datetime import datetime
# 导入 datetime 模块用于生成时间戳文件名

# 定义全局静态变量
DEFAULT_CDP_ENDPOINT = f"http://127.0.0.1:9222"
# 默认的 Chrome 远程调试端口
DEFAULT_TIMEOUT = 30000

TOUTIAO_URL = "https://tophub.today/n/x9ozB4KoXb"
# 获取当前脚本所在目录
LAST_RECORD_FILE =  os.path.join(os.path.dirname(os.path.abspath(__file__)), "last_record.json")
@CLICK.group()
# 定义 CLICK 命令行组
def cli():
# 定义主入口函数
    """Chrome 命令行工具。"""
    # 组文档字符串
    pass
    # 占位符
# 默认的页面加载/操作超时时间（毫秒）
@cli.command(context_settings=dict(ignore_unknown_options=True))
# 定义 open 子命令，忽略未知的命令行选项
# 添加 --rank 参数（支持 -r 别名）
@CLICK.option('--rank', '-r', type=int, help='只选增量排名最高的前n个')
def toutiao(rank, **kwargs):
# 定义 toutiao 命令的执行逻辑，使用 **kwargs 接收被忽略的额外参数

    # 命令文档字符串
    os.environ['NODE_NO_WARNINGS'] = '1'
    # 隐藏 Node.js 的 DeprecationWarning

    try:
    # 开始错误捕获
        with sync_playwright() as p:
        # 启动 playwright 同步环境
            # 构建 CDP 连接端点 URL
            browser = p.chromium.connect_over_cdp(DEFAULT_CDP_ENDPOINT)
            # 通过 CDP 连接到现有的 Chromium 浏览器

            if not browser:
            # 如果连接失败
                CLICK.echo("无法连接到浏览器。请确保浏览器已通过 chrome-start.py 启动。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序
            page = None
            # 初始化页面变量
            for context_item in browser.contexts:
            # 遍历浏览器所有上下文
                for p_page in context_item.pages:
                # 遍历上下文中的所有页面
                    parsed_current_url = urljoin(p_page.url, '/')
                    # 解析当前页面 URL
                    parsed_target_url = urljoin(TOUTIAO_URL, '/')
                    # 解析目标 URL
                    if parsed_current_url == parsed_target_url:
                    # 如果 URL 匹配（忽略 hash）
                        page = p_page
                        # 选中该页面
                        break
                        # 跳出内层循环
                if page:
                # 如果找到匹配页面
                    break
                    # 跳出外层循环

            if page:
            # 如果找到了已存在的页面
                #CLICK.echo(f"找到已存在的页面: {page.url}，正在切换并重新加载...")
                # 打印提示信息
                page.bring_to_front()
                # 将页面切换到最前端
                page.reload(timeout=DEFAULT_TIMEOUT)
                # 重新加载页面
            else:
            # 如果没有找到匹配页面
                #CLICK.echo("未找到匹配页面，正在创建新页面...")
                # 打印提示信息
                context = browser.contexts[0] if browser.contexts else browser.new_context()
                # 获取第一个上下文或创建一个新上下文
                page = context.new_page()
                # 在上下文中创建新页面
                #CLICK.echo(f"正在访问 URL: {url}")
                # 打印访问信息
                page.goto(TOUTIAO_URL, timeout=DEFAULT_TIMEOUT)
                # 导航到目标 URL
            
            # 等待 tbody 元素加载完成
            page.wait_for_selector("tbody", timeout=DEFAULT_TIMEOUT)
            # 获取页面的 HTML 内容
            html_content = page.content()
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html_content, "html.parser")
            # 找到 tbody 元素
            tbody = soup.find("tbody")
            # 判断是否找到 tbody
            if tbody:
                # 初始化 last_record 为空列表
                last_record = []

                # 判断文件是否存在
                if os.path.exists(LAST_RECORD_FILE):
                    # 如果存在，则打开文件
                    with open(LAST_RECORD_FILE, "r", encoding="utf-8") as f:
                        # 读取文件内容并解析为 JSON 对象赋值给 last_record
                        last_record = json.load(f)
                
                # 找到 tbody 中所有 align 属性为 "right" 的 td 节点
                tds = tbody.find_all("td", align="right")
                # 遍历所有找到的 td 节点，将其移除
                for td in tds:
                    td.decompose() # 移除该 td 元素
                
                # 初始化一个空列表，用于存储提取的数据
                data_list = []
                # 找到 tbody 中所有的 tr 元素（每一行数据）
                trs = tbody.find_all("tr")
                # 遍历每一行
                for tr in trs:
                    # 尝试找到当前行中包含链接的 a 标签（通常是标题）
                    a_tag = tr.find("a")
                    # 尝试找到当前行中所有的 td 标签
                    td_tags = tr.find_all("td")
                    # 确保找到了 a 标签且至少有两个 td 标签（热度数据通常在中间的 td）
                    if a_tag and len(td_tags) >= 2:
                        # 提取链接文本作为 keyword
                        keyword = a_tag.get_text(strip=True)
                        # 提取 href 属性作为 link，如果存在的话需要补全
                        #link = urljoin(TOUTIAO_URL, a_tag.get("href", "")) if a_tag.get("href") else ""
                        # 提取第二个 td 的文本作为 ws（热度值）
                        ws = td_tags[2].get_text(strip=True)
                        # 将提取的数据组装成字典并添加到列表中
                        data_list.append({
                            "搜索词": keyword,
                            "热度": ws
                        })
                # 将提取的数据列表转换为格式化的 JSON 字符串，确保中文不被转义
                json_content = json.dumps(data_list, ensure_ascii=False, indent=2)                        
                # 将 JSON 内容写入文件
                with open(LAST_RECORD_FILE, "w", encoding="utf-8") as f:
                    f.write(json_content)                                          
                # 定义一个辅助函数，用于将热度字符串（如 "1089.2万"）转换为数值
                def parse_ws(ws_str):
                    # 提取字符串中的数字部分并转换为浮点数
                    try:
                        return float(re.sub(r'[^\d.]', '', ws_str))
                    # 如果转换失败则返回 0
                    except ValueError:
                        return 0.0

                # 将 last_record 转换为以 keyword 为键的字典，方便快速查找
                last_record_dict = {item.get("搜索词"): item for item in last_record if item.get("搜索词")}

                # 遍历新提取的数据列表，计算并添加增量
                for item in data_list:
                    # 获取当前数据的 keyword
                    keyword = item["搜索词"]
                    # 获取当前数据的热度数值
                    current_ws_val = parse_ws(item["热度"])
                    # 如果该 keyword 在历史记录中存在
                    if keyword in last_record_dict:
                        # 获取历史热度数值
                        last_ws_val = parse_ws(last_record_dict[keyword].get("热度", "0"))
                        # 计算增量数值（当前热度 - 历史热度）
                        diff_val = current_ws_val - last_ws_val
                        # 将增量格式化为字符串，带正负号和"万"单位
                        item["增量"] = f"{diff_val:+.1f}万"
                        # 内部存储用于排序的纯数字增量
                        item["_diff_num"] = diff_val
                    # 如果不存在历史记录
                    else:
                        # 将增量标记为 "新上榜"
                        item["增量"] = "新上榜"
                        # 新上榜的增量等于当前热度
                        item["_diff_num"] = current_ws_val
                
                # 如果传入了 rank 参数，则根据增量进行降序排序并截取前 n 个
                if rank is not None and rank > 0:
                    data_list.sort(key=lambda x: x["_diff_num"], reverse=True)
                    data_list = data_list[:rank]
                
                # 清理内部使用的 _diff_num 字段
                for item in data_list:
                    if "_diff_num" in item:
                        del item["_diff_num"]

                # 将提取的数据列表转换为格式化的 JSON 字符串，确保中文不被转义
                json_content = json.dumps(data_list, ensure_ascii=False, indent=2)
                

                # 打印 JSON 字符串
                CLICK.echo(json_content)
                
            # 否则
            else:
                # 打印未找到的提示
                CLICK.echo("未找到 tbody 元素")

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出

@cli.command(context_settings=dict(ignore_unknown_options=True))
# 定义 search 子命令，忽略未知的命令行选项
@CLICK.option('--keyword', '-k', required=True, help='搜索词')
# 添加 --keyword 参数（支持 -k 别名），该参数是必须的
def search(keyword, **kwargs):
# 定义 search 命令的执行逻辑，接收 keyword 参数和额外参数
    # 命令文档字符串
    os.environ['NODE_NO_WARNINGS'] = '1'
    # 隐藏 Node.js 的 DeprecationWarning

    try:
    # 开始错误捕获
        with sync_playwright() as p:
        # 启动 playwright 同步环境
            # 构建 CDP 连接端点 URL
            browser = p.chromium.connect_over_cdp(DEFAULT_CDP_ENDPOINT)
            # 通过 CDP 连接到现有的 Chromium 浏览器

            if not browser:
            # 如果连接失败
                CLICK.echo("无法连接到浏览器。请确保浏览器已通过 chrome-start.py 启动。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序
            
            # 构建搜索 URL，使用 urllib.parse.quote 对关键词进行 URL 编码
            import urllib.parse
            # 导入 urllib.parse 模块用于 URL 编码
            search_url = f"https://so.toutiao.com/search?keyword={urllib.parse.quote(keyword)}"
            # 拼接并编码生成完整的搜索 URL
            
            # 直接创建一个新页面
            context = browser.contexts[0] if browser.contexts else browser.new_context()
            # 获取第一个上下文或创建一个新上下文
            page = context.new_page()
            # 在上下文中创建新页面
            
            # 导航到目标 URL，将 wait_until 设置为 domcontentloaded，避免某些追踪脚本或缺失结果导致 load 事件超时
            page.goto(search_url, timeout=DEFAULT_TIMEOUT, wait_until="domcontentloaded")
            
            # 额外等待一下，确保最后的渲染完成
            page.wait_for_timeout(5000)
            
            # 使用物理按键 (PageDown) 模拟页面往下翻 5 屏
            for _ in range(10):
                page.keyboard.press("PageDown")
                # 每次翻页后稍微等待一下，让内容加载
                page.wait_for_timeout(1000)
            
            # 额外等待一下，确保最后的渲染完成
            page.wait_for_timeout(5000)
            
            
            # 获取页面的 HTML 内容
            html_content = page.content()
            # 使用 BeautifulSoup 解析 HTML
            soup = BeautifulSoup(html_content, "html.parser")
            
            # 初始化一个字典，用于汇总三部分的数据
            result_data = {
                "头条新闻": [],
                "相关新闻": [],
                "热门点评": [],
                "相关搜索词": []
            }
            
            # 找到页面上所有满足条件的容器 div
            containers = soup.find_all("div", attrs={"data-hotadmin-container-id": "base-feed-list-container"})
            
            # 处理第一个容器
            if len(containers) > 0:
                first_container = containers[0]
                # 1、找第一个 div 下的所有元素的 text，并去除空白
                first_texts = [text.strip() for text in first_container.stripped_strings]
                # 赋值给结果字典
                result_data["头条新闻"] = first_texts
            
            # 处理第二个容器
            if len(containers) > 1:
                second_container = containers[1]
                # 找到第二个容器下的每个直接子 div（代表每一条数据卡片）
                item_divs = second_container.find_all("div", recursive=False)
                # 遍历每个数据卡片
                for item_div in item_divs:
                    # 获取该卡片下所有纯文本，并去除空白
                    item_data = [text.strip() for text in item_div.stripped_strings if text.strip()]
                    # 将该卡片的数据组加入 part2
                    if item_data:
                        result_data["相关新闻"].append(item_data)
            
            # 处理第三个容器
            if len(containers) > 2:
                third_container = containers[2]
                # 找到第三个容器下的每个直接子 div
                item_divs = third_container.find_all("div", recursive=False)
                # 遍历每个数据卡片
                for item_div in item_divs:
                    # 获取该卡片下所有纯文本，并去除空白
                    item_data = [text.strip() for text in item_div.stripped_strings if text.strip()]
                    # 将该卡片的数据组加入 part3
                    if item_data:
                        result_data["热门点评"].append(item_data)
            

            # 4、找//div[@class="l-view block l-button-group mt-12 flex flex-wrap -mx-4"] 下的所有元素的 text，并去除空白
            related_search_divs = soup.find_all("div", class_="l-view block l-button-group mt-12 flex flex-wrap -mx-4")
            if related_search_divs:
                item_texts = []
                for div in related_search_divs:
                    item_texts.extend([text.strip() for text in div.stripped_strings if text.strip()])
                # 去重并保持原有顺序
                seen = set()
                unique_texts = [x for x in item_texts if not (x in seen or seen.add(x))]
                # 赋值给结果字典
                result_data["相关搜索词"] = unique_texts
            else:
                result_data["相关搜索词"] = []

            # 5、汇总并转换为格式化的 JSON 字符串
            if containers:
                json_result = json.dumps(result_data, ensure_ascii=False, indent=2)
                # 打印最终的 JSON 字符串
                CLICK.echo(json_result)
            else:
                # 6、找全部 class="result-content" 的 div，提取每个 div 下所有纯文本并去除空白
                result_contents = soup.find_all("div", class_="result-content")
                if result_contents:
                    item_texts = []
                    for div in result_contents:
                        div_texts = [text.strip() for text in div.stripped_strings if text.strip()]
                        # 去掉数组中的最后一个元素（通常是“分享”、“评论”之类的无用按钮文本）
                        if len(div_texts) > 0:
                            div_texts = div_texts[:-1]
                        if div_texts:
                            item_texts.append(div_texts)
                    # 赋值给结果字典
                    result_data["头条新闻"] = item_texts
                    # 打印最终的 JSON 字符串
                    json_result = json.dumps(result_data, ensure_ascii=False, indent=2)
                    CLICK.echo(json_result)
                else:
                    # 打印未找到容器的提示
                    CLICK.echo("未找到任何新闻")
            # 关闭浏览器页面
            page.close()

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出
        



if __name__ == '__main__':
    # 假设你的组名叫 cli
    cli() 