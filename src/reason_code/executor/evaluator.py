import ast
import subprocess
import tempfile
import os
import asyncio
import json
from functools import lru_cache
from typing import Tuple, Dict, Any, List
from datetime import datetime

def _ensure_logs_dir():
    os.makedirs("logs", exist_ok=True)

def log_failure(prompt: str, candidate: str, stderr: str, test_case: str):
    _ensure_logs_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "candidate": candidate,
        "stderr": (stderr or "").strip(),
        "test_case": test_case
    }
    with open("logs/fail_cases.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

def log_success(prompt: str, original_code: str, corrected_code: str, test_case: str):
    _ensure_logs_dir()
    entry = {
        "timestamp": datetime.now().isoformat(),
        "prompt": prompt,
        "original": original_code,
        "corrected": corrected_code,
        "test_case": test_case,
        "type": "success"
    }
    with open("logs/success_cases.jsonl", "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

@lru_cache(maxsize=1024)
def validate_repair(original: str, repaired: str, test_runner: str, timeout: int = 5) -> bool:
    """
    将 repaired 代码与 test_runner 拼接并在本地执行，返回 True/False。
    test_runner 应当是缩进好的 Python 片段，例如:
        '    from submission import add\\n    assert add(1,2) == 3'
    """
    with tempfile.TemporaryDirectory() as tmp:
        code_path = os.path.join(tmp, "submission.py")
        runner_path = os.path.join(tmp, "runner.py")
        with open(code_path, "w", encoding="utf-8") as f:
            f.write(repaired)
            f.write("\n")
        runner_code = f"import sys\nfrom submission import *\n\n{test_runner}\n"
        with open(runner_path, "w", encoding="utf-8") as f:
            f.write(runner_code)
        try:
            proc = subprocess.run(
                ["python", runner_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
                cwd=tmp,
                text=True
            )
            return proc.returncode == 0
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

class CodeEvaluator:
    """三级评估：语法 -> 静态分析 -> 运行时测试"""

    def __init__(self):
        self.levels = [
            self._syntax_check,
            self._static_analysis,
            self._runtime_test
        ]

    def evaluate(self, code: str, test_runner: str, prompt: str = "") -> Dict[str, Any]:
        """
        同步接口，返回每一级的结果与 overall 信息
        overall.reward in [0,1]
        """
        results: Dict[str, Any] = {}
        for i, level_func in enumerate(self.levels, start=1):
            level_name = f"level_{i}"
            passed, message = level_func(code, test_runner)
            results[level_name] = {"passed": passed, "message": message}

            if not passed:
                # 只有运行时失败才写入 failure log（避免大量语法/风格噪声）
                if level_name == "level_3":
                    try:
                        log_failure(prompt, code, message, test_runner)
                    except Exception:
                        pass
                results["overall"] = {
                    "passed": False,
                    "failed_at": level_name,
                    "reward": self._calculate_reward(i, passed)
                }
                return results

        results["overall"] = {"passed": True, "failed_at": None, "reward": 1.0}
        try:
            # 如果成功，记录成功样本方便后续微调
            log_success(prompt, "<original_unknown>", code, test_runner)
        except Exception:
            pass
        return results

    def _calculate_reward(self, failed_level: int, passed: bool) -> float:
        if not passed:
            if failed_level == 1:
                return 0.0
            elif failed_level == 2:
                return 0.3
            elif failed_level == 3:
                return 0.7
            else:
                return 0.0
        return 1.0

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
            for func in functions:
                has_return = any(isinstance(n, ast.Return) for n in ast.walk(func))
                if not has_return:
                    # 不把缺 return 作为 fatal
                    pass
            return True, "static ok"
        except Exception as e:
            return False, f"static analysis error: {e}"

    def _runtime_test(self, code: str, test_runner: str):
        try:
            try:
                from src.reason_code.executor.sandbox import PersistentSandbox

                if not hasattr(self, '_sandbox'):
                    self._sandbox = PersistentSandbox()

                exit_code, stdout, stderr = self._sandbox.execute_code(code, test_runner)

                if exit_code == 0:
                    return True, f"测试通过: {stdout.strip() or '无输出'}"
                else:
                    return False, f"测试失败: {(stderr or stdout).strip()}"

            except ImportError:
                ok = validate_repair("", code, test_runner, timeout=8)
                if ok:
                    return True, "runtime tests passed (fallback)"
                else:
                    return False, "runtime tests failed (fallback)"

        except Exception as e:
            return False, f"运行时错误: {e}"

# 全局评估器
evaluator = CodeEvaluator()

# 同步入口，保持向后兼容
def evaluate_code(code: str, test_runner: str, prompt: str = "") -> Dict[str, Any]:
    return evaluator.evaluate(code, test_runner, prompt)

# 异步并发评估入口，返回与 candidates 顺序对应的评估 dict 列表
async def evaluate_candidates_async(candidates: List[str], test_runner: str, prompt: str = "") -> List[Dict[str, Any]]:
    loop = asyncio.get_running_loop()
    tasks = []
    for c in candidates:
        tasks.append(loop.run_in_executor(None, evaluator.evaluate, c, test_runner, prompt))
    results = await asyncio.gather(*tasks)
    return results     
    
