import click
from PIL import Image, ImageDraw, ImageFont
import datetime
import os
import json

def get_font(size):
    windir = os.environ.get('WINDIR', r'C:\Windows')
    fonts = [
        os.path.join(windir, "Fonts", "msyh.ttc"),    # 微软雅黑 (Win10+)
        os.path.join(windir, "Fonts", "msyh.ttf"),    # 微软雅黑 (旧版)
        os.path.join(windir, "Fonts", "simhei.ttf"),  # 黑体
        os.path.join(windir, "Fonts", "simsun.ttc"),  # 宋体
        "/System/Library/Fonts/PingFang.ttc",         # Mac
        "/usr/share/fonts/truetype/wqy/wqy-microhei.ttc" # Linux
    ]
    for font in fonts:
        if os.path.exists(font):
            return ImageFont.truetype(font, size)
    
    click.echo("警告：未找到合适的中文字体，中文可能会显示为方块。请安装微软雅黑或黑体字体。", err=True)
    return ImageFont.load_default()

def num2rmb(n):
    units = ["", "拾", "佰", "仟", "万", "拾", "佰", "仟", "亿"]
    nums = ["零", "壹", "贰", "叁", "肆", "伍", "陆", "柒", "捌", "玖"]
    
    s = str(round(n, 2)).split('.')
    int_part = s[0]
    dec_part = s[1] if len(s) > 1 else ""
    
    res = ""
    for i, c in enumerate(int_part[::-1]):
        if i >= len(units): break
        res = nums[int(c)] + units[i] + res
        
    res = res.replace("零仟", "零").replace("零佰", "零").replace("零拾", "零")
    while "零零" in res:
        res = res.replace("零零", "零")
    res = res.replace("零万", "万").replace("零亿", "亿").replace("亿万", "亿")
    if res.endswith("零"):
        res = res[:-1]
    if res == "":
        res = "零"
    res += "元"
    
    if not dec_part or dec_part == "0" or dec_part == "00":
        res += "整"
    else:
        if len(dec_part) > 0:
            res += nums[int(dec_part[0])] + "角"
        if len(dec_part) > 1:
            res += nums[int(dec_part[1])] + "分"
    
    if res.startswith("元"):
        res = res[1:]
    return res

@click.command()
@click.option('--items', '-i', required=True, help='商品数组字符串，例如: {802-#3-m[5,6,7]-10.00}')
@click.option('--output', '-o', default=None, help='指定输出的图片路径。默认会保存在脚本同级目录的image文件夹下。')
def generate_receipt(items, output):
    """生成明细码单凭证图片"""
    # 解析商品数组
    import re
    items_data = []
    blocks = re.findall(r'\{([^}]+)\}', items)
    if not blocks:
        click.echo("❌ 格式错误，请检查入参是否是合法的字符串，例如: {802-#3-m[5,6,7]-10.00}", err=True)
        raise click.Abort()
        
    for block in blocks:
        try:
            parts = block.split('-m[')
            if len(parts) != 2:
                raise ValueError("缺少 '-m['")
            right_parts = parts[1].split(']-')
            if len(right_parts) != 2:
                raise ValueError("缺少 ']-'")
                
            meters_str = right_parts[0]
            unit_price_str = right_parts[1]
            
            left_parts = parts[0].rsplit('-', 1)
            if len(left_parts) != 2:
                raise ValueError("型号和颜色之间缺少 '-'")
                
            model = left_parts[0].strip()
            color = left_parts[1].strip()
            
            meters = [float(x.strip()) if '.' in x else int(x.strip()) for x in meters_str.split(',') if x.strip()]
            unit_price = float(unit_price_str.strip())
            
            items_data.append({
                "model": model,
                "color": color,
                "meters": meters,
                "unit_price": unit_price
            })
        except Exception as e:
            click.echo(f"❌ 解析商品 '{{{block}}}' 失败: {e}", err=True)
            raise click.Abort()
        
    # 图片基础设置
    width, height = 840, 600
    img = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(img)
    
    # 字体设置
    font_title = get_font(30)
    font_company = get_font(24)
    font_normal = get_font(14)
    font_small = get_font(12)
    font_tiny = get_font(10)
    
    # --- 绘制头部信息 ---
    # 标题
    title = "明细码单凭证"
    try:
        bbox = draw.textbbox((0, 0), title, font=font_title)
        title_w = bbox[2] - bbox[0]
    except AttributeError:
        title_w = font_title.getlength(title)
    draw.text(((width - title_w) / 2, 20), title, font=font_title, fill='black')
    
    # 标题下横线
    draw.line((20, 70, 820, 70), fill='black', width=2)
    
    # 公司名及地址
    draw.text((20, 80), "千亿纺织", font=font_company, fill='black')
    draw.text((160, 95), "地址:广州市海珠区逸景路新长江(中国)轻纺城北区二楼R103档", font=font_tiny, fill='black')
    
    # 日期
    today = datetime.datetime.now().strftime("%Y/%m/%d")
    draw.text((600, 90), today, font=font_normal, fill='black')
    
    # 客户与单号
    draw.text((20, 120), "客户:", font=font_normal, fill='black')
    order_no = "单号: BD-" + datetime.datetime.now().strftime("%Y%m%d%H%M")
    draw.text((600, 120), order_no, font=font_normal, fill='black')
    
    # --- 绘制表格 ---
    x_start = 20
    y_start = 150
    x_end = 820
    row_height = 30
    
    # 列坐标：重构各列宽度以防止重叠
    cols = [x_start]
    # 列宽依次为: 货名(140), 单位(40), 颜色(60), 1-10(各32, 共320), 数量(60), 单价(80), 金额(100) -> 总和 800
    widths = [140, 40, 60] + [32] * 10 + [60, 80, 100]
    for w in widths:
        cols.append(cols[-1] + w)
    
    def draw_cell_text(text, x_left, x_right, y_top, font):
        text_str = str(text)
        try:
            bbox = draw.textbbox((0,0), text_str, font=font)
            w = bbox[2] - bbox[0]
            h = bbox[3] - bbox[1]
        except AttributeError:
            w = font.getlength(text_str)
            h = 14 # 估算高度
        x = x_left + (x_right - x_left - w) / 2
        y = y_top + (row_height - h) / 2 - 2
        draw.text((x, y), text_str, font=font, fill='black')

    y_current = y_start
    
    # 表头
    headers = ["货名", "单位", "颜色", "1", "2", "3", "4", "5", "6", "7", "8", "9", "10", "数量", "单价", "金额"]
    draw.line((x_start, y_current, x_end, y_current), fill='black', width=1)
    for i in range(len(headers)):
        draw_cell_text(headers[i], cols[i], cols[i+1], y_current, font_normal)
    y_current += row_height
    
    # 数据行
    num_data_rows = 7
    total_all_quantity = 0
    total_all_amount = 0

    for row in range(num_data_rows):
        draw.line((x_start, y_current, x_end, y_current), fill='black', width=1)
        if row < len(items_data):
            item = items_data[row]
            model = str(item.get("model", ""))
            color = str(item.get("color", ""))
            meters = item.get("meters", [])
            unit_price = float(item.get("unit_price", 10.00))

            # 支持字符串输入或数组输入的米数
            if isinstance(meters, str):
                meter_list = [float(x.strip()) for x in meters.replace('，', ',').split(',') if x.strip()]
            else:
                meter_list = [float(x) for x in meters]
                
            total_quantity = sum(meter_list)
            total_amount = total_quantity * unit_price
            
            total_all_quantity += total_quantity
            total_all_amount += total_amount

            draw_cell_text(model, cols[0], cols[1], y_current, font_normal)
            draw_cell_text("米", cols[1], cols[2], y_current, font_normal)
            draw_cell_text(color, cols[2], cols[3], y_current, font_normal)
            
            for i, meter in enumerate(meter_list[:10]):
                m_str = str(int(meter)) if float(meter).is_integer() else str(meter)
                draw_cell_text(m_str, cols[3+i], cols[4+i], y_current, font_normal)
                
            qty_str = str(int(total_quantity)) if float(total_quantity).is_integer() else str(total_quantity)
            draw_cell_text(qty_str, cols[13], cols[14], y_current, font_normal)
            draw_cell_text(f"￥{unit_price:.2f}", cols[14], cols[15], y_current, font_normal)
            draw_cell_text(f"￥{total_amount:.2f}", cols[15], cols[16], y_current, font_normal)
        
        y_current += row_height
        
    # 合计行
    draw.line((x_start, y_current, x_end, y_current), fill='black', width=1)
    draw_cell_text("合计", cols[14], cols[15], y_current, font_normal)
    draw_cell_text(f"￥{total_all_amount:.2f}", cols[15], cols[16], y_current, font_normal)
    y_current += row_height
    draw.line((x_start, y_current, x_end, y_current), fill='black', width=1)
    
    # 绘制表格竖线
    for col_x in cols:
        draw.line((col_x, y_start, col_x, y_current), fill='black', width=1)
        
    # --- 绘制底部信息 ---
    # 总数量、优惠、应收、已收行
    seg_w = (x_end - x_start) / 4
    qty_str = str(int(total_all_quantity)) if float(total_all_quantity).is_integer() else str(total_all_quantity)
    draw.text((x_start + 5, y_current + 6), f"总数量: {qty_str}", font=font_normal, fill='black')
    draw.text((x_start + seg_w + 5, y_current + 6), "优惠:", font=font_normal, fill='black')
    draw.text((x_start + 2*seg_w + 5, y_current + 6), f"本单应收: ￥{total_all_amount:.2f}", font=font_normal, fill='black')
    draw.text((x_start + 3*seg_w + 5, y_current + 6), "本单已收:", font=font_normal, fill='black')
    y_current += row_height
    draw.line((x_start, y_current, x_end, y_current), fill='black', width=1)
    
    # 收款大写行
    draw.text((x_start + 5, y_current + 6), f"收款大写: {num2rmb(total_all_amount)}", font=font_normal, fill='black')
    y_current += row_height
    draw.line((x_start, y_current, x_end, y_current), fill='black', width=1)
    
    # 备注行
    draw.text((x_start + 5, y_current + 6), "备注:", font=font_normal, fill='black')
    y_current += row_height
    draw.line((x_start, y_current, x_end, y_current), fill='black', width=1)
    
    # 底部信息的左右边框
    draw.line((x_start, y_current - 3 * row_height, x_start, y_current), fill='black', width=1)
    draw.line((x_end, y_current - 3 * row_height, x_end, y_current), fill='black', width=1)
    
    # 底部声明与签名
    y_current += 10
    draw.text((x_start, y_current), "特别申明: 收货方如发现质量问题请于七天内书面向供方提出，否则供货方一律不承担责任。", font=font_small, fill='black')
    
    y_current += 40
    draw.text((x_start, y_current), "制单人:", font=font_normal, fill='black')
    draw.text((x_end - 200, y_current), "签单人:", font=font_normal, fill='black')
    
    # 保存图片
    if output:
        output_filename = os.path.abspath(output)
        os.makedirs(os.path.dirname(output_filename), exist_ok=True)
    else:
        current_dir = os.path.dirname(os.path.abspath(__file__))
        image_dir = os.path.join(current_dir, "image")
        os.makedirs(image_dir, exist_ok=True)
        output_filename = os.path.join(image_dir, f"receipt_{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.png")
        
    img.save(output_filename)
    
    # 按照标准 CLI 工具输出：使用 JSON 格式，方便调用方解析
    result = {
        "status": "success",
        "message": "生成成功",
        "file_path": output_filename
    }
    click.echo(json.dumps(result, ensure_ascii=False))

if __name__ == "__main__":
    generate_receipt()

