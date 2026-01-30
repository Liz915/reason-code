import json
import sys
import os
import argparse
import re
from tqdm import tqdm

# --- 1. 动态定位项目根目录 ---
# tools/score_mbpp.py -> tools/ -> reason-code/
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
sys.path.insert(0, project_root)

# 引用沙箱执行器
from src.reason_code.executor.sandbox import execute_code

# --- 2. 核心配置：指定真值文件路径 ---
# 无论你在哪运行，它都会去 project_root/data/final/data_mbpp.jsonl 找
DATA_PATH = os.path.join(project_root, "data", "final", "data_mbpp.jsonl")

def extract_code(text):
    """提取代码逻辑，兼容 Markdown 和纯代码"""
    text = str(text).replace("<|im_end|>", "")
    # 优先找 ```python
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match: return match.group(1).strip()
    # 其次找 ```
    match_gen = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match_gen: return match_gen.group(1).strip()
    # 兜底：MBPP 经常直接写 def
    if "def " in text:
        match_def = re.search(r"def\s+.*", text, re.DOTALL)
        if match_def:
            return match_def.group(0).strip()
    return text.strip()

def check_pass(code, test_code):
    if not code: return False
    
    # 🔥 加上必要的 import 头文件，防止因缺少库而误判
    header = """
import math
import heapq
import re
import sys
from typing import List, Dict, Tuple, Optional, Any
import collections
"""
    full_script = f"{header}\n{code}\n{test_code}\nprint('ALL_TESTS_PASSED')"
    
    # 运行沙箱
    res = execute_code(full_script, timeout=5)
    return "ALL_TESTS_PASSED" in str(res)

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("result_file", type=str, help="Path to the .jsonl result file")
    args = parser.parse_args()

    # 1. 检查真值文件是否存在
    if not os.path.exists(DATA_PATH):
        print(f"❌ 错误: 找不到真值文件: {DATA_PATH}")
        print("   请确保 data_mbpp.jsonl 位于 data/final/ 目录下。")
        return

    print(f"🚀 正在评测 MBPP [文件: {os.path.basename(args.result_file)}] ...")
    
    # 2. 加载真值数据 (Ground Truth)
    problems = {}
    with open(DATA_PATH, "r") as f:
        for line in f:
            d = json.loads(line)
            problems[d['task_id']] = d

    # 3. 加载你的预测结果
    results = {}
    try:
        with open(args.result_file, "r") as f:
            for line in f:
                if not line.strip(): continue
                d = json.loads(line)
                results[d['task_id']] = d
    except FileNotFoundError:
        print(f"❌ 找不到结果文件: {args.result_file}")
        return

    # 4. 开始跑分
    passed = 0
    total = 0
    
    # 使用 tqdm 显示进度条
    for task_id in tqdm(problems):
        if task_id not in results:
            continue # 结果文件里没有这题，跳过
            
        total += 1
        problem = problems[task_id]
        
        # 获取生成的代码
        completion = results[task_id]['completion']
        # 兼容 list (Best-of-N) 和 str
        candidate = completion[0] if isinstance(completion, list) else completion
        
        # 提取并测试
        code_to_test = extract_code(candidate)
        if check_pass(code_to_test, problem['test']):
            passed += 1

    # 5. 输出结果
    pass_rate = (passed / total) * 100 if total > 0 else 0
    print(f"\n📊 MBPP 最终成绩:")
    print(f"   文件路径: {args.result_file}")
    print(f"   题目数量: {total}")
    print(f"   通过数量: {passed}")
    print(f"   🏆 Pass Rate: {pass_rate:.2f}%")

if __name__ == "__main__":
    main()