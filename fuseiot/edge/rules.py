from typing import Callable, Dict, Any
from ..hub import Hub

class EdgeRules:
    """Manages edge computing rules."""

    def __init__(self, hub: Hub):
        self._hub = hub
        self._rules: Dict[str, Callable[[Any], None]] = {}

    def add_rule(self, rule_id: str, condition: Callable[[Any], bool], action: Callable[[], None]) -> None:
        """Add a rule."""
        def wrapped(event):
            if condition(event):
                action()
        self._rules[rule_id] = wrapped

    def process_event(self, event: Any) -> None:
        """Process an event against rules."""
        for rule in self._rules.values():
            rule(event)