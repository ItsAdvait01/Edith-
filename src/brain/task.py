from dataclasses import dataclass, field
from typing import Any, Dict


@dataclass
class Task:
    """A structured action requested by the planner.

    Keeping tasks structured prevents the executor from rebuilding natural
    language only for a tool to parse it again.
    """

    tool: str
    action: str
    target: str = ""
    parameters: Dict[str, Any] = field(default_factory=dict)
    priority: int = 1
    status: str = "pending"
