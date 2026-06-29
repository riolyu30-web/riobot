# 导入 FastAPI 框架，用于构建 Web 应用
from fastapi import FastAPI
# 导入 sqladmin 提供的 Admin 和 ModelView 组件，用于构建后台管理界面
from sqladmin import Admin, ModelView
# 导入 markupsafe 提供的 Markup，用于渲染 HTML 标签
from markupsafe import Markup
# 导入 wtforms 提供的 SelectField，用于下拉单选框
from wtforms import SelectField
# 导入 uvicorn，用于运行 FastAPI 应用服务器
import uvicorn
# 导入 models.py 中定义的数据库引擎以及所有对应数据表的模型，并导入 init_db 函数用于初始化数据库
from models import engine, Sales, Company, Contact, Friend, Order, Task, Tag, init_db
# 导入 contextlib.asynccontextmanager 用于管理 FastAPI 生命周期
from contextlib import asynccontextmanager
import webbrowser
from crm_api import api_router
# 实例化 Admin 对象，将其与 FastAPI 应用和 SQLAlchemy 数据库引擎进行绑定，并指定模板目录为 crm 目录下的 templates 目录
import os
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
# 定义 FastAPI 应用的生命周期管理函数
@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时：初始化数据库表
    init_db()
    # yield 分隔了启动和关闭的逻辑
    yield
    # 关闭时的逻辑可以放在这里

# 实例化 FastAPI 应用，设置文档标题为“CRM 管理系统”，并配置生命周期管理
app = FastAPI(title="CRM 管理系统", lifespan=lifespan)
# 将外部的 API 路由注册到当前 app 中
app.include_router(api_router)

admin = Admin(app, engine, templates_dir=os.path.join(BASE_DIR, "templates"))

# 定义基于 Tag 模型的管理视图类
class TagAdmin(ModelView, model=Tag):
    # 设置默认每页显示 50 条数据
    page_size = 50
    page_size_options = [50, 100, 200]
    column_list = [Tag.id, Tag.name, Tag.description]
    column_searchable_list = [Tag.name, Tag.description]
    name = "标签"
    name_plural = "标签管理"
    icon = "fa-solid fa-tags"
    column_labels = {Tag.id: "编号", Tag.name: "标签名", Tag.description: "标签描述",Tag.sales: "关联销售",Tag.companies: "关联公司"}
    form_args = {
        "name": {"label": "标签名"},
        "description": {"label": "标签描述"}
    }
    can_create = True
    can_edit = True
    can_delete = True
    can_view_details = True

# 定义基于 Sales 模型的管理视图类
class SalesAdmin(ModelView, model=Sales):
    # 设置默认每页显示 50 条数据
    page_size = 50
    page_size_options = [50, 100, 200]
    # 定义在后台列表中需要展示的字段
    column_list = [Sales.id, Sales.name, Sales.phone, Sales.platform, Sales.tags, Sales.created_at]
    # 定义在后台列表中支持模糊搜索的字段
    column_searchable_list = [Sales.name, Sales.phone, Sales.platform]
    # 定义侧边栏菜单中该模块的单数名称
    name = "销售人员"
    # 定义侧边栏菜单中该模块的复数名称
    name_plural = "销售人员管理"
    # 定义侧边栏菜单使用的 FontAwesome 图标
    icon = "fa-solid fa-user-tie"
    # 定义在后台列表中各个字段显示的中文名称
    column_labels = {Sales.id: "编号", Sales.name: "姓名", Sales.phone: "手机号", Sales.platform: "平台", Sales.tags: "标签", Sales.created_at: "创建时间", Sales.friends: "关联好友"}
    # 定义在新增/编辑表单中各个字段显示的中文名称
    form_args = {
        "name": {"label": "姓名"},
        "phone": {"label": "手机号"},
        "platform": {"label": "平台"},
        "tags": {"label": "标签"}
    }
    # 配置标签的多选自动补全功能
    form_ajax_refs = {
        "tags": {
            "fields": ("name",)
        }
    }
    # 允许在后台新建 Sales 数据
    can_create = True
    # 允许在后台编辑 Sales 数据
    can_edit = True
    # 允许在后台删除 Sales 数据
    can_delete = True
    # 允许在后台查看 Sales 数据详情
    can_view_details = True

# 定义基于 Company 模型的管理视图类
class CompanyAdmin(ModelView, model=Company):
    # 设置默认每页显示 50 条数据
    page_size = 50
    page_size_options = [50, 100, 200]
    # 指定自定义的列表模板
    list_template = "company_list.html"
    # 定义在后台列表中需要展示的字段
    column_list = [Company.id, Company.name, Company.shortname, Company.tags, Company.keyword, Company.source_words, Company.shop_link, Company.product_link, Company.level, Company.certification, Company.status, Company.created_at]
    # 定义在后台列表中支持模糊搜索的字段
    column_searchable_list = [Company.name, Company.shortname, Company.keyword, Company.source_words, Company.tags, Company.level, Company.status]
    # 定义侧边栏菜单中该模块的单数名称
    name = "公司"
    # 定义侧边栏菜单中该模块的复数名称
    name_plural = "公司管理"
    # 定义侧边栏菜单使用的 FontAwesome 图标
    icon = "fa-solid fa-building"
    # 定义在后台列表中各个字段显示的中文名称
    column_labels = {Company.id: "编号", Company.name: "公司名", Company.shortname: "简称", Company.keyword: "核心词", Company.source_words: "来源词", Company.tags: "标签", Company.level: "等级", Company.certification: "认证", Company.shop_link: "店铺链接", Company.product_link: "商品链接", Company.status: "状态", Company.created_at: "创建时间",Company.contacts: "关联客户"}
    
    # 定义列表字段格式化，使链接可点击
    column_formatters = {
        Company.shop_link: lambda m, a: Markup(f'<a href="{m.shop_link}" target="_blank">店铺链接</a>') if m.shop_link else "",
        Company.product_link: lambda m, a: Markup(f'<a href="{m.product_link}" target="_blank">商品链接</a>') if m.product_link else ""
    }
    # 指定特定字段使用的表单控件类型
    form_overrides = {
        "certification": SelectField,
        "status": SelectField
    }
    # 定义在新增/编辑表单中各个字段显示的中文名称，并为单选框配置选项
    form_args = {
        "name": {"label": "公司名"},
        "shortname": {"label": "简称"},
        "keyword": {"label": "核心词"},
        "source_words": {"label": "来源词"},
        "tags": {"label": "标签"},
        "level": {"label": "等级"},
        "certification": {
            "label": "认证",
            "choices": [("", "请选择"), ("白", "白"), ("红", "红"), ("紫", "紫")]
        },
        "status": {
            "label": "状态",
            "choices": [("待挖掘", "待挖掘"), ("已挖掘", "已挖掘"), ("已失效", "已失效")]
        },
        "shop_link": {"label": "店铺链接"},
        "product_link": {"label": "商品链接"}
    }
    # 配置标签的多选自动补全功能
    form_ajax_refs = {
        "tags": {
            "fields": ("name",)
        }
    }
    # 允许在后台新建 Company 数据
    can_create = True
    # 允许在后台编辑 Company 数据
    can_edit = True
    # 允许在后台删除 Company 数据
    can_delete = True
    # 允许在后台查看 Company 数据详情
    can_view_details = True

# 定义基于 Contact 模型的管理视图类
class ContactAdmin(ModelView, model=Contact):
    # 设置默认每页显示 50 条数据
    page_size = 50
    page_size_options = [50, 100, 200]
    # 指定自定义的列表模板
    list_template = "contact_list.html"
    # 定义在后台列表中需要展示的字段，使用 company 关系属性可以下拉选择
    column_list = [Contact.id, Contact.name, Contact.shortname, Contact.phone, Contact.company, "company_keyword", "company_tags", "company_level", "company_certification", "company_shop_link", "company_product_link", Contact.status, Contact.created_at]
    # 定义在后台列表中支持模糊搜索的字段
    column_searchable_list = [Contact.name, Contact.shortname, Contact.phone, Contact.status]
    # 定义侧边栏菜单中该模块的单数名称
    name = "客户"
    # 定义侧边栏菜单中该模块的复数名称
    name_plural = "客户管理"
    # 定义侧边栏菜单使用的 FontAwesome 图标
    icon = "fa-solid fa-users"
    # 定义在后台列表中各个字段显示的中文名称
    column_labels = {Contact.id: "编号", Contact.name: "姓名", Contact.shortname: "简称", Contact.phone: "手机号", Contact.company: "关联公司", "company_keyword": "公司核心词", "company_tags": "公司标签", "company_level": "公司等级", "company_certification": "公司认证", "company_shop_link": "公司链接", "company_product_link": "商品链接", Contact.status: "状态", Contact.created_at: "创建时间",Contact.friends: "关联好友"}
    # 指定字段的自定义格式化，将链接转换为可点击并在新页面打开的HTML标签
    column_formatters = {
        "company_shop_link": lambda m, a: Markup(f'<a href="{m.company_shop_link}" target="_blank">店铺链接</a>') if m.company_shop_link else "",
        "company_product_link": lambda m, a: Markup(f'<a href="{m.company_product_link}" target="_blank">商品链接</a>') if m.company_product_link else ""
    }
    # 指定特定字段使用的表单控件类型
    form_overrides = {
        "status": SelectField
    }
    # 定义在新增/编辑表单中各个字段显示的中文名称，并为单选框配置选项
    form_args = {
        "name": {"label": "姓名"},
        "shortname": {"label": "简称"},
        "phone": {"label": "手机号"},
        "company": {"label": "关联公司"},
        "status": {
            "label": "状态",
            "choices": [
                ("未验证", "未验证"), 
                ("已请求", "已请求"), 
                ("被拒绝", "被拒绝"), 
                ("已失效", "已失效"), 
                ("已通过", "已通过")
            ]
        }
    }
    # 允许在后台新建 Contact 数据
    can_create = True
    # 允许在后台编辑 Contact 数据
    can_edit = True
    # 允许在后台删除 Contact 数据
    can_delete = True
    # 允许在后台查看 Contact 数据详情
    can_view_details = True

# 定义基于 Friend 模型的管理视图类
class FriendAdmin(ModelView, model=Friend):
    # 设置默认每页显示 50 条数据
    page_size = 50
    page_size_options = [50, 100, 200]
    # 定义在后台列表中需要展示的字段，使用 contact 和 sales 关系属性以支持下拉选择
    column_list = [Friend.id, Friend.nickname, Friend.contact, Friend.level, Friend.sales, Friend.created_at]
    # 定义在后台列表中支持模糊搜索的字段
    column_searchable_list = [Friend.nickname, Friend.level]
    # 定义侧边栏菜单中该模块的单数名称
    name = "好友"
    # 定义侧边栏菜单中该模块的复数名称
    name_plural = "好友管理"
    # 定义侧边栏菜单使用的 FontAwesome 图标
    icon = "fa-solid fa-user-group"
    # 定义在后台列表中各个字段显示的中文名称
    column_labels = {Friend.id: "编号", Friend.nickname: "昵称", Friend.contact: "关联客户", Friend.level: "等级", Friend.sales: "关联销售", Friend.created_at: "创建时间"}
    # 定义在新增/编辑表单中各个字段显示的中文名称
    form_args = {
        "nickname": {"label": "昵称"},
        "contact": {"label": "关联客户"},
        "level": {"label": "等级"},
        "sales": {"label": "销售人员"}
    }
    # 允许在后台新建 Friend 数据
    can_create = True
    # 允许在后台编辑 Friend 数据
    can_edit = True
    # 允许在后台删除 Friend 数据
    can_delete = True
    # 允许在后台查看 Friend 数据详情
    can_view_details = True

# 定义基于 Order 模型的管理视图类
class OrderAdmin(ModelView, model=Order):
    # 设置默认每页显示 50 条数据
    page_size = 50
    page_size_options = [50, 100, 200]
    # 定义在后台列表中需要展示的字段，使用 friend 关系属性以支持下拉选择
    column_list = [Order.id, Order.friend, Order.order_type, Order.status, Order.total_amount, Order.order_time]
    # 定义在后台列表中支持模糊搜索的字段
    column_searchable_list = [Order.order_type, Order.status]
    # 定义侧边栏菜单中该模块的单数名称
    name = "订单"
    # 定义侧边栏菜单中该模块的复数名称
    name_plural = "订单管理"
    # 定义侧边栏菜单使用的 FontAwesome 图标
    icon = "fa-solid fa-cart-shopping"
    # 定义在后台列表中各个字段显示的中文名称
    column_labels = {Order.id: "编号", Order.friend: "关联好友", Order.order_type: "订单类型", Order.status: "状态", Order.total_amount: "总金额", Order.order_time: "订单时间", Order.order_details: "订单细节", Order.created_at: "创建时间"}
    # 指定特定字段使用的表单控件类型
    form_overrides = {
        "status": SelectField
    }
    # 定义在新增/编辑表单中各个字段显示的中文名称，并为单选框配置选项
    form_args = {
        "friend": {"label": "关联好友"},
        "order_type": {"label": "订单类型"},
        "status": {
            "label": "状态",
            "choices": [
                ("正常", "正常"), 
                ("撤销", "撤销")
            ]
        },
        "total_amount": {"label": "总金额"},
        "order_time": {"label": "订单时间"},
        "order_details": {"label": "订单细节"}
    }
    # 允许在后台新建 Order 数据
    can_create = True
    # 允许在后台编辑 Order 数据
    can_edit = True
    # 允许在后台删除 Order 数据
    can_delete = True
    # 允许在后台查看 Order 数据详情
    can_view_details = True

# 定义基于 Task 模型的管理视图类
class TaskAdmin(ModelView, model=Task):
    # 设置默认每页显示 50 条数据
    page_size = 50
    page_size_options = [50, 100, 200]
    # 定义在后台列表中需要展示的字段，使用 friend 关系属性以支持下拉选择
    column_list = [Task.id, Task.description, Task.due_date, Task.friend, Task.status, Task.created_at]
    # 定义在后台列表中支持模糊搜索的字段
    column_searchable_list = [Task.description, Task.status]
    # 定义侧边栏菜单中该模块的单数名称
    name = "任务"
    # 定义侧边栏菜单中该模块的复数名称
    name_plural = "任务管理"
    # 定义侧边栏菜单使用的 FontAwesome 图标
    icon = "fa-solid fa-list-check"
    # 定义在后台列表中各个字段显示的中文名称
    column_labels = {Task.id: "编号", Task.description: "任务描述", Task.due_date: "截止日期", Task.friend: "关联好友", Task.status: "状态", Task.created_at: "创建时间"}
    # 指定特定字段使用的表单控件类型
    form_overrides = {
        "status": SelectField
    }
    # 定义在新增/编辑表单中各个字段显示的中文名称，并为单选框配置选项
    form_args = {
        "description": {"label": "任务描述"},
        "due_date": {"label": "截止日期"},
        "friend": {"label": "关联好友"},
        "status": {
            "label": "状态",
            "choices": [
                ("待执行", "待执行"), 
                ("已完成", "已完成"),
                ("已撤销", "已撤销")
            ]
        }
    }
    # 允许在后台新建 Task 数据
    can_create = True
    # 允许在后台编辑 Task 数据
    can_edit = True
    # 允许在后台删除 Task 数据
    can_delete = True
    # 允许在后台查看 Task 数据详情
    can_view_details = True

# 将 TagAdmin 注册到后台管理应用中
admin.add_view(TagAdmin)
# 将 SalesAdmin 注册到后台管理应用中
admin.add_view(SalesAdmin)
# 将 CompanyAdmin 注册到后台管理应用中
admin.add_view(CompanyAdmin)
# 将 ContactAdmin 注册到后台管理应用中
admin.add_view(ContactAdmin)
# 将 FriendAdmin 注册到后台管理应用中
admin.add_view(FriendAdmin)
# 将 OrderAdmin 注册到后台管理应用中
admin.add_view(OrderAdmin)
# 将 TaskAdmin 注册到后台管理应用中
admin.add_view(TaskAdmin)

# 判断是否作为主入口程序执行
if __name__ == "__main__":
    # 在控制台打印后台启动提示及访问地址
    print("后台已启动，请在浏览器打开: http://127.0.0.1:8201/admin")
    # 打开系统默认浏览器并访问后台管理页面
    webbrowser.open("http://127.0.0.1:8201/admin")
    # 启动 uvicorn 服务器运行 FastAPI 实例，监听本地 8201 端口
    uvicorn.run(app, host="127.0.0.1", port=8201)

