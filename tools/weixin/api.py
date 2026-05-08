# api.py
# 导入FastAPI相关模块
from fastapi import APIRouter, HTTPException
# 导入Path用于路径操作
from pathlib import Path
# 导入BaseModel用于定义请求体模型
from pydantic import BaseModel
# 导入ILinkApi用于调用底层发送接口
from wechatbot.protocol import ILinkApi
# 导入load_credentials用于读取凭证文件
from wechatbot.auth import load_credentials

# 创建APIRouter实例
router = APIRouter()

# 定义请求体数据模型
class SendMessageRequest(BaseModel):
    # 定义text字段，接收要发送的文案
    text: str
    # 定义user_id字段，选填，如果不填则发给配置中的默认用户
    user_id: str | None = None

# 定义发送消息的POST接口
@router.post("/send")
# 定义异步处理函数
async def send_wechat_message(req: SendMessageRequest):
    # 定义凭证文件的绝对路径
    cred_path = Path(r"c:\develop\nanobot\.nanobot\credentials.json")
    
    try:
        # 尝试从文件中加载微信登录凭证
        creds = await load_credentials(cred_path)
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

