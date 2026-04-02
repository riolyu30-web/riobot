import os
import shutil
from pathlib import Path
from openviking import OpenViking

def test_openviking_final():
    """
    OpenViking 最终修正版测试脚本：
    1. 通过 ov.config.json 配置文件管理大模型。
    2. 修正 add_resource 的用法，通过临时文件写入文本。
    3. 增加更明确的 API Key 错误引导。
    """
    print("=== OpenViking 最终修正版测试脚本 ===")

    # 1. 设置与检查配置文件
    config_path = Path(__file__).parent.parent / ".nanobot" / "ov.config.json"
    if not config_path.exists():
        print(f"❌ 错误：配置文件不存在！")
        print(f"请在以下路径创建 ov.config.json 文件：\n{config_path}")
        return
    os.environ['OPENVIKING_CONFIG_FILE'] = str(config_path)
    print(f"✅ 已指定配置文件: {config_path}")

    # 2. 准备测试环境
    test_db_path = Path(__file__).parent.parent / ".nanobot" / "viking_test_db"
    if test_db_path.exists():
        shutil.rmtree(test_db_path)
        print(f"🧹 已清理旧的测试数据库: {test_db_path}")

    # 3. 初始化客户端
    client = OpenViking(path=str(test_db_path))
    try:
        client.initialize()
        print("✅ OpenViking 初始化成功！")
    except Exception as e:
        print(f"❌ OpenViking 初始化失败: {e}")
        if "401" in str(e) and "Incorrect API key" in str(e):
            print("👉 检测到 API Key 错误！请打开下面的文件，将 'your-openai-api-key' 替换为你的真实 OpenAI API Key:")
            print(f"  {config_path}")
        else:
            print("👉 请检查网络连接或配置文件格式。")
        return

    knowledge_uri = ""
    temp_file_path = Path(__file__).parent / "temp_knowledge.txt"

    try:
        # ==========================================
        # 4. 写入知识 (通过临时文件)
        # ==========================================
        print("\n--- 步骤 4: 写入知识 ---")
        knowledge_text = (
            "Nanobot 架构设计深度解析\n\n"
            "核心理念：Nanobot 的设计哲学是“小而美”，它并非一个大而全的框架，"
            "而是一个高度可扩展的微型 Agent 内核。\n\n"
            "与 OpenViking 的结合点：\n"
            "OpenViking 可以作为 Nanobot 的一个超级“外部大脑”。"
            "通过 client.add_resource() 将文档存入 OpenViking，"
            "然后通过 client.find() 进行语义搜索，"
            "可以赋予 Nanobot 无限的、且与上下文高度相关的记忆能力。"
        )
        
        # 最佳实践：将文本内容写入临时文件，再将文件路径传给 add_resource
        temp_file_path.write_text(knowledge_text, encoding='utf-8')
        print(f"📝 已创建临时知识文件: {temp_file_path}")

        result = client.add_resource(
            path=str(temp_file_path),
            name="Nanobot 架构设计" # 指定在 OpenViking 中显示的名称
        )
        knowledge_uri = result['root_uri']
        print(f"✅ 知识已提交，URI: {knowledge_uri}")

        print("⏳ 正在等待 OpenViking 后台处理（生成向量和摘要）...")
        client.wait_processed()
        print("✅ 后台处理完成！")

        # ==========================================
        # 5. 按需读取知识
        # ==========================================
        print("\n--- 步骤 5: 按需读取分层知识 ---")
        l0_summary = client.abstract(knowledge_uri)
        print(f"【L0 摘要】: {l0_summary}")

        l1_overview = client.overview(knowledge_uri)
        print(f"【L1 概述】: \n{l1_overview}")

        l2_content = client.read(knowledge_uri)
        print(f"【L2 全文】: \n{l2_content[:200]}...")

        # ==========================================
        # 6. 语义搜索
        # ==========================================
        print("\n--- 步骤 6: 语义搜索 ---")
        query = "Nanobot是什么？"
        print(f"🔍 用户提问: '{query}'")
        
        search_results = client.find(query, limit=3)
        if search_results and search_results.resources:
            for res in search_results.resources:
                print(f"  🎯 命中: {res}")
                print(f"     匹配内容: {getattr(res, 'content', getattr(res, 'text', str(res)))}")  
        else:
            print("  - 未找到相关结果。")

    except Exception as e:
        print(f"\n❌ 在与 OpenViking 交互时发生错误: {e}")
        if "401" in str(e) and "Incorrect API key" in str(e):
            print("👉 检测到 API Key 错误！请打开下面的文件，将 'your-openai-api-key' 替换为你的真实 OpenAI API Key:")
            print(f"  {config_path}")
        import traceback
        traceback.print_exc()





    finally:
        # ==========================================
        # 7. 清理
        # ==========================================
        print("\n--- 步骤 7: 清理测试环境 ---")
        client.close()
        if test_db_path.exists():
            shutil.rmtree(test_db_path)
        if temp_file_path.exists():
            os.remove(temp_file_path)
            print(f"🗑️ 已删除临时文件: {temp_file_path}")
        print("✅ 测试完成并清理完毕！")

if __name__ == "__main__":
    test_openviking_final()