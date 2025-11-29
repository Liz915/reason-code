import json
import sys
import os
import textwrap  # 引入这个库来处理缩进
from datasets import load_dataset
from tqdm import tqdm

# 确保能导入 src
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.reason_code.executor.sandbox import execute_code

def evaluate_logic(filename, label):
    print(f"\n🚀 正在评测 [{label}] 的逻辑正确率 (Running Tests)...")
    
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

    for line in tqdm(lines, desc=f"评测中"):
        if not line.strip(): continue
        
        try:
            data = json.loads(line)
            task_id = data.get('task_id')
            completion = data.get('completion', '')
            
            # 1. 基础过滤：没代码或没def直接挂
            if not completion or "def " not in completion:
                total += 1
                continue

            if task_id not in problems:
                continue

            total += 1
            
            problem = problems[task_id]
            test_code = problem['test']
            entry_point = problem['entry_point']
            
            # 2. 构造原始测试脚本
            raw_runner = f"\n{test_code}\ncheck({entry_point})"
            
            # ✅ 关键修复：给测试代码加上缩进！
            # 这样它才能正确地跑在 if __name__ == '__main__': 下面
            runner_script = textwrap.indent(raw_runner, '    ')
            
            # 3. 执行
            exit_code, _, _ = execute_code(completion, runner_script)
            
            if exit_code == 0:
                passed += 1
                
        except Exception as e:
            pass

    if total == 0:
        print(f"📄 {label}: 无有效数据")
    else:
        acc = passed / total
        print(f"📊 {label} 最终真实成绩:")
        print(f"   题目数量: {total}")
        print(f"   逻辑通过: {passed}")
        print(f"   🏆 Logic Pass Rate: {acc:.2%}")

if __name__ == "__main__":
    # 评测三个文件
    evaluate_logic("results_zeroshot.jsonl", "Baseline (Zero-shot)")
    evaluate_logic("results_reflexion.jsonl", "Ablation (Reflexion)")
    evaluate_logic("results_ours.jsonl", "Ours (Reason-Code)")