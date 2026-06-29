import time
import logging
from pyweixin import Messages
from models import get_session, Contact, Friend, Task
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
            # 1. 检查是否 chat_name 包含了客户手机号（手机号是唯一的）
            contact = db.query(Contact).filter(Contact.phone != None, Contact.phone != '', literal(chat_name).contains(Contact.phone)).first()
            if not contact:
                logging.info(f"忽略来自 {chat_name} 的消息：未匹配到客户手机号。")
                continue
                
            # 2. 检查该客户是否已经是 Friend
            friend = db.query(Friend).filter(Friend.contact_id == contact.id).first()
            if not friend:
                friend = Friend(
                    contact_id=contact.id,
                    level="B"
                )
                db.add(friend)
                db.flush()
                contact.status = "已通过"
            logging.info(f"已关联好友 (Contact: {contact.name})。")
                
            # 3. 如果 msgs 有“通过了你的朋友验证请求”，生成一个任务
            just_approved = False
            for msg in msgs:
                content = msg.get('content', '')
                if '通过了你的朋友验证请求' in content:
                    just_approved = True
                    break
            
            if just_approved:         
                task = Task(
                    friend_id=friend.id,
                    description="通过好友验证，请及时与客户进行初步沟通并记录需求",
                    status="待执行"
                )
                db.add(task)
            elif msgs:
                last_msg = msgs[-1]
                sender = last_msg.get('sender', '')
                if sender == chat_name:
                    customer_msgs = [m.get('content', '') for m in msgs if m.get('sender', '') == chat_name]
                    combined_content = "\n".join(customer_msgs)
                    task_content = f"请及时回复客户的新提问：\n{combined_content}"
                    
                    task = Task(
                        friend_id=friend.id,
                        description=task_content,
                        status="待执行"
                    )
                    db.add(task)
                    logging.info(f"为好友(ID:{friend.id})生成了新消息回复任务。")
            
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