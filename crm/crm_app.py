# c:\develop\nanobot\crm\admin_app.py
import uvicorn
import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from crm_api import api_router
from pyweixin_api import wx_router  # 导入外部定义的 API 路由

# 导入你写好的模型和引擎
from models import engine, Account, Contact, Opportunity, Task, Message
from pyweixin_watcher import check_and_process

import os

async def crm_background_loop():
    """后台异步循环，替代 crm.py 中的 main() 同步循环"""
    logging.info("CRM 微信消息监听服务已随 FastAPI 启动...")
    while True:
        try:
            # 使用 to_thread 避免同步网络/数据库操作阻塞 FastAPI 主事件循环
            await asyncio.to_thread(check_and_process)
            logging.info("等待 5 分钟后进行下一轮检查...")
            await asyncio.sleep(300)  # 异步等待 5 分钟
        except asyncio.CancelledError:
            logging.info("CRM 微信消息监听服务正在安全关闭...")
            break
        except Exception as e:
            logging.error(f"CRM 监听服务发生异常: {e}")
            await asyncio.sleep(60)  # 发生异常时稍作等待再重试，防止死循环刷日志

@asynccontextmanager
async def lifespan(app: FastAPI):
    # FastAPI 启动时：创建并运行后台任务
    task = asyncio.create_task(crm_background_loop())
    yield
    # FastAPI 关闭时：取消后台任务并等待它安全退出
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        pass

app = FastAPI(title="极简 CRM 后台", lifespan=lifespan)

# 将外部的 API 路由注册到当前 app 中
app.include_router(api_router)
app.include_router(wx_router)  # 注册微信 API 路由  

# 将 Admin 绑定到 FastAPI 和你的 SQLite 引擎上
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
admin = Admin(app, engine, title="CRM 数据管理", templates_dir=templates_dir)

# 1. 线索管理
class AccountAdmin(ModelView, model=Account):
    column_list = [Account.id, Account.name, Account.status, Account.flag, Account.created_at]
    column_searchable_list = [Account.name, Account.status, Account.flag]
    name = "公司 (Account)"
    name_plural = "公司列表"
    icon = "fa-solid fa-filter"
    list_template = "account_list.html"
    can_create = False  # 隐藏 "+ New 公司" 按钮
    can_export = False  # 隐藏 "Export" 按钮


# 3. 客户管理
class ContactAdmin(ModelView, model=Contact):
    column_list = [Contact.id, Contact.name, Contact.phone, Contact.account, Contact.status, Contact.created_at]
    column_searchable_list = [Contact.name, Contact.phone]
    name = "客户 (Contact)"
    name_plural = "客户列表"
    icon = "fa-solid fa-user"
    list_template = "contact_list.html"
    can_create = True  # 隐藏 "+ New 线索" 按钮
    can_export = False  # 隐藏 "Export" 按钮

# 4. 商机管理（会话管理）
class OpportunityAdmin(ModelView, model=Opportunity):
    column_list = [Opportunity.id, Opportunity.name, Opportunity.stage, Opportunity.level, Opportunity.remark, Opportunity.contact]
    name = "商机 (Opportunity)"
    name_plural = "商机列表"
    icon = "fa-solid fa-handshake"
    can_create = True  # 隐藏 "+ New 商机" 按钮
    can_export = False  # 隐藏 "Export" 按钮

# 5. 任务管理
class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.content,Task.type, Task.status, Task.due_date, Task.opportunity]
    column_searchable_list = [Opportunity.name, Task.content, Task.status]
    name = "任务 (Task)"
    name_plural = "任务列表"
    icon = "fa-solid fa-list-check"
    can_create = False  # 隐藏 "+ New 线索" 按钮
    can_export = False  # 隐藏 "Export" 按钮

# 6. 聊天信息管理
class MessageAdmin(ModelView, model=Message):
    column_list = [Message.id, Message.opportunity, Message.sender, Message.content, Message.created_at]
    
    # 格式化 content 列，使其在列表中只显示前 30 个字符，超出的用省略号代替
    column_formatters = {
        Message.content: lambda m, a: f"{m.content[:30]}..." if m.content and len(m.content) > 30 else m.content
    }
    
    name = "聊天信息 (Message)"
    name_plural = "聊天信息列表"
    icon = "fa-solid fa-comment"
    can_create = False  # 隐藏 "+ New 聊天信息" 按钮
    can_export = False  # 隐藏 "Export" 按钮



# 把这些页面注册到后台  
admin.add_view(AccountAdmin)
admin.add_view(ContactAdmin)
admin.add_view(OpportunityAdmin)
admin.add_view(TaskAdmin)
admin.add_view(MessageAdmin)

if __name__ == "__main__":
    print("后台已启动，请在浏览器打开: http://127.0.0.1:8201/admin")
    uvicorn.run(app, host="127.0.0.1", port=8201)