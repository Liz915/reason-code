import json
import os
import sys
import asyncio
from datasets import load_dataset
from tqdm.asyncio import tqdm

# 引入项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from src.reason_code.agent.mcts import EnhancedMCTS

INPUT_FILE = "humaneval_results_clean.jsonl"
OUTPUT_FILE = "humaneval_results_patched.jsonl"

async def run_one_problem(problem, n_simulations):
    task_id = problem["task_id"]
    prompt = problem["prompt"]
    entry_point = problem["entry_point"]
    
    full_prompt = f"{prompt}\n    # TODO: Implement {entry_point}\n"
    
    try:
        # N=10, 这里的 agent 会调用你刚修改过(512 token)的 llm.py
        agent = EnhancedMCTS(root_code=full_prompt, n_simulations=n_simulations, n_candidates=1)
        generated_code = await agent.run("") 
        
        result = {
            "task_id": task_id,
            "completion": generated_code,
            "prompt": prompt,
            "status": "patched",
            "n_simulations": n_simulations
        }
    except Exception as e:
        print(f"❌ Patch failed for {task_id}: {e}")
        result = {
            "task_id": task_id,
            "completion": "",
            "prompt": prompt,
            "status": "failed"
        }
    return result

async def main():
    print("🔍 Identifying truncated/failed tasks...")
    
    previous_results = {}
    if not os.path.exists(INPUT_FILE):
        print(f"❌ Error: {INPUT_FILE} not found! Did you verify the cleaning step?")
        return

    with open(INPUT_FILE, 'r') as f:
        for line in f:
            if line.strip():
                item = json.loads(line)
                previous_results[item['task_id']] = item

    # 筛选条件：长度 > 800 (疑似截断) OR 代码太短/为空
    targets = []
    for task_id, item in previous_results.items():
        code = item.get('completion', '')
        if len(code) > 800 or len(code) < 10:
            targets.append(task_id)
            
    print(f"🎯 Found {len(targets)} tasks that look truncated or empty.")
    
    if not targets:
        print("No targets found. Maybe 800 threshold is too high? Or file is perfect.")
        return

    # 加载数据集
    ds = load_dataset("openai_humaneval", split="test")
    problems_to_run = [p for p in ds if p['task_id'] in targets]
    
    print(f"🚀 Starting Rescue Mission for {len(problems_to_run)} tasks...")

    # 运行
    results_map = {}
    sem = asyncio.Semaphore(1)

    async def sem_task(problem):
        async with sem:
            return await run_one_problem(problem, n_simulations=10)

    tasks = [sem_task(p) for p in problems_to_run]
    new_results = await tqdm.gather(*tasks)
    
    for res in new_results:
        results_map[res['task_id']] = res
        
    # 合并写入
    final_count = 0
    with open(OUTPUT_FILE, 'w') as f:
        for problem in ds:
            tid = problem['task_id']
            if tid in results_map:
                f.write(json.dumps(results_map[tid]) + "\n")
            elif tid in previous_results:
                f.write(json.dumps(previous_results[tid]) + "\n")
            final_count += 1
            
    print(f"✅ Rescue Complete! Saved {final_count} tasks to {OUTPUT_FILE}")
    print("👉 Next steps:")
    print("   1. python tools/clean_markdown.py --input humaneval_results_patched.jsonl --output humaneval_final.jsonl")
    print("   2. python tools/score_real.py humaneval_final.jsonl")

if __name__ == "__main__":
    asyncio.run(main())
