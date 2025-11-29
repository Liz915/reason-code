import os
from src.reason_code.models.llm import LocalLoraModel

# 尝试导入 OpenAIAdapter
try:
    from src.reason_code.models.openai_adapter import OpenAIModel
except ImportError:
    OpenAIModel = None

class ModelRouter:
    def __init__(self):
        self.local_model = LocalLoraModel()
        self.remote_model = None

        # Adapter 内部会自动判断：没 Key -> Mock模式；有 Key -> 真实模式
        if OpenAIModel:
            self.remote_model = OpenAIModel()

    def get_model(self, complexity: str = "easy"):
        """
        根据任务复杂度选择模型
        """
        # 如果任务难，且远程模型可用（无论是 Mock 还是 Real），就切过去
        if complexity == "hard" and self.remote_model:
            return self.remote_model
        
        # 默认回退到本地模型
        return self.local_model

# 全局单例
router = ModelRouter()