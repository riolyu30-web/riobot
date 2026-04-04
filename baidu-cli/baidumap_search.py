# 导入 requests 库，用于发起 HTTP 请求
import requests
# 导入 os 库，用于读取环境变量
import os
# 导入 dotenv 库，用于加载 .env 文件中的环境变量
import dotenv
# 导入 click 库，用于创建命令行界面工具
import click

# 调用 load_dotenv 函数，加载项目目录下的 .env 文件
dotenv.load_dotenv()
# 从环境变量中获取百度地图的 AK（API Key）
ak = os.getenv("BAIDU_MAP_API_KEY")

# 定义一个获取地址详情的函数，接收各个 API 参数
def get_address_by_location(
    lat, lng, ak, 
    poi_types="", 
    extensions_poi="0", 
    radius=1000, 
    extensions_road="false", 
    region_data_source=2, 
    entire_poi=0, 
    sort_strategy="distance", 
    coordtype="wgs84ll", 
    ret_coordtype="wgs84ll", 
    sn="", 
    output="json", 
    callback="", 
    language="zh-CN", 
    language_auto=0
):
    # 定义百度地图逆地理编码的 API 接口地址
    url = "https://api.map.baidu.com/reverse_geocoding/v3/"
    
    # 构造请求参数字典，使用传入的参数
    params = {
        # 传入百度地图的 AK
        "ak": ak,
        # 将纬度和经度拼接成 location 参数
        "location": f"{lat},{lng}",
        # 是否返回 POI 数据
        "extensions_poi": extensions_poi,
        # POI 召回半径
        "radius": radius,
        # 是否召回最近的道路数据
        "extensions_road": extensions_road,
        # 行政区划数据的来源
        "region_data_source": region_data_source,
        # 是否召回更多 POI
        "entire_poi": entire_poi,
        # POI 结果排序策略
        "sort_strategy": sort_strategy,
        # 传入的坐标系类型
        "coordtype": coordtype,
        # 返回的坐标系类型
        "ret_coordtype": ret_coordtype,
        # 输出格式（json 或 xml）
        "output": output,
        # 返回参数的语言类型
        "language": language,
        # 是否自动填充行政区划语言
        "language_auto": language_auto
    }
    
    # 如果用户指定了 poi_types，则添加到参数字典中
    if poi_types:
        # 将 poi_types 添加到 params
        params["poi_types"] = poi_types
        
    # 如果用户提供了 sn 校验码，则添加到参数字典中
    if sn:
        # 将 sn 添加到 params
        params["sn"] = sn
        
    # 如果用户提供了 callback 函数名，则添加到参数字典中
    if callback:
        # 将 callback 添加到 params
        params["callback"] = callback
    
    # 开始 try 块，捕获可能的网络异常
    try:
        # 使用 requests.get 发起 HTTP GET 请求
        response = requests.get(url, params=params)
        # 检查响应状态码，如果不为 200 则抛出异常
        response.raise_for_status()
        
        # 判断请求的输出格式是否为 json
        if output == "json":
            # 将响应结果解析为 JSON 格式的字典
            data = response.json()
            
            # 判断返回结果中的状态码 status 是否为 0（代表成功）
            if data.get("status") == 0:
                # 提取返回数据中的 result 字段内容
                result = data["result"]
                
                # 获取完整的格式化地址信息
                formatted_address = result.get("formatted_address")
                
                # 获取地址的组成部分（省市区等细节）
                address_component = result.get("addressComponent", {})
                # 提取省份信息
                province = address_component.get("province")
                # 提取城市信息
                city = address_component.get("city")
                # 提取区县信息
                district = address_component.get("district")
                
                # 获取语义化的位置描述（如在某大厦附近）
                sematic_description = result.get("sematic_description", "")
                
                # 向终端输出解析成功的提示
                click.echo(f"解析成功！")
                # 向终端输出完整的格式化地址
                click.echo(f"完整地址: {formatted_address}")
                # 向终端输出省、市、区的拼接字符串
                click.echo(f"省市区: {province} - {city} - {district}")
                # 判断是否存在语义化位置描述
                if sematic_description:
                    # 如果存在，则向终端输出位置描述
                    click.echo(f"位置描述: {sematic_description}")
                
                # 判断用户是否在请求中要求展示 POI（兴趣点）信息
                if str(extensions_poi) == "1":
                    # 从结果中获取 POI 列表，如果没有则返回空列表
                    pois = result.get("pois", [])
                    # 向终端输出 POI 列表的标题
                    click.echo("\n--- 周边兴趣点 (POI) ---")
                    # 遍历获取到的每一个 POI 信息
                    for poi in pois:
                        # 提取 POI 的名称
                        name = poi.get("name")
                        # 提取 POI 的地址
                        addr = poi.get("addr")
                        # 获取当前 POI 的标签分类
                        tag = poi.get("tag", "")
                        # 向终端输出该 POI 的名称、地址和标签
                        click.echo(f"名称: {name} | 地址: {addr} | 标签: {tag}")
                
                # 如果开启了召回最近道路数据，检查是否有 roads 字段
                if str(extensions_road) == "true" and "roads" in result:
                    # 向终端输出道路列表的标题
                    click.echo("\n--- 周边道路 ---")
                    # 遍历返回的道路数据
                    for road in result["roads"]:
                        # 提取道路名称
                        road_name = road.get("name")
                        # 提取道路距离
                        road_distance = road.get("distance")
                        # 向终端输出道路信息
                        click.echo(f"道路名称: {road_name} | 距离: {road_distance}米")
                
                # 返回完整的 result 字典供其他逻辑使用
                return result
            # 如果返回的 status 不为 0，说明接口报错
            else:
                # 向终端输出接口报错的状态码和信息
                click.echo(f"接口报错啦！错误码: {data.get('status')}, 信息: {data.get('message')}")
                # 返回 None 代表解析失败
                return None
        # 如果输出格式不是 json（例如 xml 或使用了 callback）
        else:
            # 直接向终端输出原始的文本响应
            click.echo("返回原始数据:")
            # 输出响应内容
            click.echo(response.text)
            # 返回响应文本
            return response.text
            
    # 捕获 requests 库抛出的请求异常
    except requests.exceptions.RequestException as e:
        # 向终端输出网络请求失败的具体异常信息
        click.echo(f"网络请求失败: {e}")
        # 返回 None 代表请求失败
        return None

# 注册一个 click 命令行命令
@click.command()
# 定义命令行选项 --lat，用于接收纬度，必须提供
@click.option('--lat', required=True, type=float, help="纬度 (如 39.951335)")
# 定义命令行选项 --lng，用于接收经度，必须提供
@click.option('--lng', required=True, type=float, help="经度 (如 116.514844)")
# 定义命令行选项 --poi-types，控制返回附近 POI 类型
@click.option('--poi-types', default="", help="控制返回附近POI类型，例如 '酒店|房地产'")
# 定义命令行选项 --extensions-poi，控制是否返回 POI 数据
@click.option('--extensions-poi', default="1", help="1返回pois数据和语义化数据，0不返回")
# 定义命令行选项 --radius，设置 POI 召回半径
@click.option('--radius', default=1000, type=int, help="POI召回半径，区间0-3000米")
# 定义命令行选项 --extensions-road，控制是否召回最近道路
@click.option('--extensions-road', default="false", help="当取值为true时，召回坐标周围最近的3条道路数据")
# 定义命令行选项 --region-data-source，设置行政区划数据来源
@click.option('--region-data-source', default=2, type=int, help="行政区划数据的来源: 1-统计局 2-民政部")
# 定义命令行选项 --entire-poi，控制是否召回更多 POI
@click.option('--entire-poi', default=0, type=int, help="设置该参数为1可召回更多POI，优化地址结果")
# 定义命令行选项 --sort-strategy，设置 POI 结果排序策略
@click.option('--sort-strategy', default="distance", help="POI结果排序策略: distance、rank、default")
# 定义命令行选项 --coordtype，指定传入坐标系类型
@click.option('--coordtype', default="wgs84ll", help="传入的坐标类型: bd09ll、gcj02ll 等")
# 定义命令行选项 --ret-coordtype，指定返回坐标系类型
@click.option('--ret-coordtype', default="wgs84ll", help="返回的坐标类型: bd09ll、gcj02ll 等")
# 定义命令行选项 --sn，用于 SN 校验
@click.option('--sn', default="", help="若用户所用ak的校验方式为sn校验时该参数必须")
# 定义命令行选项 --output，设置输出格式
@click.option('--output', default="json", help="输出格式为 json 或者 xml")
# 定义命令行选项 --callback，设置 JSONP 回调函数名
@click.option('--callback', default="", help="将json格式的返回值通过callback函数返回以实现jsonp功能")
# 定义命令行选项 --language，指定返回语言
@click.option('--language', default="zh-CN", help="指定返回参数的语言类型，如 zh-CN, en")
# 定义命令行选项 --language-auto，控制是否自动填充行政区划语言
@click.option('--language-auto', default=0, type=int, help="当用户指定language参数时，是否自动填充行政区划: 1填充，0不填充")
# 定义命令行的主入口函数，接收所有 click 解析后的参数
def cli(lat, lng, poi_types, extensions_poi, radius, extensions_road, region_data_source, entire_poi, sort_strategy, coordtype, ret_coordtype, sn, output, callback, language, language_auto):
    # 检查全局变量 AK 是否已正确加载
    if not ak:
        # 如果 AK 为空，向终端输出提示让用户配置环境变量
        click.echo("错误：未找到 BAIDU_AMP_API_KEY 环境变量，请在 .env 文件中配置！")
        # 直接返回，不再执行后续逻辑
        return
    
    # 向终端输出正在查询的经纬度信息
    click.echo(f"正在查询坐标: 纬度 {lat}, 经度 {lng} (坐标系: {coordtype})")
    
    # 调用封装好的逆地理编码函数进行查询，并传入所有参数
    get_address_by_location(
        lat=lat,
        lng=lng,
        ak=ak,
        poi_types=poi_types,
        extensions_poi=extensions_poi,
        radius=radius,
        extensions_road=extensions_road,
        region_data_source=region_data_source,
        entire_poi=entire_poi,
        sort_strategy=sort_strategy,
        coordtype=coordtype,
        ret_coordtype=ret_coordtype,
        sn=sn,
        output=output,
        callback=callback,
        language=language,
        language_auto=language_auto
    )

# 判断当前文件是否作为主程序直接运行
if __name__ == "__main__":
    # 调用 cli 函数，触发 click 的命令行解析并执行
    cli()