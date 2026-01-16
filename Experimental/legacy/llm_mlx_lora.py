"""
Legacy local MLX + LoRA backend.
Not used in main experiments.
"""

import os
from typing import List
import structlog
from mlx_lm import load, generate

logger = structlog.get_logger(__name__)

class LocalLoraModel:
    def __init__(self, model_path: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct", adapter_path: str = "lora-reason-coder-v3"):
        self.model_path = model_path
        self.adapter_path = adapter_path
        self.model = None
        self.tokenizer = None
        self._load_model()

    def _load_model(self):
        logger.info("model_loading_start", base_model=self.model_path, device="cpu/gpu")
        
        try:
            # 检查适配器是否存在
            if os.path.exists(self.adapter_path):
                logger.info("loading_lora_weights", path=self.adapter_path)
                self.model, self.tokenizer = load(self.model_path, adapter_path=self.adapter_path)
                logger.info("✅ Local LoRA Model Loaded Successfully")
            else:
                logger.warning("⚠️ Adapter not found, loading base model", path=self.adapter_path)
                self.model, self.tokenizer = load(self.model_path)
        except Exception as e:
            logger.error("model_load_failed", error=str(e))
            raise e

    def generate(self, prompt: str, temperature: float = 0.7, max_new_tokens: int = 1024) -> str:
        messages = [{"role": "user", "content": prompt}]
        formatted_prompt = self.tokenizer.apply_chat_template(
            messages, add_generation_prompt=True, tokenize=False
        )
        
        output = generate(
            self.model,
            self.tokenizer,
            prompt=formatted_prompt,
            temp=temperature,
            max_tokens=max_new_tokens,
            verbose=False
        )
        return output

# 全局单例
try:
    llm_model = LocalLoraModel()
except Exception as e:
    logger.error("init_failed", error=str(e))
    llm_model = None

# 为了兼容 import，保留这个别名
_local_model = llm_model

# 恢复 MCTS 需要的异步接口 (用同步模拟异步)
async def generate_code_candidates(prompt: str, n: int = 1, temperature: float = 0.7) -> List[str]:
    """
    本地批量生成 (串行模拟)
    """
    candidates = []
    if llm_model:
        for _ in range(n):
            # 本地推理通常很快，或者是串行的，这里直接调
            code = llm_model.generate(prompt, temperature=temperature)
            candidates.append(code)
    return candidates
