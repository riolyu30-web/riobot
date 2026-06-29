import click # 导入 Click 库，用于构建命令行界面
import sqlite3 # 导入 sqlite3 模块，用于 SQLite 数据库操作
from datetime import date as datetime_date # 导入日期类并重命名，避免与命令参数重名

DATABASE_NAME = 'account.db' # 定义数据库文件名

def get_db_connection(): # 定义获取数据库连接的函数
    """
    获取 SQLite 数据库连接。
    """
    conn = sqlite3.connect(DATABASE_NAME) # 连接到 SQLite 数据库
    conn.row_factory = sqlite3.Row # 设置行工厂，使查询结果可以像字典一样访问
    return conn # 返回数据库连接

def init_db(): # 定义初始化数据库的函数
    """
    初始化数据库，创建 transactions 表。
    """
    conn = get_db_connection() # 获取数据库连接
    cursor = conn.cursor() # 获取游标对象
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            type TEXT NOT NULL,
            amount REAL NOT NULL,
            description TEXT,
            date TEXT NOT NULL
        )
    ''')
    conn.commit() # 提交事务
    conn.close() # 关闭数据库连接

def normalize_date_text(date_text): # 定义日期规范化函数
    """
    将日期文本规范化为 YYYY-MM-DD。
    """
    try: # 尝试解析日期文本
        year_text, month_text, day_text = str(date_text).split('-') # 将日期文本按连字符拆分为年月日
        normalized_date = datetime_date(int(year_text), int(month_text), int(day_text)) # 使用年月日构造标准日期对象
    except ValueError as error: # 如果日期文本格式或数值非法
        raise click.BadParameter('日期格式必须为 YYYY-MM-DD。') from error # 抛出 Click 参数错误并提示用户
    return normalized_date.isoformat() # 返回标准化后的日期字符串

@click.group() # 使用 @click.group() 装饰器定义一个命令组
def cli(): # 定义主命令组函数
    """
    一个简单的记账 CLI 工具。
    """
    init_db() # 在 CLI 启动时初始化数据库
    pass # 命令组本身不需要执行任何操作，所以使用 pass

@cli.command() # 使用 @cli.command() 装饰器定义一个子命令
@click.argument('amount', type=float) # 定义金额参数，类型为浮点数
@click.argument('description') # 定义描述参数
@click.option('--date', 'txn_date', default=None, help='交易日期 (YYYY-MM-DD). 默认为今天.') # 定义日期选项并映射到不冲突的参数名
def expense(amount, description, txn_date): # 定义支出命令函数
    """
    记录一笔支出。
    """
    if txn_date is None: # 如果没有提供日期
        txn_date = datetime_date.today().isoformat() # 使用 datetime 模块获取今天日期并格式化为 YYYY-MM-DD
    else: # 如果提供了日期
        txn_date = normalize_date_text(txn_date) # 将输入日期规范化为 YYYY-MM-DD
    conn = get_db_connection() # 获取数据库连接
    cursor = conn.cursor() # 获取游标对象
    cursor.execute('INSERT INTO transactions (type, amount, description, date) VALUES (?, ?, ?, ?)', # 插入支出记录
                   ('expense', amount, description, txn_date)) # 绑定参数
    conn.commit() # 提交事务
    conn.close() # 关闭数据库连接
    click.echo(f"记录支出: {amount:.2f} - {description} (日期: {txn_date})") # 输出成功信息

@cli.command() # 使用 @cli.command() 装饰器定义一个子命令
@click.argument('amount', type=float) # 定义金额参数，类型为浮点数
@click.argument('description') # 定义描述参数
@click.option('--date', 'txn_date', default=None, help='交易日期 (YYYY-MM-DD). 默认为今天.') # 定义日期选项并映射到不冲突的参数名
def income(amount, description, txn_date): # 定义收入命令函数
    """
    记录一笔收入。
    """
    if txn_date is None: # 如果没有提供日期
        txn_date = datetime_date.today().isoformat() # 使用 datetime 模块获取今天日期并格式化为 YYYY-MM-DD
    else: # 如果提供了日期
        txn_date = normalize_date_text(txn_date) # 将输入日期规范化为 YYYY-MM-DD
    conn = get_db_connection() # 获取数据库连接
    cursor = conn.cursor() # 获取游标对象
    cursor.execute('INSERT INTO transactions (type, amount, description, date) VALUES (?, ?, ?, ?)', # 插入收入记录
                   ('income', amount, description, txn_date)) # 绑定参数
    conn.commit() # 提交事务
    conn.close() # 关闭数据库连接
    click.echo(f"记录收入: {amount:.2f} - {description} (日期: {txn_date})") # 输出成功信息

@cli.command() # 使用 @cli.command() 装饰器定义一个子命令
@click.option('--start-date', type=click.DateTime(formats=['%Y-%m-%d']), default=None, help='开始日期，格式为 YYYY-MM-DD。') # 定义开始日期选项并限制输入格式
@click.option('--end-date', type=click.DateTime(formats=['%Y-%m-%d']), default=None, help='结束日期，格式为 YYYY-MM-DD。') # 定义结束日期选项并限制输入格式
def ledger(start_date, end_date): # 定义查看账目命令函数
    """
    显示所有交易记录。
    """
    if start_date is not None and end_date is not None and start_date > end_date: # 校验开始日期不能晚于结束日期
        raise click.BadParameter('开始日期不能晚于结束日期。') # 抛出 Click 参数错误并提示用户
    start_date_text = start_date.strftime('%Y-%m-%d') if start_date is not None else None # 将开始日期转换为数据库可比较的字符串
    end_date_text = end_date.strftime('%Y-%m-%d') if end_date is not None else None # 将结束日期转换为数据库可比较的字符串
    conn = get_db_connection() # 获取数据库连接
    cursor = conn.cursor() # 获取游标对象
    cursor.execute('SELECT id, date, type, amount, description FROM transactions') # 查询所有交易记录以便对历史日期做规范化处理
    raw_transactions = cursor.fetchall() # 获取所有原始查询结果
    conn.close() # 关闭数据库连接
    transactions = [] # 初始化规范化后的交易记录列表
    for transaction in raw_transactions: # 遍历每条原始交易记录
        normalized_date = normalize_date_text(transaction['date']) # 将数据库中的日期统一规范化
        if start_date_text is not None and normalized_date < start_date_text: # 如果记录日期早于开始日期
            continue # 跳过不在范围内的记录
        if end_date_text is not None and normalized_date > end_date_text: # 如果记录日期晚于结束日期
            continue # 跳过不在范围内的记录
        transactions.append({'id': transaction['id'], 'date': normalized_date, 'type': transaction['type'], 'amount': transaction['amount'], 'description': transaction['description']}) # 将规范化后的记录加入结果列表
    transactions.sort(key=lambda item: (item['date'], item['id']), reverse=True) # 按日期和编号倒序排列规范化后的结果

    if not transactions: # 如果没有交易记录
        click.echo("没有交易记录。") # 输出提示信息
        return # 结束函数

    income_total = sum(transaction['amount'] for transaction in transactions if transaction['type'] == 'income') # 统计筛选结果中的总收入
    expense_total = sum(transaction['amount'] for transaction in transactions if transaction['type'] == 'expense') # 统计筛选结果中的总支出
    balance_total = income_total - expense_total # 计算筛选结果中的净额
    click.echo("\n--- 交易记录 ---") # 输出标题
    for transaction in transactions: # 遍历每条交易记录
        click.echo(f"日期: {transaction['date']} | 类型: {transaction['type']} | 金额: {transaction['amount']:.2f} | 描述: {transaction['description']}") # 格式化输出交易信息
    click.echo("----------------") # 输出分隔线
    click.echo(f"记录数: {len(transactions)}") # 输出筛选范围内的记录总数
    click.echo(f"总收入: {income_total:.2f}") # 输出筛选范围内的收入总额
    click.echo(f"总支出: {expense_total:.2f}") # 输出筛选范围内的支出总额
    click.echo(f"净额: {balance_total:.2f}") # 输出筛选范围内的收支净额
    click.echo("----------------\n") # 输出分隔线

if __name__ == '__main__': # 如果脚本作为主程序运行
    cli() # 调用主命令组
