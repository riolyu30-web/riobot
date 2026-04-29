"""Shell execution tool."""

import os
from pathlib import Path
from typing import Any
from nanobot.utils.helpers import ensure_dir
from nanobot.agent.tools.base import Tool

class MemoryTool(Tool):

    def __init__(
        self,
        workspace: Path | None = None,
    ):
        self.workspace = workspace

    @property
    def name(self) -> str:
        return "memory"

    @property
    def description(self) -> str:
        return "Update the content of MEMORY.md file."
    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                    "memory_update": {
                        "type": "string",
                        "description": "Full updated long-term memory as markdown. "
                        "that the user explicitly and deliberately instructed you to remember.  "
                    },
            },
            "required": ["memory_update"]
        }
    
    async def execute(self, memory_update: str, **kwargs: Any) -> str:
        """Append the new memory record to MEMORY.md."""
        try:
            # 确保工作空间已设置，否则返回错误提示
            if self.workspace is None:
                return "Workspace is not set."             
            # 构建 MEMORY.md 文件的完整路径
            memory_dir = ensure_dir(self.workspace / "memory")
            memory_file_path = memory_dir / "MEMORY.md"

            # 以写入模式打开文件并写入更新的记忆内容
            with open(memory_file_path, "w", encoding="utf-8") as f:
                # 写入内容并添加换行符以确保格式清晰
                f.write(f"{memory_update}\n")
                
            # 返回成功保存的提示信息
            return "Memory successfully appended to MEMORY.md"
        except Exception as e:
            # 如果发生异常，返回错误信息
            return f"Error appending to MEMORY.md: {str(e)}"
