from dotenv import load_dotenv
from scrapegraphai.graphs import SmartScraperGraph # 假设你使用 SmartScraperGraph

load_dotenv() # 确保在创建图之前加载环境变量

graph_config = {
    "llm": {
        "model": "dashscope/qwen3.6-plus",  # 指定 DashScope 模型
        "api_key": "sk-50141226087d472b8c6d13739154ada2", # 不推荐直接在这里硬编码
    },
    "verbose": True,
    "headless": False,
    # ... 其他配置
}

# 假设你有一个 SmartScraperGraph 实例
smart_scraper_graph = SmartScraperGraph(
    prompt="找到输入框的元素，想想阿斯莫去LLEFD【、。x、",
    source="https://www.baidu.com",
    config=graph_config,
)

result = smart_scraper_graph.run()
print(result)