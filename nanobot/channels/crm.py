# 导入 asyncio 模块用于异步操作
import asyncio
# 导入 loguru 的 logger 用于日志记录
from loguru import logger
# 导入 InboundMessage 和 OutboundMessage 事件模型
from nanobot.bus.events import InboundMessage, OutboundMessage
# 导入 MessageBus 消息总线
from nanobot.bus.queue import MessageBus
# 导入 BaseChannel 基类
from nanobot.channels.base import BaseChannel
# 导入 CRM 相关的模型：任务、商机、消息记录和获取数据库会话的方法
from crm.models import get_session, Task, Opportunity, Message
# 导入 pyweixin 中的 Messages 模块用于发送消息
from pyweixin import Messages

# 定义 CRMChannel 类，继承自 BaseChannel
class CRMChannel(BaseChannel):
    # 定义渠道的名称为 crm
    name: str = "crm"

    # 初始化方法，接收配置和消息总线对象
    def __init__(self, config, bus: MessageBus):
        # 调用父类的初始化方法
        super().__init__(config, bus)
        # 初始化轮询任务为空
        self._poll_task = None
        # 初始化一个异步锁，防止多个聊天消息同时操作微信客户端产生冲突错乱
        self._send_lock = asyncio.Lock()

    # 启动渠道的异步方法
    async def start(self) -> None:
        # 将运行状态设置为 True
        self._running = True
        # 创建一个异步任务来运行轮询循环
        self._poll_task = asyncio.create_task(self._poll_loop())
        # 记录启动日志
        logger.info("CRM 渠道已启动，开始每1分钟轮询任务。")

    # 停止渠道的异步方法
    async def stop(self) -> None:
        # 将运行状态设置为 False
        self._running = False
        # 如果轮询任务存在
        if self._poll_task:
            # 取消该异步任务
            self._poll_task.cancel()
            # 记录停止日志
            logger.info("CRM 渠道已停止。")

    # 发送消息的异步方法，接收 OutboundMessage 对象
    async def send(self, msg: OutboundMessage) -> None:

        # 尝试执行发送逻辑
        try:
            # 获取数据库会话对象
            db = get_session()
            # 根据消息中的 chat_id 查询对应的商机（chat_id 存储了商机 ID）
            opp = db.query(Opportunity).filter(Opportunity.id == int(msg.chat_id)).first()
            # 如果成功查询到商机
            if opp:
                # 使用异步锁，保证同一时间只有一个任务能操作微信 UI
                async with self._send_lock:
                    # 由于 send_messages_to_friend 是同步阻塞调用，通过 to_thread 将其放入独立线程执行，防止阻塞主事件循环
                    await asyncio.to_thread(
                        Messages.send_messages_to_friend,
                        friend=opp.name,
                        messages=[msg.content]
                    )
                # 记录发送成功的日志信息
                logger.info(f"成功通过 CRM 渠道发送消息给 {opp.name}")
                
                #更新历史对话记录
                new_message = Message(
                    opportunity_id=opp.id,
                    sender="AI助手",  # 标识这是由系统/机器人发出的消息
                    content=msg.content
                )
                db.add(new_message)                
                # 更新任务的状态和响应内容
                # 查找属于该商机的正在处理中的任务（可能是在轮询时刚刚被设置为 '处理中' 的任务）
                task = db.query(Task).filter(Task.opportunity_id == opp.id, Task.status == '处理中').order_by(Task.created_at.desc()).first()
                if task:
                    task.response = msg.content
                    task.status = '已完成'
                db.commit()
                #更新历史对话记录
                
            # 如果没有找到对应的商机或客户
            else:
                # 记录警告日志
                logger.warning(f"无法发送消息：未找到对应的商机或客户 (ID: {msg.chat_id})")
        # 捕获异常
        except Exception as e:
            # 记录错误日志
            logger.error(f"CRM 渠道发送消息时发生异常: {e}")
        # 无论是否发生异常都执行
        finally:
            # 关闭数据库会话释放资源
            db.close()

    # 内部方法，用于循环轮询数据库中的任务
    async def _poll_loop(self) -> None:
        # 当渠道处于运行状态时不断循环
        while self._running:
            
            # 尝试执行单次轮询逻辑
            try:
                # 获取数据库会话
                db = get_session()
                # 查询状态为 待办中 的任务，按创建时间升序排列并获取第一条（即最远的任务）
                task = db.query(Task).filter(Task.status == '待办中').order_by(Task.created_at.asc()).first()
                # 如果查询到了这样的任务
                if task:
                    # 1. 判断是否为“对话”任务，不是则跳过处理（但仍更新状态）
                    # 2. 判断 opportunity_id 是否存在，不存在则跳过
                    if task.type == '对话' and task.opportunity_id:
                        # 3. 获取关联的商机对象，不存在则跳过
                        opp = db.query(Opportunity).filter(Opportunity.id == task.opportunity_id).first()
                        if opp:
                         
                            # 根据商机 ID 查询最近 50 条历史聊天记录，按时间降序取 50 条，再翻转回升序
                            messages = db.query(Message).filter(Message.opportunity_id == opp.id).order_by(Message.created_at.desc()).limit(50).all()
                            messages.reverse()
                            
                            # 4. 组装客户等级、阶段、备注和聊天记录（如果不为空）
                            content_parts = [f"任务内容: {task.content}"]
                            if opp.contact:
                                content_parts.append(f"客户名称: {opp.contact.name}")
                            if opp.level:
                                content_parts.append(f"客户等级: {opp.level}")
                            if opp.stage:
                                content_parts.append(f"当前阶段: {opp.stage}")
                            if opp.remark:
                                content_parts.append(f"备注: {opp.remark}")
                                
                            if messages:
                                history_str = "\n".join([f"{m.sender}: {m.content}" for m in messages])
                                content_parts.append(f"最近聊天记录:\n{history_str}")
                                
                            # 将所有部分拼接成最终内容
                            content = "\n".join(content_parts)
                            
                            # 构造 InboundMessage 消息对象
                            inbound_msg = InboundMessage(
                                # 设置渠道名称为当前渠道
                                channel=self.name,
                                # 设置发送者 ID，如果客户存在则使用客户名称，否则为 unknown
                                sender_id=str(opp.contact.name) if getattr(opp, 'contact', None) else "unknown",
                                # 设置聊天 ID 为当前商机 ID
                                chat_id=str(opp.id),
                                # 填入刚刚构造好的内容
                                content=content
                            )
                            # 将构造好的消息发送到消息总线
                            await self.bus.publish_inbound(inbound_msg)
                            # 记录日志说明已发送该商机的任务
                            logger.info(f"已向总线发送商机 (ID: {opp.id}) 的对话任务。")
                    # 为了防止任务被重复处理，将任务状态更新为 处理中
                    task.status = '处理中'
                    # 提交数据库事务
                    db.commit()
            # 捕获轮询过程中可能出现的异常
            except Exception as e:
                # 记录轮询任务的错误日志
                logger.error(f"CRM 渠道获取任务时发生异常: {e}")
            # 无论如何都在最后执行
            finally:
                # 判断当前作用域中是否有 db 变量
                if 'db' in locals():
                    # 关闭数据库会话
                    db.close()
            logger.info(f"CRM 渠道轮询任务完成，等待 60 秒后继续下一次轮询")
            # 异步等待 60 秒（即 1分钟）后进行下一次轮询
            await asyncio.sleep(60)
