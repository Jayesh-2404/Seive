"""Domain models."""
from dataclasses import dataclass
@dataclass
class User:
    id: int; name: str; email: str
@dataclass
class Order:
    id: int; uid: int; total: float; ts: str
