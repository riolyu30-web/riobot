import time
import logging
from pyweixin import Messages
from models import get_session, Contact, Opportunity, Task, Message
from sqlalchemy import literal

# 配置日志输出格式
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_and_process():
    """检查新消息并处理CRM业务逻辑"""
    logging.info("开始检查新消息...")
    db = get_session()
    try:
        # 调用 pyweixin 的底层方法获取新消息，包含发送者信息
        new_msgs_dict = Messages.check_new_messages(with_sender=True, close_weixin=False)
        
        if not new_msgs_dict:
            logging.info("没有收到新消息。")
            return

        for chat_name, msgs in new_msgs_dict.items():
            
                       
            # 1. 检查有没有商机名等于 chat_name 的商机
            # 在 Opportunity 表中查询商机名精确等于 chat_name 的第一条记录
            opp = db.query(Opportunity).filter(Opportunity.name == chat_name).first()
            # 如果不存在该商机
            if not opp:
                # 2. 检查是否 chat_name 包含了客户手机号（手机号是唯一的）
                contact = db.query(Contact).filter(Contact.phone != None, Contact.phone != '', literal(chat_name).contains(Contact.phone)).first()
                # 如果没有匹配到对应的客户
                if not contact:
                    # 记录日志，说明该消息的发件人不是 CRM 客户
                    logging.info(f"忽略来自 {chat_name} 的消息：未匹配到客户手机号。")
                    # 跳过当前循环，处理下一个发件人
                    continue                
                # 实例化一条新的商机记录
                opp = Opportunity(
                    # 关联对应的客户ID
                    contact_id=contact.id,
                    # 将商机名称设置为 chat_name
                    name=chat_name,
                    # 设置商机初始阶段
                    stage="需求沟通",
                    # 设置商机级别
                    level="B"
                )
                # 将新商机添加到数据库会话中
                db.add(opp)
                # 刷新会话以获取自增的商机ID
                db.flush()
                # 改变原来 contact 的状态为“已通过”
                contact.status = "已通过"
            logging.info(f"会话名称为 {opp.name}。")
            # 3. 把当前的对话加到历史记录里
            # 遍历当前获取到的所有新消息
            for msg in msgs:
                # 获取当前消息发送者
                sender = msg.get('sender', '')
                # 获取当前消息内容
                content = msg.get('content', '')
                
                # 在数据库中查询是否已存在相同商机、相同发送者且相同内容的消息
                existing_msg = db.query(Message).filter(
                    Message.opportunity_id == opp.id,
                    Message.sender == sender,
                    Message.content == content
                ).first()
                
                # 如果数据库中不存在相同的消息记录
                if not existing_msg:
                    # 实例化一条新的 Message 记录作为历史记录
                    new_message = Message(
                        # 关联到对应的商机ID
                        opportunity_id=opp.id,
                        # 设置消息发送者
                        sender=sender,
                        # 设置消息内容
                        content=content
                    )
                    # 将新消息记录添加到数据库会话中
                    db.add(new_message)
            # 记录日志，提示聊天记录处理完毕
            logging.info(f"已处理并去重后将聊天记录保存到商机(ID:{opp.name})名下。")
                
            # 4. 如果 msgs 有“通过了你的朋友验证请求”，生成一个任务
            # 初始化一个标志位，用于记录是否包含好友验证通过的消息
            just_approved = False
            # 遍历当前获取到的所有新消息
            for msg in msgs:
                # 获取消息内容字符串
                content = msg.get('content', '')
                # 判断内容中是否包含好友验证的提示语
                if '通过了你的朋友验证请求' in content:
                    # 如果包含，则将标志位设为 True
                    just_approved = True
                    # 找到目标消息后跳出循环
                    break
            # 如果标志位为 True，即刚刚通过了好友验证
            if just_approved:         
                # 实例化一条新的 Task 记录
                task = Task(
                    opportunity_id=opp.id,
                    # 设置任务的内容说明
                    content="通过好友验证，请及时与客户进行初步沟通并记录需求",
                    # 设置任务状态
                    status="待办中",
                    # 设置任务类型为对话
                    type="对话"
                )
                # 将新任务添加到数据库会话中
                db.add(task)
            elif msgs:
                # 检查最后一条消息是否来自对方
                last_msg = msgs[-1]
                sender = last_msg.get('sender', '')
                # 如果发送者名称与客户/商机名称匹配（说明是对方发来的消息，不是自己发出的）
                if sender == chat_name:
                    # 提取该轮所有来自客户的消息并拼接到一起
                    customer_msgs = [m.get('content', '') for m in msgs if m.get('sender', '') == chat_name]
                    combined_content = "\n".join(customer_msgs)

                    # 将商机的相关信息和客户所有的对话组装到内容中
                    task_content = f"请及时回复客户的新提问：\n{combined_content}"
                    
                    # 实例化一条新的 Task 记录，提示需要回复客户
                    task = Task(
                        opportunity_id=opp.id,
                        content=task_content,
                        status="待办中",
                        type="对话"
                    )
                    # 将新任务添加到数据库会话中
                    db.add(task)
                    logging.info(f"为商机(ID:{opp.id})生成了新消息回复任务。")
            
                
        # 提交所有数据库变更
        db.commit()
        logging.info("本轮消息处理完成，已保存数据。")
        
    except Exception as e:
        logging.error(f"处理消息时发生异常: {e}")
        db.rollback()
    finally:
        db.close()

def main():
    """主循环，每5分钟执行一次"""
    logging.info("CRM 微信消息监听服务已启动...")
    while True:
        check_and_process_messages()
        # 等待5分钟 (300秒) 后进行下一轮检查
        logging.info("等待 5 分钟后进行下一轮检查...")
        time.sleep(300)

if __name__ == "__main__":
    main()