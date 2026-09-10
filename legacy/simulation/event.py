from dataclasses import dataclass, field 
from typing import Dict, Any

@dataclass
class Event:
    tick: int
    entity_name: str
    action: str
    reason: str
    before: Dict[str, Any]
    after: Dict[str, Any]
    context: Dict[str, Any] = field(default_factory=dict) #contexto extra de tile e posições. 

