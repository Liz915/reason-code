import json
import sys
import os
import re
from tqdm import tqdm

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reason_code.executor.sandbox import execute_code

def extract_code_content(text):
    text = str(text)
    # 1. 清洗 Qwen 的特殊 Token
    text = text.replace("<|im_end|>", "")
    
    # 2. 优先匹配 Markdown
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match: return match.group(1).strip()
    
    # 3. 其次匹配 def 开头 (针对 MBPP 这种直接续写的)
    # 找到第一个 def，截取到最后
    match_def = re.search(r"def\s+.*", text, re.DOTALL)
    if match_def:
        return match_def.group(0).strip()
        
    return text.strip()

def evaluate_mbpp(filename, label):
    print(f"\n🚀 正在评测 MBPP [{label}] ...")
    
    # 加载原始题目以获取 test cases
    problems = {}
    try:
        with open("data_mbpp.jsonl", 'r') as f:
            for line in f:
                d = json.loads(line)
                problems[d['task_id']] = d
    except FileNotFoundError:
        print("❌ 找不到 data_mbpp.jsonl，请确认文件路径")
        return

    total = 0
    passed = 0
    
    with open(filename, 'r') as f:
        lines = f.readlines()

    for line in tqdm(lines, desc="Scoring"):
        if not line.strip(): continue
        try:
            data = json.loads(line)
        except json.JSONDecodeError:
            continue
            
        task_id = data.get('task_id')
        
        # 兼容处理
        completion = data.get('completion')
        if completion is None: continue
        candidates = completion if isinstance(completion, list) else [completion]
        
        if task_id not in problems: continue
        problem = problems[task_id]
        
        # Best-of-N Logic
        any_pass = False
        for cand in candidates:
            code = extract_code_content(cand)
            if not code: continue
            
            # 🔥 修复：直接拼接测试用例，不要加 try-except 缩进块
            # 如果 assert 失败，脚本会报错退出，打印不出 PASS 标记 -> 判定失败
            full_script = f"""
import math
import heapq
import re
from typing import List, Dict, Tuple, Optional, Any

{code}

# Tests
{problem['test']}

print("ALL_TESTS_PASSED")
"""
            # 执行
            result = execute_code(full_script, timeout=5)
            
            if "ALL_TESTS_PASSED" in result:
                any_pass = True
                break
        
        total += 1
        if any_pass:
            passed += 1

    if total == 0:
        print("⚠️ 没有找到有效数据")
        return

    print(f"\n📊 MBPP {label} 最终成绩:")
    print(f"   题目数量: {total}")
    print(f"   通过数量: {passed}")
    print(f"   🏆 Pass Rate: {passed/total:.2%}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        evaluate_mbpp(sys.argv[1], "Run")
    else:
        print("Usage: python tools/score_mbpp.py <result_file>")