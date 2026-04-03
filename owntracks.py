from fastapi import FastAPI, Request
import json
from datetime import datetime
import os

app = FastAPI()

# 存储位置数据的文件
DATA_FILE = ".nanobot/location.json"

@app.post("/owntracks")
async def receive_location(request: Request):
    """接收 OwnTracks 发来的位置数据"""
    try:
        # OwnTracks 会发送 JSON 格式的数据
        data = await request.json()
        
            
        # 把最新的位置覆盖写入文件（你也可以改成追加写入记录轨迹）
        with open(DATA_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
                
        #print(f"[{time_str}] 收到新位置: 经度 {lon}, 纬度 {lat}, 电量 {batt}%")
            
        # OwnTracks 要求服务端返回空的 JSON 数组表示接收成功
        return []
    except Exception as e:
        print(f"处理错误: {e}")
        return []

@app.get("/api/current_location")
async def get_current_location():
    """电脑端用来获取最新位置的接口"""
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"error": "暂无位置数据"}

if __name__ == "__main__":
    import uvicorn
    # 运行在 8000 端口，0.0.0.0 允许外部访问
    uvicorn.run(app, host="0.0.0.0", port=8200)