# clients/python_client.py
import asyncio
import websockets
import json


async def test_tts_service():
    uri = "ws://localhost:8765"

    async with websockets.connect(uri) as websocket:
        # 接收欢迎消息
        welcome = await websocket.recv()
        print("服务端响应:", welcome)

        # 发送合成请求
        request = {
            "type": "synthesize",
            "request_id": "test_001",
            "text": "这是一个测试文本，用于验证语音合成服务是否正常工作。"
        }

        await websocket.send(json.dumps(request))
        print("已发送合成请求")

        # 接收响应
        async for message in websocket:
            data = json.loads(message)
            print(f"收到消息类型: {data['type']}")

            if data['type'] == 'synthesis_complete':
                print("合成完成!")
                break


if __name__ == "__main__":
    asyncio.run(test_tts_service())