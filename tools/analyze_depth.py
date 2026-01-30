import json
import argparse
import numpy as np

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Path to MCTS log file (jsonl)")
    args = parser.parse_args()
    
    # 如果 completion 很长，或者我们能从日志恢复树深
    # 但因为我们现在的 jsonl 只存了最终结果，我们用“生成长度”作为深度的 Proxy
    
    print("注：精确的深度分析需要解析详细 Log (n10_local_log.txt)。")
    print("这里我们统计 '代码长度' 分布，作为复杂度的侧面证据。")
    
    lens = []
    with open(args.file, "r") as f:
        for line in f:
            try:
                data = json.loads(line)
                code = data['completion']
                if isinstance(code, list): code = code[0]
                lens.append(len(code))
            except: pass
            
    print(f"Avg Code Length: {np.mean(lens):.0f} chars")
    print(f"Max Code Length: {np.max(lens)} chars")

if __name__ == "__main__":
    main()