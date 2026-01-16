import math
import asyncio
from typing import Optional, List, Any, Dict
from dataclasses import dataclass, field

import structlog
from src.reason_code.utils.logger import logger as global_logger
logger = structlog.get_logger(__name__)
from src.reason_code.utils.trace import trace_span
from src.reason_code.models.llm import generate_code_candidates
from src.reason_code.executor.sandbox import execute_code
from src.reason_code.executor.evaluator import evaluate_code, evaluate_candidates_async
from src.reason_code.utils.config import MCTS_C
from src.reason_code.agent.retriever import simple_retrieve 
from src.reason_code.models.router import router
from src.reason_code.agent.reflexion import attempt_fix

@dataclass
class Node:
    code: str
    parent: Optional["Node"]
    visits: int = 0
    wins: float = 0.0
    children: List["Node"] = field(default_factory=list)
    last_result: Any = None
    evaluation_result: Any = None

    def ucb_score(self, c: float = MCTS_C):
        if self.visits == 0:
            return float("inf")
        parent_visits = self.parent.visits if self.parent else 1
        return (self.wins / self.visits) + c * math.sqrt(math.log(parent_visits) / self.visits)

class EnhancedMCTS:
    """增强版MCTS：集成分级评估与自我修复 (Final Fix Version)"""
    
    def __init__(self, root_code: str, n_simulations: int = 30, n_candidates: int = 3):
        self.root = Node(code=root_code, parent=None)
        self.n_simulations = n_simulations
        self.n_candidates = n_candidates
        self.stats = {
            "syntax_checks": 0,
            "static_analyses": 0, 
            "runtime_tests": 0,
            "early_rejects": 0,
            "llm_calls": 0
        }
    
    @trace_span(span_name="mcts_run")
    async def run(self, test_runner: str):
        logger.info("mcts_start", n_simulations=self.n_simulations, root_code_preview=self.root.code[:50])
        
        for i in range(self.n_simulations):
            log = logger.bind(iteration=i)
            node = self._select(self.root)
            reward = await self._expand_and_simulate(node, test_runner)
            self._backpropagate(node, reward)
            
            # 如果已经找到完美解，其实可以提前退出，但为了跑满数据收集，这里选择继续或者你可以加逻辑退出
            if reward == 1.0:
                 log.info("perfect_solution_found_in_simulation")

            if (i + 1) % 5 == 0:  
                log.info("mcts_progress", progress=f"{i+1}/{self.n_simulations}")
        
        best = self._get_best_child()
        final_code = best.code if best else self.root.code
        
        logger.info("mcts_complete", best_wins=best.wins if best else 0)
        return final_code

    def _select(self, node: Node) -> Node:
        # 典型的 UCB 选择
        while node.children:
            node = max(node.children, key=lambda n: n.ucb_score())
        return node

    def _get_best_child(self):
        # 选择访问次数最多或胜率最高的子节点
        if not self.root.children:
            return None
        # 优先选 Reward 高的，其次选访问次数多的
        return max(self.root.children, key=lambda n: (n.wins, n.visits))

    @trace_span(span_name="expand_node")
    async def _expand_and_simulate(self, node: Node, test_runner: str) -> float:
        # 1. 构建 Prompt
        prompt = self._build_prompt(node, test_runner)
        self.stats["llm_calls"] += 1
        
        # 2. 动态调整 LLM 模式
        # 如果是根节点，用 default (384 tokens)
        # 如果是子节点（意味着正在修复或优化），用 reflexion (512+ tokens)
        mode = "reflexion" if node.parent else "default"
        
        candidates = await generate_code_candidates(prompt, n=self.n_candidates, mode=mode)

        # 3. 批量评估
        eval_results = await evaluate_candidates_async(candidates, test_runner, prompt)

        best_reward = 0.0

        for cand, eval_result in zip(candidates, eval_results):
            final_code = cand
            final_result = eval_result
            
            overall = eval_result.get("overall", {})
            passed = overall.get("passed", False)
            failed_at = overall.get("failed_at")
            reward = overall.get("reward", 0.0)

            # 🔥 核心修复逻辑：Reflexion 触发条件 🔥
            # 只要没通过，且死在了 Runtime (level_3)，就尝试修复
            # 不再依赖具体的 reward 数值
            if not passed and failed_at == "level_3":
                error_msg = eval_result.get("level_3", {}).get("message", "Unknown Error")
                
                # 记录尝试修复
                logger.info("reflexion_attempt", error_preview=error_msg[:50])
                
                self.stats["llm_calls"] += 1
                fixed_code = await attempt_fix(cand, error_msg, test_runner)
                
                if fixed_code != cand:
                    # 如果代码变了，重新评估
                    new_result = evaluate_code(fixed_code, test_runner) # 同步调用即可
                    
                    # 如果修复后通过了 (Reward=1.0)
                    if new_result["overall"].get("passed"):
                        logger.info("reflexion_success", original_reward=reward, new_reward=1.0)
                        final_code = fixed_code
                        final_result = new_result
                        reward = 1.0 # 更新 Reward
                    else:
                        logger.info("reflexion_failed_still_bad")
                        # 即使没完全修好，也可以选择保留新代码作为一个探索分支
                        # 这里我们保留新代码，看看它会不会比旧的稍微好一点（虽然 reward 可能还是 0）
                        final_code = fixed_code
                        final_result = new_result

            # 4. 创建新节点挂载到树上
            child = Node(code=final_code, parent=node)
            child.evaluation_result = final_result
            child.last_result = final_result.get("overall", {})
            
            # 初始化子节点统计
            child.visits = 1
            child.wins = reward
            
            node.children.append(child)
            self._update_stats(final_result)

            if reward > best_reward:
                best_reward = reward

        return best_reward

    def _update_stats(self, eval_result: dict):
        for level in ["level_1", "level_2", "level_3"]:
            if level in eval_result:
                if level == "level_1": self.stats["syntax_checks"] += 1
                elif level == "level_2": self.stats["static_analyses"] += 1
                elif level == "level_3": self.stats["runtime_tests"] += 1
                if not eval_result[level]["passed"] and level != "level_3":
                    self.stats["early_rejects"] += 1

    def _build_prompt(self, node: Node, test_runner: str) -> str:
        # 🔥 核心修复：纯英文 Prompt，区分 Root 和 Child
        
        # Case 1: 根节点 (Task Prompt) -> "Implement this"
        if node.parent is None:
            # node.code 这里是题目的 docstring/signature
            return f"""{node.code}
            
# Instruction
Please implement the function above. 
Ensure the code is complete, correct, and wrapped in ```python ... ``` blocks.
"""

        # Case 2: 子节点 (Reflexion/Refinement) -> "Fix this"
        prompt = f"Current Code:\n```python\n{node.code}\n```\n\n"
        
        if node.evaluation_result:
            failed_level = node.evaluation_result["overall"].get("failed_at")
            if failed_level and failed_level in node.evaluation_result:
                level_msg = node.evaluation_result[failed_level].get("message", "")
                prompt += f"[Error Message]\n{level_msg}\n\n"
        
        prompt += "# Instruction\nFix the code above to pass the tests. Return ONLY the fixed Python code wrapped in ```python ... ```."
        return prompt

    def _backpropagate(self, node: Node, reward: float):
        cur = node
        while cur:
            cur.visits += 1
            cur.wins += reward
            cur = cur.parent