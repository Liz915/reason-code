import json
import re
import sys
import os

# 路径适配
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reason_code.executor.sandbox import execute_code

def extract_code(text):
    text = str(text).replace("<|im_end|>", "")
    # 优先提取 Markdown
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match: return match.group(1).strip()
    
    # MBPP 经常直接写函数，没有 Markdown
    # 找第一个 def
    if "def " in text:
        return text.strip()
        
    return text.strip()

def check_pass(code, task_data):
    if not code: return False
    
    
    full_script = f"""
import math
import heapq
import re
from typing import List, Dict, Tuple, Optional, Any

{code}

# Tests
{task_data['test']}

print("ALL_TESTS_PASSED")
"""
    res = execute_code(full_script, timeout=5)
    return "ALL_TESTS_PASSED" in str(res)

def main():
    print("🚀 分析 MBPP 修复案例...")
    
    # 1. 加载原始题目（获取测试用例）
    problems = {}
    try:
        with open("data/final/data_mbpp.jsonl", "r") as f:
            for line in f:
                d = json.loads(line)
                problems[d['task_id']] = d
    except FileNotFoundError:
        print("❌ 找不到 data_mbpp.jsonl")
        return

    # 2. 加载 Baseline (N=1)
    baseline_passed = set()
    try:
        with open("data/final/results_mbpp_baseline_n1.jsonl", "r") as f:
            for line in f:
                if not line.strip(): continue
                d = json.loads(line)
                # Baseline 结果是 list
                comp = d['completion']
                code = comp[0] if isinstance(comp, list) else comp
                
                if d['task_id'] in problems:
                    if check_pass(extract_code(code), problems[d['task_id']]):
                        baseline_passed.add(d['task_id'])
    except FileNotFoundError:
        print("❌ 找不到 results_mbpp_baseline_n1.jsonl")

    # 3. 加载 MCTS (N=3)
    mcts_passed = set()
    try:
        with open("data/final/results_mbpp_mcts_n3.jsonl", "r") as f:
            for line in f:
                if not line.strip(): continue
                d = json.loads(line)
                # MCTS 结果通常是 str (top-1 selection)
                comp = d['completion']
                code = comp[0] if isinstance(comp, list) else comp
                
                if d['task_id'] in problems:
                    if check_pass(extract_code(code), problems[d['task_id']]):
                        mcts_passed.add(d['task_id'])
    except FileNotFoundError:
        print("❌ 找不到 results_mbpp_mcts_n3.jsonl")

    # 4. 计算差异
    fixed = mcts_passed - baseline_passed
    broken = baseline_passed - mcts_passed
    
    print(f"\n📊 MBPP 差异分析报告:")
    print(f"Baseline (N=1) 总通过: {len(baseline_passed)}")
    print(f"MCTS (N=3) 总通过:     {len(mcts_passed)}")
    print(f"--------------------------------")
    print(f"🛠️  MCTS 独家修复 (Baseline错, MCTS对): {len(fixed)}")
    print(f"💔 MCTS 意外改坏 (Baseline对, MCTS错): {len(broken)}")
    
    if fixed:
        print(f"\n✅ 修复案例 ID: {sorted(list(fixed))}")
    if broken:
        print(f"\n❌ 改坏案例 ID: {sorted(list(broken))}")

if __name__ == "__main__":
    main()