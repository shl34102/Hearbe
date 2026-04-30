# OCR 텍스트를 LLM으로 요약
import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

import requests
from typing import Dict, List, Tuple

try:
    from .product_type_detector import (
        ProductType,
        detect_product_type,
        get_keywords_for_type,
        get_type_description,
        is_keyword_valid_for_type
    )
except ImportError:
    from product_type_detector import (
        ProductType,
        detect_product_type,
        get_keywords_for_type,
        get_type_description,
        is_keyword_valid_for_type
    )

try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent / ".env"
    load_dotenv(dotenv_path=env_path)
except ImportError:
    pass

DEFAULT_INPUT = os.path.join("output", "샴푸_res_texts.json")
DEFAULT_OUTPUT = os.path.join("output", "샴푸_texts_summary.json")

try:
    from .ocr_text_preprocessor import load_and_preprocess_ocr_json
    PREPROCESSOR_AVAILABLE = True
except ImportError:
    try:
        from ocr_text_preprocessor import load_and_preprocess_ocr_json
        PREPROCESSOR_AVAILABLE = True
    except ImportError:
        PREPROCESSOR_AVAILABLE = False


def _load_ocr_texts(path: str, preprocess: bool = True) -> Tuple[List[str], Dict]:
    with open(path, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    if preprocess and PREPROCESSOR_AVAILABLE:
        texts, stats = load_and_preprocess_ocr_json(data, min_score=0.7, min_length=2, verbose=True)
    else:
        texts = data.get("rec_texts") or []
        texts = [t.strip() for t in texts if isinstance(t, str) and t.strip()]
    
    return texts, data


def _build_prompt(texts: List[str], product_type: ProductType, size_table: str = None) -> Dict[str, str]:
    numbered = "\n".join(f"{i + 1}. {t}" for i, t in enumerate(texts))

    system = (
        "당신은 시각장애인 사용자에게 제품을 대신 읽어주는 **따뜻하고 친절한 쇼핑 친구**이자, "
        "안전을 책임지는 **꼼꼼한 확인자**입니다. "
        "기계적인 요약 대신 **사용자가 바로 옆에 있는 것처럼** 제품의 매력(소재, 기능, 맛, 특징)을 생생하게 설명하세요. "
        "단, 안전과 직결된 **숫자, 유통기한, 전압, 성분 등은 절대로 추측하지 말고** OCR 텍스트에 적힌 그대로 정확하게 전달해야 합니다."
        "원산지 정보도 꼭 전달해주세요"
    )
    
    # 의류/신발/패션잡화일 때 사이즈 정보 필수 지시
    size_instruction = ""
    if product_type in [ProductType.의류, ProductType.신발, ProductType.패션잡화]:
        size_instruction = (
            "\n\n**🔴 의류/신발 사이즈 정보 필수 전달 규칙**\n"
            "이 제품은 의류/신발/패션잡화입니다. OCR 텍스트에 SIZE 표나 실측 정보가 있다면:\n"
            "1. **summary**에 사이즈 정보를 **모든 사이즈별로 자세히** 포함하세요.\n"
            "   - 의류 예: \"사이즈는 M(허리 34, 영덩이 67, 총장 103), L(허리 36, 영덩이 69, 총장 105)...\"\n"
            "   - SIZE 표의 **모든 항목**(허리, 엉덩이, 밑위, 허벅지, 밑단, 총장 등)을 빠짐없이 포함하세요.\n"
            "2. **(중요) 신발 사이즈 추출 규칙**:\n"
            "   - 신발의 경우 mm 사이즈(예: 240, 245, 250...)와 EU/국제 사이즈(예: 38, 39, 40...)가 **나열**되어 있습니다.\n"
            "   - **⚠️ 필수: OCR 텍스트에서 사이즈 관련 숫자를 모두 찾아 최소값~최대값 전체 범위를 추출하세요.**\n"
            "   - mm 사이즈는 보통 230~290 범위, EU 사이즈는 35~50 범위입니다.\n"
            "   - 예: OCR에 '240', '245', '250', '255', '260', '265', '270', '275'가 있으면 → \"240-275mm\" (240부터!)\n"
            "   - 예: OCR에 '38', '39', '40', '42', '43', '44', '45'가 있으면 → \"38-45\" (38부터!)\n"
            '   - 숫자 1이 흔히 7로 오인식 되는 경우가 많습니다. 텍스트에서 전체 숫자 흐름을 파악하고 오인식된 숫자를 수정하세요.\n'
            "3. **(중요) 줄글로 나열된 표 해석 가이드**:\n"
            "   OCR 결과가 표 구조 없이 'M 34 67 35...' 처럼 줄글로 나열돼 있어도 당황하지 마세요.\n"
            "   - **패턴 인식**: '허리, 엉덩이, 총장, 기장, 가슴둘레, 어깨넓이, 어깨너비, 소매길이' 같은 헤더가 먼저 나오고, 그 뒤에 'M', 'L' 같은 행(Row) 시작점이 나옵니다.\n"
            "   - **매핑**: 행 시작점(M) 뒤에 나오는 숫자들을 순서대로 헤더와 매칭하세요. (예: M -> 첫번째숫자(허리) -> 두번째숫자(엉덩이)...)\n"
            "4. **keywords**에도 \"사이즈\" 항목을 만들고, 동일한 내용을 포함하세요.\n"
            "5. 표에 있는 수치는 **절대 추측하지 말고** OCR 텍스트 그대로 옮기세요.\n"
        )

    instructions = (
        "다음 OCR 텍스트를 분석하여 친구에게 말해주듯이 JSON 형식으로 응답하세요."
        + size_instruction
        + "\n\n"
        "**💡 1단계: 냉철한 팩트 체크 (Strict Check)**\n"
        "- **추측 금지**: 텍스트에 없는 내용을 상상해서 채워 넣지 마세요.\n"
        "- **숫자/단위**: 용량, 사이즈(cm), 무게(g), 전압(V), 개수 등은 텍스트 그대로 정확히 찾으세요.\n"
        "- **안전 정보**: 유통기한, KC인증, 전격전압, 알레르기 주의사항 등 안전과 관련된 정보는 **원문 그대로** 추출하세요. 명백한 오타만 문맥에 맞게 수정하세요.\n"
        "- **소비기한**: 소비기한, 유통기한은 다루지 마세요.\n"
        "- **🚫 선택형 옵션 목록(PRODUCT INFO 스케일) 완전 제외**:\n"
        "   쇼핑몰 상세페이지에는 '핏/두께감/촉감/신축성' 등의 카테고리별로 **3~4개 선택지를 나열한 스케일(척도)** 형태의 PRODUCT INFO가 자주 등장합니다.\n"
        "   이 선택지들은 이미지 상에서 하나만 체크/강조되어 있지만, OCR은 **모든 선택지 텍스트를 동시에 추출**하므로 어떤 값이 실제 선택되었는지 알 수 없습니다.\n"
        "   따라서 아래 규칙을 따르세요:\n\n"
        "   **[인식 방법]** 다음 중 하나라도 해당하면 선택형 옵션입니다:\n"
        "   - 카테고리명 + 슬래시(/)나 가운뎃점(·)으로 구분된 2~4개 선택지가 나열된 패턴\n"
        "   - 영문+한글 병기 카테고리 헤더: EDITION TYPE/핏, THICKNESS/두께감, SOFT/촉감, ELASTICITY/신축성, SEASON/계절, LINING/안감, TRANSPARENCY/비침 등\n"
        "   - 스케일(낮음→높음) 형태로 배치된 텍스트: 예) '얇음 - 적당함 - 두꺼움', '없음 - 약간 있음 - 좋음'\n\n"
        "   **[제외 대상 카테고리와 흔한 선택지 변형]** (아래 단어와 정확히 일치하지 않아도, 의미가 유사하면 모두 제외):\n"
        "   - 핏/핏감: 슬림핏, 슬림, 적당함, 보통, 레귤러, 루즈핏, 루즈, 오버핏\n"
        "   - 두께감: 얇음, 얇은, 적당함, 보통, 두꺼움, 두꺼운\n"
        "   - 촉감: 약간 뻣뻣함, 뻣뻣함, 까끌거림, 적당함, 보통, 부드러움, 부드러운\n"
        "   - 신축성: 없음, 약간 있음, 보통, 좋음, 매우 좋음\n"
        "   - 비침정도/비침: 있음, 약간 있음, 보통, 없음\n"
        "   - 안감: 있음, 없음, 기모안감, 기모\n"
        "   - 계절/시즌: 봄, 여름, 가을, 겨울, 봄&가을, 사계절\n"
        "   - 세탁방법: 손세탁, 드라이클리닝, 기계세탁\n\n"
        "   **[핵심 원칙]** 위 카테고리에 해당하는 선택형 정보는 설령 OCR 텍스트에 포함되어 있더라도 summary와 keywords 모두에서 **완전히 제외**하세요.\n"
        "   단, 소재(100% 면 등)나 사이즈 표처럼 **사실 확인이 가능한 정보**는 제외 대상이 아닙니다.\n"
        "**💖 2단계: 매력 포인트 발견 (Rich Description)**\n"
        "- 딱딱한 스펙 외에, 포장지에 적힌 **설명 문구**를 적극적으로 찾으세요.\n"
        "- **(범용 예시)**:\n"
        "   - 식품: \"진한 풍미\", \"부드러운 식감\", \"국산 원료\"\n"
        "   - 의류/잡화: \"통기성 좋은 매쉬\", \"구김 없는 소재\", \"편안한 착용감\"\n"
        "   - 가전/생활: \"저소음 설계\", \"초고속 충전\", \"자극 없는 순면\"\n"
        "- 단순히 \"제품입니다\"라고 하지 말고, **\"통기성이 좋아서 시원한 여름용 티셔츠\"** 또는 **\"진한 버섯 풍미가 가득한 스프\"**처럼 수식어를 살려주세요.\n\n"
        "**✍️ 3단계: 친절한 말하기 (요약 작성)**\n"
        "다음 흐름으로 **3~6문장**의 이야기를 들려주세요. (~해요/네요 체 사용)\n"
        "1. **첫인상**: \"이건 [브랜드]의 **[제품명]**이에요. 포장지에 [매력 포인트/수식어]라고 적혀 있네요.\"\n"
        "2. **상세 설명**: \"이 제품은 [소재/스펙]이고, [주요 특징]이 돋보이는 제품이에요. [용도/상황]에 쓰기 좋을 것 같아요.\"\n"
        "3. **사이즈(의류만)**: 의류/신발이고 SIZE 표가 있다면, **모든 사이즈의 실측 치수를 자세히** 설명하세요.\n"
        "   - 예: \"사이즈는 M(허리 34, 엉덩이 67, 허벅지 38, 밑단 24.5, 총장 103), L(허리 36, 엉덩이 69, 허벅지 39.5, 밑단 25.5, 총장 105), XL(허리 38, 엉덩이 72, 허벅지 41, 밑단 26.5, 총장 107), 2XL(허리 40, 엉덩이 75, 허벅지 42.5, 밑단 27.5, 총장 108)로 나와요.\"\n"
        "4. **사용/관리**: OCR 텍스트에 세탁법, 사용법, 조리법 등이 **명시적으로 적혀 있을 때만** 해당 내용을 그대로 전달하세요. "
        "**⚠️ 텍스트에 관련 내용이 없으면 이 항목을 반드시 생략하세요. 절대로 추측하거나 일반 상식으로 채워 넣지 마세요.**\n"
        "5. **안전 챙김**: OCR 텍스트에 주의사항, 알레르기, 정격전압 등이 **명시적으로 적혀 있을 때만** 전달하세요. "
        "**텍스트에 없으면 반드시 생략하세요.**\n\n"
        "**출력 JSON 형식:**\n"
        "{\n"
        "  \"product_type\": \"자동 감지한 제품군\",\n"
        "  \"product_name\": \"제품명\",\n"
        "  \"confidence\": 1.0,\n"
        "  \"summary\": [\n"
        "    \"이야기하듯 작성한 첫 번째 문장\",\n"
        "    \"두 번째 문장\",\n"
        "    \"세 번째 문장...\"\n"
        "  ],\n"
        "  \"keywords\": {\n"
        "    \"키워드1(예: 소재/성분)\": { \"answer\": \"내용\", \"status\": \"found|not_found\" },\n"
        "    \"키워드2(예: 사이즈/용량)\": { \"answer\": \"내용\", \"status\": \"found|not_found\" },\n"
        "    \"키워드3(자동생성)\": { \"answer\": \"내용\", \"status\": \"found|not_found\" }\n"
        "  }\n"
        "}\n"
    )
    
    user = "분석할 OCR 텍스트:\n" + numbered

    # SIZE 표가 재구성되었으면 추가
    if size_table:
        user += "\n\n**📏 재구성된 SIZE 표 (좌표 기반 정렬)**:\n"
        user += "```\n"
        user += size_table
        user += "\n```\n"
        user += "위 표를 참고하여 모든 사이즈 정보를 정확히 요약에 포함하세요."

    return {"system": system, "instructions": instructions, "user": user}


def _call_openai(prompt: Dict[str, str], max_retries: int = 3) -> Dict:
    api_key = os.environ.get("GMS_API_KEY")
    if not api_key:
        raise RuntimeError("GMS_API_KEY 환경변수가 설정되지 않았습니다.")

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    url = "https://gms.ssafy.io/gmsapi/api.openai.com/v1/chat/completions"

    messages = [
        {
            "role": "developer",
            "content": prompt["system"] + "\n\n" + prompt["instructions"]
        },
        {
            "role": "user",
            "content": prompt["user"]
        }
    ]

    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.1,
    }

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    last_error = None
    for attempt in range(max_retries):
        try:
            response = requests.post(
                url,
                json=payload,
                headers=headers,
                timeout=(10, 120),
            )
            response.raise_for_status()
            raw = response.json()

            choices = raw.get("choices", [])
            if not choices:
                raise RuntimeError("LLM 응답에 choices가 없습니다.")
            
            output_text = choices[0].get("message", {}).get("content", "")
            if not output_text:
                raise RuntimeError("LLM 응답 내용이 비어있습니다.")

            # JSON 객체 추출: 코드블록 감싸기, 전후 텍스트 등 다양한 LLM 출력 대응
            json_match = re.search(r'\{[\s\S]*\}', output_text)
            if json_match:
                output_text = json_match.group()

            try:
                return json.loads(output_text)
            except json.JSONDecodeError:
                last_error = ValueError(f"LLM 응답이 유효한 JSON이 아닙니다: {output_text[:200]}")
                if attempt < max_retries - 1:
                    wait_time = 2 ** attempt
                    time.sleep(wait_time)
                    continue
                raise RuntimeError(f"LLM이 {max_retries}회 시도 후에도 유효한 JSON을 반환하지 않았습니다.") from last_error

        except requests.exceptions.RequestException as e:
            last_error = e
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt
                time.sleep(wait_time)
            else:
                raise RuntimeError(f"LLM 요청이 {max_retries}회 재시도 후에도 실패했습니다: {last_error}") from last_error


def summarize_texts(
    texts: List[str],
    product_type: ProductType = None,
    verbose: bool = True,
    use_cache: bool = True,
    prompt_version: str = "v1",
    size_table: str = None,
) -> Dict:
    if not texts:
        return {
            "product_type": "기타",
            "product_name": "알 수 없음",
            "confidence": 0.0,
            "summary": ["텍스트가 없어 요약할 수 없습니다."],
            "keywords": {},
            "error": "입력 텍스트가 비어있습니다."
        }
    
    if product_type is None:
        product_type = detect_product_type(texts)

    prompt = _build_prompt(texts, product_type, size_table)

    summary = _call_openai(prompt)

    return summary


def _write_json(path: str, data: Dict) -> None:
    dir_path = os.path.dirname(path)
    if dir_path:
        os.makedirs(dir_path, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def _normalize(text: str) -> str:
    return "".join(text.lower().split())


def _build_keyword_aliases() -> Dict[str, List[str]]:
    return {
        "가격": ["가격", "price", "값", "얼마", "비용"],
        "제품명": ["제품명", "상품명", "이름", "product", "name", "뭐에요"],
        "특징": ["특징", "특성", "설명", "소개", "맛", "식감"],
        "브랜드/캐릭터": ["브랜드", "캐릭터", "제조사", "만든곳"],
        "섭취방법": ["섭취", "먹는법", "먹는 방법", "조리", "전자레인지", "어떻게 먹어"],
        "중량/용량": ["중량", "용량", "그램", "g", "ml", "리터", "양", "무게"],
        "원재료/성분": ["원재료", "성분", "재료", "ingredient", "뭐가 들어"],
        "알레르기": ["알레르기", "알러지", "allergy", "주의성분"],
        "보관방법": ["보관", "보관방법", "보관법", "온도", "냉장", "냉동"],
        "유통기한": ["유통기한", "소비기한", "기한", "expiry", "언제까지"],
        "영양정보": ["영양", "영양정보", "칼로리", "kcal", "열량"],
        "주의사항": ["주의", "주의사항", "경고", "조심"],
        "기타": ["기타", "참고"],
    }


def _find_keyword_key(question: str, keywords: Dict[str, Dict]) -> str:
    normalized = _normalize(question)
    aliases = _build_keyword_aliases()
    
    for key, tokens in aliases.items():
        for token in tokens:
            if _normalize(token) in normalized:
                if key in keywords:
                    return key
    return ""


def _answer_query(summary: Dict, question: str) -> str:
    product_type_str = summary.get("product_type", "기타")
    try:
        product_type = ProductType(product_type_str)
    except ValueError:
        product_type = ProductType.기타
    
    keywords = summary.get("keywords", {})
    key = _find_keyword_key(question, keywords)
    
    if not key:
        available = ", ".join(keywords.keys())
        return f"죄송합니다. 질문과 일치하는 정보를 찾지 못했습니다.\n알려드릴 수 있는 정보: {available}"
    
    if not is_keyword_valid_for_type(product_type, key):
        type_desc = get_type_description(product_type)
        return f"이 제품은 '{type_desc}'이므로 '{key}'에 대한 정보는 없습니다."
    
    item = keywords.get(key, {})
    status = item.get("status", "not_found")
    answer = item.get("answer", "OCR 텍스트에 없음")
    
    if status != "found":
        return f"죄송합니다. '{key}'에 대한 정보가 포장에 적혀있지 않습니다."
        
    return f"{key}: {answer}"


def main() -> int:
    parser = argparse.ArgumentParser(description="OCR 결과를 분석하여 JSON으로 요약")
    parser.add_argument("--input", default=DEFAULT_INPUT)
    parser.add_argument("--output", default=DEFAULT_OUTPUT)
    parser.add_argument("--query", default="")
    args = parser.parse_args()

    if args.query:
        if not os.path.exists(args.output):
            print(f"오류: 요약 파일({args.output})을 찾을 수 없습니다.")
            return 1
        with open(args.output, "r", encoding="utf-8") as f:
            summary = json.load(f)
        print(_answer_query(summary, args.query))
        return 0

    print(f"분석 시작: {args.input}")
    
    texts, _ = _load_ocr_texts(args.input)
    if not texts:
        print("오류: 유효한 OCR 텍스트가 없습니다.")
        return 1

    product_type = detect_product_type(texts)
    type_desc = get_type_description(product_type)
    print(f"감지된 제품 타입: {product_type.value} ({type_desc})")
    print(f"추출 목표 키워드: {', '.join(get_keywords_for_type(product_type))}")

    prompt = _build_prompt(texts, product_type, None)

    print("LLM 분석 중...", end="", flush=True)
    summary = _call_openai(prompt)
    print(" 완료!")
    
    summary["source_file"] = args.input
    _write_json(args.output, summary)
    print(f"요약 결과가 저장되었습니다: {args.output}")
    
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
