import sys
import os
import json
import asyncio
from typing import List

# 确保能导入 src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reason_code.agent.mcts import EnhancedMCTS
# 需要安装 datasets: pip install datasets
from datasets import load_dataset 
from tqdm.asyncio import tqdm

async def run_one_problem(problem, output_file):
    task_id = problem["task_id"]
    prompt = problem["prompt"]
    # HumanEval 的 test 通常包含在 test 字段里
    test_code = problem["test"]
    entry_point = problem["entry_point"]
    
    # 构造一个适合我们 Agent 的 Prompt
    # 告诉 Agent 不要重复 prompt，只写函数体
    full_prompt = f"{prompt}\n    # TODO: Implement {entry_point}\n"
    
    # 构造 Runner 代码 (把生成的代码和测试代码拼起来)
    runner_script = f"\n{test_code}\ncheck({entry_point})"

    try:
        # 实例化 Agent (为了跑得快，论文实验可以把 simulations 设为 10)
        agent = EnhancedMCTS(root_code=full_prompt, n_simulations=1, n_candidates=1)
        
        # 运行
        generated_code = await agent.run(runner_script)
        
        result = {
            "task_id": task_id,
            "completion": generated_code,
            "prompt": prompt,
            "status": "generated"
        }
    except Exception as e:
        result = {
            "task_id": task_id,
            "completion": "",
            "status": "failed",
            "error": str(e)
        }
    
    # 实时写入文件 (防止跑一半断电)
    with open(output_file, "a") as f:
        f.write(json.dumps(result) + "\n")

async def main():
    print("🚀 Loading HumanEval dataset...")
    dataset = load_dataset("openai_humaneval", split="test")
    dataset = dataset.select(range(90, 110))
    
    output_file = "humaneval_results_mcts.jsonl"
    
    # 如果文件存在，先清空或跳过已跑的
    if os.path.exists(output_file):
        os.remove(output_file)

    print(f"🔥 Starting Evaluation on {len(dataset)} problems...")
    
    # 限制并发数，防止 M1 显存爆炸
    # 使用 Semaphore 控制并发
    sem = asyncio.Semaphore(1) # M1 上建议串行，或者最多 2 并发

    async def sem_task(problem):
        async with sem:
            await run_one_problem(problem, output_file)

    tasks = [sem_task(p) for p in dataset]
    await tqdm.gather(*tasks)
    
    print("✅ Evaluation Complete!")

if __name__ == "__main__":
    asyncio.run(main())