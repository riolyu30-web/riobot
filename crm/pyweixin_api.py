from fastapi import APIRouter, Request, HTTPException, UploadFile, File, Query # 导入 FastAPI 相关的组件
from pydantic import BaseModel # 导入 BaseModel 用于定义请求体数据模型
from typing import List, Optional # 导入类型提示，用于指定可选参数和列表类型
from pyweixin import Messages, FriendSettings # 从 pyweixin 模块中导入处理消息和好友设置的工具类

wx_router = APIRouter() # 创建一个名为 wx_router 的 API 路由对象

class SendMessagesRequest(BaseModel): # 定义发送消息请求的数据模型
    friend: str # 好友名称或群聊备注，必填
    messages: List[str] # 需要发送的消息内容列表，必填
    at_members: Optional[List[str]] = [] # 需要@的群成员列表，选填，默认为空列表
    at_all: Optional[bool] = False # 是否@所有人，选填，默认为 False
    search_pages: Optional[int] = None # 查找好友的翻页次数，选填
    clear: Optional[bool] = None # 是否清除聊天框已有内容，选填
    send_delay: Optional[float] = None # 发送多条消息之间的延迟时间，选填
    is_maximize: Optional[bool] = None # 微信窗口是否最大化，选填
    close_weixin: Optional[bool] = None # 发送完毕后是否关闭微信窗口，选填

class AddFriendRequest(BaseModel): # 定义添加好友请求的数据模型
    number: str # 需要添加的微信号或手机号，必填
    greetings: Optional[str] = None # 添加好友时的打招呼用语，选填
    remark: Optional[str] = None # 给好友设置的备注名，选填
    chat_only: Optional[bool] = False # 是否设置权限为“仅聊天”，选填，默认为 False
    is_maximize: Optional[bool] = None # 微信窗口是否最大化，选填
    close_weixin: Optional[bool] = None # 添加完毕后是否关闭微信窗口，选填

@wx_router.post("/wx/send_messages") # 定义处理 POST 请求的路由 /send_messages
async def send_messages(request: SendMessagesRequest): # 接收符合 SendMessagesRequest 模型的请求体数据
    """
    单聊发送文本
    """
    try: # 尝试执行发送消息的逻辑
        Messages.send_messages_to_friend( # 调用 pyweixin 中的发送消息方法
            friend=request.friend, # 传入目标好友名称
            messages=request.messages, # 传入要发送的消息列表
            at_members=request.at_members, # 传入需要@的成员列表
            at_all=request.at_all, # 传入是否@所有人参数
            search_pages=request.search_pages, # 传入搜索页数配置
            clear=request.clear, # 传入是否清空输入框配置
            send_delay=request.send_delay, # 传入发送延迟时间配置
            is_maximize=request.is_maximize, # 传入是否最大化配置
            close_weixin=request.close_weixin # 传入是否关闭微信配置
        ) # 发送方法调用结束
        return {"code": 200, "message": "success"} # 发送成功，返回成功状态码及信息
    except Exception as e: # 如果发生异常，捕获异常对象 e
        raise HTTPException(status_code=500, detail=str(e)) # 抛出 500 错误，并返回异常的具体信息

@wx_router.get("/wx/get_messages") # 定义处理 GET 请求的路由 /get_messages
async def get_messages( # 定义获取消息的异步函数
    friend: str = Query(..., description="好友名称或群聊备注"), # 接收好友名称作为必填的查询参数
    number: int = Query(100, description="获取的消息数量"), # 接收获取数量作为查询参数，默认 100
    with_sender: bool = Query(False, description="是否区分发送者"), # 接收是否区分发送者作为查询参数，默认 False
    search_pages: Optional[int] = Query(None, description="查找好友翻页次数"), # 接收翻页次数作为选填查询参数
    is_maximize: Optional[bool] = Query(None, description="微信界面是否全屏"), # 接收是否最大化作为选填查询参数
    close_weixin: Optional[bool] = Query(None, description="任务结束后是否关闭微信") # 接收是否关闭微信作为选填查询参数
): # 函数参数定义结束
    """
    获取某会话对话
    """
    try: # 尝试执行获取消息的逻辑
        if with_sender: # 判断请求是否要求区分发送者
            msgs = Messages.pull_messages_with_sender( # 如果要求，调用能够区分发送者的方法
                friend=friend, # 传入目标好友名称
                number=number, # 传入要获取的消息数量
                search_pages=search_pages, # 传入搜索页数配置
                is_maximize=is_maximize, # 传入是否最大化配置
                close_weixin=close_weixin # 传入是否关闭微信配置
            ) # 带发送者的消息获取完毕
        else: # 如果请求不需要区分发送者
            msgs = Messages.pull_messages( # 调用普通的获取消息方法
                friend=friend, # 传入目标好友名称
                number=number, # 传入要获取的消息数量
                search_pages=search_pages, # 传入搜索页数配置
                is_maximize=is_maximize, # 传入是否最大化配置
                close_weixin=close_weixin # 传入是否关闭微信配置
            ) # 普通消息获取完毕
        return {"code": 200, "data": msgs} # 获取成功，返回成功状态码及获取到的消息数据
    except Exception as e: # 如果发生异常，捕获异常对象 e
        raise HTTPException(status_code=500, detail=str(e)) # 抛出 500 错误，并返回异常的具体信息

@wx_router.post("/wx/add_friend") # 定义处理 POST 请求的路由 /add_friend
async def add_friend(request: AddFriendRequest): # 接收符合 AddFriendRequest 模型的请求体数据
    """
    加好友
    """
    try: # 尝试执行添加好友的逻辑
        FriendSettings.add_new_friend( # 调用 pyweixin 中的添加好友方法
            number=request.number, # 传入需要添加的微信号或手机号
            greetings=request.greetings, # 传入添加时的打招呼用语
            remark=request.remark, # 传入给该好友设置的备注
            chat_only=request.chat_only, # 传入是否仅聊天权限的配置
            is_maximize=request.is_maximize, # 传入是否最大化配置
            close_weixin=request.close_weixin # 传入是否关闭微信配置
        ) # 添加好友方法调用结束
        return {"code": 200, "message": "success"} # 添加成功，返回成功状态码及信息
    except Exception as e: # 如果发生异常，捕获异常对象 e
        raise HTTPException(status_code=500, detail=str(e)) # 抛出 500 错误，并返回异常的具体信息


