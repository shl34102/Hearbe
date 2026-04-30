# Faster-Whisper -> Qwen3-ASR 전환 계획

## 개요

기존 Faster-Whisper ASR을 Qwen3-ASR로 전환하되, Provider 패턴으로 두 백엔드를 환경변수로 선택 가능하게 구현합니다.

### 배경
- Qwen3-ASR 테스트 결과, 한국어 인식 품질이 Faster-Whisper보다 우수
- 기존 시스템 호환성 유지 필요 (롤백 가능)
- 환경변수 기반 전환으로 운영 유연성 확보

### 선택된 옵션
| 항목 | 선택 | 이유 |
|------|------|------|
| 스트리밍 | PTT 모드 유지 | 안정성 우선, Transformers 백엔드 사용 |
| 모델 | Qwen3-ASR-0.6B | ~2GB VRAM, 테스트에서 품질 확인됨 |
| Docker | 단일 이미지 + 환경변수 | 관리 단순화, 즉시 롤백 가능 |

---

## 아키텍처

### Before (현재)
```
ASRService (service.py)
    └── WhisperModel (faster_whisper)
```

### After (변경 후)
```
ASRService (Factory wrapper)
    └── ASRServiceFactory
            ├── WhisperASRProvider
            │       └── WhisperModel
            └── Qwen3ASRProvider
                    └── Qwen3ASRModel
```

---

## 디렉토리 구조

```
/home/ssafy/S14P11D108/AI/services/asr/
├── __init__.py          # ASRService export 유지
├── service.py           # Factory wrapper로 수정
├── factory.py           # ASRServiceFactory (신규)
└── providers/
    ├── __init__.py      # Provider exports
    ├── base.py          # BaseASRProvider 추상 클래스
    ├── whisper.py       # WhisperASRProvider (기존 코드 이동)
    └── qwen3.py         # Qwen3ASRProvider (신규)
```

---

## 주요 변경사항

### 1. Provider 패턴 구현

#### BaseASRProvider (추상 클래스)
```python
from abc import abstractmethod
from core.interfaces import IASRService, ASRResult

class BaseASRProvider(IASRService):
    def __init__(self, config):
        self._config = config
        self._model = None
        self._ready = False

    @abstractmethod
    async def initialize(self): pass

    @abstractmethod
    async def transcribe(self, audio_data: bytes, is_final: bool = True,
                         segment_id: str = None) -> ASRResult: pass

    def is_ready(self) -> bool:
        return self._ready
```

#### WhisperASRProvider
- 기존 `ASRService` 코드를 그대로 이동
- 클래스명만 `WhisperASRProvider`로 변경

#### Qwen3ASRProvider
```python
class Qwen3ASRProvider(BaseASRProvider):
    LANGUAGE_MAP = {
        "ko": "Korean",
        "en": "English",
        "zh": "Chinese",
        "ja": "Japanese"
    }

    async def initialize(self):
        import torch
        from qwen_asr import Qwen3ASRModel

        self._model = Qwen3ASRModel.from_pretrained(
            self._config.qwen3_model_name,
            dtype=torch.bfloat16,
            device_map=self._config.device,
            max_inference_batch_size=self._config.qwen3_max_batch_size,
            max_new_tokens=self._config.qwen3_max_new_tokens,
        )
        self._ready = True

    async def transcribe(self, audio_data: bytes, is_final: bool = True,
                         segment_id: str = None) -> ASRResult:
        audio_tuple = self._preprocess_audio(audio_data)
        language = self.LANGUAGE_MAP.get(self._config.language)

        results = self._model.transcribe(audio=audio_tuple, language=language)

        return ASRResult(
            text=results[0].text,
            confidence=1.0,
            language=self._config.language,
            duration=len(audio_tuple[0]) / 16000.0,
            is_final=is_final,
            segment_id=segment_id
        )
```

#### ASRServiceFactory
```python
from enum import Enum

class ASRProviderType(str, Enum):
    WHISPER = "whisper"
    QWEN3 = "qwen3"

class ASRServiceFactory:
    @staticmethod
    def create(config):
        if config.provider == ASRProviderType.QWEN3:
            from .providers.qwen3 import Qwen3ASRProvider
            return Qwen3ASRProvider(config)
        else:
            from .providers.whisper import WhisperASRProvider
            return WhisperASRProvider(config)
```

---

### 2. 설정 스키마 확장

#### ASRConfig 변경
```python
@dataclass
class ASRConfig:
    # 공통
    provider: str = "whisper"  # "whisper" | "qwen3"
    device: str = "cuda"
    language: str = "ko"

    # Whisper 전용
    model_name: str = "large-v3-turbo"
    compute_type: str = "float16"
    beam_size: int = 5

    # Qwen3 전용
    qwen3_model_name: str = "Qwen/Qwen3-ASR-0.6B"
    qwen3_max_batch_size: int = 32
    qwen3_max_new_tokens: int = 256
```

#### 환경변수
```bash
# ASR Provider 선택
ASR_PROVIDER=whisper  # whisper | qwen3

# Qwen3 전용 설정
ASR_QWEN3_MODEL_NAME=Qwen/Qwen3-ASR-0.6B
ASR_QWEN3_MAX_BATCH_SIZE=32
ASR_QWEN3_MAX_NEW_TOKENS=256
```

---

### 3. Dockerfile 수정

```dockerfile
# 기존 faster-whisper 스택 유지
# + qwen-asr 추가
RUN pip install --no-cache-dir "qwen-asr"
```

---

## 수정 대상 파일

| 파일 | 작업 |
|------|------|
| `services/asr/providers/__init__.py` | 신규 생성 |
| `services/asr/providers/base.py` | 신규 생성 |
| `services/asr/providers/whisper.py` | 신규 생성 (기존 service.py 코드 이동) |
| `services/asr/providers/qwen3.py` | 신규 생성 |
| `services/asr/factory.py` | 신규 생성 |
| `services/asr/service.py` | Factory wrapper로 수정 |
| `services/asr/__init__.py` | export 수정 |
| `core/config.py` | ASRConfig 확장 |
| `Dockerfile` | qwen-asr 패키지 추가 |
| `.env.example` | 환경변수 문서화 |

---

## 마이그레이션 순서

### Phase 1: Provider 패턴 구현
1. `providers/` 디렉토리 및 기반 클래스 생성
2. `WhisperASRProvider` 구현 (기존 코드 이동)
3. 기존 테스트 통과 확인 (Whisper 하위 호환성)

### Phase 2: Qwen3 Provider 구현
4. `Qwen3ASRProvider` 구현
5. 언어 코드 매핑 (ko -> Korean)

### Phase 3: 설정 및 Docker
6. `ASRConfig` 확장 및 환경변수 매핑
7. `Dockerfile` 수정 (qwen-asr 추가)

### Phase 4: 테스트
8. Docker 재빌드 및 통합 테스트

---

## 검증 방법

### 1. Whisper 하위 호환성 테스트
```bash
# 기존 설정으로 실행 (ASR_PROVIDER=whisper 또는 미설정)
docker compose up -d

# WebSocket 테스트
python tests/test_ws_mic.py
```

### 2. Qwen3 전환 테스트
```bash
# 환경변수 변경
ASR_PROVIDER=qwen3

# Docker 재시작
docker compose down && docker compose up -d

# WebSocket 테스트
python tests/test_ws_mic.py
```

### 3. GPU 메모리 확인
```bash
docker exec hearbe nvidia-smi
```

---

## 롤백 계획

환경변수만 변경하여 즉시 롤백 가능:

```bash
# Whisper로 롤백
ASR_PROVIDER=whisper
docker compose restart
```

---

## 참고: 언어 코드 매핑

| Whisper | Qwen3-ASR |
|---------|-----------|
| "ko"    | "Korean"  |
| "en"    | "English" |
| "zh"    | "Chinese" |
| "ja"    | "Japanese"|

---

## 참고: 응답 형식 차이

### Whisper
```python
segments, info = model.transcribe(audio)
# info.language_probability -> confidence
```

### Qwen3
```python
results: List[ASRTranscription] = model.transcribe(audio)
# results[0].language -> "Korean"
# results[0].text -> 전사 텍스트
# confidence 필드 없음 -> 기본값 1.0 사용
```

---

## 작성일: 2026-02-02
## 작성자: Claude Code
