"""
FlowEngine 유닛 테스트

담당: 김재환
"""

import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from pathlib import Path

from services.flow_engine import (
    FlowEngine,
    FlowDefinition,
    FlowStep,
    FlowContext,
    FlowState,
    FlowType,
    StepResult,
)


class TestFlowEngine:
    """FlowEngine 테스트"""

    # ---- 초기화 테스트 ----

    def test_init(self):
        """엔진 초기화"""
        engine = FlowEngine()

        assert engine._flows_dir is not None
        assert len(engine._loaded_flows) == 0
        assert len(engine._active_contexts) == 0

    def test_init_with_custom_path(self, tmp_path):
        """커스텀 경로로 초기화"""
        engine = FlowEngine(flows_dir=str(tmp_path))

        assert engine._flows_dir == tmp_path

    # ---- 플로우 로딩 테스트 ----

    @pytest.mark.asyncio
    async def test_load_flow_file(self, tmp_path):
        """플로우 파일 로딩"""
        # 테스트용 플로우 JSON 생성
        flow_dir = tmp_path / "coupang"
        flow_dir.mkdir()

        flow_file = flow_dir / "search.json"
        flow_file.write_text('''
        {
            "flow_id": "test_search",
            "flow_type": "search",
            "site": "coupang",
            "total_steps": 1,
            "steps": [
                {
                    "step_id": 1,
                    "name": "test_step",
                    "prompt": "테스트입니다"
                }
            ]
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        assert "test_search" in engine._loaded_flows

    @pytest.mark.asyncio
    async def test_get_flow(self, tmp_path):
        """플로우 조회"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "my_flow",
            "flow_type": "search",
            "site": "test",
            "total_steps": 1,
            "steps": []
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        flow = engine.get_flow("my_flow")
        assert flow is not None
        assert flow.flow_id == "my_flow"

    @pytest.mark.asyncio
    async def test_get_flow_not_found(self):
        """존재하지 않는 플로우 조회"""
        engine = FlowEngine()

        flow = engine.get_flow("nonexistent")
        assert flow is None

    @pytest.mark.asyncio
    async def test_list_flows(self, tmp_path):
        """플로우 목록 조회"""
        flow_dir = tmp_path / "site"
        flow_dir.mkdir()

        for name in ["flow1", "flow2"]:
            flow_file = flow_dir / f"{name}.json"
            flow_file.write_text(f'''
            {{
                "flow_id": "{name}",
                "flow_type": "search",
                "site": "site",
                "total_steps": 1,
                "steps": []
            }}
            ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        flows = engine.list_flows()
        assert len(flows) == 2
        assert "flow1" in flows
        assert "flow2" in flows

    # ---- 플로우 시작 테스트 ----

    @pytest.mark.asyncio
    async def test_start_flow(self, tmp_path):
        """플로우 시작"""
        flow_dir = tmp_path / "coupang"
        flow_dir.mkdir()

        flow_file = flow_dir / "search.json"
        flow_file.write_text('''
        {
            "flow_id": "coupang_search",
            "flow_type": "search",
            "site": "coupang",
            "total_steps": 2,
            "steps": [
                {"step_id": 1, "name": "step1", "prompt": "첫 번째"},
                {"step_id": 2, "name": "step2", "prompt": "두 번째"}
            ]
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        context = await engine.start_flow(
            session_id="session-1",
            flow_id="coupang_search",
            initial_data={"keyword": "물티슈"}
        )

        assert context.state == FlowState.STARTED
        assert context.current_step_index == 0
        assert context.collected_data["keyword"] == "물티슈"

    @pytest.mark.asyncio
    async def test_start_flow_not_found(self):
        """존재하지 않는 플로우 시작"""
        engine = FlowEngine()

        with pytest.raises(ValueError) as exc_info:
            await engine.start_flow("session-1", "nonexistent")

        assert "Flow not found" in str(exc_info.value)

    # ---- 단계 실행 테스트 ----

    @pytest.mark.asyncio
    async def test_execute_step(self, tmp_path):
        """단계 실행"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "test_flow",
            "flow_type": "search",
            "site": "test",
            "total_steps": 1,
            "steps": [
                {
                    "step_id": 1,
                    "name": "navigate",
                    "prompt": "사이트에 접속합니다",
                    "action": {
                        "tool_name": "navigate_to_url",
                        "arguments": {"url": "https://example.com"}
                    }
                }
            ]
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        await engine.start_flow("session-1", "test_flow")
        result = await engine.execute_step("session-1")

        assert result.success is True
        assert len(result.tool_calls) == 1
        assert result.tool_calls[0]["tool_name"] == "navigate_to_url"

    @pytest.mark.asyncio
    async def test_execute_step_no_active_flow(self):
        """활성 플로우 없이 단계 실행"""
        engine = FlowEngine()

        result = await engine.execute_step("no-session")

        assert result.success is False
        assert "No active flow" in result.error

    # ---- 사용자 입력 처리 테스트 ----

    @pytest.mark.asyncio
    async def test_handle_user_input_positive(self, tmp_path):
        """긍정 응답 처리"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "test_flow",
            "flow_type": "checkout",
            "site": "test",
            "total_steps": 2,
            "steps": [
                {
                    "step_id": 1,
                    "name": "confirm",
                    "prompt": "진행할까요?",
                    "user_confirmation": true,
                    "next_step": 2
                },
                {
                    "step_id": 2,
                    "name": "done",
                    "prompt": "완료되었습니다"
                }
            ]
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        await engine.start_flow("session-1", "test_flow")
        await engine.execute_step("session-1")

        result = await engine.handle_user_input("session-1", "네")

        assert result.success is True

    @pytest.mark.asyncio
    async def test_handle_user_input_negative(self, tmp_path):
        """부정 응답 처리 (취소)"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "test_flow",
            "flow_type": "checkout",
            "site": "test",
            "total_steps": 1,
            "steps": [
                {
                    "step_id": 1,
                    "name": "confirm",
                    "prompt": "진행할까요?",
                    "user_confirmation": true
                }
            ]
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        await engine.start_flow("session-1", "test_flow")
        await engine.execute_step("session-1")

        result = await engine.handle_user_input("session-1", "아니")

        assert result.success is False
        assert "User cancelled" in result.error

    # ---- MCP 결과 처리 테스트 ----

    @pytest.mark.asyncio
    async def test_handle_step_result_success(self, tmp_path):
        """MCP 성공 결과 처리"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "test_flow",
            "flow_type": "search",
            "site": "test",
            "total_steps": 2,
            "steps": [
                {"step_id": 1, "name": "step1", "prompt": "1단계", "next_step": 2},
                {"step_id": 2, "name": "step2", "prompt": "2단계"}
            ]
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        await engine.start_flow("session-1", "test_flow")

        result = await engine.handle_step_result(
            "session-1",
            {"success": True}
        )

        # 다음 단계로 진행
        context = engine._active_contexts["session-1"]
        assert context.current_step_index == 1

    @pytest.mark.asyncio
    async def test_handle_step_result_failure_retry(self, tmp_path):
        """MCP 실패 시 재시도"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "test_flow",
            "flow_type": "search",
            "site": "test",
            "total_steps": 1,
            "steps": [
                {"step_id": 1, "name": "step1", "prompt": "실행", "fallback": "실패했습니다"}
            ]
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        await engine.start_flow("session-1", "test_flow")

        result = await engine.handle_step_result(
            "session-1",
            {"success": False, "error": "timeout"}
        )

        assert result.success is False
        context = engine._active_contexts["session-1"]
        assert context.retry_count == 1

    # ---- 진행률 테스트 ----

    @pytest.mark.asyncio
    async def test_get_progress(self, tmp_path):
        """진행률 조회"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "test_flow",
            "flow_type": "search",
            "site": "test",
            "total_steps": 5,
            "steps": []
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        await engine.start_flow("session-1", "test_flow")

        progress = engine.get_progress("session-1")
        assert progress == "1/5"

    # ---- 플로우 중단 테스트 ----

    @pytest.mark.asyncio
    async def test_abort_flow(self, tmp_path):
        """플로우 중단"""
        flow_dir = tmp_path / "test"
        flow_dir.mkdir()

        flow_file = flow_dir / "flow.json"
        flow_file.write_text('''
        {
            "flow_id": "test_flow",
            "flow_type": "search",
            "site": "test",
            "total_steps": 1,
            "steps": []
        }
        ''', encoding='utf-8')

        engine = FlowEngine(flows_dir=str(tmp_path))
        await engine.initialize()

        await engine.start_flow("session-1", "test_flow")

        result = await engine.abort_flow("session-1")

        assert result is True
        assert "session-1" not in engine._active_contexts

    @pytest.mark.asyncio
    async def test_abort_flow_not_found(self):
        """존재하지 않는 플로우 중단"""
        engine = FlowEngine()

        result = await engine.abort_flow("nonexistent")
        assert result is False

    # ---- 리소스 정리 테스트 ----

    @pytest.mark.asyncio
    async def test_close(self):
        """리소스 정리"""
        engine = FlowEngine()
        await engine.close()

        assert len(engine._active_contexts) == 0
        assert len(engine._loaded_flows) == 0
