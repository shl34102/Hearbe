"""
ASR Module Test Script

Usage (inside container):
    python -m services.asr.test_asr [audio_file]

Without audio file, generates a test tone.
"""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))


async def test_asr_initialization():
    """Test ASR model loading."""
    from services.asr.service import ASRService

    print("=" * 60)
    print("Testing ASR Service Initialization")
    print("=" * 60)

    asr = ASRService()
    print(f"Config: model={asr._config.model_name}, device={asr._config.device}")

    print("Loading model... (this may take a while on first run)")
    await asr.initialize()

    assert asr.is_ready(), "ASR service should be ready after initialization"
    print("Model loaded successfully!")

    return asr


async def test_transcribe_audio(asr, audio_path: str = None):
    """Test transcription with audio file or generated tone."""
    print("\n" + "=" * 60)
    print("Testing Transcription")
    print("=" * 60)

    if audio_path and Path(audio_path).exists():
        # Use provided audio file
        print(f"Using audio file: {audio_path}")
        with open(audio_path, "rb") as f:
            audio_data = f.read()
    else:
        # Generate test audio (silent + simple tone)
        print("Generating test audio (1 second silence)...")
        import numpy as np
        import io
        import soundfile as sf

        # 1 second of silence at 16kHz
        sample_rate = 16000
        duration = 1.0
        audio_array = np.zeros(int(sample_rate * duration), dtype=np.float32)

        # Write to WAV bytes
        buffer = io.BytesIO()
        sf.write(buffer, audio_array, sample_rate, format="WAV")
        audio_data = buffer.getvalue()

    print(f"Audio data size: {len(audio_data)} bytes")

    result = await asr.transcribe(audio_data)
    print(f"Transcription result:")
    print(f"  text: '{result.text}'")
    print(f"  confidence: {result.confidence:.3f}")
    print(f"  language: {result.language}")
    print(f"  duration: {result.duration:.2f}s")

    return result


async def main():
    audio_path = sys.argv[1] if len(sys.argv) > 1 else None

    try:
        asr = await test_asr_initialization()
        await test_transcribe_audio(asr, audio_path)
        await asr.shutdown()
        print("\nAll tests passed!")
    except Exception as e:
        print(f"\nTest failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
