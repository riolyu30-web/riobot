from fastapi import APIRouter, Request, HTTPException, UploadFile, File
import easyocr
import cv2
import re
import os
import warnings
import numpy as np
from typing import List
from models import get_session, Account, Contact
from xunkebao import search_account
from pyweixin import FriendSettings


api_router = APIRouter()

# 初始化 EasyOCR 读者 (首次运行会下载模型，建议只初始化一次)
# 支持中英文
# gpu=False: 如果你没有NVIDIA显卡，可以显式声明不用GPU，减少一些警告
reader = easyocr.Reader(['ch_sim', 'en'], gpu=False)

def _extract_company_name(text_list: list[str]) -> str | None:
    """
    一个简单的启发式规则：从 OCR 提取出的文本列表中寻找公司名称。
    """
    print(text_list)
    for text in text_list:
        # 清理多余的空格
        clean_text = text.replace(" ", "")
        
        # 1. 优先匹配带前缀的明确格式：(公司名称|经销商)[冒号](实际名字)[可能带个体户括号]
        # 匹配：公司名称:莆田市南岛电子商务有限公司, 经销商:杭州禾煊商贸有限公司, 公司名称:杭州市钱塘区锡北服装工作室(个体工商...
        match_prefix = re.search(r'(?:公司名称|经销商|单位名称|厂商)[:：]\s*(.+?(?:公司|厂|部|中心|工作室|店))', clean_text)
        if match_prefix:
            return match_prefix.group(1)

        # 2. 匹配没有前缀，但是典型公司名称结尾的，并且过滤掉尾部的括号（如：(个体工商)）
        # 匹配：莆田市南岛电子商务有限公司, 杭州市钱塘区锡北服装工作室(个体工商
        match_suffix = re.search(r'(.+?(?:公司|厂|部|中心|工作室|店))', clean_text)
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

# 定义请求数据模型
class BatchUpdateFlagRequest(BaseModel):
    # 主键列表
    pks: List[int]
    # 新的标签
    flag: str

# 定义批量更新标签的路由
@api_router.post("/account/batch_update_flag")
async def batch_update_flag(req: BatchUpdateFlagRequest):
    # 接口文档说明
    """批量修改公司标签"""
    # 获取数据库会话
    db = get_session()  
    try:
        # 查询所有匹配的主键
        accounts = db.query(Account).filter(Account.id.in_(req.pks)).all()
        # 遍历查询到的线索
        for account in accounts:
            # 将标签修改为用户输入的新标签
            account.flag = req.flag
        # 提交数据库事务
        db.commit()
        # 返回成功消息
        return {"message": f"成功修改 {len(accounts)} 个公司的标签为 '{req.flag}'"}
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        # 抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 关闭数据库会话
        db.close()

@api_router.post("/account/add")
async def add_accounts(files: List[UploadFile] = File(...)):
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
                # 1. 读取文件内容到内存
                contents = await file.read()
                
                # 2. 将图片字节转换为 numpy 数组供 cv2 读取
                nparr = np.frombuffer(contents, np.uint8)
                img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                if img is None:
                    raise ValueError("Invalid image format")
                    
                # 3. 使用 EasyOCR 读取文本
                result_texts = reader.readtext(img, detail=0)
                
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
                    
                # 5. 存入 SQLite 数据库
                new_account = Account(
                    name=company_name,
                )
                db.add(new_account)
                db.commit()
                db.refresh(new_account)
                
                results.append({
                    "filename": file.filename,
                    "status": "success",
                    "company_name": new_account.name
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

@api_router.post("/account/mine")
def mine_unmined_accounts():
    """挖掘所有未挖掘的公司"""
    db = get_session()
    try:
        # 查询所有未挖掘的公司
        accounts = db.query(Account).filter(Account.status == '未挖掘').all()
        if not accounts:
            return {"message": "没有找到需要挖掘的公司", "count": 0}
        
        # 调用寻客宝爬虫进行挖掘
        # 传入的 accounts 对象属于当前的 db session
        search_account(accounts)
        
        # 统一提交以保存 search_account 中对 account.status 做的修改
        db.commit()
        
        return {"message": f"成功完成 {len(accounts)} 个公司的挖掘任务", "count": len(accounts)}
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        db.close()

# 定义链接商机请求数据模型
class LinkOpportunityRequest(BaseModel):
    # 主键列表
    pks: List[int]

# 定义链接商机的路由
@api_router.post("/contact/link_opportunity")
async def link_opportunity(req: LinkOpportunityRequest):
    """把勾选的客户 逐一调用 /add_friend 并修改状态"""
    # 获取数据库会话
    db = get_session()
    try:
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
                # 逐一调用 pyweixin 里的添加好友方法
                FriendSettings.add_new_friend(
                    number=contact.phone, # 传入电话号码
                    greetings="您好，我们在中大专供天丝面料，希望能和您合作", # 默认打招呼用语
                    remark=f"{contact.name}-{contact.phone}", # 默认给对方的备注名称
                    close_weixin=False # 连续处理时不要每次关闭微信
                )
                
                # 将客户状态修改为“已请求”
                contact.status = "已请求"
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
        return {"message": f"成功链接 {success_count} 个客户并发送了好友请求"}
    except Exception as e:
        # 发生异常时回滚事务
        db.rollback()
        # 抛出 HTTP 500 异常
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # 关闭数据库会话
        db.close()
