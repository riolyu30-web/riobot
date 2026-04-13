import os
import threading
import time
from datetime import datetime, timedelta

import uiautomation

import dialog

import pc

import chrome

import dataframe
import auth
import network, picture
import client


def worker1():
    chrome.open("https://xunkebao.baidu.com/")
    pass


def worker2():
    window = dialog.create_window("【A8】一键获取厂家微信并加好友")
    dialog.add_text_row(window, 1,
                        '找厂家找供应商，我们可以尝试加对方负责人为好友\n\n==使用说明==\n第1步：运行前确定【启动微信】并【成功登录】弹出的网站\n第2步：或录入【公司名单】或者录入【联系人名单】\n第3步：点击确认并离开鼠标等待【程序跑完】')
    dialog.add_tips_row(window, 2,
                        '仅供学习研究，侵权必究！切勿用于商业行为，后果自负！')
    dialog.add_text_row(window, 3,
                        '①：指定一个txt文件，脚本会按公司名去查询对方联系方式')
    file_entry = dialog.add_file_row(window, 4, "公司名单", dialog.select_one_file, "")
    dialog.add_text_row(window, 5,
                        '②：指定一个xlsx文件，脚本会按名单启动微信加好友\n启动前需要设置加好友请求语与标签')
    xlsx_entry = dialog.add_file_row(window, 6, "微信名单", dialog.select_one_file, "")
    intro_entry = dialog.add_input_row(window, 7, "申请语")
    intro_entry.insert(0, "老板，我家主营天丝面料，专供二批，可否发您报价表")
    flag_entry = dialog.add_input_row(window, 8, "标签")
    flag_entry.insert(0, "拼多多")

    def start():
        file_path = file_entry.get()
        xlsx_path = xlsx_entry.get()
        intro_str = intro_entry.get()
        flag_str = flag_entry.get()
        browser = chrome.get_current_browser()

        if xlsx_path:
            chrome.quit(browser)
            worker3_start(xlsx_path, intro_str, flag_str)
        else:
            xlsx_path = start_crawling(file_path,browser)
            chrome.quit(browser)
            worker3_start(xlsx_path, intro_str, flag_str)
        dialog.close(window, progress_bar, "程序已跑完")

    progress_bar = dialog.add_button_row(window, 9, start)
    dialog.show(window)


def worker3_start(xlsx_path, intro_str, flag_str):
    df = dataframe.import_by_xlsx(xlsx_path)
    file_dir = os.path.dirname(xlsx_path)
    log_file = file_dir + "/log.txt"
    # 遍历 "微信名" 列
    window_control = client.get_window('WeChatMainWndForPC')
    # 遍历 "微信名" 列，同时获取序号和微信名
    for index, row in df.iterrows():
        wechat_name = row["微信名"]
        control = client.get_control(window_control.ButtonControl(Name='聊天', Depth=4))
        client.click(control)
        # 执行与“微信名”相关的操作
        control = client.get_control(window_control.PaneControl(Depth=3).EditControl(Name='搜索', Depth=4))
        client.send_keys(control, wechat_name)
        control = client.get_control(client.find_one(window_control, "网络查找手机/QQ号"))
        if client.click(control):
            control = client.get_control(window_control.PaneControl(
                foundIndex=2, Depth=3).ButtonControl(Name='确定', Depth=1))
            if client.click(control):
                pc.append_file(log_file, str(wechat_name) + "找不到该用户")
                print(str(wechat_name) + "找不到该用户")
            else:
                pan = client.get_control(
                    uiautomation.PaneControl(Name='微信', ClassName='ContactProfileWnd', Depth=1))
                control = client.find_one(pan, "添加到通讯录")
                if client.click(control):
                    if intro_str:
                        control = client.get_control(window_control.EditControl(Depth=8))
                        client.send_keys(control, intro_str)
                    if flag_str:
                        control = client.get_control(
                            window_control.PaneControl(foundIndex=3, Depth=6).EditControl(Depth=3))
                        client.send_keys(control, flag_str)
                        pc.enter()
                    control = client.get_control(
                        window_control.PaneControl(foundIndex=2, Depth=3).ButtonControl(Name='确定', Depth=1))
                    if client.click(control):
                        control = client.get_control(window_control.WindowControl(Name='微信', ClassName='AlertDialog',
                                                                                  Depth=1).PaneControl(ClassName='',
                                                                                                       Depth=1).PaneControl(
                            Depth=1).PaneControl(Depth=1).ButtonControl(Name='关闭', Depth=1)
                                                     )
                        if client.click(control):
                            pc.append_file(log_file, str(wechat_name) + "今天到此为止")
                            print(str(wechat_name) + "今天到此为止")
                            break
                    pc.append_file(log_file, str(wechat_name) + "成功发送请求")
                    print(str(wechat_name) + "成功发送请求")
                    pc.wait()
                else:
                    pc.append_file(log_file, str(wechat_name) + "该用户已添加")
                    print(str(wechat_name) + "该用户已添加")
                    pc.wait()


def start_crawling(file_path,browser):
    content = pc.read_file(file_path)
    if content:
        desc = ["公司", "微信名", "法人", "联系人", "操作记录"]
        df = dataframe.create_by_header(desc)
        time_str = pc.get_date_str()
        file_dir = pc.make_dir(os.path.dirname(file_path), "a8")
        xlsx_path = file_dir + "/" + time_str + "-微信名单.xlsx"
        lines = content.splitlines()
        for company in lines:
            xpath = '//input[@placeholder="请输入公司名、人名、产品等关键词"]'
            chrome.clear(browser, xpath)
            chrome.send_keys(browser, xpath, company)
            xpath = '//span[text()="查询一下"]'
            chrome.click(browser, xpath)
            chrome.wait_complete(browser)
            xpath = '//span[contains(text(),"法人代表")]/following-sibling::span/span'
            name = chrome.get_text(browser, xpath)
            if name:
                xpath = '//span[text()=" 极速联系 "]'
                chrome.click(browser, xpath)
                xpath = '//div[@data-text="手机"]/following-sibling::div/div[@class="dis-start-desc open-dis"]'
                count = chrome.count(browser, xpath)
                if count > 0:
                    for i in range(count):
                        xpath = '//div[@data-text="手机"]/following-sibling::div/div[@class="dis-start-desc open-dis"]/div[@class="check"]/span'
                        check = chrome.get_text(browser, xpath, i)
                        xpath = '//div[@data-text="手机"]/following-sibling::div/div[@class="dis-start-desc open-dis"]/div[@class="p"]/div[@class="name-con"]/div[@class="name-img"]'
                        con = chrome.get_text(browser, xpath, i)
                        xpath = '//div[@data-text="手机"]/following-sibling::div/div[@class="dis-start-desc open-dis"]/div[@class="p"]/div[@class="name-con"]/span[@class="text f-1"]'
                        phone = chrome.get_text(browser, xpath, i)
                        if "沉默号码" in check or "可拨通" in check:
                            row = [company, phone, name, con, ""]
                            dataframe.append_row(df, row)

                dataframe.export_to_xlsx(df, xlsx_path)
                xpath = '//span[text()="收起"]'
                chrome.click(browser, xpath)
        return xlsx_path
    return None


def main():
    # 创建线程对象
    thread1 = threading.Thread(target=worker1)
    thread2 = threading.Thread(target=worker2)

    # 启动线程
    thread1.start()
    thread2.start()

    # 等待所有线程完成
    thread1.join()
    thread2.join()


#f auth.run("a8", b'vrhZPaH9b_x8gK3o8Vh6SV7YM8SEV2aJtOezLGLpfXI=',True):
main()
