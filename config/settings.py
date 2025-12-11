import os
from dataclasses import dataclass

@dataclass
class TTSSettings:
    """TTS服务配置"""
    HOST: str = "0.0.0.0"
    PORT: int = 8765
    RATE: int = 150
    VOLUME: float = 0.9
    VOICE_INDEX: int = 0
    CHUNK_SIZE: int = 4096
    MAX_MESSAGE_SIZE: int = 10 * 1024 * 1024  # 10MB

# 全局配置实例
settings = TTSSettings()