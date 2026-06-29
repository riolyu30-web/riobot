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
from models import engine, Sales, Company, Contact, Friend, Order, Task
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
            await asyncio.sleep(60)  # 异步等待 5 分钟
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

# 1. 销售管理
class SalesAdmin(ModelView, model=Sales):
    column_list = [Sales.id, Sales.name, Sales.phone, Sales.platform, Sales.tags, Sales.created_at]
    column_searchable_list = [Sales.name, Sales.phone, Sales.platform]
    name = "销售人员 (Sales)"
    name_plural = "销售人员列表"
    icon = "fa-solid fa-user-tie"
    can_create = True
    can_export = False

# 2. 公司管理
class CompanyAdmin(ModelView, model=Company):
    column_list = [Company.id, Company.name, Company.level, Company.certification, Company.created_at]
    column_searchable_list = [Company.name, Company.tags, Company.level]
    name = "公司 (Company)"
    name_plural = "公司列表"
    icon = "fa-solid fa-building"
    # list_template = "account_list.html"  # 暂不启用，避免新旧字段冲突报错
    can_create = True
    can_export = False

# 3. 客户管理
class ContactAdmin(ModelView, model=Contact):
    column_list = [Contact.id, Contact.name, Contact.phone, Contact.company, Contact.status, Contact.created_at]
    column_searchable_list = [Contact.name, Contact.phone, Contact.status]
    name = "客户 (Contact)"
    name_plural = "客户列表"
    icon = "fa-solid fa-users"
    # list_template = "contact_list.html" # 暂不启用，避免新旧字段冲突报错
    can_create = True
    can_export = False

# 4. 好友管理
class FriendAdmin(ModelView, model=Friend):
    column_list = [Friend.id, Friend.contact, Friend.level, Friend.sales, Friend.created_at]
    name = "好友 (Friend)"
    name_plural = "好友列表"
    icon = "fa-solid fa-user-group"
    can_create = True
    can_export = False

# 5. 订单管理
class OrderAdmin(ModelView, model=Order):
    column_list = [Order.id, Order.friend, Order.order_type, Order.status, Order.total_amount, Order.order_time]
    name = "订单 (Order)"
    name_plural = "订单列表"
    icon = "fa-solid fa-cart-shopping"
    can_create = True
    can_export = False

# 6. 任务管理
class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.description, Task.due_date, Task.friend, Task.status, Task.created_at]
    column_searchable_list = [Task.description, Task.status]
    name = "任务 (Task)"
    name_plural = "任务列表"
    icon = "fa-solid fa-list-check"
    can_create = True
    can_export = False

# 把这些页面注册到后台  
admin.add_view(SalesAdmin)
admin.add_view(CompanyAdmin)
admin.add_view(ContactAdmin)
admin.add_view(FriendAdmin)
admin.add_view(OrderAdmin)
admin.add_view(TaskAdmin)

if __name__ == "__main__":
    print("后台已启动，请在浏览器打开: http://127.0.0.1:8201/admin")
    uvicorn.run(app, host="127.0.0.1", port=8201)
