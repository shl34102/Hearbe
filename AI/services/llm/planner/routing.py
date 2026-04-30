"""
Routing policy for rule vs LLM decisions.
"""

from dataclasses import dataclass
from typing import Dict, Set

from core.interfaces import IntentResult, IntentType

from ..generators.command_generator import CommandResult


@dataclass
class RoutingDecision:
    use_llm: bool
    reason: str


class LLMRoutingPolicy:
    def __init__(self):
        self.low_confidence_rules: Set[str] = {"site_access", "generic"}
        self.intent_rule_allowlist: Dict[IntentType, Set[str]] = {
            IntentType.SEARCH: {"search"},
            IntentType.SELECT_ITEM: {"select"},
            IntentType.ADD_TO_CART: {"cart"},
            IntentType.CHECKOUT: {"checkout"},
            IntentType.LOGIN: {"login"},
        }
        self.force_llm_intents: Set[IntentType] = {IntentType.SIGNUP}
        self.navigation_intents: Set[IntentType] = {
            IntentType.NAVIGATE,
            IntentType.UNKNOWN,
        }
        self.intent_confidence_threshold = 0.6

    def _is_hearbe_navigation_rule(self, rule_result: CommandResult) -> bool:
        # Hearbe typed-route navigation rules are intentionally "goto+wait" only.
        # Treat them as deterministic rules (do not force LLM) even if NLU misclassifies intent.
        return (
            bool(rule_result.matched_rule)
            and rule_result.matched_rule.startswith("hearbe_")
            and self._is_navigation_only(rule_result)
        )

    def decide(
        self,
        user_text: str,
        intent: IntentResult,
        rule_result: CommandResult,
    ) -> RoutingDecision:
        if rule_result.matched_rule in ("empty",):
            return RoutingDecision(use_llm=False, reason="empty_input")

        if rule_result.matched_rule in ("none", "llm_error"):
            return RoutingDecision(use_llm=True, reason="rule_miss")

        if not intent or intent.confidence < self.intent_confidence_threshold:
            return RoutingDecision(use_llm=False, reason="low_intent_confidence")

        intent_type = intent.intent
        allow_rules = self.intent_rule_allowlist.get(intent_type)
        if allow_rules is not None:
            if rule_result.matched_rule in allow_rules:
                return RoutingDecision(use_llm=False, reason="intent_rule_match")
            if self._is_low_confidence(rule_result) or (
                self._is_navigation_only(rule_result) and not self._is_hearbe_navigation_rule(rule_result)
            ):
                return RoutingDecision(use_llm=True, reason="intent_rule_mismatch_low_conf")
            return RoutingDecision(use_llm=False, reason="intent_rule_mismatch")

        if intent_type in self.force_llm_intents:
            if self._is_low_confidence(rule_result) or self._is_navigation_only(rule_result):
                return RoutingDecision(use_llm=True, reason="force_llm_intent")
            return RoutingDecision(use_llm=False, reason="force_llm_intent_rule_ok")

        if self._is_low_confidence(rule_result) and intent_type not in self.navigation_intents:
            return RoutingDecision(use_llm=True, reason="low_confidence_rule")

        if self._is_navigation_only(rule_result) and intent_type not in self.navigation_intents:
            return RoutingDecision(use_llm=True, reason="navigation_only")

        return RoutingDecision(use_llm=False, reason="rule_ok")

    def _is_low_confidence(self, rule_result: CommandResult) -> bool:
        return rule_result.matched_rule in self.low_confidence_rules

    def _is_navigation_only(self, rule_result: CommandResult) -> bool:
        if not rule_result.commands:
            return True
        return all(cmd.tool_name in {"goto", "wait"} for cmd in rule_result.commands)
