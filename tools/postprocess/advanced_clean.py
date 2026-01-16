import json
import re
import argparse
import sys

def extract_code(text):
    # 1. 优先尝试提取 Markdown 代码块 (最稳)
    pattern = r"```python\s*(.*?)\s*```"
    match = re.search(pattern, text, re.DOTALL)
    if match:
        return match.group(1).strip()
    
    # 2. 尝试通用代码块
    pattern_generic = r"```\s*(.*?)\s*```"
    match_generic = re.search(pattern_generic, text, re.DOTALL)
    if match_generic:
        return match_generic.group(1).strip()
        
    # 3. 如果没有代码块，进行“去噪”处理
    lines = text.split('\n')
    clean_lines = []
    for line in lines:
        # 去掉包含中文字符的行 (这是 Instruct 模型废话的特征)
        if any(u'\u4e00' <= c <= u'\u9fff' for c in line):
            continue
        # 去掉 MCTS 的注释痕迹
        if "# 失败候选" in line or "# 错误:" in line or "IndentationError" in line:
            continue
        clean_lines.append(line)
    
    return '\n'.join(clean_lines).strip()

def main(input_file, output_file):
    print(f"🧼 Deep cleaning: {input_file}")
    records = []
    
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip(): continue
            data = json.loads(line)
            
            raw = data.get('completion', '')
            clean = extract_code(raw)
            
            # 如果清洗后为空，但原文本不为空，保留原文本(万一是对的呢)
            # 但如果是纯中文废话，清空也好
            data['completion'] = clean
            records.append(data)

    with open(output_file, 'w', encoding='utf-8') as f:
        for record in records:
            f.write(json.dumps(record) + '\n')
            
    print(f"✅ Saved cleaned data to: {output_file}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    args = parser.parse_args()
    main(args.input, args.output)
