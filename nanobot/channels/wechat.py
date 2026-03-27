"""WeChat channel implementation using wechatbot SDK."""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import WechatConfig

try:
    from wechatbot.client import WeChatBot
    from wechatbot.types import IncomingMessage
    WECHAT_AVAILABLE = True
except ImportError:
    WECHAT_AVAILABLE = False
    WeChatBot = None
    IncomingMessage = None

if TYPE_CHECKING:
    from wechatbot.client import WeChatBot
    from wechatbot.types import IncomingMessage


class WeChatChannel(BaseChannel):
    """WeChat channel using wechatbot SDK."""

    name = "wechat"

    def __init__(self, config: WechatConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: WechatConfig = config
        self._bot: "WeChatBot | None" = None

    async def start(self) -> None:
        """Start the WeChat bot."""
        if not WECHAT_AVAILABLE:
            logger.error("wechatbot module not available. Please ensure it is in the Python path.")
            return

        if not self.config.token or not self.config.account_id:
            logger.error("WeChat token and account_id not configured")
            return

        self._running = True
        self._bot = WeChatBot()

        # Load credentials from config
        try:
            await self._bot.checkin(
                token=self.config.token,
                base_url=self.config.base_url,
                account_id=self.config.account_id,
                user_id=self.config.user_id,
                saved_at=self.config.saved_at,
            )
        except Exception as e:
            logger.error(f"Failed to checkin wechatbot: {e}")
            return

        @self._bot.on_message
        async def handle_message(msg: "IncomingMessage"):
            await self._on_message(msg)

        logger.info("WeChat bot started")
        await self._run_bot()

    async def _run_bot(self) -> None:
        """Run the bot connection."""
        try:
            await self._bot.start()
        except Exception as e:
            logger.warning("WeChat bot error: {}", e)
        finally:
            self._running = False

    async def stop(self) -> None:
        """Stop the WeChat bot."""
        self._running = False
        if self._bot:
            self._bot.stop()
        logger.info("WeChat bot stopped")

    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through WeChat."""
        if not self._bot:
            logger.warning("WeChat client not initialized")
            return

        try:
            # Using send will require the context_token to be cached internally by WeChatBot
            # If there's a recent message from the user, it should work.
            await self._bot.send(msg.chat_id, msg.content)
        except Exception as e:
            logger.error("Error sending WeChat message: {}", e)

    async def _on_message(self, msg: "IncomingMessage") -> None:
        """Handle incoming message from WeChat."""
        try:
            content = (msg.text or "").strip()
            if not content and not (msg.images or msg.voices or msg.files or msg.videos):
                return
            
            chat_id = msg.user_id
            sender_id = msg.user_id

            await self._handle_message(
                sender_id=sender_id,
                chat_id=chat_id,
                content=content,
            )
        except Exception:
            logger.exception("Error handling WeChat message")
