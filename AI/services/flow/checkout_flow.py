"""
결제 플로우 관리

사이트별 결제 플로우 설정을 로드하고 단계별 명령을 생성합니다.
"""

import json
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional

logger = logging.getLogger(__name__)


# =============================================================================
# 데이터 클래스
# =============================================================================

@dataclass
class FlowAction:
    """플로우 단일 액션"""
    action: str  # click, fill, wait, wait_for
    selector: str = ""
    fallback_text: str = ""
    text: str = ""
    ms: int = 1000
    optional: bool = False


@dataclass
class FlowStep:
    """결제 플로우 단계"""
    id: str
    name: str
    actions: List[FlowAction]
    description: str = ""
    prompt: str = ""
    wait_for_user: bool = False
    requires_confirmation: bool = False
    options: List[Dict[str, str]] = field(default_factory=list)


@dataclass
class CheckoutConfig:
    """사이트별 결제 설정"""
    site: str
    name: str
    steps: List[FlowStep]
    selectors: Dict[str, str] = field(default_factory=dict)


# =============================================================================
# CheckoutFlowManager
# =============================================================================

class CheckoutFlowManager:
    """결제 플로우 관리자"""
    
    def __init__(self, config_dir: str = None):
        if config_dir is None:
            # 기본 경로: AI/config/checkout
            config_dir = Path(__file__).parent.parent.parent / "config" / "checkout"
        self.config_dir = Path(config_dir)
        self.configs: Dict[str, CheckoutConfig] = {}
        self._load_configs()
    
    def _load_configs(self):
        """설정 파일 로드"""
        if not self.config_dir.exists():
            logger.warning(f"결제 설정 디렉토리 없음: {self.config_dir}")
            return
        
        for file in self.config_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                config = self._parse_config(data)
                self.configs[config.site] = config
                logger.info(f"결제 설정 로드: {config.site} ({len(config.steps)}단계)")
            except Exception as e:
                logger.error(f"설정 로드 실패 ({file}): {e}")
    
    def _parse_config(self, data: Dict[str, Any]) -> CheckoutConfig:
        """JSON 데이터를 CheckoutConfig로 변환"""
        steps = []
        for step_data in data.get("steps", []):
            actions = []
            for action_data in step_data.get("actions", []):
                actions.append(FlowAction(
                    action=action_data.get("action", ""),
                    selector=action_data.get("selector", ""),
                    fallback_text=action_data.get("fallback_text", ""),
                    text=action_data.get("text", ""),
                    ms=action_data.get("ms", 1000),
                    optional=action_data.get("optional", False)
                ))
            
            steps.append(FlowStep(
                id=step_data.get("id", ""),
                name=step_data.get("name", ""),
                description=step_data.get("description", ""),
                actions=actions,
                prompt=step_data.get("prompt", ""),
                wait_for_user=step_data.get("wait_for_user", False),
                requires_confirmation=step_data.get("requires_confirmation", False),
                options=step_data.get("options", [])
            ))
        
        return CheckoutConfig(
            site=data.get("site", ""),
            name=data.get("name", ""),
            steps=steps,
            selectors=data.get("selectors", {})
        )
    
    def get_config(self, site: str) -> Optional[CheckoutConfig]:
        """사이트별 설정 조회"""
        return self.configs.get(site)
    
    def list_sites(self) -> List[str]:
        """지원 사이트 목록"""
        return list(self.configs.keys())
    
    def get_step(self, site: str, step_id: str) -> Optional[FlowStep]:
        """특정 단계 조회"""
        config = self.configs.get(site)
        if not config:
            return None
        for step in config.steps:
            if step.id == step_id:
                return step
        return None
    
    def get_next_step(self, site: str, current_step_id: str = None) -> Optional[FlowStep]:
        """다음 단계 조회"""
        config = self.configs.get(site)
        if not config or not config.steps:
            return None
        
        if current_step_id is None:
            return config.steps[0]
        
        for i, step in enumerate(config.steps):
            if step.id == current_step_id:
                if i + 1 < len(config.steps):
                    return config.steps[i + 1]
                return None
        
        return None
    
    def generate_step_commands(self, step: FlowStep) -> List[Dict[str, Any]]:
        """단계의 액션을 명령 목록으로 변환"""
        commands = []
        
        for action in step.actions:
            if action.action == "click":
                # 셀렉터 우선, fallback으로 텍스트 클릭
                if action.selector:
                    commands.append({
                        "tool_name": "click",
                        "arguments": {"selector": action.selector},
                        "description": f"{step.name} - 클릭"
                    })
                elif action.fallback_text:
                    commands.append({
                        "tool_name": "click_text",
                        "arguments": {"text": action.fallback_text},
                        "description": f"{step.name} - '{action.fallback_text}' 클릭"
                    })
            
            elif action.action == "fill":
                commands.append({
                    "tool_name": "fill",
                    "arguments": {
                        "selector": action.selector,
                        "text": action.text
                    },
                    "description": f"{step.name} - 입력"
                })
            
            elif action.action == "wait":
                commands.append({
                    "tool_name": "wait",
                    "arguments": {"ms": action.ms},
                    "description": f"대기 {action.ms}ms"
                })
            
            elif action.action == "wait_for":
                commands.append({
                    "tool_name": "wait",
                    "arguments": {"ms": 1000},
                    "description": f"{action.selector} 로딩 대기"
                })
        
        return commands


# =============================================================================
# 싱글톤
# =============================================================================

_manager: Optional[CheckoutFlowManager] = None

def get_checkout_manager() -> CheckoutFlowManager:
    """CheckoutFlowManager 싱글톤"""
    global _manager
    if _manager is None:
        _manager = CheckoutFlowManager()
    return _manager
