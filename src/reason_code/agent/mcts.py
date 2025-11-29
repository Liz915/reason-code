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
from src.reason_code.executor.evaluator import evaluate_code
from src.reason_code.utils.config import MCTS_C
from src.reason_code.agent.retriever import simple_retrieve 
from src.reason_code.models.router import router

@dataclass
class Node:
    code: str
    parent: Optional["Node"]
    visits: int = 0
    wins: float = 0.0
    children: List["Node"] = field(default_factory=list)
    last_result: Any = None
    evaluation_result: Any = None  # 新增：评估结果

    def ucb_score(self, c: float = MCTS_C):
        if self.visits == 0:
            return float("inf")
        parent_visits = self.parent.visits if self.parent else 1
        return (self.wins / self.visits) + c * math.sqrt(math.log(parent_visits) / self.visits)

class EnhancedMCTS:
    """增强版MCTS：集成分级评估"""
    
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
            
            #记录关键节点
            if (i + 1) % 5 == 0:  
                log.info("mcts_progress", progress=f"{i+1}/{self.n_simulations}")
        
        best = self._get_best_child()
        final_code = best.code if best else self.root.code
        
        logger.info("mcts_complete", best_wins=best.wins if best else 0)
        return final_code

    def _select(self, node: Node) -> Node:
        while node.children:
            node = max(node.children, key=lambda n: n.ucb_score())
        return node

    def _get_best_child(self):
        return max(self.root.children, key=lambda n: (n.wins / n.visits) if n.visits > 0 else -1, default=None)

    @trace_span(span_name="expand_node")
    async def _expand_and_simulate(self, node: Node, test_runner: str) -> float:
        prompt = self._build_prompt(node, test_runner)
        self.stats["llm_calls"] += 1
        # 并发请求 LLM 生成候选
        # 注意：llm.py 内部已经做了串行化处理以适应 MPS，这里无需改动接口
        candidates = await generate_code_candidates(prompt, n=self.n_candidates)

        # 并发评估所有候选
        from src.reason_code.executor.evaluator import evaluate_candidates_async
        eval_results = await evaluate_candidates_async(candidates, test_runner, prompt)

        best_reward = 0.0

        from src.reason_code.agent.reflexion import attempt_fix

        for cand, eval_result in zip(candidates, eval_results):
            
            final_code = cand
            final_result = eval_result
            
            # 🚑 抢救机制：如果运行时失败 (得分0.7)，尝试修复
            if eval_result["overall"]["reward"] == 0.7:
                failed_level = eval_result["overall"]["failed_at"]
                if failed_level == "level_3": # 运行时错误
                    error_msg = eval_result[failed_level]["message"]
                    
                    self.stats["llm_calls"] += 1
                    # 尝试修复
                    fixed_code = await attempt_fix(cand, error_msg, test_runner)
                    
                    if fixed_code != cand:
                        # 重新评估修复后的代码
                        # 这里简单同步调用 evaluate，或者你可以封装成 await
                        from src.reason_code.executor.evaluator import evaluate_code
                        new_result = evaluate_code(fixed_code, test_runner)
                        
                        if new_result["overall"]["reward"] > 0.7:
                        # 记录关键里程碑：Reflexion 成功救活了代码
                            logger.info(
                                "reflexion_success", 
                                score_improvement=f"0.7->{new_result['overall']['reward']}",
                                fixed_level=failed_level
                            )
                            final_code = fixed_code
                            final_result = new_result
                    else:
                        # 记录一次无效的尝试
                        logger.debug("reflexion_attempt_no_improvement")

            child = Node(code=final_code, parent=node)
            node.children.append(child)

            child.evaluation_result = final_result
            child.last_result = final_result.get("overall", {})
            node.children.append(child)

            child.evaluation_result = eval_result
            child.last_result = eval_result.get("overall", {})

            # 更新统计
            self._update_stats(eval_result)

            reward = eval_result.get("overall", {}).get("reward", 0.0)
            child.visits += 1
            child.wins += reward

            if reward > best_reward:
                best_reward = reward
                if reward == 1.0:
                    logger.info("solution_found", reward=1.0, code_preview=final_code[:30])
        return best_reward

    def _update_stats(self, eval_result: dict):
        """更新分级评估统计"""
        for level in ["level_1", "level_2", "level_3"]:
            if level in eval_result:
                if level == "level_1":
                    self.stats["syntax_checks"] += 1
                elif level == "level_2":
                    self.stats["static_analyses"] += 1
                elif level == "level_3":
                    self.stats["runtime_tests"] += 1
                
                if not eval_result[level]["passed"] and level != "level_3":
                    self.stats["early_rejects"] += 1

    def _build_prompt(self, node: Node, test_runner: str) -> str:
        prompt = f"当前代码:\n```python\n{node.code}\n```\n\n"
        
        # 简单的 RAG 检索
        retrieved = simple_retrieve(node.code, k=3)
        if retrieved:
            prompt += "\n\n# 以下是过去类似失败的修复参考："
            for r in retrieved:
                prompt += f"\n# 失败候选: {r['candidate']}"
                prompt += f"\n# 错误: {r['stderr']}"

        if node.evaluation_result:
            failed_level = node.evaluation_result["overall"]["failed_at"]
            if failed_level:
                level_msg = node.evaluation_result[failed_level]["message"]
                prompt += f"在{failed_level}失败: {level_msg}\n\n"
        
        prompt += "请修复代码使其通过测试。只返回修复后的Python代码。"
        return prompt

    def _backpropagate(self, node: Node, reward: float):
        cur = node
        while cur:
            cur.visits += 1
            cur.wins += reward
            cur = cur.parent

    def _print_progress(self, current_iter: int):
        best_child = self._get_best_child()
        best_rate = (best_child.wins / best_child.visits) if best_child and best_child.visits > 0 else 0
        total_nodes = len(self.root.children) if self.root.children else 0
        
        logger.info("mcts_progress", current_iter=current_iter + 1, total_simulations=self.n_simulations, best_pass_rate=round(best_rate, 2), total_branches=total_nodes)

    def _print_final_stats(self):
        # 1. 先计算比率 (防止除以0报错)
        if self.stats['syntax_checks'] > 0:
            reject_rate = self.stats['early_rejects'] / self.stats['syntax_checks']
        else:
            reject_rate = 0.0

        # 2. 打印日志
        logger.info(
            "mcts_statistics",
            llm_calls=self.stats['llm_calls'],
            syntax_checks=self.stats['syntax_checks'],
            static_analyses=self.stats['static_analyses'],
            runtime_tests=self.stats['runtime_tests'],
            early_rejects=self.stats['early_rejects'],
            early_reject_rate=round(reject_rate, 4) # 保留4位小数
        )