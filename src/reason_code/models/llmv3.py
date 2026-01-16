"""
Reason-Code Local LLM (Robust / Paper-Exact / Diversity-Fix Version)
"""
import os
import inspect
import re
import random
from typing import List
import structlog
from mlx_lm import load, generate

logger = structlog.get_logger(__name__)

BASE_MODEL = os.getenv("BASE_MODEL_NAME", "Qwen/Qwen2.5-Coder-1.5B-Instruct")

class LocalMLXModel:
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._load()

    def _load(self):
        logger.info("model_loading_start", backend="mlx", base_model=BASE_MODEL)
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

        # 动态参数检测
        sig = inspect.signature(generate)
        supported_args = sig.parameters.keys()
        
        # 基础生成参数
        gen_kwargs = {
            "model": self.model, 
            "tokenizer": self.tokenizer, 
            "verbose": False
        }
        
        if "max_tokens" in supported_args: gen_kwargs["max_tokens"] = max_tokens
        elif "max_new_tokens" in supported_args: gen_kwargs["max_new_tokens"] = max_tokens

        # 采样参数设置
        # 如果需要生成多个样本，强制开启采样
        do_sample = num_return_sequences > 1
        
        if do_sample:
            # 强制使用高温度和 top_p 来保证多样性
            final_temp = max(0.8, temperature) # N>1 时温度至少 0.8
            if "temperature" in supported_args: gen_kwargs["temperature"] = final_temp
            elif "temp" in supported_args: gen_kwargs["temp"] = final_temp
            
            if "top_p" in supported_args: gen_kwargs["top_p"] = 0.95
        else:
            # N=1 时保持贪婪搜索 (Greedy) 以获得最稳的 Baseline
            if "temperature" in supported_args: gen_kwargs["temperature"] = 0.0
            elif "temp" in supported_args: gen_kwargs["temp"] = 0.0

        for i in range(num_return_sequences):
            try:
                # 🛠️ Dirty Hack for Diversity:
                # 如果是 N>1，我们在 Prompt 后面随机加几个空格，确保 KV Cache 不会完全锁死结果
                # 这对某些顽固的推理引擎非常有效
                current_prompt_text = prompt
                if i > 0:
                    current_prompt_text += " " * i 
                
                messages = [
                    {"role": "system", "content": system_content},
                    {"role": "user", "content": current_prompt_text}
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
    if mode == "reflexion": max_tokens = 640 
    elif mode == "hard": max_tokens = 640
    else: max_tokens = 512 
    
    # 这里传给 generate 的 temp 只是个参考，generate 内部会根据 n 自动调整
    return _instance.generate(prompt, num_return_sequences=n, temperature=0.7, max_tokens=max_tokens)