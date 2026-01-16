import asyncio
from typing import List, Dict, Any
from src.reason_code.workflow.node import BaseNode
from src.reason_code.utils.logger import logger

class WorkflowEngine:
    def __init__(self, nodes: List[BaseNode], edges: List[List[str]]):
        self.nodes = {n.node_id: n for n in nodes}
        self.edges = edges
        self.context = {} # 全局记忆

    async def run(self, initial_input: Dict[str, Any]):
        """
        极简版 DAG 执行：目前只支持线性执行 (A -> B -> C)
        """
        logger.info("workflow_start", nodes_count=len(self.nodes))
        
        current_data = initial_input
        
        # 这里做一个简单的线性假设：按照 edges 定义的顺序执行
        # 实际生产环境需要解析图结构
        sorted_node_ids = self._sort_nodes()
        
        for node_id in sorted_node_ids:
            node = self.nodes[node_id]
            logger.info("node_start", node_id=node_id, type=node.node_type)
            
            try:
                # 执行节点逻辑
                output = await node.execute(current_data, self.context)
                
                # 更新数据流
                current_data.update(output)
                # 更新全局上下文
                self.context.update(output)
                
            except Exception as e:
                logger.error("node_failed", node_id=node_id, error=str(e))
                break
                
        logger.info("workflow_end")
        return current_data

    def _sort_nodes(self):
        """简单解析：直接按 Edge 顺序提取 (简化版)"""
        # 假设 edges = [["start", "search"], ["search", "mcts"]]
        # 提取出: start -> search -> mcts
        ordered = []
        if not self.edges: return []
        
        # 找到起点
        current = self.edges[0][0]
        ordered.append(current)
        
        for edge in self.edges:
            if edge[0] == current:
                current = edge[1]
                ordered.append(current)
        
        return ordered