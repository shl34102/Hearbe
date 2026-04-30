"""
Scripted WebSocket text test (no ASR).

Usage:
  python tests/test_ws_scripted.py --host localhost --port 8000 --delay 12
"""

import argparse
import asyncio
import json
import uuid
from typing import List

try:
    import websockets
    from websockets.exceptions import ConnectionClosed
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    raise SystemExit(1)


DEFAULT_MESSAGES = [
    "쿠팡 접속",
    "생수 검색해줘",
    "검색 결과 읽어줘",
    "첫 번째 상품 선택",
    "상품 정보 읽어줘",
    "이 상품 장바구니에 담아",
]


async def run(host: str, port: int, messages: List[str], delay: float, reconnects: int) -> None:
    session_id = str(uuid.uuid4())
    uri = f"ws://{host}:{port}/ws/{session_id}"
    print(f"Connecting to {uri}...")

    msg_index = 0
    attempt = 0

    while msg_index < len(messages):
        if attempt > reconnects:
            print("Reconnect limit reached. Exiting.")
            return

        try:
            async with websockets.connect(uri, open_timeout=15, close_timeout=5) as ws:
                stop_event = asyncio.Event()

                async def receiver() -> None:
                    try:
                        while not stop_event.is_set():
                            msg = await ws.recv()
                            data = json.loads(msg)
                            mtype = data.get("type")
                            payload = data.get("data", {})
                            if mtype == "tool_calls":
                                cmds = payload.get("commands", [])
                                print(f"[tool_calls] {len(cmds)} command(s)")
                            elif mtype == "tts_chunk":
                                print(
                                    f"[tts_chunk] final={payload.get('is_final', False)} bytes={len(payload.get('audio',''))//2}"
                                )
                            else:
                                print(f"[{mtype}] {payload}")
                    except Exception as e:
                        print(f"[receiver] {e}")

                recv_task = asyncio.create_task(receiver())

                while msg_index < len(messages):
                    text = messages[msg_index]
                    print(f"\n>> {text}")
                    await ws.send(json.dumps({"type": "user_input", "data": {"text": text}}))
                    msg_index += 1
                    await asyncio.sleep(delay)

                await asyncio.sleep(3)
                stop_event.set()
                recv_task.cancel()
                try:
                    await recv_task
                except asyncio.CancelledError:
                    pass

        except ConnectionClosed as e:
            attempt += 1
            print(f"[reconnect] {e} (attempt {attempt}/{reconnects})")
            await asyncio.sleep(2)
            continue
        except TimeoutError as e:
            attempt += 1
            print(f"[reconnect] handshake timeout (attempt {attempt}/{reconnects})")
            await asyncio.sleep(2)
            continue


def main() -> None:
    parser = argparse.ArgumentParser(description="Scripted WebSocket text test")
    parser.add_argument("--host", default="localhost")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--delay", type=float, default=12.0)
    parser.add_argument("--reconnects", type=int, default=3)
    parser.add_argument("--messages", nargs="*", default=None)
    args = parser.parse_args()

    messages = args.messages if args.messages else DEFAULT_MESSAGES
    asyncio.run(run(args.host, args.port, messages, args.delay, args.reconnects))


if __name__ == "__main__":
    main()
