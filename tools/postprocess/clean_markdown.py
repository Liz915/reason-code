import json
import re
import argparse
import sys

def clean_markdown(input_file, output_file):
    print(f"🧹 Cleaning Markdown from: {input_file}")
    
    clean_count = 0
    records = []
    
    try:
        with open(input_file, 'r', encoding='utf-8') as f:
            for line in f:
                if not line.strip(): continue
                try:
                    data = json.loads(line)
                    raw_code = data.get('completion', '')
                    
                    # 清洗逻辑: 移除 ```python 和 ``` 
                    clean_code = re.sub(r'^```python\s*', '', raw_code, flags=re.MULTILINE)
                    clean_code = re.sub(r'^```\s*', '', clean_code, flags=re.MULTILINE)
                    clean_code = re.sub(r'```$', '', clean_code, flags=re.MULTILINE)
                    
                    data['completion'] = clean_code.strip()
                    records.append(data)
                    clean_count += 1
                except json.JSONDecodeError:
                    continue
    except FileNotFoundError:
        print(f"❌ Error: Input file '{input_file}' not found!")
        sys.exit(1)

    with open(output_file, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
            
    print(f"✅ Cleaned {clean_count} records. Saved to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="humaneval_results_mcts.jsonl")
    parser.add_argument("--output", default="humaneval_results_clean.jsonl")
    args = parser.parse_args()
    
    clean_markdown(args.input, args.output)
