"""
WebSocket ASR Push-to-Talk Test

Usage:
    pip install pyaudio websockets keyboard
    python tests/test_ws_ptt.py [--host localhost] [--port 8000]

Hold SPACE to record, release to send.
Audio is auto-sent every 3 seconds while holding.
"""

if __name__ != "__main__":
    # This file is an interactive script, not a unit test. Avoid failing pytest
    # collection when optional deps (pyaudio/keyboard) are missing.
    import pytest

    pytest.skip("interactive push-to-talk script (skipped during pytest)", allow_module_level=True)

import asyncio
import argparse
import json
import base64
import sys
import threading
import time

try:
    import pyaudio
except ImportError:
    print("Error: pyaudio not installed")
    print("Install with: pip install pyaudio")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("Error: websockets not installed")
    print("Install with: pip install websockets")
    sys.exit(1)

try:
    import keyboard
except ImportError:
    print("Error: keyboard not installed")
    print("Install with: pip install keyboard")
    print("Note: On Linux, you may need to run as root")
    sys.exit(1)


# Audio settings
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = 1024  # Larger chunks for PTT mode
CHUNK_DURATION_SEC = 3.0  # Send every 3 seconds
MIN_RECORDING_SEC = 0.5   # Minimum recording duration to send


class PTTStreamer:
    def __init__(self, host: str, port: int, device_index: int = None):
        self.uri = f"ws://{host}:{port}/ws"
        self.device_index = device_index
        self.ws = None
        self.audio = None
        self.stream = None
        self.running = True
        self.recording = False
        self.audio_buffer = b""
        self.seq = 0
        self.lock = threading.Lock()
        self.record_start_time = 0

    async def connect(self):
        """Connect to WebSocket server."""
        print(f"Connecting to {self.uri}...")
        self.ws = await websockets.connect(self.uri)
        response = await self.ws.recv()
        msg = json.loads(response)
        print(f"Server: {msg.get('data', {}).get('message', 'Connected')}")

    def init_audio(self):
        """Initialize PyAudio."""
        self.audio = pyaudio.PyAudio()

        # List input devices
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        print("\nAvailable input devices:")
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  [{i}] {device_info.get('name')}")

        if self.device_index is not None:
            print(f"\nUsing device index: {self.device_index}")
        else:
            print(f"\nUsing default input device")

    def start_recording(self):
        """Start recording audio."""
        if self.recording:
            return

        with self.lock:
            self.recording = True
            self.audio_buffer = b""
            self.record_start_time = time.time()

        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input=True,
            input_device_index=self.device_index,
            frames_per_buffer=CHUNK_SIZE
        )
        print("\n[REC] Recording started...")

    def stop_recording(self):
        """Stop recording and return buffered audio."""
        if not self.recording:
            return None

        with self.lock:
            self.recording = False
            buffer = self.audio_buffer
            self.audio_buffer = b""

        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
            self.stream = None

        duration = len(buffer) / (SAMPLE_RATE * 2)  # 2 bytes per sample
        print(f"[STOP] Recording stopped ({duration:.2f}s)")
        return buffer

    def read_audio_chunk(self):
        """Read audio from stream and add to buffer."""
        if not self.recording or not self.stream:
            return None

        try:
            data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
            with self.lock:
                self.audio_buffer += data

            # Check if 3 seconds reached
            elapsed = time.time() - self.record_start_time
            if elapsed >= CHUNK_DURATION_SEC:
                with self.lock:
                    buffer = self.audio_buffer
                    self.audio_buffer = b""
                    self.record_start_time = time.time()
                return ("chunk", buffer)

            return None
        except Exception as e:
            print(f"Audio read error: {e}")
            return None

    async def send_audio(self, audio_data: bytes, is_final: bool):
        """Send audio to server."""
        if not audio_data or len(audio_data) < 100:
            # Still send is_final signal if needed (empty audio)
            if is_final:
                self.seq += 1
                message = {
                    "type": "audio_chunk",
                    "data": {
                        "audio": "",
                        "seq": self.seq,
                        "is_final": True
                    }
                }
                await self.ws.send(json.dumps(message))
                print(f"[SEND] FINAL signal (no audio)")
            return

        duration = len(audio_data) / (SAMPLE_RATE * 2)

        # Skip audio if recording is too short (causes Whisper hallucination)
        # But still send is_final signal to complete the session
        if is_final and duration < MIN_RECORDING_SEC:
            print(f"[SKIP] Audio too short ({duration:.2f}s < {MIN_RECORDING_SEC}s), sending final signal only")
            self.seq += 1
            message = {
                "type": "audio_chunk",
                "data": {
                    "audio": "",
                    "seq": self.seq,
                    "is_final": True
                }
            }
            await self.ws.send(json.dumps(message))
            return

        self.seq += 1

        message = {
            "type": "audio_chunk",
            "data": {
                "audio": base64.b64encode(audio_data).decode("ascii"),
                "seq": self.seq,
                "is_final": is_final
            }
        }

        await self.ws.send(json.dumps(message))
        status = "FINAL" if is_final else "PARTIAL"
        print(f"[SEND] {status} chunk #{self.seq} ({duration:.2f}s, {len(audio_data)} bytes)")

    async def receive_messages(self):
        """Background task to receive server messages."""
        try:
            async for message in self.ws:
                msg = json.loads(message)
                msg_type = msg.get("type")
                data = msg.get("data", {})

                if msg_type == "asr_result":
                    text = data.get("text", "")
                    is_final = data.get("is_final", False)
                    confidence = data.get("confidence", 0)

                    prefix = "[FINAL]" if is_final else "[PARTIAL]"
                    print(f"\n{prefix} {text} (conf={confidence:.2f})")

                elif msg_type == "tool_calls":
                    # LLM이 생성한 MCP 명령 출력
                    commands = data.get("commands", [])
                    print(f"\n[LLM] 명령 {len(commands)}개 생성:")
                    for i, cmd in enumerate(commands, 1):
                        tool = cmd.get("tool_name", "")
                        args = cmd.get("arguments", {})
                        desc = cmd.get("description", "")
                        print(f"  [{i}] {tool}: {args}")
                        if desc:
                            print(f"      → {desc}")

                elif msg_type == "flow_step":
                    # Flow 단계 안내
                    prompt = data.get("prompt", "")
                    step_id = data.get("step_id", "")
                    print(f"\n[FLOW] {step_id}: {prompt}")

                elif msg_type == "tts_chunk":
                    # TTS 응답 (오디오 데이터는 생략, 상태만 출력)
                    is_final = data.get("is_final", False)
                    if is_final:
                        print("\n[TTS] 응답 완료")

                elif msg_type == "error":
                    print(f"\n[ERROR] {data.get('error', '')}")

        except websockets.ConnectionClosed:
            print("\nConnection closed")
        except asyncio.CancelledError:
            pass

    async def run(self):
        """Main loop."""
        await self.connect()
        self.init_audio()

        print("\n" + "=" * 60)
        print("Push-to-Talk Mode")
        print("  - Hold SPACE to record")
        print("  - Release SPACE to send")
        print("  - Auto-sends every 3 seconds while holding")
        print("  - Press ESC to quit")
        print("=" * 60 + "\n")

        # Start receiver task
        receiver = asyncio.create_task(self.receive_messages())

        # Keyboard event handlers
        space_pressed = False
        interrupt_requested = False

        def on_space_press(e):
            nonlocal space_pressed
            nonlocal interrupt_requested
            if not space_pressed:
                space_pressed = True
                interrupt_requested = True
                self.start_recording()

        def on_space_release(e):
            nonlocal space_pressed
            space_pressed = False

        keyboard.on_press_key("space", on_space_press)
        keyboard.on_release_key("space", on_space_release)

        try:
            while self.running:
                if keyboard.is_pressed("esc"):
                    print("\n[EXIT] ESC pressed")
                    break

                # Handle recording
                if self.recording:
                    result = self.read_audio_chunk()
                    if result and result[0] == "chunk":
                        # 3 seconds reached, send partial
                        await self.send_audio(result[1], is_final=False)

                # Interrupt current TTS/logic on space press (barge-in)
                if interrupt_requested:
                    interrupt_requested = False
                    message = {
                        "type": "interrupt",
                        "data": {}
                    }
                    await self.ws.send(json.dumps(message))

                # Check if space was released
                if not space_pressed and not self.recording:
                    pass
                elif not space_pressed and self.recording:
                    # Space released, send final
                    buffer = self.stop_recording()
                    if buffer:
                        await self.send_audio(buffer, is_final=True)

                await asyncio.sleep(0.01)

        except Exception as e:
            print(f"Error: {e}")
        finally:
            keyboard.unhook_all()
            receiver.cancel()
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            if self.audio:
                self.audio.terminate()
            if self.ws:
                await self.ws.close()


async def main():
    parser = argparse.ArgumentParser(description="WebSocket ASR Push-to-Talk Test")
    parser.add_argument("--host", default="localhost", help="Server host")
    parser.add_argument("--port", type=int, default=8000, help="Server port")
    parser.add_argument("--device", type=int, default=None, help="Input device index")
    args = parser.parse_args()

    streamer = PTTStreamer(args.host, args.port, args.device)
    await streamer.run()


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket ASR Push-to-Talk Test")
    print("=" * 60)

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")

    print("\nDone!")
