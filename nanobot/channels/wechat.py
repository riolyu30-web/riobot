"""WeChat channel implementation using wechatbot SDK."""

import asyncio
from typing import TYPE_CHECKING

from loguru import logger

from nanobot.bus.events import OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel
from nanobot.config.schema import WechatConfig
# 导入 os 模块用于路径检查
import os
# 导入 json 模块用于读取 JSON 文件
import json

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

from nanobot.config.paths import get_media_dir
import time
                    
# 获取 wechat 通道的专属媒体存放目录
MEDIA_PATH = get_media_dir("wechat")

class WeChatChannel(BaseChannel):
    """WeChat channel using wechatbot SDK."""

    name = "wechat"

    def __init__(self, config: WechatConfig, bus: MessageBus):
        super().__init__(config, bus)
        self.config: WechatConfig = config
        self._bot: "WeChatBot | None" = None
        self._media_cache: dict[str, list[tuple[str, str]]] = {}

    async def start(self) -> None:
        """Start the WeChat bot."""
        # 如果微信模块不可用，记录错误日志并返回
        if not WECHAT_AVAILABLE:
            # 记录 wechatbot 模块不可用的错误信息
            logger.error("wechatbot module not available. Please ensure it is in the Python path.")
            # 结束启动过程
            return

        # 检查是否配置了凭据文件路径
        if not self.config.cred_path:
            # 记录未配置凭据文件路径的错误信息
            logger.error("WeChat cred_path not configured")
            # 结束启动过程
            return

        # 检查凭据文件是否存在
        if not os.path.exists(self.config.cred_path):
            # 记录凭据文件不存在的错误信息
            logger.error(f"WeChat credentials file not found: {self.config.cred_path}")
            # 结束启动过程
            return

        # 尝试读取 JSON 格式的凭据文件
        try:
            # 以只读模式打开凭据文件
            with open(self.config.cred_path, "r", encoding="utf-8") as f:
                # 解析 JSON 数据到字典
                creds = json.load(f)
        # 捕获 JSON 解析或其他读取错误
        except Exception as e:
            # 记录读取凭据文件失败的错误信息
            logger.error(f"Failed to read WeChat credentials file: {e}")
            # 结束启动过程
            return

        # 提取 token 参数，如果不存在则使用空字符串
        token = creds.get("token", "")
        # 提取 base_url 参数，如果不存在则使用空字符串
        base_url = creds.get("baseUrl", "")
        # 提取 account_id 参数，如果不存在则使用空字符串
        account_id = creds.get("accountId", "")
        # 提取 user_id 参数，如果不存在则使用空字符串
        user_id = creds.get("userId", "")
        # 提取 saved_at 参数，如果不存在则使用空字符串
        saved_at = creds.get("saved_at", "")

        # 检查 token 和 account_id 是否存在
        if not token or not account_id:
            # 记录 token 和 account_id 缺失的错误信息
            logger.error("WeChat token and account_id not found in credentials file")
            # 结束启动过程
            return

        # 设置运行状态标志为 True
        self._running = True
        # 初始化 WeChatBot 实例
        self._bot = WeChatBot()

        # 尝试使用凭据登录微信
        try:
            # 调用 checkin 方法登录
            await self._bot.checkin(
                # 传入 token 参数
                token=token,
                # 传入 base_url 参数
                base_url=base_url,
                # 传入 account_id 参数
                account_id=account_id,
                # 传入 user_id 参数
                user_id=user_id,
                # 传入 saved_at 参数
                saved_at=saved_at,
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
        # 检查机器人客户端是否已经初始化
        if not self._bot:
            # 如果未初始化，记录警告日志
            logger.warning("WeChat client not initialized")
            # 直接返回，不执行后续发送操作
            return

        # 尝试执行发送消息的操作
        try:
            # 检查消息内容是否非空
            if msg.content:
                # 使用缓存的 context_token 发送文本消息
                await self._bot.send(msg.chat_id, msg.content)
            
            # 检查是否包含媒体文件
            if msg.media:
                # 导入 os 模块用于路径和文件操作
                import os
                # 导入 mimetypes 模块用于推断文件类型
                import mimetypes
                
                # 遍历所有需要发送的媒体文件路径
                for media_path in msg.media:
                    # 检查当前媒体文件是否存在
                    if not os.path.exists(media_path):
                        # 如果文件不存在，记录警告日志
                        logger.warning("Media file not found: {}", media_path)
                        # 跳过当前文件，继续处理下一个
                        continue
                    
                    # 根据文件路径推断媒体的 MIME 类型
                    mime_type, _ = mimetypes.guess_type(media_path)
                    
                    # 以二进制只读模式打开文件
                    with open(media_path, "rb") as f:
                        # 读取文件的全部字节数据
                        data = f.read()
                        
                    # 初始化一个空字典用于构建发送内容
                    content_dict = {}
                    
                    # 判断文件是否为图片类型
                    if mime_type and mime_type.startswith("image/"):
                        # 如果是图片，将数据存入 image 键
                        content_dict["image"] = data
                    # 判断文件是否为视频类型
                    elif mime_type and mime_type.startswith("video/"):
                        # 如果是视频，将数据存入 video 键
                        content_dict["video"] = data
                    # 否则作为普通文件处理
                    else:
                        # 将数据存入 file 键
                        content_dict["file"] = data
                        # 从路径中提取文件名并存入 file_name 键
                        content_dict["file_name"] = os.path.basename(media_path)
                        
                    # 调用机器人的 send_media 方法发送多媒体消息
                    await self._bot.send_media(msg.chat_id, content_dict)
        # 捕获发送过程中的所有异常
        except Exception as e:
            # 记录发送微信消息时发生的错误
            logger.error("Error sending WeChat message: {}", e)

    async def _on_message(self, msg: "IncomingMessage") -> None:
        """Handle incoming message from WeChat."""
        try:
            content = (msg.text or "").strip()
            if not content and not (msg.images or msg.voices or msg.files or msg.videos):
                return
                
            chat_id = msg.user_id
            sender_id = msg.user_id

            if sender_id not in self._media_cache:
                self._media_cache[sender_id] = []

            # 1. 尝试下载新到达的媒体文件并加入缓存
            if msg.images or msg.voices or msg.files or msg.videos:
                downloaded = await self._bot.download(msg)
                if downloaded:
                   
                    # 生成唯一文件名
                    if downloaded.file_name:
                        filename = f"{int(time.time())}_{downloaded.file_name}"
                    else:
                        ext = ""
                        if downloaded.type == "image":
                            ext = ".jpg"
                        elif downloaded.type == "voice":
                            ext = ".silk" if downloaded.format == "silk" else ".amr"
                        elif downloaded.type == "video":
                            ext = ".mp4"
                        else:
                            ext = ".bin"
                        filename = f"{int(time.time())}{ext}"
                    
                    # 写入文件
                    file_path = MEDIA_PATH / filename
                    with open(file_path, "wb") as f:
                        f.write(downloaded.data)
                    
                    # 构建媒体标签以便追加到 content 中 (如 [image: path] 或 [file: path])
                    media_type = "image" if downloaded.type == "image" else "file"
                    media_tag = f"[{media_type}: {file_path}]"
                    
                    # 将下载好的媒体信息放入该用户的缓存中
                    self._media_cache[sender_id].append((media_tag, str(file_path)))
            
            # 2. 如果没有文本内容，说明这是一条纯媒体消息，则先暂存，不立即下发给系统

            if not content or content in "[image]" or content in "[file]" or content in "[video]":
                return

            # 3. 如果收到了文本，提取该用户之前缓存的所有媒体记录，与本次文本一起合并发送
            media_paths = []
            cached_media = self._media_cache.pop(sender_id, [])
            for m_tag, m_path in cached_media:
                content = f"{content}\n{m_tag}" if content else m_tag
                media_paths.append(m_path)

            await self._handle_message(
                sender_id=sender_id,
                chat_id=chat_id,
                content=content,
                media=media_paths,
            )
        except Exception:
            logger.exception("Error handling WeChat message")
