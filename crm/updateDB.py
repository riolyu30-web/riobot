# 导入 sqlite3 模块以操作 SQLite 数据库
import sqlite3
import os

# 获取当前文件所在目录的绝对路径
DB_DIR = os.path.dirname(os.path.abspath(__file__))
# 拼接SQLite数据库文件的绝对路径
DB_PATH = os.path.join(DB_DIR, 'crm_v3.db')

def update_db():
    # 连接到数据库
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查 companies 表中是否有 shortname 字段
    cursor.execute("PRAGMA table_info(companies)")
    columns = [col[1] for col in cursor.fetchall()]
    
    # 如果不存在 shortname 字段，则执行 ALTER TABLE 添加
    if 'shortname' not in columns:
        print("添加 shortname 字段到 companies 表...")
        cursor.execute("ALTER TABLE companies ADD COLUMN shortname VARCHAR(100)")
        conn.commit()
        print("字段添加成功！")
    else:
        print("shortname 字段已存在，跳过添加。")
        
    # 检查 friends 表中是否有 nickname 字段
    cursor.execute("PRAGMA table_info(friends)")
    friends_columns = [col[1] for col in cursor.fetchall()]
    
    if 'nickname' not in friends_columns:
        print("添加 nickname 字段到 friends 表...")
        cursor.execute("ALTER TABLE friends ADD COLUMN nickname VARCHAR(100)")
        conn.commit()
        print("字段 nickname 添加成功！")
    else:
        print("nickname 字段已存在，跳过添加。")
    
    # 更新已有数据的 shortname
    print("开始更新现有公司的 shortname...")
    # 查询 shortname 为空的公司
    cursor.execute("SELECT id, name FROM companies WHERE shortname IS NULL OR shortname = ''")
    companies = cursor.fetchall()
    
    # 定义需要被去除的通用词汇
    common_words = [
        "有限公司", "有限责任公司", "电子商务", "经营部", "(个体工商户)", 
        "（个体工商户）", "个体工商户", "商贸", "贸易", "实业", "服饰", 
        "服装", "纺织", "针织", "工作室", "厂", "店", "批发", "零售", "制造"
    ]
    
    update_count = 0
    # 遍历需要更新的公司
    for comp_id, name in companies:
        if not name:
            continue
            
        shortname = name
        # 遍历去除这些通用词
        for word in common_words:
            shortname = shortname.replace(word, "")
        # 去除可能产生的多余空格
        shortname = shortname.strip()
        
        # 更新数据库中的 shortname
        cursor.execute("UPDATE companies SET shortname = ? WHERE id = ?", (shortname, comp_id))
        update_count += 1
        
    # 提交事务并关闭连接
    conn.commit()
    conn.close()
    print(f"数据库更新完成！共更新了 {update_count} 个公司的简称。")

if __name__ == '__main__':
    update_db()
