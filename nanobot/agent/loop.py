"""Agent loop: the core processing engine."""

from __future__ import annotations

import asyncio
import json
import re
from contextlib import AsyncExitStack
from pathlib import Path
from typing import TYPE_CHECKING, Any, Awaitable, Callable
import shutil
from loguru import logger
from torchvision.models import mobilenet

from nanobot.config.schema import Config
from nanobot.agent.context import ContextBuilder
from nanobot.agent.memory import MemoryConsolidator
from nanobot.agent.subagent import SubagentManager
from nanobot.agent.tools.cron import CronTool
from nanobot.agent.tools.filesystem import EditFileTool, ListDirTool, ReadFileTool, WriteFileTool
from nanobot.agent.tools.message import MessageTool
from nanobot.agent.tools.registry import ToolRegistry
from nanobot.agent.tools.shell import ExecTool
from nanobot.agent.tools.spawn import SpawnTool
from nanobot.agent.tools.web import WebFetchTool, WebSearchTool
from nanobot.agent.tools.history import HistoryTool
from nanobot.agent.tools.memory import MemoryTool
from nanobot.agent.tools.location import LocationTool
from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.providers.base import LLMProvider
from nanobot.session.manager import Session, SessionManager
# 引入 estimate_message_tokens 方法用于计算单个消息的 token 数量
from nanobot.utils.helpers import estimate_message_tokens
import os
from dotenv import load_dotenv
load_dotenv()

# 导入同步模板目录结构的辅助函数
from nanobot.utils.helpers import sync_workspace_templates
# 导入 get_data_dir 获取项目的基础数据目录
from nanobot.config.paths import get_data_dir

if TYPE_CHECKING:
    from nanobot.config.schema import ChannelsConfig, ExecToolConfig
    from nanobot.cron.service import CronService

CONOLIDATED_NUM = int(os.getenv("CONOLIDATED_NUM", 5))


class AgentLoop:
    """
    The agent loop is the core processing engine.

    It:
    1. Receives messages from the bus
    2. Builds context with history, memory, skills
    3. Calls the LLM
    4. Executes tool calls
    5. Sends responses back
    """

    _TOOL_RESULT_MAX_CHARS = 500

    def __init__(
        self,
        bus: MessageBus,
        config: Config,
        default_provider: LLMProvider | None ,
        workspace: Path,
        model: str | None = None,
        max_iterations: int = 40,
        temperature: float = 0.1,
        max_tokens: int = 4096,
        reasoning_effort: str | None = None,
        context_window_tokens: int = 65_536,
        brave_api_key: str | None = None,
        web_proxy: str | None = None,
        exec_config: ExecToolConfig | None = None,
        cron_service: CronService | None = None,
        restrict_to_workspace: bool = False,
        session_manager: SessionManager | None = None,
        mcp_servers: dict | None = None,
        channels_config: ChannelsConfig | None = None,
    ):
        from nanobot.config.schema import ExecToolConfig
        self.bus = bus
        self.config = config
        self.channels_config = channels_config
        self.workspace = workspace
        self.model = model 
        self.default_model = self.model
        self.provider = self._make_provider(self.model)
        self.default_provider = default_provider or self.provider
        self.max_iterations = max_iterations
        self.temperature = temperature
        self.max_tokens = max_tokens
        self.reasoning_effort = reasoning_effort
        self.context_window_tokens = context_window_tokens
        self.brave_api_key = brave_api_key
        self.web_proxy = web_proxy
        self.exec_config = exec_config or ExecToolConfig()
        self.cron_service = cron_service
        self.restrict_to_workspace = restrict_to_workspace
        
        # 缓存工作空间相关的组件
        self._workspace_components: dict[str, dict] = {}
        
        self.context = ContextBuilder(workspace)
        self.sessions = session_manager or SessionManager(workspace)
        self.tools = ToolRegistry()
        self.subagents = SubagentManager(
            provider=self.provider,
            workspace=workspace,
            bus=bus,
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
            reasoning_effort=reasoning_effort,
            brave_api_key=brave_api_key,
            web_proxy=web_proxy,
            exec_config=self.exec_config,
            restrict_to_workspace=restrict_to_workspace,
        )

        self._running = False
        self._mcp_servers = mcp_servers or {}
        self._mcp_stack: AsyncExitStack | None = None
        self._mcp_connected = False
        self._mcp_connecting = False
        self._active_tasks: dict[str, list[asyncio.Task]] = {}  # session_key -> tasks
        self._processing_lock = asyncio.Lock()
        self.memory_consolidator = MemoryConsolidator(
            workspace=workspace,
            provider=self.default_provider,
            model=self.model,
            sessions=self.sessions,
            context_window_tokens=context_window_tokens,
            build_messages=self.context.build_messages,
            get_tool_definitions=self.tools.get_definitions,
        )
        self._register_default_tools()
        
        # 保存初始工作空间的组件到缓存中
        self._cache_workspace_components(str(self.workspace.resolve()))

    def _cache_workspace_components(self, ws_key: str) -> None:
        """Cache components tied to a specific workspace."""
        self._workspace_components[ws_key] = {
            "context": self.context,
            "sessions": self.sessions,
            "tools": self.tools,
            "subagents": self.subagents,
            "memory_consolidator": self.memory_consolidator,
        }

    def _switch_workspace(self, spacename: str) -> bool:
        """Switch to a different workspace and initialize its components."""
        if not spacename:
            return False
        else:
            # 计算新工作空间的绝对路径，将其放在数据目录下的 workspaces 目录中
            new_workspace = (get_data_dir() / spacename).expanduser().resolve()
        
        # 记录是否为新建工作空间
        is_new_workspace = not new_workspace.exists()
        
        # 检查该工作空间目录是否已经存在
        if is_new_workspace:

            # 在新工作空间创建或同步完整的 Markdown 文档目录结构
            sync_workspace_templates(new_workspace)
        # 获取新工作空间的唯一键（绝对路径的字符串形式）
        ws_key = str(new_workspace)
        
        # 更新当前 AgentLoop 的 workspace 属性
        self.workspace = new_workspace
        
        # 如果缓存中已存在该工作空间的组件，则直接复用
        if ws_key in self._workspace_components:
            cached = self._workspace_components[ws_key]
            self.context = cached["context"]
            self.sessions = cached["sessions"]
            self.tools = cached["tools"]
            self.subagents = cached["subagents"]
            self.memory_consolidator = cached["memory_consolidator"]
        else:
            # 否则重新实例化这些组件
            # 重新实例化 ContextBuilder 以使用新工作空间
            self.context = ContextBuilder(new_workspace)
            # 重新实例化 SessionManager 以使用新工作空间
            self.sessions = SessionManager(new_workspace)
            # 重新实例化子代理管理器以使用新工作空间
            self.subagents = SubagentManager(
                provider=self.provider,
                workspace=new_workspace,
                bus=self.bus,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=self.reasoning_effort,
                brave_api_key=self.brave_api_key,
                web_proxy=self.web_proxy,
                exec_config=self.exec_config,
                restrict_to_workspace=self.restrict_to_workspace,
            )
            # 重置工具注册表
            self.tools = ToolRegistry()
            # 重新注册默认工具，使它们绑定到新工作空间
            self._register_default_tools()
            # 重新实例化 MemoryConsolidator 以使用新工作空间和相关新组件
            self.memory_consolidator = MemoryConsolidator(
                workspace=new_workspace,
                provider=self.default_provider,
                model=self.model,
                sessions=self.sessions,
                context_window_tokens=self.context_window_tokens,
                build_messages=self.context.build_messages,
                get_tool_definitions=self.tools.get_definitions,
            )
            # 将新实例化的组件存入缓存
            self._cache_workspace_components(ws_key)

        return is_new_workspace
        

    def _apply_identity(self, msg: Any) -> None:
        """Apply workspace and tool constraints from message identity."""
        # 解析 identity，推荐使用更优雅且扩展性更强的 [WorkspaceName][tool1,tool2][profile] 格式
        if hasattr(msg, "identity") and msg.identity and msg.identity != "*":
            # 提取去除两端空白的 identity 字符串
            identity_str = msg.identity.strip()
            # 使用正则表达式查找所有方括号内的内容，兼容 []、[xxx]、[][][] 等任意组合
            parts = re.findall(r"\[(.*?)\]", identity_str)
            # 如果成功解析出方括号块
            if parts:
                if len(parts) > 2:
                    model_str = parts[2].strip()
                    if model_str and model_str != "*":
                        self.model = model_str
                        self.provider = self._make_provider(model_str)
                
                # 如果存在第二块，则解析为工具列表
                if len(parts) > 1:
                    # 注意处理中文逗号的情况，替换为英文逗号
                    tool_str = parts[1].replace("，", ",")
                    tool_names = [t.strip() for t in tool_str.split(",") if t.strip()]
                    # 只有当解析出的工具列表不为空时，才覆盖默认的所有工具设置
                    if tool_names and tool_names != ["*"]:
                        self.tools.set_available_tools(tool_names)


                # 获取第一块作为工作空间名称
                parsed_workspace = parts[0].strip()
                # 如果解析出的工作空间名称不为空，且不是占位符，则进行切换
                if parsed_workspace and parsed_workspace != "*":
                    self._switch_workspace(parsed_workspace)


    def _make_provider(self, model: str):
        """Create the appropriate LLM provider from config."""
        from nanobot.providers.openai_codex_provider import OpenAICodexProvider
        from nanobot.providers.azure_openai_provider import AzureOpenAIProvider

        provider_name = self.config.get_provider_name(model)
        p = self.config.get_provider(model)

        # OpenAI Codex (OAuth)
        if provider_name == "openai_codex" or model.startswith("openai-codex/"):
            return OpenAICodexProvider(default_model=model)

        # Custom: direct OpenAI-compatible endpoint, bypasses LiteLLM
        from nanobot.providers.custom_provider import CustomProvider
        if provider_name == "custom":
            return CustomProvider(
                api_key=p.api_key if p else "no-key",
                api_base=self.config.get_api_base(model) or "http://localhost:8000/v1",
                default_model=model,
            )

        # Azure OpenAI: direct Azure OpenAI endpoint with deployment name
        if provider_name == "azure_openai":
            if not p or not p.api_key or not p.api_base:
                logger.info("Error: Azure OpenAI requires api_key and api_base.")
                logger.info("Set them in ~/.nanobot/config.json under providers.azure_openai section")
                logger.info("Use the model field to specify the deployment name.")
                raise typer.Exit(1)
            
            return AzureOpenAIProvider(
                api_key=p.api_key,
                api_base=p.api_base,
                default_model=model,
            )

        from nanobot.providers.litellm_provider import LiteLLMProvider
        from nanobot.providers.registry import find_by_name
        spec = find_by_name(provider_name)
        if not model.startswith("bedrock/") and not (p and p.api_key) and not (spec and spec.is_oauth):
            logger.info("Error: No API key configured.")
            logger.info("Set one in ~/.nanobot/config.json under providers section")
            raise typer.Exit(1)

        return LiteLLMProvider(
            api_key=p.api_key if p else None,
            api_base=self.config.get_api_base(model),
            default_model=model,
            extra_headers=p.extra_headers if p else None,
            provider_name=provider_name,
        )


    def _register_default_tools(self) -> None:
        """Register the default set of tools."""
        allowed_dir = self.workspace if self.restrict_to_workspace else None
        for cls in (ReadFileTool, WriteFileTool, EditFileTool, ListDirTool):
            self.tools.register(cls(workspace=self.workspace, allowed_dir=allowed_dir))
        self.tools.register(ExecTool(
            working_dir=str(self.workspace),
            timeout=self.exec_config.timeout,
            restrict_to_workspace=self.restrict_to_workspace,
            path_append=self.exec_config.path_append,
        ))
        self.tools.register(WebSearchTool(api_key=self.brave_api_key, proxy=self.web_proxy))
        self.tools.register(WebFetchTool(proxy=self.web_proxy))
        self.tools.register(MessageTool(send_callback=self.bus.publish_outbound))
        self.tools.register(SpawnTool(manager=self.subagents))
        self.tools.register(HistoryTool(sessions=self.sessions))
        self.tools.register(MemoryTool(workspace=self.workspace))
        self.tools.register(LocationTool(workspace=self.workspace))
        if self.cron_service:
            self.tools.register(CronTool(self.cron_service))

    async def _connect_mcp(self) -> None:
        """Connect to configured MCP servers (one-time, lazy)."""
        if self._mcp_connected or self._mcp_connecting or not self._mcp_servers:
            return
        self._mcp_connecting = True
        from nanobot.agent.tools.mcp import connect_mcp_servers
        try:
            self._mcp_stack = AsyncExitStack()
            await self._mcp_stack.__aenter__()
            await connect_mcp_servers(self._mcp_servers, self.tools, self._mcp_stack)
            self._mcp_connected = True
        except Exception as e:
            logger.error("Failed to connect MCP servers (will retry next message): {}", e)
            if self._mcp_stack:
                try:
                    await self._mcp_stack.aclose()
                except Exception:
                    pass
                self._mcp_stack = None
        finally:
            self._mcp_connecting = False

    def _set_tool_context(self, channel: str, chat_id: str, message_id: str | None = None) -> None:
        """Update context for all tools that need routing info."""
        for name in ("message", "spawn", "cron"):
            if tool := self.tools.get(name):
                if hasattr(tool, "set_context"):
                    tool.set_context(channel, chat_id, *([message_id] if name == "message" else []))

    @staticmethod
    def _strip_think(text: str | None) -> str | None:
        """Remove <think>…</think> blocks that some models embed in content."""
        if not text:
            return None
        return re.sub(r"<think>[\s\S]*?</think>", "", text).strip() or None

    @staticmethod
    def _tool_hint(tool_calls: list) -> str:
        """Format tool calls as concise hint, e.g. 'web_search("query")'."""
        def _fmt(tc):
            args = (tc.arguments[0] if isinstance(tc.arguments, list) else tc.arguments) or {}
            val = next(iter(args.values()), None) if isinstance(args, dict) else None
            if not isinstance(val, str):
                return tc.name
            return f'{tc.name}("{val[:40]}…")' if len(val) > 40 else f'{tc.name}("{val}")'
        return ", ".join(_fmt(tc) for tc in tool_calls)

    async def _run_agent_loop(
        self,
        initial_messages: list[dict],
        on_progress: Callable[..., Awaitable[None]] | None = None,
    ) -> tuple[str | None, list[str], list[dict]]:
        """Run the agent iteration loop."""
        messages = initial_messages
        iteration = 0
        final_content = None
        tools_used: list[str] = []
        total_tokens_used = 0

        while iteration < self.max_iterations:
            iteration += 1

            tool_defs = self.tools.get_definitions()

            # --- 新增的打印与字数统计代码结束 ---            
            response = await self.provider.chat_with_retry(
                messages=messages,
                tools=tool_defs,
                model=self.model,
                temperature=self.temperature,
                max_tokens=self.max_tokens,
                reasoning_effort=self.reasoning_effort,
            )

            if response.has_tool_calls:
                if on_progress:
                    thought = self._strip_think(response.content)
                    if thought:
                        await on_progress(thought)
                    await on_progress(self._tool_hint(response.tool_calls), tool_hint=True)

                tool_call_dicts = [
                    {
                        "id": tc.id,
                        "type": "function",
                        "function": {
                            "name": tc.name,
                            "arguments": json.dumps(tc.arguments, ensure_ascii=False)
                        }
                    }
                    for tc in response.tool_calls
                ]
                messages = self.context.add_assistant_message(
                    messages, response.content, tool_call_dicts,
                    reasoning_content=response.reasoning_content,
                    thinking_blocks=response.thinking_blocks,
                )

                for tool_call in response.tool_calls:
                    tools_used.append(tool_call.name)
                    args_str = json.dumps(tool_call.arguments, ensure_ascii=False)
                    logger.info("Tool call: {}({})", tool_call.name, args_str[:200])
                    result = await self.tools.execute(tool_call.name, tool_call.arguments)
                    messages = self.context.add_tool_result(
                        messages, tool_call.id, tool_call.name, result
                    )
                # --- 字数统计代码 ---
                total_tokens_used = self._count_tokens(messages, iteration, total_tokens_used)

            else:
                clean = self._strip_think(response.content)
                # Don't persist error responses to session history — they can
                # poison the context and cause permanent 400 loops (#1303).
                if response.finish_reason == "error":
                    logger.error("LLM returned error: {}", (clean or "")[:200])
                    final_content = clean or "Sorry, I encountered an error calling the AI model."
                    break
                messages = self.context.add_assistant_message(
                    messages, clean, reasoning_content=response.reasoning_content,
                    thinking_blocks=response.thinking_blocks,
                )
                final_content = clean
                # --- 字数统计代码 ---
                total_tokens_used = self._count_tokens(messages, iteration, total_tokens_used)
                break


        if final_content is None and iteration >= self.max_iterations:
            logger.warning("Max iterations ({}) reached", self.max_iterations)
            final_content = (
                f"I reached the maximum number of tool call iterations ({self.max_iterations}) "
                "without completing the task. You can try breaking the task into smaller steps."
            )

        return final_content, tools_used, messages
    
    def _count_tokens(self, messages: list[dict], iteration: int, total_tokens_used: int) -> int:
        """Count the number of tokens in the messages."""
        try:
            # 初始化本次请求的 token 计数器为 0
            current_tokens = 0
            # 遍历当前 messages 列表中的每一条消息
            for msg in messages:
                # 累加每条消息预估的 token 数量
                current_tokens += estimate_message_tokens(msg)
                
            # 将本次请求使用的 token 数量累加到总数中
            total_tokens_used += current_tokens
            
            # 将 messages 转换为带缩进的 JSON 字符串，仅用于日志展示（确保中文可读）
            formatted_msgs = json.dumps(messages, indent=2, ensure_ascii=False)
            
            # 打印日志，展示本次和累计使用的 token 数量，并附带完整消息内容
            logger.info(f"{formatted_msgs}\n--- 第{iteration}次请求 (本次 {current_tokens} tokens, 累计 {total_tokens_used} tokens)")
            
            # 返回本次使用的 token 数和累计使用的 token 总数
            return total_tokens_used
        except Exception as e:
            # 如果计算或格式化过程中出现异常，则记录警告日志
            logger.warning("无法计算 tokens 或格式化 messages: {}", e)
            # 发生异常时原样返回传入的 total_tokens_used，当前 token 计为 0
            return total_tokens_used
    
    async def run(self) -> None:
        """Run the agent loop, dispatching messages as tasks to stay responsive to /stop."""
        self._running = True
        await self._connect_mcp()
        logger.info("Agent loop started")

        while self._running:
            try:
                msg = await asyncio.wait_for(self.bus.consume_inbound(), timeout=1.0)
            except asyncio.TimeoutError:
                continue

            if msg.content.strip().lower() == "/stop":
                await self._handle_stop(msg)
            else:
                task = asyncio.create_task(self._dispatch(msg))
                self._active_tasks.setdefault(msg.session_key, []).append(task)
                task.add_done_callback(lambda t, k=msg.session_key: self._active_tasks.get(k, []) and self._active_tasks[k].remove(t) if t in self._active_tasks.get(k, []) else None)

    async def _handle_stop(self, msg: InboundMessage) -> None:
        """Cancel all active tasks and subagents for the session."""
        tasks = self._active_tasks.pop(msg.session_key, [])
        cancelled = sum(1 for t in tasks if not t.done() and t.cancel())
        for t in tasks:
            try:
                await t
            except (asyncio.CancelledError, Exception):
                pass
        sub_cancelled = await self.subagents.cancel_by_session(msg.session_key)
        total = cancelled + sub_cancelled
        content = f"⏹ Stopped {total} task(s)." if total else "No active task to stop."
        await self.bus.publish_outbound(OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=content,
        ))

    async def _dispatch(self, msg: InboundMessage) -> None:
        """Process a message under the global lock."""
        async with self._processing_lock:
            try:
                response = await self._process_message(msg)
                if response is not None:
                    await self.bus.publish_outbound(response)
                elif msg.channel == "cli":
                    await self.bus.publish_outbound(OutboundMessage(
                        channel=msg.channel, chat_id=msg.chat_id,
                        content="", metadata=msg.metadata or {},
                    ))

            except asyncio.CancelledError:
                logger.info("Task cancelled for session {}", msg.session_key)
                raise
            except Exception:
                logger.exception("Error processing message for session {}", msg.session_key)
                await self.bus.publish_outbound(OutboundMessage(
                    channel=msg.channel, chat_id=msg.chat_id,
                    content="Sorry, I encountered an error.",
                ))

    async def close_mcp(self) -> None:
        """Close MCP connections."""
        if self._mcp_stack:
            try:
                await self._mcp_stack.aclose()
            except (RuntimeError, BaseExceptionGroup):
                pass  # MCP SDK cancel scope cleanup is noisy but harmless
            self._mcp_stack = None

    def stop(self) -> None:
        """Stop the agent loop."""
        self._running = False
        logger.info("Agent loop stopping")

    async def _process_message(
        self,
        msg: InboundMessage,
        session_key: str | None = None,
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> OutboundMessage | None:
        """Process a single inbound message and return the response."""
        # System messages: parse origin from chat_id ("channel:chat_id")
        if msg.channel == "system":
            channel, chat_id = (msg.chat_id.split(":", 1) if ":" in msg.chat_id
                                else ("cli", msg.chat_id))
            logger.info("Processing system message from {}", msg.sender_id)
            key = f"{channel}:{chat_id}"
            session = self.sessions.get_or_create(key)
            self._set_tool_context(channel, chat_id, msg.metadata.get("message_id"))
            history = session.get_history(max_messages=0)
            messages = self.context.build_messages(
                history=history,
                current_message=msg.content, channel=channel, chat_id=chat_id,
            )
            final_content, _, all_msgs = await self._run_agent_loop(messages)
            self._save_turn(session, all_msgs, 1 + len(history))
            self.sessions.save(session)
            return OutboundMessage(channel=channel, chat_id=chat_id,
                                  content=final_content or "Background task completed.")

        preview = msg.content[:80] + "..." if len(msg.content) > 80 else msg.content
        logger.info("Processing message from {}:{}: {}", msg.channel, msg.sender_id, preview)

        # Slash commands
        cmd = msg.content.strip().lower()
        if cmd.startswith("/add "):
            # 获取用户要添加的技能名称
            skill_name = msg.content.strip()[5:].strip()
            if not skill_name:
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content="Please provide a skill name: /add {skill_name}")
            
            # 计算 skill-room 的根目录路径
            skill_room_dir = Path.cwd() / "skill-room"
            
            # 初始化目标源路径为空
            skill_source = None
            # 遍历 skill-room 目录下的所有子目录
            if skill_room_dir.exists() and skill_room_dir.is_dir():
                for item in skill_room_dir.iterdir():
                    # 检查是否为目录且名称包含要添加的技能关键字（忽略大小写）
                    if item.is_dir() and skill_name.lower() in item.name.lower():
                        # 找到第一个匹配的目录，将其作为源路径
                        skill_source = item
                        # 更新 skill_name 为实际的完整目录名，以便后续安装路径使用
                        skill_name = item.name
                        break
                        
            # 如果没有找到匹配的目录，返回未找到的提示
            if not skill_source:
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=f"Skill matching '{skill_name}' not found in skill-room")
            # 目标安装路径
            skill_dest = self.workspace / "skills" / skill_name

            try:
                # 拷贝目录及子文件
                shutil.copytree(skill_source, skill_dest, dirs_exist_ok=True)
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=f"{skill_name}技能安装成功")
            except Exception as e:
                logger.error(f"Failed to copy skill {skill_name}: {e}")
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=f"Failed to install skill {skill_name}: {e}")

        if cmd.startswith("/del "):
            # 获取用户要删除的技能关键字
            skill_name = msg.content.strip()[5:].strip()        
            # 如果关键字为空，则返回提示信息要求提供名称
            if not skill_name:
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content="Please provide a skill name to delete: /del {skill_name}")
            
            # 计算当前工作空间下的 skills 目录路径
            skills_dir = self.workspace / "skills"
            
            # 初始化目标删除路径为空
            skill_target = None
            # 遍历 skills 目录下的所有子目录
            if skills_dir.exists() and skills_dir.is_dir():
                for item in skills_dir.iterdir():
                    # 检查是否为目录且名称包含要删除的技能关键字（忽略大小写）
                    if item.is_dir() and skill_name.lower() in item.name.lower():
                        # 找到第一个匹配的目录，将其作为要删除的目标路径
                        skill_target = item
                        # 更新 skill_name 为实际的完整目录名，用于日志和提示信息
                        skill_name = item.name
                        break
            
            # 如果没有找到匹配的目录，返回未找到的提示
            if not skill_target:
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=f"Skill matching '{skill_name}' not found in workspace skills")
            
            try:
                # 使用 shutil.rmtree 删除该目录及其包含的所有子文件和子目录
                shutil.rmtree(skill_target)
                # 返回删除成功的提示信息
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=f"{skill_name}技能卸载成功")
            except Exception as e:
                # 记录删除失败的错误日志
                logger.error(f"Failed to delete skill {skill_name}: {e}")
                # 返回删除失败的提示信息给用户
                return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=f"Failed to delete skill {skill_name}: {e}")
        
        if cmd == "/help":
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id,
                                  content="rio commands:\n/add {skill_name} — Add a skill from skill-room\n/del {skill_name} — Delete a skill from workspace skills")

        if cmd == "/root":
            # 调用私有方法切换工作空间
            self._switch_workspace("root")
            # 构造成功切换工作空间的提示信息
            response_content = f"切换到工作空间: root"            
            # 返回包含成功信息的 OutboundMessage
            return OutboundMessage(channel=msg.channel, chat_id=msg.chat_id, content=response_content)


        # 调用私有方法解析并应用 identity
        self._apply_identity(msg)

        key = session_key or msg.session_key
        session = self.sessions.get_or_create(key)
        self._set_tool_context(msg.channel, msg.chat_id, msg.metadata.get("message_id"))
        # 准备处理消息之前，重置发消息工具的状态
        if message_tool := self.tools.get("message"):
            if isinstance(message_tool, MessageTool):
                message_tool.start_turn()

        history = session.get_history(max_messages=0)
        initial_messages = self.context.build_messages(
            history=history,
            current_message=msg.content,
            media=msg.media if msg.media else None,
            channel=msg.channel, chat_id=msg.chat_id,
        )

        async def _bus_progress(content: str, *, tool_hint: bool = False) -> None:
            meta = dict(msg.metadata or {})
            meta["_progress"] = True
            meta["_tool_hint"] = tool_hint
            await self.bus.publish_outbound(OutboundMessage(
                channel=msg.channel, chat_id=msg.chat_id, content=content, metadata=meta,
            ))

        final_content, _, all_msgs = await self._run_agent_loop(
            initial_messages, on_progress=on_progress or _bus_progress,
        )

        if final_content is None:
            final_content = "I've completed processing but have no response to give."

        self._save_turn(session, all_msgs, 1 + len(history))
        self.sessions.save(session)

        # 定义一个异步后台任务来处理会话的压缩整理，避免阻塞主流程
        async def _background_consolidate(session_obj: Session) -> None:
            # 获取当前消息对应的会话对象专属异步锁
            lock = self.memory_consolidator.get_lock(session_obj.key)
            # 加锁执行会话的压缩整理逻辑
            async with lock:
                # 获取当前所有尚未合并的消息列表
                chunk = session_obj.messages[session_obj.last_consolidated:]
                # 如果未合并的消息数量大于0条，则触发压缩机制
                if len(chunk) > 0:
                    # 调用方法将这部分消息进行归档压缩
                    if await self.memory_consolidator.consolidate_messages(chunk):
                        # 压缩成功后，更新会话的最后合并位置
                        session_obj.last_consolidated += len(chunk)
                        # 将更新后的会话状态持久化保存
                        self.sessions.save(session_obj)

        # 使用 asyncio.create_task 将压缩任务放入后台异步执行
        asyncio.create_task(_background_consolidate(session))

        # 有时候大模型会在执行过程中，**主动调用系统提供的发消息工具（比如 MessageTool ）**来和用户沟通。
        # 如果它已经通过工具把想说的话发给用户了，系统最后再自动打包发一遍 final_content ，用户就会收到两条重复或者矛盾的消息。
        if (mt := self.tools.get("message")) and isinstance(mt, MessageTool) and mt._sent_in_turn:
            return None


        return OutboundMessage(
            channel=msg.channel, chat_id=msg.chat_id, content=final_content,
            metadata=msg.metadata or {},
        )

    def _save_turn(self, session: Session, messages: list[dict], skip: int) -> None:
        """Save new-turn messages into session, truncating large tool results."""
        from datetime import datetime
        for m in messages[skip:]:
            entry = dict(m)
            role, content = entry.get("role"), entry.get("content")
            if role == "assistant" and not content and not entry.get("tool_calls"):
                continue  # skip empty assistant messages — they poison session context
            if role == "tool" and isinstance(content, str) and len(content) > self._TOOL_RESULT_MAX_CHARS:
                entry["content"] = content[:self._TOOL_RESULT_MAX_CHARS] + "\n... (truncated)"
            elif role == "user":
                if isinstance(content, str) and content.startswith(ContextBuilder._RUNTIME_CONTEXT_TAG):
                    # Strip the runtime-context prefix, keep only the user text.
                    parts = content.split("\n\n", 1)
                    if len(parts) > 1 and parts[1].strip():
                        entry["content"] = parts[1]
                    else:
                        continue
                if isinstance(content, list):
                    filtered = []
                    for c in content:
                        if c.get("type") == "text" and isinstance(c.get("text"), str) and c["text"].startswith(ContextBuilder._RUNTIME_CONTEXT_TAG):
                            continue  # Strip runtime context from multimodal messages
                        if (c.get("type") == "image_url"
                                and c.get("image_url", {}).get("url", "").startswith("data:image/")):
                            filtered.append({"type": "text", "text": "[image]"})
                        else:
                            filtered.append(c)
                    if not filtered:
                        continue
                    entry["content"] = filtered
            entry.setdefault("timestamp", datetime.now().isoformat())
            session.messages.append(entry)
        session.updated_at = datetime.now()

    async def process_direct(
        self,
        content: str,
        session_key: str = "cli:direct",
        channel: str = "cli",
        chat_id: str = "direct",
        identity: str = "[root]",
        on_progress: Callable[[str], Awaitable[None]] | None = None,
    ) -> str:
        """Process a message directly (for CLI or cron usage)."""
        await self._connect_mcp()
        msg = InboundMessage(channel=channel, sender_id="user", chat_id=chat_id, content=content, identity=identity)
        response = await self._process_message(msg, session_key=session_key, on_progress=on_progress)
        return response.content if response else ""
