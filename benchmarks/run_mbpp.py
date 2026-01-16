import argparse
import asyncio
import json
import os
import sys
import time
from tqdm.asyncio import tqdm

# 路径适配
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reason_code.models.llm import generate_code_candidates
from src.reason_code.agent.mcts import EnhancedMCTS

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--mode", type=str, default="baseline", choices=["baseline", "mcts", "reflexion"])
    args = parser.parse_args()

    input_file = "data_mbpp.jsonl"
    if not os.path.exists(input_file):
        print(f"❌ 找不到 {input_file}")
        return

    output_file = f"results_mbpp_{args.mode}_n{args.n}.jsonl"
    print(f"🚀 Running MBPP Experiment | Mode: {args.mode} | N={args.n}")
    
    # 断点续传
    finished_tasks = set()
    if os.path.exists(output_file):
        print(f"🔄 读取现有进度...")
        with open(output_file, 'r') as f:
            for line in f:
                if line.strip():
                    try:
                        d = json.loads(line)
                        finished_tasks.add(d['task_id'])
                    except: pass
        print(f"⏩ 跳过 {len(finished_tasks)} 题")
    else:
        with open(output_file, 'w') as f: pass

    all_tasks = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                all_tasks.append(json.loads(line))
    
    tasks_to_run = [t for t in all_tasks if t['task_id'] not in finished_tasks]
    print(f"📂 剩余任务: {len(tasks_to_run)}")

    if not tasks_to_run:
        print("✅ 全部完成")
        return

    # 并发控制：N越大，并发越要小
    sem_limit = 1 if args.n >= 5 else 5
    sem = asyncio.Semaphore(sem_limit) 

    async def process_task(task):
        async with sem:
            task_id = task["task_id"]
            prompt = task["prompt"]
            
            #  心跳日志
            print(f"▶️ Start {task_id}...", end="\r") 
            
            try:
                start_time = time.time()
                if args.mode == "mcts":
                    agent = EnhancedMCTS(root_code=prompt, n_simulations=args.n, n_candidates=1)
                    completion = await agent.run(test_runner="python") 
                else:
                    # 保持 batch 生成，避免 diversity collapse
                    candidates = await generate_code_candidates(prompt, n=args.n, mode=args.mode)
                    completion = candidates
                
                duration = time.time() - start_time
                
                
                return {
                    "task_id": task_id,
                    "completion": completion,
                    "prompt": prompt,
                    "mode": args.mode,
                    "n": args.n
                }
            except Exception as e:
                print(f"❌ Error {task_id}: {e}")
                return None

    futures = [process_task(t) for t in tasks_to_run]
    
    for f in tqdm(asyncio.as_completed(futures), total=len(futures), desc="Generating"):
        res = await f
        if res:
            with open(output_file, 'a') as f_out:
                f_out.write(json.dumps(res) + "\n")

    print(f"✅ 完成！结果保存在 {output_file}")

if __name__ == "__main__":
    asyncio.run(main())