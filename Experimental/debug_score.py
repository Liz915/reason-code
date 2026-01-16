"""
Debug utility for diagnosing baseline failures.
Not used for any reported metrics.
"""

import json
import sys
import os

sys.path.insert(0, os.path.abspath("."))

from src.reason_code.executor.sandbox import execute_code

def debug_first_fail():
    print("🔍 开始诊断 Baseline 0分问题...")
    
    # 读取你刚才生成的基线文件
    file_path = "results_zeroshot.jsonl" 
    
    if not os.path.exists(file_path):
        print(f"❌ 找不到文件: {file_path}")
        return

    with open(file_path, "r") as f:
        # 只读第一行
        line = f.readline()
        if not line:
            print("❌ 文件是空的")
            return
            
        data = json.loads(line)
        task_id = data["task_id"]
        code = data["completion"]
        
        # 你的 Prompt (为了还原 HumanEval 真实运行环境，通常需要拼上 prompt + completion + test)
        # 这里我们先只跑代码，看看通不通
        print(f"\n🧪 正在测试 Task: {task_id}")
        print("-" * 20)
        print(f"💻 待执行代码片段 (前100字符):\n{code[:100]}...")
        print("-" * 20)
        
        # 尝试执行
        print("⚙️ 发送到 Sandbox 执行中...")
        result = execute_code(code)
        
        print(f"\n📝 Sandbox 返回结果:\n{result}")
        print("-" * 20)
        
        if "Error" in result or "Traceback" in result:
            print("❌ 诊断: 代码执行出错。请检查上面的错误信息。")
            if "IndentationError" in result:
                print("💡 提示: 可能是缩进问题。检查 sandbox.py 里的 wrapping 逻辑。")
            elif "not found" in result:
                print("💡 提示: 可能是 Docker 环境里缺包，或者 entry point 不对。")
        else:
            print("✅ 诊断: 代码似乎能运行，可能是 score_real.py 的判定逻辑太严了。")

if __name__ == "__main__":
    debug_first_fail()