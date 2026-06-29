# 导入 json 模块，用于处理 JSON 数据的解析和生成
import json

# 导入 click 模块，用于创建美观的命令行接口
import click

# 导入 os 模块，用于处理文件路径等操作系统相关功能
import os

# 导入 sys 模块，用于处理系统级别的参数和退出等操作
import sys

from pathlib import Path

# 使用 click.command 装饰器，将 search_products 函数转换为命令行命令，提供帮助信息
@click.command(help="根据产品编号模糊搜索产品")
# 使用 click.argument 装饰器定义参数，nargs=-1 表示接受任意数量的位置参数（字符串数组），required=True 表示至少需要输入一个参数
@click.argument('product_nos', nargs=-1, required=True)
# 定义搜索产品的处理函数，接收 product_nos 元组作为入参
def search_products(product_nos):
    # 定义 products.json 文件的绝对路径，确保程序能正确找到该数据源文件
    json_path = Path(__file__).parent / "products.json"
    # 检查 json_path 对应的文件是否实际存在于硬盘上
    if not os.path.exists(json_path):
        # 如果文件不存在，则向标准错误输出红色提示信息
        click.secho(f"错误：找不到文件 {json_path}", fg="red", err=True)
        
        # 异常情况下以状态码 1 退出整个程序运行
        sys.exit(1)
        
    # 尝试读取并解析 JSON 文件内容
    try:
        # 使用上下文管理器安全打开 products.json 文件，显式指定编码为 utf-8
        with open(json_path, 'r', encoding='utf-8') as f:
            # 读取文件中的所有内容，并将其解析转换为 Python 的列表对象
            products = json.load(f)
            
    # 捕获 JSON 解析过程中可能出现的格式错误异常
    except json.JSONDecodeError:
        # 如果解析失败，向标准错误输出红色提示信息，告知数据源格式错误
        click.secho("错误：products.json 格式不正确", fg="red", err=True)
        
        # 异常情况下以状态码 1 退出整个程序运行
        sys.exit(1)
        
    # 初始化一个空列表，用于收集并存储匹配到的产品对象
    matched_products = []
    
    # 遍历命令行输入参数中包含的每一个要搜索的产品编号字符串
    for search_str in product_nos:
        # 针对当前的搜索字符串，遍历 JSON 文件中存储的每一个产品对象
        for product in products:
            # 安全获取当前产品对象的 productNo 字段，如果该字段不存在则回退为空字符串
            product_no = product.get("productNo", "")
            product_name = product.get("name", "")
            
            # 判断当前的搜索字符串是否作为子串包含在该产品的编号或品名中（实现模糊匹配）
            if search_str in product_no or search_str in product_name:
                # 检查该产品是否已被处理过并添加到匹配列表中，通过比较原始产品对象是否存在于已有映射的来源中，但这里简单起见我们比较已提取字典的 '品号'
                # 为避免重复，先检查是否已存在具有相同 '品号' 的记录
                is_duplicate = any(item.get('品号') == product_no for item in matched_products)
                
                # 如果没有重复的品号，则处理该产品
                if not is_duplicate:
                    # 创建一个新的字典，仅包含需要保留的属性，并将其重命名为中文属性名
                    filtered_product = {
                        # 将 productNo 映射为中文属性 '品号'
                        '品号': product.get('productNo'),
                        # 将 name 映射为中文属性 '品名'
                        '品名': product.get('name'),
                        # 将 description 映射为中文属性 '特性'
                        '特性': product.get('description'),
                        # 将 whitePrice 映射为中文属性 '纯白单价'
                        '纯白单价': product.get('whitePrice'),
                        # 将 colorPrice 映射为中文属性 '彩色单价'
                        '彩色单价': product.get('colorPrice'),
                        # 将 samplePrice 映射为中文属性 '版布价'
                        '版布价': product.get('samplePrice'),
                        # 将 fullPrice 映射为中文属性 '足米价'
                        '足米价': product.get('fullPrice'),
                        # 将 content 映射为中文属性 '成分'
                        '成分': product.get('content'),
                        # 将 width 映射为中文属性 '门幅'
                        '门幅': product.get('width'),
                        # 将 weight 映射为中文属性 '克重'
                        '克重': product.get('weight'),
                        # 将 hc 映射为中文属性 '空差'
                        '空差': product.get('hc'),
                        # 将 colors 映射为中文属性 '颜色数'
                        '颜色数': product.get('colors'),
                        # 将 category 映射为中文属性 '类目'
                        '类目': product.get('category')
                    }
                    
                    # 将经过过滤并重命名属性的字典追加到匹配结果列表中
                    matched_products.append(filtered_product)
                    
    # 将包含所有匹配产品对象的列表重新序列化为具有缩进格式的 JSON 字符串
    result_json = json.dumps(matched_products, ensure_ascii=False, indent=2)
    
    # 使用 click.echo 将最终格式化好的 JSON 字符串打印到标准输出终端，作为 CLI 的最终出参
    click.echo(result_json)

# 判断当前模块是否被作为主程序独立运行
if __name__ == "__main__":
    # 如果是主程序运行，则调用经过 click 装饰的 search_products 函数启动命令行接口
    search_products()
