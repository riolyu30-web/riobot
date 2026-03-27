"""Chat channels module with plugin architecture."""

from nanobot.channels.base import BaseChannel
from nanobot.channels.manager import ChannelManager
from .telegram import TelegramChannel
from .wechat import WeChatChannel
from .whatsapp import WhatsAppChannel

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
    "APIChannel",
]
