"""Shell execution tool."""

import os
from pathlib import Path
from nanobot.session.manager import Session, SessionManager
from typing import Any
from nanobot.utils.helpers import ensure_dir
from nanobot.agent.tools.base import Tool
import json


class LocationTool(Tool):

    def __init__(
        self,
        workspace: Path | None = None,
    ):
        self.workspace = workspace 

    @property
    def name(self) -> str:
        return "location"

    @property
    def description(self) -> str:
        return "get current location and user status"
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
            "required": []
        }
    
    async def execute(self, **kwargs: Any) -> str:
        # 读取并解析 OwnTracks 位置信息
        location_file = self.workspace.parent / "location.json"
        lines = []
        if location_file.exists():
            try:
                data = json.loads(location_file.read_text(encoding="utf-8"))
                lines.append(f"[User Current Status]") 
                lines.append(f"- 坐标体系: wgs84ll")
                lines.append(f"- 所在纬度 (Latitude): {data.get('lat', '未知')}")
                lines.append(f"- 所在经度 (Longitude): {data.get('lon', '未知')}") 
                lines.append(f"- 所在海拔 (altitude): {data.get('alt', '未知')}")
                lines.append(f"- 定位精度: {data.get('acc', '未知')}")
                lines.append(f"- 垂直精度: {data.get('vac', '未知')}")
                lines.append(f"- 移动速度: {data.get('vel', '未知')}")
                lines.append(f"- 气压 {data.get('p', '未知')}")                             
                lines.append(f"- 手机电量百分比: {data.get('batt', '未知')}")   
                bs_map = {0: "未知", 1: "未充电", 2: "正在充电", 3: "已充满"}
                bs_val = data.get('bs', 0)
                lines.append(f"- 电池充电状态: ({bs_map.get(bs_val, '未知')})")
                motion_map = {"stationary": "静止/放置", "walking": "走路", "automotive": "开车"}
                motion_val = data.get('motionactivities', ['未知'])[0] if data.get('motionactivities') else '未知'
                lines.append(f"- 当前运动状态: {motion_map.get(motion_val, motion_val)}")                
                conn_map = {"w": "Wi-Fi 连接", "m": "蜂窝移动网络", "o": "离线"}
                conn_val = data.get('conn', '未知')
                lines.append(f"- 当前网络连接类型: ({conn_map.get(conn_val, '未知')})")
            except Exception as e:
                lines.append(f"- 位置信息解析错误: {str(e)}")
        else:
            lines.append(f"-位置服务没有开启")
        return "".join(lines)

        
