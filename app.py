# app.py (修改后的版本)
import asyncio
import logging
import signal
import sys
import platform  # 新增：用于判断操作系统
from core.websocket_server import TTSWebSocketServer
from config.settings import settings

# 配置日志 - 修复编码问题
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        # 使用支持UTF-8编码的StreamHandler，避免Windows命令行GBK编码问题
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('tts_service.log', encoding='utf-8')  # 确保日志文件也是UTF-8
    ]
)

logger = logging.getLogger(__name__)


class TTSService:
    def __init__(self):
        self.server = TTSWebSocketServer()
        self.is_running = False

    async def run(self):
        """运行TTS服务"""
        self.is_running = True

        # 修复信号处理：Windows兼容方案
        if platform.system() == 'Windows':
            # Windows平台使用signal.signal
            signal.signal(signal.SIGINT, self._windows_signal_handler)
            signal.signal(signal.SIGTERM, self._windows_signal_handler)
            logger.info("已注册Windows平台的信号处理器")
        else:
            # Unix/Linux/macOS平台使用原有的add_signal_handler
            loop = asyncio.get_event_loop()
            for sig in [signal.SIGINT, signal.SIGTERM]:
                try:
                    loop.add_signal_handler(sig, self.graceful_shutdown)
                    logger.info(f"已注册信号处理器: {sig}")
                except NotImplementedError:
                    logger.warning(f"信号 {sig} 注册失败，当前平台可能不支持")

        try:
            await self.server.start_server()
        except KeyboardInterrupt:
            self.graceful_shutdown()
        except Exception as e:
            logger.error(f"服务器运行错误: {e}")
        finally:
            self.is_running = False

    def _windows_signal_handler(self, signum, frame):
        """Windows平台的信号处理函数"""
        logger.info(f"Windows系统接收到信号: {signum}")
        self.graceful_shutdown()

    def graceful_shutdown(self, signum=None, frame=None):
        """优雅关闭服务器 (兼容Unix和Windows的信号参数)"""
        if self.is_running:
            logger.info("正在关闭TTS服务...")
            self.server.stop_server()
            self.is_running = False
            # 如果是Windows，可能需要直接退出
            if platform.system() == 'Windows':
                sys.exit(0)
            # 对于Unix系统，loop.run_forever()会在loop.stop()后自然退出


def main():
    """主函数"""
    print("=" * 50)
    print("   流式语音合成服务 (TTS WebSocket Server)")
    print("=" * 50)
    print(f"服务地址: ws://{settings.HOST}:{settings.PORT}")
    print(f"音频格式: WAV")
    print(f"合成参数: 语速={settings.RATE}, 音量={settings.VOLUME}")
    print(f"运行平台: {platform.system()} {platform.release()}")
    print("=" * 50)

    service = TTSService()

    try:
        asyncio.run(service.run())
    except KeyboardInterrupt:
        logger.info("接收到键盘中断，服务即将关闭")
        service.graceful_shutdown()


if __name__ == "__main__":
    main()