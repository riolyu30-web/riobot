"""Memory system for persistent agent memory."""

from __future__ import annotations

import asyncio
import datetime
import json
import os
import weakref
from pathlib import Path
from typing import TYPE_CHECKING, Any, Callable

from loguru import logger
from openviking import OpenViking

from nanobot.utils.helpers import ensure_dir, estimate_message_tokens, estimate_prompt_tokens_chain

if TYPE_CHECKING:
    from nanobot.providers.base import LLMProvider
    from nanobot.session.manager import Session, SessionManager
import os
from dotenv import load_dotenv
load_dotenv()
MEMORY_SCORE = float(os.getenv("MEMORY_SCORE", 0.3))

_SAVE_MEMORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_memory",
            "description": "Save the memory consolidation result to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "memory_update": {
                        "type": "string",
                        "description": "Full updated long-term memory as markdown. Include existing memory plus new explicit decisions or requests you were told to remember. "
                        "Ignore general conversation, user questions, or vague corrections."
                        "Only save finalized information or direct remember this instructions. Return unchanged if nothing new."
                    },
                },
                "required": ["memory_update"],
            },
        },
    }
]

_SAVE_HISTORY_TOOL = [
    {
        "type": "function",
        "function": {
            "name": "save_history",
            "description": "Save the history entry to persistent storage.",
            "parameters": {
                "type": "object",
                "properties": {
                    "history_entry": {
                        "type": "string",
                        "description": "A paragraph summarizing key events/decisions/topics. "
                        "Start with [YYYY-MM-DD HH:MM]. Include detail useful for grep search.",
                    },
                },
                "required": ["history_entry",],
            },
        },
    }
]


def _ensure_text(value: Any) -> str:
    """Normalize tool-call payload values to text for file storage."""
    return value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)

def _normalize_save_memory_args(args: Any) -> dict[str, Any] | None:
    """Normalize provider tool-call arguments to the expected dict shape."""
    if isinstance(args, str):
        args = json.loads(args)
    if isinstance(args, list):
        return args[0] if args and isinstance(args[0], dict) else None
    return args if isinstance(args, dict) else None

class MemoryStore:
    """OpenViking-based memory storage."""

    def __init__(self, workspace: Path):
        self.memory_dir = ensure_dir(workspace / "memory")
        self.history_file = self.memory_dir / "HISTORY.md"
        self.memory_file = self.memory_dir / "MEMORY.md"

    def read_long_term(self) -> str:
        if self.memory_file.exists():
            return self.memory_file.read_text(encoding="utf-8")
        return ""

    def write_long_term(self, content: str) -> None:
        self.memory_file.write_text(content, encoding="utf-8")

    def append_history(self, entry: str) -> None:
        with open(self.history_file, "a", encoding="utf-8") as f:
            f.write(entry.rstrip() + "\n\n")

    def get_memory_context(self) -> str:
        long_term = self.read_long_term()
        return f"{long_term}" if long_term else ""

    @staticmethod
    def _format_all_messages(messages: list[dict]) -> str:
        # 初始化一个空列表，用于存储格式化后的消息行
        lines = []
        # 遍历传入的消息列表
        for message in messages:
            # 如果消息没有内容，则跳过当前循环
            if not message.get("content"):
                # 跳过无内容的消息
                continue
            # 将格式化后的消息追加到列表中，格式为：[时间戳] 角色: 内容
            lines.append(
                # 拼接时间戳、角色和内容字符串
                f"[{message.get('timestamp', '?')[:16]}] {message['role'].upper()}: {message['content']}"
            )
        # 将列表中的所有行用换行符连接成一个完整的字符串并返回
        return "\n".join(lines)

    @staticmethod
    def _format_user_messages(messages: list[dict]) -> str:
        # 初始化一个空列表，用于存储格式化后的消息行
        lines = []
        # 遍历传入的消息列表
        for message in messages:
            # 如果消息没有内容，则跳过当前循环
            if not message.get("content"):
                # 跳过无内容的消息
                continue
            # 如果消息包含工具使用记录，则过滤掉该条记录
            if message['role'].upper() == "USER":
                # 将格式化后的消息追加到列表中，格式为：[时间戳] 角色: 内容
                lines.append(
                    # 拼接时间戳、角色和内容字符串
                    f"[{message.get('timestamp', '?')[:16]}] {message['role'].upper()}: {message['content']}"
                )
        # 将列表中的所有行用换行符连接成一个完整的字符串并返回
        return "\n".join(lines)

    async def consolidate(
        self,
        messages: list[dict],
        provider: 'LLMProvider',
        model: str,
    ) -> bool:

        """Consolidate the provided message chunk into USER.md + HISTORY.md + OpenViking resources."""
        if not messages:
            return True
        try:
            conversation_context = self._format_all_messages(messages)
            # 1. 提取历史记录            
            if conversation_context:
                
                prompt = f"""Process this conversation and call the save_history tool with your consolidation.

        ## Conversation to Process
        {conversation_context}"""

                response = await provider.chat_with_retry(
                    messages=[
                        {"role": "system", "content": "You are a memory consolidation agent. Call the save_history tool with your consolidation of the conversation."},
                        {"role": "user", "content": prompt},
                    ],
                    tools=_SAVE_HISTORY_TOOL,
                    model=model,
                )

                if not response.has_tool_calls:
                    logger.warning("Memory consolidation: LLM did not call save_history, skipping")
                    return False

                args = _normalize_save_memory_args(response.tool_calls[0].arguments)

                if entry := args.get("history_entry"):
                    self.append_history(_ensure_text(entry))
                # 2. 提取用户记
            conversation_context = self._format_user_messages(messages)
            if conversation_context:
                current_memory = self.get_memory_context()
                prompt = f"""Process this conversation and call the save_memory tool with your consolidation.

        ## Current Long-term Memory
        {current_memory or "(empty)"}            

        ## Conversation to Process
        {conversation_context}"""

                response = await provider.chat_with_retry(
                    messages=[
                        {"role": "system", "content": "You are a memory consolidation agent. Call the save_memory tool with your consolidation of the conversation."},
                        {"role": "user", "content": prompt},
                    ],
                    tools=_SAVE_MEMORY_TOOL,
                    model=model,
                )

                if not response.has_tool_calls:
                    logger.warning("Memory consolidation: LLM did not call save_memory, skipping")
                    return False

                args = _normalize_save_memory_args(response.tool_calls[0].arguments)
                if update := args.get("memory_update"):
                    update = _ensure_text(update)
                    if update != current_memory:
                        self.write_long_term(update)
        
            logger.info("Memory consolidation done for {} messages", len(messages))
            return True
        except Exception:
                logger.exception("Memory consolidation failed")
        return False


class MemoryConsolidator:
    """Owns consolidation policy, locking, and session offset updates."""

    # 设置最大合并轮次，防止无限循环
    _MAX_CONSOLIDATION_ROUNDS = 5

    def __init__(
        self,
        # 工作区路径，用于初始化存储
        workspace: Path,
        # LLM 提供者，用于调用大模型
        provider: LLMProvider,
        # 使用的模型名称
        model: str,
        # 会话管理器
        sessions: SessionManager,
        # 上下文窗口的最大 Token 数
        context_window_tokens: int,
        # 构建消息列表的回调函数
        build_messages: Callable[..., list[dict[str, Any]]],
        # 获取工具定义的回调函数
        get_tool_definitions: Callable[[], list[dict[str, Any]]],
    ):
        # 初始化持久化记忆存储
        self.store = MemoryStore(workspace)
        # 保存 LLM 提供者实例
        self.provider = provider
        # 保存模型名称
        self.model = model
        # 保存会话管理器实例
        self.sessions = sessions
        # 保存上下文窗口的 Token 阈值
        self.context_window_tokens = context_window_tokens
        # 保存构建消息的回调
        self._build_messages = build_messages
        # 保存获取工具定义的回调
        self._get_tool_definitions = get_tool_definitions
        # 使用弱引用字典管理每个会话的异步锁，防止内存泄漏
        self._locks: weakref.WeakValueDictionary[str, asyncio.Lock] = weakref.WeakValueDictionary()

    def get_lock(self, session_key: str) -> asyncio.Lock:
        """Return the shared consolidation lock for one session."""
        # 如果会话锁存在则返回，否则创建并返回一个新的异步锁
        return self._locks.setdefault(session_key, asyncio.Lock())

    async def consolidate_messages(self, messages: list[dict[str, object]]) -> bool:
        """Archive a selected message chunk into persistent memory."""
        # 调用 store 的 consolidate 方法，将消息块归档到持久化记忆中
        return await self.store.consolidate(messages, self.provider, self.model)

    def pick_consolidation_boundary(
        self,
        # 当前会话对象
        session: Session,
        # 需要移除的 Token 数量目标
        tokens_to_remove: int,
    ) -> tuple[int, int] | None:
        """Pick a user-turn boundary that removes enough old prompt tokens."""
        # 获取上次已合并的消息索引作为起始点
        start = session.last_consolidated
        # 如果起始点超出消息长度，或者不需要移除 Token，则返回 None
        if start >= len(session.messages) or tokens_to_remove <= 0:
            # 直接返回空，无需操作
            return None

        # 初始化已移除的 Token 计数器
        removed_tokens = 0
        # 记录上一个合法的切分边界（必须是 user 角色）
        last_boundary: tuple[int, int] | None = None
        # 遍历从 start 开始的所有未合并消息
        for idx in range(start, len(session.messages)):
            # 获取当前索引对应的消息对象
            message = session.messages[idx]
            # 如果不是第一条消息，且角色是 user，则可以作为一个边界
            if idx > start and message.get("role") == "user":
                # 更新最新的边界信息：(当前索引, 到目前为止累计的 Token 数)
                last_boundary = (idx, removed_tokens)
                # 如果累计的 Token 数已经达到或超过需要移除的目标值
                if removed_tokens >= tokens_to_remove:
                    # 直接返回找到的边界
                    return last_boundary
            # 累加当前消息预估的 Token 数量
            removed_tokens += estimate_message_tokens(message)

        # 遍历完还没达到目标，则返回找到的最后一个边界
        return last_boundary

    def estimate_session_prompt_tokens(self, session: Session) -> tuple[int, str]:
        """Estimate current prompt size for the normal session history view."""
        # 获取会话中未合并的最新历史消息记录
        history = session.get_history(max_messages=0)
        # 尝试从 session.key 中解析 channel 和 chat_id，如果存在冒号则拆分，否则为 None
        channel, chat_id = (session.key.split(":", 1) if ":" in session.key else (None, None))
        # 构建一个包含探测标记的探针消息列表
        probe_messages = self._build_messages(
            # 传入当前历史记录
            history=history,
            # 使用 "[token-probe]" 模拟当前新消息
            current_message="[token-probe]",
            # 传入频道信息
            channel=channel,
            # 传入聊天 ID
            chat_id=chat_id,
        )
        # 调用估算函数链计算这些消息及工具定义的总 Token 数，并返回估算值和数据源信息
        return estimate_prompt_tokens_chain(
            # LLM 提供者
            self.provider,
            # 模型名称
            self.model,
            # 构建好的探针消息列表
            probe_messages,
            # 获取并传入工具定义列表
            self._get_tool_definitions(),
        )

    async def archive_unconsolidated(self, session: Session) -> bool:
        """Archive the full unconsolidated tail for /new-style session rollover."""
        # 根据 session.key 获取对应的异步锁，确保并发安全
        lock = self.get_lock(session.key)
        # 加锁以执行后续的归档操作
        async with lock:
            # 切片获取从上次合并位置到最后的所有未合并消息
            snapshot = session.messages[session.last_consolidated:]
            # 如果没有未合并的消息
            if not snapshot:
                # 直接返回成功
                return True
            # 将获取到的消息快照进行合并归档，并返回结果
            return await self.consolidate_messages(snapshot)

    async def maybe_consolidate_by_tokens(self, session: Session) -> None:
        """Loop: archive old messages until prompt fits within half the context window."""
        # 如果会话没有消息，或未设置上下文 Token 限制，则直接返回
        if not session.messages or self.context_window_tokens <= 0:
            # 退出当前方法
            return

        # 获取会话专属的异步锁以防并发冲突
        lock = self.get_lock(session.key)
        # 进入异步上下文管理器获取锁
        async with lock:
            # 设定目标 Token 数为上下文窗口阈值的一半
            target = self.context_window_tokens // 2
            # 估算当前会话历史占用的 Token 数和计算来源
            estimated, source = self.estimate_session_prompt_tokens(session)
            # 如果估算值异常（<= 0）
            if estimated <= 0:
                # 直接退出
                return
            # 如果当前占用还没有达到上下文阈值限制
            if estimated < self.context_window_tokens:
                # 记录调试日志，说明目前不需要合并
                logger.debug(
                    # 格式化字符串
                    "Token consolidation idle {}: {}/{} via {}",
                    # 会话 key
                    session.key,
                    # 当前估算 Token
                    estimated,
                    # 最大允许 Token
                    self.context_window_tokens,
                    # 来源信息
                    source,
                )
                # 退出方法
                return

            # 最多循环执行 _MAX_CONSOLIDATION_ROUNDS 次归档操作
            for round_num in range(self._MAX_CONSOLIDATION_ROUNDS):
                # 如果估算值已经降低到目标阈值及以下
                if estimated <= target:
                    # 退出循环，完成归档
                    return

                # 计算需要移除的 Token 数，并挑选出合适的切分边界
                boundary = self.pick_consolidation_boundary(session, max(1, estimated - target))
                # 如果找不到安全的边界（例如没有用户消息作为分隔点）
                if boundary is None:
                    # 记录调试日志说明情况
                    logger.debug(
                        # 格式化字符串
                        "Token consolidation: no safe boundary for {} (round {})",
                        # 会话 key
                        session.key,
                        # 当前轮次
                        round_num,
                    )
                    # 无法继续合并，退出
                    return

                # 提取边界的结束索引
                end_idx = boundary[0]
                # 截取从上次合并位置到结束索引之间的消息块
                chunk = session.messages[session.last_consolidated:end_idx]
                # 如果切片为空
                if not chunk:
                    # 退出循环
                    return

                # 记录信息日志，开始进行一轮合并归档
                logger.info(
                    # 格式化字符串
                    "Token consolidation round {} for {}: {}/{} via {}, chunk={} msgs",
                    # 当前轮次
                    round_num,
                    # 会话 key
                    session.key,
                    # 估算 Token
                    estimated,
                    # 上下文窗口限制
                    self.context_window_tokens,
                    # 来源信息
                    source,
                    # 消息块的长度
                    len(chunk),
                )
                # 调用 consolidate_messages 异步执行合并，如果失败
                if not await self.consolidate_messages(chunk):
                    # 直接退出
                    return
                # 更新会话的最后一次合并索引位置
                session.last_consolidated = end_idx
                # 将更新后的会话状态持久化保存
                self.sessions.save(session)

                # 重新估算当前剩余历史消息的 Token 数
                estimated, source = self.estimate_session_prompt_tokens(session)
                # 如果重新估算结果异常
                if estimated <= 0:
                    # 直接退出
                    return
