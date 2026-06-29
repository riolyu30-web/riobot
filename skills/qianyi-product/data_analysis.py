# 导入pandas数据处理库
import pandas as pd
# 导入os操作系统接口库
import os
# 导入json库用于生成HTML中的数据
import json

import glob

# 定义一个内部辅助方法，根据给定的目录名获取其下所有的 CSV 文件路径
def get_csv_files_from_dir(target_dir_name):
    base_dir = os.path.dirname(os.path.abspath(__file__))
    # 构造 stats 目录下的目标目录绝对路径
    target_dir = os.path.join(base_dir, 'stats', target_dir_name)
    # 使用 glob 获取该目录下所有的 .csv 文件
    csv_files = glob.glob(os.path.join(target_dir, '*.csv'))
    return csv_files




# 定义一个按国家统计贸易数据的方法，接收一个目标目录名参数
def analyze(target_dir_name="data"):
    # 获取当前py文件所在的绝对路径目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 获取目标目录下的所有CSV文件路径
    csv_paths = get_csv_files_from_dir(target_dir_name)
    
    if not csv_paths:
        print(f"在 stats/{target_dir_name} 目录下未找到任何CSV文件。")
        return
    
    # 存放所有读取的DataFrame的列表
    dfs = []
    
    for csv_path in csv_paths:
        # 尝试执行以下代码块
        try:
            # 读取CSV文件，使用gb18030编码，并将千位分隔符解析为普通数字
            # 强制指定贸易方式编码为字符串类型，避免丢失前导零或被错误解析
            df = pd.read_csv(csv_path, encoding='gb18030', thousands=',', dtype={'贸易方式编码': str})
            
            # 清理列名中的不可见字符和空格，以确保列名判断准确
            df.columns = df.columns.str.strip().str.replace('\ufeff', '').str.replace('\u200b', '')
            
            # 检查当前文件中是否存在'数据年月'列
            if '数据年月' not in df.columns:
                # 尝试从文件名中提取年月（例如：从 data20250106.csv 中提取 202501）
                file_name = os.path.basename(csv_path)
                # 使用正则查找连续的6位或8位数字
                import re
                match = re.search(r'\d{6,8}', file_name)
                if match:
                    # 如果匹配到8位，则截取前6位作为年月
                    month_val = match.group(0)[:6]
                    # 为 DataFrame 新增一列 '数据年月'，并填充提取出的年月
                    df['数据年月'] = month_val
                    print(f"文件 {file_name} 缺失'数据年月'列，已自动使用文件名补充值为: {month_val}")
                else:
                    print(f"文件 {file_name} 缺失'数据年月'列，且无法从文件名中提取出有效的年月，将被跳过。")
                    continue
                    
            dfs.append(df)
        # 捕获所有可能出现的异常
        except Exception as e:
            # 如果出错，打印出具体的错误信息
            print(f"读取文件 {csv_path} 出错: {e}")
            
    if not dfs:
        print("没有成功读取到任何数据。")
        return
        
    # 合并所有读取的DataFrame
    df = pd.concat(dfs, ignore_index=True)
    
    # 对合并后的数据进行全局去重，防止多个CSV文件中存在完全重复的数据行
    initial_rows = len(df)
    df = df.drop_duplicates()
    final_rows = len(df)
    if initial_rows > final_rows:
        print(f"按国家统计：数据合并后已去除 {initial_rows - final_rows} 条完全重复的记录。")
    
    # 对所有列名进行处理，去除首尾可能存在的空格，并去除不可见的零宽字符等特殊字符
    df.columns = df.columns.str.strip().str.replace('\ufeff', '').str.replace('\u200b', '')
    
    # 打印测试信息：展示合并后的数据包含了哪些列，以便排查列名缺失问题
    print(f"数据读取完成，处理后的列名有：{list(df.columns)}")
    
    # 筛选只包含贸易方式编码为 '10'（一般贸易）的数据
    if '贸易方式编码' in df.columns:
        # 清理编码列可能的首尾空格，并过滤等于'10'的行
        df['贸易方式编码'] = df['贸易方式编码'].str.strip()
        df = df[df['贸易方式编码'] == '10']
    else:
        # 如果不存在该列，打印提示并返回
        print("CSV文件中未找到'贸易方式编码'列，无法进行过滤。")
        return
    
    # 定义需要进行数值化计算的列名列表
    numeric_cols = ['第一数量', '第二数量', '人民币']
    
    # 遍历每一个需要转换为数值类型的列名
    for col in numeric_cols:
        # 判断当前列名是否存在于数据表中
        if col in df.columns:
            # 判断当前列的数据类型是否为字符串（object）类型
            if df[col].dtype == object:
                # 将该列转换为字符串类型，替换掉可能遗漏的逗号，最后转换为浮点数类型
                df[col] = df[col].astype(str).str.replace(',', '').astype(float)
            # 如果不是字符串类型
            else:
                # 强制转换为数值类型，遇到错误转为NaN，并将NaN填充为0
                df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0)
    
    # 定义一个内部函数，用于复用按指定维度（如国家、注册地）统计并生成报表的逻辑
    def generate_report(df_data, group_col, group_label, html_file_name, title_prefix):
        # 判断必备的分组字段是否存在于数据表中
        if group_col not in df_data.columns or '数据年月' not in df_data.columns:
            # 如果不存在，打印提示信息
            print(f"CSV文件中未找到所需的列('{group_col}'或'数据年月')，请检查数据格式。")
            # 并提前结束当前方法的执行
            return

        # 按指定维度进行全局分组，对数值列进行求和，并重置索引
        grouped = df_data.groupby([group_col])[numeric_cols].sum().reset_index()
        
        # 对汇总后的数据按人民币金额降序排列
        grouped_sorted = grouped.sort_values(by=['人民币'], ascending=[False])
        
        # 取出金额排名前20的数据进行展示
        top_data = grouped_sorted.head(20)
        
        # 重命名列名，使其符合最终打印的直观结果要求
        result = top_data.rename(columns={
            # 将分组列重命名为指定的标签名（如国家、注册地）
            group_col: group_label,
            # 将第一数量重命名为米
            '第一数量': '米',
            # 将第二数量重命名为千克
            '第二数量': '千克',
            # 将人民币重命名为人民币合计
            '人民币': '人民币合计'
        })
        
        # 计算米价（人民币合计 / 米），如果米数量为0则避免除零错误
        result['米价'] = result.apply(lambda row: row['人民币合计'] / row['米'] if row['米'] != 0 else 0, axis=1)
        
        # 计算千克价（人民币合计 / 千克），如果千克数量为0则避免除零错误
        result['千克价'] = result.apply(lambda row: row['人民币合计'] / row['千克'] if row['千克'] != 0 else 0, axis=1)
        
        # 将米列格式化为带千位分隔符且保留两位小数的字符串
        result['米'] = result['米'].apply(lambda x: f"{x:,.2f}")
        # 将千克列格式化为带千位分隔符且保留两位小数的字符串
        result['千克'] = result['千克'].apply(lambda x: f"{x:,.2f}")
        # 将人民币合计列格式化为带千位分隔符且保留两位小数的字符串
        result['人民币合计'] = result['人民币合计'].apply(lambda x: f"{x:,.2f}")
        
        # 将米价列格式化为带千位分隔符且保留两位小数的字符串
        result['米价'] = result['米价'].apply(lambda x: f"{x:,.2f}")
        # 将千克价列格式化为带千位分隔符且保留两位小数的字符串
        result['千克价'] = result['千克价'].apply(lambda x: f"{x:,.2f}")
        
        # 重置结果数据的索引，丢弃原有的索引值以保证打印美观
        result = result.reset_index(drop=True)
        
        # 调整索引使其从1开始，作为排名的序号
        result.index = range(1, len(result) + 1)
        # 为索引设置一个名称，使其在打印时作为序号列的表头显示
        result.index.name = '序号'
        
        # ==========================
        # 新增：构造可排序的 HTML 表格
        # ==========================
        # 初始化 HTML 表格的字符串结构，并赋予 DataTables 所需的 id 和 class
        table_html = f'<table id="dataTable" class="display" style="width:100%">\n'
        # 添加表格的表头，包含所有的列名
        table_html += f'    <thead><tr><th>序号</th><th>{group_label}</th><th>米</th><th>千克</th><th>人民币合计</th><th>米价</th><th>千克价</th></tr></thead>\n'
        # 添加表格的实体部分标签
        table_html += '    <tbody>\n'
        
        # 遍历排名前20的结果数据框
        for index, row in result.iterrows():
            # 去除米数量中的逗号，保留原始数字字符串以供排序使用
            mi_raw = row['米'].replace(',', '')
            # 去除千克数量中的逗号，保留原始数字字符串以供排序使用
            kg_raw = row['千克'].replace(',', '')
            # 去除人民币合计中的逗号，保留原始数字字符串以供排序使用
            rmb_raw = row['人民币合计'].replace(',', '')
            # 去除米价中的逗号，保留原始数字字符串以供排序使用
            mi_price_raw = row['米价'].replace(',', '')
            # 去除千克价中的逗号，保留原始数字字符串以供排序使用
            kg_price_raw = row['千克价'].replace(',', '')
            
            # 开始拼接当前行的数据
            table_html += '        <tr>\n'
            # 添加序号列
            table_html += f'            <td>{index}</td>\n'
            # 添加分组标签列（国家或注册地）
            table_html += f'            <td>{row[group_label]}</td>\n'
            # 添加米数量列，利用 data-order 属性注入原始数值以支持正确排序
            table_html += f'            <td data-order="{mi_raw}">{row["米"]}</td>\n'
            # 添加千克数量列，利用 data-order 属性注入原始数值以支持正确排序
            table_html += f'            <td data-order="{kg_raw}">{row["千克"]}</td>\n'
            # 添加人民币合计列，利用 data-order 属性注入原始数值以支持正确排序
            table_html += f'            <td data-order="{rmb_raw}">{row["人民币合计"]}</td>\n'
            # 添加米价列，利用 data-order 属性注入原始数值以支持正确排序
            table_html += f'            <td data-order="{mi_price_raw}">{row["米价"]}</td>\n'
            # 添加千克价列，利用 data-order 属性注入原始数值以支持正确排序
            table_html += f'            <td data-order="{kg_price_raw}">{row["千克价"]}</td>\n'
            # 结束当前行的拼接
            table_html += '        </tr>\n'
        # 结束表格的实体和整体标签
        table_html += '    </tbody>\n</table>\n'
        
        # 打印提示信息，说明表格内容已转入 HTML
        print(f"按{group_label}（{title_prefix}）统计的数据表格已转存至生成的 HTML 文件中。")

        # ==========================
        # 新增：附表（按维度和月份透视）
        # ==========================
        # 获取排名前20的名称列表
        top_item_names = top_data[group_col].tolist()
        
        # 从原始数据中筛选出这前20的数据
        df_top20 = df_data[df_data[group_col].isin(top_item_names)]
        
        # 按维度和月份进行分组求和，只统计人民币合计
        monthly_grouped = df_top20.groupby([group_col, '数据年月'])['人民币'].sum().reset_index()
        
        # 将数据透视为以维度为行、月份为列的表格，缺失值填充为0
        pivot_df = monthly_grouped.pivot(index=group_col, columns='数据年月', values='人民币').fillna(0)
        
        # 将列名（月份）转换为字符串并排序，以确保打印顺序正确
        pivot_df.columns = pivot_df.columns.astype(str)
        # 获取排序后的月份列表
        months = sorted(pivot_df.columns.tolist())
        
        # 按照之前计算出的排名前20的顺序重新排列行
        pivot_df = pivot_df.reindex(top_item_names)
        
        # 打印附表的表头和分割线，动态计算总宽度
        # 基础宽度为 排名(6) + 空格(1) + 维度名称(20) = 27
        # 每个月份宽度为 20，加上前面一个空格 = 21
        table_width = 27 + len(months) * 21
        
        # ==========================
        # 新增：构造各月金额透视 HTML 表格
        # ==========================
        # 初始化附表 HTML 字符串结构
        pivot_table_html = f'<table id="pivotTable" class="display" style="width:100%">\n'
        # 添加表头
        pivot_table_html += f'    <thead><tr><th>排名</th><th>{group_label}</th>'
        for m in months:
            pivot_table_html += f'<th>{m}</th>'
        pivot_table_html += '</tr></thead>\n    <tbody>\n'
        
        # 遍历排名前20的维度，逐行构建附表数据
        for i, item_name in enumerate(top_item_names, 1):
            pivot_table_html += '        <tr>\n'
            # 添加排名列
            pivot_table_html += f'            <td>{i}</td>\n'
            # 添加名称列
            pivot_table_html += f'            <td>{item_name}</td>\n'
            
            # 遍历每个月份，格式化输出该月的人民币合计金额
            for m in months:
                val = pivot_df.loc[item_name, m]
                val_str = f"{val:,.2f}"
                val_raw = str(val)
                # 利用 data-order 注入原始数值支持排序
                pivot_table_html += f'            <td data-order="{val_raw}">{val_str}</td>\n'
                
            pivot_table_html += '        </tr>\n'
        # 结束附表 HTML
        pivot_table_html += '    </tbody>\n</table>\n'
        
        # 打印提示信息
        print(f"附表（排名前20{group_label}各月金额）也已转存至生成的 HTML 文件中。")

        # ==========================
        # 新增：生成可交互的HTML折线图
        # ==========================
        # 准备 ECharts 需要的月份数据格式
        months_js = json.dumps(months)
        # 准备 ECharts 需要的图例数据格式
        legend_data = json.dumps(top_item_names)
        # 初始化系列数据列表
        series_data = []
        
        # 遍历排名前20的维度项
        for item_name in top_item_names:
            # 获取当前项各月份的金额数据，转换为列表
            y_values = pivot_df.loc[item_name, months].tolist()
            # 将该项的折线图数据追加到系列列表中
            series_data.append({
                "name": str(item_name),
                "type": "line",
                "data": y_values
            })
        # 准备 ECharts 需要的系列数据格式
        series_js = json.dumps(series_data)
        
        # 构建 HTML 内容，嵌入 ECharts 库和数据，以及 DataTables 表格
        html_content = f"""<!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>排名前20{group_label}统计报告</title>
    <!-- 引入 ECharts CDN -->
    <script src="https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"></script>
    <!-- 引入 jQuery CDN，DataTables 依赖它 -->
    <script src="https://code.jquery.com/jquery-3.7.0.min.js"></script>
    <!-- 引入 DataTables CSS 样式 -->
    <link rel="stylesheet" href="https://cdn.datatables.net/1.13.6/css/jquery.dataTables.min.css">
    <!-- 引入 DataTables JS 脚本 -->
    <script src="https://cdn.datatables.net/1.13.6/js/jquery.dataTables.min.js"></script>
    <!-- 自定义一些基础样式 -->
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        h2 {{ text-align: center; margin-bottom: 20px; }}
        h3 {{ color: #333; margin-bottom: 15px; border-left: 4px solid #4CAF50; padding-left: 10px; }}
        .table-container {{ margin-bottom: 50px; padding: 20px; background-color: #f9f9f9; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); overflow-x: auto; }}
        .chart-container {{ margin-bottom: 50px; padding: 20px; background-color: #fff; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }}
    </style>
</head>
<body>
    <!-- 报表主标题 -->
    <h2>排名前20{group_label}（{title_prefix}）贸易数据综合报表</h2>
    
    <!-- 数据表格容器：总量统计 -->
    <div class="table-container">
        <h3>一、总量统计排名</h3>
        {table_html}
    </div>

    <!-- 数据表格容器：各月明细透视表 -->
    <div class="table-container">
        <h3>二、各月人民币金额合计透视表</h3>
        {pivot_table_html}
    </div>
    
    <!-- 图表容器：为 ECharts 准备一个定义了宽高的 DOM -->
    <div class="chart-container">
        <h3>三、各月人民币金额合计趋势图</h3>
        <div id="main" style="width: 100%; height: 800px;"></div>
    </div>
    
    <script type="text/javascript">
        // 当文档加载完成后初始化 DataTable
        $(document).ready(function() {{
            // 初始化总量统计表
            $('#dataTable').DataTable({{
                "paging": false,       // 禁用分页，直接展示20条
                "searching": false,    // 禁用搜索框
                "info": false,         // 禁用左下角的表格信息
                "order": [[ 4, "desc" ]] // 默认按第5列（索引4，人民币合计）进行降序排序
            }});
            
            // 初始化各月透视表
            $('#pivotTable').DataTable({{
                "paging": false,       // 禁用分页
                "searching": false,    // 禁用搜索框
                "info": false,         // 禁用信息展示
                "order": [[ 0, "asc" ]] // 默认按第1列（索引0，排名）进行升序排序
            }});
        }});

        // 基于准备好的dom，初始化echarts实例
        var myChart = echarts.init(document.getElementById('main'));

        // 指定图表的配置项和数据
        var option = {{
            title: {{
                text: '排名前20{group_label}各月人民币金额合计趋势图'
            }},
            tooltip: {{
                trigger: 'axis'
            }},
            legend: {{
                data: {legend_data},
                type: 'scroll', // 当图例过多时允许滚动
                orient: 'vertical',
                right: 10,
                top: 20,
                bottom: 20
            }},
            grid: {{
                left: '3%',
                right: '15%', // 留出右侧空间给图例
                bottom: '3%',
                containLabel: true
            }},
            toolbox: {{
                feature: {{
                    saveAsImage: {{}}
                }}
            }},
            xAxis: {{
                type: 'category',
                boundaryGap: false,
                data: {months_js}
            }},
            yAxis: {{
                type: 'value',
                name: '人民币合计（元）'
            }},
            series: {series_js}
        }};

        // 使用刚指定的配置项和数据显示图表。
        myChart.setOption(option);
    </script>
</body>
</html>"""

        # 构造并定义HTML文件保存至对应 stats/目标目录名 下的绝对路径
        html_path = os.path.join(base_dir, 'stats', target_dir_name, html_file_name)
        
        # 将生成的 HTML 字符串写入文件
        with open(html_path, 'w', encoding='utf-8') as f:
            # 写入内容
            f.write(html_content)
            
        # 打印成功生成文件的提示
        print(f"\n已生成交互式折线图(HTML)并保存至: {html_path}")

    # 调用内部函数，按国家（贸易伙伴名称）进行分析并生成报告
    generate_report(df, '贸易伙伴名称', '国家', f'出口大国.html', '贸易伙伴')
    
    # 打印空行和分割线以分隔输出
    print("\n" + "=" * 130 + "\n")
    print("开始按注册地名称统计贸易数据...\n")
    
    # 调用内部函数，按注册地名称进行分析并生成报告
    generate_report(df, '注册地名称', '注册地', f'供应大省.html', '注册地名称')
    
    # 打印空行和分割线以分隔输出
    print("\n" + "=" * 130 + "\n")
    print("开始按商品名称统计贸易数据...\n")
    
    # 调用内部函数，按商品名称进行分析并生成报告
    generate_report(df, '商品名称', '商品', f'产品分类.html', '商品名称')

# 定义一个比较两个CSV文件中特定月份数据是否一致的方法
def compare_monthly_data(csv1_relative_path, csv2_relative_path, target_month):
    # 获取当前py文件所在的绝对路径目录
    base_dir = os.path.dirname(os.path.abspath(__file__))
    
    # 拼接出两个CSV文件的绝对路径
    csv1_path = os.path.join(base_dir, csv1_relative_path)
    csv2_path = os.path.join(base_dir, csv2_relative_path)
    
    # 定义一个内部辅助函数，用于读取并清洗数据
    def read_and_clean(file_path):
        try:
            # 读取CSV文件，使用gb18030编码，并将千位分隔符解析为普通数字，同时指定贸易方式编码为字符串
            df = pd.read_csv(file_path, encoding='gb18030', thousands=',', dtype={'贸易方式编码': str})
        except Exception as e:
            # 如果出错，打印错误并返回None
            print(f"读取文件 {file_path} 出错: {e}")
            return None
            
        # 去除所有列名的首尾空格
        df.columns = df.columns.str.strip()
        
        # 检查是否存在'数据年月'列
        if '数据年月' not in df.columns:
            print(f"文件 {file_path} 中未找到'数据年月'列。")
            return None
            
        # 将数据年月列转换为字符串格式，并去除首尾空格
        df['数据年月'] = df['数据年月'].astype(str).str.strip()
        
        # 筛选出目标月份的数据
        df_month = df[df['数据年月'] == str(target_month)]
        
        # 对筛选出的数据进行全局去重
        df_month = df_month.drop_duplicates()
        
        # 按照所有列的值进行排序，重置索引，以便后续能够准确进行数据框比较
        # 由于列中可能存在NaN，排序前将NaN暂时填充，排序后恢复（或者直接通过重置索引后的比较）
        # 为了稳定比较，我们先按所有列排序，并丢弃原来的索引
        df_month = df_month.sort_values(by=list(df_month.columns)).reset_index(drop=True)
        
        return df_month

    print(f"\n开始比较文件 '{csv1_relative_path}' 和 '{csv2_relative_path}' 中 {target_month} 月份的数据...")
    
    # 读取并处理第一个文件
    df1 = read_and_clean(csv1_path)
    # 读取并处理第二个文件
    df2 = read_and_clean(csv2_path)
    
    # 如果有任何一个文件读取失败，则终止比较
    if df1 is None or df2 is None:
        print("由于文件读取失败，比较已终止。")
        return
        
    # 获取两个文件在目标月份的数据行数
    len1 = len(df1)
    len2 = len(df2)
    
    # 无论行数是否一致，我们都通过 outer merge 找出两个数据框的交集和差异集
    # 使用 merge 时带上 indicator=True，这会生成一列 '_merge'
    # '_merge' 的值为 'both' 表示两边都有（一致的记录），'left_only' 表示仅存在于文件1，'right_only' 表示仅存在于文件2
    merged = df1.merge(df2, indicator=True, how='outer')
    
    # 统计完全一致的记录数量
    consistent_count = len(merged[merged['_merge'] == 'both'])
    
    # 统计仅在文件1中存在的记录数量
    only_in_df1 = len(merged[merged['_merge'] == 'left_only'])
    
    # 统计仅在文件2中存在的记录数量
    only_in_df2 = len(merged[merged['_merge'] == 'right_only'])
    
    # 计算总的不一致记录条数（即只在其中一方存在的记录总和）
    inconsistent_count = only_in_df1 + only_in_df2
    
    print(f"对比完成！文件一（{len1}条）和文件二（{len2}条）在 {target_month} 月份的数据情况如下：")
    print(f" - 完全一致的记录: {consistent_count} 条")
    print(f" - 不一致的记录: {inconsistent_count} 条 (其中 {only_in_df1} 条仅存在于文件一，{only_in_df2} 条仅存在于文件二)")

# 判断当前文件是否作为主程序入口直接运行
if __name__ == "__main__":
    # 定义需要统计的目标目录名称，脚本将读取 stats/该目录名 下的所有 CSV 文件
    target_dir = "5407"  # 请确保存在 stats/data_collection 目录，或者修改为您实际的目录名

    # 调用按国家统计分析方法并传入目录名
    analyze(target_dir)
    
    # 打印两行空行分隔不同结果
    print("\n\n")
    # 调用比较方法，比较两个CSV文件中特定月份（如202501）的数据是否一致
    #compare_monthly_data("data202506.csv", "data20250106.csv", "202506")
