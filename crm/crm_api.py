from fastapi import APIRouter, Request, HTTPException, UploadFile, File
import re
import os
import random
import warnings
from typing import List
import json
from models import get_session, Company, Contact, Tag, Friend, Sales
from xunkebao import search_account
from pyweixin import FriendSettings
# 导入 tempfile 模块用于创建临时文件
import tempfile
# 从 ocr_manager 导入 get_text 函数
from ocr_manager import get_text

api_router = APIRouter()

import subprocess
import threading
import sys

# 存储后台任务的进程引用
background_processes = {}

# 启动监听搜索词的后台任务
@api_router.post("/system/listen_keyword_bank")
async def start_listen_keyword_bank():
    # 接口文档说明
    """启动监听搜索词"""
    try:
        # 如果之前已经启动过且还在运行，先尝试终止它
        if "listen_keyword_bank" in background_processes:
            # 获取旧的进程对象
            old_p = background_processes["listen_keyword_bank"]
            # 检查进程是否还在运行
            if old_p.poll() is None:
                # 终止进程
                old_p.terminate()
        
        # 使用 subprocess 在后台运行脚本
        p = subprocess.Popen([sys.executable, "listen_keyword_bank.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
        # 保存进程对象到全局字典中
        background_processes["listen_keyword_bank"] = p
        
        # 返回成功消息
        return {"message": "监听搜索词任务已启动"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 关闭监听搜索词的后台任务
@api_router.post("/system/stop_listen_keyword_bank")
async def stop_listen_keyword_bank():
    # 接口文档说明
    """关闭监听搜索词"""
    try:
        # 检查是否在全局字典中记录了该任务
        if "listen_keyword_bank" in background_processes:
            # 获取进程对象
            p = background_processes["listen_keyword_bank"]
            # 检查进程是否还在运行
            if p.poll() is None:
                # 终止进程
                p.terminate()
                # 等待进程退出
                p.wait()
            # 从字典中移除该任务
            del background_processes["listen_keyword_bank"]
            # 返回成功消息
            return {"message": "监听搜索词任务已关闭"}
        else:
            # 如果没有记录，尝试使用 Windows 命令行强制终止残留进程
            if os.name == 'nt':
                # 调用 wmic 命令终止所有执行该脚本的 Python 进程
                os.system('wmic process where "name=\'python.exe\' and commandline like \'%listen_keyword_bank.py%\'" call terminate')
            # 返回提示消息
            return {"message": "未在记录中找到运行的任务，已尝试通过系统命令清理"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 启动监听公司的后台任务
@api_router.post("/system/listen_company")
async def start_listen_company():
    # 接口文档说明
    """启动监听公司"""
    try:
        # 如果之前已经启动过且还在运行，先尝试终止它
        if "listen_company" in background_processes:
            # 获取旧的进程对象
            old_p = background_processes["listen_company"]
            # 检查进程是否还在运行
            if old_p.poll() is None:
                # 终止进程
                old_p.terminate()
                
        # 使用 subprocess 在后台运行脚本
        p = subprocess.Popen([sys.executable, "listen_keyword_company.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
        # 保存进程对象到全局字典中
        background_processes["listen_company"] = p
        
        # 返回成功消息
        return {"message": "监听公司任务已启动"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 关闭监听公司的后台任务
@api_router.post("/system/stop_listen_company")
async def stop_listen_company():
    # 接口文档说明
    """关闭监听公司"""
    try:
        # 检查是否在全局字典中记录了该任务
        if "listen_company" in background_processes:
            # 获取进程对象
            p = background_processes["listen_company"]
            # 检查进程是否还在运行
            if p.poll() is None:
                # 终止进程
                p.terminate()
                # 等待进程退出
                p.wait()
            # 从字典中移除该任务
            del background_processes["listen_company"]
            # 返回成功消息
            return {"message": "监听公司任务已关闭"}
        else:
            # 如果没有记录，尝试使用 Windows 命令行强制终止残留进程
            if os.name == 'nt':
                # 调用 wmic 命令终止所有执行该脚本的 Python 进程
                os.system('wmic process where "name=\'python.exe\' and commandline like \'%listen_keyword_company.py%\'" call terminate')
            # 返回提示消息
            return {"message": "未在记录中找到运行的任务，已尝试通过系统命令清理"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 启动登录寻客宝的后台任务
@api_router.post("/system/login_xunkebao")
async def start_login_xunkebao():
    # 接口文档说明
    """启动登录寻客宝"""
    try:
        # 使用 subprocess 在后台运行脚本
        subprocess.Popen([sys.executable, "xunkebao.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
        # 返回成功消息
        return {"message": "登录寻客宝任务已启动，请在弹出的浏览器中扫码"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 启动讲述人的后台任务
@api_router.post("/system/trigger_narrator")
async def start_trigger_narrator():
    # 接口文档说明
    """启动讲述人"""
    try:
        # 使用 subprocess 在后台运行脚本
        subprocess.Popen([sys.executable, "narrator.py"], cwd=os.path.dirname(os.path.abspath(__file__)))
        # 返回成功消息
        return {"message": "讲述人已启动，请等待"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 启动文件上传服务的后台任务
@api_router.post("/system/start_file_service")
async def start_file_service():
    # 接口文档说明
    """启动文件上传服务"""
    try:
        # 如果之前已经启动过且还在运行，先尝试终止它
        if "file_service" in background_processes:
            # 获取旧的进程对象
            old_p = background_processes["file_service"]
            # 检查进程是否还在运行
            if old_p.poll() is None:
                # 终止进程
                old_p.terminate()
                
        # 计算 tools\weixin 目录的绝对路径
        tools_weixin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "weixin")
        # 使用 subprocess 在后台运行脚本
        p = subprocess.Popen([sys.executable, "file_service.py"], cwd=tools_weixin_dir)
        # 保存进程对象到全局字典中
        background_processes["file_service"] = p
        
        # 返回成功消息
        return {"message": "文件上传服务已启动"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 关闭文件上传服务的后台任务
@api_router.post("/system/stop_file_service")
async def stop_file_service():
    # 接口文档说明
    """关闭文件上传服务"""
    try:
        # 检查是否在全局字典中记录了该任务
        if "file_service" in background_processes:
            # 获取进程对象
            p = background_processes["file_service"]
            # 检查进程是否还在运行
            if p.poll() is None:
                # 终止进程
                p.terminate()
                # 等待进程退出
                p.wait()
            # 从字典中移除该任务
            del background_processes["file_service"]
            # 返回成功消息
            return {"message": "文件上传服务已关闭"}
        else:
            # 如果没有记录，尝试使用 Windows 命令行强制终止残留进程
            if os.name == 'nt':
                # 调用 wmic 命令终止所有执行该脚本的 Python 进程
                os.system('wmic process where "name=\'python.exe\' and commandline like \'%file_service.py%\'" call terminate')
            # 返回提示消息
            return {"message": "未在记录中找到运行的任务，已尝试通过系统命令清理"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 启动注册机器人的后台任务
@api_router.post("/system/start_config_service")
async def start_config_service():
    # 接口文档说明
    """启动注册机器人"""
    try:
        # 计算 tools\weixin 目录的绝对路径
        tools_weixin_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tools", "weixin")
        # 使用 subprocess 在后台运行脚本
        subprocess.Popen([sys.executable, "config_service.py"], cwd=tools_weixin_dir)
        # 返回成功消息
        return {"message": "注册机器人任务已启动"}
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 运行数据库备份脚本
@api_router.post("/system/backup_db")
async def backup_db():
    # 接口文档说明
    """备份数据库"""
    try:
        # 使用 subprocess 同步运行备份脚本，并捕获输出
        result = subprocess.run([sys.executable, "backupDB.py"], cwd=os.path.dirname(os.path.abspath(__file__)), capture_output=True, text=True)
        # 检查是否成功执行
        if result.returncode == 0:
            # 返回成功消息
            return {"message": "数据库备份成功！\n" + result.stdout.strip()}
        else:
            # 返回错误消息
            raise HTTPException(status_code=500, detail="备份失败：" + result.stderr.strip())
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))

# 忽略来自 DataLoader 的关于 pin_memory 的警告
warnings.filterwarnings("ignore", category=UserWarning, module="torch.utils.data.dataloader")

def _extract_company_name(text_list: list[str]) -> str | None:
    """
    一个简单的启发式规则：从 OCR 提取出的文本列表中寻找公司名称。
    """
    # 将所有文本拼接成一个字符串，方便进行整体匹配
    full_text = "".join(text_list).replace(" ", "")
    print(full_text)

    # 1. 优先匹配带前缀的明确格式：(公司名称|经销商)[冒号](实际名字)[可能带个体户括号]
    # 匹配：公司名称:莆田市南岛电子商务有限公司, 经销商:杭州禾煊商贸有限公司, 公司名称:杭州市钱塘区锡北服装工作室(个体工商...
    match_prefix = re.search(r'(?:公司名称|经销商|单位名称|厂商)[:：]\s*(.+?(?:公司|厂|部|中心|工作室|店))', full_text)
    if match_prefix:
        return match_prefix.group(1)

    # 2. 匹配 "企业名称" 和 "类型" 之间的公司名称
    match_enterprise_type = re.search(r'企业名称[:：]\s*(.+?(?:公司|厂|部|中心|工作室|店))\s*类型', full_text)
    if match_enterprise_type:
        return match_enterprise_type.group(1)

    # 3. 匹配没有前缀，但是典型公司名称结尾的，并且过滤掉尾部的括号（如：(个体工商)）
    # 匹配：莆田市南岛电子商务有限公司, 杭州市钱塘区锡北服装工作室(个体工商
    match_suffix = re.search(r'(.+?(?:公司|厂|部|中心|工作室|店))', full_text)
    if match_suffix:
        # 简单验证一下长度，防止匹配到太短的无效词（比如 "销售部"）
        name_candidate = match_suffix.group(1)
        if len(name_candidate) > 3:
            return name_candidate
    
    # 如果没找到带后缀的，返回第一行相对较长的文本作为备选
    for text in text_list:
        if len(text) > 4:
            return text
    
    return None

from pydantic import BaseModel

@api_router.get("/tags")
async def get_all_tags():
    """获取所有标签"""
    db = get_session()
    try:
        tags = db.query(Tag).all()
        return {"tags": [{"id": tag.id, "name": tag.name} for tag in tags]}
    finally:
        db.close()

# 定义请求数据模型
class BatchUpdateKeywordRequest(BaseModel):
    # 主键列表
    pks: List[int]
    # 新的核心词
    keyword: str

# 定义批量更新核心词的路由
@api_router.post("/company/batch_update_keyword")
async def batch_update_keyword(req: BatchUpdateKeywordRequest):
    # 接口文档说明
    """批量修改公司核心词"""
    # 获取数据库会话
    db = get_session()  
    try:
        # 查询所有匹配的主键
        companies = db.query(Company).filter(Company.id.in_(req.pks)).all()
        # 遍历查询到的线索
        for company in companies:
            # 将核心词修改为用户输入的新核心词
            company.keyword = req.keyword
        # 提交数据库事务
        db.commit()
        # 返回成功消息
        return {"message": f"成功修改 {len(companies)} 个公司的核心词为 '{req.keyword}'"}
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        # 抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 关闭数据库会话
        db.close()

# 定义请求数据模型
class BatchUpdateTagsRequest(BaseModel):
    # 主键列表
    pks: List[int]
    # 新的标签ID
    tag_id: int

# 定义批量更新标签的路由
@api_router.post("/company/batch_update_tags")
async def batch_update_tags(req: BatchUpdateTagsRequest):
    # 接口文档说明
    """批量修改公司标签"""
    # 获取数据库会话
    db = get_session()  
    try:
        # 查找指定的标签
        tag = db.query(Tag).filter(Tag.id == req.tag_id).first()
        if not tag:
            raise HTTPException(status_code=404, detail="标签未找到")
        
        # 查询所有匹配的主键
        companies = db.query(Company).filter(Company.id.in_(req.pks)).all()
        # 遍历查询到的线索
        for company in companies:
            # 将标签与公司关联，这里如果要求单选关联，我们就替换原来的标签
            company.tags = [tag]
        # 提交数据库事务
        db.commit()
        # 返回成功消息
        return {"message": f"成功修改 {len(companies)} 个公司的标签为 '{tag.name}'"}
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        # 抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 关闭数据库会话
        db.close()

@api_router.post("/company/add_namecards")
async def add_companies(files: List[UploadFile] = File(...)):
    """
    接收前端通过 multipart/form-data 上传的多张图片，提取名片并入库。
    """
    if not files:
        raise HTTPException(status_code=400, detail="No files uploaded")
        
    results = []
    db = get_session()
    
    try:
        for file in files:
            try:

                # 读取上传文件的二进制内容
                contents = await file.read()
                # 提取上传文件的后缀名
                file_suffix = os.path.splitext(file.filename)[1]
                # 创建命名临时文件并设置不自动删除
                with tempfile.NamedTemporaryFile(delete=False, suffix=file_suffix) as tmp_file:
                    # 将文件内容写入临时文件
                    tmp_file.write(contents)
                    # 保存临时文件的绝对路径
                    temp_path = tmp_file.name
                # 使用 RapidOCR 读取临时文件中的文本
                result_texts = get_text(temp_path)
                # 从磁盘中删除该临时文件
                os.remove(temp_path)
                
                if not result_texts:
                    results.append({
                        "filename": file.filename,
                        "status": "warning",
                        "message": "No text detected in image"
                    })
                    continue
                    
                # 4. 提取公司名称
                company_name = _extract_company_name(result_texts)
                if not company_name:
                    company_name = result_texts[0] + " (待确认)"
                    
                # 检查数据库中是否已存在该店铺，避免重复导入
                existing = db.query(Company).filter(Company.name == company_name).first()
                # 如果已存在该店铺记录
                if existing:                    
                    results.append({
                        "filename": file.filename,
                        "status": "success",
                        "company_name": existing.name,
                        "message": "已存在，更新来源词"
                    })
                    # 结束当前条目的处理，进行下一条
                    continue
                # 提取简称：去掉常见的通用词
                shortname = company_name
                # 定义要去除的通用后缀或词语
                common_words = ["有限公司", "有限责任公司", "电子商务", "经营部", "(个体工商户)", "（个体工商户）", "个体工商户", "商贸", "贸易", "实业", "服饰", "服装", "纺织", "针织", "工作室", "厂", "店", "批发", "零售", "制造"]
                # 遍历去除这些通用词
                for word in common_words:
                    shortname = shortname.replace(word, "")
                    # 去除可能产生的多余空格
                shortname = shortname.strip()
                # 5. 存入 SQLite 数据库
                new_company = Company(
                    name=company_name,
                    shortname=shortname,
                    source_words="名片导入",
                )
                db.add(new_company)
                db.commit()
                db.refresh(new_company)
                
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "company_name": new_company.name
                })
                
            except Exception as e:
                db.rollback()
                results.append({
                    "filename": file.filename,
                    "status": "error",
                    "message": str(e)
                })
    finally:
        db.close()
        
    # 计算成功数量
    success_count = sum(1 for r in results if r["status"] == "success")
    return {
        "message": f"成功导入 {success_count} 个公司，失败 {len(files) - success_count} 个",
        "results": results
    }

@api_router.post("/company/import_json")
async def import_json(files: List[UploadFile] = File(...)):
    """
    接收前端上传的JSON文件，解析并存入公司表
    """
    if not files:
        raise HTTPException(status_code=400, detail="没有上传文件")
        
    db = get_session()
    success_count = 0
    skip_count = 0
    error_count = 0
    
    try:
        for file in files:
            try:
                # 读取JSON文件内容
                contents = await file.read()
                # 解析JSON格式数据
                parsed_json = json.loads(contents)
                # 获取上传的文件名（仅保留基本名称，去除非法路径）
                filename = os.path.basename(file.filename)
                
                # 定义数据数组
                data_array = []
                # 判断文件开头分类并提取数据数组
                if filename.startswith("hot_items"):
                    data_array = parsed_json.get("data", {}).get("data", {}).get("data", [])
                elif filename.startswith("item_rank") or filename.startswith("shop_rank"):
                    data_array = parsed_json.get("data", {}).get("data", [])
                else:
                    # 如果不属于这三种格式，记为错误并跳过
                    error_count += 1
                    continue
                
                # 遍历数据数组中的每一项
                for entry in data_array:
                    # 获取店铺信息字典
                    shop = entry.get("shop", {})
                    # 获取商品信息字典
                    item = entry.get("item", {})
                    
                    # 获取店铺名称
                    shop_name = shop.get("shopName")
                    # 如果没有店铺名称则跳过
                    if not shop_name:
                        continue
                    
                    # 提取简称：去掉常见的通用词
                    shortname = shop_name
                    # 定义要去除的通用后缀或词语
                    common_words = ["有限公司", "有限责任公司", "电子商务", "经营部", "(个体工商户)", "（个体工商户）", "个体工商户", "商贸", "贸易", "实业", "服饰", "服装", "纺织", "针织", "工作室", "厂", "店", "批发", "零售", "制造"]
                    # 遍历去除这些通用词
                    for word in common_words:
                        shortname = shortname.replace(word, "")
                    # 去除可能产生的多余空格
                    shortname = shortname.strip()
                        
                    # 获取店铺链接
                    shop_link = shop.get("shopUrl")
                    # 获取店铺等级
                    level = shop.get("tradeMedalGrade")
                    # 获取商品链接（如果存在item字典）
                    product_link = item.get("detailUrl") if item else None
                    # 获取不带扩展名的文件名
                    base_name = os.path.splitext(filename)[0]
                    # 初始化来源词为不带扩展名的文件名
                    source_words = base_name
                    # 判断如果文件名以 shop_rank_ 开头
                    if base_name.startswith("shop_rank_"):
                        # 去掉前缀 shop_rank_
                        source_words = base_name.replace("shop_rank_", "", 1)
                        # 去掉尾部的 _数字
                        source_words = re.sub(r'_\d+$', '', source_words)
                    # 判断如果文件名以 item_rank_ 开头
                    elif base_name.startswith("item_rank_"):
                        # 去掉前缀 item_rank_
                        source_words = base_name.replace("item_rank_", "", 1)
                        # 去掉尾部的 _数字
                        source_words = re.sub(r'_\d+$', '', source_words)
                    # 判断如果文件名以 hot_items_ 开头
                    elif base_name.startswith("hot_items_"):
                        # 去掉前缀 hot_items_
                        source_words = base_name.replace("hot_items_", "", 1)

                    # 获取认证状态，默认为白
                    certification = '白'
                    # 判断是否出现 identity 且值为 svip
                    if shop.get("identity") == "svip":
                        # 设置认证为紫
                        certification = '紫'
                    # 判断如果 realBusiness 和 tp 均为 true，且当前不为 svip
                    elif shop.get("realBusiness") is True and shop.get("tp") is True:
                        # 设置认证为红
                        certification = '红'
                    
                    # 检查数据库中是否已存在该店铺，避免重复导入
                    existing = db.query(Company).filter(Company.name == shop_name).first()
                    # 如果已存在该店铺记录
                    if existing:
                        # 检查新获取的商品链接是否存在
                        if product_link:
                            # 覆盖更新为最新的商品链接
                            existing.product_link = product_link
                        # 检查原有的来源词是否存在
                        if existing.source_words:
                            # 判断新的来源词是否不在原有来源词列表内（按、分割）
                            if source_words not in existing.source_words.split('、'):
                                # 用、号连接在原有来源词后面
                                existing.source_words += f"、{source_words}"
                        # 如果原有来源词为空
                        else:
                            # 直接赋值为新的来源词
                            existing.source_words = source_words
                        # 将跳过计数加一，表示是更新而非新增
                        skip_count += 1
                        # 结束当前条目的处理，进行下一条
                        continue
                        
                    # 实例化新的公司对象
                    new_company = Company(
                        name=shop_name,
                        shortname=shortname,
                        shop_link=shop_link,
                        level=level,
                        product_link=product_link,
                        source_words=source_words,
                        certification=certification,
                    )
                    # 添加到数据库会话中
                    db.add(new_company)
                    # 成功计数加一
                    success_count += 1
                    
            except Exception as e:
                # 发生异常时错误计数加一
                error_count += 1
                
        # 统一提交所有事务
        db.commit()
    except Exception as e:
        # 如果发生严重异常则回滚
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 关闭数据库会话
        db.close()
        
    # 返回执行结果摘要
    return {
        "message": f"成功导入 {success_count} 个公司，跳过 {skip_count} 个已存在，处理失败 {error_count} 个文件"
    }

@api_router.post("/company/mine")
def mine_unmined_companies():
    """挖掘所有未挖掘的公司"""
    db = get_session()
    try:
        # 查询所有状态为“待挖掘”的公司
        companies = db.query(Company).filter(Company.status == '待挖掘').all()
        if not companies:
            return {"message": "没有找到需要挖掘的公司", "count": 0}
        
        # 调用寻客宝爬虫进行挖掘 (由于模型变更，xunkebao 可能也需要相应修改，暂且保留调用)
        search_account(companies)
        
        # 统一提交
        db.commit()
        
        return {"message": f"成功完成 {len(companies)} 个公司的挖掘任务", "count": len(companies)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# 定义添加好友请求数据模型
class AddFriendRequest(BaseModel):
    # 主键列表
    pks: List[int]
    # 销售人员ID
    sales_id: int

# 定义获取所有销售人员的路由
@api_router.get("/sales/all")
def get_all_sales():
    """获取所有销售人员列表"""
    # 获取数据库会话
    db = get_session()
    try:
        # 查询所有销售人员
        sales_list = db.query(Sales).all()
        # 返回销售人员列表
        return [{"id": s.id, "name": s.name} for s in sales_list]
    except Exception as e:
        # 发生异常时抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 关闭数据库会话
        db.close()

# 定义添加好友的路由
@api_router.post("/contact/add_friend")
async def add_friend(req: AddFriendRequest):
    """把勾选的客户 逐一调用 /add_friend 并修改状态"""
    # 获取数据库会话
    db = get_session()
    try:
        # 获取选中的销售人员信息
        sales_person = db.query(Sales).filter(Sales.id == req.sales_id).first()
        # 获取销售人员的名称，如果不存在则默认为空字符串
        ss = sales_person.name if sales_person else ""
        
        # 查询所有匹配的主键
        contacts = db.query(Contact).filter(Contact.id.in_(req.pks)).all()
        # 记录成功处理的数量
        success_count = 0
        
        # 遍历查询到的客户
        for contact in contacts:
            # 如果没有电话号码，则跳过无法添加微信
            if not contact.phone:
                continue
            try:    
                # 获取客户简称，默认为空字符串
                xx = contact.shortname or ""
                # 获取公司标签，如果有多个取第一个或直接用字符串，由于模型里有 company_tags 属性，我们可以使用
                yy = contact.company_tags or ""
                # 获取公司核心词，默认为空字符串
                zzz = contact.company.keyword if contact.company and contact.company.keyword else ""
                
                # 定义三个打招呼模板
                templates = [
                    f"{xx}您好，我是{yy}面料厂家{ss}。一直关注贵司{zzz}，这季有几款垂感极佳的现货{xx}，很适合做爆款，想加个好友分享资料，支持快反。",
                    f"{xx}您好，我是{yy}面料厂家{ss}。近期开发了几款高品质{xx}新品，触感和垂坠感特别适合{zzz}，想寄份小样给您对比看看，方便加个好友吗？",
                    f"{xx}您好，我是{yy}面料厂家{ss}。专门供应高品质{yy}，贵司{zzz}版型很好，我们有几款面料很适配贵司风格，希望能加好友对接一下供应链。"
                ]
                # 随机选择一个打招呼模板
                selected_greeting = random.choice(templates)
                
                # 逐一调用 pyweixin 里的添加好友方法
                FriendSettings.add_new_friend(
                    number=contact.phone, # 传入电话号码
                    greetings=selected_greeting, # 随机选择的打招呼用语
                    remark=f"{contact.shortname}-{contact.company.shortname}-{contact.phone}-C", # 默认给对方的备注名称
                    close_weixin=False # 连续处理时不要每次关闭微信
                )
                
                # 将客户状态修改为“已请求”
                contact.status = "已请求"
                
                # 创建并添加好友记录
                new_friend = Friend(
                    contact_id=contact.id, # 关联当前客户ID
                    nickname=f"{contact.shortname}-{contact.company.shortname}-{contact.phone}", # 设置好友昵称
                    level="C", # 设置好友等级为C
                    sales_id=req.sales_id # 关联指定的销售人员
                )
                # 将新好友记录添加到数据库会话中
                db.add(new_friend)
                
                # 增加成功计数
                success_count += 1
            except Exception as e:
                if "无法添加该好友" in str(e):
                    contact.status = "已拒绝"
                else:
                    contact.status = "已失效"
            finally:
                db.commit()

        # 提交数据库事务保存状态修改
        return {"message": f"成功添加 {success_count} 个客户并发送了好友请求"}
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        # 抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 关闭数据库会话
        db.close()
