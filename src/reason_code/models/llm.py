"""
Reason-Code Local LLM (7B / Scientifically Rigorous Version)
"""
import os
import inspect
import re
from typing import List
import structlog
from mlx_lm import load, generate

logger = structlog.get_logger(__name__)

# 保持 4-bit 量化版
BASE_MODEL = os.getenv("BASE_MODEL_NAME", "mlx-community/Qwen2.5-Coder-7B-Instruct-4bit")

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

    def generate(self, prompt: str, num_return_sequences: int = 1, temperature: float = 0.7, max_tokens: int = 512, force_sample: bool = False) -> List[str]:
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

        # 🔥 科学严谨的采样逻辑 🔥
        # 只有在 N>1 或者 明确要求采样 (MCTS/Reflexion) 时才开启 Randomness
        do_sample = (num_return_sequences > 1) or force_sample
        
        if do_sample:
            # MCTS/Reflexion 甜区：0.8
            # Best-of-N (N>1) 激进区：1.1 (由外部 temperature 参数传入)
            final_temp = temperature 
            if "temperature" in supported_args: gen_kwargs["temperature"] = final_temp
            elif "temp" in supported_args: gen_kwargs["temp"] = final_temp
            
            # 保底多样性
            if "top_p" in supported_args: gen_kwargs["top_p"] = 0.95 
            # 移除 top_k 以允许长尾探索 (除非你觉得太发散可以加回 top_k=50)
        else:
            # 🚨 严格 Baseline 定义：N=1 必须是 Greedy (Temp=0)
            # 即使外部传入了 0.7，只要 force_sample=False 且 N=1，这里也会强制归零
            if "temperature" in supported_args: gen_kwargs["temperature"] = 0.0
            elif "temp" in supported_args: gen_kwargs["temp"] = 0.0

        for i in range(num_return_sequences):
            try:
                current_prompt = prompt
                # 仅在采样模式下加入微小扰动，避免 deterministic collapse
                if do_sample and i > 0:
                    current_prompt += f"\n# attempt {i}"
                
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
    
    # 🔥 关键修复：Default (Baseline) 必须是不采样的
    # 只有 reflexion 和 mcts 明确需要采样能力
    should_force_sample = (mode in ["reflexion", "mcts"])
    
    # 注意：这里传入的 temperature 只有在 should_force_sample=True 或 n>1 时才生效
    # 如果 mode="default" 且 n=1，底层会自动忽略这个 0.8，使用 0.0
    return _instance.generate(prompt, num_return_sequences=n, temperature=0.8, max_tokens=max_tokens, force_sample=should_force_sample)