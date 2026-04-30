"""
WebSocket ASR Microphone Test

Usage:
    pip install pyaudio websockets
    python tests/test_ws_mic.py [--host localhost] [--port 8000]

Records audio from microphone and streams to WebSocket server.
Press Ctrl+C to stop recording and get final result.
"""

if __name__ != "__main__":
    # This file is an interactive script, not a unit test. Avoid failing pytest
    # collection when optional audio deps (pyaudio) are missing.
    import pytest

    pytest.skip("interactive microphone script (skipped during pytest)", allow_module_level=True)

import asyncio
import argparse
import json
import base64
import sys
import signal
import struct
import math

try:
    import pyaudio
except ImportError:
    print("Error: pyaudio not installed")
    print("Install with: pip install pyaudio")
    print("On Windows, you may need: pip install pipwin && pipwin install pyaudio")
    sys.exit(1)

try:
    import websockets
except ImportError:
    print("Error: websockets not installed")
    print("Install with: pip install websockets")
    sys.exit(1)


# Audio settings (must match server expectations)
SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = 320  # 20ms @ 16kHz (as per WEBSOCKET_STREAMING_ARCHITECTURE.md)
CHUNK_BYTES = CHUNK_SIZE * 2  # 16-bit = 2 bytes per sample


def calculate_rms(audio_data: bytes) -> float:
    """Calculate RMS energy of PCM16 audio"""
    if len(audio_data) < 2:
        return 0.0
    num_samples = len(audio_data) // 2
    samples = struct.unpack(f"<{num_samples}h", audio_data[:num_samples * 2])
    sum_squares = sum(s * s for s in samples)
    return math.sqrt(sum_squares / num_samples) if num_samples > 0 else 0.0


class MicrophoneStreamer:
    def __init__(self, host: str, port: int, device_index: int = None):
        self.uri = f"ws://{host}:{port}/ws"
        self.running = False
        self.ws = None
        self.audio = None
        self.stream = None
        self.seq = 0
        self.device_index = device_index
        self.rms_buffer = []  # For averaging RMS over 1 second

    async def connect(self):
        """Connect to WebSocket server."""
        print(f"Connecting to {self.uri}...")
        self.ws = await websockets.connect(self.uri)

        # Wait for connection confirmation
        response = await self.ws.recv()
        msg = json.loads(response)
        print(f"Server response: {msg['type']} - {msg.get('data', {}).get('message', '')}")

    def init_audio(self):
        """Initialize PyAudio stream."""
        self.audio = pyaudio.PyAudio()

        # Find input device
        info = self.audio.get_host_api_info_by_index(0)
        num_devices = info.get('deviceCount')

        print("\nAvailable input devices:")
        for i in range(num_devices):
            device_info = self.audio.get_device_info_by_host_api_device_index(0, i)
            if device_info.get('maxInputChannels') > 0:
                print(f"  [{i}] {device_info.get('name')}")

        # Select device
        if self.device_index is not None:
            print(f"\nUsing device index: {self.device_index}")
        else:
            print(f"\nUsing default input device (index=None)")

        print(f"Sample rate: {SAMPLE_RATE} Hz")
        print(f"Chunk size: {CHUNK_SIZE} samples ({CHUNK_SIZE * 1000 // SAMPLE_RATE}ms)")
        print()

        self.stream = self.audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=SAMPLE_RATE,
            input_device_index=self.device_index,
            input=True,
            frames_per_buffer=CHUNK_SIZE
        )

    async def receive_messages(self):
        """Background task to receive and print server messages."""
        try:
            async for message in self.ws:
                msg = json.loads(message)
                msg_type = msg.get("type")
                data = msg.get("data", {})

                if msg_type == "asr_result":
                    text = data.get("text", "")
                    is_final = data.get("is_final", False)
                    confidence = data.get("confidence", 0)
                    duration = data.get("duration", 0)
                    segment_id = data.get("segment_id", "")

                    prefix = "[FINAL]" if is_final else "[PARTIAL]"
                    print(f"\n{prefix} {text}")
                    print(f"         (confidence={confidence:.2f}, duration={duration:.2f}s, segment={segment_id})")

                elif msg_type == "status":
                    print(f"[STATUS] {data.get('message', '')}")

                elif msg_type == "error":
                    print(f"[ERROR] {data.get('error', '')}")

                else:
                    print(f"[{msg_type}] {data}")

        except websockets.ConnectionClosed:
            print("\nConnection closed by server")
        except asyncio.CancelledError:
            pass

    async def stream_audio(self):
        """Stream audio from microphone to server."""
        print("=" * 60)
        print("Recording... Speak into your microphone!")
        print("Press Ctrl+C to stop and get final result")
        print("=" * 60)
        print()
        print("RMS Guide: ~50-150 silence | ~200-500 soft speech | ~500-2000 normal | 2000+ loud")
        print()

        self.running = True
        chunks_per_second = 50  # 20ms * 50 = 1 second

        try:
            while self.running:
                # Read audio chunk (blocking but fast)
                try:
                    audio_data = self.stream.read(CHUNK_SIZE, exception_on_overflow=False)
                except Exception as e:
                    print(f"Audio read error: {e}")
                    continue

                self.seq += 1

                # Calculate and display RMS
                rms = calculate_rms(audio_data)
                self.rms_buffer.append(rms)

                # Display RMS meter every 1 second (50 chunks)
                if len(self.rms_buffer) >= chunks_per_second:
                    avg_rms = sum(self.rms_buffer) / len(self.rms_buffer)
                    max_rms = max(self.rms_buffer)
                    # Visual bar (scale: 0-3000 -> 0-30 chars)
                    bar_len = min(int(avg_rms / 100), 30)
                    bar = "#" * bar_len + "-" * (30 - bar_len)
                    print(f"\r[RMS] avg={avg_rms:6.0f} max={max_rms:6.0f} |{bar}|", end="", flush=True)
                    self.rms_buffer = []

                # Encode and send
                message = {
                    "type": "audio_chunk",
                    "data": {
                        "audio": base64.b64encode(audio_data).decode("ascii"),
                        "seq": self.seq,
                        "is_final": False
                    }
                }

                await self.ws.send(json.dumps(message))

                # Small delay to match real-time (20ms chunks)
                await asyncio.sleep(0.015)  # Slightly less than 20ms to account for processing

        except asyncio.CancelledError:
            pass

    async def send_final(self):
        """Send final chunk to trigger last transcription."""
        print("\nSending final chunk...")
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

        # Wait a bit for final result
        await asyncio.sleep(2.0)

    def cleanup(self):
        """Clean up audio resources."""
        if self.stream:
            self.stream.stop_stream()
            self.stream.close()
        if self.audio:
            self.audio.terminate()

    async def run(self):
        """Main run loop."""
        try:
            await self.connect()
            self.init_audio()

            # Start receiver task
            receiver_task = asyncio.create_task(self.receive_messages())

            # Start streaming
            stream_task = asyncio.create_task(self.stream_audio())

            # Wait for Ctrl+C
            try:
                await stream_task
            except asyncio.CancelledError:
                pass

            # Send final chunk
            await self.send_final()

            # Cancel receiver
            receiver_task.cancel()
            try:
                await receiver_task
            except asyncio.CancelledError:
                pass

        except OSError:
            print(f"Error: Cannot connect to {self.uri}")
            print("Make sure the server is running.")

        except Exception as e:
            print(f"Error: {e}")
        finally:
            self.cleanup()
            if self.ws:
                await self.ws.close()


async def main():
    parser = argparse.ArgumentParser(description="WebSocket ASR Microphone Test")
    parser.add_argument("--host", default="localhost", help="Server host (default: localhost)")
    parser.add_argument("--port", type=int, default=8000, help="Server port (default: 8000)")
    parser.add_argument("--device", type=int, default=None, help="Input device index (default: system default)")
    args = parser.parse_args()

    streamer = MicrophoneStreamer(args.host, args.port, args.device)

    # Handle Ctrl+C
    loop = asyncio.get_event_loop()

    def signal_handler():
        streamer.running = False

    if sys.platform != "win32":
        loop.add_signal_handler(signal.SIGINT, signal_handler)

    try:
        await streamer.run()
    except KeyboardInterrupt:
        streamer.running = False
        await streamer.send_final()
        streamer.cleanup()


if __name__ == "__main__":
    print("=" * 60)
    print("WebSocket ASR Microphone Test")
    print("=" * 60)
    print()

    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nStopped by user")

    print("\nDone!")
