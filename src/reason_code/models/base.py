from abc import ABC, abstractmethod
from typing import List

class BaseModel(ABC):
    @abstractmethod
    def generate(self, prompt: str, n: int = 1) -> List[str]:
        pass
    
    @abstractmethod
    def name(self) -> str:
        pass