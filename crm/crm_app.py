# c:\develop\nanobot\crm\admin_app.py
import uvicorn
from fastapi import FastAPI
from sqladmin import Admin, ModelView
from crm_api import api_router
from pyweixin_api import wx_router  # 导入外部定义的 API 路由

# 导入你写好的模型和引擎
from models import engine, Account, Contact, Opportunity, Task

import os

app = FastAPI(title="极简 CRM 后台")

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
    can_create = False  # 隐藏 "+ New 线索" 按钮
    can_export = False  # 隐藏 "Export" 按钮

# 4. 商机管理
class OpportunityAdmin(ModelView, model=Opportunity):
    column_list = [Opportunity.id, Opportunity.name, Opportunity.stage, Opportunity.level, Opportunity.remark, Opportunity.contact]
    name = "商机 (Opportunity)"
    name_plural = "商机列表"
    icon = "fa-solid fa-handshake"
    can_create = False  # 隐藏 "+ New 线索" 按钮
    can_export = False  # 隐藏 "Export" 按钮

# 5. 任务管理
class TaskAdmin(ModelView, model=Task):
    column_list = [Task.id, Task.content, Task.status, Task.due_date, Task.contact]
    name = "任务 (Task)"
    name_plural = "任务列表"
    icon = "fa-solid fa-list-check"
    can_create = False  # 隐藏 "+ New 线索" 按钮
    can_export = False  # 隐藏 "Export" 按钮

# 把这些页面注册到后台  
admin.add_view(AccountAdmin)
admin.add_view(ContactAdmin)
admin.add_view(OpportunityAdmin)
admin.add_view(TaskAdmin)

if __name__ == "__main__":
    print("后台已启动，请在浏览器打开: http://127.0.0.1:8201/admin")
    uvicorn.run(app, host="127.0.0.1", port=8201)