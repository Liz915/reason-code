#!/usr/bin/env python3
"""
增强训练数据 - 创建更多样化的训练样本
"""

import json
import random

def augment_training_data():
    """增强训练数据"""
    
    # 读取现有成功案例
    try:
        with open("logs/success_cases.jsonl", "r") as f:
            success_cases = [json.loads(line) for line in f if line.strip()]
    except:
        success_cases = []
    
    print(f"现有成功案例: {len(success_cases)} 条")
    
    # 基础训练数据模板
    base_cases = [
        {
            "instruction": "修复以下add函数的代码错误:\n```python\ndef add(a, b): return a - b\n```",
            "input": "",
            "output": "def add(a, b): return a + b"
        },
        {
            "instruction": "修复以下multiply函数的代码错误:\n```python\ndef multiply(a, b): return a\n```", 
            "input": "",
            "output": "def multiply(a, b): return a * b"
        },
        {
            "instruction": "修复以下subtract函数的代码错误:\n```python\ndef subtract(a, b): return a + b\n```",
            "input": "", 
            "output": "def subtract(a, b): return a - b"
        },
        {
            "instruction": "修复以下divide函数的代码错误:\n```python\ndef divide(a, b): return a * b\n```",
            "input": "",
            "output": "def divide(a, b): return a / b"
        }
    ]
    
    # 合并数据
    all_cases = base_cases + success_cases
    
    # 保存增强数据
    with open("augmented_sft_data.jsonl", "w") as f:
        for case in all_cases:
            f.write(json.dumps(case, ensure_ascii=False) + "\n")
    
    print(f"增强后训练数据: {len(all_cases)} 条")
    print("保存到: augmented_sft_data.jsonl")

if __name__ == "__main__":
    augment_training_data()