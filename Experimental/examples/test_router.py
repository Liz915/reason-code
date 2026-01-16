import sys
import os
import asyncio

# 确保能导入 src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reason_code.models.llm import generate_code_candidates
from src.reason_code.utils.logger import logger

async def test_routing():
    print("🧪 开始测试模型路由逻辑...\n")

    # Case 1: 简单任务 (期望: Local Qwen)
    print("1️⃣ 测试简单任务 (Easy)...")
    short_prompt = "def add(a, b): return a + b"
    await generate_code_candidates(short_prompt, n=1)
    

    print("\n" + "-"*30 + "\n")

    # Case 2: 困难任务 (期望: OpenAI Mock)
    print("2️⃣ 测试困难任务 (Hard)...")
    # 造一个超长的 prompt 触发 hard 阈值 (>1000 chars)
    long_prompt = "def complex_logic():\n" + "# context\n" * 100 
    await generate_code_candidates(long_prompt, n=1)


if __name__ == "__main__":
    asyncio.run(test_routing())