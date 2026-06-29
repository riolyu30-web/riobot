# 导入sqlite3模块用于操作SQLite数据库
import sqlite3
# 导入datetime模块用于获取当前时间
import datetime
# 导入os模块用于处理文件和目录路径
import os

# 获取当前脚本所在的绝对路径目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 拼接出源数据库文件的完整路径 (crm_v3.db)
src_db_path = os.path.join(current_dir, 'crm.db')

# 获取当前系统时间，并格式化为 年月日_时分秒 的字符串
current_time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
# 构造备份数据库的文件名，加入时间戳以便区分不同版本的备份
backup_db_name = f'crm_backup_{current_time}.db'
# 拼接出备份数据库文件的完整存储路径
backup_db_path = os.path.join(current_dir,"backup",backup_db_name)
# 确保备份目录存在，如果不存在则创建
os.makedirs(os.path.dirname(backup_db_path), exist_ok=True)



# 在控制台输出开始备份的提示信息
print(f"开始备份数据库: {src_db_path} -> {backup_db_path}")

# 建立与源数据库文件的连接
src = sqlite3.connect(src_db_path)
# 建立与目标（备份）数据库文件的连接，如果文件不存在会自动创建
dst = sqlite3.connect(backup_db_path)

# 使用with上下文管理器，确保备份完成后事务正确提交
with dst:
    # 调用sqlite3的backup方法，将源数据库的所有数据和结构完整复制到目标数据库中
    src.backup(dst)

# 操作完成，关闭目标数据库的连接
dst.close()
# 操作完成，关闭源数据库的连接
src.close()

# 在控制台输出备份成功完成的提示信息
print("数据库备份成功完成！")