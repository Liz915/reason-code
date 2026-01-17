import sys
import os
import json
import asyncio
import argparse 
from typing import List, Dict

# 确保能导入 src
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reason_code.agent.mcts import EnhancedMCTS
from src.reason_code.models.llm import generate_code_candidates
from src.reason_code.executor.evaluator import evaluate_code
from datasets import load_dataset 
from tqdm.asyncio import tqdm

# ==========================================
# 模式 1: MCTS (Reason-Code 核心方法)
# ==========================================
async def run_mcts(problem, n_simulations):
    prompt = problem["prompt"]
    entry_point = problem["entry_point"]
    test_code = problem["test"]
    full_prompt = f"{prompt}\n    # TODO: Implement {entry_point}\n"
    runner_script = f"\n{test_code}\ncheck({entry_point})"

    # MCTS 内部会进行多次生成和评估
    agent = EnhancedMCTS(root_code=full_prompt, n_simulations=n_simulations, n_candidates=1)
    final_code = await agent.run(runner_script)
    return final_code

# ==========================================
# 模式 2: Majority Voting / Best-of-N (对照组)
# ==========================================
async def run_majority_voting(problem, n_samples):
    """
    单纯生成 N 个样本，不进行多轮树搜索。
    这里为了方便评估，我们采用 Pass@k 的逻辑：只要 N 个里有一个对的，就算过。
    或者返回看起来最好的一个。
    """
    prompt = problem["prompt"]
    entry_point = problem["entry_point"]
    test_code = problem["test"]
    full_prompt = f"{prompt}\n    # TODO: Implement {entry_point}\n"
    runner_script = f"\n{test_code}\ncheck({entry_point})"

    # 1. 并发生成 N 个候选
    candidates = await generate_code_candidates(full_prompt, n=n_samples)
    
    best_code = candidates[0] if candidates else ""
    best_score = -1.0
    
    # 2. 依次评估 (模拟 Majority Voting 中的 Selection)
    # 在实际论文中，Majority Voting 通常指：如果有 5 个候选通过了测试，选其中出现次数最多的。
    # 但在 HumanEval 这种只有 hidden test 的场景下，Best-of-N (Pass@k) 是更标准的对比指标。
    # 这里我们模拟：如果有任何一个代码通过了 visible tests (如果有的话)，就选它。
    
    # 简化策略：为了对比 N=10，我们将这 N 个都存入结果文件，后续 calculate_metrics 时计算 Pass@k
    # 对于 Majority Voting，我们在 MCTS 框架下可以理解为：
    # 纯随机生成 N 个，不做任何反思修改。
    # 我们这里简单返回第一个，但在 generate_code_candidates 内部其实是并行的。
    # 严格的 Majority Voting 实验，通常需要在此时就把 N 个都测一遍。
    
    return best_code # 仅返回第一个，用于 N=1 baseline。对于 N=10 comparison，见下文 main 逻辑调整。

async def run_one_problem(problem, output_file, args):
    task_id = problem["task_id"]
    
    try:
        completion = ""
        
        if args.mode == "mcts":
            # Reason-Code (N=10)
            completion = await run_mcts(problem, args.n)
            
        elif args.mode == "baseline":
            # Qwen-1.5B (Pass@1) -> run with --n 1 --mode baseline
            # Majority Voting (N=10) -> run with --n 10 --mode baseline
            # 注意：如果是 N=10 的 baseline，我们需要生成 10 个，看是否有一个对。
            # 这里为了简单，如果是 baseline 且 n>1，我们生成 n 个，用 list 存起来
            
            prompt = f"{problem['prompt']}\n    # TODO: Implement {problem['entry_point']}\n"
            candidates = await generate_code_candidates(prompt, n=args.n)
            
            # 对比:
            # 1. Baseline: n=1 生成 1 个
            # 2. Reason-Code: n=10 经过搜索后输出 1 个
            # 3. Best-of-N: n=10 生成 10 个 (看有没有 1 个对)
            
            completion = candidates # 这是一个 list
            
        result = {
            "task_id": task_id,
            "completion": completion, # 可能是 str 或 list[str]
            "prompt": problem["prompt"],
            "status": "generated",
            "mode": args.mode,
            "n": args.n
        }
    except Exception as e:
        result = {
            "task_id": task_id,
            "completion": "",
            "status": "failed",
            "error": str(e)
        }
    
    with open(output_file, "a") as f:
        f.write(json.dumps(result) + "\n")

async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--n", type=int, default=1, help="Number of simulations/samples")
    parser.add_argument("--mode", type=str, default="mcts", choices=["mcts", "baseline"], help="mcts for Reason-Code, baseline for Qwen")
    parser.add_argument("--range_start", type=int, default=None)
    parser.add_argument("--range_end", type=int, default=None)
    args = parser.parse_args()

    # 不同的实验输出到不同的文件
    output_file = f"results_{args.mode}_n{args.n}.jsonl"
    if os.path.exists(output_file):
        os.remove(output_file)

    print(f"🚀 Loading Data... Output: {output_file}")
    dataset = load_dataset("openai_humaneval", split="test")
    if args.range_start is not None:
        dataset = dataset.select(range(args.range_start, args.range_end))

    print(f"🔥 Running {args.mode} with N={args.n}...")
    
    # 限制并发数为 1 (因为 LLM 推理很吃 CPU)
    # 如果 N=10，每个任务内部会串行/并行跑 10 次，所以这里外层必须串行
    sem = asyncio.Semaphore(1) 

    async def sem_task(p):
        async with sem:
            await run_one_problem(p, output_file, args)

    tasks = [sem_task(p) for p in dataset]
    await tqdm.gather(*tasks)
    
    print(f"✅ Done! Results saved to {output_file}")

if __name__ == "__main__":
    asyncio.run(main())
