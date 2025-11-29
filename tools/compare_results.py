import json
import os
import textwrap
import sys

# 导入沙箱执行器
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from src.reason_code.executor.sandbox import execute_code
from datasets import load_dataset
from tqdm import tqdm

def check_one_file(filename):
    """返回一个字典: {task_id: bool (是否通过)}"""
    results = {}
    if not os.path.exists(filename):
        print(f"⚠️ 警告: 文件不存在 {filename}")
        return results
        
    with open(filename, 'r', encoding='utf-8') as f:
        for line in f:
            try:
                data = json.loads(line)
                results[data['task_id']] = data.get('completion', '')
            except:
                pass
    return results

def main():
    print("🚀 加载数据集 (HumanEval 90-110)...")
    dataset = load_dataset("openai_humaneval", split="test")
    
    # Task 90 到 110
    problems = {item['task_id']: item for item in dataset.select(range(90, 110))}
    
    # 只对比这两个文件，去掉 Reflexion 以免报错
    files = {
        "Baseline": "results_zeroshot_hard.jsonl",
        "Ours": "results_ours_hard.jsonl"
    }
    
    # 加载所有代码
    file_codes = {name: check_one_file(fname) for name, fname in files.items()}
    
    print(f"\n{'Task ID':<15} | {'Baseline':<10} | {'Ours':<10}")
    print("-" * 45)
    
    # 逐题对比
    scores = {"Baseline": 0, "Ours": 0}
    
    for task_id in problems.keys():
        row_str = f"{task_id:<15} | "
        
        problem = problems[task_id]
        test_code = problem['test']
        entry_point = problem['entry_point']
        # 加上缩进，确保代码能跑
        runner = textwrap.indent(f"\n{test_code}\ncheck({entry_point})", '    ')
        
        for name in ["Baseline", "Ours"]:
            code = file_codes[name].get(task_id, "")
            
            # 判分逻辑
            status = "❌"
            if code and "def " in code:
                try:
                    exit_code, _, _ = execute_code(code, runner)
                    if exit_code == 0:
                        status = "✅"
                        scores[name] += 1
                except:
                    pass
            
            row_str += f"{status:<10} | "
        
        print(row_str)
        
    print("-" * 45)
    print(f"Total Score:    | {scores['Baseline']:<10} | {scores['Ours']:<10}")

if __name__ == "__main__":
    main()