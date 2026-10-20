from dataclasses import dataclass
from typing import Any


@dataclass
class HiddenEvent:
    tick: int
    event: Any
