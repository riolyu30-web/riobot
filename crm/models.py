import os
from datetime import datetime
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Text, Table
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# 定义数据库文件路径
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(DB_DIR, 'crm.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
Base = declarative_base()

class Account(Base):
    """公司 (Account) ：经过寻客宝查询，系统会自动把这个 Lead 拆分成一个“公司”"""
    __tablename__ = 'accounts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(100), nullable=False)  # 姓名或公司名
    flag = Column(String(50), default='未知')                 # 线索来源标志
    status = Column(String(20), default='未挖掘')  # 未挖掘, 已挖掘, 已丢单
    created_at = Column(DateTime, default=datetime.now)

    # 一对多关系：一个公司有多个联系人
    contacts = relationship("Contact", back_populates="account")

    def __str__(self):
        return f"{self.name} (Account)"



class Contact(Base):
    """客户 (Contact) ：经过寻客宝查询，系统会自动把这个 Lead 拆分成一个“客户”"""
    __tablename__ = 'contacts'

    id = Column(Integer, primary_key=True, autoincrement=True)
    account_id = Column(Integer, ForeignKey('accounts.id'))
    name = Column(String(50), nullable=False)
    phone = Column(String(20), nullable=False)
    tags = Column(String(20), default='未知')
    status = Column(String(20), default='未验证')  # 未验证, 已请求, 被拒绝，已失效，已通过
    created_at = Column(DateTime, default=datetime.now)

    # 关系映射
    account = relationship("Account", back_populates="contacts")
    opportunities = relationship("Opportunity", back_populates="contact")

    def __str__(self):
        return f"{self.name} - {self.phone or '无电话'}"

class Opportunity(Base):
    """建立商机 (Opportunities) ：针对客户建一个具体的会话、聊天室”"""
    __tablename__ = 'opportunities'

    id = Column(Integer, primary_key=True, autoincrement=True)
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    name = Column(String(100), nullable=False)
    stage = Column(String(50), default='需求沟通') # 需求沟通、报价、赢单、丢单
    level = Column(String(10))                     # A, B, C 等级
    remark = Column(String(100),  default='')            # 备注
    created_at = Column(DateTime, default=datetime.now)

    # 关系映射
    contact = relationship("Contact", back_populates="opportunities")
    tasks = relationship("Task", back_populates="opportunity")
    messages = relationship("Message", back_populates="opportunity")

    def __str__(self):
        return f"{self.name}"

class Task(Base):
    """派发任务 (Tasks) ： 关联商机，按SOP自动生成一个 Task"""
    __tablename__ = 'tasks'

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=True)
    content = Column(Text, nullable=False)          # 任务内容：比如“朋友圈给对方点3个赞”
    response = Column(Text, nullable=True)          # 响应内容：执行任务后的长文本反馈
    status = Column(String(20), default='待办中')  # 待办中, 处理中, 已完成，被中断
    type = Column(String(20), default='对话')  # 对话, 发朋友圈, 点赞
    due_date = Column(DateTime)                     # 截止日期
    created_at = Column(DateTime, default=datetime.now)

    # 关系映射
    opportunity = relationship("Opportunity", back_populates="tasks")

    def __str__(self):
        return f"[{self.status}] {self.content[:15]}..."

class Message(Base):
    """聊天信息 (Message) ：记录与客户的聊天信息，关联商机"""
    __tablename__ = 'messages'

    id = Column(Integer, primary_key=True, autoincrement=True)
    opportunity_id = Column(Integer, ForeignKey('opportunities.id'), nullable=True)
    sender = Column(String(100), nullable=False)    # 发送者名称
    content = Column(Text, nullable=False)          # 消息内容
    created_at = Column(DateTime, default=datetime.now)

    # 关系映射
    opportunity = relationship("Opportunity", back_populates="messages")

    def __str__(self):
        return f"{self.sender}: {self.content[:15]}..."

def init_db():
    """初始化数据库表结构"""
    Base.metadata.create_all(engine)
    print(f"数据库已创建: {DB_PATH}")

def get_session():
    """获取数据库会话"""
    Session = sessionmaker(bind=engine)
    return Session()

if __name__ == '__main__':
    # 如果直接运行此脚本，则初始化数据库
    init_db()
