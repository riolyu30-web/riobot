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

            # 定义需要匹配的接口请求路径的正则表达式，同时匹配原有接口和新增加的 relatedWord 接口
            link_pattern = r"sycm\.1688\.com/ms/compete/keyword(?:Rank/list|/relatedWord)\.json"
            
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
                    
                    # 获取 class 为 oui-cascader-value-item 的 ul 元素的内部文本列表
                    cascader_texts = target_page.locator('ul.oui-cascader-value-item').all_inner_texts()
                    
                    # 设置默认的文件名前缀
                    file_prefix = "search_bank_data"
                    
                    # 如果拦截到的是 relatedWord 接口，则尝试从请求 URL 中获取 searchWord 的值作为文件名前缀
                    if "relatedWord.json" in response.url:
                        # 使用正则表达式提取 searchWord 参数的值
                        search_word_match = re.search(r'[?&]searchWord=([^&]+)', response.url)
                        if search_word_match:
                            # 如果获取到了，直接作为文件名前缀
                            from urllib.parse import unquote
                            file_prefix = unquote(search_word_match.group(1))
                    else:
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
                                # 如果不为空，则将处理后的字符串作为文件名前缀
                                file_prefix = parsed_prefix
                            
                    # 从请求 URL 中使用正则表达式提取 dateType 参数的值
                    date_type_match = re.search(r'[?&]dateType=([^&]+)', response.url)
                    # 如果匹配成功则获取对应的值，否则使用默认值 'unknown_date'
                    date_type = date_type_match.group(1) if date_type_match else "unknown_date"
    
                    # 从请求 URL 中使用正则表达式提取 searchWordType 参数的值
                    search_word_type_match = re.search(r'[?&]searchWordType=([^&]+)', response.url)
                    # 如果匹配成功则获取对应的值，否则使用默认值 'unknown_word_type'
                    search_word_type = search_word_type_match.group(1) if search_word_type_match else "unknown_word_type"
    
                    # 拼接最终的 JSON 文件名，去除了时间戳，同名将被直接覆盖
                    filename = f"{file_prefix}_{date_type}_{search_word_type}.json"
                    
                    # 获取当前脚本所在目录的绝对路径
                    base_dir = os.path.dirname(os.path.abspath(__file__))
                    
                    # 生成只包含年月日的日期字符串，例如 20260525
                    date_str = datetime.now().strftime("%Y%m%d")
                    
                    # 拼接目标文件夹路径：基础目录 / keywords / 当前日期
                    target_dir = os.path.join(base_dir, "keywords", date_str)
                    
                    # 检查目标文件夹是否存在，如果不存在则级联创建（包含 keywords 文件夹）
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
                
                    get_keywords(save_path)

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



def get_keywords(keywords_file: str) -> list: # 定义获取产品关键词的方法
    # 初始化一个空列表，用于存储最终返回的关键词
    keywords = []
    
    # 尝试执行文件读取和数据处理操作
    try:
        # 以 UTF-8 编码读取指定的 JSON 关键词文件
        with open(keywords_file, 'r', encoding='utf-8') as f:
            # 将读取的文件内容解析为 JSON 对象
            json_data = json.load(f)
            
        # 尝试从 JSON 数据中提取关键词列表数据
        # 根据提供的数据结构，数据通常在 json_data["data"]["data"] 中
        data_list = json_data.get("data", {}).get("data", [])
        
        # 检查是否成功获取到了数据列表
        if not data_list:
            # 如果没有数据，打印提示信息
            print(f"在文件 {keywords_file} 中未找到关键词数据")
            # 返回空列表
            return keywords
            
        # 遍历数据列表，为每个关键词条目计算 roi (投产比) 并存储
        for item in data_list:
            # 尝试获取计算所需的各个指标值，如果不存在则默认为 0
            # 包月价/参考价 (referencePrice)
            reference_price = item.get("referencePrice", {}).get("value", 0)
            # 点击率 (clkRate)
            clk_rate = item.get("clkRate", {}).get("value", 0)
            # 在线商品数 (seMaxRescnt)
            se_max_rescnt = item.get("seMaxRescnt", {}).get("value", 0)
            
            # 获取关键词文本 (seKeyword 或 searchWord 都可以，这里取 searchWord 更直接，或者取 seKeyword.value)
            se_keyword = item.get("searchWord", item.get("seKeyword", {}).get("value", ""))
            
            # 计算人头数：在线商品数 * 点击率
            headcount = se_max_rescnt * clk_rate
            # 将人头数存储起来方便后续提取
            item["_headcount"] = headcount
            
            # 确保分母（包月价）不为 0，防止除零错误
            if reference_price > 0:
                # 计算投产比 (roi)：人头数 / 包月价
                roi = headcount / reference_price
                # 将计算结果存储回字典中，方便后续排序
                item["_roi"] = roi
                # 将关键词文本存储起来方便后续提取
                item["_keyword_text"] = se_keyword
            else:
                # 如果包月价为 0，则该项投产比设为 0
                item["_roi"] = 0
                # 将关键词文本存储起来方便后续提取
                item["_keyword_text"] = se_keyword
                
        # 根据计算出的 roi 对数据列表进行降序排序
        # lambda 表达式提取每个条目的 _roi 进行比较
        sorted_data = sorted(data_list, key=lambda x: x.get("_roi", 0), reverse=True)
        
        # 打印提示信息，准备输出前 20 名关键词
        print(f"--- 文件 {os.path.basename(keywords_file)} 中 排名前 20 的关键词 ---")
        
        # 遍历排好序的前 20 个条目（如果总数不足 20 个，则遍历所有）
        for i, item in enumerate(sorted_data[:20], 1):
            # 获取关键词文本
            kw = item.get("_keyword_text", "")
            # 获取计算出的投产比 (roi)
            roi = item.get("_roi", 0)
            # 获取包月价 (参考价)
            ref_price = item.get("referencePrice", {}).get("value", 0)
            # 获取人头数
            headcount = item.get("_headcount", 0)
            
            # 打印排名、关键词、包月价、人头数和投产比，保留 4 位小数
            print(f"Top {i}: {kw} (包月价: {ref_price}, 进店数: {headcount:.4f}, 投产比: {roi:.4f})")
            
            # 只有当关键词不为空时，才将其添加到最终返回的列表中
            if kw:
                # 将关键词追加到列表中
                keywords.append(kw)
                
    # 捕获文件未找到等 IO 异常
    except IOError as e:
        # 打印读取文件失败的错误信息
        print(f"读取关键词文件失败: {e}")
    # 捕获 JSON 解析异常
    except json.JSONDecodeError as e:
        # 打印 JSON 解析失败的错误信息
        print(f"解析关键词文件 JSON 数据失败: {e}")
    # 捕获其他未知异常
    except Exception as e:
        # 打印处理过程中的未知错误
        print(f"处理关键词数据时发生错误: {e}")

    return keywords # 返回关键词列表
# 如果当前脚本是作为主程序直接运行
if __name__ == '__main__':
    # 调用刚定义的方法开始侦听并保存数据
    listen_and_save_search_bank_data()


