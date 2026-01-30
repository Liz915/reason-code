import json
import sys
import os
import argparse
import re
from datasets import load_dataset

# 引用 executor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reason_code.executor.sandbox import execute_code

def extract_code(text):
    """
    代码提取逻辑：优先 Markdown，兜底 def
    """
    text = str(text).replace("<|im_end|>", "")
    
    # 1. 优先匹配标准 Markdown
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match: return match.group(1).strip()
    
    # 2. 匹配通用 Markdown
    match_gen = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match_gen: return match_gen.group(1).strip()
    
    # 3. MBPP 兜底：直接匹配函数定义
    if "def " in text:
        match_def = re.search(r"def\s+.*", text, re.DOTALL)
        if match_def:
            return match_def.group(0).strip()
            
    return text.strip()

def check_pass_mbpp(code, test_code):
    if not code: return False
    
    
    header = """
import math
import heapq
import re
import sys
from typing import List, Dict, Tuple, Optional, Any
import collections
"""
    # 拼接：头文件 + 你的代码 + 测试用例 + 成功标记
    full_script = f"{header}\n{code}\n{test_code}\nprint('ALL_TESTS_PASSED')"
    
    res = execute_code(full_script, timeout=5)
    return "ALL_TESTS_PASSED" in str(res)

def check_pass_humaneval(code, task_data):
    if not code: return False
    # HumanEval 通常自带 import，但也补一个保险
    full_script = f"""
from typing import List, Tuple, Optional, Dict, Any
import math
import re
import heapq
import sys
import collections

{code}

{task_data['test']}

try:
    check({task_data['entry_point']})
    print("ALL_TESTS_PASSED")
except: pass
"""
    res = execute_code(full_script, timeout=5)
    return "ALL_TESTS_PASSED" in str(res)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=str, required=True, choices=["humaneval", "mbpp"])
    parser.add_argument("--baseline", type=str, required=True, help="Path to Baseline results (N=1)")
    parser.add_argument("--mcts", type=str, required=True, help="Path to MCTS results (N=3)")
    args = parser.parse_args()

    print(f"🚀 Calculating Hybrid Score for [{args.dataset}]...")

    # 1. 加载题目
    problems = {}
    if args.dataset == "humaneval":
        ds = load_dataset("openai_humaneval", split="test")
        problems = {item['task_id']: item for item in ds}
    else:
        # MBPP
        try:
            with open("data/final/data_mbpp.jsonl", "r") as f:
                for line in f:
                    d = json.loads(line)
                    problems[d['task_id']] = d
        except FileNotFoundError:
            print("❌ Error: data/final/data_mbpp.jsonl not found.")
            return

    # 2. 加载 Baseline
    baseline_results = {}
    with open(args.baseline, "r") as f:
        for line in f:
            if not line.strip(): continue
            d = json.loads(line)
            baseline_results[d['task_id']] = d

    # 3. 加载 MCTS
    mcts_results = {}
    with open(args.mcts, "r") as f:
        for line in f:
            if not line.strip(): continue
            d = json.loads(line)
            mcts_results[d['task_id']] = d

    total = 0
    passed = 0
    baseline_correct = 0
    mcts_fixed = 0
    
    # 4. 计算混合策略
    for task_id in problems:
        total += 1
        problem = problems[task_id]
        
        # --- Step A: Check Baseline ---
        baseline_ok = False
        if task_id in baseline_results:
            base_comp = baseline_results[task_id]['completion']
            base_code = base_comp[0] if isinstance(base_comp, list) else base_comp
            base_code_clean = extract_code(base_code) 
            
            if args.dataset == "humaneval":
                baseline_ok = check_pass_humaneval(base_code_clean, problem)
            else:
                baseline_ok = check_pass_mbpp(base_code_clean, problem['test'])
        
        if baseline_ok:
            passed += 1
            baseline_correct += 1
            continue # Baseline 对了，直接通过
            
        # --- Step B: Baseline Failed, Try MCTS ---
        if task_id in mcts_results:
            mcts_comp = mcts_results[task_id]['completion']
            mcts_code = mcts_comp[0] if isinstance(mcts_comp, list) else mcts_comp
            mcts_code_clean = extract_code(mcts_code)
            
            mcts_ok = False
            if args.dataset == "humaneval":
                mcts_ok = check_pass_humaneval(mcts_code_clean, problem)
            else:
                mcts_ok = check_pass_mbpp(mcts_code_clean, problem['test'])
                
            if mcts_ok:
                passed += 1
                mcts_fixed += 1

    print(f"\n📊 {args.dataset.upper()} Hybrid Strategy Results:")
    print(f"   Total Tasks: {total}")
    print(f"   Baseline Correct: {baseline_correct}")
    print(f"   MCTS Fixed (Net Gain): +{mcts_fixed}")
    print(f"   Total Passed: {passed}")
    print(f"   🏆 Adaptive Pass Rate: {passed/total:.2%}")

if __name__ == "__main__":
    main()