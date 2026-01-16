"""
自我修复模块：基于执行反馈修复代码 (Syntax Fix Version)
"""
import sys
import os
import re

# 导入 LLM 接口
from src.reason_code.models.llm import _local_model
import structlog
from src.reason_code.utils.logger import logger as global_logger
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
    # 1. 简略错误日志
    last_error = error_msg.splitlines()[-1] if error_msg else 'Unknown Error'
    
    prompt = construct_fix_prompt(code, error_msg, test_runner)

    try:
        # 给足 token 空间 (600) 和适当的温度 (0.5)
        candidates = _local_model.generate(
            prompt, 
            num_return_sequences=1,
            max_tokens=600,
            temperature=0.5
        )
    
        if candidates:
            fixed_code = candidates[0]
            
            # 简单的防呆检查
            if "def " not in fixed_code:
                logger.warning("reflexion_failed_structure", reason="missing 'def'")
                return code 
            
            return fixed_code
            
    except Exception as e:
        logger.error("reflexion_exception", error=str(e))
    
    return code