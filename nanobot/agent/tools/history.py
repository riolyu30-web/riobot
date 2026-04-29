"""Shell execution tool."""


from nanobot.session.manager import Session, SessionManager
from typing import Any

from nanobot.agent.tools.base import Tool


class HistoryTool(Tool):
    """Tool to get message history."""

    def __init__(
        self,
        sessions: SessionManager | None = None,
    ):
        self.sessions = sessions 

    @property
    def name(self) -> str:
        return "history"

    @property
    def description(self) -> str:
        return "Get the history of messages for a channel and chat ID."

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "channel": {
                    "type": "string",
                    "description": "target channel (telegram, discord, etc.)"
                },
                "chat_id": {
                    "type": "string",
                    "description": "target chat/user ID"
                },
                "max_messages": {
                    "type": "integer",
                    "description": "Optional: maximum number of messages to return"
                }
            },
            "required": ["channel", "chat_id"]
        }
    
    async def execute(self, channel: str, chat_id: str, max_messages: int = 50, **kwargs: Any) -> str:
        """Execute a shell command and return its output."""
        if self.sessions is None:
            return "Session manager is not initialized."
        key = f"{channel}:{chat_id}"
        session = self.sessions.get_or_create(key)
        if session is None:
            return "No session found for this channel and chat ID."
        return session.get_history(max_messages=max_messages)
