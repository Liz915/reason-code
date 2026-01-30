import json
import argparse
import numpy as np
import os

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("files", nargs='+', help="Path to result jsonl files")
    args = parser.parse_args()
    
    print(f"{'Method':<30} | {'Avg (s)':<10} | {'P95 (s)':<10} | {'Count':<5}")
    print("-" * 65)

    for filepath in args.files:
        if not os.path.exists(filepath): continue
        
        latencies = []
        with open(filepath, "r") as f:
            for line in f:
                try:
                    data = json.loads(line)
                    # 兼容可能存在的不同命名
                    lat = data.get("latency_seconds")
                    if lat is not None:
                        latencies.append(float(lat))
                except: pass
        
        if not latencies:
            print(f"{os.path.basename(filepath):<30} | {'N/A':<10} | {'N/A':<10} | 0")
            continue

        avg_lat = np.mean(latencies)
        p95_lat = np.percentile(latencies, 95)
        
        print(f"{os.path.basename(filepath):<30} | {avg_lat:<10.2f} | {p95_lat:<10.2f} | {len(latencies)}")

if __name__ == "__main__":
    main()