# 导入FastAPI模块
from fastapi import APIRouter, Request, HTTPException # 导入路由器、请求类和HTTP异常
import asyncio # 导入 asyncio 模块用于异步操作
# 导入Pydantic的BaseModel用于数据验证
from pydantic import BaseModel # 导入基础模型类
# 从服务层导入接口函数
from .dashscope_manager import dashscope_happy_create,get_dashscope_task_status
from .jiekou_manager import jiekou_sd2,jiekou_query_task_status



# 定义图生视频请求体的数据模型
class Image2VideoRequest(BaseModel):
    # 文本提示词
    text_prompt: str
    # 图片路径
    image_path: str

# 定义API路由器
router = APIRouter() # 创建APIRouter实例

# 定义图生视频接口
@router.post("/hh/create") # 定义POST路由路径
async def happy_create(request: Image2VideoRequest): # 定义异步处理函数
    # 调用 dashscope_happy_create 获取任务 ID
    create_result = dashscope_happy_create(
        prompt=request.text_prompt,
        first_frame_image=request.image_path
    )
    
    if create_result.get("error"): # 如果创建任务失败
        raise HTTPException(status_code=500, detail=f"Task creation failed: {create_result['error']}") # 抛出HTTP异常
    
    task_id = create_result.get("output", {}).get("task_id") # 获取任务ID
    if not task_id: # 如果没有获取到任务 ID
        raise HTTPException(status_code=500, detail="Failed to get task ID from DashScope") # 抛出HTTP异常

    # 循环查询任务状态
    while True: # 无限循环
        task_result = get_dashscope_task_status(task_id) # 查询任务状态
        
        if task_result.get("error"): # 如果查询任务状态失败
            raise HTTPException(status_code=500, detail=f"Task status query failed: {task_result['error']}") # 抛出HTTP异常

        task_status = task_result.get("output", {}).get("task_status") # 获取任务状态
        
        if task_status == "SUCCEEDED": # 如果任务成功
            downloaded_paths = task_result.get("downloaded_paths", []) # 获取本地视频路径列表
            if downloaded_paths: # 如果本地视频路径存在
                return downloaded_paths # 返回视频路径列表
            else: # 如果没有本地视频路径
                raise HTTPException(status_code=500, detail="Task succeeded but no local video path found") # 抛出HTTP异常
        elif task_status == "FAILED": # 如果任务失败
            reason = task_result.get("output", {}).get("message", "Unknown error") # 获取失败原因
            raise HTTPException(status_code=500, detail=f"Task failed: {reason}") # 抛出HTTP异常
        elif task_status == "CANCELED": # 如果任务已取消
            raise HTTPException(status_code=500, detail="Task was canceled") # 抛出HTTP异常
        elif task_status == "PENDING" or task_status == "RUNNING": # 如果任务排队中或处理中
            print(f"DashScope Task {task_id} status: {task_status}") # 打印任务状态
            await asyncio.sleep(5) # 等待5秒后再次查询
        else: # 其他未知状态
            raise HTTPException(status_code=500, detail=f"Unknown task status: {task_status}") # 抛出HTTP异常


# 定义SD生成接口
@router.post("/sd/create") # 定义POST路由路径
async def sd_create(request: Image2VideoRequest): # 定义异步处理函数
    reference_images = [request.image_path]
    task_id = jiekou_sd2(prompt=request.text_prompt, reference_images=reference_images) # 调用 jiekou_sd2 获取任务 ID
    if not task_id: # 如果没有获取到任务 ID
        raise HTTPException(status_code=500, detail=f"Task failed: 图片或提示词违规.") # 抛出HTTP异常，包含失败原因

    # 循环查询任务状态
    while True: # 无限循环
        task_result = jiekou_query_task_status(task_id) # 查询任务状态
        status = task_result.get("task", {}).get("status") # 获取任务状态
        if status == "TASK_STATUS_SUCCEED": # 如果任务成功
            # 如果任务成功，提取视频或图片路径并返回
            if task_result.get("videos"): # 如果有视频结果
                return task_result["downloaded_paths"] # 返回视频路径列表
            elif task_result.get("images"): # 如果有图片结果
                return task_result["downloaded_paths"] # 返回图片路径列表
            else: # 如果没有视频或图片结果
                raise HTTPException(status_code=500, detail="Task succeeded but no media found") # 抛出HTTP异常，表示任务成功但未找到媒体文件
        elif status == "TASK_STATUS_FAILED": # 如果任务失败
            reason = task_result.get("task", {}).get("reason", "Unknown error") # 获取失败原因
            raise HTTPException(status_code=500, detail=f"Task failed: {reason}") # 抛出HTTP异常，包含失败原因
        elif status == "TASK_STATUS_QUEUED" or status == "TASK_STATUS_PROCESSING": # 如果任务排队中或处理中
            print(f"SD2 Task {task_id} status: {status}")
            await asyncio.sleep(5) # 等待5秒后再次查询
        else: # 其他未知状态
            raise HTTPException(status_code=500, detail=f"Unknown task status: {status}") # 抛出HTTP异常，表示未知任务状态
