from abc import ABC, abstractmethod
from typing import List
"""
Abstract interface for code generation backends.
"""
class BaseModel(ABC):
    @abstractmethod
    def generate(self, prompt: str, n: int = 1) -> List[str]:
        pass
    
    @abstractmethod
    def name(self) -> str:
        pass