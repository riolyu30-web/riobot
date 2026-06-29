# api.py
# 导入FastAPI相关模块
from fastapi import APIRouter, HTTPException
# 导入Path用于路径操作
from pathlib import Path
import os # 导入 os 模块
# 导入BaseModel用于定义请求体模型
from pydantic import BaseModel
import io # 导入io用于处理内存中的图像数据
from PIL import Image # 导入Pillow库用于图像处理
# 导入ILinkApi用于调用底层发送接口
from wechatbot.protocol import ILinkApi
# 导入load_credentials用于读取凭证文件
from wechatbot.auth import load_credentials

# 导入WeChatBot及相关类型用于图片发送
from wechatbot.client import WeChatBot, _cdn_media_dict
from wechatbot.types import MediaType, MessageItemType

# 创建APIRouter实例
router = APIRouter()

# 定义请求体数据模型
class SendMessageRequest(BaseModel):
    # 定义text字段，接收要发送的文案
    text: str
    # 定义user_id字段，选填，如果不填则发给配置中的默认用户
    user_id: str | None = None

    path: str | None = None

# 定义发送消息的POST接口
@router.post("/message")
# 定义异步处理函数
async def send_wechat_message(req: SendMessageRequest):

    try:
        # 尝试从文件中加载微信登录凭证
        creds = await load_credentials(path=Path(req.path) if req.path else None)
    except Exception as e:
        # 如果加载报错，则抛出500服务端异常
        raise HTTPException(status_code=500, detail=f"加载凭证失败: {e}")
    
    # 判断凭证是否成功获取
    if not creds:
        # 如果没有凭证，则抛出401未授权异常
        raise HTTPException(status_code=401, detail="未找到微信登录凭证")
    
    # 确定要发送的目标用户ID，如果指定为 "filehelper" 或未传，则默认发给凭证中的自己（即文件传输助手）
    if not req.user_id or req.user_id == "filehelper":
        target_user_id = creds.user_id
    else:
        target_user_id = req.user_id
    
    # 检查目标用户ID是否为空
    if not target_user_id:
        # 为空则抛出400参数异常
        raise HTTPException(status_code=400, detail="缺少目标用户ID")
    
    # 实例化ILinkApi客户端
    api = ILinkApi()
    
    # 构造发送文本消息的数据结构，context_token置空
    msg = api.build_text_message(target_user_id, "", req.text)
    
    try:
        # 调用底层接口向微信发送消息
        res = await api.send_message(creds.base_url, creds.token, msg)
        # 返回成功响应及结果数据
        return {"success": True, "response": res}
    except Exception as e:
        # 捕获发送过程中的异常并返回500错误
        raise HTTPException(status_code=500, detail=f"发送消息失败: {e}")

# 定义发送媒体文件的请求体数据模型
class SendMediaRequest(BaseModel):
    # 定义file_path字段，接收媒体文件的绝对路径
    file_path: str
    # 定义media_type字段，选填，指定媒体类型(1=IMAGE, 2=VIDEO, 3=FILE, 4=VOICE)，默认为IMAGE
    media_type: int = MediaType.IMAGE
    # 定义user_id字段，选填，如果不填则发给配置中的默认用户
    user_id: str | None = None
    
    path: str | None = None

    # 定义spec字段，选填，指定图片规格(原图, 1:1, 4:3, 16:9)，默认为原图
    spec: str = "原图"

# 私有方法：根据指定规格拉伸调整图像比例
def _resize_image_by_spec(file_data: bytes, spec: str) -> bytes:
    if spec == "原图" or not spec: # 如果是原图或未指定，直接返回原数据
        return file_data
    
    try:
        # 使用Pillow打开图像
        image = Image.open(io.BytesIO(file_data))
        width, height = image.size # 获取原图宽高
        
        # 根据不同规格计算目标比例
        if spec == "1:1":
            target_ratio = 1.0 # 目标比例 1:1
        elif spec == "4:5":
            target_ratio = 4.0 / 5.0 # 目标比例 4:5
        elif spec == "16:9":
            target_ratio = 16.0 / 9.0 # 目标比例 16:9
        elif spec == "3:4":
            target_ratio = 3.0 / 4.0 # 目标比例 3:4
        elif spec == "9:16":
            target_ratio = 9.0 / 16.0 # 目标比例 9:16
        elif spec == "1.91:1":
            target_ratio = 1.91 / 1.0 # 目标比例 1.91:1
        else:
            return file_data # 不支持的规格直接返回原图
            
        current_ratio = width / height # 计算当前比例
        
        # 以拉伸的方式调整图片（保持高度不变，拉伸宽度；或者保持宽度不变，拉伸高度）
        # 这里选择简单粗暴地直接修改宽高，即不裁剪，直接拉伸导致变形
        if current_ratio > target_ratio:
            # 原图比较宽，要达到目标比例，需要缩小宽度或增加高度，这里选择保持高度，压缩宽度
            new_width = int(height * target_ratio)
            new_height = height
        else:
            # 原图比较高，要达到目标比例，需要增加宽度或缩小高度，这里选择保持宽度，压缩高度
            new_width = width
            new_height = int(width / target_ratio)
            
        # 执行拉伸调整尺寸
        resized_image = image.resize((new_width, new_height), Image.Resampling.LANCZOS)
        
        # 将调整后的图像保存到内存并返回字节数据
        output = io.BytesIO()
        # 尝试保持原格式，如果是JPEG，需要处理RGBA转换为RGB
        img_format = image.format if image.format else 'JPEG'
        if img_format == 'JPEG' and resized_image.mode == 'RGBA':
            resized_image = resized_image.convert('RGB')
        resized_image.save(output, format=img_format)
        return output.getvalue()
        
    except Exception as e:
        print(f"图像尺寸调整失败: {e}")
        return file_data # 如果处理失败，退回到返回原图数据

# 定义发送媒体文件的POST接口
@router.post("/media")
# 定义异步处理函数
async def send_wechat_media(req: SendMediaRequest):
    # 将传入的路径转为Path对象
    file_path = Path(req.file_path)
    
    # 检查媒体文件是否存在
    if not file_path.exists() or not file_path.is_file():
        raise HTTPException(status_code=400, detail="媒体文件不存在或无效")
    
    # 读取媒体文件二进制数据
    try:
        file_data = file_path.read_bytes()
        
        # 如果是图片类型且指定了规格，调用私有方法处理图片比例拉伸
        if req.media_type == MediaType.IMAGE and req.spec and req.spec != "原图":
            file_data = _resize_image_by_spec(file_data, req.spec)
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"读取或处理媒体文件失败: {e}")

    try:
        # 尝试从文件中加载微信登录凭证
        creds = await load_credentials(path=Path(req.path) if req.path else None)
    except Exception as e:
        # 如果加载报错，则抛出500服务端异常
        raise HTTPException(status_code=500, detail=f"加载凭证失败: {e}")
    
    # 判断凭证是否成功获取
    if not creds:
        # 如果没有凭证，则抛出401未授权异常
        raise HTTPException(status_code=401, detail="未找到微信登录凭证")
    
    # 确定要发送的目标用户ID，如果指定为 "filehelper" 或未传，则默认发给凭证中的自己（即文件传输助手）
    if not req.user_id or req.user_id == "filehelper":
        target_user_id = creds.user_id
    else:
        target_user_id = req.user_id
    
    # 检查目标用户ID是否为空
    if not target_user_id:
        # 为空则抛出400参数异常
        raise HTTPException(status_code=400, detail="缺少目标用户ID")

    # 实例化WeChatBot客户端以便复用其上传CDN的能力
    bot = WeChatBot()
    # 临时把凭证注入给bot实例
    bot._credentials = creds
    
    try:
        # 调用bot封装的方法将媒体文件上传至微信CDN，并指定媒体类型
        upload_result = await bot.upload(file_data, target_user_id, req.media_type)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"媒体文件上传CDN失败: {e}")

    # 根据不同的媒体类型构造不同的 item_list 数据结构
    if req.media_type == MediaType.IMAGE:
        item_list = [{
            "type": int(MessageItemType.IMAGE),
            "image_item": {
                "media": _cdn_media_dict(upload_result.media),
                "mid_size": upload_result.encrypted_file_size,
            }
        }]
    elif req.media_type == MediaType.VIDEO:
        item_list = [{
            "type": int(MessageItemType.VIDEO),
            "video_item": {
                "media": _cdn_media_dict(upload_result.media),
                "video_size": upload_result.encrypted_file_size,
            }
        }]
    elif req.media_type == MediaType.FILE:
        item_list = [{
            "type": int(MessageItemType.FILE),
            "file_item": {
                "media": _cdn_media_dict(upload_result.media),
                "file_name": file_path.name,
                "len": str(len(file_data)),
            }
        }]
    elif req.media_type == MediaType.VOICE:
        item_list = [{
            "type": int(MessageItemType.VOICE),
            "voice_item": {
                "media": _cdn_media_dict(upload_result.media),
                "voice_format": 0,
            }
        }]
    else:
        raise HTTPException(status_code=400, detail="不支持的媒体类型")

    # 实例化ILinkApi客户端
    api = ILinkApi()
    
    # 调用底层接口构造发送媒体消息的数据结构，context_token置空
    msg = api.build_media_message(target_user_id, "", item_list)
    
    try:
        # 调用底层接口向微信发送消息
        res = await api.send_message(creds.base_url, creds.token, msg)
        # 返回成功响应及结果数据
        return {"success": True, "response": res}
    except Exception as e:
        # 捕获发送过程中的异常并返回500错误
        raise HTTPException(status_code=500, detail=f"发送媒体文件失败: {e}")




@router.get("/list")
# 定义异步处理函数
async def send_wechat_list():
    config_dir = Path(__file__).parent / "config" # 获取当前文件所在目录下的config文件夹路径
    json_files = [] # 初始化一个空列表来存储符合条件的JSON文件路径

    if config_dir.is_dir(): # 检查config文件夹是否存在
        for file_path in config_dir.iterdir(): # 遍历config文件夹中的所有文件和子目录
            if file_path.is_file() and file_path.suffix == ".json": # 检查是否是文件且扩展名为.json
                file_name_without_ext = file_path.stem # 获取不带扩展名的文件名
                if file_name_without_ext.isalpha(): # 检查文件名是否全部由字母组成
                    json_files.append(str(file_path.resolve())) # 将文件的绝对路径添加到列表中

    return  {"success": True, "response": json_files} # 返回包含JSON文件绝对路径的字典
