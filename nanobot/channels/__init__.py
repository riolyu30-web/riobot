"""Chat channels module with plugin architecture."""

from nanobot.channels.base import BaseChannel
from nanobot.channels.manager import ChannelManager
from .telegram import TelegramChannel
from .wechat import WeChatChannel
from .whatsapp import WhatsAppChannel
from .crm import CRMChannel # 导入 CRMChannel
from .websocket import WebSocketChannel # 导入 WebSocketChannel

__all__ = [
    "BaseChannel",
    "ChannelManager",
    "TelegramChannel",
    "WhatsAppChannel",
    "DiscordChannel",
    "FeishuChannel",
    "DingTalkChannel",
    "EmailChannel",
    "SlackChannel",
    "QQChannel",
    "WeChatChannel",
    "MatrixChannel",
    "CRMChannel", # 将 CRMChannel 添加到 __all__ 列表中
    "WebSocketChannel", # 将 WebSocketChannel 添加到 __all__ 列表中
]
