import json
import re
import os
from datasets import load_dataset
from tqdm import tqdm

def extract_signature(code):
    """
    从代码中提取完整的函数签名 (e.g., 'def my_func(x, y):')
    """
    # 匹配 def 开头，直到冒号结束的行
    # re.DOTALL 允许匹配跨行的参数定义
    match = re.search(r"def\s+[a-zA-Z_][a-zA-Z0-9_]*\s*\(.*?\)\s*:", code, re.DOTALL)
    if match:
        return match.group(0).strip()
    return None

def extract_function_name(signature):
    """从签名中提取函数名，用于 entry_point"""
    match = re.search(r"def\s+([a-zA-Z_][a-zA-Z0-9_]*)\s*\(", signature)
    if match:
        return match.group(1)
    return None

def format_mbpp_to_jsonl():
    print("🚀 正在加载 MBPP (Sanitized) 数据集...")
    try:
        # 尝试加载 sanitized 版本
        dataset = load_dataset("mbpp", "sanitized", split="test")
    except Exception as e:
        print(f"❌ 加载 sanitized 失败: {e}")
        return

    # 🔥 调试信息：打印第一条数据的 Key，确保字段名正确
    if len(dataset) > 0:
        print(f"📋 数据集字段预览: {list(dataset[0].keys())}")

    output_file = "data_mbpp.jsonl"
    converted_data = []

    print(f"🔄 正在转换 {len(dataset)} 条数据...")
    
    success_count = 0
    for item in tqdm(dataset):
        task_id = f"MBPP/{item['task_id']}"
        
        # 🔥 修正点：MBPP Sanitized 通常用 'prompt' 存储描述
        # 如果 'text' 不存在，尝试 'prompt'，再不行用空字符串防止报错
        description = item.get('text') or item.get('prompt') or ""
        
        tests = item['test_list']
        reference_code = item['code']
        
        # 1. 提取完整函数签名 (关键步骤！)
        signature = extract_signature(reference_code)
        
        if not signature:
            # print(f"⚠️ 跳过 Task {task_id}: 无法提取函数签名") # 减少刷屏
            continue
            
        entry_point = extract_function_name(signature)
        if not entry_point:
            continue

        # 2. 构造 Prompt (In-Context Definition)
        # 格式：
        # def func(a, b):
        #     """
        #     description
        #     """
        prompt = f'{signature}\n    """\n    {description}\n    """\n'

        # 3. 构造 Test Block
        test_block = "\n".join(tests)

        task_obj = {
            "task_id": task_id,
            "prompt": prompt,
            "entry_point": entry_point,
            "canonical_solution": reference_code,
            "test": test_block
        }
        converted_data.append(task_obj)
        success_count += 1

    with open(output_file, 'w', encoding='utf-8') as f:
        for item in converted_data:
            f.write(json.dumps(item) + "\n")
    
    print(f"✅ 转换完成！已保存到 {output_file}")
    print(f"📊 成功转换: {success_count}/{len(dataset)}")
    
    if len(converted_data) > 0:
        print("\n[Preview Item]")
        print(json.dumps(converted_data[0], indent=2))

if __name__ == "__main__":
    format_mbpp_to_jsonl()