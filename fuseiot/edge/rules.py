import time
import asyncio
from typing import Dict, Any, List, Optional, Callable, Union
from dataclasses import dataclass, field
from enum import Enum

from ..logging_config import get_logger
from ..hub import Hub

logger = get_logger("edge.rules")


class Operator(Enum):
    EQ = "=="
    NE = "!="
    LT = "<"
    GT = ">"
    LE = "<="
    GE = ">="
    CONTAINS = "contains"
    CHANGED = "changed"


@dataclass
class Condition:
    """Rule condition."""
    device_id: str
    property: str
    operator: Union[Operator, str]
    value: Any = None
    
    def __post_init__(self):
        if isinstance(self.operator, str):
            self.operator = Operator(self.operator)
    
    def evaluate(self, hub: Hub) -> bool:
        """Evaluate condition against current state."""
        try:
            device = hub[self.device_id]
            current_value = getattr(device, self.property, None)
            
            if current_value is None:
                state = device.read_state()
                current_value = state.get(self.property)
            
            if self.operator == Operator.EQ:
                return current_value == self.value
            elif self.operator == Operator.NE:
                return current_value != self.value
            elif self.operator == Operator.LT:
                return current_value < self.value
            elif self.operator == Operator.GT:
                return current_value > self.value
            elif self.operator == Operator.LE:
                return current_value <= self.value
            elif self.operator == Operator.GE:
                return current_value >= self.value
            elif self.operator == Operator.CONTAINS:
                return self.value in current_value
            elif self.operator == Operator.CHANGED:
                # Always true, used for change detection
                return True
            
            return False
            
        except Exception as e:
            logger.error("condition_evaluate_failed", condition=self, error=str(e))
            return False


@dataclass
class Action:
    """Rule action."""
    device_id: str
    method: str
    params: Dict[str, Any] = field(default_factory=dict)
    delay: float = 0.0  # Delay in seconds
    
    async def execute(self, hub: Hub) -> bool:
        """Execute action."""
        try:
            if self.delay > 0:
                await asyncio.sleep(self.delay)
            
            device = hub[self.device_id]
            method_func = getattr(device, self.method, None)
            
            if method_func is None:
                logger.error("action_method_not_found", device=self.device_id, method=self.method)
                return False
            
            if asyncio.iscoroutinefunction(method_func):
                result = await method_func(**self.params)
            else:
                loop = asyncio.get_event_loop()
                result = await loop.run_in_executor(None, lambda: method_func(**self.params))
            
            return result.success if hasattr(result, 'success') else True
            
        except Exception as e:
            logger.error("action_execute_failed", action=self, error=str(e))
            return False


@dataclass
class Trigger:
    """Rule trigger (time-based or event-based)."""
    type: str  # "interval", "cron", "sunrise", "sunset"
    params: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Rule:
    """Automation rule."""
    name: str
    conditions: List[Condition]
    actions: List[Action]
    else_actions: Optional[List[Action]] = None
    enabled: bool = True
    last_triggered: Optional[float] = None
    
    def evaluate(self, hub: Hub) -> bool:
        """Evaluate all conditions."""
        return all(c.evaluate(hub) for c in self.conditions)


class RuleEngine:
    """Local automation rules engine."""
    
    def __init__(self, hub: Hub):
        self.hub = hub
        self.rules: List[Rule] = []
        self.running = False
        self._task: Optional[asyncio.Task] = None
    
    def add(self, rule: Rule) -> None:
        """Add a rule."""
        self.rules.append(rule)
        logger.info("rule_added", name=rule.name)
    
    def add_simple(
        self,
        name: str,
        if_condition: Condition,
        then_actions: List[Action],
        else_actions: Optional[List[Action]] = None
    ) -> Rule:
        """Add a simple rule."""
        rule = Rule(
            name=name,
            conditions=[if_condition],
            actions=then_actions,
            else_actions=else_actions
        )
        self.add(rule)
        return rule
    
    def remove(self, name: str) -> bool:
        """Remove a rule by name."""
        for i, rule in enumerate(self.rules):
            if rule.name == name:
                self.rules.pop(i)
                logger.info("rule_removed", name=name)
                return True
        return False
    
    async def evaluate(self) -> None:
        """Evaluate all rules once."""
        for rule in self.rules:
            if not rule.enabled:
                continue
            
            if rule.evaluate(self.hub):
                logger.info("rule_triggered", name=rule.name)
                rule.last_triggered = time.time()
                
                # Execute actions
                for action in rule.actions:
                    await action.execute(self.hub)
            else:
                # Execute else actions if conditions not met
                if rule.else_actions:
                    for action in rule.else_actions:
                        await action.execute(self.hub)
    
    async def run(self, interval: float = 5.0) -> None:
        """Run rules engine continuously."""
        self.running = True
        logger.info("rules_engine_started", interval=interval)
        
        while self.running:
            await self.evaluate()
            await asyncio.sleep(interval)
        
        logger.info("rules_engine_stopped")
    
    def start(self, interval: float = 5.0) -> None:
        """Start rules engine in background."""
        self._task = asyncio.create_task(self.run(interval))
    
    def stop(self) -> None:
        """Stop rules engine."""
        self.running = False
        if self._task:
            self._task.cancel()
    
    def list_rules(self) -> List[Dict[str, Any]]:
        """List all rules with status."""
        return [
            {
                "name": r.name,
                "enabled": r.enabled,
                "last_triggered": r.last_triggered,
                "conditions_count": len(r.conditions),
                "actions_count": len(r.actions)
            }
            for r in self.rules
        ]