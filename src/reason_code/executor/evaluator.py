"""
Code Evaluator with Multi-Level Validation.

Evaluation proceeds in three stages:
1. Syntax and static checks.
2. Runtime execution in a sandboxed environment.
3. Explicit success token verification to prevent reward hacking.

Only solutions that pass all stages receive a reward of 1.0.
"""

import ast
import subprocess
import tempfile
import os
import asyncio
import json
from functools import lru_cache
from typing import Tuple, Dict, Any, List
from datetime import datetime
from src.reason_code.executor.sandbox import sandbox  # 确保这里导入了 sandbox

def _ensure_logs_dir():
    os.makedirs("logs", exist_ok=True)

class CodeEvaluator:
    def __init__(self):
        self.levels = [
            self._syntax_check,
            self._static_analysis
        ]

    def evaluate(self, code: str, test_runner: str, prompt: str = "") -> Dict[str, Any]:
        """
        三级评估：语法 -> 静态 -> 运行时
        注意：prompt 参数仅用于日志记录，绝不参与代码执行！
        """
        results: Dict[str, Any] = {}
        
        # 1. 语法和静态分析 (快速过滤)
        for i, level_func in enumerate(self.levels, start=1):
            level_name = f"level_{i}"
            passed, message = level_func(code, test_runner)
            results[level_name] = {"passed": passed, "message": message}

            if not passed:
                results["overall"] = {
                    "passed": False,
                    "failed_at": level_name,
                    "reward": 0.0 # 语法/静态错误一律 0 分
                }
                return results

        # 2. 运行时测试 (Level 3 - The Real Test)
        passed, message = self._runtime_test(code, test_runner)
        results["level_3"] = {"passed": passed, "message": message}

        if not passed:
            results["overall"] = {
                "passed": False,
                "failed_at": "level_3",
                "reward": 0.0  # Reward Hacking：运行报错也给 0.0
            }
        else:
            # Only when the magic success token is printed do we assign reward = 1.0
            results["overall"] = {"passed": True, "failed_at": None, "reward": 1.0}
            
        return results

    def _syntax_check(self, code: str, test_runner: str) -> Tuple[bool, str]:
        try:
            ast.parse(code)
            return True, "syntax ok"
        except SyntaxError as e:
            return False, f"SyntaxError: {e.msg} (line {e.lineno})"
        except Exception as e:
            return False, f"parse error: {e}"

    def _static_analysis(self, code: str, test_runner: str) -> Tuple[bool, str]:
        try:
            tree = ast.parse(code)
            functions = [n for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
            if not functions:
                return False, "no function definition found"
            return True, "static ok"
        except Exception as e:
            return False, f"static analysis error: {e}"

    def _runtime_test(self, code: str, test_runner: str):
        """
        Level 3: 运行时测试 (Anti-Reward-Hacking & Anti-Pollution Version)
        """
        # 🔥 兜底校验：确保 test_runner 看起来是合法的
        if "check(" not in test_runner:
            return False, "Invalid test_runner: missing check()"

        try:
            # 构造能够 "自我证明" 的脚本
            magic_token = "MCTS_SUCCESS_TOKEN"
            
            # 这里的 imports 需要包含基本的库，以防模型忘记写 import math 等
            common_header = "from typing import List, Tuple, Optional, Dict, Any\nimport math\nimport re\n"
            
            full_script = f"""
{common_header}

{code}

{test_runner}

print('{magic_token}')
"""

            """
            All code execution is performed inside a restricted sandbox with
            time and resource limits to prevent unsafe operations.
            """

            # 执行 (8秒超时)
            output = sandbox.execute(full_script, timeout=8)

            # 判定逻辑
            output_str = str(output)
            
            # 情况 1: 包含 Error (stderr 有东西) -> 失败
            if output_str.startswith("Error"):
                return False, f"Runtime Error: {output_str}"
                
            # 情况 2: 包含 Magic Token -> 成功
            if magic_token in output_str:
                return True, "All Tests Passed"
                
            # 情况 3: 既没报错，也没 Magic Token -> 失败 (说明中途 Assert 挂了)
            return False, "Execution finished but tests did not verify (Silent Failure)."

        except Exception as e:
            return False, f"System Error: {e}"

# 全局实例
evaluator = CodeEvaluator()

def evaluate_code(code: str, test_runner: str, prompt: str = "") -> Dict[str, Any]:
    # prompt 参数保留接口兼容性，但不再使用
    return evaluator.evaluate(code, test_runner, prompt)

async def evaluate_candidates_async(candidates: List[str], test_runner: str, prompt: str = "") -> List[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    tasks = []
    for c in candidates:
        tasks.append(loop.run_in_executor(None, evaluator.evaluate, c, test_runner, prompt))
    results = await asyncio.gather(*tasks)
    return results