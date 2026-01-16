"""
自我修复模块：基于执行反馈修复代码 (Refined Version)
"""
import sys
import os
import re
import structlog

# 导入 LLM 接口
from src.reason_code.models.llm import _local_model

logger = structlog.get_logger(__name__)

def construct_fix_prompt(code: str, error_msg: str, test_runner: str) -> str:
    """
    构造修复 Prompt (使用安全拼接，防止语法错误)
    """
    # 使用括号自动拼接字符串，避免三引号的缩进/闭合问题
    prompt = (
        "The current code failed to pass the tests.\n\n"
        "[Current Code]\n"
        "```python\n"
        f"{code}\n"
        "```\n\n"
        "[Error Message]\n"
        f"{error_msg}\n\n"
        "[Instruction]\n"
        "Fix the bugs in the code above based on the error message.\n"
        "Return the COMPLETE fixed function.\n"
        "Do not output explanations.\n"
        "Wrap the code in ```python ... ```."
    )
    return prompt

async def attempt_fix(code: str, error_msg: str, test_runner: str) -> str: 
    """尝试修复代码""" 
    
    prompt = construct_fix_prompt(code, error_msg, test_runner)

    try:
        # 🔥 关键修改 1: 传入 force_sample=True
        # 我们需要一定的温度 (0.5) 来让模型产生"不同于之前"的修复思路。
        # 如果不加 force_sample，llm.py 会因为 n=1 而强制使用 Greedy (T=0)，导致模型一直重复生成同样的错误代码。
        candidates = _local_model.generate(
            prompt, 
            num_return_sequences=1,
            max_tokens=600,
            temperature=0.5,
            force_sample=True 
        )
    
        if candidates:
            fixed_code = candidates[0]
            
            # 🔥 关键修改 2: 使用正则进行更鲁棒的结构检查
            # 旧逻辑: if "def " not in fixed_code: (容易误杀)
            # 新逻辑: 只要包含 "def 函数名" 结构即可，允许前面有 import 或 helper function
            if not re.search(r"def\s+\w+", fixed_code):
                logger.warning("reflexion_failed_structure", reason="missing 'def function'")
                # 如果格式不对，与其返回空或报错，不如返回原代码，让 MCTS 去处理
                return code 
            
            return fixed_code
            
    except Exception as e:
        logger.error("reflexion_exception", error=str(e))
    
    return code