"""
Google Cloud TTS 테스트 스크립트

사용법:
    cd /home/murphy/S14P11D108/AI
    python -m services.tts.test_google_tts
"""

import asyncio
import wave
import sys
import os

# 프로젝트 루트를 path에 추가
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from services.tts.service import TTSService


def save_as_wav(audio_data: bytes, filename: str, sample_rate: int = 24000):
    """PCM 오디오 데이터를 WAV 파일로 저장"""
    with wave.open(filename, 'wb') as wav_file:
        wav_file.setnchannels(1)  # 모노
        wav_file.setsampwidth(2)  # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(audio_data)
    print(f"저장됨: {filename}")


async def test_basic_synthesis():
    """기본 TTS 합성 테스트"""
    print("=" * 50)
    print("기본 TTS 합성 테스트")
    print("=" * 50)

    tts = TTSService()
    await tts.initialize()

    # 테스트 문장들
    test_texts = [
        "안녕하세요, 음성 쇼핑 도우미입니다.",
        "검색 결과를 안내해드리겠습니다.",
        "총 5개의 상품이 검색되었습니다. 첫 번째 상품은 삼성 갤럭시 S24이며, 가격은 119만원입니다.",
    ]

    for i, text in enumerate(test_texts, 1):
        print(f"\n[{i}] 텍스트: {text}")
        audio_data = await tts.synthesize(text)
        print(f"    오디오 크기: {len(audio_data):,} bytes")

        # WAV 파일로 저장
        filename = f"test_output_{i}.wav"
        save_as_wav(audio_data, filename)

    await tts.shutdown()


async def test_streaming():
    """스트리밍 TTS 테스트"""
    print("\n" + "=" * 50)
    print("스트리밍 TTS 테스트")
    print("=" * 50)

    tts = TTSService()
    await tts.initialize()

    text = "스트리밍 테스트입니다. 음성이 청크 단위로 전송됩니다."
    print(f"\n텍스트: {text}")

    chunks = []
    chunk_count = 0

    async for chunk in tts.synthesize_stream(text):
        chunk_count += 1
        chunks.append(chunk.audio_data)
        print(f"  청크 {chunk_count}: {len(chunk.audio_data)} bytes, is_final={chunk.is_final}")

    # 전체 오디오 합치기
    full_audio = b"".join(chunks)
    print(f"\n총 청크 수: {chunk_count}")
    print(f"전체 오디오 크기: {len(full_audio):,} bytes")

    save_as_wav(full_audio, "test_streaming.wav")

    await tts.shutdown()


async def test_voice_list():
    """음성 목록 테스트"""
    print("\n" + "=" * 50)
    print("사용 가능한 음성 목록")
    print("=" * 50)

    tts = TTSService()
    voices = tts.get_voice_list()

    for voice in voices:
        print(f"  - {voice['id']}: {voice['name']}")


async def main():
    """메인 테스트 실행"""
    print("\nGoogle Cloud TTS Chirp 테스트")
    print("=" * 50)

    try:
        await test_voice_list()
        await test_basic_synthesis()
        await test_streaming()

        print("\n" + "=" * 50)
        print("모든 테스트 완료!")
        print("생성된 파일: test_output_1.wav, test_output_2.wav, test_output_3.wav, test_streaming.wav")
        print("=" * 50)

    except Exception as e:
        print(f"\n오류 발생: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
