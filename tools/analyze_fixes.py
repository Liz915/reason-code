import json
import sys
import os

# 确保能导入 src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reason_code.executor.sandbox import execute_code

def extract_code(text):
    text = str(text)
    text = text.replace("<|im_end|>", "")
    import re
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match: return match.group(1).strip()
    return text.strip()

def check_pass(code, task_data):
    if not code: return False
    # 构造完整测试脚本
    full_script = f"""
from typing import List, Tuple, Optional, Dict, Any
import math
import re
import heapq
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
    from datasets import load_dataset
    print("正在加载数据集...")
    ds = load_dataset("openai_humaneval", split="test")
    problems = {item['task_id']: item for item in ds}

    print("正在分析 Baseline (N=1)...")
    baseline_passed = set()
    try:
        with open("data/final/results_baseline_n1.jsonl", "r") as f:
            for line in f:
                if not line.strip(): continue
                d = json.loads(line)
                code = d['completion'][0] if isinstance(d['completion'], list) else d['completion']
                if check_pass(extract_code(code), problems[d['task_id']]):
                    baseline_passed.add(d['task_id'])
    except FileNotFoundError:
        print("❌ 找不到 results_baseline_n1.jsonl")
        return

    print("正在分析 MCTS (N=3)...")
    mcts_passed = set()
    try:
        with open("data/final/results_mcts_n3.jsonl", "r") as f:
            for line in f:
                if not line.strip(): continue
                d = json.loads(line)
                code = d['completion'][0] if isinstance(d['completion'], list) else d['completion']
                if check_pass(extract_code(code), problems[d['task_id']]):
                    mcts_passed.add(d['task_id'])
    except FileNotFoundError:
        print("❌ 找不到 results_mcts_n3.jsonl")
        return

    fixed = mcts_passed - baseline_passed
    broken = baseline_passed - mcts_passed
    
    print(f"\n📊 差异分析报告:")
    print(f"Baseline (N=1) 总通过: {len(baseline_passed)}")
    print(f"MCTS (N=3) 总通过: {len(mcts_passed)}")
    print(f"--------------------------------")
    print(f"🛠️  MCTS 独家修复 (Baseline错, MCTS对): {len(fixed)}")
    print(f"💔 MCTS 意外改坏 (Baseline对, MCTS错): {len(broken)}")
    
    if fixed:
        print(f"\n✅ MCTS 修复的高价值题目 ID: {sorted(list(fixed))}")
    if broken:
        print(f"\n❌ 被改坏的简单题目 ID: {sorted(list(broken))}")

if __name__ == "__main__":
    main()