"""API gateway channel for HTTP-based interactions."""

import asyncio
import uuid
from typing import Any

import uvicorn
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel

from nanobot.bus.events import InboundMessage, OutboundMessage
from nanobot.bus.queue import MessageBus
from nanobot.channels.base import BaseChannel


class ProcessRequest(BaseModel):
    """Request model for /process endpoint."""
    sender_id: str
    content: str
    media: list[str] | None = None
    metadata: dict[str, Any] | None = None


class ProcessResponse(BaseModel):
    """Response model for /process endpoint."""
    content: str
    media: list[str] | None = None
    metadata: dict[str, Any] | None = None


class APIChannel(BaseChannel):
    """
    API Channel implementation.
    
    Provides an HTTP API for programmatic interaction with the bot.
    """

    name: str = "api"

    def __init__(self, config: Any, bus: MessageBus):
        super().__init__(config, bus)
        self.app = FastAPI(title="Nanobot API Channel")
        
        # Add CORS middleware to allow requests from the web UI
        self.app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Allow all origins for the web UI
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        
        self._server: uvicorn.Server | None = None
        self._pending_requests: dict[str, asyncio.Queue[OutboundMessage]] = {}
        self._setup_routes()

    def _setup_routes(self) -> None:
        @self.app.post("/process", response_model=ProcessResponse)
        async def process_message(req: ProcessRequest) -> ProcessResponse:
            if not self.is_allowed(req.sender_id):
                raise HTTPException(status_code=403, detail="Sender not allowed")

            # Create a unique identifier for tracking this request
            session_id = str(uuid.uuid4())
            
            # Create a mailbox (queue) for receiving the response
            mailbox: asyncio.Queue[OutboundMessage] = asyncio.Queue()
            self._pending_requests[session_id] = mailbox
            
            try:
                # Wrap the request into an InboundMessage and publish
                msg = InboundMessage(
                    channel=self.name,
                    sender_id=req.sender_id,
                    chat_id=session_id,  # Use session_id as chat_id so outbound comes back to it
                    content=req.content,
                    media=req.media or [],
                    metadata=req.metadata or {},
                    session_key_override=session_id,
                )
                
                logger.info("API Channel processing request: {} for session: {}", req.content, session_id)
                await self.bus.publish_inbound(msg)
                
                # Wait for the response in our mailbox
                # The agent may send progress messages or tool hints before the final message.
                # We collect all text until a non-progress message arrives.
                final_content = ""
                final_media: list[str] = []
                final_metadata: dict[str, Any] = {}
                
                while True:
                    # Timeout after 5 minutes
                    response = await asyncio.wait_for(mailbox.get(), timeout=300.0)
                    
                    if response.metadata and response.metadata.get("_progress"):
                        # Ignore progress messages for synchronous API
                        continue
                        
                    final_content = response.content
                    final_media = response.media
                    final_metadata = response.metadata
                    break
                    
                return ProcessResponse(
                    content=final_content,
                    media=final_media,
                    metadata=final_metadata,
                )
                
            except asyncio.TimeoutError:
                raise HTTPException(status_code=504, detail="Request timed out")
            finally:
                # Clean up the listener mailbox
                self._pending_requests.pop(session_id, None)

    async def start(self) -> None:
        """Start the uvicorn server."""
        self._running = True
        
        host = getattr(self.config, "host", "127.0.0.1")
        port = getattr(self.config, "port", 8000)
        
        config = uvicorn.Config(
            app=self.app,
            host=host,
            port=port,
            log_level="warning",
        )
        self._server = uvicorn.Server(config)
        
        logger.info("Starting API Channel server on {}:{}", host, port)
        await self._server.serve()

    async def stop(self) -> None:
        """Stop the uvicorn server."""
        self._running = False
        if self._server:
            self._server.should_exit = True
            
    async def send(self, msg: OutboundMessage) -> None:
        """
        Receive an outbound message and route it to the correct mailbox.
        """
        # The agent sets chat_id to the session_id we provided in InboundMessage
        session_id = msg.chat_id
        
        if session_id in self._pending_requests:
            mailbox = self._pending_requests[session_id]
            await mailbox.put(msg)
        else:
            logger.warning("API Channel received message for unknown session: {}", session_id)
