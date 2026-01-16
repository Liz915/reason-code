import json
import os

def sort_key(item):
    # 从 "HumanEval/62" 中提取数字 62 进行排序
    return int(item['task_id'].split('/')[-1])

def sort_and_inspect():
    # 配置：文件名和标签
    files_to_process = [
        {"path": "results_ours_n5_final.jsonl", "label": "🟢 Local (1.5B + MCTS)"},
        {"path": "results_deepseek_n1.jsonl",   "label": "🔴 DeepSeek API (SOTA)"}
    ]
    
    target_id = "HumanEval/62" # 我们要找的那个“奇迹样本”
    
    print(f"🧹 开始执行：排序 & 查找 {target_id}...\n")

    found_samples = {}

    for file_info in files_to_process:
        filename = file_info["path"]
        label = file_info["label"]
        
        if not os.path.exists(filename):
            print(f"❌ 找不到文件: {filename}")
            continue

        # 1. 读取
        with open(filename, 'r', encoding='utf-8') as f:
            data = []
            for line in f:
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except: pass
        
        # 2. 排序
        data.sort(key=sort_key)
        
        # 3. 覆盖写入（原地排序）
        with open(filename, 'w', encoding='utf-8') as f:
            for item in data:
                f.write(json.dumps(item) + "\n")
        
        print(f"✅ 文件已排序: {filename} (共 {len(data)} 条)")

        # 4. 提取目标题目
        target = next((x for x in data if x['task_id'] == target_id), None)
        if target:
            code = target.get('completion', '').strip()
            # 如果代码被markdown包裹，去掉它以便查看
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
                
            found_samples[label] = code

    # --- 打印对比 ---
    print("\n" + "="*60)
    print(f"⚔️  巅峰对决: {target_id} (Polynomial Derivative)")
    print("="*60)
    
    for label, code in found_samples.items():
        print(f"\n【 {label} 】")
        print("-" * 30)
        print(code)
        print("-" * 30)

if __name__ == "__main__":
    sort_and_inspect()