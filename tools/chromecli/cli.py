import click as CLICK
# 导入 CLICK 库用于构建命令行界面
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
# 默认的页面加载/操作超时时间（毫秒）

ALLOWED_ATTRS = ['class', 'src', 'placeholder']
# 定义允许保留的 HTML 属性列表
TAGS_TO_REMOVE = ['defs', 'path', 'style', 'script', 'noscript', 'meta', 'link', 'svg']
# 定义需要移除的 HTML 标签列表

def _clean_html_content(full_html_string: str) -> str:
# 定义清理 HTML 内容的函数，现在接受完整的 HTML 字符串
    """
    清理HTML内容，移除指定标签，并只保留指定属性。
    该函数现在会从完整的HTML中提取body内容进行清理。
    """
    # 函数文档字符串
    full_soup = BeautifulSoup(full_html_string, 'html.parser')
    # 使用 html.parser 解析完整的 HTML 字符串
    body_tag = full_soup.find('body')
    # 查找 body 标签
    
    if body_tag:
    # 如果找到了 body 标签
        soup = BeautifulSoup(str(body_tag), 'html.parser')
        # 使用 body 的 HTML 字符串创建一个新的 BeautifulSoup 对象
    else:
    # 如果没有 body 标签
        soup = full_soup
        # 则使用完整的 HTML 内容进行清理
    
    # 移除指定的无内容标签
    for tag_name in TAGS_TO_REMOVE:
    # 遍历需要移除的标签名
        for tag in soup.find_all(tag_name):
        # 查找所有匹配的标签
            tag.decompose()
            # 彻底移除标签及其内容
    
    # 清理属性
    for tag in soup.find_all(True):
    # 遍历 HTML 中的所有标签
        attrs_to_remove = [attr for attr in tag.attrs if attr not in ALLOWED_ATTRS]
        # 找出不在允许列表中的属性
        for attr in attrs_to_remove:
        # 遍历需要移除的属性
            del tag.attrs[attr]
            # 从标签中删除该属性
            
    return str(soup)
    # 返回处理后的 HTML 字符串

def _get_page_by_id(browser, id: str, fallback_to_last: bool = False):
# 定义根据 ID 获取页面的辅助函数
    """
    根据给定的 ID 从浏览器实例中获取对应的页面。
    如果 fallback_to_last 为 True，在 ID 为空且找不到页面时尝试返回最后一个可见页面。
    """
    page = None
    if id:
        try:
            context_idx, page_idx = map(int, id.split('-'))
        except ValueError:
            CLICK.echo(f"无效的页面标识符格式: {id}。期望格式为 'context_index-page_index' (例如: 0-0)。")
            sys.exit(1)

        if context_idx < len(browser.contexts):
            context = browser.contexts[context_idx]
            if page_idx < len(context.pages):
                page = context.pages[page_idx]

    if not page and fallback_to_last and browser.contexts:
        last_context = browser.contexts[-1]
        if last_context.pages:
            page = last_context.pages[-1]

    if not page:
    # 如果最终仍未找到任何页面
        if id:
            CLICK.echo(f"未找到标识符为 {id} 的页面。")
        else:
            CLICK.echo("未找到任何打开的页面。")
        # 打印错误消息
        sys.exit(1)
        # 退出程序

    return page

@CLICK.group()
# 定义 CLICK 命令行组
def cli():
# 定义主入口函数
    """Chrome 命令行工具。"""
    # 组文档字符串
    pass
    # 占位符

@cli.command(context_settings=dict(ignore_unknown_options=True))
# 定义 open 子命令，忽略未知的命令行选项
@CLICK.option('--url', '-u', required=True, type=str, help='要访问的网页地址。')
# 添加 --url 参数（支持 -u 别名）
def open(url: str, **kwargs):
# 定义 open 命令的执行逻辑，使用 **kwargs 接收被忽略的额外参数
    """连接到现有Chrome浏览器，访问指定URL，并返回清理后的HTML内容与页面ID。"""
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
                    parsed_target_url = urljoin(url, '/')
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
                page.goto(url, timeout=DEFAULT_TIMEOUT)
                # 导航到目标 URL
            
            page.wait_for_load_state('networkidle', timeout=DEFAULT_TIMEOUT)
            # 等待网络空闲，确保动态内容加载完成

            html_content = page.content()
            # 获取页面的完整 HTML 内容
            
            # 清理HTML属性和移除无内容标签
            preprocessed_body_html = _clean_html_content(html_content)
            # 调用函数清理 HTML 内容，直接传入完整的 HTML

            minified_html = minify(preprocessed_body_html)
            # 压缩清理后的 HTML

            CLICK.echo("\n--- HTML输出开始 ---")
            # 打印输出开始标记
            CLICK.echo(minified_html)
            # 打印最终的 HTML 内容
            CLICK.echo("\n--- HTML输出结束 ---")
            # 打印输出结束标记

            # 输出页面的唯一标识符
            context_index = browser.contexts.index(page.context)
            # 获取页面所属上下文的索引
            page_index = page.context.pages.index(page)
            # 获取页面在上下文中的索引
            CLICK.echo(f"页面唯一标识符ID: {context_index}-{page_index}")
            # 打印页面的唯一标识符

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出

@cli.command(context_settings=dict(ignore_unknown_options=True))
# 定义 click 子命令，忽略未知的命令行选项
@CLICK.option('--id', '-id', type=str, help='要操作的页面唯一标识符 (例如: 0-0)。')
# 添加 --id 参数，并说明其作用
@CLICK.option('--xpath', '-x', required=True, type=str, help='要点击元素的 XPath。')
# 添加 --xpath 参数（支持 -x 别名）
def click(id: str, xpath: str, **kwargs):
# 定义 click 命令的执行逻辑，使用 **kwargs 接收被忽略的额外参数
    """在指定页面中点击指定 XPath 的元素。自动检测并报告点击后的状态（新页面、当前页跳转、或当前页无跳转）。"""
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

            page = _get_page_by_id(browser, id, fallback_to_last=True)
            # 使用辅助函数获取页面，允许在未提供 ID 时回退到最后一个页面

            from playwright.sync_api import TimeoutError as PlaywrightTimeoutError

            # 记录点击前的状态
            initial_url = page.url
            context = page.context
            initial_pages_count = len(context.pages)
            
            # 尝试执行点击并自动检测后续状态
            try:
                # 使用 Promise.all 风格的方式同时监听新页面和当前页跳转
                # 但因为是同步 API，我们只能先点击，然后再根据状态判断
                page.click(f"{xpath}", timeout=DEFAULT_TIMEOUT)
                
                # 给浏览器一点点反应时间 (比如 JavaScript 触发的 window.open 或 location.href)
                page.wait_for_timeout(500)
                
                # 检查 1: 是否有新页面被创建
                current_pages = context.pages
                if len(current_pages) > initial_pages_count:
                    # 找到了新页面（通常是最后一个）
                    new_page = current_pages[-1]
                    # 新页面也等待网络空闲，确保动态内容加载完成
                    try:
                        new_page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT)
                    except PlaywrightTimeoutError:
                        pass # 忽略加载超时，尽量继续处理
                    
                    # 获取新页面的标识符
                    context_index = browser.contexts.index(context)
                    page_index = context.pages.index(new_page)
                    new_page_id = f"{context_index}-{page_index}"
                    
                    CLICK.echo(f"点击已完成，打开了新页面。")
                    CLICK.echo(f"新页面ID: {new_page_id}")
                    #CLICK.echo(f"新页面URL: {new_page.url}")
                    
                    # 打印新页面的 HTML
                    html_content = new_page.content()
                    preprocessed_html = _clean_html_content(html_content)
                    minified_html = minify(preprocessed_html)
                    CLICK.echo("\n--- HTML输出开始 ---")
                    CLICK.echo(minified_html)
                    CLICK.echo("\n--- HTML输出结束 ---")
                    
                    return

                # 检查 2: 当前页面是否发生了跳转
                try:
                    # 等待网络空闲，确保动态内容加载完成
                    page.wait_for_load_state("networkidle", timeout=DEFAULT_TIMEOUT)
                except PlaywrightTimeoutError:
                    pass # 忽略加载超时，继续判断 URL

                current_url = page.url
                if current_url != initial_url:
                    CLICK.echo(f"点击已完成，当前页面发生了跳转。")
                    CLICK.echo(f"当前页面ID: {id}")
                    #CLICK.echo(f"跳转后URL: {current_url}")
                    
                    # 打印跳转后页面的 HTML
                    html_content = page.content()
                    preprocessed_html = _clean_html_content(html_content)
                    minified_html = minify(preprocessed_html)
                    CLICK.echo("\n--- HTML输出开始 ---")
                    CLICK.echo(minified_html)
                    CLICK.echo("\n--- HTML输出结束 ---")
                    
                    return


                # 检查 3: 没有任何跳转或新页面
                CLICK.echo(f"点击已完成，页面URL未改变，也未打开新页面。")
                CLICK.echo(f"当前页面ID: {id}")
                   
                # 打印跳转后页面的 HTML
                html_content = page.content()
                preprocessed_html = _clean_html_content(html_content)
                minified_html = minify(preprocessed_html)
                CLICK.echo("\n--- HTML输出开始 ---")
                CLICK.echo(minified_html)
                CLICK.echo("\n--- HTML输出结束 ---")             
                            
            except PlaywrightTimeoutError:
                CLICK.echo(f"点击失败: 无法在 {DEFAULT_TIMEOUT}ms 内找到或点击元素 {xpath}")
                sys.exit(1)
            

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出

@cli.command(context_settings=dict(ignore_unknown_options=True))
# 定义 fill 子命令，忽略未知的命令行选项
@CLICK.option('--id', '-id', type=str, help='要操作的页面唯一标识符 (例如: 0-0)。')
# 添加 --id 参数，并说明其作用
@CLICK.option('--xpath', '-x', required=True, type=str, help='要填写文本的输入框的 XPath。')
# 添加 --xpath 参数
@CLICK.option('--value', '-v', required=True, type=str, help='要填写的文本内容。')
# 添加 --value 参数（支持 -v 别名）
def fill(id: str, xpath: str, value: str, **kwargs):
# 定义 fill 命令的执行逻辑，使用 **kwargs 接收被忽略的额外参数
    """在指定页面中，向指定 XPath 的输入框填写文本。"""
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

            page = _get_page_by_id(browser, id, fallback_to_last=True)
            # 使用辅助函数获取页面，允许在未提供 ID 时回退到最后一个页面

            page.fill(f"{xpath}", value, timeout=DEFAULT_TIMEOUT)
            # 执行填写操作，使用 xpath 选择器
            CLICK.echo("文本填写操作已完成")
            # 打印成功消息

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出

@cli.command(context_settings=dict(ignore_unknown_options=True))
# 定义 screenshot 子命令，忽略未知的命令行选项
@CLICK.option('--id', '-id', type=str, help='要截图的页面唯一标识符 (例如: 0-0)。')
# 添加 --id 参数，并说明其作用
@CLICK.option('--xpath', '-x', type=str, help='要截图的特定元素的 XPath。如果提供，将只截取该元素。')
# 添加 --xpath 参数（支持 -x 别名）
@CLICK.option('--path', '-p', type=str, help='截图保存的路径和文件名。如果未提供，将生成一个默认文件名。')
# 添加 --path 参数（支持 -p 别名）
@CLICK.option('--full-page', is_flag=True, help='如果设置，将截取整个页面的滚动区域。与 --xpath 不兼容。')
# 添加 --full-page 标志
def screenshot(id: str, xpath: str, path: str, full_page: bool, **kwargs):
# 定义 screenshot 命令的执行逻辑，使用 **kwargs 接收被忽略的额外参数
    """对指定页面或页面上的特定元素进行截图。"""
    # 命令文档字符串
    os.environ['NODE_NO_WARNINGS'] = '1'
    # 隐藏 Node.js 的 DeprecationWarning

    try:
    # 开始错误捕获
        with sync_playwright() as p:
            # 构建 CDP 连接端点 URL
            browser = p.chromium.connect_over_cdp(DEFAULT_CDP_ENDPOINT)
            # 通过 CDP 连接到现有的 Chromium 浏览器

            if not browser:
            # 如果连接失败
                CLICK.echo("无法连接到浏览器。请确保浏览器已通过 chrome-start.py 启动。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序

            page = _get_page_by_id(browser, id, fallback_to_last=True)
            # 使用辅助函数获取页面，允许在未提供 ID 时回退到最后一个页面

            # 确定截图保存路径
            if not path:
            # 如果没有提供路径
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                # 生成当前时间戳
                path = f"screenshot_{timestamp}.png"
                # 生成默认文件名
            
            if xpath:
            # 如果提供了元素 XPath
                if full_page:
                # 如果同时提供了 --full-page
                    CLICK.echo("错误: 不能同时使用 --xpath 和 --full-page。")
                    # 打印错误消息
                    sys.exit(1)
                    # 退出程序
                
                #CLICK.echo(f"正在对页面 {page.url} 上 XPath='{xpath}' 的元素进行截图，保存到: {path}")
                # 打印元素截图信息
                page.locator(f"{xpath}").screenshot(path=path)
                # 执行元素截图操作
            else:
            # 如果没有提供元素 XPath，则进行页面截图
                #CLICK.echo(f"正在对页面 {page.url} 进行截图，保存到: {path}")
                # 打印页面截图信息
                page.screenshot(path=path, full_page=full_page)
                # 执行页面截图操作
            CLICK.echo(f"截图操作已完成。保存到: {path}")
            # 打印成功消息
    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出
@cli.command()
# 定义 switch 子命令
@CLICK.option('--id', '-id', required=True, type=str, help='要切换到的页面唯一标识符 (例如: 0-0)。')
# 添加 --id 参数
def switch(id: str):
# 定义 switch 命令的执行逻辑
    """切换到指定唯一标识符的页面。"""
    # 命令文档字符串
    os.environ['NODE_NO_WARNINGS'] = '1'
    # 隐藏 Node.js 的 DeprecationWarning

    try:
    # 开始错误捕获
        with sync_playwright() as p:
            # 构建 CDP 连接端点 URL
            browser = p.chromium.connect_over_cdp(DEFAULT_CDP_ENDPOINT)
            # 通过 CDP 连接到现有的 Chromium 浏览器

            if not browser:
            # 如果连接失败
                CLICK.echo("无法连接到浏览器。请确保浏览器已通过 chrome-start.py 启动。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序

            try:
            # 尝试解析页面标识符
                context_idx, page_idx = map(int, id.split('-'))
                # 将标识符拆分为上下文索引和页面索引
            except ValueError:
            # 如果标识符格式不正确
                CLICK.echo(f"无效的页面标识符格式: {id}。例如: 0-0")
                # 打印错误消息
                sys.exit(1)
                # 退出程序

            target_page = None
            # 初始化目标页面变量
            if context_idx < len(browser.contexts):
            # 如果上下文索引在有效范围内
                context = browser.contexts[context_idx]
                # 获取目标上下文
                if page_idx < len(context.pages):
                # 如果页面索引在有效范围内
                    target_page = context.pages[page_idx]
                    # 获取目标页面

            if target_page:
            # 如果找到了目标页面
                #CLICK.echo(f"正在切换到页面: {target_page.url} (标识符: {id})")
                # 打印切换信息
                target_page.bring_to_front()
                # 将目标页面带到前台
                CLICK.echo("页面切换到前台")
                # 打印成功消息
            else:
            # 如果未找到目标页面
                CLICK.echo(f"未找到标识符为 '{id}' 的页面。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出

@cli.command()
# 定义 listen 子命令
@CLICK.option('--id', '-id', required=True, type=str, help='要操作的页面唯一标识符 (例如: 0-0)。')
# 添加 --id 参数
@CLICK.option('--link', '-l', required=True, type=str, help='要侦听的请求 URL 片段或正则表达式。')
# 添加 --link 参数
def listen(id: str, link: str):
# 定义 listen 命令的执行逻辑
    """在指定页面中侦听匹配特定 URL 的请求响应。"""
    # 命令文档字符串
    os.environ['NODE_NO_WARNINGS'] = '1'
    # 隐藏 Node.js 的 DeprecationWarning

    try:
    # 开始错误捕获
        with sync_playwright() as p:
            # 构建 CDP 连接端点 URL
            browser = p.chromium.connect_over_cdp(DEFAULT_CDP_ENDPOINT)
            # 通过 CDP 连接到现有的 Chromium 浏览器

            if not browser:
            # 如果连接失败
                CLICK.echo("无法连接到浏览器。请确保浏览器已通过 chrome-start.py 启动。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序

            try:
            # 尝试解析页面标识符
                context_idx, page_idx = map(int, id.split('-'))
                # 将标识符拆分为上下文索引和页面索引
            except ValueError:
            # 如果标识符格式不正确
                CLICK.echo(f"无效的页面标识符格式: {id}。期望格式为 'context_index-page_index' (例如: 0-0)。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序

            target_page = None
            # 初始化目标页面变量
            if context_idx < len(browser.contexts):
            # 如果上下文索引在有效范围内
                context = browser.contexts[context_idx]
                # 获取目标上下文
                if page_idx < len(context.pages):
                # 如果页面索引在有效范围内
                    target_page = context.pages[page_idx]
                    # 获取目标页面

            if not target_page:
            # 如果未找到目标页面
                CLICK.echo(f"未找到标识符为 '{id}' 的页面。")
                # 打印错误消息
                sys.exit(1)
                # 退出程序

            #CLICK.echo(f"正在页面 {target_page.url} 中侦听包含 '{link}' 的请求...")
            # 打印侦听信息

            # 刷新页面并侦听请求
            with target_page.expect_response(re.compile(link), timeout=DEFAULT_TIMEOUT) as response_info:
            # 期望一个匹配 link 的响应
                target_page.reload(timeout=DEFAULT_TIMEOUT)
                # 重新加载页面
            
            response = response_info.value
            # 获取响应值
            CLICK.echo(f"捕获到请求: {response.url}")
            # 打印捕获到的请求 URL
            CLICK.echo(f"响应状态: {response.status}")
            # 打印响应状态
            CLICK.echo("--- 响应体开始 ---")
            # 打印响应体开始标记
            CLICK.echo(response.text())
            # 打印响应文本
            CLICK.echo("--- 响应体结束 ---")
            # 打印响应体结束标记

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出




@cli.command(context_settings=dict(ignore_unknown_options=True))
# 定义 get 子命令，忽略未知的命令行选项
@CLICK.option('--id', '-id', required=True, type=str, help='要获取内容的页面唯一标识符 (例如: 0-0)。')
# 添加 --id 参数，并说明其作用
def get(id: str, **kwargs):
# 定义 get 命令的执行逻辑，使用 **kwargs 接收被忽略的额外参数
    """获取指定页面标识符的清理后的 HTML 内容。"""
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

            page = _get_page_by_id(browser, id, fallback_to_last=False)
            # 使用辅助函数获取页面，get 命令如果找不到指定的 ID，则不回退

            html_content = page.content()
            # 获取页面的完整 HTML 内容
            
            # 清理HTML属性和移除无内容标签
            preprocessed_html = _clean_html_content(html_content)
            # 调用函数清理 HTML 内容，直接传入完整的 HTML

            minified_html = minify(preprocessed_html)
            # 压缩清理后的 HTML

            CLICK.echo("\n--- HTML输出开始 ---")
            # 打印输出开始标记
            CLICK.echo(minified_html)
            # 打印最终的 HTML 内容
            CLICK.echo("\n--- HTML输出结束 ---")
            # 打印输出结束标记

    except Exception as e:
    # 捕获执行过程中的异常
        CLICK.echo(f"发生错误: {e}")
        # 打印错误详情
        sys.exit(1)
        # 异常退出


if __name__ == '__main__':
# 如果是作为主脚本运行
    cli()
    # 执行 CLICK 命令行组
