from playwright.sync_api import sync_playwright

# 定义默认的 CDP 调试端点地址
DEFAULT_CDP_ENDPOINT = "http://127.0.0.1:9222"
# 定义默认的操作超时时间为 30 秒（30000毫秒）
DEFAULT_TIMEOUT = 30000
import os
import logging

# 忽略 Windows 下 asyncio 关闭 Proactor pipe 时产生的无害报错
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# 导入数据库模型和会话函数
from models import Company, Contact, get_session

# 设置环境变量隐藏 Node.js 的弃用警告
os.environ['NODE_NO_WARNINGS'] = '1'

# 定义保存登录状态的文件名
AUTH_FILE = "auth_state.json"

def login_and_save_state():
    with sync_playwright() as p:
        # 通过 CDP 协议连接到本地已开启调试端口的 Chrome 浏览器
        browser = p.chromium.connect_over_cdp(DEFAULT_CDP_ENDPOINT)
        
        # 获取已经存在的默认上下文，而不是使用 new_context() 新开一个隔离窗口
        if len(browser.contexts) > 0:
            # 使用现有的上下文，直接复用已有的浏览器窗口和登录状态
            context = browser.contexts[0]
            print("已连接到现有的 Chrome 窗口...")
        else:
            # 如果没有上下文，则创建一个全新的上下文
            context = browser.new_context()
            
        # 在现有的上下文中打开一个新标签页
        page = context.new_page()
        
        # 2. 访问你需要登录的网站，比如微信网页版、淘宝等
        page.goto("https://xunkebao.baidu.com/#/")
        
        # ==========================================================
        # 3. 核心：在这里暂停，等待你扫码登录成功
        # ==========================================================
        
        # 既然登录后网址不会改变，我们需要监听 DOM 元素变化或网络请求
        
        # 方法 A (推荐): 等待登录成功后才会出现的网页元素
        # 比如登录成功后页面上会出现“退出”、“个人中心”或者用户的手机号/名字
        try:
            print("请在打开的浏览器中扫码登录...")
            # timeout=0 表示无限期等待，直到带有 el-dropdown 类的 div 内部出现了子元素
            # '//div[@class="el-dropdown"]/*[1]' 意味着寻找 el-dropdown 下的第一个直接子元素
            page.wait_for_selector('//div[@class="el-dropdown"]/*[1]', timeout=0) 
            print("检测到已登录状态的页面元素，登录成功！")
        except Exception as e:
            print("等待出错:", e)
            
        # 方法 B: 监听登录成功的后端 API 接口响应
        '''
        try:
            print("请在打开的浏览器中扫码登录...")
            # 无限期等待，直到拦截到包含 'login' (或实际的登录接口路径) 的请求，并且状态码为 200
            page.wait_for_response(lambda res: "login" in res.url and res.status == 200, timeout=0)
            print("检测到登录接口成功响应，登录完成！")
        except Exception as e:
            print("等待出错:", e)
        '''
        
        # 方法 C (最笨但最稳): 强制让代码休眠 60 秒，给你充足的时间扫码
        # page.wait_for_timeout(60000) 
        
        # ==========================================================
        
        # 登录成功后，把状态（Cookie等）保存到文件里
        context.storage_state(path=AUTH_FILE)
        # 打印保存成功的提示信息
        print(f"登录状态已保存到 {AUTH_FILE}，下次运行无需再次扫码！")

        # 登录成功并保存状态后，关闭当前用于登录的标签页
        page.close()



def search_account(account_list:list[Company]):
        
        # 接下来你就可以继续写爬取数据或自动化的代码了...
        # 1. 输入公司名 (先清空后输入)
    with sync_playwright() as p:
        # 使用无头浏览器启动，不再依赖本地开启的 Chrome
        browser = p.chromium.launch(headless=True)
        
        # 检查是否存在已保存的登录状态文件
        if not os.path.exists(AUTH_FILE):
            # 如果不存在，抛出异常提示用户先扫码登录
            raise Exception(f"找不到登录状态文件 {AUTH_FILE}，请先在系统后台点击「登录寻客宝」扫码登录！")
            
        # 使用保存的本地 Cookie 文件创建一个全新的隔离上下文
        context = browser.new_context(storage_state=AUTH_FILE)
            
        # 在该上下文中打开一个新标签页
        page = context.new_page()
        # 访问寻客宝页面
        page.goto("https://xunkebao.baidu.com/#/")
        
        for account in account_list:

            search_input = page.locator('//input[@placeholder="请输入公司名、人名、产品等关键词"]')
            search_input.clear()
            search_input.fill(account.name)

            # 2. 点击“查询一下”按钮
            page.locator('//span[text()="查询一下"]').click()

            page.wait_for_timeout(5000)

            # 3. 获取法人代表名称
            # Playwright 会自动等待元素出现，不需要手动 wait_complete
            # 解决 strict mode violation，使用 first 选取第一个匹配的元素
            name_locator = page.locator('//span[contains(text(),"法人代表")]/following-sibling::span/span').first
            name = name_locator.inner_text() if name_locator.count() > 0 else None

            if name:
                page.wait_for_timeout(5000)
                # 4. 点击“极速联系”
                
                with page.expect_response(lambda response: "/enterpriseContact/queryContactDetail" in response.url and response.status == 200) as response_info:
                
                    # 在这里面执行触发请求的动作
                    # 解决 strict mode violation，使用 first 选取第一个匹配的元素
                    page.locator('//span[text()=" 极速联系 "]').first.click()
                    
                # 当代码走到这里时，说明 API 已经请求完并返回数据了！
                response = response_info.value
                
                # 拿到 API 返回的纯数据 (直接就是字典格式)
                api_data = response.json()
                print(f"""{account.name}数据：{api_data}""")
                
                # 从api_data获取手机号 保存为Account
                # 获取数据库会话对象
                session = get_session()

                # 判断查询结果是否为空
                if  account:
                    # 修改Company实例的状态
                    account.status = '已挖掘'
                    # 提交会话以保存修改
                    session.commit()
                
                # 获取API返回结果的状态码
                res_code = api_data.get('code')
                # 判断状态码是否为'0'，表示成功
                if res_code == '0':
                    # 提取出最外层的data列表
                    outer_data = api_data.get('data', [])

                    if not outer_data:
                        account.status = '已失效'
                        # 提交会话以保存修改
                        session.commit()

                    # 遍历该data列表
                    for item in outer_data:
                        # 提取不同类型联系方式列表
                        contact_types = item.get('contactsDetailTypeAndNumsVos', [])
                        # 遍历各个类型的联系方式
                        for c_type in contact_types:
                            # 提取当前的类型编号
                            type_id = c_type.get('type')
                            # 判断类型是否为1，代表手机号
                            if type_id == 1:
                                # 提取具体的联系方式列表
                                details = c_type.get('contactsDetailAndNumsVos', [])
                                # 遍历每一个具体的联系人
                                for d in details:
                                     # 提取联系人状态 1表示可拨通
                                    contact_status= d.get('status')
                                    if contact_status != 1:
                                        continue
                                    # 提取联系人姓名
                                    contact_name = d.get('name')
                                    # 提取联系人手机号
                                    contact_value = d.get('value')
                                    # 尝试通过手机号在数据库查询联系人
                                    existing_contact = session.query(Contact).filter_by(phone=contact_value).first()
                                    # 判断该手机号是否已存在
                                    if not existing_contact:
                                        # 初始化默认的简称和联系人姓名
                                        shortname = '老板'
                                        # 如果联系人姓名不是“未知”且存在
                                        if contact_name and contact_name != '未知':
                                            # 去掉联系人姓名中的星号和空格作为最终存入数据库的姓名
                                            contact_name = contact_name.replace('*', '').replace(' ', '')
                                            # 提取联系人的姓氏
                                            surname = contact_name[0] if contact_name else ''
                                            # 判断联系人姓氏是否与法人代表的姓氏一致
                                            if name and surname and surname == name[0]:
                                                # 如果一致，则拼接“董”作为简称
                                                shortname = surname + '董'
                                            else:
                                                # 如果不一致，则拼接“总”作为简称
                                                shortname = surname + '总'
                                        # 如果不存在，则创建新的Contact实例，并传入相应的简称
                                        new_contact = Contact(company_id=account.id, name=f"{contact_name}({name})", shortname=shortname, phone=contact_value)
                                        # 将新的联系人对象添加到会话中
                                        session.add(new_contact)
                

                
                # 提交所有新增联系人到数据库
                session.commit()
                # 关闭数据库会话
                session.close()

                # 9. 点击“收起”
                page.locator('//span[text()="收起"]').click()
            else:
                print("未找到法人代表名称")
                # 判断查询结果是否为空
                if  account:
                    # 获取数据库会话对象
                    session = get_session()
                    # 修改Company实例的状态为已失效
                    account.status = '已失效'
                    # 提交会话以保存修改
                    session.commit()
                    # 关闭会话
                    session.close()
        # 任务完成后关闭上下文
        context.close()
        # 关闭无头浏览器实例
        browser.close()

if __name__ == "__main__":
    login_and_save_state()