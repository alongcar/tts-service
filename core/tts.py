import pyttsx3
import warnings
import threading
import tempfile
import os
from io import BytesIO
import base64
import json
import asyncio
import logging
from typing import AsyncGenerator, Dict, Any
from config.settings import settings

warnings.filterwarnings("ignore", category=DeprecationWarning)


class SpeechSynthesizer:
    def __init__(self, rate=settings.RATE, volume=settings.VOLUME, voice_index=settings.VOICE_INDEX):
        self.rate = rate
        self.volume = volume
        self.voice_index = voice_index
        self.lock = threading.Lock()
        self.logger = logging.getLogger(__name__)
        self._init_engine()

    def _init_engine(self):
        """初始化语音合成引擎"""
        try:
            self.engine = pyttsx3.init()
            self.engine.setProperty('rate', self.rate)
            self.engine.setProperty('volume', self.volume)

            # 设置语音
            voices = self.engine.getProperty('voices')
            if voices and len(voices) > self.voice_index:
                self.engine.setProperty('voice', voices[self.voice_index].id)

            self.logger.info("✓ 语音合成器初始化完成")
            self.logger.info(f"可用语音数量: {len(voices)}")
            for i, voice in enumerate(voices):
                self.logger.info(f"语音 {i}: {voice.name}")

        except Exception as e:
            self.logger.error(f"❌ 语音合成器初始化失败: {e}")
            raise

    async def text_to_speech_stream(self, text: str, chunk_size=settings.CHUNK_SIZE) -> AsyncGenerator[bytes, None]:
        """
        异步流式语音合成
        Args:
            text: 要合成的文本
            chunk_size: 流式输出块大小
        Yields:
            音频数据块（bytes）
        """
        if not text or len(text.strip()) < 1:
            yield b""
            return

        temp_file = None
        temp_filename = None

        try:
            # 创建临时文件
            with tempfile.NamedTemporaryFile(suffix='.wav', delete=False) as temp_file:
                temp_filename = temp_file.name

            self.logger.info(f"🎵 开始合成语音，文本长度: {len(text)} 字符")

            # 在线程中执行阻塞的合成操作
            def synthesize():
                with self.lock:
                    try:
                        engine = pyttsx3.init()
                        engine.setProperty('rate', self.rate)
                        engine.setProperty('volume', self.volume)

                        voices = engine.getProperty('voices')
                        if voices and len(voices) > self.voice_index:
                            engine.setProperty('voice', voices[self.voice_index].id)

                        engine.save_to_file(text, temp_filename)
                        engine.runAndWait()
                    except Exception as e:
                        self.logger.error(f"合成过程中出错: {e}")

            # 在线程池中执行合成
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, synthesize)

            # 流式读取音频文件
            if os.path.exists(temp_filename):
                with open(temp_filename, 'rb') as f:
                    while True:
                        chunk = f.read(chunk_size)
                        if not chunk:
                            break
                        yield chunk

                self.logger.info("✅ 语音合成完成")
            else:
                self.logger.error("❌ 临时音频文件未生成")
                yield b""

        except Exception as e:
            self.logger.error(f"❌ 语音合成过程中出错: {e}")
            yield b""
        finally:
            # 清理临时文件
            if temp_filename and os.path.exists(temp_filename):
                try:
                    os.unlink(temp_filename)
                except Exception as e:
                    self.logger.warning(f"清理临时文件失败: {e}")

    async def synthesize_and_stream(self, websocket, text: str, request_id: str):
        """
        合成语音并流式传输到WebSocket
        Args:
            websocket: WebSocket连接
            text: 要合成的文本
            request_id: 请求ID用于跟踪
        """
        try:
            # 发送开始消息
            start_message = {
                "type": "synthesis_start",
                "request_id": request_id,
                "text_length": len(text),
                "timestamp": asyncio.get_event_loop().time()
            }
            await websocket.send(json.dumps(start_message))

            total_size = 0
            chunk_index = 0

            # 流式合成和发送音频
            async for audio_chunk in self.text_to_speech_stream(text):
                if not audio_chunk:
                    continue

                chunk_index += 1
                total_size += len(audio_chunk)

                # 编码音频数据
                audio_base64 = base64.b64encode(audio_chunk).decode('utf-8')

                # 发送音频块
                chunk_message = {
                    "type": "audio_chunk",
                    "request_id": request_id,
                    "chunk_index": chunk_index,
                    "audio_data": audio_base64,
                    "chunk_size": len(audio_chunk),
                    "total_size": total_size,
                    "is_final": False
                }
                await websocket.send(json.dumps(chunk_message))
                await asyncio.sleep(0.001)  # 小延迟避免发送过快

            # 发送结束消息
            end_message = {
                "type": "synthesis_complete",
                "request_id": request_id,
                "total_chunks": chunk_index,
                "total_size": total_size,
                "timestamp": asyncio.get_event_loop().time()
            }
            await websocket.send(json.dumps(end_message))

            self.logger.info(f"✅ 语音流式发送完成，请求ID: {request_id}, 总大小: {total_size} 字节")

        except Exception as e:
            self.logger.error(f"❌ 流式音频发送失败: {e}")
            error_message = {
                "type": "error",
                "request_id": request_id,
                "message": f"音频流发送失败: {str(e)}",
                "timestamp": asyncio.get_event_loop().time()
            }
            await websocket.send(json.dumps(error_message))

    def get_voice_info(self) -> Dict[str, Any]:
        """获取语音合成器信息"""
        voices = self.engine.getProperty('voices')
        current_voice = voices[self.voice_index] if voices and len(voices) > self.voice_index else None

        return {
            "rate": self.rate,
            "volume": self.volume,
            "voice_index": self.voice_index,
            "current_voice": current_voice.name if current_voice else "Unknown",
            "available_voices": len(voices),
            "voices": [{"id": i, "name": v.name} for i, v in enumerate(voices)]
        }

    def stop(self):
        """停止语音合成器"""
        try:
            self.engine.stop()
            self.logger.info("语音合成器已停止")
        except:
            pass