import json
import statistics

def diagnose(file_path):
    print(f"🕵️‍♂️ Diagnosing: {file_path}")
    
    data = []
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    try:
                        data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    except FileNotFoundError:
        print(f"❌ Error: File {file_path} not found!")
        return
    
    total = len(data)
    if total == 0:
        print("❌ Error: No valid data found in file.")
        return

    lengths = []
    truncated_suspects = 0
    empty_counts = 0
    
    for item in data:
        code = item.get('completion', '')
        if not code:
            empty_counts += 1
            continue
            
        lengths.append(len(code))
        
        # 简单判断截断：长度接近阈值(256 tokens * 4 ≈ 1000 chars)
        if len(code) > 800: 
            truncated_suspects += 1

    avg_len = statistics.mean(lengths) if lengths else 0
    max_len = max(lengths) if lengths else 0
    
    print("-" * 40)
    print(f"📊 Total Samples: {total}")
    print(f"🚫 Empty Completions: {empty_counts} ({empty_counts/total:.1%})")
    print(f"📏 Avg Length (chars): {avg_len:.0f}")
    print(f"📏 Max Length (chars): {max_len}")
    print(f"✂️  Potential Truncations: {truncated_suspects}")
    print("-" * 40)
    
    if empty_counts > 10:
        print("💡 Insight: Too many empty outputs! Check your prompt template.")
    elif truncated_suspects > 20:
        print("💡 Insight: Max Token Limit (256) is likely too short!")
    else:
        print("💡 Insight: Length seems fine. The issue might be model capability (Logic Error).")

if __name__ == "__main__":
    # 诊断清洗后的文件
    diagnose("humaneval_results_clean.jsonl")
