"""
使用 HumanEval 数据集测试 Agent 能力
"""
import sys
import os
import asyncio
import json
import textwrap  # 👈 新增引入

# 确保路径正确
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from mcts_enhanced import EnhancedMCTS
from evaluator import evaluate_code

# HumanEval 第 0 题
HUMAN_EVAL_0 = {
    "task_id": "HumanEval/0",
    "prompt": "from typing import List\n\ndef has_close_elements(numbers: List[float], threshold: float) -> bool:\n    \"\"\" Check if in given list of numbers, are any two numbers closer to each other than\n    given threshold.\n    >>> has_close_elements([1.0, 2.0, 3.0], 0.5)\n    False\n    >>> has_close_elements([1.0, 2.8, 3.0, 4.0, 5.0], 0.3)\n    True\n    \"\"\"\n",
    "test": "\n\nMETADATA = {\n    'author': 'jt',\n    'dataset': 'test'\n}\n\n\ndef check(candidate):\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.3) == True\n    assert candidate([1.0, 2.0, 3.9, 4.0, 5.0, 2.2], 0.05) == False\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.95) == True\n    assert candidate([1.0, 2.0, 5.9, 4.0, 5.0], 0.8) == False\n    assert candidate([1.0, 2.0, 3.0, 4.0, 5.0, 2.0], 0.1) == True\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 1.0) == True\n    assert candidate([1.1, 2.2, 3.1, 4.1, 5.1], 0.5) == False\n\n"
}

async def solve_humaneval():
    print(f"🧠 挑战 HumanEval/0: has_close_elements")
    print("-" * 50)
    
    problem_prompt = HUMAN_EVAL_0["prompt"]
    
    # 原始测试逻辑
    # 注意：这里我们去掉了外层的 if __name__ == '__main__':
    # 因为 sandbox.py 会自动帮我们要加这个头
    raw_test_runner = f"""
{HUMAN_EVAL_0['test']}

# 直接调用 check，因为外层已经被 sandbox 包裹在 main 里了
# 这里的 has_close_elements 来自 submission.py (在 sandbox 环境中)
# 但由于 sandbox 直接拼接文件，我们需要确保存入 submission 的代码能被访问
# 实际上 sandbox 把代码和测试拼在同一个文件里，所以直接调用即可

try:
    check(has_close_elements)
    print("ALL TESTS PASSED")
except AssertionError:
    print("TEST FAILED")
    exit(1)
except Exception as e:
    print(f"ERROR: {{e}}")
    exit(1)
"""

    
    
    test_runner = textwrap.indent(raw_test_runner, '    ')

    mcts = EnhancedMCTS(
        root_code=problem_prompt, 
        n_simulations=10,
        n_candidates=1
    )
    
    best_code = await mcts.run(test_runner)
    
    print("\n🎉 最终生成的代码:")
    print("=" * 40)
    print(best_code)
    print("=" * 40)

if __name__ == "__main__":
    asyncio.run(solve_humaneval())