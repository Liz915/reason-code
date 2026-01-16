import structlog
# 重新指向本地模型
from src.reason_code.models.llm import llm_model

logger = structlog.get_logger(__name__)

class ModelRouter:
    def __init__(self):
        self.local_model = llm_model

    def route(self, complexity: str, prompt: str = ""):
        """
        强制路由到本地模型
        """
        # 返回模型实例
        return self.local_model

# 全局单例
router = ModelRouter()