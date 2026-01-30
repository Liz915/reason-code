import argparse
import asyncio
import json
import os
import sys
import time
import random
from tqdm.asyncio import tqdm

# 路径适配
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reason_code.models.llm import generate_code_candidates
from src.reason_code.agent.mcts import EnhancedMCTS

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1)
    parser.add_argument("--mode", type=str, default="baseline", choices=["baseline", "mcts"])
    # 🔥 新增 strategy 参数，用于 Ablation (UCB vs Random)
    parser.add_argument("--strategy", type=str, default="ucb", choices=["ucb", "random"], help="Search strategy")
    parser.add_argument("--range_start", type=int, default=None)
    parser.add_argument("--range_end", type=int, default=None)
    args = parser.parse_args()

    input_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data/final/data_mbpp.jsonl")
    if not os.path.exists(input_file):
        # 尝试相对路径兜底
        input_file = "data_mbpp.jsonl"
        if not os.path.exists(input_file):
            print(f"❌ 找不到输入文件，请确认 data/final/data_mbpp.jsonl 存在")
            return

    # 输出文件名带上 strategy，防止覆盖
    suffix = f"_{args.strategy}" if args.mode == "mcts" else ""
    output_file = f"results_mbpp_{args.mode}_n{args.n}{suffix}.jsonl"
    
    print(f"🚀 Running MBPP Experiment | Mode: {args.mode} | N={args.n} | Strategy: {args.strategy}")
    
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

    all_tasks = []
    with open(input_file, 'r') as f:
        for line in f:
            if line.strip():
                all_tasks.append(json.loads(line))
    
    start_idx = args.range_start if args.range_start is not None else 0
    end_idx = args.range_end if args.range_end is not None else len(all_tasks)
    all_tasks = all_tasks[start_idx:end_idx]

    tasks_to_run = [t for t in all_tasks if t['task_id'] not in finished_tasks]
    print(f"📂 剩余任务: {len(tasks_to_run)}")

    if not tasks_to_run:
        print("✅ 全部完成")
        return

    # 并发控制：MCTS 很吃资源，并发设小一点
    sem_limit = 1 
    sem = asyncio.Semaphore(sem_limit) 

    async def process_task(task):
        async with sem:
            task_id = task["task_id"]
            prompt = task["prompt"]
            
            # 构造 MBPP 的完整 Prompt (加上 Entry Point)
            # 注意：MBPP 的 prompt 字段通常已经包含了函数签名，但也可能需要微调
            # 这里假设 data_mbpp.jsonl 里的 prompt 是干净的
            
            # 为了严谨，MBPP 通常需要把 test case 拼成 runner script
            # 这里的 task 结构应该是 {'task_id':..., 'prompt':..., 'test':...}
            test_code = task.get("test", "")
            entry_point = task.get("entry_point", "")
            
            # 构造运行脚本 (用于 Reflexion 执行)
            runner_script = f"\n{test_code}\ncheck({entry_point})"
            
            try:
                start_time = time.time() # ⏱️ 开始计时
                
                if args.mode == "mcts":
                    # 🔥 传入 strategy 参数
                    # 注意：需要在 mcts.py 的 __init__ 里接收这个参数
                    agent = EnhancedMCTS(
                        root_code=prompt, 
                        n_simulations=args.n, 
                        n_candidates=1,
                        selection_strategy=args.strategy 
                    )
                    completion = await agent.run(test_runner=runner_script) 
                else:
                    candidates = await generate_code_candidates(prompt, n=args.n, mode="baseline")
                    completion = candidates
                
                end_time = time.time() # ⏱️ 结束计时
                latency = end_time - start_time
                
                return {
                    "task_id": task_id,
                    "completion": completion,
                    "prompt": prompt,
                    "mode": args.mode,
                    "n": args.n,
                    "strategy": args.strategy if args.mode == "mcts" else "n/a",
                    "latency_seconds": latency # ✅ 记录时间
                }
            except Exception as e:
                print(f"❌ Error {task_id}: {e}")
                # 失败也要记录，方便 Debug，但 latency 记为 0
                return None

    futures = [process_task(t) for t in tasks_to_run]
    
    # 实时写入文件
    for f in tqdm(asyncio.as_completed(futures), total=len(futures), desc="MBPP Running"):
        res = await f
        if res:
            with open(output_file, 'a') as f_out:
                f_out.write(json.dumps(res) + "\n")

    print(f"✅ 完成！结果保存在 {output_file}")

if __name__ == "__main__":
    asyncio.run(main())