from playwright.sync_api import sync_playwright
import os
import logging

# 忽略 Windows 下 asyncio 关闭 Proactor pipe 时产生的无害报错
logging.getLogger("asyncio").setLevel(logging.CRITICAL)

# 导入数据库模型和会话函数
from models import Account, Contact, get_session

# 定义保存登录状态的文件名
AUTH_FILE = "auth_state.json"

def login_and_save_state():
    with sync_playwright() as p:
        # 1. 必须显示浏览器，让你能看到二维码 (headless=False)
        browser = p.chromium.launch(headless=False)
        
        # 判断是否已经有保存的登录状态文件
        if os.path.exists(AUTH_FILE):
            print("找到已保存的登录状态，尝试直接使用...")
            # 加载之前的登录状态
            context = browser.new_context(storage_state=AUTH_FILE)
        else:
            print("没有找到登录状态，需要重新登录...")
            # 创建一个全新的上下文
            context = browser.new_context()
            
        page = context.new_page()
        
        # 2. 访问你需要登录的网站，比如微信网页版、淘宝等
        page.goto("https://xunkebao.baidu.com/#/")
        
        # ==========================================================
        # 3. 核心：在这里暂停，等待你扫码登录成功
        # ==========================================================
        
        # 方法 A (推荐): 等待登录成功后才会出现的网址
        # 比如登录成功后网址会变成 /dashboard 或 /home
        
        '''
        try:
            print("请在打开的浏览器中扫码登录...")
            # timeout=0 表示无限期等待，直到网址包含 dashboard 为止
            page.wait_for_url("**/dashboard**", timeout=0) 
            print("检测到网址跳转，登录成功！")
        except Exception as e:
            print("等待超时或出错:", e)
        '''
        
        # 方法 B: 等待登录成功后才会出现的网页元素
        # page.wait_for_selector("text='欢迎回来'", timeout=0)
        
        # 方法 C (最笨但最稳): 强制让代码休眠 60 秒，给你充足的时间扫码
        # page.wait_for_timeout(60000) 
        
        # ==========================================================
        
        # 4. 登录成功后，把状态（Cookie等）保存到文件里



        context.storage_state(path=AUTH_FILE)
        print(f"登录状态已保存到 {AUTH_FILE}，下次运行无需再次扫码！")



def search_account(account_list:list[Account]):
        
        # 接下来你就可以继续写爬取数据或自动化的代码了...
        # 1. 输入公司名 (先清空后输入)
    with sync_playwright() as p:
        # 1. 必须显示浏览器，让你能看到二维码 (headless=False)
        browser = p.chromium.launch(headless=True)
        
        if not os.path.exists(AUTH_FILE):
            raise Exception(f"找不到登录状态文件 {AUTH_FILE}，请先执行 python xunkebao.py 扫码登录！")
            
        context = browser.new_context(storage_state=AUTH_FILE)
        page = context.new_page()
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
                print("直接拿到的后台数据：", api_data)
                
                # 从api_data获取手机号 保存为Account
                # 获取数据库会话对象
                session = get_session()

                # 判断查询结果是否为空
                if  account:
                    # 修改Account实例的状态
                    account.status = '已挖掘'
                    # 提交会话以保存修改
                    session.commit()
                
                # 获取API返回结果的状态码
                res_code = api_data.get('code')
                # 判断状态码是否为'0'，表示成功
                if res_code == '0':
                    # 提取出最外层的data列表
                    outer_data = api_data.get('data', [])
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
                                    # 提取联系人的重要头衔（作为标签使用）
                                    contact_title = d.get('importantTitle')
                                    # 尝试通过手机号在数据库查询联系人
                                    existing_contact = session.query(Contact).filter_by(phone=contact_value).first()
                                    # 判断该手机号是否已存在
                                    if not existing_contact:
                                        # 如果不存在，则创建新的Contact实例
                                        new_contact = Contact(account_id=account.id, name=contact_name+'('+name+')', phone=contact_value)
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
                    # 修改Account实例的状态
                    account.status = '已丢单'
                    # 提交会话以保存修改
                    session.commit()
        context.close()
        browser.close()

if __name__ == "__main__":
    login_and_save_state()