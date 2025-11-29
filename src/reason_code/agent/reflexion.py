"""
自我修复模块：基于执行反馈修复代码
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
    """构造修复 Prompt，利用报错信息"""
    return f"""
你是一个代码修复专家。
当前代码运行时出现了错误。

[当前代码]
```python
{code}
[错误信息] {error_msg}

[有Bug的代码]
```python
{code}

[修复要求]
    1、请输出完整的修复后的函数代码。

    2、严格遵守Python缩进规则 (Indentation)。

    3、必须使用 python ... 代码块包裹。

    4、不要解释，只给代码。

    [修复后的代码] """   

async def attempt_fix(code: str, error_msg: str, test_runner: str) -> str: 
    """尝试修复代码""" 
    # 1. 先定义变量，解决"红线"问题 
    last_error = error_msg.splitlines()[-1] if error_msg else 'Unknown Error'
    # 2. 再打印日志
    logger.info("reflexion_triggered", error_msg=last_error)

    prompt = construct_fix_prompt(code, error_msg, test_runner)

    try:
    # 串行生成 1 个候选
        candidates = _local_model.generate(prompt, num_return_sequences=1)
    
        if candidates:
            fixed_code = candidates[0]
            logger.debug(
                    "reflexion_proposal", 
                    fixed_code_snippet=fixed_code[:100] + "...", # 只记录前100字符预览，防止日志爆炸
                    full_code=fixed_code 
                )
            
        
        # 简单的防呆检查：如果没有 def，可能是模型只输出了片段
            if "def " not in fixed_code:
                logger.warning("reflexion_failed_structure", reason="missing 'def' in output")
                return code
            
            return fixed_code
        
    except Exception as e:
        logger.error("reflexion_exception", error=str(e))
    
    return code