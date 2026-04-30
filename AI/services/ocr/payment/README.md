# Payment OCR (필요 데이터 / 추출 데이터)

## 필요한 데이터

1) 결제 키패드 **이미지 파일**
- 예: `../tests/fixtures/결제.png`

2) **DOM 키 순서 배열** (`dom_keys.json`)
- 키패드 버튼의 실제 DOM 식별자(예: `data-key`, `id`, `class`)를
  **화면 표시 순서대로** 0~9 배열로 제공
- 없으면 기본값 `["0","1","2","3","4","5","6","7","8","9"]` 사용

예시:
```json
["key-0","key-1","key-2","key-3","key-4","key-5","key-6","key-7","key-8","key-9"]
```

---

## 추출되는 데이터

### 최종 출력 파일
- `output/<이미지명>_mapped.json`

### 출력 형식
- 숫자 → DOM 키 매핑 JSON

예시:
```json
{
  "digits": ["2","6","8","0","9","7","3","5","4","1"],
  "dom_keys": ["key-0","key-1","key-2","key-3","key-4","key-5","key-6","key-7","key-8","key-9"],
  "digit_to_key_mapping": {
    "2": "key-0",
    "6": "key-1",
    "8": "key-2",
    "0": "key-3",
    "9": "key-4",
    "7": "key-5",
    "3": "key-6",
    "5": "key-7",
    "4": "key-8",
    "1": "key-9"
  }
}
```
