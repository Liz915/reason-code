import json
import sys
import os
import re
from datasets import load_dataset
from tqdm import tqdm

# 确保能导入 src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reason_code.executor.sandbox import execute_code

def extract_code_content(text):
    """
    鲁棒的代码提取 (修复 <|im_end|> 问题)
    """
    if not text:
        return ""

    # 🔥 核心修复：清洗 Qwen 的特殊结束符
    text = text.replace("<|im_end|>", "")

    # 1. 标准 Markdown
    match = re.search(r"```python\s*(.*?)```", text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. 通用 Markdown
    match = re.search(r"```\s*(.*?)```", text, re.DOTALL)
    if match:
        return match.group(1).strip()

    # 3. 如果没有 Markdown，但包含代码特征，直接返回清洗后的文本
    if "def " in text or "import " in text:
        return text.strip()

    return text.strip()

def evaluate_best_of_n(filename):
    print(f"\n🚀 正在评测 Best-of-N (Pass@k) ...")
    print(f"📂 读取文件: {filename}")
    
    if not os.path.exists(filename):
        print(f"❌ 找不到文件: {filename}")
        return

    try:
        dataset = load_dataset("openai_humaneval", split="test")
        problems = {item['task_id']: item for item in dataset}
    except Exception as e:
        print(f"⚠️ 无法加载数据集: {e}")
        return

    total = 0
    passed_at_least_one = 0
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in tqdm(lines, desc="评测 Best-of-N"):
        if not line.strip(): continue
        
        try:
            data = json.loads(line)
            task_id = data.get('task_id')
            candidates = data.get('completion', [])
            
            # 兼容性处理
            if isinstance(candidates, str):
                candidates = [candidates]
            
            if not candidates:
                total += 1
                continue

            if task_id not in problems: continue
            problem = problems[task_id]
            
            # 遍历该题目的所有候选代码 (N=10)
            any_pass = False
            for cand in candidates:
                clean_code = extract_code_content(cand)
                if not clean_code: continue
                
                # 构造测试脚本
                full_script = f"""
from typing import List, Tuple, Optional, Dict, Any
import math
import re
import heapq

{clean_code}

{problem['test']}

try:
    check({problem['entry_point']})
    print("ALL_TESTS_PASSED")
except Exception as e:
    pass
"""
                # 执行 (6秒超时足够)
                result = execute_code(full_script, timeout=6)
                
                if "ALL_TESTS_PASSED" in result:
                    any_pass = True
                    break # 只要有一个对了，这题就算 Pass@10 通过
            
            total += 1
            if any_pass:
                passed_at_least_one += 1

        except Exception as e:
            print(f"系统错误 {task_id}: {e}")

    if total == 0:
        print("无有效数据")
    else:
        acc = passed_at_least_one / total
        print(f"\n📊 Best-of-N (Oracle) 最终成绩:")
        print(f"   题目数量: {total}")
        print(f"   解决题目数: {passed_at_least_one}")
        print(f"   🏆 Pass@{len(candidates)} Rate: {acc:.2%}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        evaluate_best_of_n(sys.argv[1])
    else:
        print("Usage: python tools/score_best_of_n.py <filename>")