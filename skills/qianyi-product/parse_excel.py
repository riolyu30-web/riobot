import re
import openpyxl
from openai import OpenAI
import base64
import mimetypes
import os
import time # 导入时间模块用于生成唯一文件名
import json # 导入JSON模块用于解析响应数据
from datetime import datetime # 导入datetime模块用于获取当前日期
import hashlib # 导入hashlib模块用于MD5哈希

from PIL import Image
import io
from dotenv import load_dotenv
load_dotenv()
JIEKOU_API_KEY = os.getenv("JIEKOU_API_KEY")
import re

# 来自6号运营微信置顶消息
WX_DATA = """
乐丽丝
501#乐丽丝玲珑麻135克(88色)
502#乐丽丝双色平纹135克(70色)
503#乐丽丝直条135克(66色)
504#乐丽丝波浪条135克(66色)
505#乐丽丝宝格丽135克(66色)
506#乐丽丝菱形条135克(66色)
507#乐丽丝仿麻135克(88色)
508#乐丽丝猫眼135克(70色)

天丝
801#涤天丝55克(226色)
802#天丝仙女条65克(141色)
803#天丝彩虹条58克
804#天丝千鸟格58克
805#加密花丝皱65克(132色)
806#洛施棉60克(77色)
807#喜之麻80克(83色)
808#天丝皱65克(162色)
809#闪光天丝60克(58色)
810#亮丝麻50克(61色)
811#天丝蚂蚁皱65克(71色)
812#天丝波浪条65克
813#天丝牙签条85克(143色)
814#天丝闪光皱68克(49色)
815#蚕丝字母条80克(59色)
816#666高密天丝120克(91色)
817#天丝竹节85克(95色)
818#天丝亚运条80克(59色)
819#朗姆58g
822#加厚醋酸天丝73克(18色)
823#天丝亚麻85克(65色)
825#加厚曲天丝80克(43色)
826#沙面平纹140克(111色)
827#香格麻160克(66色)
828#韩国棉120克(89色)
829#复古棉145克(76色)
830#平纹麻110克(72色)
831#乱麻格120克(189色)
832#双股树皮皱130g(123色)

仿牛仔
703#天丝麻165-170克
713#天丝棉140-145克
726#32支斜纹145克
746#3236免洗牛仔160克

绣花印花底布
601#75D珍珠雪纺85克
602#75D雪纺皱85克
603#30D真丝皱35克
604#全涤闪光天丝60克
605#麻纱65克
606#40支棉感竹节95克
607#双碱雪纺皱85克
608#加密珍珠雪纺100克
609#花瑶皱85克

棉布
901#2060洗水竹节100克(186色)
903#4438高品质180克(168色)
904#加厚砂洗竹节145克(159色)
907#20支洗水皱130克(301色)
911#天然麻140克(171色)
912#加厚双层平布125克(86色)
905#双层皱布125克
906#12*12粘麻竹节砂洗210克
908#9088半工艺60克
909#9088全工艺75克
910#40支平纹仿天丝125克
913#24支砂洗竹节110克
914#高密2060竹节120克
915#高密洗水皱135克
916#洗水皱145克
917#12*12竹节长车185克
918#5147麻棉200克
919#2119苎麻棉140克
920#3068麻棉110克"""

def extract_float_from_string(text): # 定义一个函数来从字符串中提取浮点数
    if text is None : # 如果文本为空
        return 0.0 # 返回100.0
    text = str(text) # 确保文本是字符串
    match = re.search(r'(\d+\.?\d*)', text) # 查找字符串中的浮点数模式
    if match: # 如果找到匹配项
        return float(match.group(1)) # 返回提取到的浮点数
    return 0.0 # 如果没有找到浮点数，返回0.0

def extract_persent_from_string(text): # 定义一个函数来从字符串中提取浮点数
    if text is None or text == "足米" : # 如果文本为空
        return 100 # 返回100.0
    text = str(text) # 确保文本是字符串
    match = re.search(r'(\d+\.?\d*)', text) # 查找字符串中的浮点数模式
    if match: # 如果找到匹配项
        return int(match.group(1)) # 返回提取到的浮点数
    return 0 # 如果没有找到浮点数，返回0.0

def slugify(text): # 定义一个slugify函数，用于将文本转换为16字符的MD5哈希值
    return hashlib.md5(str(text).encode('utf-8')).hexdigest()[:16] # 计算MD5哈希并截取前16个字符

def parse_content_field(content_str): # 定义一个函数来解析成份字段
    if not content_str: # 如果成份字符串为空
        return [] # 返回空列表
    
    # 移除所有空格，并将全角逗号、顿号、斜杠等替换为半角逗号，以便统一分割
    cleaned_str = content_str.replace(' ', '').replace('，', ',').replace('、', ',').replace('/', ',').replace('；', ',')
    
    # 使用更灵活的正则表达式来匹配“数字%或#材质名称”的模式
    # 例如：90%天丝, 75#天丝, 23%锦
    matches = re.findall(r'(\d+)[%#]([\u4e00-\u9fa5]+)', cleaned_str)
    
    parsed_content = [] # 初始化一个空列表来存储解析后的成份
    for percentage_str, name in matches: # 遍历所有匹配项
        if name in ['涤', '全涤']: # 判断材质名称是否为'涤'或'全涤'
            name = '涤纶' # 如果是，则统一规范替换为'涤纶'
        if name in ['棉', '全棉']: # 判断材质名称是否为'棉'或'全棉'
            name = '棉' # 如果是，则统一规范替换为'棉'
        if name in ['莱塞尔天丝', '莱塞尔']: # 判断材质名称是否为'麻'或'全麻'
            name = '天丝' # 如果是，则统一规范替换为'麻'
        if name in ['锦', '全锦']: # 判断材质名称是否为'锦'或'全锦'
            name = '锦纶' # 如果是，则统一规范替换为'锦纶'
        try:
            percentage = int(percentage_str) # 将百分比字符串转换为整数
            parsed_content.append({"name": name, "percentage": percentage}) # 将解析结果添加到列表中
        except ValueError: # 如果转换失败，则跳过
            continue
            
    return parsed_content # 返回解析后的成份列表

def jiekou_chat_json(system_prompt: str, user_prompt: str, model: str = "claude-sonnet-4-5-20250929") -> dict | None:
    client = OpenAI(
        base_url="https://api.jiekou.ai/openai",
        api_key=JIEKOU_API_KEY,
    )
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=False,
            max_tokens=64000,
        )

        content = response.choices[0].message.content
        print(content)

        # Extract JSON content if wrapped in markdown code block
        json_match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
        json_str = json_match.group(1) if json_match else content

        try:
            json_data = json.loads(json_str)
            return json_data
        except json.JSONDecodeError as e:
            print(f"Error decoding JSON from response: {e}")
            print(f"Problematic JSON string: {json_str}")
            return None

    except Exception as e:
        print(f"Error calling chat API: {e}")
        return None

def find_product_images(product_no: str, images_dir: str = "./images/products") -> list[str]: # 定义一个函数来查找产品图片
    found_images = [] # 初始化一个空列表来存储找到的图片
    cleaned_product_no = product_no.replace('#', '') # 清理产品编号，移除'#'
    
    product_dir = os.path.join(images_dir, cleaned_product_no) # 拼接出该产品专属的图片目录路径
    
    if not os.path.exists(product_dir): # 如果该产品的图片目录不存在
        print(f"Warning: Product image directory '{product_dir}' not found.") # 打印警告信息
        return [] # 返回空列表

    for filename in os.listdir(product_dir): # 遍历该产品图片目录中的所有文件
        if filename.endswith('.jpg') or filename.endswith('.png'): # 如果文件是jpg或png图片格式
            # 将相对路径添加到列表中，并确保所有的斜杠方向一致
            image_path = f"{product_dir.replace('./', '/')}/{filename}"
            found_images.append(image_path.replace('\\', '/'))
    return found_images # 返回找到的图片列表

def parse_wx_data(wx_data_str: str) -> dict: # 定义一个函数来解析微信数据
    parsed_data = {} # 初始化一个空字典来存储解析后的数据
    current_category = None # 初始化当前类别
    
    lines = wx_data_str.strip().split('\n') # 按行分割字符串并去除空白
    for line in lines: # 遍历每一行
        line = line.strip() # 去除行首尾空白
        if not line: # 如果行为空，则跳过
            continue
            
        if re.match(r'^[\u4e00-\u9fa5]+$', line): # 如果行只包含中文字符，认为是类别
            current_category = line # 设置当前类别
            parsed_data[current_category] = [] # 初始化该类别下的产品列表
        else: # 否则，认为是产品信息
            # 使用更精确的正则表达式匹配：产品编号 + 产品名称 + (可选的颜色数量)
            match = re.match(r'^(\d+#)(.*?)(?:[\(（](\d+)色[\)）])?$', line) 
            if match and current_category: # 如果匹配成功且有当前类别
                product_no = match.group(1) # 提取产品编号
                product_name = match.group(2).strip() # 提取产品名称
                colors_str = match.group(3) # 提取颜色数量字符串
                colors = int(colors_str) if colors_str else 0 # 提取颜色数量，默认为0
                
                parsed_data[current_category].append({ # 将产品信息添加到当前类别下
                    "product_no": product_no, # 产品编号
                    "product_name": product_name, # 产品名称
                    "colors": colors # 颜色数量
                })
    return parsed_data # 返回解析后的数据

def process_excel(excel_file_path: str, output_json_file_path: str) -> None:
    all_products = [] # 初始化一个空列表来存储所有产品数据
    wx_parsed_data = parse_wx_data(WX_DATA) # 解析微信数据
    print(wx_parsed_data)
    try:
        workbook = openpyxl.load_workbook(excel_file_path) # 加载Excel工作簿
        sheet = workbook.active # 获取活动工作表

        # 获取表头，用于映射列名
        headers = [cell.value for cell in sheet[1]] # 获取第一行的所有单元格值作为表头

        for row_index, row_values in enumerate(sheet.iter_rows(min_row=2, values_only=True)): # 遍历工作表的每一行，从第二行开始（跳过标题行）
            row_data = dict(zip(headers, row_values)) # 将表头和当前行数据组合成字典

            product_no = str(row_data.get('编号', '')).strip() # 获取编号并转换为字符串，去除空白
            if not product_no: # 如果编号为空，则跳过此行
                print(f"Skipping row {row_index + 2} due to missing '编号'.") # 打印跳过行的信息
                continue # 继续下一行

            product_name = str(row_data.get('品名名称', '')).strip() # 获取品名名称并转换为字符串，去除空白
            product_fullname = product_name # 初始化全名默认为品名名称
            # 初始化 category, type, colors
            category = "天丝" # 类别默认为天丝
            type = "面料" # 类型默认为面料 选项 辅料 
            colors = 88 # 颜色数量默认为0

            # 尝试从 WX_DATA 中匹配产品信息
            wx_matched = False # 标记是否从微信数据中匹配到
            for wx_category, wx_products in wx_parsed_data.items(): # 遍历微信数据中的类别和产品
                for wx_product in wx_products: # 遍历每个类别下的产品
                    if wx_product["product_no"].replace('#', '') == product_no.replace('#', ''): # 如果产品编号匹配
                        category = wx_category # 设置类别为微信数据中的类别
                        product_fullname = wx_product["product_name"] # 使用微信数据中的产品名称
                        colors = wx_product["colors"] # 设置颜色数量
                        wx_matched = True # 标记为已匹配
                        break # 跳出内层循环
                if wx_matched: # 如果已匹配
                    break # 跳出外层循环

            # 生成图片路径
            images = find_product_images(product_no) # 调用函数查找产品图片

            # 解析成份字段
            content_str = str(row_data.get('成份', '')).strip() # 获取成份并转换为字符串，去除空白
            parsed_content = parse_content_field(content_str) # 调用函数解析成份字段

            # 获取价格，并处理可能为空的情况
            white_price = extract_float_from_string(row_data.get('白色（元）')) # 获取白色价格，如果为空则默认为0
            color_price = extract_float_from_string(row_data.get('彩色（元）')) # 获取彩色价格，如果为空则默认为0
            sample_price = extract_float_from_string(row_data.get('版布价')) # 获取版布价，如果为空则默认为0
            empty_difference = extract_persent_from_string(row_data.get('空差')) # 获取空差，如果为空则默认为0

            # 计算 price 字段
            calculated_price = 0.0 # 初始化计算后的价格
            if color_price == 0: # 如果彩色价格为0
                calculated_price = white_price # 则使用白色价格
            elif empty_difference != 0: # 否则，如果空差不为0
                calculated_price = round(color_price / empty_difference * 100, 2) # 计算价格并保留两位小数

            # 提取用于生成 keywords 的字段
            keywords = [product_fullname,f'{colors}色'] # 初始化一个空列表来存储关键词部分
            for key in ['编号', '品名名称', '幅宽（cm）', '克重（g）', '成份']: # 遍历需要提取的关键词字段
                value = row_data.get(key) # 获取字段值
                if value is not None: # 如果值不为空
                    keywords.append(str(value).replace('、', '').strip()) # 将值转换为字符串并去除空白，添加到列表中

            # 获取幅宽和克重
            width_val = int(extract_float_from_string(row_data.get('幅宽（cm）'))) # 获取并转换幅宽为整数
            weight_val = int(extract_float_from_string(row_data.get('克重（g）'))) # 获取并转换克重为整数

            # 计算公斤出米数 (100000 / (幅宽 * 克重))
            meters_per_kg = 0.0 # 初始化公斤出米数为0.0
            if width_val > 0 and weight_val > 0: # 如果幅宽和克重都大于0
                meters_per_kg = round(100000 / (width_val * weight_val), 2) # 计算公斤出米数并保留两位小数

            # 定义类别英文映射表
            category_map = {"乐丽丝": "L", "天丝": "T", "仿牛仔": "N", "绣花印花底布": "X", "棉布": "M"}
            # 获取类别对应的英文字母前缀
            category_prefix = category_map.get(category, "")
            # 去除产品编号中的#号
            clean_product_no = product_no.replace('#', '')
            # 将去除#号后的产品编号倒序排列
            reversed_product_no = clean_product_no[::-1]
            # 拼接英文字母前缀和倒序后的产品编号生成myid
            myid = f"{category_prefix}{reversed_product_no}"

            product = { # 构建产品字典
                "id": f"prod-{product_no.replace('#', '')}", # 生成产品ID
                "myid": myid, # 拼接生成的自定义ID
                "productNo": product_no, # 产品编号
                "name": product_name, # 产品名称
                "fullname": product_fullname, # 产品全名
                "slug": slugify(product_name), # 生成产品slug
                "description": "", # 描述默认为空
                "whitePrice": white_price, # 白色价格
                "colorPrice": color_price, # 彩色价格
                "samplePrice": sample_price, # 样品价格
                "fullPrice": calculated_price, # 足米价格
                "images": images, # 图片列表
                "category": category, # 类别
                "type": type, # 面料类型
                "content": parsed_content, # 成份列表
                "tags": [], # 标签列表默认为空
                "inStock": True, # 是否有库存默认为True
                "width": width_val, # 幅宽
                "weight": weight_val, # 克重
                "metersPerKg": meters_per_kg, # 公斤出米数
                "empty": empty_difference, # 空差
                "keywords": keywords, # 关键词
                "colors": colors, # 颜色数量
                "updatedAt": datetime.now().strftime("%Y-%m-%d"), # 更新日期为当前日期
                "featured": False # 是否特色产品默认为False
            }
            all_products.append(product) # 将产品添加到列表中

    except FileNotFoundError:
        print(f"Error: Excel file not found at {excel_file_path}") # 打印文件未找到错误
    except Exception as e:
        print(f"An unexpected error occurred: {e}") # 打印其他意外错误
    finally:
        with open(output_json_file_path, 'w', encoding='utf-8') as f: # 最后将所有产品写入JSON文件
            json.dump(all_products, f, ensure_ascii=False, indent=4) # 使用UTF-8编码和4空格缩进写入JSON
        print(f"All products saved to {output_json_file_path}") # 打印保存成功的消息



if __name__ == "__main__": # 当脚本作为主程序运行时
    excel_file = "./input.xlsx" # 定义输入Excel文件路径
    output_json = "./products.json" # 定义输出JSON文件路径
    process_excel(excel_file, output_json) # 调用处理Excel和聊天的函数
