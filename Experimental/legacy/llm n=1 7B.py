"""
Reason-Code Local LLM (7B 4-bit Quantized Version)
"""
import os
import inspect
import re
from typing import List
import structlog
from mlx_lm import load, generate

logger = structlog.get_logger(__name__)

# 🔥 核心修改：切换到 MLX 社区优化的 4-bit 量化版
# 这个模型只有 5GB 大小，跑起来飞快，且精度几乎无损
BASE_MODEL = os.getenv("BASE_MODEL_NAME", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")

class LocalMLXModel:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load()

    def _load(self):
        logger.info("model_loading_start", backend="mlx", base_model=BASE_MODEL)
        # MLX 会自动识别量化配置
        self.model, self.tokenizer = load(BASE_MODEL)
        logger.info("base_model_loaded", backend="mlx")

    def strip_markdown(self, code: str) -> str:
        code = re.sub(r"^```python\s*", "", code, flags=re.MULTILINE)
        code = re.sub(r"^```\s*", "", code, flags=re.MULTILINE)
        code = re.sub(r"```\s*$", "", code, flags=re.MULTILINE)
        return code.strip()

    def generate(self, prompt: str, num_return_sequences: int = 1, temperature: float = 0.7, max_tokens: int = 512) -> List[str]:
        system_content = (
            "You are a professional coding assistant. "
            "Provide valid Python code to solve the problem. "
            "Wrap your code in ```python ... ``` blocks. "
            "Do NOT provide explanations, thinking processes, or test cases. "
            "Just print the code."
        )
        
        candidates: List[str] = []
        sig = inspect.signature(generate)
        supported_args = sig.parameters.keys()
        
        gen_kwargs = {
            "model": self.model, 
            "tokenizer": self.tokenizer, 
            "verbose": False
        }
        
        if "max_tokens" in supported_args: gen_kwargs["max_tokens"] = max_tokens
        elif "max_new_tokens" in supported_args: gen_kwargs["max_new_tokens"] = max_tokens

        # 采样策略 (保持 7B 的甜区配置)
        do_sample = num_return_sequences > 1
        
        if do_sample:
            final_temp = 0.85 
            if "temperature" in supported_args: gen_kwargs["temperature"] = final_temp
            elif "temp" in supported_args: gen_kwargs["temp"] = final_temp
            
            if "top_p" in supported_args: gen_kwargs["top_p"] = 0.95 
            if "top_k" in supported_args: gen_kwargs["top_k"] = 50 
        else:
            if "temperature" in supported_args: gen_kwargs["temperature"] = 0.0
            elif "temp" in supported_args: gen_kwargs["temp"] = 0.0

        for i in range(num_return_sequences):
            try:
                current_prompt = prompt
                if i > 0:
                    current_prompt += f"\n# variation {i}"
                
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": current_prompt}
                ]
                formatted_prompt = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)

                output = generate(prompt=formatted_prompt, **gen_kwargs)
                code = self.strip_markdown(output)
                if code: candidates.append(code)
            except Exception as e:
                logger.error("generation_failed", error=str(e))
                continue
        return candidates

_instance = LocalMLXModel()
_local_model = _instance
llm_model = _instance

async def generate_code_candidates(prompt: str, n: int = 1, mode: str = "default") -> List[str]:
    if mode == "reflexion": max_tokens = 800 
    else: max_tokens = 640 
    return _instance.generate(prompt, num_return_sequences=n, temperature=0.7, max_tokens=max_tokens)