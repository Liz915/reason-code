import json
import sys
import os
import re
import argparse
from tqdm import tqdm
from datasets import load_dataset

# 1. 动态定位项目根目录
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

from src.reason_code.executor.sandbox import execute_code

# MBPP 真值文件路径
MBPP_DATA_PATH = os.path.join(project_root, "data", "final", "data_mbpp.jsonl")

def extract_code_content(text):
    """鲁棒的代码提取"""
    text = str(text).replace("<|im_end|>", "")
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match: return match.group(1).strip()
    match_gen = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match_gen: return match_gen.group(1).strip()
    if "def " in text:
        match_def = re.search(r"def\s+.*", text, re.DOTALL)
        if match_def: return match_def.group(0).strip()
    return text.strip()

def check_pass_mbpp(code, test_code):
    if not code: return False
    # 🔥 加上必要的 import 头文件
    header = """
import math
import heapq
import re
import sys
from typing import List, Dict, Tuple, Optional, Any
import collections
"""
    full_script = f"{header}\n{code}\n{test_code}\nprint('ALL_TESTS_PASSED')"
    res = execute_code(full_script, timeout=5)
    return "ALL_TESTS_PASSED" in str(res)

def check_pass_humaneval(code, task_data):
    if not code: return False
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

def evaluate_best_of_n(filename, dataset_name):
    print(f"\n🚀 正在评测 Best-of-N (Oracle) [{dataset_name.upper()}] ...")
    print(f"📂 读取文件: {filename}")
    
    if not os.path.exists(filename):
        print(f"❌ 找不到文件: {filename}")
        return

    # 1. 加载真值数据
    problems = {}
    if dataset_name == "humaneval":
        ds = load_dataset("openai_humaneval", split="test")
        problems = {item['task_id']: item for item in ds}
    else:
        if not os.path.exists(MBPP_DATA_PATH):
            print(f"❌ 错误: 找不到 MBPP 真值文件: {MBPP_DATA_PATH}")
            return
        with open(MBPP_DATA_PATH, "r") as f:
            for line in f:
                d = json.loads(line)
                problems[d['task_id']] = d

    total = 0
    passed_at_least_one = 0
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 2. 遍历结果文件
    for line in tqdm(lines, desc="Running Oracle Eval"):
        if not line.strip(): continue
        
        try:
            data = json.loads(line)
            task_id = data.get('task_id')
            candidates = data.get('completion', [])
            
            # 兼容单条结果 (N=1) 和 多条结果 (N>1)
            if isinstance(candidates, str):
                candidates = [candidates]
            
            if task_id not in problems: continue
            
            total += 1
            problem = problems[task_id]
            
            # 3. 只要有一个 Candidate 能过，这题就算过 (Oracle Setting)
            any_pass = False
            for cand in candidates:
                clean_code = extract_code_content(cand)
                
                is_pass = False
                if dataset_name == "humaneval":
                    is_pass = check_pass_humaneval(clean_code, problem)
                else:
                    is_pass = check_pass_mbpp(clean_code, problem['test'])
                
                if is_pass:
                    any_pass = True
                    break # 找到了正确答案，提前退出
            
            if any_pass:
                passed_at_least_one += 1

        except Exception as e:
            # print(f"Error processing {task_id}: {e}")
            pass

    if total == 0:
        print("无有效数据")
    else:
        acc = passed_at_least_one / total
        print(f"\n📊 Best-of-N (Oracle) 最终成绩:")
        print(f"   数据集: {dataset_name}")
        print(f"   题目数量: {total}")
        print(f"   解决题目数: {passed_at_least_one}")
        print(f"   🏆 Oracle Pass Rate: {acc:.2%}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("filename", type=str, help="Result JSONL file")
    parser.add_argument("--dataset", type=str, default="humaneval", choices=["humaneval", "mbpp"], help="Dataset type")
    args = parser.parse_args()
    
    evaluate_best_of_n(args.filename, args.dataset)