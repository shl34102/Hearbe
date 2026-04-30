# WebSocket ASR 스트리밍 아키텍처

> PTT(Push-to-Talk) 기반 실시간 음성 인식 처리 아키텍처

**버전**: 2.0
**작성일**: 2026-01-21
**관련 문서**: [WEBSOCKET_PROTOCOL.md](./WEBSOCKET_PROTOCOL.md)

---

## 1. 개요

### 1.1 목적

WebSocket을 통한 **Push-to-Talk(PTT) 방식** 음성 인식 시스템:
- 클라이언트가 녹음 시작/종료를 제어
- 서버는 수신된 오디오를 버퍼링 후 `is_final=true` 시점에 transcribe
- VAD(Voice Activity Detection) 없이 단순하고 안정적인 구조

### 1.2 PTT vs VAD 비교

| 항목 | PTT (현재) | VAD |
|------|-----------|-----|
| 녹음 제어 | 클라이언트 (사용자 버튼) | 서버 (음성 감지) |
| 구현 복잡도 | 낮음 | 높음 |
| Whisper 환각 | 없음 (무음 전송 안함) | 있음 (무음 시 발생) |
| 사용자 경험 | 명시적 (버튼 누름) | 암묵적 (자동 감지) |

### 1.3 아키텍처 다이어그램

```
┌─────────────────────────────────────────────────────────────────────────┐
│  Client (MCP App / Test Script)                                          │
│                                                                          │
│  [Microphone] → [Hold SPACE] → [3s chunks] → WebSocket                  │
│                     │                              │                     │
│                     │  is_final=false (3s auto)   │                     │
│                     │  is_final=true (release)    ▼                     │
└─────────────────────────────────────────────────────────────────────────┘
                                    │
                                    ▼
┌─────────────────────────────────────────────────────────────────────────┐
│  AI Server - WebSocket Handler (PTT Mode)                                │
│                                                                          │
│  ┌──────────────────┐     ┌──────────────────┐     ┌──────────────────┐ │
│  │  Receive Loop    │     │   Audio Queue    │     │   ASR Worker     │ │
│  │                  │     │                  │     │   (PTT Mode)     │ │
│  │  - Parse JSON    │────▶│  asyncio.Queue   │────▶│  - Buffer audio  │ │
│  │  - Decode Base64 │     │  (per session)   │     │  - Wait is_final │ │
│  │  - Non-blocking  │     │  max_size=50     │     │  - Transcribe    │ │
│  └──────────────────┘     └──────────────────┘     └──────────────────┘ │
│                                                            │            │
│                          ┌──────────────────┐              │            │
│                          │    ASR Lock      │              │            │
│                          │  (GPU serialize) │◀─────────────┘            │
│                          └──────────────────┘                            │
│                                    │                                     │
│                                    ▼                                     │
│                          ┌──────────────────┐                            │
│                          │  Faster-Whisper  │                            │
│                          │  (GPU/CUDA)      │                            │
│                          └──────────────────┘                            │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Audio Contract

클라이언트와 서버 간 오디오 포맷 명세입니다.

### 2.1 필수 스펙

| 항목 | 값 | 설명 |
|------|-----|------|
| Sample Rate | 16000 Hz | Whisper 모델 요구사항 |
| Channels | 1 (Mono) | 단일 채널 |
| Bit Depth | 16-bit | Signed Integer |
| Byte Order | Little Endian | PCM 표준 |
| Frame Size | 320 samples | 20ms @ 16kHz |
| Chunk Size | 640 bytes | 320 samples × 2 bytes |

### 2.2 서버 상수

**파일**: [api/websocket.py](../api/websocket.py)

```python
# Audio Contract Constants
AUDIO_SAMPLE_RATE = 16000          # 16kHz (Whisper requirement)
AUDIO_CHANNELS = 1                  # Mono
AUDIO_BIT_DEPTH = 16                # 16-bit signed integer
AUDIO_FRAME_SIZE = 320              # 20ms @ 16kHz (320 samples)
AUDIO_CHUNK_BYTES = 640             # 320 samples * 2 bytes

# Buffer Management
BUFFER_THRESHOLD_BYTES = 32000      # ~1 second of audio (triggers transcription)
BUFFER_OVERLAP_BYTES = 6400         # 200ms overlap for continuity
MAX_BUFFER_SIZE = 320000            # 10 seconds max (memory limit)

# Queue Management
MAX_QUEUE_SIZE = 50                 # Max pending chunks per session
```

### 2.3 클라이언트 구현 예시

```javascript
// JavaScript (Browser)
const audioContext = new AudioContext({ sampleRate: 16000 });
const FRAME_SIZE = 320;  // 20ms

processor.onaudioprocess = (e) => {
  const float32 = e.inputBuffer.getChannelData(0);
  const int16 = new Int16Array(float32.length);

  for (let i = 0; i < float32.length; i++) {
    int16[i] = Math.max(-32768, Math.min(32767, float32[i] * 32768));
  }

  ws.send(JSON.stringify({
    type: "audio_chunk",
    data: {
      audio: btoa(String.fromCharCode(...new Uint8Array(int16.buffer))),
      sample_rate: 16000,
      channels: 1,
      format: "pcm16",
      sequence: sequenceNumber++,
      is_final: false
    }
  }));
};
```

---

## 3. Queue 기반 처리 아키텍처

### 3.1 세션별 리소스

각 WebSocket 연결(세션)마다 독립적인 리소스를 할당합니다.

```python
# Per-session state
self._audio_queues: Dict[str, asyncio.Queue] = {}      # Audio chunk queues
self._audio_buffers: Dict[str, bytes] = {}             # Accumulated audio buffers
self._worker_tasks: Dict[str, asyncio.Task] = {}       # ASR worker tasks
self._chunk_counters: Dict[str, int] = {}              # Received chunk count
self._segment_counters: Dict[str, int] = {}            # Transcription segment count
```

### 3.2 Receive Loop (Non-blocking)

WebSocket 메시지 수신은 빠르게 처리하고 Queue에 전달합니다.

```python
async def _handle_audio_chunk(self, session_id: str, data: dict):
    """Handle incoming audio chunk - fast path to queue."""
    queue = self._audio_queues.get(session_id)
    if not queue:
        return

    chunk = AudioChunk(
        data=base64.b64decode(data.get("audio", "")),
        sequence=data.get("sequence", 0),
        is_final=data.get("is_final", False),
        timestamp=datetime.now()
    )

    # Non-blocking queue put with backpressure handling
    try:
        queue.put_nowait(chunk)
    except asyncio.QueueFull:
        logger.warning(f"Queue full, dropping oldest chunk: {session_id}")
        queue.get_nowait()  # Drop oldest
        queue.put_nowait(chunk)
```

### 3.3 ASR Worker (PTT Mode)

PTT 모드에서는 `is_final=true`를 받을 때만 transcribe를 수행합니다.

```python
async def _asr_worker(self, session_id: str):
    """
    ASR worker task for PTT (Push-to-Talk) mode.

    Client controls recording start/stop:
    - Receives audio chunks and buffers them
    - Transcribes when is_final=true (user released record button)
    """
    queue = self._audio_queues.get(session_id)
    if not queue:
        return

    while True:
        try:
            chunk: AudioChunk = await asyncio.wait_for(
                queue.get(),
                timeout=30.0
            )

            # Append chunk to buffer
            buffer = self._audio_buffers.get(session_id, b"")
            buffer += chunk.data
            self._audio_buffers[session_id] = buffer

            # Check buffer size limit
            if len(buffer) > MAX_BUFFER_SIZE:
                logger.warning(f"Buffer overflow, truncating: {session_id}")
                buffer = buffer[-MAX_BUFFER_SIZE:]
                self._audio_buffers[session_id] = buffer

            # Transcribe only when is_final=true (user released button)
            should_transcribe = chunk.is_final and len(buffer) > 0

            if should_transcribe and self.asr.is_ready():
                await self._process_audio_buffer(
                    session_id,
                    buffer,
                    is_final=chunk.is_final
                )
                # Clear buffer after transcription
                self._audio_buffers[session_id] = b""

        except asyncio.TimeoutError:
            continue  # Keep waiting
        except asyncio.CancelledError:
            break  # Clean shutdown
```

### 3.4 PTT 처리 흐름

```
Client                          Server
  │                               │
  │  [User holds SPACE]           │
  │  ──────────────────────────►  │
  │  audio_chunk (is_final=false) │  Buffer += chunk.data
  │  ──────────────────────────►  │  Buffer += chunk.data
  │  audio_chunk (is_final=false) │  Buffer += chunk.data
  │  ...                          │  ...
  │                               │
  │  [3 seconds elapsed]          │
  │  audio_chunk (is_final=false) │  (Partial: buffer sent, but no transcribe)
  │  ──────────────────────────►  │
  │                               │
  │  [User releases SPACE]        │
  │  audio_chunk (is_final=true)  │  Transcribe(buffer)
  │  ──────────────────────────►  │  Clear buffer
  │                               │
  │  ◄──────────────────────────  │
  │  asr_result                   │
  │                               │
```

---

## 4. GPU 동시성 제어

### 4.1 ASR Lock

단일 GPU에서 여러 세션의 동시 추론을 방지합니다.

```python
# Global ASR lock for GPU serialization
_asr_lock = asyncio.Lock()

async def _process_audio_buffer(self, session_id: str, buffer: bytes, is_final: bool):
    """Process accumulated audio buffer with GPU lock."""

    async with _asr_lock:  # Serialize GPU access
        segment_id = f"seg_{self._segment_counters[session_id]}"
        self._segment_counters[session_id] += 1

        result = await self.asr.transcribe(
            buffer,
            is_final=is_final,
            segment_id=segment_id
        )

    # Send result (outside lock)
    await self._send_asr_result(session_id, result)
```

### 4.2 왜 Lock이 필요한가?

| 문제 | Lock 없을 때 | Lock 있을 때 |
|------|-------------|-------------|
| GPU 메모리 | OOM 위험 | 순차 사용으로 안정 |
| 추론 속도 | 경합으로 느려짐 | 예측 가능한 latency |
| 결과 순서 | 뒤섞임 가능 | 세션별 순서 보장 |

---

## 5. PTT 버퍼링 전략

### 5.1 클라이언트 측 버퍼링

PTT 모드에서는 클라이언트가 녹음 시간을 제어합니다.

```
Time →
┌────────────────────────────────────────────────────────────────────────┐
│  User holds SPACE                                                       │
├────────┬────────┬────────┬────────┬────────┬────────┬────────┬────────┤
│ chunk1 │ chunk2 │ chunk3 │ ...    │ chunkN │ chunkN+1 │ ...   │ final │
└────────┴────────┴────────┴────────┴────────┴────────┴────────┴────────┘
         │                          │                           │
         │◄─── 3 seconds ──────────►│                           │
         │      (is_final=false)    │                           │
         │                          │◄─── remaining ───────────►│
         │                          │      (is_final=true)      │
```

### 5.2 PTT 청크 크기

| 설정 | 값 | 설명 |
|------|-----|------|
| `CHUNK_DURATION_SEC` | 3.0초 | 자동 분할 간격 |
| `MIN_RECORDING_SEC` | 0.5초 | 최소 녹음 시간 (미만 시 스킵) |
| `MAX_BUFFER_SIZE` | 320000 bytes | 10초 최대 (메모리 제한) |

### 5.3 짧은 녹음 처리

Whisper는 무음 또는 극히 짧은 오디오에서 환각(hallucination)을 일으킵니다.

```
Recording < 0.5s:
- Skip audio data (don't send to Whisper)
- Send is_final=true signal (empty audio)
- Server processes any previously buffered audio

Example output:
[SKIP] Audio too short (0.13s < 0.5s), sending final signal only
```

### 5.4 서버 측 버퍼링

서버는 `is_final=true`를 받을 때까지 오디오를 누적합니다.

```python
# PTT mode: no overlap, no automatic transcription
# Just buffer until is_final=true
should_transcribe = chunk.is_final and len(buffer) > 0

if should_transcribe:
    await self._process_audio_buffer(session_id, buffer)
    self._audio_buffers[session_id] = b""  # Clear completely
```

---

## 6. Backpressure 처리

### 6.1 Queue Full 시나리오

클라이언트가 빠르게 전송하고 서버 처리가 느릴 때:

```python
MAX_QUEUE_SIZE = 50  # ~1초 분량 (20ms × 50)

try:
    queue.put_nowait(chunk)
except asyncio.QueueFull:
    # Strategy: Drop oldest chunk
    logger.warning(f"Queue full, dropping oldest: {session_id}")
    queue.get_nowait()
    queue.put_nowait(chunk)
```

### 6.2 대안 전략

| 전략 | 구현 | 장단점 |
|------|------|--------|
| **Drop Oldest (현재)** | `get_nowait()` 후 `put_nowait()` | 최신 데이터 유지, 일부 손실 |
| Drop Newest | `put_nowait()` 무시 | 구현 간단, 최신 손실 |
| Block | `await queue.put()` | 손실 없음, 지연 누적 |
| Resize | 동적 큐 확장 | 메모리 증가 |

---

## 7. 세션 생명주기

### 7.1 연결 시 초기화

```python
async def _initialize_session(self, session_id: str):
    """Initialize per-session resources."""
    self._audio_queues[session_id] = asyncio.Queue(maxsize=MAX_QUEUE_SIZE)
    self._audio_buffers[session_id] = b""
    self._chunk_counters[session_id] = 0
    self._segment_counters[session_id] = 0

    # Start ASR worker task
    self._worker_tasks[session_id] = asyncio.create_task(
        self._asr_worker(session_id)
    )
```

### 7.2 연결 해제 시 정리

```python
async def _cleanup_session(self, session_id: str):
    """Clean up session resources on disconnect."""
    # Cancel worker task
    if session_id in self._worker_tasks:
        task = self._worker_tasks.pop(session_id)
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    # Clear resources
    self._audio_queues.pop(session_id, None)
    self._audio_buffers.pop(session_id, None)
    self._chunk_counters.pop(session_id, None)
    self._segment_counters.pop(session_id, None)
```

---

## 8. 메시지 프로토콜 확장

### 8.1 `audio_chunk` 확장 필드

```json
{
  "type": "audio_chunk",
  "data": {
    "audio": "base64_encoded_pcm16",
    "sample_rate": 16000,
    "channels": 1,
    "format": "pcm16",
    "sequence": 123,
    "is_final": false
  }
}
```

| 필드 | 타입 | 필수 | 설명 |
|------|------|------|------|
| `audio` | string | O | Base64 인코딩된 PCM 데이터 |
| `sample_rate` | int | O | 16000 (고정) |
| `channels` | int | O | 1 (고정) |
| `format` | string | O | "pcm16" |
| `sequence` | int | O | 청크 순서 번호 |
| `is_final` | bool | O | 녹음 종료 시 true |

### 8.2 `asr_result` 확장 필드

```json
{
  "type": "asr_result",
  "data": {
    "text": "쿠팡에서 우유 검색해줘",
    "confidence": 0.95,
    "language": "ko",
    "duration": 2.5,
    "is_final": true,
    "segment_id": "seg_3"
  }
}
```

| 필드 | 타입 | 설명 |
|------|------|------|
| `text` | string | 인식된 텍스트 |
| `confidence` | float | 언어 감지 신뢰도 (0.0~1.0) |
| `language` | string | 언어 코드 ("ko") |
| `duration` | float | 처리된 오디오 길이 (초) |
| `is_final` | bool | 최종 결과 여부 |
| `segment_id` | string | 세그먼트 식별자 ("seg_N") |

---

## 9. 성능 메트릭

### 9.1 모니터링 지표

| 메트릭 | 측정 방법 | 목표값 |
|--------|----------|--------|
| Queue Depth | `queue.qsize()` | < 30 |
| Buffer Size | `len(buffer)` | < 64KB |
| ASR Latency | 추론 시작~완료 | < 500ms |
| End-to-End | 청크 수신~결과 전송 | < 1.5s |

### 9.2 로깅

```python
logger.debug(f"ASR transcribed: session={session_id}, "
             f"duration={result.duration:.2f}s, "
             f"text={result.text[:50]}...")
```

---

## 10. 테스트 클라이언트

### 10.1 PTT 테스트 (`test_ws_ptt.py`)

Hold-to-talk 방식의 테스트 클라이언트입니다.

**실행 방법**:
```bash
pip install pyaudio websockets keyboard
python tests/test_ws_ptt.py --host localhost --port 8000
```

**사용법**:
- **SPACE 누르고 있기**: 녹음 시작
- **SPACE 놓기**: 녹음 종료 및 전송
- **ESC**: 종료

**자동 분할**:
- 3초 이상 녹음 시 자동으로 partial chunk 전송 (`is_final=false`)
- SPACE를 놓으면 남은 버퍼 전송 (`is_final=true`)

**예시 출력**:
```
[REC] Recording started...
[SEND] PARTIAL chunk #1 (2.94s, 94208 bytes)
[STOP] Recording stopped (1.50s)
[SEND] FINAL chunk #2 (1.50s, 48000 bytes)
[FINAL] 쿠팡에서 우유 검색해줘 (conf=0.95)
```

### 10.2 연속 스트리밍 테스트 (`test_ws_mic.py`)

RMS 모니터링이 포함된 연속 스트리밍 테스트입니다.

```bash
python tests/test_ws_mic.py --host localhost --port 8000 --device 1
```

---

## 11. 향후 개선 계획

| 기능 | 우선순위 | 설명 |
|------|----------|------|
| Mobile PTT Button | High | 모바일 앱용 PTT 버튼 UI |
| Streaming Partial Results | Medium | 긴 녹음 중 중간 결과 표시 |
| Multi-GPU | Low | 여러 GPU 간 로드밸런싱 |
| WebRTC | Low | UDP 기반 저지연 전송 |

---

## 12. 참고 자료

- [Faster-Whisper GitHub](https://github.com/SYSTRAN/faster-whisper)
- [asyncio.Queue Documentation](https://docs.python.org/3/library/asyncio-queue.html)
- [WebSocket Backpressure Patterns](https://websockets.readthedocs.io/en/stable/topics/flow-control.html)

---

**문서 버전**: 2.0
**최종 수정일**: 2026-01-21
**변경 이력**:
- v2.0 (2026-01-21): VAD에서 PTT 모드로 전환, 테스트 클라이언트 문서 추가
- v1.0 (2026-01-21): 초기 버전 (VAD 기반)
