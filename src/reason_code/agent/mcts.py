import math
import asyncio
from dataclasses import dataclass, field
from typing import List, Optional, Any
import structlog
from src.reason_code.utils.logger import logger as global_logger
from src.reason_code.models.llm import generate_code_candidates
from src.reason_code.executor.evaluator import evaluate_candidates_async, evaluate_code
from src.reason_code.agent.reflexion import attempt_fix

logger = structlog.get_logger(__name__)

@dataclass
class Node:
    code: str
    parent: Optional["Node"]
    visits: int = 0
    wins: float = 0.0
    children: List["Node"] = field(default_factory=list)
    evaluation_result: Any = None

    def ucb_score(self, c: float = 1.414):
        if self.visits == 0: return float("inf")
        # 简单的 UCB1 实现
        parent_visits = self.parent.visits if self.parent else 1
        return (self.wins / self.visits) + c * math.sqrt(math.log(parent_visits) / self.visits)

class EnhancedMCTS:
    def __init__(self, root_code: str, n_simulations: int = 3, n_candidates: int = 1):
        self.root = Node(code=root_code, parent=None)
        self.n_simulations = n_simulations
        self.n_candidates = n_candidates

    async def run(self, test_runner: str):
        # 日志记录开始
        root_preview = self.root.code[:50].replace("\n", "\\n") + "..."
        logger.info("mcts_start", n_simulations=self.n_simulations, root_code_preview=root_preview)
        
        for i in range(self.n_simulations):
            # 1. Selection
            node = self._select(self.root)
            
            # 2. Expansion & Simulation (Reflexion 解耦版)
            reward = await self._expand_and_simulate(node, test_runner)
            
            # 3. Backpropagation
            self._backpropagate(node, reward)
            
            # 如果在模拟中找到了满分答案，这轮 MCTS 其实已经成功了
            if reward == 1.0:
                logger.info("perfect_solution_found_in_simulation", iteration=i)
        
        # 最终选择：访问次数最多或胜率最高的子节点
        best = self._get_best_child()
        best_wins = best.wins if best else 0.0
        logger.info("mcts_complete", best_wins=best_wins)
        
        return best.code if best else self.root.code

    def _select(self, node: Node) -> Node:
        # 如果当前节点有孩子，应用 UCB 选择最优孩子
        # 如果没有孩子（叶节点），就直接返回该节点进行扩展
        while node.children:
            node = max(node.children, key=lambda n: n.ucb_score())
        return node

    def _get_best_child(self):
        if not self.root.children: return None
        # 鲁棒策略：优先选访问次数多的，其次选平均分高的
        return max(self.root.children, key=lambda n: (n.visits, n.wins/n.visits if n.visits>0 else 0))

    async def _expand_and_simulate(self, node: Node, test_runner: str) -> float:
        """
        核心改动：将 '原始生成' 和 'Reflexion修复' 拆分为独立的子节点扩展。
        """
        # 1. 确定模式：如果是根节点，用 mcts 模式生成；否则用 reflexion 模式
        is_root = (node is self.root)
        mode = "mcts" if is_root else "reflexion"
        
        prompt = self._build_prompt(node)
        
        # 2. 生成候选代码
        # 注意：llm.py 已经配置好 force_sample，这里只需传入 mode
        candidates = await generate_code_candidates(prompt, n=self.n_candidates, mode=mode)
        eval_results = await evaluate_candidates_async(candidates, test_runner)
        
        step_best_reward = 0.0
        
        # 3. 处理每个生成结果
        for cand, res in zip(candidates, eval_results):
            raw_reward = res["overall"]["reward"]
            step_best_reward = max(step_best_reward, raw_reward)
            
            # [Node A]: 原始生成的代码，必须作为一个独立节点加入树中
            child_node = Node(code=cand, parent=node, evaluation_result=res)
            child_node.visits = 1
            child_node.wins = raw_reward
            node.children.append(child_node)
            
            # [Reflexion Branch]: 只有当原始代码有错，且是运行时错误时，尝试生成修正节点
            # 这是一个“机会主义”扩展：如果修好了，就加一个更强的兄弟节点
            if not res["overall"]["passed"] and res["overall"]["failed_at"] == "level_3":
                error_msg = res["level_3"]["message"]
                error_preview = error_msg.split('\n')[-1][:50]
                
                logger.info("reflexion_attempt", error_preview=error_preview)
                
                # 尝试修复
                fixed_code = await attempt_fix(cand, error_msg, test_runner)
                
                # 只有当代码真的变了，才评估并添加新节点
                if fixed_code != cand:
                    fixed_res = evaluate_code(fixed_code, test_runner)
                    fixed_reward = fixed_res["overall"]["reward"]
                    
                    if fixed_res["overall"]["passed"]:
                        logger.info("reflexion_success")
                        fixed_reward = 1.0 # 满分奖励
                    
                    # [Node B]: 修复后的代码，作为 Node A 的兄弟（或者平行分支）加入
                    # 这样树结构中同时保留了“原始尝试”和“修正尝试”
                    reflexion_node = Node(code=fixed_code, parent=node, evaluation_result=fixed_res)
                    reflexion_node.visits = 1
                    reflexion_node.wins = fixed_reward
                    node.children.append(reflexion_node)
                    
                    # 更新本轮模拟的最佳奖励
                    step_best_reward = max(step_best_reward, fixed_reward)

        return step_best_reward

    def _build_prompt(self, node: Node) -> str:
        # 显式判断是否为根节点，逻辑更严谨
        if node is self.root:
            return f"{node.code}\n\n# Instruction\nImplement the function above. Return COMPLETE code."
        
        # 子节点扩展：基于错误信息构造 Prompt
        prompt = f"Current Code:\n```python\n{node.code}\n```\n\n"
        if node.evaluation_result:
            failed = node.evaluation_result["overall"]["failed_at"]
            msg = node.evaluation_result[failed]["message"]
            prompt += f"[Error]\n{msg}\n\n"
        prompt += "Fix the code to pass the tests. Return ONLY the fixed code."
        return prompt

    def _backpropagate(self, node: Node, reward: float):
        while node:
            node.visits += 1
            # 使用 max 更新策略（Best-of-N 风格）通常在代码生成中比平均值更有效
            # 但为了保持标准 MCTS 定义，这里用累加，Selection 时用平均值
            node.wins += reward
            node = node.parent