import json
import sys
import os

# 目标 ID 列表
TARGET_IDS = ['MBPP/20', 'MBPP/419', 'MBPP/428', 'MBPP/71']

def main():
    print(f"🔍 正在深入解剖案例: {TARGET_IDS}")
    
    # 1. 加载题目
    problems = {}
    with open("data_mbpp.jsonl", "r") as f:
        for line in f:
            d = json.loads(line)
            if d['task_id'] in TARGET_IDS:
                problems[d['task_id']] = d

    # 2. 加载 Baseline (错误代码)
    baseline_codes = {}
    try:
        with open("results_mbpp_baseline_n1.jsonl", "r") as f:
            for line in f:
                d = json.loads(line)
                if d['task_id'] in TARGET_IDS:
                    comp = d['completion']
                    baseline_codes[d['task_id']] = comp[0] if isinstance(comp, list) else comp
    except: pass

    # 3. 加载 MCTS (正确代码)
    mcts_codes = {}
    try:
        with open("results_mbpp_mcts_n3.jsonl", "r") as f:
            for line in f:
                d = json.loads(line)
                if d['task_id'] in TARGET_IDS:
                    comp = d['completion']
                    mcts_codes[d['task_id']] = comp[0] if isinstance(comp, list) else comp
    except: pass

    # 4. 打印报告
    for tid in TARGET_IDS:
        if tid not in problems: continue
        
        print("\n" + "="*80)
        print(f"📌 {tid}")
        print("="*80)
        
        # 提取题目描述（去掉函数签名部分，只看 docstring）
        prompt = problems[tid]['prompt']
        print(f"📝 [Problem Prompt]:\n{prompt.strip()[:200]}...") # 只打印前200字符
        
        print("\n❌ [Baseline Error Code]:")
        print(baseline_codes.get(tid, "N/A").strip())
        
        print("\n✅ [Reason-Code Fixed Code]:")
        print(mcts_codes.get(tid, "N/A").strip())
        
        print("-" * 80)

if __name__ == "__main__":
    main()