
import os
import tempfile # 导入tempfile模块用于创建临时文件
# 从PIL库中导入Image、ImageDraw和ImageFont模块用于图像处理和文字绘制
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from moviepy.editor import ImageClip, VideoFileClip, concatenate_videoclips, CompositeVideoClip # 从moviepy.editor导入所需的类和函数
import requests
import base64
import mimetypes
import json
import shutil # 导入shutil模块用于文件操作
from openai import OpenAI
from dotenv import load_dotenv
load_dotenv()
JIEKOU_API_KEY = os.getenv("JIEKOU_API_KEY")

PRODUCT_HOME_PATH = os.path.dirname(os.path.abspath(__file__))


def encode_base64(file_path):
        # 如果输入已经是Base64格式（以data:image开头），直接返回
    if file_path.startswith("data:image"):
        return file_path
    mime_type, _ = mimetypes.guess_type(file_path)
    if not mime_type or not mime_type.startswith("image/"):
        raise ValueError("不支持或无法识别的图像格式")
    with open(file_path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
    return f"data:{mime_type};base64,{encoded_string}"
# 定义合成图片函数，输入背景图、前景图绝对路径，以及标题、副标题，返回输出图片的绝对路径
def _overlay_images(bg_path, fg_path, frame_path="", title="", subtitle=""):
    print(bg_path, fg_path, frame_path, title, subtitle)
    
    # 检查背景图是否存在，如果不存在则直接跳过并返回None
    if not bg_path or not os.path.exists(bg_path):
        print(f"背景图片不存在: {bg_path}，跳过合成")
        return None
        
    # 检查前景图是否存在，如果不存在则直接跳过并返回None
    if not fg_path or not os.path.exists(fg_path):
        print(f"前景图片不存在: {fg_path}，跳过合成")
        return None
        
    # 根据背景图路径生成默认的输出图片路径
    output_path = os.path.join(os.path.dirname(bg_path), "index.png")
    # 打开第一张（背景）图片并转换为RGBA模式
    bg_img = Image.open(bg_path).convert("RGBA")
    # 打开第二张（前景）图片并转换为RGBA模式
    fg_img = Image.open(fg_path).convert("RGBA")
    # 获取背景图片的宽度
    bg_width = bg_img.width
    # 获取背景图片的高度
    bg_height = bg_img.height
    # 计算前景图的目标宽度为背景图的五分之一
    new_fg_width = bg_width // 5
    # 按照前景图的宽高比计算缩放后的目标高度
    new_fg_height = int(fg_img.height * (new_fg_width / fg_img.width))
    # 使用缩放尺寸对前景图进行缩小操作
    fg_img = fg_img.resize((new_fg_width, new_fg_height), Image.LANCZOS)
    # 重新获取缩小后前景图片的宽度
    fg_width = fg_img.width
    # 计算水平居中的X坐标
    pos_x = (bg_width - fg_width) // 2
    # 垂直方向放在距离背景图顶部十分之一的位置
    pos_y = bg_height // 10
    
    # 边框不为空时，叠加在背景上面，前景下面，且居下居中
    if frame_path and os.path.exists(frame_path):
        frame_img = Image.open(frame_path).convert("RGBA")
        frame_x = (bg_width - frame_img.width) // 2
        frame_y = bg_height - frame_img.height
        bg_img.paste(frame_img, (frame_x, frame_y), mask=frame_img)
        
    # 将第二张图片粘贴到第一张图片上，并使用自身的alpha通道作为遮罩
    bg_img.paste(fg_img, (pos_x, pos_y), mask=fg_img)
    # 判断是否传入了标题或副标题参数，如果有则进行绘制
    if title or subtitle:
        # 创建ImageDraw对象用于在背景图上绘图
        draw = ImageDraw.Draw(bg_img)
        # 计算主标题字体大小，高度为图1的十分之一，再缩小为原来的0.6倍
        font_size = int((bg_height // 10) * 0.6)
        # 计算副标题的字体大小，设定为主标题的一半再增大50%（即图1的十分之一乘以0.5乘以1.5），也缩小为0.6倍
        font_size_subtitle = int((bg_height // 20) * 1.5 * 0.6)
        # 尝试加载支持中文的字体（全部使用微软雅黑）
        try:
            # 加载主标题微软雅黑粗体（通常为msyhbd.ttc），实现加粗效果
            font = ImageFont.truetype("msyhbd.ttc", font_size)
        except IOError:
            try:
                # 降级尝试加载普通微软雅黑字体作为主标题
                font = ImageFont.truetype("msyh.ttc", font_size)
            except IOError:
                # 降级使用默认字体作为主标题
                font = ImageFont.load_default()
        
        try:
            # 加载副标题微软雅黑字体，字号增大50%
            font_subtitle = ImageFont.truetype("msyh.ttc", font_size_subtitle)
        except IOError:
            # 降级使用默认字体作为副标题
            font_subtitle = ImageFont.load_default()
        
        # 计算副标题高度（如果有）以便整体底部对齐
        sub_height = 0
        if subtitle:
            bbox_sub = draw.textbbox((0, 0), subtitle, font=font_subtitle)
            sub_width = bbox_sub[2] - bbox_sub[0]
            sub_height = bbox_sub[3] - bbox_sub[1]

        # 判断是否传入了标题参数，如果有则绘制标题
        if title:
            # 获取主标题文字的边界框
            bbox = draw.textbbox((0, 0), title, font=font)
            # 计算主标题文字的宽度
            text_width = bbox[2] - bbox[0]
            # 计算主标题文字的高度
            text_height = bbox[3] - bbox[1]
            # 计算主标题文字右对齐的X坐标，离右边距40px
            text_x = bg_width - text_width - 40
            
            # 修改标题的位置 放在离底部40px 的地方（如果有副标题则在副标题上方）
            if subtitle:
                text_y = bg_height - sub_height - (bg_height // 20) - text_height - 40
            else:
                text_y = bg_height - text_height - 40
                
            # 计算主标题阴影的水平左偏移量，按字体大小比例计算且至少偏移2像素
            shadow_x = text_x - max(2, font_size // 20)
            # 计算主标题阴影的垂直下偏移量，按字体大小比例计算且至少偏移2像素
            shadow_y = text_y + max(2, font_size // 20)
            # 在背景图上绘制左下角黑色主标题阴影文字
            draw.text((shadow_x, shadow_y), title, fill=(0, 0, 0, 255), font=font)
            # 在背景图上绘制白色主标题文字
            draw.text((text_x, text_y), title, fill=(255, 255, 255, 255), font=font)
            # 更新主标题底部的Y坐标，为副标题提供相对位置
            title_bottom_y = text_y + text_height
        else:
            title_bottom_y = bg_height - sub_height - 40 - (bg_height // 20)
            
        # 判断是否传入了副标题参数，如果有则绘制副标题
        if subtitle:
            # 计算副标题文字右对齐的X坐标，离右边距40px
            sub_x = bg_width - sub_width - 40
            # 计算副标题文字垂直坐标，放置在主标题下方
            if title:
                sub_y = title_bottom_y + (bg_height // 20)
            else:
                sub_y = bg_height - sub_height - 40
            
            # 绘制副标题阴影
            sub_shadow_x = sub_x - max(2, font_size_subtitle // 20)
            sub_shadow_y = sub_y + max(2, font_size_subtitle // 20)
            draw.text((sub_shadow_x, sub_shadow_y), subtitle, fill=(0, 0, 0, 255), font=font_subtitle)
            # 绘制白色副标题
            draw.text((sub_x, sub_y), subtitle, fill=(255, 255, 255, 255), font=font_subtitle)

    # 将合成后的图片保存到输出路径
    bg_img.save(output_path)
    # 返回生成图片的绝对路径
    return os.path.abspath(output_path)

def _download_images(response_text: str, prefix: str = "jiekou", out_dir: str = None, filename:str = "0") -> list[str]: # 定义下载图片到本地的辅助函数
    if out_dir is None: # 如果没有传入out_dir参数
        out_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products") # 使用PRODUCT_HOME_PATH构造绝对路径作为默认输出目录
    if not response_text: # 如果响应文本为空则直接返回空列表
        return [] # 返回空列表
    try: # 开始尝试解析JSON并下载
        data = json.loads(response_text) if isinstance(response_text, str) else response_text # 如果输入是字符串则解析JSON，否则直接使用
        raw_images = data.get("images", []) # 获取响应中的图片数据列表
        image_urls = [] # 初始化图片URL列表
        for img in raw_images: # 遍历原始图片数据
            if isinstance(img, str): # 如果元素是字符串（直接是URL）
                image_urls.append(img) # 直接添加到URL列表
            elif isinstance(img, dict) and img.get("url"): # 如果是字典且包含url键
                image_urls.append(img.get("url")) # 提取url并添加到列表
        out_dir = os.path.join(out_dir, prefix) # 确保路径是绝对路径
        if not os.path.exists(out_dir): # 如果输出目录不存在
            os.makedirs(out_dir) # 递归创建输出目录
        saved_paths = [] # 初始化保存路径列表
        for i, url in enumerate(image_urls): # 遍历图片链接列表
            try: # 尝试下载单张图片
                res = requests.get(url) # 发送GET请求获取图片内容
                res.raise_for_status() # 检查请求是否成功
                file_name = f"{filename}{i}.png" # 构造本地文件名
                file_path = os.path.join(out_dir, file_name) # 拼接完整文件路径
                with open(file_path, "wb") as f: # 以二进制写模式打开文件
                    f.write(res.content) # 写入图片二进制数据
                saved_paths.append(file_path.replace("\\", "/")) # 将路径存入列表并统一使用正斜杠
            except Exception as e: # 捕获单张图片下载异常
                print(f"Failed to download {url}: {e}") # 打印下载失败信息
        return saved_paths # 返回成功保存的所有图片路径列表
    except Exception as e: # 捕获整体处理异常
        print(f"Error in download_images: {e}") # 打印处理错误信息
        return [] # 返回空列表

def _jiekou_gpt_image(prompt: str, prefix: str, filename:str, n: int = 1, size: str = "1536x1024", quality: str = "low", background: str = "auto", moderation: str = "auto", output_format: str = "png") -> list[str]: # 定义生成GPT图片的接口函数并返回路径列表
    url = "https://api.jiekou.ai/v3/gpt-image-2-text-to-image" # 设置接口请求的URL地址
    payload = { # 构造请求的载荷数据字典
        "n": n, # 设置生成图片的数量
        "size": size, # 设置图片的尺寸规格
        "prompt": prompt, # 设置生成图片的提示词
        "quality": quality, # 设置生成图片的质量级别
        "background": background, # 设置背景处理模式
        "moderation": moderation, # 设置内容审核模式
        "output_format": output_format # 设置输出图片的格式
    } # 结束载荷字典的定义
    headers = { # 构造请求的头部信息字典
        "Content-Type": "application/json", # 指定请求内容类型为JSON格式
        "Authorization": f"Bearer {JIEKOU_API_KEY}" # 设置API授权令牌
    } # 结束头部字典的定义
    try: # 开始尝试执行网络请求
        response = requests.post(url, json=payload, headers=headers) # 发送POST请求并获取响应
        response.raise_for_status() # 如果响应状态码不是200则抛出异常
        print(response.text) # 在控制台打印接口返回的原始文本
        return _download_images(response.text, prefix=prefix,filename=filename) # 解析响应并下载图片到本地，返回路径列表
    except Exception as e: # 捕获请求过程中的异常
        print(f"Error calling jiekou_gpt_image: {e}") # 打印详细的错误描述
        return None # 发生错误时返回空值

def _jiekou_gpt_image_edit(image_path: str, prompt: str, prefix: str, mask_path: str = None, n: int = 1, size: str = "1536x1024", quality: str = "low", background: str = "auto", output_format: str = "png",filename:str="0") -> list[str]: # 定义编辑GPT图片的接口函数并返回路径列表
    url = "https://api.jiekou.ai/v3/gpt-image-2-edit" # 设置编辑图片的接口URL
    payload = { # 初始化请求载荷字典
        "n": n, # 设置生成的图片数量
        "prompt": prompt, # 设置修改图片的提示词
        "image": encode_base64(image_path), # 调用encode_base64编码主图文件
        "size": size, # 设置生成的图片尺寸
        "quality": quality, # 设置生成的图片质量
        "background": background, # 设置图片的背景模式
        "output_format": output_format # 设置最终输出的文件格式
    } # 结束基本载荷字典的定义
    if mask_path: # 判断是否提供了蒙版文件路径
        payload["mask"] = encode_base64(mask_path) # 编码蒙版图片并添加到载荷中
    headers = { # 构造HTTP请求头字典
        "Content-Type": "application/json", # 设置请求体格式为JSON
        "Authorization": f"Bearer {JIEKOU_API_KEY}" # 配置API访问授权令牌
    } # 结束请求头字典的定义
    try: # 进入网络请求尝试块
        response = requests.post(url, json=payload, headers=headers) # 发起POST异步请求，禁用代理设置
        response.raise_for_status() # 验证HTTP响应状态是否正常
        print(response.text) # 在终端打印接口返回的原始数据
        return _download_images(response.text, prefix=prefix,filename=filename) # 调用辅助函数将返回的图片保存至本地并返回路径
    except Exception as e: # 捕获所有可能的运行异常
        print(f"Error calling jiekou_gpt_image_edit: {e}") # 输出详细的错误调用日志
        return None # 遇到错误时统一返回空值

def _jiekou_chat(system_prompt: str, user_prompt: str,model: str = "claude-opus-4-8-r") -> None:
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

        return response

    except Exception as e:
        print(f"Error: {e}")

import random # 导入random模块用于随机选择场景

def generate_product_image(target_product: dict, envword: str = None, reference_image_filename: str = None) -> str: # 定义根据产品编号生成商品首图的方法，reference_image_filename为指定参考图的文件名
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成首图") # 如果为空，打印跳过提示
        return None # 直接返回 None 结束方法

    if not envword: # 如果envword为空或未填
        scenes = [ # 定义场景数组
            "绿意草坪与法式野餐", # 场景1
            "露天咖啡馆", # 场景2
            "波光粼粼的泳池畔", # 场景3
            "活力网球场", # 场景4
            "繁花秘境", # 场景5
            "海滨沙滩与礁石", # 场景6
            "植物园", # 场景8
            "玻璃温室", # 场景9
            "天台落日余晖" # 场景10
        ] # 结束场景数组定义
        envword = random.choice(scenes) # 随机选择一个场景作为环境变量
    product_no = target_product.get("productNo", "").replace("#", "") # 获取产品的编号
    abs_img_path = None # 初始化最终找到的有效绝对路径为None
    if reference_image_filename: # 如果指定了参考图文件名
        temp_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, reference_image_filename) # 拼接指定参考图的绝对路径
        if os.path.exists(temp_path): # 检查该绝对路径对应的图片文件是否存在
            abs_img_path = temp_path # 如果存在则赋值给最终路径变量
    else: # 如果没有指定参考图文件名，则按原有逻辑遍历
        images_in_product_dir = [] # 初始化一个列表来存储产品目录下的所有图片
        product_no_for_path = target_product.get("productNo", "").replace("#", "") # 获取产品编号用于构建路径
        product_image_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no_for_path) # 拼接产品图片目录的绝对路径

        if os.path.exists(product_image_dir): # 检查产品图片目录是否存在
            for f in os.listdir(product_image_dir): # 遍历目录下的所有文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.jpg', '.jpeg', '.png']: # 检查是否是数字命名的图片文件
                    images_in_product_dir.append((int(name), os.path.join(product_image_dir, f))) # 将(数字文件名, 绝对路径)添加到列表中

        if images_in_product_dir: # 如果找到了数字命名的图片
            images_in_product_dir.sort(key=lambda x: x[0], reverse=True) # 按数字文件名降序排序
            abs_img_path = images_in_product_dir[0][1] # 选择数字最大的图片作为abs_img_path
        else: # 如果没有找到数字命名的图片
            print(f"产品 {target_product.get('productNo', '')} 的产品目录下没有找到数字命名的图片") # 打印提示信息
            return None # 返回None表示获取图片失败
    model_index_path = os.path.join(PRODUCT_HOME_PATH,"model_index.jpg")
    
    if not abs_img_path: # 如果遍历完所有图片仍未找到有效路径
        print(f"产品 {target_product.get('productNo', '')} 的所有参考图片均不存在") # 打印无法找到图片的错误信息
        return None # 返回None表示获取图片失败

    # --- 新增：合并图片逻辑 ---
    merged_image_path = _merge_images(abs_img_path, model_index_path) # 调用私有方法合并图片
    if merged_image_path is None: # 如果合并图片失败
        print("合并图片失败，跳过生成商品展示图") # 打印错误信息
        return None # 返回None表示生成失败

    try: # 尝试调用接口编辑图片
        print(f"图片合并成功，临时文件路径: {merged_image_path}") # 打印合并成功信息

        prompt = f"""左图是面料色卡，取参考图上面料细致纹理与质感，搭配3-4多巴胺颜色，
        采用抓捏、悬挂或自然堆叠的方式，让面料产生自然的褶皱和阴影，利用侧逆光拍摄，
        参考右图，拍出面料轻薄透气，背景是{envword}，不要出现文字或标签，生成面料占95%的广告商品展示图  """ # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1024", # 设置生成的图片尺寸
            prefix=product_no # 传入前缀，用于保存文件命名
        ) # 结束接口调用
    finally: # 确保临时文件被删除
        if merged_image_path and os.path.exists(merged_image_path): # 如果临时文件存在
            os.remove(merged_image_path) # 删除临时文件
            print(f"临时文件已删除: {merged_image_path}") # 打印删除信息

    if generated_paths and len(generated_paths) > 0: # 判断是否成功生成图片
        generated_image_path = generated_paths[0] # 获取第一张生成图片的路径作为商品首图
        print(f"生成商品展示图成功: {generated_image_path}")
        return generated_image_path # 返回 商品首图路径
    elif generated_paths is None: # 如果生成失败
        print("生成商品首图失败") # 打印失败提示
        return None # 返回空值

def _merge_images(img1_path: str, img2_path: str) -> str: # 定义私有方法合并图片
    merged_image_path = None # 初始化合并图片路径
    try: # 尝试合并图片
        # 打开两张图片
        img1 = Image.open(img1_path).convert("RGBA") # 打开第一张图片并转换为RGBA模式
        img2 = Image.open(img2_path).convert("RGBA") # 打开第二张图片并转换为RGBA模式

        # 调整第二张图片的高度与第一张图片相同，并保持比例
        if img2.height != img1.height: # 如果两张图片高度不同
            img2_width, img2_height = img2.size # 获取第二张图片的宽度和高度
            aspect_ratio = img2_width / img2_height # 计算宽高比
            new_img2_height = img1.height # 新高度与第一张图片相同
            new_img2_width = int(new_img2_height * aspect_ratio) # 根据比例计算新宽度
            img2 = img2.resize((new_img2_width, new_img2_height), Image.LANCZOS) # 调整图片大小

        # 创建一张新的图片，宽度为两张图片宽度之和，高度为第一张图片的高度
        merged_width = img1.width + img2.width # 计算合并后的总宽度
        merged_height = img1.height # 合并后的高度与第一张图片相同
        merged_img = Image.new("RGBA", (merged_width, merged_height)) # 创建新的空白图片

        # 将两张图片粘贴到新图片上
        merged_img.paste(img1, (0, 0)) # 将第一张图片粘贴到左侧
        merged_img.paste(img2, (img1.width, 0)) # 将第二张图片粘贴到第一张图片右侧

        # 保存合并后的图片到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png") # 创建一个临时文件
        merged_image_path = temp_file.name # 获取临时文件路径
        merged_img.save(merged_image_path) # 保存合并后的图片到临时文件
        temp_file.close() # 关闭临时文件句柄

        print(f"图片合并成功，临时文件路径: {merged_image_path}") # 打印合并成功信息
        return merged_image_path # 返回合并后的图片路径
    except Exception as e: # 捕获合并图片过程中的异常
        print(f"合并图片时出错: {e}") # 打印异常信息
        return None # 返回None表示合并图片失败



def generate_product_part30_image(target_product: dict, envword: str = None, reference_image_filename: str = None) -> str: # 定义根据产品编号生成商品首图的方法，reference_image_filename为指定参考图的文件名
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成首图") # 如果为空，打印跳过提示
        return None # 直接返回 None 结束方法

    if not envword: # 如果envword为空或未填
        scenes = [ # 定义场景数组
            "#FFD700", # 场景1
            "#FF1493", # 场景2
            "#002FA7", # 场景3
            "#32CD32", # 场景4
            "#FF4500", # 场景5
            "#8A2BE2", # 场景6
            "#FF8C69", # 场景9
            "#FF007F" # 场景10
        ] # 结束场景数组定义
        envword = random.choice(scenes) # 随机选择一个场景作为环境变量
    product_no = target_product.get("productNo", "").replace("#", "") # 获取产品的编号
    abs_img_path = None # 初始化最终找到的有效绝对路径为None
    if reference_image_filename: # 如果指定了参考图文件名
        temp_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, reference_image_filename) # 拼接指定参考图的绝对路径
        if os.path.exists(temp_path): # 检查该绝对路径对应的图片文件是否存在
            abs_img_path = temp_path # 如果存在则赋值给最终路径变量
    else: # 如果没有指定参考图文件名，则按原有逻辑遍历
        images_in_product_dir = [] # 初始化一个列表来存储产品目录下的所有图片
        product_no_for_path = target_product.get("productNo", "").replace("#", "") # 获取产品编号用于构建路径
        product_image_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no_for_path) # 拼接产品图片目录的绝对路径

        if os.path.exists(product_image_dir): # 检查产品图片目录是否存在
            for f in os.listdir(product_image_dir): # 遍历目录下的所有文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.jpg', '.jpeg', '.png']: # 检查是否是数字命名的图片文件
                    images_in_product_dir.append((int(name), os.path.join(product_image_dir, f))) # 将(数字文件名, 绝对路径)添加到列表中

        if images_in_product_dir: # 如果找到了数字命名的图片
            images_in_product_dir.sort(key=lambda x: x[0], reverse=True) # 按数字文件名降序排序
            abs_img_path = images_in_product_dir[0][1] # 选择数字最大的图片作为abs_img_path
        else: # 如果没有找到数字命名的图片
            print(f"产品 {target_product.get('productNo', '')} 的产品目录下没有找到数字命名的图片") # 打印提示信息
            return None # 返回None表示获取图片失败
    model_index_path = os.path.join(PRODUCT_HOME_PATH,"model_01.png")
    
    if not abs_img_path: # 如果遍历完所有图片仍未找到有效路径
        print(f"产品 {target_product.get('productNo', '')} 的所有参考图片均不存在") # 打印无法找到图片的错误信息
        return None # 返回None表示获取图片失败

    # --- 新增：合并图片逻辑 ---
    merged_image_path = None # 初始化合并图片路径
    try: # 尝试合并图片
        # 打开两张图片
        img1 = Image.open(abs_img_path).convert("RGBA") # 打开第一张图片并转换为RGBA模式
        img2 = Image.open(model_index_path).convert("RGBA") # 打开第二张图片并转换为RGBA模式

        # 调整第二张图片的高度与第一张图片相同，并保持比例
        if img2.height != img1.height: # 如果两张图片高度不同
            img2_width, img2_height = img2.size # 获取第二张图片的宽度和高度
            aspect_ratio = img2_width / img2_height # 计算宽高比
            new_img2_height = img1.height # 新高度与第一张图片相同
            new_img2_width = int(new_img2_height * aspect_ratio) # 根据比例计算新宽度
            img2 = img2.resize((new_img2_width, new_img2_height), Image.LANCZOS) # 调整图片大小

        # 创建一张新的图片，宽度为两张图片宽度之和，高度为第一张图片的高度
        merged_width = img1.width + img2.width # 计算合并后的总宽度
        merged_height = img1.height # 合并后的高度与第一张图片相同
        merged_img = Image.new("RGBA", (merged_width, merged_height)) # 创建新的空白图片

        # 将两张图片粘贴到新图片上
        merged_img.paste(img1, (0, 0)) # 将第一张图片粘贴到左侧
        merged_img.paste(img2, (img1.width, 0)) # 将第二张图片粘贴到第一张图片右侧

        # 保存合并后的图片到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png") # 创建一个临时文件
        merged_image_path = temp_file.name # 获取临时文件路径
        merged_img.save(merged_image_path) # 保存合并后的图片到临时文件
        temp_file.close() # 关闭临时文件句柄

        print(f"图片合并成功，临时文件路径: {merged_image_path}") # 打印合并成功信息

        prompt = f"""生成商品展示页，要求如下：
            1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}，文案要与面料相关，不能与面料无关
            2、参考右图的结构，生成对应的面料细节展示图，采用抓捏、悬挂或自然堆叠的方式，让面料产生自然的褶皱和阴影，利用侧逆光拍摄，保持一致的纹理与轻薄度
            3、采用简约风格与绿色为主题
            4、不可使用参考左图与右图原图, 不可使用任何品牌
            """ # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1536", # 设置生成的图片尺寸
            prefix=product_no, 
            filename="part3", # 传入前缀，用于保存文件命名
        ) 
        # 结束接口调用
    finally: # 确保临时文件被删除
        if merged_image_path and os.path.exists(merged_image_path): # 如果临时文件存在
            os.remove(merged_image_path) # 删除临时文件
            print(f"临时文件已删除: {merged_image_path}") # 打印删除信息
    return envword # 返回空值

def generate_product_part40_image(target_product: dict, envword: str = None, reference_image_filename: str = None) -> str: # 定义根据产品编号生成商品首图的方法，reference_image_filename为指定参考图的文件名
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成首图") # 如果为空，打印跳过提示
        return None # 直接返回 None 结束方法

    if not envword: # 如果envword为空或未填
        scenes = [ # 定义场景数组
            "#FFD700", # 场景1
            "#FF1493", # 场景2
            "#002FA7", # 场景3
            "#32CD32", # 场景4
            "#FF4500", # 场景5
            "#8A2BE2", # 场景6
            "#FF8C69", # 场景9
            "#FF007F" # 场景10
        ] # 结束场景数组定义
        envword = random.choice(scenes) # 随机选择一个场景作为环境变量
    product_no = target_product.get("productNo", "").replace("#", "") # 获取产品的编号
    abs_img_path = None # 初始化最终找到的有效绝对路径为None
    if reference_image_filename: # 如果指定了参考图文件名
        temp_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, reference_image_filename) # 拼接指定参考图的绝对路径
        if os.path.exists(temp_path): # 检查该绝对路径对应的图片文件是否存在
            abs_img_path = temp_path # 如果存在则赋值给最终路径变量
    else: # 如果没有指定参考图文件名，则按原有逻辑遍历
        images_in_product_dir = [] # 初始化一个列表来存储产品目录下的所有图片
        product_no_for_path = target_product.get("productNo", "").replace("#", "") # 获取产品编号用于构建路径
        product_image_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no_for_path) # 拼接产品图片目录的绝对路径

        if os.path.exists(product_image_dir): # 检查产品图片目录是否存在
            for f in os.listdir(product_image_dir): # 遍历目录下的所有文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.jpg', '.jpeg', '.png']: # 检查是否是数字命名的图片文件
                    images_in_product_dir.append((int(name), os.path.join(product_image_dir, f))) # 将(数字文件名, 绝对路径)添加到列表中

        if images_in_product_dir: # 如果找到了数字命名的图片
            images_in_product_dir.sort(key=lambda x: x[0], reverse=True) # 按数字文件名降序排序
            abs_img_path = images_in_product_dir[0][1] # 选择数字最大的图片作为abs_img_path
        else: # 如果没有找到数字命名的图片
            print(f"产品 {target_product.get('productNo', '')} 的产品目录下没有找到数字命名的图片") # 打印提示信息
            return None # 返回None表示获取图片失败
    model_index_path = os.path.join(PRODUCT_HOME_PATH,"model_02.png")
    
    if not abs_img_path: # 如果遍历完所有图片仍未找到有效路径
        print(f"产品 {target_product.get('productNo', '')} 的所有参考图片均不存在") # 打印无法找到图片的错误信息
        return None # 返回None表示获取图片失败

    # --- 新增：合并图片逻辑 ---
    merged_image_path = None # 初始化合并图片路径
    try: # 尝试合并图片
        # 打开两张图片
        img1 = Image.open(abs_img_path).convert("RGBA") # 打开第一张图片并转换为RGBA模式
        img2 = Image.open(model_index_path).convert("RGBA") # 打开第二张图片并转换为RGBA模式

        # 调整第二张图片的高度与第一张图片相同，并保持比例
        if img2.height != img1.height: # 如果两张图片高度不同
            img2_width, img2_height = img2.size # 获取第二张图片的宽度和高度
            aspect_ratio = img2_width / img2_height # 计算宽高比
            new_img2_height = img1.height # 新高度与第一张图片相同
            new_img2_width = int(new_img2_height * aspect_ratio) # 根据比例计算新宽度
            img2 = img2.resize((new_img2_width, new_img2_height), Image.LANCZOS) # 调整图片大小

        # 创建一张新的图片，宽度为两张图片宽度之和，高度为第一张图片的高度
        merged_width = img1.width + img2.width # 计算合并后的总宽度
        merged_height = img1.height # 合并后的高度与第一张图片相同
        merged_img = Image.new("RGBA", (merged_width, merged_height)) # 创建新的空白图片

        # 将两张图片粘贴到新图片上
        merged_img.paste(img1, (0, 0)) # 将第一张图片粘贴到左侧
        merged_img.paste(img2, (img1.width, 0)) # 将第二张图片粘贴到第一张图片右侧

        # 保存合并后的图片到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png") # 创建一个临时文件
        merged_image_path = temp_file.name # 获取临时文件路径
        merged_img.save(merged_image_path) # 保存合并后的图片到临时文件
        temp_file.close() # 关闭临时文件句柄

        print(f"图片合并成功，临时文件路径: {merged_image_path}") # 打印合并成功信息

        name = target_product.get("name", "N/A") # 获取产品的名称属性
        content = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in target_product.get("content", [])]) # 获取产品成分并格式化为如90%天丝10%涤的字符串
        width = target_product.get("width", "N/A") # 获取产品的门幅属性
        weight = target_product.get("weight", "N/A") # 获取产品的克重属性
        meters_per_kg = target_product.get("metersPerKg", "N/A") # 获取产品的每公斤出米数属性
        colors = target_product.get("colors", "N/A") # 获取产品的颜色数量属性
        content_content = f"产品名：{name} 成分：{content} \n门幅： {width}cm 克重： {weight}克 每公斤出：{meters_per_kg}米 颜色： {colors}"# 按照指定格式打印产品详情信息

        prompt = f"""生成商品展示页，要求如下：
            1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}，文案要与面料相关，不能与面料无关
            2、参考右图的结构，生成对应的面料细节展示图，采用抓捏、悬挂或自然堆叠的方式，让面料产生自然的褶皱和阴影，利用侧逆光拍摄，保持一致的纹理与轻薄度
            3、采用简约风格与绿色为主题
            4、不可使用参考左图与右图原图, 不可使用任何品牌
            5、面料信息：{content_content}
            """ # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1536", # 设置生成的图片尺寸
            prefix=product_no, 
            filename="part4", # 传入前缀，用于保存文件命名
        ) 
        # 结束接口调用
    finally: # 确保临时文件被删除
        if merged_image_path and os.path.exists(merged_image_path): # 如果临时文件存在
            os.remove(merged_image_path) # 删除临时文件
            print(f"临时文件已删除: {merged_image_path}") # 打印删除信息

    return envword # 返回空值


def generate_product_part50_image(target_product: dict, envword: str = None, reference_image_filename: str = None) -> str: # 定义根据产品编号生成商品首图的方法，reference_image_filename为指定参考图的文件名
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成首图") # 如果为空，打印跳过提示
        return None # 直接返回 None 结束方法

    if not envword: # 如果envword为空或未填
        scenes = [ # 定义场景数组
            "#FFD700", # 场景1
            "#FF1493", # 场景2
            "#002FA7", # 场景3
            "#32CD32", # 场景4
            "#FF4500", # 场景5
            "#8A2BE2", # 场景6
            "#FF8C69", # 场景9
            "#FF007F" # 场景10
        ] # 结束场景数组定义
        envword = random.choice(scenes) # 随机选择一个场景作为环境变量
    product_no = target_product.get("productNo", "").replace("#", "") # 获取产品的编号
    abs_img_path = None # 初始化最终找到的有效绝对路径为None
    if reference_image_filename: # 如果指定了参考图文件名
        temp_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, reference_image_filename) # 拼接指定参考图的绝对路径
        if os.path.exists(temp_path): # 检查该绝对路径对应的图片文件是否存在
            abs_img_path = temp_path # 如果存在则赋值给最终路径变量
    else: # 如果没有指定参考图文件名，则按原有逻辑遍历
        images_in_product_dir = [] # 初始化一个列表来存储产品目录下的所有图片
        product_no_for_path = target_product.get("productNo", "").replace("#", "") # 获取产品编号用于构建路径
        product_image_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no_for_path) # 拼接产品图片目录的绝对路径

        if os.path.exists(product_image_dir): # 检查产品图片目录是否存在
            for f in os.listdir(product_image_dir): # 遍历目录下的所有文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.jpg', '.jpeg', '.png']: # 检查是否是数字命名的图片文件
                    images_in_product_dir.append((int(name), os.path.join(product_image_dir, f))) # 将(数字文件名, 绝对路径)添加到列表中

        if images_in_product_dir: # 如果找到了数字命名的图片
            images_in_product_dir.sort(key=lambda x: x[0], reverse=True) # 按数字文件名降序排序
            abs_img_path = images_in_product_dir[0][1] # 选择数字最大的图片作为abs_img_path
        else: # 如果没有找到数字命名的图片
            print(f"产品 {target_product.get('productNo', '')} 的产品目录下没有找到数字命名的图片") # 打印提示信息
            return None # 返回None表示获取图片失败
    model_index_path = os.path.join(PRODUCT_HOME_PATH,"model_03.png")
    
    if not abs_img_path: # 如果遍历完所有图片仍未找到有效路径
        print(f"产品 {target_product.get('productNo', '')} 的所有参考图片均不存在") # 打印无法找到图片的错误信息
        return None # 返回None表示获取图片失败

    # --- 新增：合并图片逻辑 ---
    merged_image_path = None # 初始化合并图片路径
    try: # 尝试合并图片
        # 打开两张图片
        img1 = Image.open(abs_img_path).convert("RGBA") # 打开第一张图片并转换为RGBA模式
        img2 = Image.open(model_index_path).convert("RGBA") # 打开第二张图片并转换为RGBA模式

        # 调整第二张图片的高度与第一张图片相同，并保持比例
        if img2.height != img1.height: # 如果两张图片高度不同
            img2_width, img2_height = img2.size # 获取第二张图片的宽度和高度
            aspect_ratio = img2_width / img2_height # 计算宽高比
            new_img2_height = img1.height # 新高度与第一张图片相同
            new_img2_width = int(new_img2_height * aspect_ratio) # 根据比例计算新宽度
            img2 = img2.resize((new_img2_width, new_img2_height), Image.LANCZOS) # 调整图片大小

        # 创建一张新的图片，宽度为两张图片宽度之和，高度为第一张图片的高度
        merged_width = img1.width + img2.width # 计算合并后的总宽度
        merged_height = img1.height # 合并后的高度与第一张图片相同
        merged_img = Image.new("RGBA", (merged_width, merged_height)) # 创建新的空白图片

        # 将两张图片粘贴到新图片上
        merged_img.paste(img1, (0, 0)) # 将第一张图片粘贴到左侧
        merged_img.paste(img2, (img1.width, 0)) # 将第二张图片粘贴到第一张图片右侧

        # 保存合并后的图片到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png") # 创建一个临时文件
        merged_image_path = temp_file.name # 获取临时文件路径
        merged_img.save(merged_image_path) # 保存合并后的图片到临时文件
        temp_file.close() # 关闭临时文件句柄

        print(f"图片合并成功，临时文件路径: {merged_image_path}") # 打印合并成功信息

        prompt = f"""生成商品展示页，要求如下：
            1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}，文案要与面料相关，不能与面料无关
            2、参考右图的结构，生成对应的面料细节展示图，采用抓捏、悬挂或自然堆叠的方式，让面料产生自然的褶皱和阴影，利用侧逆光拍摄，保持一致的纹理与轻薄度
            3、采用简约风格与绿色为主题
            4、不可使用参考左图与右图原图, 不可使用任何品牌
            5、模特图不同姿势不同服饰
            """ # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1536", # 设置生成的图片尺寸
            prefix=product_no, 
            filename="part5", # 传入前缀，用于保存文件命名
        ) 
        # 结束接口调用
    finally: # 确保临时文件被删除
        if merged_image_path and os.path.exists(merged_image_path): # 如果临时文件存在
            os.remove(merged_image_path) # 删除临时文件
            print(f"临时文件已删除: {merged_image_path}") # 打印删除信息
    return envword # 返回空值


def generate_product_part60_image(target_product: dict, envword: str = None, reference_image_filename: str = None) -> str: # 定义根据产品编号生成商品首图的方法，reference_image_filename为指定参考图的文件名
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成首图") # 如果为空，打印跳过提示
        return None # 直接返回 None 结束方法

    if not envword: # 如果envword为空或未填
        scenes = [ # 定义场景数组
            "#FFD700", # 场景1
            "#FF1493", # 场景2
            "#002FA7", # 场景3
            "#32CD32", # 场景4
            "#FF4500", # 场景5
            "#8A2BE2", # 场景6
            "#FF8C69", # 场景9
            "#FF007F" # 场景10
        ] # 结束场景数组定义
        envword = random.choice(scenes) # 随机选择一个场景作为环境变量
    product_no = target_product.get("productNo", "").replace("#", "") # 获取产品的编号
    abs_img_path = None # 初始化最终找到的有效绝对路径为None
    if reference_image_filename: # 如果指定了参考图文件名
        temp_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, reference_image_filename) # 拼接指定参考图的绝对路径
        if os.path.exists(temp_path): # 检查该绝对路径对应的图片文件是否存在
            abs_img_path = temp_path # 如果存在则赋值给最终路径变量
    else: # 如果没有指定参考图文件名，则按原有逻辑遍历
        images_in_product_dir = [] # 初始化一个列表来存储产品目录下的所有图片
        product_no_for_path = target_product.get("productNo", "").replace("#", "") # 获取产品编号用于构建路径
        product_image_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no_for_path) # 拼接产品图片目录的绝对路径

        if os.path.exists(product_image_dir): # 检查产品图片目录是否存在
            for f in os.listdir(product_image_dir): # 遍历目录下的所有文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.jpg', '.jpeg', '.png']: # 检查是否是数字命名的图片文件
                    images_in_product_dir.append((int(name), os.path.join(product_image_dir, f))) # 将(数字文件名, 绝对路径)添加到列表中

        if images_in_product_dir: # 如果找到了数字命名的图片
            images_in_product_dir.sort(key=lambda x: x[0], reverse=True) # 按数字文件名降序排序
            abs_img_path = images_in_product_dir[0][1] # 选择数字最大的图片作为abs_img_path
        else: # 如果没有找到数字命名的图片
            print(f"产品 {target_product.get('productNo', '')} 的产品目录下没有找到数字命名的图片") # 打印提示信息
            return None # 返回None表示获取图片失败
    model_index_path = os.path.join(PRODUCT_HOME_PATH,"model_04.jpg")
    
    if not abs_img_path: # 如果遍历完所有图片仍未找到有效路径
        print(f"产品 {target_product.get('productNo', '')} 的所有参考图片均不存在") # 打印无法找到图片的错误信息
        return None # 返回None表示获取图片失败

    # --- 新增：合并图片逻辑 ---
    merged_image_path = None # 初始化合并图片路径
    try: # 尝试合并图片
        # 打开两张图片
        img1 = Image.open(abs_img_path).convert("RGBA") # 打开第一张图片并转换为RGBA模式
        img2 = Image.open(model_index_path).convert("RGBA") # 打开第二张图片并转换为RGBA模式

        # 调整第二张图片的高度与第一张图片相同，并保持比例
        if img2.height != img1.height: # 如果两张图片高度不同
            img2_width, img2_height = img2.size # 获取第二张图片的宽度和高度
            aspect_ratio = img2_width / img2_height # 计算宽高比
            new_img2_height = img1.height # 新高度与第一张图片相同
            new_img2_width = int(new_img2_height * aspect_ratio) # 根据比例计算新宽度
            img2 = img2.resize((new_img2_width, new_img2_height), Image.LANCZOS) # 调整图片大小

        # 创建一张新的图片，宽度为两张图片宽度之和，高度为第一张图片的高度
        merged_width = img1.width + img2.width # 计算合并后的总宽度
        merged_height = img1.height # 合并后的高度与第一张图片相同
        merged_img = Image.new("RGBA", (merged_width, merged_height)) # 创建新的空白图片

        # 将两张图片粘贴到新图片上
        merged_img.paste(img1, (0, 0)) # 将第一张图片粘贴到左侧
        merged_img.paste(img2, (img1.width, 0)) # 将第二张图片粘贴到第一张图片右侧

        # 保存合并后的图片到临时文件
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".png") # 创建一个临时文件
        merged_image_path = temp_file.name # 获取临时文件路径
        merged_img.save(merged_image_path) # 保存合并后的图片到临时文件
        temp_file.close() # 关闭临时文件句柄

        print(f"图片合并成功，临时文件路径: {merged_image_path}") # 打印合并成功信息
    except Exception as e: # 捕获合并图片过程中的异常
        print(f"合并图片时出错: {e}") # 打印异常信息
        return None # 返回None表示合并图片失败

    try: # 尝试合并图片
        prompt = f"""生成商品特写图，要求如下
                1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}
                2、选取参考右图九宫格中的一个构图，生成对应的面料特写图，利用柔和正面光微距拍摄，要求高度还原面料纹理与轻薄度
                3、不可使用参考左图与右图原图, 不可使用任何品牌，不可出现高光""" # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1024", # 设置生成的图片尺寸
            prefix=product_no, # 传入前缀，用于保存文件命名
            filename="part6"
        ) 

        prompt = f"""生成商品特写图，要求如下
                1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}
                2、选取参考右图九宫格中的一个构图，生成对应的面料特写图，利用柔和正面光微距拍摄，要求高度还原面料纹理与轻薄度
                3、不可使用参考左图与右图原图, 不可使用任何品牌，不可出现高光""" # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1024", # 设置生成的图片尺寸
            prefix=product_no, # 传入前缀，用于保存文件命名
            filename="part7"
        ) 
        # 结束接口调用
    finally: # 确保临时文件被删除
        if merged_image_path and os.path.exists(merged_image_path): # 如果临时文件存在
            os.remove(merged_image_path) # 删除临时文件
            print(f"临时文件已删除: {merged_image_path}") # 打印删除信息

    return envword

def generate_product_wx_image(target_product: dict, envword: str = None, reference_image_filename: str = None) -> str: # 定义根据产品编号生成商品首图的方法，reference_image_filename为指定参考图的文件名
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成首图") # 如果为空，打印跳过提示
        return None # 直接返回 None 结束方法

    if not envword: # 如果envword为空或未填
        scenes = [ # 定义场景数组
            "淡黄", # 场景1
            "淡紫", # 场景2
            "淡蓝", # 场景3
            "淡绿", # 场景4
            "淡橙", # 场景5
            "淡红", # 场景6
        ] # 结束场景数组定义
        envword = random.choice(scenes) # 随机选择一个场景作为环境变量
    product_no = target_product.get("productNo", "").replace("#", "") # 获取产品的编号
    abs_img_path = None # 初始化最终找到的有效绝对路径为None
    if reference_image_filename: # 如果指定了参考图文件名
        temp_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, reference_image_filename) # 拼接指定参考图的绝对路径
        if os.path.exists(temp_path): # 检查该绝对路径对应的图片文件是否存在
            abs_img_path = temp_path # 如果存在则赋值给最终路径变量
    else: # 如果没有指定参考图文件名，则按原有逻辑遍历
        images_in_product_dir = [] # 初始化一个列表来存储产品目录下的所有图片
        product_no_for_path = target_product.get("productNo", "").replace("#", "") # 获取产品编号用于构建路径
        product_image_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no_for_path) # 拼接产品图片目录的绝对路径

        if os.path.exists(product_image_dir): # 检查产品图片目录是否存在
            for f in os.listdir(product_image_dir): # 遍历目录下的所有文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.jpg', '.jpeg', '.png']: # 检查是否是数字命名的图片文件
                    images_in_product_dir.append((int(name), os.path.join(product_image_dir, f))) # 将(数字文件名, 绝对路径)添加到列表中

        if images_in_product_dir: # 如果找到了数字命名的图片
            images_in_product_dir.sort(key=lambda x: x[0], reverse=True) # 按数字文件名降序排序
            abs_img_path = images_in_product_dir[0][1] # 选择数字最大的图片作为abs_img_path
        else: # 如果没有找到数字命名的图片
            print(f"产品 {target_product.get('productNo', '')} 的产品目录下没有找到数字命名的图片") # 打印提示信息
            return None # 返回None表示获取图片失败
    
    
    if not abs_img_path: # 如果遍历完所有图片仍未找到有效路径
        print(f"产品 {target_product.get('productNo', '')} 的所有参考图片均不存在") # 打印无法找到图片的错误信息
        return None # 返回None表示获取图片失败

    try: # 尝试合并图片
        name = target_product.get("name", "N/A") # 获取产品的名称属性
        content = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in target_product.get("content", [])]) # 获取产品成分并格式化为如90%天丝10%涤的字符串
        width = target_product.get("width", "N/A") # 获取产品的门幅属性
        weight = target_product.get("weight", "N/A") # 获取产品的克重属性
        meters_per_kg = target_product.get("metersPerKg", "N/A") # 获取产品的每公斤出米数属性

        model_index_path = os.path.join(PRODUCT_HOME_PATH,"wx_01.jpg")
        all_generated_image_paths = [] # 初始化一个列表来收集所有生成的图片路径
        # --- 新增：合并图片逻辑 ---
        merged_image_path = _merge_images(abs_img_path, model_index_path)
        prompt = f"""生成商品商品图，要求
            1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}，
            2、保持参考右图的构图，替换对应的面料细节展示图与色卡色块，采用抓捏、悬挂或自然堆叠的方式，让面料产生自然的褶皱和阴影，利用侧逆光拍摄，保持一致的纹理与轻薄度
            3、不可使用参考左图与右图原图, 不可使用任何品牌
            4、生成对应与面料相关的广告文案并更换对应参数，全部文案用英文，面料名：{name} 成分：{content}""" # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1024", # 设置生成的图片尺寸
            prefix=product_no, # 传入前缀，用于保存文件命名
            filename="wx1"
        ) 
        all_generated_image_paths.append(merged_image_path) # 将生成的图片路径添加到列表中
        
        model_index_path = os.path.join(PRODUCT_HOME_PATH,"wx_02.jpg")
        # --- 新增：合并图片逻辑 ---
        merged_image_path = _merge_images(abs_img_path, model_index_path)
        prompt = f"""生成商品商品图，要求
            1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}，
            2、按参考右图的构图，生成对应的面料细节展示图，采用抓捏、悬挂或自然堆叠的方式，让面料产生自然的褶皱和阴影，利用侧逆光拍摄，保持一致的纹理与轻薄度
            3、不可使用参考左图与右图原图, 不可使用任何品牌
            4、生成对应与面料相关的广告文案并更换对应参数，全部文案用英文，面料名：{name} 成分：{content} 门幅： {width}cm 克重： {weight}克""" # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1024", # 设置生成的图片尺寸
            prefix=product_no, # 传入前缀，用于保存文件命名
            filename="wx2"
        ) 
        all_generated_image_paths.append(merged_image_path) # 将生成的图片路径添加到列表中


        model_index_path = os.path.join(PRODUCT_HOME_PATH,"wx_03.jpg")
        # --- 新增：合并图片逻辑 ---
        merged_image_path = _merge_images(abs_img_path, model_index_path)
        prompt = f"""生成商品商品图，要求
            1、选取参考左图中的面料，记住纹理与轻薄度，换成图中的色卡块，颜色为{envword}，
            2、按参考右图的构图，生成对应的面料细节展示图，利用正面光拍摄，保持一致的纹理与轻薄度
            3、不可使用参考左图与右图原图, 不可使用任何品牌
            4、生成对应与面料相关的广告文案并更换对应参数，全部文案用英文，面料名：{name} 成分：{content} 门幅： {width}cm 克重： {weight}克""" # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1024", # 设置生成的图片尺寸
            prefix=product_no, # 传入前缀，用于保存文件命名
            filename="wx3"
        ) 
        all_generated_image_paths.append(merged_image_path) # 将生成的图片路径添加到列表中


        model_index_path = os.path.join(PRODUCT_HOME_PATH,"wx_04.jpg")
        # --- 新增：合并图片逻辑 ---
        merged_image_path = _merge_images(abs_img_path, model_index_path)
        prompt = f"""生成商品商品图，要求
            1、选取参考左图中的面料，记住纹理与轻薄度，颜色为{envword}，
            2、按参考右图的构图，生成对应的面料细节展示图，利用正面光拍摄，保持一致的纹理与轻薄度
            3、不可使用参考左图与右图原图, 不可使用任何品牌
            4、生成对应与面料相关的广告文案并更换对应参数，全部文案用英文，面料名：{name} 成分：{content} 门幅： {width}cm 克重： {weight}克 每公斤出：{meters_per_kg}米""" # 定义AI绘图的提示词
        generated_paths = _jiekou_gpt_image_edit( # 调用接口编辑图片
            image_path=merged_image_path, # 传入合并后的临时图片路径
            prompt=prompt, # 传入提示词
            size="1024x1024", # 设置生成的图片尺寸
            prefix=product_no, # 传入前缀，用于保存文件命名
            filename="wx4"
        ) 
        all_generated_image_paths.append(merged_image_path) # 将生成的图片路径添加到列表中

        for image_path in all_generated_image_paths:
            if image_path and os.path.exists(image_path): # 如果临时文件存在
                os.remove(image_path) # 删除临时文件
                print(f"临时文件已删除: {image_path}") # 打印删除信息


    except Exception as e: # 捕获异常
        print(f"合并图片时出错: {e}") # 打印异常信息
        return None # 返回None表示合并图片失败

    return envword



def get_product_by_no(product_no: str) -> dict: # 定义根据产品编号获取商品对象
    json_path = os.path.join(PRODUCT_HOME_PATH, "products.json") # 拼接products.json的绝对路径
    if not os.path.exists(json_path): # 检查json文件是否存在
        print(f"找不到产品数据文件: {json_path}") # 打印错误信息
        return None # 返回空值
    with open(json_path, 'r', encoding='utf-8') as f: # 打开并读取json文件
        products = json.load(f) # 解析json数据为列表
    target_product = None # 初始化目标产品变量
    for prod in products: # 遍历产品列表
        if prod.get("productNo", "").replace("#", "") == product_no.replace("#", ""): # 比对产品编号，忽略#号
            target_product = prod # 找到目标产品并赋值
            break # 跳出循环
    if not target_product: # 判断是否找到产品
        print(f"未找到编号为 {product_no} 的产品") # 打印未找到的提示
        return None # 返回空值
        
    myid = target_product.get("myid", "N/A") # 获取产品的myid属性
    name = target_product.get("name", "N/A") # 获取产品的名称属性
    content = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in target_product.get("content", [])]) # 获取产品成分并格式化为如90%天丝10%涤的字符串
    width = target_product.get("width", "N/A") # 获取产品的门幅属性
    weight = target_product.get("weight", "N/A") # 获取产品的克重属性
    meters_per_kg = target_product.get("metersPerKg", "N/A") # 获取产品的每公斤出米数属性
    colors = target_product.get("colors", "N/A") # 获取产品的颜色数量属性
    print(f"产品编号：{myid} 产品名：{name} 成分：{content} \n门幅： {width}cm 克重： {weight}克 每公斤出：{meters_per_kg}米 颜色： {colors}") # 按照指定格式打印产品详情信息
        
    w_price = target_product.get('whitePrice', 'N/A') # 获取白坯价格
    w_sell = round(float(w_price) * 1.2, 2) if w_price not in ('N/A', '', None) else 'N/A' # 计算白坯售卖价
    print(f"白坯价: {w_price} 售卖价: {w_sell}") # 打印白坯价格及售卖价
    
    c_price = target_product.get('colorPrice', 'N/A') # 获取彩色价格
    c_sell = round(float(c_price) * 1.2, 2) if c_price not in ('N/A', '', None) else 'N/A' # 计算彩色售卖价
    print(f"彩色价: {c_price} 售卖价: {c_sell}") # 打印彩色价格及售卖价
    
    s_price = target_product.get('samplePrice', 'N/A') # 获取样品价格
    s_sell = round(float(s_price) + 2, 2) if s_price not in ('N/A', '', None) else 'N/A' # 计算样品售卖价
    print(f"样品价: {s_price} 售卖价: {s_sell}") # 打印样品价格及售卖价
        
    return target_product

def generate_product_index_image2(target_product: dict,main_image_path: str) -> None: # 定义根据产品对象生成商品首图的方法
    """
    根据产品信息生成商品首图，模拟detail_product.html的布局和样式。
    """
    # --- 1. 参数解析 --
    product_no = target_product.get("productNo", "").replace("#", "") # 获取产品的编号
    image_abs_path = os.path.join(PRODUCT_HOME_PATH, 'images', 'products', product_no, 'index.png') # 获取主图片路径
    label_image_path = os.path.join(PRODUCT_HOME_PATH, 'label.png') # 获取标签图片路径
    badge_text = '现货' # 获取徽章文本，默认为“现货”
    width = target_product.get("width", "N/A") # 获取产品的门幅属性
    weight = target_product.get("weight", "N/A") # 获取产品的克重属性
    info_line_1 = f'克重:{weight}g/㎡ 幅宽:{width}CM' # 获取信息第一行，提供默认值
    content = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in target_product.get("content", [])]) # 获取产品成分并格式化为如90%天丝10%涤的字符串
    info_line_2 = content # 获取信息第二行，提供默认值
    if not main_image_path or not os.path.exists(main_image_path): # 检查主图片路径是否存在
        print(f"主图片不存在: {main_image_path}") # 打印错误信息
        return # 提前返回

    # --- 2. 加载主图片 ---
    main_img = Image.open(main_image_path).convert("RGBA") # 打开主图片并转换为RGBA模式
    img_width, img_height = main_img.size # 获取图片宽度和高度

    # --- 3. 加载并放置左上角标签图片 ---
    if label_image_path and os.path.exists(label_image_path): # 检查标签图片路径是否存在
        label_img = Image.open(label_image_path).convert("RGBA") # 打开标签图片并转换为RGBA模式
        
        # CSS .top-left-label 样式模拟
        label_width_css = 260 # CSS中定义的宽度
        label_padding_css = 20 # CSS中定义的内边距
        
        # 计算实际放置的标签宽度，考虑内边距
        actual_label_width = label_width_css - (label_padding_css * 2) # 实际标签宽度
        
        # 根据实际宽度等比例缩放标签图片
        label_img_resized = label_img.resize((actual_label_width, int(label_img.height * (actual_label_width / label_img.width))), Image.LANCZOS) # 缩放标签图片
        
        # 计算放置位置，考虑内边距
        label_x = label_padding_css # 标签X坐标
        label_y = label_padding_css # 标签Y坐标
        
        main_img.paste(label_img_resized, (label_x, label_y), label_img_resized) # 将标签图片粘贴到主图片上

    # --- 4. 创建底部导航条 ---
    navbar_height = int(img_height * 0.15) # 导航条高度，约占图片高度的15%
    navbar_bottom_offset = 20 # 导航条距离底部20px
    navbar_left_right_margin = 50 # 导航条左右边距50px
    
    navbar_width = img_width - (navbar_left_right_margin * 2) # 导航条宽度
    navbar_x = navbar_left_right_margin # 导航条X坐标
    navbar_y = img_height - navbar_height - navbar_bottom_offset # 导航条Y坐标

    navbar_radius = 30 # 导航条圆角半径

    # 模拟毛玻璃效果 (backdrop-filter: blur(10px))
    # 裁剪导航条区域的背景
    navbar_bg_area = main_img.crop((navbar_x, navbar_y, navbar_x + navbar_width, navbar_y + navbar_height)) # 裁剪导航条背景区域
    # 应用高斯模糊
    blurred_navbar_bg = navbar_bg_area.filter(ImageFilter.GaussianBlur(radius=10)) # 对背景区域应用高斯模糊
    # 将模糊后的背景粘贴回主图片，并应用圆角蒙版
    mask = Image.new("L", (navbar_width, navbar_height), 0) # 创建一个灰度蒙版
    mask_draw = ImageDraw.Draw(mask) # 创建蒙版绘图对象
    mask_draw.rounded_rectangle([0, 0, navbar_width, navbar_height], radius=navbar_radius, fill=255) # 绘制圆角矩形作为蒙版
    main_img.paste(blurred_navbar_bg, (navbar_x, navbar_y), mask) # 将模糊背景粘贴回主图片，并应用蒙版

    # 绘制半透明圆角矩形作为导航条背景
    overlay = Image.new('RGBA', (navbar_width, navbar_height), (255, 255, 255, int(255 * 0.15))) # 创建半透明白色叠加层
    draw_overlay = ImageDraw.Draw(overlay) # 创建叠加层绘图对象
    # 绘制圆角矩形
    draw_overlay.rounded_rectangle([0, 0, navbar_width, navbar_height], radius=navbar_radius, fill=(255, 255, 255, int(255 * 0.15))) # 绘制圆角矩形
    main_img.paste(overlay, (navbar_x, navbar_y), overlay) # 将叠加层粘贴到主图片上

    # 绘制导航条边框 (1px solid rgba(255, 255, 255, 0.2))


    # 绘制导航条边框 (1px solid rgba(255, 255, 255, 0.2))
    draw = ImageDraw.Draw(main_img) # 创建主图片绘图对象

    # --- 5. 绘制“现货”徽章 ---
    badge_padding_x = 40 # 徽章水平内边距
    badge_padding_y = 8 # 徽章垂直内边距
    badge_radius = 30 # 徽章圆角半径
    badge_bg_color = (240, 216, 0, 255) # 徽章背景颜色 #f0d800
    badge_text_color = (51, 51, 51, 255) # 徽章文本颜色 #333

    # 尝试加载中文字体
    try: # 尝试加载微软雅黑粗体
        font_badge = ImageFont.truetype(os.path.join(PRODUCT_HOME_PATH, "msyhbd.ttc"), size=int(3.6 * 16)) # 徽章字体大小
    except IOError: # 如果加载失败
        try: # 尝试加载普通微软雅黑
            font_badge = ImageFont.truetype(os.path.join(PRODUCT_HOME_PATH, "msyh.ttc"), size=int(3.6 * 16)) # 徽章字体大小
        except IOError: # 如果再次失败
            font_badge = ImageFont.load_default() # 加载默认字体
            print("警告: 未找到msyhbd.ttc或msyh.ttc字体，使用默认字体。") # 打印警告信息

    badge_bbox = draw.textbbox((0, 0), badge_text, font=font_badge) # 获取徽章文本边界框
    badge_text_width = badge_bbox[2] - badge_bbox[0] # 徽章文本宽度
    badge_text_height = badge_bbox[3] - badge_bbox[1] # 徽章文本高度

    badge_width = badge_text_width + (badge_padding_x * 2) # 徽章总宽度
    badge_height = badge_text_height + (badge_padding_y * 2) # 徽章总高度

    badge_x = navbar_x + 20 # 徽章X坐标 (navbar padding-left 20px)
    badge_y = navbar_y + (navbar_height - badge_height) // 2 # 徽章Y坐标 (垂直居中)

    # 绘制徽章背景
    draw.rounded_rectangle([badge_x, badge_y, badge_x + badge_width, badge_y + badge_height], radius=badge_radius, fill=badge_bg_color) # 绘制徽章背景

    # 绘制徽章文本
    # 使用getbbox获取更精确的文本尺寸，包括基线偏移
    text_left, text_top, text_right, text_bottom = font_badge.getbbox(badge_text) # 获取文本边界框
    text_height_actual = text_bottom - text_top # 实际文本高度
    
    badge_text_x = badge_x + (badge_width - (text_right - text_left)) // 2 # 徽章文本X坐标 (居中)
    badge_text_y = badge_y + (badge_height - text_height_actual) // 2 - text_top # 徽章文本Y坐标 (居中，考虑基线)
    draw.text((badge_text_x, badge_text_y), badge_text, fill=badge_text_color, font=font_badge) # 绘制徽章文本

    # --- 6. 绘制产品信息文本 ---
    info_text_color = (0, 0, 0, 255) # 产品信息文本颜色 #000000
    info_text_shadow_color = (255, 255, 255, int(255 * 0.7)) # 文本阴影颜色
    info_text_shadow_offset = 2 # 文本阴影偏移量

    # 尝试加载中文字体
    try: # 尝试加载微软雅黑
        font_info_line1 = ImageFont.truetype(os.path.join(PRODUCT_HOME_PATH, "msyh.ttc"), size=int(1.5 * 40)) # 信息第一行字体大小
        font_info_line2 = ImageFont.truetype(os.path.join(PRODUCT_HOME_PATH, "msyh.ttc"), size=int(1.2 * 40)) # 信息第二行字体大小
    except IOError: # 如果加载失败
        font_info_line1 = ImageFont.load_default() # 加载默认字体
        font_info_line2 = ImageFont.load_default() # 加载默认字体
        print("警告: 未找到msyh.ttc字体，产品信息使用默认字体。") # 打印警告信息

    # 计算产品信息区域的起始X坐标 (在徽章右侧，留有gap)
    info_area_x = badge_x + badge_width + 20 # 信息区域X坐标 (徽章宽度 + gap 20px)
    info_area_width = (navbar_x + navbar_width) - info_area_x - 20 # 信息区域宽度 (navbar padding-right 20px)

    # 绘制第一行信息
    info1_bbox = draw.textbbox((0, 0), info_line_1, font=font_info_line1) # 获取第一行文本边界框
    info1_text_height = info1_bbox[3] - info1_bbox[1] # 第一行文本高度
    
    info1_text_x = info_area_x # 第一行文本X坐标
    info1_text_y = navbar_y + (navbar_height // 2) - info1_text_height - 5 # 第一行文本Y坐标 (略微向上偏移)

    # 绘制阴影
    draw.text((info1_text_x + info_text_shadow_offset, info1_text_y + info_text_shadow_offset), info_line_1, fill=info_text_shadow_color, font=font_info_line1) # 绘制阴影
    # 绘制文本
    draw.text((info1_text_x, info1_text_y), info_line_1, fill=info_text_color, font=font_info_line1) # 绘制文本

    # 绘制第二行信息
    info2_bbox = draw.textbbox((0, 0), info_line_2, font=font_info_line2) # 获取第二行文本边界框
    info2_text_height = info2_bbox[3] - info2_bbox[1] # 第二行文本高度

    info2_text_x = info_area_x # 第二行文本X坐标
    info2_text_y = navbar_y + (navbar_height // 2) + 5 # 第二行文本Y坐标 (略微向下偏移)

    # 绘制阴影
    draw.text((info2_text_x + info_text_shadow_offset, info2_text_y + info_text_shadow_offset), info_line_2, fill=info_text_shadow_color, font=font_info_line2) # 绘制阴影
    # 绘制文本
    draw.text((info2_text_x, info2_text_y), info_line_2, fill=info_text_color, font=font_info_line2) # 绘制文本

    # --- 7. 保存最终图片 ---
    main_img.save(image_abs_path) # 保存最终图片
    print(f"图片已生成并保存到: {image_abs_path}") # 打印保存路径

def generate_product_index_image(target_product: dict, image_abs_path: str) -> str: # 定义根据产品对象生成商品首图的方法
        if not target_product: # 检查传入的 target_product 是否为空
            print("传入的产品对象为空，跳过生成商品首图带Logo") # 打印跳过提示
            return None # 直接返回 None 结束方法
            
        fg_path = os.path.join(PRODUCT_HOME_PATH, "logo-nt-w.png") # 获取logo的绝对路径作为前景图
        frame_path = os.path.join(PRODUCT_HOME_PATH, "frame.png") # 获取logo的绝对路径作为前景图
        raw_name = target_product.get('name', '') # 获取产品原始名称
        clean_name = raw_name.split('（')[0].split('(')[0] # 截取括号前的内容以去除括号及其中文字
        title = f"{target_product.get('fullname', '')}{target_product.get('colors', '')}色" # 拼接标题：产品号+清理后的产品名称
        content_list = target_product.get('content', []) # 获取产品成分列表
        content_str = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in content_list]) # 拼接成分信息
        content_suffix = f"{content_str}" if content_str else "" # 如果有成分信息则添加斜杠前缀
        subtitle = f"{target_product.get('colors', 0)}色/{target_product.get('weight', 0)}g/{target_product.get('width', 0)}cm\n{content_suffix}" # 拼接副标题：颜色/克重/门幅/成分
        final_output = _overlay_images( # 调用合成方法
            bg_path=image_abs_path, # 传入生成的背景图路径
            fg_path=fg_path, # 传入logo前景图路径
            frame_path=frame_path, # 传入边框背景图路径
            title=title, # 传入拼接好的标题
            #subtitle=subtitle # 传入拼接好的副标题
        ) 
        if final_output: # 检查合成结果是否有效
            print(f"生成商品首图成功: {final_output}")
        else: # 如果合成跳过了
            print("生成商品首图被跳过")
        return final_output # 返回最终合成图片的路径
    
# 定义天丝面料适合制作的衣服类型静态变量数组
TENCEL_CLOTHING_TYPES = [
    "阔腿裤", "拖地裤", "液态裤", "冰丝裤", "衬衫", "风衬衫",
    "牛仔衬衫", "牛仔裙", "牛仔裤", "连衣裙", "吊带裙", "衬衫裙",
    "半身伞裙", "鱼尾裙", "西装外套", "西装", "防晒衫", "空调衫",
    "开衫", "短裤",  "家居服", "睡衣", "睡裙"
]

def generate_product_title(target_product: dict, custom_keywords: list, advice: str, acount: int = 6) -> list: # 定义根据产品和自定义关键词数组生成标题的方法，新增生成数量参数，返回列表
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成标题") # 打印跳过提示
        return [] # 直接返回空列表结束方法
        
    import random # 导入random模块以实现随机组合功能
    keyword_data = [] # 初始化空列表用于存放从产品属性提取的关键词
    
    name = target_product.get("name", "") # 获取产品的名称
    if name: # 如果名称存在
        keyword_data.append(name) # 将名称添加到关键词列表中
        
    content_list = target_product.get("content", []) # 获取产品成分列表
    if content_list: # 如果成分列表存在
        content_str = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in content_list]) # 格式化成分为字符串
        #keyword_data.append(content_str) # 将成分字符串添加到关键词列表中

    if isinstance(custom_keywords, list): # 判断传入的自定义关键词是否为数组格式
        keyword_data.extend(custom_keywords) # 如果是数组则将其所有元素一并添加到列表中
    
    # 去重处理，如果某词被其他词包含，则剔除该词（例如“涤天丝”包含“天丝”，则剔除“天丝”）
    keyword_data = list(dict.fromkeys(keyword_data)) # 先进行基础的完全相同去重
    filtered_keywords = [] # 初始化存放过滤后关键词的列表
    for i, word in enumerate(keyword_data): # 遍历去重后的关键词列表
        is_contained = False # 标记当前词是否被其他词包含，默认为False
        for j, other_word in enumerate(keyword_data): # 再次遍历关键词列表进行两两比较
            if i != j and word in other_word: # 如果不是同一个词，并且当前词被其他词包含
                is_contained = True # 将标记设为True
                break # 已经确定被包含，跳出内层循环
        if not is_contained: # 如果当前词没有被任何其他词包含
            filtered_keywords.append(word) # 将当前词加入过滤后的列表
    keyword_data = filtered_keywords # 将过滤后的列表重新赋值给keyword_data
    system_prompt = f"""你是一个商品标题生成器，标题通顺高点击量，不能超过60字，不要少于58字，数字英文1个字，汉字算2个字，用提供的关键词生成商品标题，一共推荐{acount}个，返回格式用JSON，例如：[{{"1": "天丝面料"}}]"""
    response = _jiekou_chat( system_prompt, # 调用接口生成商品副标题的文本
        user_prompt=f"关键词：{keyword_data}" # 传入拼接好的商品信息
    ) # 结束接口调用    

    titles = [] # 初始化空列表用于存放提取出来的标题
    content_text = "" # 初始化存放模型返回文本的变量
    
    if response: # 判断接口返回是否为空
        if hasattr(response, 'choices') and len(response.choices) > 0: # 判断返回对象是否包含choices属性（处理API对象结构）
            content_text = response.choices[0].message.content # 提取出真正的文本内容
        elif isinstance(response, dict) and 'choices' in response: # 判断返回对象是否为字典且包含choices键
            content_text = response['choices'][0]['message']['content'] # 从字典中提取出真正的文本内容
            
    if content_text: # 判断是否成功提取到了文本内容
        try: # 尝试解析 JSON 数据
            # 清理可能的 markdown 代码块标记，如 ```json 和 ```，防止大模型包裹代码块导致解析失败
            clean_text = content_text.replace("```json", "").replace("```", "").strip() # 去除干扰字符
            parsed_json = json.loads(clean_text) # 将清理后的文本解析为 JSON 对象
            
            print("--- 大模型生成的商品标题推荐 ---") # 打印标题输出开始的分割线
            if isinstance(parsed_json, list): # 判断解析后的数据是否为列表
                for item in parsed_json: # 遍历列表中的每一个元素
                    if isinstance(item, dict): # 判断元素是否为字典
                        for key, value in item.items(): # 遍历字典的键值对
                            titles.append(value) # 将提取到的标题值添加到列表中
                            print(f"推荐标题 {key}: {value}") # 格式化打印出对应的标题
                            
                # 获取产品编号用于创建或定位文件夹
                product_no = target_product.get('productNo', '').replace('#', '')
                if product_no: # 只有当产品编号存在时才进行保存操作
                    # 拼接存放标题的目标文件夹路径: images/products/产品编号
                    title_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no)
                    # 确保目标文件夹存在，不存在则自动创建
                    os.makedirs(title_dir, exist_ok=True)
                    # 拼接目标文件 title.md 的完整路径
                    title_path = os.path.join(title_dir, "title.md")
                    
                    try: # 尝试执行文件写入操作
                        # 以追加模式(a)或覆盖模式(w)打开文件，这里使用 w 模式覆盖旧标题
                        with open(title_path, 'w', encoding='utf-8') as f:
                            f.write("## 推荐商品标题\n\n") # 写入 Markdown 标题
                            for i, title in enumerate(titles, 1): # 遍历已提取的标题列表
                                f.write(f"{i}. {title}\n") # 将每个标题按列表格式写入文件
                        print(f"标题已成功保存至: {title_path}") # 打印保存成功的提示
                    except IOError as e: # 捕获文件写入异常
                        print(f"保存标题文件时发生错误: {e}") # 打印错误信息
            else: # 如果解析出来的不是列表格式
                print(f"返回的 JSON 格式不符合预期: {parsed_json}") # 打印格式异常提示
        except json.JSONDecodeError as e: # 捕获 JSON 解析异常
            print(f"解析大模型返回的 JSON 数据失败: {e}\n原始返回内容: {content_text}") # 打印解析失败信息及原文
    else: # 如果未能提取到文本内容
        print("未获取到大模型生成的有效内容") # 打印错误提示

    return titles # 返回包含多个生成标题的列表


def generate_product_info(target_product: dict) -> str: # 定义根据产品对象生成商品副标题的方法
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成商品文案") # 打印跳过提示
        return "" # 返回空字符串结束方法
        
    content_list = target_product.get('content', []) # 获取产品成分列表
    content_str = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in content_list]) # 拼接成分信息，例如80%涤20%棉
    width = target_product.get('width', 0) # 获取产品门幅
    weight = target_product.get('weight', 0) # 获取产品克重
    meters_per_kg = target_product.get('metersPerKg', 0) # 获取每公斤出米数
    price = target_product.get('colorPrice', target_product.get('price', 0)) * 1.2 # 获取每米单价，优先使用colorPrice，并乘以1.2
    product_info = f"成分{content_str} 门幅{width}cm 克重{weight}g 每公斤出{meters_per_kg}米 每米{price}元" # 拼接完整的商品信息
    system_prompt = f"你是一个专业的服装设计师，特别擅长分析面料适合做什么衣服为什么，至少包含三块内容：面料成分特性分析、适合制作的服装、市场定位建议，采用总分结构，总结在开头，每个模块字数不超300字"
    response = _jiekou_chat( system_prompt, # 调用接口生成商品副标题的文本
        user_prompt=f"面料特性：{product_info}" # 传入拼接好的商品信息
    ) # 结束接口调用
    
    product_no = target_product.get('productNo', '').replace('#', '') # 获取产品编号并移除#号
    base_dir = os.path.dirname(os.path.abspath(__file__)) # 获取当前脚本所在目录的绝对路径
    info_dir = os.path.join(base_dir, "images", "products", product_no) # 拼接存放info.md的目标文件夹路径
    os.makedirs(info_dir, exist_ok=True) # 确保目标文件夹存在，如果不存在则创建
    info_path = os.path.join(info_dir, "info.md") # 拼接info.md文件的完整绝对路径
    
    content_to_write = response # 将接口返回的内容赋值给待写入变量
    if hasattr(response, 'choices') and len(response.choices) > 0: # 判断返回对象是否包含choices属性（处理API对象结构）
        content_to_write = response.choices[0].message.content # 提取出真正的文本内容
    elif isinstance(response, dict) and 'choices' in response: # 判断返回对象是否为字典且包含choices键
        content_to_write = response['choices'][0]['message']['content'] # 从字典中提取出真正的文本内容
        
    with open(info_path, 'w', encoding='utf-8') as f: # 以写入模式打开info.md文件，指定utf-8编码
        f.write(content_to_write) # 将大模型生成的分析报告内容写入文件
        
    print(f"产品分析报告已保存至: {info_path}") # 打印保存成功的提示信息
    return response # 返回最终随机组合生成的商品副标题字符串


def generate_product_wx_info(target_product: dict, count:int=100): #输入产品对象字数，输出微信文字部分
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成产品说明图片") # 打印跳过提示
        return [] # 返回空列表结束方法
        
    product_no = target_product.get('productNo', '').replace('#', '') # 获取产品编号并移除可能存在的#号
    info_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, "info.md") # 拼接出对应产品的info.md绝对路径
    
    if not os.path.exists(info_path): # 检查目标info.md文件是否存在
        print(f"未找到该产品的说明文件: {info_path}") # 如果文件不存在则打印错误提示
        return [] # 文件不存在时返回空列表
        
    with open(info_path, 'r', encoding='utf-8') as f: # 以只读模式和UTF-8编码打开文件
        content = f.read() # 读取文件的全部文本内容
        
    lines = content.split('\n') # 按行分割内容
    h2_indices = [i for i, line in enumerate(lines) if line.startswith('## ')] # 找到所有以 ## 开头的行的索引

    # 1. 获取第三个##以上部分文本
    processed_lines = [] # 初始化处理后的文本行列表
    if len(h2_indices) >= 3: # 如果存在至少三个 ## 标题
        # 截取到第三个 ## 标题之前的所有行
        text_to_process = lines[:h2_indices[2]]
    else:
        # 如果不足三个 ## 标题，则处理所有行
        text_to_process = lines

    # 2. 去掉以 # 开头的行
    for line in text_to_process: # 遍历待处理的文本行
        if not line.strip().startswith('#'): # 如果行不以 # 开头（忽略前导空格）
            processed_lines.append(line) # 将该行添加到处理后的文本行列表

    # 3. 保存到当前目录的 wx.md
    output_content = '\n'.join(processed_lines) # 将处理后的文本行重新拼接成字符串
    system_prompt = f"把下面内容浓缩为一段话，适合口头表达，适合发朋友圈，轻松诙谐一些,不要包含具体价格，在{count}字内"
    response = _jiekou_chat( system_prompt, # 调用接口生成商品副标题的文本
        user_prompt=output_content # 传入拼接好的商品信息
    ) # 结束接口调用

    content_to_write = response # 将接口返回的内容赋值给待写入变量
    if hasattr(response, 'choices') and len(response.choices) > 0: # 判断返回对象是否包含choices属性（处理API对象结构）
        content_to_write = response.choices[0].message.content # 提取出真正的文本内容
    elif isinstance(response, dict) and 'choices' in response: # 判断返回对象是否为字典且包含choices键
        content_to_write = response['choices'][0]['message']['content'] # 从字典中提取出真正的文本内容
        
    wx_md_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, "wx.md") # 拼接 wx.md 的绝对路径
    with open(wx_md_path, 'w', encoding='utf-8') as f: # 以写入模式和UTF-8编码打开 wx.md 文件
        f.write(content_to_write) # 写入处理后的内容






def generate_product_info_image(target_product: dict): # 定义生成产品说明图片的方法
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成产品说明图片") # 打印跳过提示
        return [] # 返回空列表结束方法
        
    product_no = target_product.get('productNo', '').replace('#', '') # 获取产品编号并移除可能存在的#号
    info_path = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no, "info.md") # 拼接出对应产品的info.md绝对路径
    
    if not os.path.exists(info_path): # 检查目标info.md文件是否存在
        print(f"未找到该产品的说明文件: {info_path}") # 如果文件不存在则打印错误提示
        return [] # 文件不存在时返回空列表
        
    with open(info_path, 'r', encoding='utf-8') as f: # 以只读模式和UTF-8编码打开文件
        content = f.read() # 读取文件的全部文本内容
        
    lines = content.split('\n') # 按行分割内容
    h2_indices = [i for i, line in enumerate(lines) if line.startswith('## ')] # 找到所有以 ## 开头的行的索引
    
    if len(h2_indices) < 2: # 如果找到的 ## 标题少于2个
        print("未找到足够的 ## 标题行") # 打印未找到足够的 ## 标题行
        return [] # 返回空列表
        
    # 提取产品信息
    myid = target_product.get("myid", "") # 获取产品编号
    name = target_product.get("name", "") # 获取产品名
    content_list = target_product.get("content", []) # 获取产品成分列表
    content_str = "".join([f"{int(c.get('percentage', 0))}%{c.get('name', '')}" for c in content_list]) # 拼接成分信息
    width = target_product.get("width", "") # 获取产品门幅
    weight = target_product.get("weight", "") # 获取产品克重
    meters_per_kg = target_product.get("metersPerKg", "") # 获取每公斤出米数
    colors = target_product.get("colors", "") # 获取颜色
    
    # 拼接产品信息字符串
    product_desc = f"产品编号：{myid} 产品名：{name} 成分：{content_str} 门幅： {width}cm 克重： {weight}克 每公斤出：{meters_per_kg}米 颜色： {colors}"
    
    first_h2_idx = h2_indices[0] # 获取第一个 ## 标题的索引
    lines.insert(first_h2_idx, product_desc) # 在第一个 ## 标题的前一行插入产品信息
    
    second_h2_idx = h2_indices[1] + 1 # 获取插入后第二个 ## 标题的索引（因为插入了一行所以加1）
    
    part1_lines = lines[:second_h2_idx] # 获取第一部分的所有行
    part2_lines = lines[second_h2_idx:] # 获取第二部分的所有行
    
    part1_text = '\n'.join(part1_lines).strip() # 将第一部分的行重新拼接为字符串并去除首尾空白字符
    part2_text = '\n'.join(part2_lines).strip() # 将第二部分的行重新拼接为字符串并去除首尾空白字符
    
    base_prompt = "设计一张产品说明，要求逻辑顺畅，简约明了，美观清晰，必要地方补充真实图片，采用小清新风格， 内容如下：" # 定义生成图片的固定前缀提示词
    
    print("开始生成产品说明的第一部分图片...") # 打印第一部分图片开始生成的提示
    part1_images = _jiekou_gpt_image( # 调用GPT图片生成接口
        prompt=f"{base_prompt}\n{part1_text}", # 拼接固定提示词与第一部分文本
        prefix=product_no, # 传入产品编号作为文件名前缀
        filename="part1", # 传入"part1"作为生成文件的特定名称
        size="1024x1536" # 强制指定适合说明长图的垂直尺寸
    ) # 结束第一部分接口调用
    
    print("开始生成产品说明的第二部分图片...") # 打印第二部分图片开始生成的提示
    part2_images = _jiekou_gpt_image( # 调用GPT图片生成接口
        prompt=f"{base_prompt}\n{part2_text}", # 拼接固定提示词与第二部分文本
        prefix=product_no, # 传入产品编号作为文件名前缀
        filename="part2", # 传入"part2"作为生成文件的特定名称
        size="1024x1536" # 强制指定适合说明长图的垂直尺寸
    ) # 结束第二部分接口调用
    
    result_images = [] # 初始化存放最终生成图片路径的列表
    if part1_images: # 如果第一部分生成成功（返回列表不为空）
        print(f"生成说明的第一部分图片成功: {part1_images}")
        result_images.extend(part1_images) # 将第一部分的图片路径加入结果列表
    if part2_images: # 如果第二部分生成成功（返回列表不为空）
        print(f"生成说明的第二部分图片成功: {part2_images}")
        result_images.extend(part2_images) # 将第二部分的图片路径加入结果列表
        
    return result_images # 返回所有成功生成的图片绝对路径列表

def format_image_size(target_product: dict) -> str: # 定义格式化图片尺寸的方法
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过格式化图片尺寸") # 打印跳过提示
        return "传入的产品对象为空" # 返回错误提示结束方法
        
    import shutil # 引入 shutil 模块用于文件拷贝
    
    product_no = target_product.get('productNo', '').replace('#', '') # 获取产品编号并移除可能存在的#号
    product_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no) # 拼接出产品的图片存放绝对路径
    
    # 获取项目根目录，以便定位 static/media 目录
    project_root = os.path.dirname(os.path.dirname(PRODUCT_HOME_PATH)) # 获取项目根目录的绝对路径
    media_dir = os.path.join(project_root, "static", "media", product_no) # 拼接出微信收到的媒体文件存放目录
    
    if os.path.exists(media_dir): # 检查微信媒体目录是否存在
        # 找出当前已有的图片最大序号
        existing_imgs = [] # 初始化存放已有图片序号的列表
        if os.path.exists(product_dir): # 如果产品目录存在
            for f in os.listdir(product_dir): # 遍历产品目录下的文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.jpg', '.jpeg', '.png']: # 检查是否是纯数字命名的图片
                    existing_imgs.append(int(name)) # 将数字序号加入列表
        
        next_img_idx = max(existing_imgs) + 1 if existing_imgs else 0 # 计算下一个图片的起始序号（已有最大值加1，否则从0开始）
        
        # 找出当前已有的视频最大序号
        existing_vids = [] # 初始化存放已有视频序号的列表
        if os.path.exists(product_dir): # 如果产品目录存在
            for f in os.listdir(product_dir): # 遍历产品目录下的文件
                name, ext = os.path.splitext(f) # 分离文件名和扩展名
                if name.isdigit() and ext.lower() in ['.mp4', '.avi', '.mov']: # 检查是否是纯数字命名的视频
                    existing_vids.append(int(name)) # 将数字序号加入列表
                    
        next_vid_idx = max(existing_vids) + 1 if existing_vids else 1 # 计算下一个视频的起始序号（已有最大值加1，否则从1开始）
        
        if not os.path.exists(product_dir): # 如果产品目录不存在
            os.makedirs(product_dir, exist_ok=True) # 则自动创建产品目录
            
        # 遍历媒体目录中的文件进行拷贝，按文件名排序以保证顺序
        media_files = sorted(os.listdir(media_dir)) # 获取排序后的媒体文件列表
        for f in media_files: # 遍历每一个媒体文件
            src_path = os.path.join(media_dir, f) # 拼接源文件绝对路径
            if not os.path.isfile(src_path): # 检查当前路径是否是文件
                continue # 如果不是文件则跳过
                
            _, ext = os.path.splitext(f) # 获取文件的扩展名
            ext = ext.lower() # 将扩展名统一转换为小写以便匹配
            
            if ext in ['.jpg', '.jpeg', '.png']: # 如果该文件是图片
                dst_name = f"{next_img_idx:02d}{ext}" # 格式化新的图片文件名（例如 03.jpg）
                dst_path = os.path.join(product_dir, dst_name) # 拼接拷贝目标绝对路径
                shutil.copy2(src_path, dst_path) # 将图片文件拷贝到目标目录
                next_img_idx += 1 # 图片序号计数器加一
            elif ext in ['.mp4', '.avi', '.mov']: # 如果该文件是视频
                dst_name = f"{next_vid_idx:02d}{ext}" # 格式化新的视频文件名（例如 01.mp4）
                dst_path = os.path.join(product_dir, dst_name) # 拼接拷贝目标绝对路径
                shutil.copy2(src_path, dst_path) # 将视频文件拷贝到目标目录
                next_vid_idx += 1 # 视频序号计数器加一

    if not os.path.exists(product_dir): # 检查该产品目录是否存在
        return "产品目录不存在" # 如果目录不存在则返回提示信息
    count = 0 # 初始化成功处理的图片计数器
    for file_name in os.listdir(product_dir): # 遍历产品目录下的所有文件
        name_without_ext, ext = os.path.splitext(file_name) # 获取不包含扩展名的纯文件名和扩展名
        if not name_without_ext.isdigit(): # 检查纯文件名是否完全由数字组成
            continue # 如果不是数字命名则跳过处理进入下一次循环
        if ext.lower() not in ['.jpg', '.jpeg', '.png']: # 检查扩展名是否为指定的图片格式
            continue # 如果不是这些图片格式则跳过处理进入下一次循环
        abs_img_path = os.path.join(product_dir, file_name) # 拼接出当前图片的绝对路径
        if not os.path.isfile(abs_img_path): # 检查当前路径是否为文件
            continue # 如果不是文件则跳过处理
        try: # 尝试打开并处理图片以防止非图片文件导致报错
            img = Image.open(abs_img_path) # 使用PIL库打开目标图片
            if img.mode != 'RGBA': # 检查图片是否不是RGBA模式
                img = img.convert('RGBA') # 将图片统一转换为RGBA模式以兼容透明通道
            width, height = img.size # 获取原图片的宽度和高度
            if width == height: # 判断图片是否已经是正方形
                continue # 如果已经是正方形则直接跳过后续的填充处理
            max_size = max(width, height) # 计算原图片宽度和高度中的最大值作为新正方形的边长
            new_img = Image.new("RGBA", (max_size, max_size), "white") # 创建一个纯白背景的RGBA正方形新图片
            paste_x = (max_size - width) // 2 # 计算原图片在新背景上的水平居中粘贴坐标
            paste_y = (max_size - height) // 2 # 计算原图片在新背景上的垂直居中粘贴坐标
            new_img.paste(img, (paste_x, paste_y), img) # 将原图片以自身为遮罩粘贴到白底正方形图片的中心位置
            final_img = new_img.convert("RGB") # 将合并后的图片转换为RGB模式以支持保存为所有常规格式（如JPEG）
            final_img.save(abs_img_path) # 将处理后的正方形图片覆盖保存回原路径
            count += 1 # 成功处理后将计数器加一
        except Exception as e: # 捕获处理图片时可能发生的异常
            print(f"处理图片 {file_name} 时出错: {e}") # 打印错误信息以便排查
    return f"成功处理了 {count} 张图片" # 返回包含处理数量的提示字符串


def generate_product_video(target_product: dict, watermark_path: str = None) -> str: # 定义生成产品视频的方法，增加水印图片绝对路径参数
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成视频") # 打印跳过提示
        return "" # 返回空字符串结束方法
        
    product_no = target_product.get('productNo', '').replace('#', '') # 获取产品编号并去掉可能存在的#号
    product_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no) # 拼接产品目录的绝对路径
    index_img_path = os.path.join(product_dir, "index.png") # 拼接首图index.png的绝对路径
    if not os.path.exists(index_img_path): # 检查首图是否存在，如果不存在则返回空字符串
        print(f"首图不存在: {index_img_path}") # 打印首图不存在的提示信息
        return "" # 返回空字符串表示生成失败
    img_clip = ImageClip(index_img_path).set_duration(2) # 加载首图为ImageClip并设置持续时间为2秒
    target_w, target_h = img_clip.size # 获取首图的宽度和高度
    
    watermark_clip = None # 初始化水印片段为空
    if watermark_path is None: # 如果水印路径为空，则使用默认的logo作为水印
        watermark_path = os.path.join(PRODUCT_HOME_PATH, "logo-nt-w.png") # 获取logo的绝对路径作为默认水印图
    if watermark_path and os.path.exists(watermark_path): # 判断是否传入了水印路径且文件存在
        watermark_clip = ImageClip(watermark_path) # 加载水印图片为ImageClip
        watermark_w = int(target_w / 5) # 计算水印的目标宽度为视频宽度的五分之一
        watermark_clip = watermark_clip.resize(width=watermark_w) # 将水印等比例缩放到目标宽度
        watermark_clip = watermark_clip.set_opacity(0.8) # 设置水印透明度为80%
        watermark_clip = watermark_clip.set_position("center") # 将水印设置为居中位置
        
    clips = [img_clip] # 初始化待拼接的视频片段列表，首帧为图片clip
    files = sorted(os.listdir(product_dir)) # 获取产品目录下所有文件并排序，确保视频按数字顺序拼接
    for f in files: # 遍历排序后的文件列表
        name, ext = os.path.splitext(f) # 获取不带扩展名的文件名和扩展名
        if name.isdigit() and ext.lower() == '.mp4': # 判断文件是否为纯数字命名且是mp4格式
            vid_path = os.path.join(product_dir, f) # 拼接当前视频文件的绝对路径
            vid_clip = VideoFileClip(vid_path) # 加载视频文件为VideoFileClip
            vw, vh = vid_clip.size # 获取当前视频的宽度和高度
            target_ratio = target_w / target_h # 计算目标宽高比
            vid_ratio = vw / vh # 计算当前视频宽高比
            if vid_ratio > target_ratio: # 判断视频是否比目标更宽
                crop_w = int(vh * target_ratio) # 如果更宽，则以高度为基准计算裁剪宽度
                vid_clip = vid_clip.crop(x_center=vw/2.0, y_center=vh/2.0, width=crop_w, height=vh) # 以中心为基准进行宽度裁剪
            else: # 如果视频比目标更窄或等宽
                crop_h = int(vw / target_ratio) # 以宽度为基准计算裁剪高度
                vid_clip = vid_clip.crop(x_center=vw/2.0, y_center=vh/2.0, width=vw, height=crop_h) # 以中心为基准进行高度裁剪
            vid_clip = vid_clip.resize((target_w, target_h)) # 将裁剪后的视频缩放到与首图完全一致的尺寸
            
            if watermark_clip: # 如果存在水印片段
                current_watermark = watermark_clip.set_duration(vid_clip.duration) # 设置当前水印持续时间与视频相同
                vid_clip = CompositeVideoClip([vid_clip, current_watermark]) # 将视频片段和水印片段合成
                
            vid_clip = vid_clip.crossfadein(1.0) # 为当前视频片段添加1秒的渐变过渡效果
            clips.append(vid_clip) # 将处理好的视频片段添加到拼接列表中
    if len(clips) == 1: # 判断是否只有首图，如果没有找到视频则直接返回
        print("未找到需要拼接的数字视频文件") # 打印没有找到视频的提示
        return "" # 返回空字符串
    final_video = concatenate_videoclips(clips, method="compose", padding=-1.0) # 使用compose方法拼接视频片段，设置padding为-1秒以实现渐变重叠效果
    final_video = final_video.without_audio() # 移除最终合成视频的所有声音轨道，确保输出静音视频
    output_path = os.path.join(product_dir, "index.mp4") # 拼接输出视频的绝对路径
    final_video.write_videofile(output_path, fps=24, logger=None, audio=False) # 将最终合成的视频写入文件，设置帧率为24，禁用声音输出，并屏蔽冗余日志
    final_video.close() # 关闭最终视频对象释放资源
    for c in clips: # 遍历所有使用过的clip释放资源
        c.close() # 关闭clip对象
    print(f"成功生成产品视频: {output_path}") # 打印视频生成成功的提示信息
    return output_path # 返回生成的视频绝对路径

def generate_product_video2(target_product: dict) -> str: # 定义生成产品视频的方法
    if not target_product: # 检查传入的 target_product 是否为空
        print("传入的产品对象为空，跳过生成视频2") # 打印跳过提示
        return "" # 返回空字符串结束方法
        
    product_no = target_product.get('productNo', '').replace('#', '') # 获取产品编号并移除可能存在的#号
    product_dir = os.path.join(PRODUCT_HOME_PATH, "images", "products", product_no) # 拼接出产品的图片存放绝对路径
    image_path = os.path.join(product_dir, "script.png") # 拼接目标图片的绝对路径，文件名为scripe.png
    
    if not os.path.exists(image_path): # 判断目标图片文件是否存在
        print(f"未找到图片文件: {image_path}") # 如果文件不存在则打印提示信息
        return "" # 返回空字符串表示生成失败
    print(image_path)   
    url = "http://127.0.0.1:8200/vi/sd/create" # 设置调用生成视频接口的URL
    payload = { # 构造请求体的字典数据
        "text_prompt": "参考图1是分镜图 请根据分镜图生成视频 ，过渡不要太生硬", # 设置生成视频的默认文本提示词
        "image_path": image_path # 设置用于生成视频的参考图片绝对路径
    } # 结束字典构造
    
    try: # 尝试执行网络请求
        response = requests.post(url, json=payload) # 发送POST请求调用接口
        response.raise_for_status() # 检查HTTP响应状态码是否正常
        result = response.json() # 将响应的JSON数据解析为Python对象
        
        if result and isinstance(result, list) and len(result) > 0: # 判断返回的结果是否为包含路径的列表
            source_video_path = result[0] # 获取列表中返回的第一个视频绝对路径
            target_video_path = os.path.join(product_dir, "video.mp4") # 拼接需要保存到产品文件夹中的目标视频路径
            
            import shutil # 导入shutil模块用于文件操作
            shutil.copy(source_video_path, target_video_path) # 将生成的视频文件复制到产品的文件夹中并命名为video.mp4
            print(f"成功生成并保存视频: {target_video_path}") # 打印视频保存成功的提示信息
            return target_video_path # 返回最终保存的视频绝对路径
        else: # 如果返回的结果不符合预期
            print(f"接口返回的数据异常: {result}") # 打印异常的数据信息
            return "" # 返回空字符串
            
    except Exception as e: # 捕获请求或处理过程中发生的异常
        print(f"生成视频时发生错误: {e}") # 打印具体的错误信息
        return "" # 发生错误时返回空字符串






def generate_products():


    # 测试用例
    for i in range(503, 509): # 遍历从810到832的产品编号
        product = get_product_by_no(f"{i}")
        #generated_image_path = generate_product_image(product)  
        #generate_product_index_image(product, generated_image_path)
        #generate_product_title(product,  ['9088纯棉平布', '水洗棉布'])
        generate_product_wx_image(product)
        generate_product_wx_info(product)
        pass

def generate_product() -> str: # 定义生成产品视频的方法
    product_no = "501"
    product = get_product_by_no(product_no)

    if product:
        # 1、生成文案
        #generate_product_info(product)
        
        # 2、生成首图
        #generated_image_path = generate_product_image(product)  
        #generate_product_index_image(product, generated_image_path)

        # 3、生成分镜图
        #color = generate_product_part30_image(product)  
        #color = generate_product_part40_image(product,color)  
        #color = generate_product_part50_image(product,color)  
        #color = generate_product_part60_image(product,color)  
        # 3、生成详情图片
        #generate_product_info_image(product)

        # 4、拍摄色卡、细节图、产品视频

        # 5、规整图片视频尺寸
        #format_image_size(product)
        
        # 6、生成视频
        #generate_product_video(product)

        # 7、生成标题
        #generate_product_title(product, ['棉麻布料', '纯棉布料', '面料布料服装', '天丝面料'])

        # 8、朋友圈
        #generate_product_wx_image(product)
        generate_product_wx_info(product)
        pass


def fix_product_title() -> str: # 定义修复产品标题的方法
    product_no = "920"
    product = get_product_by_no(product_no)
    name = product.get("name", "") # 获取产品的名称

    title = f"""3068麻棉9088纯棉平布水洗棉布面料柔软透气四季可用家居服装手工
    """
    advice = f"""
标题结构：	
标题结构较差，缺少"促销词"。
标题内容：	
标题内容丰富。
重复词：	
很好，没有重复的词
促销词：	
没有促销词
标题长度：	
标题长度60。标题长度合理
空格：	
标题中无空格。适当的空格有助于阅读
标点符号：	
很好，标题中没有标点符号
全角字母：	
没有全角字母或数字
违禁词：	
没有违禁词
广告词：	
没有广告禁止词
找工厂：	
不是找工厂产品
    """
    system_prompt = f"""你作为1688运营专家，深度理解标签规则，在原标题上修正，商品{name}，
    行业词有【'棉麻布料', '纯棉布料', '面料布料服装', '天丝面料'】，原标题：{title}，修改意见：{advice}"""
    print(system_prompt)
    response = _jiekou_chat( system_prompt, # 调用接口生成商品副标题的文本
        user_prompt=f"在推荐3个标题提高流量" # 传入拼接好的商品信息
    ) # 结束接口调用    
    content_text = "" # 初始化存放模型返回文本的变量
    
    if response: # 判断接口返回是否为空
        if hasattr(response, 'choices') and len(response.choices) > 0: # 判断返回对象是否包含choices属性（处理API对象结构）
            content_text = response.choices[0].message.content # 提取出真正的文本内容
        elif isinstance(response, dict) and 'choices' in response: # 判断返回对象是否为字典且包含choices键
            content_text = response['choices'][0]['message']['content'] # 从字典中提取出真正的文本内容      
    print(content_text)







if __name__ == "__main__":
    generate_product()
    #fix_product_title()
