"""
WebSocket Text Input Test

Usage:
    pip install websockets
    python tests/test_ws_simple.py [--host localhost] [--port 8000]

Type messages in the terminal and send them as user_input events.
"""

import asyncio
import argparse
import json
import sys

try:
    import websockets
except ImportError:
    print("Error: websockets not installed. Run: pip install websockets")
    sys.exit(1)


async def interactive_text(host: str, port: int):
    """Interactive text input test."""
    uri = f"ws://{host}:{port}/ws"

    print(f"Connecting to {uri}...")

    async with websockets.connect(uri) as ws:
        try:
            response = await asyncio.wait_for(ws.recv(), timeout=5.0)
            msg = json.loads(response)
            print(f"[server] {msg.get('type')} - {msg.get('data', {}).get('message', '')}")
        except Exception:
            pass

        stop_event = asyncio.Event()

        async def receiver():
            try:
                while not stop_event.is_set():
                    response = await ws.recv()
                    msg = json.loads(response)
                    msg_type = msg.get("type")
                    data = msg.get("data", {})

                    if msg_type == "tool_calls":
                        cmds = data.get("commands", [])
                        print(f"[tool_calls] {len(cmds)} command(s)")
                    elif msg_type == "tts_chunk":
                        audio_hex = data.get("audio", "")
                        print(f"[tts_chunk] {len(audio_hex)//2} bytes (final={data.get('is_final', False)})")
                    else:
                        print(f"[{msg_type}] {data}")
            except asyncio.CancelledError:
                pass
            except Exception as e:
                print(f"[receiver] error: {e}")

        recv_task = asyncio.create_task(receiver())

        print("Type message and press Enter. Use /quit to exit.")
        try:
            while True:
                text = await asyncio.to_thread(input, "> ")
                if not text:
                    continue
                if text.strip() in ("/quit", "/exit"):
                    break

                message = {"type": "user_input", "data": {"text": text}}
                await ws.send(json.dumps(message))
        finally:
            stop_event.set()
            recv_task.cancel()
            try:
                await recv_task
            except asyncio.CancelledError:
                pass


async def main():
    parser = argparse.ArgumentParser(description="WebSocket Text Input Test")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    args = parser.parse_args()

    await interactive_text(args.host, args.port)


if __name__ == "__main__":
    asyncio.run(main())
