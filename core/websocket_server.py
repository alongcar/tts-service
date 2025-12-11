import asyncio
import websockets
import json
import logging
import uuid
from typing import Dict, Any
from config.settings import settings
from core.tts import SpeechSynthesizer


class TTSWebSocketServer:
    def __init__(self):
        self.tts_engine = SpeechSynthesizer()
        self.logger = logging.getLogger(__name__)
        self.active_connections: Dict[str, Any] = {}

    async def handle_connection(self, websocket, path):
        """处理WebSocket连接"""
        connection_id = str(uuid.uuid4())
        self.active_connections[connection_id] = {
            'websocket': websocket,
            'connected_at': asyncio.get_event_loop().time()
        }

        self.logger.info(f"新的WebSocket连接: {connection_id}")

        try:
            await self._send_welcome_message(websocket, connection_id)

            async for message in websocket:
                await self._handle_message(websocket, message, connection_id)

        except websockets.exceptions.ConnectionClosed:
            self.logger.info(f"WebSocket连接关闭: {connection_id}")
        except Exception as e:
            self.logger.error(f"处理连接时出错: {e}")
        finally:
            if connection_id in self.active_connections:
                del self.active_connections[connection_id]
            self.logger.info(f"连接清理完成: {connection_id}")

    async def _send_welcome_message(self, websocket, connection_id):
        """发送欢迎消息和服务器信息"""
        welcome_msg = {
            "type": "welcome",
            "connection_id": connection_id,
            "service": "流式语音合成服务",
            "version": "1.0.0",
            "supported_formats": ["wav"],
            "voice_info": self.tts_engine.get_voice_info(),
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send(json.dumps(welcome_msg))

    async def _handle_message(self, websocket, message: str, connection_id: str):
        """处理接收到的消息"""
        try:
            data = json.loads(message)
            message_type = data.get('type', '')
            request_id = data.get('request_id', str(uuid.uuid4()))
            text = data.get('text', '')

            if message_type == 'synthesize':
                await self._handle_synthesis_request(websocket, text, request_id)
            elif message_type == 'get_voices':
                await self._send_voice_info(websocket, request_id)
            elif message_type == 'ping':
                await self._send_pong(websocket, request_id)
            else:
                await self._send_error(websocket, f"未知的消息类型: {message_type}", request_id)

        except json.JSONDecodeError:
            await self._send_error(websocket, "无效的JSON格式", "invalid")
        except Exception as e:
            self.logger.error(f"处理消息时出错: {e}")
            await self._send_error(websocket, str(e), "error")

    async def _handle_synthesis_request(self, websocket, text: str, request_id: str):
        """处理语音合成请求"""
        if not text or len(text.strip()) == 0:
            await self._send_error(websocket, "文本内容不能为空", request_id)
            return

        if len(text) > 10000:  # 限制文本长度
            await self._send_error(websocket, "文本长度超过限制(10000字符)", request_id)
            return

        self.logger.info(f"开始处理合成请求: {request_id}, 文本长度: {len(text)}")
        await self.tts_engine.synthesize_and_stream(websocket, text, request_id)

    async def _send_voice_info(self, websocket, request_id: str):
        """发送语音信息"""
        voice_info = self.tts_engine.get_voice_info()
        response = {
            "type": "voice_info",
            "request_id": request_id,
            "data": voice_info,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send(json.dumps(response))

    async def _send_pong(self, websocket, request_id: str):
        """响应ping消息"""
        response = {
            "type": "pong",
            "request_id": request_id,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send(json.dumps(response))

    async def _send_error(self, websocket, message: str, request_id: str):
        """发送错误消息"""
        error_msg = {
            "type": "error",
            "request_id": request_id,
            "message": message,
            "timestamp": asyncio.get_event_loop().time()
        }
        await websocket.send(json.dumps(error_msg))

    async def start_server(self):
        """启动WebSocket服务器"""
        self.logger.info(f"启动TTS WebSocket服务器: {settings.HOST}:{settings.PORT}")

        async with websockets.serve(
                self.handle_connection,
                settings.HOST,
                settings.PORT,
                max_size=settings.MAX_MESSAGE_SIZE
        ):
            self.logger.info("TTS服务器已启动，等待连接...")
            await asyncio.Future()  # 永久运行

    def stop_server(self):
        """停止服务器"""
        self.tts_engine.stop()
        self.logger.info("TTS服务器已停止")