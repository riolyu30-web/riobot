"""Chat channels module with plugin architecture."""

from nanobot.channels.base import BaseChannel
from nanobot.channels.manager import ChannelManager
from .telegram import TelegramChannel
from .wechat import WeChatChannel
from .whatsapp import WhatsAppChannel
from .crm import CRMChannel # 导入 CRMChannel

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
]
