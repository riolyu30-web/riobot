# image_html_utils.py
import os # 导入操作系统接口模块
import re # 导入正则表达式模块，用于HTML内容替换
import threading # 导入线程锁模块，用于处理并发文件写入

html_file_lock = threading.Lock() # 定义全局线程锁，防止多线程并发操作同一个文件导致冲突

def initialize_image_html_with_loading(html_path: str) -> str: # 定义函数，用于初始化HTML文件，包含加载提示
    with html_file_lock: # 获取线程锁
        if os.path.exists(html_path): # 检查HTML文件是否已经存在
            return html_path # 如果文件存在，则直接返回路径，不进行覆盖

        template = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <title>图片展示</title>
    <style>
        body {{ display: flex; flex-direction: column; align-items: center; background-color: #f0f0f0; padding: 20px; font-family: Arial, sans-serif; margin: 0; }}
        .image-gallery {{ display: flex; flex-wrap: wrap; justify-content: center; gap: 20px; width: 100%; max-width: 100%; padding: 0 20px; box-sizing: border-box; }}
        .image-container {{
            display: flex;
            flex-direction: row;
            align-items: stretch;
            background-color: #fff;
            border-radius: 8px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            padding: 15px;
            width: 600px; /* 加宽以适应左右布局 */
            max-width: 100%;
            box-sizing: border-box;
        }}
        .image-container > a {{
            flex-shrink: 0;
            display: flex;
            align-items: center;
        }}
        .image-container img {{
            max-width: 250px;
            max-height: 250px;
            height: auto;
            border-radius: 4px;
            object-fit: contain;
        }}
        .text-container {{
            display: flex;
            flex-direction: column;
            margin-left: 15px;
            flex: 1;
            overflow: hidden; /* 防止内容撑破容器 */
        }}
        .text-container .image-path {{
            font-size: 9px;
            color: #888;
            margin: 0 0 5px 0;
            word-break: break-all;
            cursor: pointer;
        }}
        .text-container .description {{
            font-size: 12px;
            color: #333;
            margin: 0;
            padding: 0;
            flex: 1; /* 占据剩余高度 */
            overflow: hidden; /* 裁切长于图片的部分 */
            white-space: pre-wrap; /* 保留空白符和换行符 */
            cursor: pointer;
        }}
        .loading {{ font-size: 24px; color: #555; }}
    </style>
    <script>
        function copyToClipboard(text) {{
            navigator.clipboard.writeText(text).then(function() {{
                alert('已复制到剪贴板:\\n' + text);
            }}, function(err) {{
                console.error('无法复制文本: ', err);
            }});
        }}
    </script>
</head>
<body>
    <div id="loading-message">
        <p class="loading">图片生成中，请稍候...</p>
    </div>
    <div class="image-gallery">
        <!-- 图片将追加到这里 -->
    </div>
</body>
</html>""" # 定义基础的HTML模版，包含加载提示和图片画廊容器
        
        with open(html_path, "w", encoding="utf-8") as f: # 以写入模式创建HTML文件
            f.write(template) # 将基础模版写入文件
            
        return html_path # 返回HTML文件的绝对路径

def append_image_to_html(html_path: str, image_abs_path: str, image_prompt: str,description: str) -> str: # 定义函数，用于将新生成的图片追加到HTML文件中，并显示提示词
    with html_file_lock: # 获取线程锁，防止并发读取和覆盖写入时导致文件损坏
        # 直接使用绝对路径
        image_absolute_path = image_abs_path.replace(chr(92), "/") # 将绝对路径的斜杠替换为正斜杠，用于 HTML
       
        with open(html_path, "r", encoding="utf-8") as f: # 以读取模式打开已存在的HTML文件
            content = f.read() # 读取现有的HTML内容
            
        # 移除加载消息（如果存在）
        if '<div id="loading-message">' in content: # 如果HTML内容中包含加载消息
            content = re.sub(r'<div id="loading-message">.*?</div>', '', content, flags=re.DOTALL) # 使用正则表达式移除加载消息
            
        # 将新图片和提示词追加到 image-gallery 中
        img_and_prompt_html = f"""        <div class="image-container">
            <a href="file:///{image_absolute_path}" target="_blank">
                <img src="file:///{image_absolute_path}" alt="{image_prompt}" title="{image_prompt}">
            </a>
            <div class="text-container">
                <p class="image-path" title="{image_absolute_path}" onclick="copyToClipboard(this.innerText)">{image_absolute_path}</p>
                <p class="description" title="{description}" onclick="copyToClipboard(this.innerText)">{description}</p>
            </div>
        </div>""" # 构建要追加的图片和提示词的HTML结构
        
        # 查找 image-gallery 结束标签，在其之前插入新图片和提示词
        updated_content = content.replace('        <!-- 图片将追加到这里 -->', f'{img_and_prompt_html}\n        <!-- 图片将追加到这里 -->') # 在注释行上方插入图片和提示词的HTML结构
        
        with open(html_path, "w", encoding="utf-8") as f: # 以写入模式重新打开该HTML文件
            f.write(updated_content) # 将更新后的内容写入文件
            
        return html_path # 返回最终生成的HTML文件绝对路径
