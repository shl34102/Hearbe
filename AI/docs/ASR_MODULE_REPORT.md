# ASR 모듈 구현 보고서

> 음성 인식을 위한 Faster-Whisper(turbo) 모델 통합

**버전**: 1.0
**작성일**: 2026-01-21
**작성자**: AI Team (minchan)
**Jira**: S14P11D108-69

---

## 1. 개요

### 1.1 목적

GPU 가속 기반의 Faster-Whisper(turbo) 모델을 활용하여 **한국어 실시간 STT(Speech-to-Text)** 기능을 구현한다.

### 1.2 범위

| 구성 요소          | 설명                                              |
| ------------------ | ------------------------------------------------- |
| ASR Service        | Faster-Whisper 기반 전사(Transcription) 핵심 로직 |
| HTTP Endpoint      | 오디오 파일 전사용 REST API                       |
| Docker Integration | GPU 사용 및 모델 캐시를 포함한 컨테이너 구성      |

### 1.3 아키텍처

```
┌─────────────────────────────────────────────────────────────────────┐
│  Client (curl / Browser Extension / MCP App)                        │
│                          │                                          │
│                    POST /api/v1/asr/transcribe                      │
│                    (multipart/form-data: audio file)                │
│                          ▼                                          │
├─────────────────────────────────────────────────────────────────────┤
│  FastAPI Server (main.py)                                           │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  api/http.py                                                │    │
│  │  - transcribe_audio() endpoint                              │    │
│  │  - Reads ASR service from app.state                         │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                          │                                          │
│                          ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  services/asr/service.py (ASRService)                       │    │
│  │  - _preprocess_audio(): WAV/PCM parsing, resampling         │    │
│  │  - transcribe(): Whisper inference                          │    │
│  │  - transcribe_stream(): Chunked streaming (future)          │    │
│  └─────────────────────────────────────────────────────────────┘    │
│                          │                                          │
│                          ▼                                          │
│  ┌─────────────────────────────────────────────────────────────┐    │
│  │  Faster-Whisper Model (turbo)                               │    │
│  │  - Device: CUDA (GPU)                                       │    │
│  │  - Compute Type: float16                                    │    │
│  │  - Language: Korean (ko)                                    │    │
│  │  - Cache: /root/.cache/huggingface (Docker volume)          │    │
│  └─────────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────────┘
```

---

## 2. 설정

### 2.1 환경 변수

| 변수               | 기본값           | 설명                 |
| ------------------ | ---------------- | -------------------- |
| `ASR_MODEL_NAME`   | `large-v3-turbo` | Whisper 모델 종류    |
| `ASR_DEVICE`       | `cuda`           | 추론 장치 (cuda/cpu) |
| `ASR_COMPUTE_TYPE` | `float16`        | GPU 추론 정밀도      |
| `ASR_LANGUAGE`     | `ko`             | 대상 언어            |
| `ASR_BEAM_SIZE`    | `5`              | Beam search 폭       |

### 2.2 설정 클래스

**파일**: [core/config.py:19-25](../core/config.py#L19-L25)

```python
@dataclass
class ASRConfig:
    """ASR (Speech Recognition) Configuration"""
    model_name: str = "large-v3-turbo"
    device: str = "cuda"
    compute_type: str = "float16"
    language: str = "ko"
    beam_size: int = 5
```

### 2.3 Docker 설정

**파일**: [docker-compose.yml](../docker-compose.yml)

```yaml
services:
  ai-server:
    build:
      context: .
      dockerfile: Dockerfile
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    volumes:
      - .:/app # Hot-reload
      - huggingface-cache:/root/.cache/huggingface # Model cache
```

**파일**: [Dockerfile](../Dockerfile)

```dockerfile
FROM nvidia/cuda:12.3.2-cudnn9-runtime-ubuntu22.04

# Faster-Whisper installation
RUN pip install --no-cache-dir \
    faster-whisper \
    "ctranslate2>=4.0,<5" \
    "huggingface_hub>=0.23" \
    ...
```

---

## 3. 구현 상세

### 3.1 ASR 서비스

**파일**: [services/asr/service.py](../services/asr/service.py)

#### 3.1.1 모델 로딩

```python
async def initialize(self):
    """Load Whisper model."""
    from faster_whisper import WhisperModel

    self._model = WhisperModel(
        self._config.model_name,      # "turbo" or "large-v3-turbo"
        device=self._config.device,   # "cuda"
        compute_type=self._config.compute_type  # "float16"
    )
    self._ready = True
```

#### 3.1.2 오디오 전처리

```python
def _preprocess_audio(self, audio_data: bytes) -> np.ndarray:
    """
    Convert raw audio bytes to numpy array for Whisper.

    Supports:
    - WAV files (any sample rate, mono/stereo)
    - Raw PCM (16kHz, mono, 16-bit) as fallback

    Processing:
    1. Parse WAV header with soundfile
    2. Convert stereo to mono (if needed)
    3. Resample to 16kHz (Whisper requirement)
    4. Return float32 array normalized to [-1, 1]
    """
```

#### 3.1.3 전사(Transcription)

```python
async def transcribe(self, audio_data: bytes) -> STTResult:
    audio_array = self._preprocess_audio(audio_data)

    segments, info = self._model.transcribe(
        audio_array,
        language=self._config.language,  # "ko"
        beam_size=self._config.beam_size,
        word_timestamps=False
    )

    text = " ".join([seg.text.strip() for seg in segments])

    return STTResult(
        text=text,
        confidence=info.language_probability,
        language=self._config.language,
        duration=len(audio_array) / 16000.0
    )
```

### 3.2 HTTP 엔드포인트

**파일**: [api/http.py:157-190](../api/http.py#L157-L190)

#### 3.2.1 엔드포인트 정의

```python
@router.post("/asr/transcribe", response_model=ASRResponse)
async def transcribe_audio(request: Request, file: UploadFile = File(...)):
    """
    Transcribe audio file to text.

    - Method: POST
    - Path: /api/v1/asr/transcribe
    - Content-Type: multipart/form-data
    - Body: file (audio WAV/PCM)
    """
```

#### 3.2.2 응답 모델

```python
class ASRResponse(BaseModel):
    text: str          # Transcribed text
    confidence: float  # Language probability (0-1)
    language: str      # Detected/forced language
    duration: float    # Audio duration in seconds
```

#### 3.2.3 서비스 주입(Wiring)

**파일**: [main.py:135-138](../main.py#L135-L138)

```python
# In lifespan context manager
app.state.asr_service = self.asr_service
app.state.tts_service = self.tts_service
app.state.ocr_service = self.ocr_service
```

---

## 4. 의존성

### 4.1 Python 패키지

**파일**: [requirements.txt](../requirements.txt)

```txt
# Core Framework
fastapi>=0.109.0
python-multipart>=0.0.6    # For file upload

# ASR (installed in Dockerfile)
soundfile>=0.12.1          # WAV file parsing
numpy>=1.24.0              # Array operations
scipy>=1.10.0              # Audio resampling
```

### 4.2 Dockerfile 설치 항목

```dockerfile
# Faster-Whisper (installed separately for CUDA compatibility)
RUN pip install --no-cache-dir \
    faster-whisper \
    "ctranslate2>=4.0,<5" \
    "huggingface_hub>=0.23" \
    "tokenizers>=0.13,<1" \
    "onnxruntime>=1.14,<2" \
    "av>=11"
```

---

## 5. API 레퍼런스

### 5.1 오디오 전사

**Endpoint**: `POST /api/v1/asr/transcribe`

#### 요청

| 파라미터 | 타입 | 필수 | 설명                  |
| -------- | ---- | ---- | --------------------- |
| file     | File | Yes  | 오디오 파일(WAV 권장) |

**지원 포맷**

- WAV (16kHz mono 권장, 그 외 포맷은 자동 변환)
- Raw PCM (16kHz, mono, 16-bit) — fallback 파싱

#### 응답

```json
{
  "text": "transcribed text here",
  "confidence": 0.95,
  "language": "ko",
  "duration": 3.5
}
```

#### 에러 응답

| Status | Detail                        |
| ------ | ----------------------------- |
| 400    | Empty audio file              |
| 503    | ASR service not available     |
| 500    | Transcription failed: {error} |

### 5.2 사용 예시

**curl (컨테이너 내부)**:

```bash
curl -X POST http://localhost:8000/api/v1/asr/transcribe \
  -F 'file=@/path/to/audio.wav'
```

**curl (Windows host)**:

```bash
curl -X POST http://localhost:8000/api/v1/asr/transcribe \
  -F "file=@C:\path\to\audio.wav"
```

**Python (requests)**:

```python
import requests

with open("audio.wav", "rb") as f:
    response = requests.post(
        "http://localhost:8000/api/v1/asr/transcribe",
        files={"file": f}
    )
print(response.json())
```

---

## 6. 테스트

### 6.1 유닛 테스트 스크립트

**파일**: [services/asr/test_asr.py](../services/asr/test_asr.py)

```bash
# Run inside container
docker exec herewego-ai python -m services.asr.test_asr

# With custom audio file
docker exec herewego-ai python -m services.asr.test_asr /app/test.wav
```

**예상 출력**

```
============================================================
Testing ASR Service Initialization
============================================================
Config: model=turbo, device=cuda
Loading model... (this may take a while on first run)
Model loaded successfully!

============================================================
Testing Transcription
============================================================
Generating test audio (1 second silence)...
Audio data size: 32044 bytes
Transcription result:
  text: '...'
  confidence: 1.000
  language: ko
  duration: 1.00s

All tests passed!
```

### 6.2 HTTP 엔드포인트 테스트

```bash
# Generate test audio and call endpoint
docker exec herewego-ai bash -c "
python -c \"
import numpy as np
import soundfile as sf
audio = np.zeros(16000, dtype=np.float32)
sf.write('/tmp/test.wav', audio, 16000)
\" && curl -s -X POST http://localhost:8000/api/v1/asr/transcribe -F 'file=@/tmp/test.wav'"
```

**예상 응답**

```json
{ "text": "...", "confidence": 1.0, "language": "ko", "duration": 1.0 }
```

---

## 7. 파일 변경 요약

| File                       | Lines          | Change Type | Description                         |
| -------------------------- | -------------- | ----------- | ----------------------------------- |
| `services/asr/service.py`  | 1-172          | Modified    | Faster-Whisper 기반 ASR 전체 구현   |
| `services/asr/test_asr.py` | 1-95           | Created     | ASR 모듈 테스트 스크립트 추가       |
| `api/http.py`              | 56-62, 157-190 | Modified    | ASRResponse 및 전사 엔드포인트 추가 |
| `main.py`                  | 135-138        | Modified    | app.state에 서비스 노출             |
| `requirements.txt`         | 10, 16         | Modified    | python-multipart, scipy 추가        |

---

## 8. 커밋

| Hash      | Message                                                        |
| --------- | -------------------------------------------------------------- |
| `2e74aca` | feat: ASR module Faster-Whisper implementation and test script |
| (pending) | feat: ASR HTTP endpoint with service wiring                    |

---

## 9. 향후 작업

### 9.1 계획 기능

| Feature             | Priority | Description                               |
| ------------------- | -------- | ----------------------------------------- |
| WebSocket Streaming | High     | `/ws` 기반 오디오 청크 실시간 전사        |
| VAD Integration     | Medium   | 발화 구간(utterance) 경계 탐지를 위한 VAD |
| Multi-language      | Low      | 동적 언어 감지 지원                       |

### 9.2 WebSocket 연동(다음 단계)

```
Browser Extension → WebSocket /ws → audio_chunk messages
                                   ↓
                              ASRService.transcribe_stream()
                                   ↓
                              stt_result messages → Client
```

---

## 10. 트러블슈팅

### 10.1 자주 발생하는 이슈

| Issue                       | Cause                     | Solution                                         |
| --------------------------- | ------------------------- | ------------------------------------------------ |
| `ASR service not available` | 모델 미로드/초기화 실패   | 컨테이너 로그에서 초기화 오류 확인               |
| `python-multipart` error    | 의존성 누락               | 컨테이너 내부에서 `pip install python-multipart` |
| 첫 요청이 느림              | 모델 다운로드/캐시 미존재 | HuggingFace 다운로드 완료까지 대기               |
| CUDA out of memory          | GPU 메모리 부족           | 배치/설정 축소 또는 CPU fallback 고려            |

### 10.2 로그 위치

- 컨테이너 로그: `docker logs herewego-ai`
- 애플리케이션 로그: `AI/logs/ai_server.log`

---

**문서 버전**: 1.0
**최종 수정일**: 2026-01-21
