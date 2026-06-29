# 导入 json 模块用于处理和保存 JSON 数据
import json
# 导入深层翻译库的 Google 翻译器 (已通过 context7 检索确认 deep-translator 库)
from deep_translator import GoogleTranslator

# 定义一个本地化翻译字典，支持多种语言的静态映射
LOCAL_DICT = {
    # 英语字典配置
    "en": {
        # 天丝的翻译
        "天丝": "Tencel",
        # 乐丽丝的翻译
        "乐丽丝": "Lelis",
        # 面料的翻译
        "面料": "Fabric",
        # 粘胶纤维的翻译
        "粘": "Viscose",
        # 苎麻的翻译
        "苎麻": "Ramie",
        # 氨纶的翻译
        "氨纶": "Spandex",
        # 棉的翻译
        "棉": "Cotton",
        # 尼龙的翻译
        "尼龙": "Nylon",
        # 亚麻的翻译
        "亚麻": "Linen",
        # 锦纶的翻译
        "锦纶": "Nylon",
        # 醋酸纤维的翻译
        "醋酸": "Acetate",
        # 麻的翻译
        "麻": "Hemp/Linen",
        # 仿牛仔的翻译
        "仿牛仔": "Faux Denim",
        # 绣花印花底布的翻译
        "绣花印花底布": "Embroidery Print Base",
        # 人棉的翻译
        "人棉": "Rayon",
        # 聚酯纤维的翻译
        "聚酯纤维": "Polyester Fiber",
        # 涤纶的翻译
        "涤纶": "Polyester",
        # 棉布的翻译
        "棉布": "Cotton Fabric"
    },
    # 越南语字典配置
    "vi": {
        # 天丝的翻译
        "天丝": "Tencel",
        # 乐丽丝的翻译
        "乐丽丝": "Lelis",
        # 面料的翻译
        "面料": "Vải",
        # 粘胶纤维的翻译
        "粘": "Viscose",
        # 苎麻的翻译
        "苎麻": "Ramie",
        # 氨纶的翻译
        "氨纶": "Spandex",
        # 棉的翻译
        "棉": "Bông",
        # 尼龙的翻译
        "尼龙": "Nylon",
        # 亚麻的翻译
        "亚麻": "Vải lanh",
        # 锦纶的翻译
        "锦纶": "Nylon",
        # 醋酸纤维的翻译
        "醋酸": "Acetate",
        # 麻的翻译
        "麻": "Hemp/Linen",
        # 仿牛仔的翻译
        "仿牛仔": "Giả denim",
        # 绣花印花底布的翻译
        "绣花印花底布": "Vải nền thêu in",
        # 人棉的翻译
        "人棉": "Rayon",
        # 聚酯纤维的翻译
        "聚酯纤维": "Sợi polyester",
        # 涤纶的翻译
        "涤纶": "Polyester",
        # 棉布的翻译
        "棉布": "Vải cotton"
    }
}

# 定义翻译辅助函数，接受文本、目标语言、语言字典以及是否使用在线翻译的标志
def translate_text(text, target_lang="en", lang_dict=None, use_online=True):
    # 如果文本为空，直接返回空字符串
    if not text: return text
    # 如果提供了字典且文本在字典中，直接返回字典中的翻译以保证一致性和速度
    if lang_dict and text in lang_dict: return lang_dict[text]
    # 如果指定不使用在线翻译，则直接返回原文
    if not use_online: return text
    # 尝试使用机器翻译处理字典中没有的动态文本
    try:
        # 调用 Google 翻译器将文本翻译为目标语言
        return GoogleTranslator(source='auto', target=target_lang).translate(text)
    # 捕获可能的网络或翻译异常
    except Exception as e:
        # 如果翻译失败，打印错误信息
        print(f"Translate error for '{text}': {e}")
        # 失败时返回原文
        return text

# 定义一个函数，用于提取产品列表中需要放入字典翻译的特定字段值并去重
def extract_unique_dict_keys(products):
    # 使用 set 集合来存储提取出的唯一词汇，自动去重
    unique_keys = set()
    # 遍历产品列表中的每一个产品字典
    for product in products:
        # 如果产品包含分类信息，将其添加到集合中
        if "category" in product and product["category"]:
            unique_keys.add(product["category"])
        # 如果产品包含类型信息，将其添加到集合中
        if "type" in product and product["type"]:
            unique_keys.add(product["type"])
        # 遍历产品的内容成分列表
        for content_item in product.get("content", []):
            # 如果成分包含名称信息，将其添加到集合中
            if "name" in content_item and content_item["name"]:
                unique_keys.add(content_item["name"])
    # 将去重后的集合转换为列表返回
    return list(unique_keys)

# 定义主翻译函数，接受产品列表和目标语言
def translate_products(products, target_lang="en"):
    # 获取目标语言的本地字典，如果不支持则默认为空字典
    lang_dict = LOCAL_DICT.get(target_lang, {})
    # 获取产品列表的总长度，用于计算进度
    total = len(products)
    # 遍历产品列表中的每一个产品字典，同时获取其索引
    for index, product in enumerate(products):
        # 打印当前处理的进度信息，包含序号和产品编号
        print(f"进度: [{index + 1}/{total}] 正在处理产品: {product.get('productNo', '')}")
        
        # 翻译产品名称，保留原有编号、价钱、图片列表不变，允许在线翻译
        product["name"] = translate_text(product.get("name", ""), target_lang, lang_dict, use_online=True)
        # 翻译产品全称，允许在线翻译
        product["fullname"] = translate_text(product.get("fullname", ""), target_lang, lang_dict, use_online=True)
        # 翻译产品描述，允许在线翻译
        product["description"] = translate_text(product.get("description", ""), target_lang, lang_dict, use_online=True)
        
        # 翻译产品分类，仅使用本地字典不调用在线翻译
        product["category"] = translate_text(product.get("category", ""), target_lang, lang_dict, use_online=False)
        # 翻译产品类型，仅使用本地字典不调用在线翻译
        product["type"] = translate_text(product.get("type", ""), target_lang, lang_dict, use_online=False)
        
        # 遍历产品内容成分列表
        for content_item in product.get("content", []):
            # 翻译成分名称，保留百分比等数字不变，仅使用本地字典
            content_item["name"] = translate_text(content_item.get("name", ""), target_lang, lang_dict, use_online=False)
            
        # 如果产品包含关键字列表
        if "keywords" in product:
            # 使用列表推导式翻译所有关键字，仅使用本地字典
            product["keywords"] = [translate_text(kw, target_lang, lang_dict, use_online=False) for kw in product["keywords"]]
            
    # 返回翻译后被就地修改的产品列表
    return products

# 定义测试执行的主函数块
if __name__ == "__main__":

    # 第一步：生成一个越南版的字典

    # 第二步：指定原始 JSON 文件的路径
    input_file = r"c:\develop\nanobot\skills\qianyi-product\products.json"
    # 指定输出 JSON 文件的路径
    output_file = r"c:\develop\nanobot\skills\qianyi-product\products_vi.json"
    
    # 打开原始文件并读取内容
    with open(input_file, 'r', encoding='utf-8') as f:
        # 解析 JSON 数据到变量中
        data = json.load(f)
    """       
    # 调用提取去重函数，获取所有的 category、type 和 content name
    unique_terms = extract_unique_dict_keys(data)
    # 打印去重后的词汇列表
    print("需要补充到本地字典中的去重词汇列表：")
    print(json.dumps(unique_terms, ensure_ascii=False, indent=4))

    """    
    # 调用翻译函数处理前几个产品进行测试，目标语言设为英文
    translated_data = translate_products(data, target_lang="vi")
    
    # 打开输出文件准备写入翻译后的内容
    with open(output_file, 'w', encoding='utf-8') as f:
        # 将翻译后的数据格式化为 JSON 并保存，保留非 ASCII 字符并美化缩进
        json.dump(translated_data, f, ensure_ascii=False, indent=4)
        
    # 打印完成提示信息
    print(f"Translation completed. Saved to {output_file}")
