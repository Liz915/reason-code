from abc import ABC, abstractmethod
from typing import Any, Dict

class BaseNode(ABC):
    def __init__(self, node_id: str, node_type: str):
        self.node_id = node_id
        self.node_type = node_type
        # 存储节点的配置 (比如 MCTS 的 simulation 次数)
        self.config = {}

    @abstractmethod
    async def execute(self, inputs: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """
        inputs: 上一个节点的输出
        context: 全局上下文 (Memory)
        """
        pass