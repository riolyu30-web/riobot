# 导入操作系统模块
import os
# 导入日期时间模块
from datetime import datetime
# 导入SQLAlchemy的核心组件
from sqlalchemy import create_engine, Column, Integer, String, DateTime, ForeignKey, Float, Text, JSON, Table
# 导入SQLAlchemy的ORM组件
from sqlalchemy.orm import declarative_base, relationship, sessionmaker

# 获取当前文件所在目录的绝对路径
DB_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼接SQLite数据库文件的绝对路径
DB_PATH = os.path.join(DB_DIR, 'crm.db')
# 创建数据库引擎，连接到SQLite数据库
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
# 创建声明式的基类
Base = declarative_base()

# 定义 Sales 和 Tag 的多对多关联表
sales_tags_association = Table(
    'sales_tags', Base.metadata,
    Column('sales_id', Integer, ForeignKey('sales.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

# 定义 Company 和 Tag 的多对多关联表
company_tags_association = Table(
    'company_tags', Base.metadata,
    Column('company_id', Integer, ForeignKey('companies.id')),
    Column('tag_id', Integer, ForeignKey('tags.id'))
)

# 定义 Tag 类，映射到 tags 表
class Tag(Base):
    # 定义表名为 tags
    __tablename__ = 'tags'
    # 定义 id 字段，为主键，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 定义标签名字段，字符串类型，不能为空
    name = Column(String(50), nullable=False, unique=True)
    # 定义标签描述字段，字符串类型
    description = Column(String(255))
    # 定义与 Sales 的多对多关系
    sales = relationship("Sales", secondary=sales_tags_association, back_populates="tags")
    # 定义与 Company 的多对多关系
    companies = relationship("Company", secondary=company_tags_association, back_populates="tags")
    # 定义对象的字符串表示方法
    def __str__(self):
        return f"{self.name}"

# 定义Sales类，映射到sales表
class Sales(Base):
    # 定义表名为sales
    __tablename__ = 'sales'
    # 定义id字段，为主键，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 定义姓名字段，字符串类型，不能为空
    name = Column(String(100), nullable=False)
    # 定义手机号字段，字符串类型
    phone = Column(String(20))
    # 定义平台字段，字符串类型
    platform = Column(String(50))
    # 定义标签字段，多对多关联 Tag 模型
    tags = relationship("Tag", secondary=sales_tags_association, back_populates="sales")
    # 定义创建时间字段，默认当前时间
    created_at = Column(DateTime, default=datetime.now)
    # 定义与Friend的一对多关系
    friends = relationship("Friend", back_populates="sales")
    # 定义对象的字符串表示方法
    def __str__(self):
        # 返回销售人员姓名
        return f"{self.name}"

# 定义Company类，映射到companies表
class Company(Base):
    # 定义表名为companies
    __tablename__ = 'companies'
    # 定义id字段，为主键，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 定义公司名字段，字符串类型，不能为空
    name = Column(String(100), nullable=False)
    # 定义简称字段，字符串类型
    shortname = Column(String(100))
    # 定义核心词字段，字符串类型，默认为空
    keyword = Column(String(255), default='')
    # 定义来源词字段，字符串类型
    source_words = Column(String(255))
    # 定义标签字段，多对多关联 Tag 模型
    tags = relationship("Tag", secondary=company_tags_association, back_populates="companies")
    # 定义等级字段，字符串类型，默认为空字符串
    level = Column(String(20), default='?')
    # 定义认证字段，白、红、紫，默认为'白'
    certification = Column(String(20), default='白')
    # 定义店铺链接字段，字符串类型
    shop_link = Column(String(255))
    # 定义商品链接字段，字符串类型
    product_link = Column(String(255))
    # 定义状态字段，待挖掘、已挖掘、已失效
    status = Column(String(20), default='待挖掘')
    # 定义创建时间字段，默认当前时间
    created_at = Column(DateTime, default=datetime.now)
    # 定义与Contact的一对多关系
    contacts = relationship("Contact", back_populates="company")
    # 定义对象的字符串表示方法
    def __str__(self):
        # 返回公司名称
        return f"{self.name}"

# 定义Contact类，映射到contacts表
class Contact(Base):
    # 定义表名为contacts
    __tablename__ = 'contacts'
    # 定义id字段，为主键，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 定义姓名字段，字符串类型，不能为空
    name = Column(String(100), nullable=False)
    # 定义手机号字段，字符串类型
    phone = Column(String(20))
    # 定义关联公司的外键字段
    company_id = Column(Integer, ForeignKey('companies.id'))
    # 定义简称字段，字符串类型，默认为“老板”
    shortname = Column(String(100), default='老板')
    # 定义状态字段，未验证, 已请求, 被拒绝，已失效，已通过
    status = Column(String(20), default='未验证')
    # 定义创建时间字段，默认当前时间
    created_at = Column(DateTime, default=datetime.now)
    # 定义与Company的多对一关系
    company = relationship("Company", back_populates="contacts")
    # 定义与Friend的一对多关系
    friends = relationship("Friend", back_populates="contact")
    # 定义对象的字符串表示方法
    def __str__(self):
        # 返回客户姓名和简称
        return f"{self.name} - {self.shortname}"

    # 定义获取公司核心词的属性
    @property
    def company_keyword(self):
        # 如果存在关联公司则返回其核心词，否则返回空
        return self.company.keyword if self.company else None

    # 定义获取公司等级的属性
    @property
    def company_level(self):
        # 如果存在关联公司则返回其等级，否则返回空
        return self.company.level if self.company else None

    # 定义获取公司认证的属性
    @property
    def company_certification(self):
        # 如果存在关联公司则返回其认证，否则返回空
        return self.company.certification if self.company else None

    # 定义获取公司店铺链接的属性
    @property
    def company_shop_link(self):
        # 如果存在关联公司则返回其店铺链接，否则返回空
        return self.company.shop_link if self.company else None

    # 定义获取公司商品链接的属性
    @property
    def company_product_link(self):
        # 如果存在关联公司则返回其商品链接，否则返回空
        return self.company.product_link if self.company else None

    # 定义获取公司标签的属性
    @property
    def company_tags(self):
        # 如果存在关联公司且有标签则返回以逗号分隔的标签字符串，否则返回空
        return ", ".join([tag.name for tag in self.company.tags]) if self.company and self.company.tags else None

# 定义Friend类，映射到friends表
class Friend(Base):
    # 定义表名为friends
    __tablename__ = 'friends'
    # 定义id字段，为主键，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 定义关联客户的外键字段
    contact_id = Column(Integer, ForeignKey('contacts.id'))
    # 定义昵称字段，字符串类型
    nickname = Column(String(100))
    # 定义等级字段，字符串类型
    level = Column(String(20))
    # 定义关联销售人员的外键字段
    sales_id = Column(Integer, ForeignKey('sales.id'))
    # 定义创建时间字段，默认当前时间
    created_at = Column(DateTime, default=datetime.now)
    # 定义与Contact的多对一关系
    contact = relationship("Contact", back_populates="friends")
    # 定义与Sales的多对一关系
    sales = relationship("Sales", back_populates="friends")
    # 定义与Order的一对多关系
    orders = relationship("Order", back_populates="friend")
    # 定义与Task的一对多关系
    tasks = relationship("Task", back_populates="friend")
    # 定义对象的字符串表示方法
    def __str__(self):
        # 返回好友ID标识
        return f"{self.nickname}"

# 定义Order类，映射到orders表
class Order(Base):
    # 定义表名为orders
    __tablename__ = 'orders'
    # 定义id字段，为主键，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 定义关联好友的外键字段
    friend_id = Column(Integer, ForeignKey('friends.id'))
    # 定义订单类型字段，大货、调样
    order_type = Column(String(50))
    # 定义状态字段，正常、撤销
    status = Column(String(20), default='正常')
    # 定义总金额字段，浮点数类型
    total_amount = Column(Float)
    # 定义订单时间字段，日期时间类型
    order_time = Column(DateTime)
    # 定义订单细节字段，长文本类型
    order_details = Column(Text)
    # 定义创建时间字段，默认当前时间
    created_at = Column(DateTime, default=datetime.now)
    # 定义与Friend的多对一关系
    friend = relationship("Friend", back_populates="orders")
    # 定义对象的字符串表示方法
    def __str__(self):
        # 返回订单ID标识
        return f"{self.id}"

# 定义Task类，映射到tasks表
class Task(Base):
    # 定义表名为tasks
    __tablename__ = 'tasks'
    # 定义id字段，为主键，自动递增
    id = Column(Integer, primary_key=True, autoincrement=True)
    # 定义任务描述字段，长文本类型
    description = Column(Text, nullable=False)
    # 定义截止日期字段，日期时间类型
    due_date = Column(DateTime)
    # 定义关联好友的外键字段
    friend_id = Column(Integer, ForeignKey('friends.id'))
    # 定义状态字段，待执行、已完成、已撤销
    status = Column(String(20), default='待执行')
    # 定义创建时间字段，默认当前时间
    created_at = Column(DateTime, default=datetime.now)
    # 定义与Friend的多对一关系
    friend = relationship("Friend", back_populates="tasks")
    # 定义对象的字符串表示方法
    def __str__(self):
        # 返回任务ID和状态
        return f"{self.id} [{self.status}]"

# 定义初始化数据库表结构的函数
def init_db():
    # 创建所有定义的表结构
    Base.metadata.create_all(engine)
    # 打印数据库创建成功的消息
    print(f"数据库已创建: {DB_PATH}")

# 定义获取数据库会话的函数
def get_session():
    # 创建sessionmaker实例绑定到引擎
    Session = sessionmaker(bind=engine)
    # 返回一个新的数据库会话对象
    return Session()

# 判断是否为主程序运行
if __name__ == '__main__':
    # 调用初始化数据库函数
    init_db()
