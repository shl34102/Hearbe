"""
pytest 공용 fixture 정의

김재환 담당 모듈 테스트용
"""

import pytest
import asyncio
from pathlib import Path


@pytest.fixture(scope="session")
def event_loop():
    """이벤트 루프 (세션 전체에서 재사용)"""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_flow_json():
    """샘플 플로우 JSON 데이터"""
    return {
        "flow_id": "test_flow",
        "flow_type": "search",
        "site": "test",
        "total_steps": 2,
        "steps": [
            {
                "step_id": 1,
                "name": "step1",
                "prompt": "첫 번째 단계입니다",
                "action": {
                    "tool_name": "navigate_to_url",
                    "arguments": {"url": "https://example.com"}
                },
                "next_step": 2
            },
            {
                "step_id": 2,
                "name": "step2",
                "prompt": "두 번째 단계입니다",
                "user_confirmation": True
            }
        ]
    }


@pytest.fixture
def sample_tool_call():
    """샘플 ToolCall 데이터"""
    return {
        "tool_name": "navigate_to_url",
        "arguments": {"url": "https://www.coupang.com"}
    }


@pytest.fixture
def sample_intent_result():
    """샘플 IntentResult 데이터"""
    return {
        "intent": "search",
        "site": "coupang",
        "parameters": {"keyword": "물티슈"},
        "confidence": 0.95,
        "requires_flow": False
    }


@pytest.fixture
def mock_openai_response():
    """Mock OpenAI API 응답"""
    return {
        "choices": [
            {
                "message": {
                    "content": '[{"tool_name": "navigate_to_url", "arguments": {"url": "https://example.com"}}]'
                }
            }
        ]
    }


@pytest.fixture
def temp_flows_dir(tmp_path):
    """임시 플로우 디렉토리 생성"""
    flows_dir = tmp_path / "flows"
    flows_dir.mkdir()

    # 쿠팡 디렉토리
    coupang_dir = flows_dir / "coupang"
    coupang_dir.mkdir()

    # 샘플 플로우 파일 생성
    search_flow = coupang_dir / "search.json"
    search_flow.write_text('''
    {
        "flow_id": "coupang_search",
        "flow_type": "search",
        "site": "coupang",
        "total_steps": 1,
        "steps": [
            {
                "step_id": 1,
                "name": "search",
                "prompt": "검색합니다"
            }
        ]
    }
    ''', encoding='utf-8')

    return flows_dir
