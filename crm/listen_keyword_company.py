# 导入 os 模块用于处理路径和环境变量
import os
# 导入 re 模块用于正则表达式匹配
import re
# 导入 json 模块用于处理 JSON 数据的序列化
import json
# 导入 sys 模块用于系统相关操作
import sys
# 从 datetime 模块导入 datetime 用于生成时间戳
from datetime import datetime
# 从 playwright.sync_api 导入 sync_playwright 用于同步控制浏览器
from playwright.sync_api import sync_playwright

# 定义默认的 CDP 调试端点地址
DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"
# 定义默认的操作超时时间为 30 秒（30000毫秒）
DEFAULT_TIMEOUT = 30000

"""
使用方法
1、开启start-chrome.bat文件
2、运行listen_keyword_bank.py文件
3、打开搜索词查询
4、收集热门商品的公司清单
"""


# 定义用于监听并保存目标接口数据的方法
def listen_and_save_search_bank_data(page_id: str = None):
    """
    连接到现有 Chrome 浏览器，监听指定的1688搜索词排行接口，
    获取返回的 JSON 数据并将其保存到本地文件中。
    """
    # 设置环境变量隐藏 Node.js 的弃用警告
    os.environ['NODE_NO_WARNINGS'] = '1'

    # 开始 try 块捕获可能发生的异常
    try:
        # 初始化并启动 playwright 的同步 API 环境
        with sync_playwright() as p:
            # 通过 CDP 协议连接到本地已开启调试端口的 Chrome 浏览器
            browser = p.chromium.connect_over_cdp(DEFAULT_CDP_ENDPOINT)

            # 检查浏览器对象是否成功创建
            if not browser:
                # 如果连接失败则打印错误信息
                print("无法连接到浏览器。请确保浏览器已启动开启了远程调试端口。")
                # 直接退出函数
                return

            # 初始化目标页面变量为空
            target_page = None

            # 如果调用时传入了页面 ID
            if page_id:
                # 尝试解析传入的页面 ID
                try:
                    # 按照中划线拆分 ID，分别获取上下文索引和页面索引
                    context_idx, page_idx = map(int, page_id.split('-'))
                    # 确保上下文索引在当前浏览器的有效范围内
                    if context_idx < len(browser.contexts):
                        # 获取对应的浏览器上下文对象
                        context = browser.contexts[context_idx]
                        # 确保页面索引在当前上下文的有效范围内
                        if page_idx < len(context.pages):
                            # 将匹配到的页面赋值给目标页面变量
                            target_page = context.pages[page_idx]
                # 捕获解析 ID 时可能出现的 ValueError 异常
                except ValueError:
                    # 打印格式错误的提示信息
                    print(f"无效的页面标识符格式: {page_id}。例如: 0-0")
                    # 直接退出函数
                    return
            # 如果没有传入指定的页面 ID
            else:
                # 遍历浏览器中所有的上下文对象
                for context in browser.contexts:
                    # 遍历当前上下文中的所有页面对象
                    for page in context.pages:
                        # 检查当前页面的 URL 是否包含 1688 生意参谋域名
                        if "sycm.1688.com" in page.url:
                            # 找到匹配域名则将其设为目标页面
                            target_page = page
                            # 跳出内层循环
                            break
                    # 如果已经找到了目标页面
                    if target_page:
                        # 跳出外层循环
                        break
                
                # 如果遍历完没找到特定页面，且浏览器有至少一个页面
                if not target_page and browser.contexts and browser.contexts[-1].pages:
                    # 默认使用最后一个上下文的最后一个页面
                    target_page = browser.contexts[-1].pages[-1]

            # 检查最终是否成功获取到了页面
            if not target_page:
                # 打印未找到页面的错误信息
                print("未找到可用的页面。")
                # 退出函数
                return

            # 定义需要匹配的接口请求路径的正则表达式，匹配 hotItems、getShopRank 和 getItmRank 接口
            link_pattern = r"sycm\.1688\.com/ms/compete/(keyword/hotItems|slrRank/getShopRank|slrRank/getItmRank)\.json"

            
            # 打印正在哪个页面进行侦听的信息
            print(f"正在页面 {target_page.url} 中侦听请求...")

            # 打印提示信息，告知用户可以在页面上操作
            print("请在页面上进行搜索、切换类目或翻页等操作，以触发数据接口...")
            # 提示用户如何退出脚本
            print("提示: 脚本将持续监听并保存数据。如需停止，请按 Ctrl+C 终止运行。")  

            # 使用无限循环来实现持续监听
            while True:
                # 使用 expect_response 拦截匹配正则的响应，设置超时为0（无限等待），等待用户在页面上进行操作触发请求
                with target_page.expect_response(re.compile(link_pattern), timeout=0) as response_info:
                    # 占位符，仅用于保持 with 块的语法，实际动作由用户在浏览器中完成
                    pass
                
                # 获取拦截到的响应对象
                response = response_info.value
                # 打印拦截成功的接口 URL
                print(f"\n捕获到请求: {response.url}")
                # 打印接口返回的 HTTP 状态码
                print(f"响应状态: {response.status}")
                
                # 尝试等待页面上的类目元素加载完成，最多等待 5 秒
                try:
                    # 等待 ul.oui-cascader-value-item 元素出现在 DOM 中
                    target_page.wait_for_selector('ul.oui-cascader-value-item', timeout=5000)
                # 捕获等待超时的异常
                except Exception:
                    # 超时未找到则忽略异常，继续后续保存逻辑
                    pass
                
                # 尝试解析响应数据并保存
                try:
                    # 将响应体的文本内容解析为 JSON 字典对象
                    json_data = response.json()
                    
                    # 从 urllib.parse 导入 unquote 用于 URL 解码
                    from urllib.parse import unquote
                    
                    # 默认文件名
                    filename = "unknown_data.json"
                    
                    # 定义 dateType 到中文的映射字典
                    date_type_mapping = {
                        # 将 recent7 映射为 近7天
                        "recent7": "近7天",
                        # 将 recent30 映射为 近30天
                        "recent30": "近30天",
                        # 将 day 映射为 当天
                        "day": "当天",
                        # 将 week 映射为 本周
                        "week": "本周",
                        # 将 month 映射为 本月
                        "month": "本月"
                    }
                    
                    # 定义 tabFlag 到中文的映射字典
                    tab_flag_mapping = {
                        # 将 ipvUvIndex 映射为 热访榜
                        "ipvUvIndex": "热访榜",
                        # 将 seUvIndex 映射为 热搜榜
                        "seUvIndex": "热搜榜",
                        # 将 seSpvChangeRate 映射为 飙升榜
                        "seSpvChangeRate": "飙升榜",
                        # 将 activeInquiryUserIndex 映射为 询盘榜
                        "activeInquiryUserIndex": "询盘榜",
                        # 将 payOrdAmtIndex 映射为 热销榜
                        "payOrdAmtIndex": "热销榜"
                    }
                    
                    # 判断当前请求是否为 hotItems 接口
                    if "hotItems.json" in response.url:
                        # 使用正则表达式提取 searchWord 参数的值
                        search_word_match = re.search(r'[?&]searchWord=([^&]+)', response.url)
                        # 如果匹配成功则对 URL 编码进行解码，否则使用默认值 'unknown_word'
                        search_word = unquote(search_word_match.group(1)) if search_word_match else "unknown_word"
                                
                        # 从请求 URL 中使用正则表达式提取 dateRange 参数的值
                        date_range_match = re.search(r'[?&]dateRange=([^&]+)', response.url)
                        # 如果匹配成功则对 URL 编码进行解码并将竖线替换为下划线，否则使用空字符串
                        date_range_str = unquote(date_range_match.group(1)).replace('|', '_') if date_range_match else ""
                        # 格式化 date_range 为文件名前缀格式
                        date_range_prefix = f"{date_range_str}_" if date_range_str else ""
                        
                        # 从请求 URL 中使用正则表达式提取 dateType 参数的值
                        date_type_match = re.search(r'[?&]dateType=([^&]+)', response.url)
                        # 如果匹配成功则获取对应的值，否则使用空字符串
                        date_type_val = date_type_match.group(1) if date_type_match else ""
                        # 根据映射字典转换为中文，如果不在字典中则使用原值或默认值 'unknown_date'
                        date_type_cn = date_type_mapping.get(date_type_val, date_type_val or "unknown_date")
        
                        # 拼接最终的 JSON 文件名，格式如: hot_items_连衣裙轻奢高级感_2026-06-10_2026-06-16_近30天.json
                        filename = f"hot_items_{search_word}_{date_range_prefix}{date_type_cn}.json"
                        
                    # 判断当前请求是否为 getShopRank 接口
                    elif "getShopRank.json" in response.url:
                        # 获取 class 为 oui-cascader-value-item 的 ul 元素的内部文本列表
                        cascader_texts = target_page.locator('ul.oui-cascader-value-item').all_inner_texts()
                        
                        # 初始化默认的文件名前缀为 shop_rank
                        file_prefix = "shop_rank"
                        
                        # 检查是否成功获取到了级联文本内容
                        if cascader_texts:
                            # 将文本列表拼接成一个初始字符串
                            raw_text = "-".join(cascader_texts)
                            # 将字符串中的斜杠、反斜杠替换为短横线，防止被识别为路径
                            raw_text = re.sub(r'[/\\]', '-', raw_text)
                            # 将字符串中的空白字符（如换行、空格等）全部替换为短横线
                            parsed_prefix = re.sub(r'\s+', '-', raw_text.strip())
                            # 将连续的多个短横线合并为单个短横线
                            parsed_prefix = re.sub(r'-+', '-', parsed_prefix)
                            # 去除字符串首尾可能多余的短横线
                            parsed_prefix = parsed_prefix.strip('-')
                            # 检查处理后的字符串是否为空
                            if parsed_prefix:
                                # 如果不为空，则将处理后的字符串加入到文件名前缀中
                                file_prefix = f"shop_rank_{parsed_prefix}"
                                
                        # 从请求 URL 中使用正则表达式提取 dateRange 参数的值
                        date_range_match = re.search(r'[?&]dateRange=([^&]+)', response.url)
                        # 如果匹配成功则对 URL 编码进行解码并将竖线替换为下划线，否则使用空字符串
                        date_range_str = unquote(date_range_match.group(1)).replace('|', '_') if date_range_match else ""
                        # 格式化 date_range 为文件名前缀格式
                        date_range_prefix = f"{date_range_str}_" if date_range_str else ""
                        
                        # 从请求 URL 中使用正则表达式提取 dateType 参数的值
                        date_type_match = re.search(r'[?&]dateType=([^&]+)', response.url)
                        # 如果匹配成功则获取对应的值，否则使用空字符串
                        date_type_val = date_type_match.group(1) if date_type_match else ""
                        # 根据映射字典转换为中文，如果不在字典中则使用原值或默认值 'unknown_date'
                        date_type_cn = date_type_mapping.get(date_type_val, date_type_val or "unknown_date")
                        
                        # 从请求 URL 中使用正则表达式提取 tabFlag 参数的值
                        tab_flag_match = re.search(r'[?&]tabFlag=([^&]+)', response.url)
                        # 如果匹配成功则获取对应的值，否则使用空字符串
                        tab_flag_val = tab_flag_match.group(1) if tab_flag_match else ""
                        # 根据映射字典转换为中文，如果不在字典中则使用原值或默认值 'unknown_tab'
                        tab_flag_cn = tab_flag_mapping.get(tab_flag_val, tab_flag_val or "unknown_tab")
                        
                        # 从请求 URL 中使用正则表达式提取 page 参数的值
                        page_match = re.search(r'[?&]page=([^&]+)', response.url)
                        # 如果匹配成功则获取对应的值，否则使用默认值 '1'
                        page = page_match.group(1) if page_match else "1"
                        
                        # 拼接最终的 JSON 文件名，格式如: shop_rank_类目_2026-06-10_2026-06-16_近30天_热销榜_1.json
                        filename = f"{file_prefix}_{date_range_prefix}{date_type_cn}_{tab_flag_cn}_{page}.json"
                        
                    # 判断当前请求是否为 getItmRank 接口
                    elif "getItmRank.json" in response.url:
                        # 获取 class 为 oui-cascader-value-item 的 ul 元素的内部文本列表
                        cascader_texts = target_page.locator('ul.oui-cascader-value-item').all_inner_texts()
                        
                        # 初始化默认的文件名前缀为 item_rank
                        file_prefix = "item_rank"
                        
                        # 检查是否成功获取到了级联文本内容
                        if cascader_texts:
                            # 将文本列表拼接成一个初始字符串
                            raw_text = "-".join(cascader_texts)
                            # 将字符串中的斜杠、反斜杠替换为短横线，防止被识别为路径
                            raw_text = re.sub(r'[/\\]', '-', raw_text)
                            # 将字符串中的空白字符（如换行、空格等）全部替换为短横线
                            parsed_prefix = re.sub(r'\s+', '-', raw_text.strip())
                            # 将连续的多个短横线合并为单个短横线
                            parsed_prefix = re.sub(r'-+', '-', parsed_prefix)
                            # 去除字符串首尾可能多余的短横线
                            parsed_prefix = parsed_prefix.strip('-')
                            # 检查处理后的字符串是否为空
                            if parsed_prefix:
                                # 如果不为空，则将处理后的字符串加入到文件名前缀中
                                file_prefix = f"item_rank_{parsed_prefix}"
                                
                        # 从请求 URL 中使用正则表达式提取 dateRange 参数的值
                        date_range_match = re.search(r'[?&]dateRange=([^&]+)', response.url)
                        # 如果匹配成功则对 URL 编码进行解码并将竖线替换为下划线，否则使用空字符串
                        date_range_str = unquote(date_range_match.group(1)).replace('|', '_') if date_range_match else ""
                        # 格式化 date_range 为文件名前缀格式
                        date_range_prefix = f"{date_range_str}_" if date_range_str else ""
                        
                        # 从请求 URL 中使用正则表达式提取 dateType 参数的值
                        date_type_match = re.search(r'[?&]dateType=([^&]+)', response.url)
                        # 如果匹配成功则获取对应的值，否则使用空字符串
                        date_type_val = date_type_match.group(1) if date_type_match else ""
                        # 根据映射字典转换为中文，如果不在字典中则使用原值或默认值 'unknown_date'
                        date_type_cn = date_type_mapping.get(date_type_val, date_type_val or "unknown_date")
                        
                        # 从请求 URL 中使用正则表达式提取 tabFlag 参数的值
                        tab_flag_match = re.search(r'[?&]tabFlag=([^&]+)', response.url)
                        # 如果匹配成功则获取对应的值，否则使用空字符串
                        tab_flag_val = tab_flag_match.group(1) if tab_flag_match else ""
                        # 根据映射字典转换为中文，如果不在字典中则使用原值或默认值 'unknown_tab'
                        tab_flag_cn = tab_flag_mapping.get(tab_flag_val, tab_flag_val or "unknown_tab")
                        
                        # 从请求 URL 中使用正则表达式提取 page 参数的值
                        page_match = re.search(r'[?&]page=([^&]+)', response.url)
                        # 如果匹配成功则获取对应的值，否则使用默认值 '1'
                        page = page_match.group(1) if page_match else "1"
                        
                        # 拼接最终的 JSON 文件名，格式如: item_rank_类目_2026-06-10_2026-06-16_近30天_热销榜_1.json
                        filename = f"{file_prefix}_{date_range_prefix}{date_type_cn}_{tab_flag_cn}_{page}.json"
                    
                    # 获取当前脚本所在目录的绝对路径
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    # 生成只包含年月日的日期字符串，例如 20260525
                    date_str = datetime.now().strftime("%Y%m%d")
                    
                    # 拼接目标文件夹路径：基础目录 / account / 当前日期
                    target_dir = os.path.join(base_dir, "account", date_str)
                    
                    # 检查目标文件夹是否存在，如果不存在则级联创建（包含 account 文件夹）
                    if not os.path.exists(target_dir):
                        # 级联创建文件夹，并捕获可能的权限等异常（由外层的 except 捕获）
                        os.makedirs(target_dir)
                    
                    # 构造用于保存数据的本地绝对文件路径
                    save_path = os.path.join(target_dir, filename)
                    
                    # 使用 utf-8 编码模式打开或创建目标文件
                    with open(save_path, 'w', encoding='utf-8') as f:
                        # 将 JSON 数据写入文件，禁止 ASCII 转义以保留中文，并设置缩进
                        json.dump(json_data, f, ensure_ascii=False, indent=4)
                        
                    # 打印成功保存文件的路径信息
                    print(f"数据已成功保存到本地: {save_path}")

                # 捕获解析或文件写入时发生的异常
                except Exception as e:
                    # 打印解析或保存失败的详细信息
                    print(f"解析或保存数据失败: {e}")

    # 捕获用户按下 Ctrl+C 触发的键盘中断异常
    except KeyboardInterrupt:
        # 打印脚本正常退出的提示信息
        print("\n脚本已由用户停止运行。")
    # 捕获整个过程中可能发生的其他异常
    except Exception as e:
        # 打印全局错误信息
        print(f"发生错误: {e}")

# 如果当前脚本是作为主程序直接运行
if __name__ == '__main__':
    # 调用刚定义的方法开始侦听并保存数据
    listen_and_save_search_bank_data()


