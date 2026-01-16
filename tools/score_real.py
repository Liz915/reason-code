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
    鲁棒的代码提取逻辑 (Fix for Special Tokens & Markdown)
    """
    if not text:
        return ""

    # 🔥 核心修复：先清洗掉 Qwen 的特殊结束符
    text = text.replace("<|im_end|>", "")

    # 1. 尝试提取标准 Markdown 块
    pattern = r"```python\s*(.*?)```"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    if match:
        return match.group(1).strip()

    # 2. 兜底：尝试提取通用代码块
    pattern_generic = r"```\s*(.*?)```"
    match_generic = re.search(pattern_generic, text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()

    # 3. 最后的防线：如果包含 def/import 但没有 markdown，假设整段都是代码
    if "def " in text or "import " in text:
        return text.strip()

    return text.strip()

def evaluate_logic(filename, label):
    print(f"\n🚀 正在评测 [{label}] 的逻辑正确率 (Running Tests)...")
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
    passed = 0
    
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    for line in tqdm(lines, desc=f"评测 {label}"):
        if not line.strip(): continue
        
        try:
            data = json.loads(line)
            task_id = data.get('task_id')
            raw_completion = data.get('completion', '')
            
            # 处理列表形式的 completion
            if isinstance(raw_completion, list):
                raw_completion = raw_completion[0] if len(raw_completion) > 0 else ""
            
            # 使用修复后的提取函数
            clean_code = extract_code_content(raw_completion)
            
            if not clean_code: 
                total += 1
                continue

            if task_id not in problems: continue
            problem = problems[task_id]
            
            # 构造测试脚本 (header + code + tests)
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
            total += 1
            result = execute_code(full_script, timeout=8)
            
            if "ALL_TESTS_PASSED" in result:
                passed += 1

        except Exception as e:
            print(f"系统错误 {task_id}: {e}")

    if total == 0:
        print(f"📄 {label}: 无有效数据")
    else:
        acc = passed / total
        print(f"📊 {label} 最终真实成绩:")
        print(f"   题目数量: {total}")
        print(f"   逻辑通过: {passed}")
        print(f"   🏆 Logic Pass Rate: {acc:.2%}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
        label = sys.argv[2] if len(sys.argv) > 2 else "Run"
        evaluate_logic(target_file, label)
    else:
        print("Usage: python score_real.py <filename> <label>")