#!/usr/bin/env python3
"""
自我进化训练循环
"""

import os
import subprocess
import time

def self_evolution_cycle(cycles=3):
    """自我进化循环"""
    
    for cycle in range(cycles):
        print(f"\n=== 自我进化循环 {cycle + 1}/{cycles} ===")
        
        # 1. 运行测试收集数据
        print("1. 运行测试收集数据...")
        subprocess.run(["python", "benchmarks/performance_test.py"], check=False)
        
        # 2. 检查是否有新数据
        success_count = 0
        if os.path.exists("logs/success_cases.jsonl"):
            with open("logs/success_cases.jsonl", "r") as f:
                success_count = len([line for line in f if line.strip()])
        
        print(f"   成功案例数: {success_count}")
        
        if success_count < 5:  # 数据太少
            print("   ⚠️ 数据不足，使用基础数据增强")
            subprocess.run(["python", "tools/augment_training_data.py"], check=True)
            data_file = "augmented_sft_data.jsonl"
        else:
            data_file = "logs/success_cases.jsonl"
        
        # 3. 训练新模型
        print("2. 训练新模型...")
        model_name = f"lora-reason-coder-cycle-{cycle+1}"
        subprocess.run([
            "python", "tools/finetune_lora.py", 
            data_file, model_name
        ], check=False)
        
        # 4. 更新模型链接
        print("3. 更新模型...")
        if os.path.exists("lora-reason-coder"):
            os.rename("lora-reason-coder", f"lora-reason-coder-backup-{cycle}")
        
        if os.path.exists(model_name):
            os.rename(model_name, "lora-reason-coder")
        
        print(f"✅ 循环 {cycle + 1} 完成")
        time.sleep(2)

if __name__ == "__main__":
    self_evolution_cycle(cycles=2)  # 运行2个循环