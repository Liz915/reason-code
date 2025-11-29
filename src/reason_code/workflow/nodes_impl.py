from src.reason_code.workflow.node import BaseNode
from src.reason_code.tools.registry import registry
from src.reason_code.agent.mcts import EnhancedMCTS
import structlog

logger = structlog.get_logger(__name__)

# 1. 工具调用节点 (Tool Node)
class ToolNode(BaseNode):
    def __init__(self, node_id: str, tool_name: str):
        super().__init__(node_id, "tool")
        self.tool_name = tool_name

    async def execute(self, inputs: dict, context: dict) -> dict:
        arg_value = inputs.get("user_input") or inputs.get("query")
        
        logger.info("executing_tool", tool=self.tool_name, arg=arg_value)
        
        # 智能参数匹配
        # 如果是搜索工具，只传 query
        if "search" in self.tool_name:
            result = registry.execute(self.tool_name, query=arg_value)
        # 如果是计算工具，只传 expression
        elif "calculator" in self.tool_name:
            result = registry.execute(self.tool_name, expression=arg_value)
        else:
            # 默认尝试传 query，你可以根据需要扩展
            result = registry.execute(self.tool_name, query=arg_value)
        
        return {"tool_result": result}
    
# 2. 推理节点 (MCTS Node)
class ReasoningNode(BaseNode):
    def __init__(self, node_id: str):
        super().__init__(node_id, "mcts_reasoning")

    async def execute(self, inputs: dict, context: dict) -> dict:
        prompt = inputs.get("user_input")
        # 获取之前工具运行的结果 (如果有)
        tool_context = context.get("tool_result", "")
        
        if tool_context:
            # RAG 模式：把工具结果拼接到 Prompt 里
            full_prompt = f"参考信息: {tool_context}\n\n任务: {prompt}"
        else:
            full_prompt = prompt
            
        logger.info("mcts_planning", prompt_len=len(full_prompt))
        
        # 调用核心算法
        # 这里的 test_runner 暂时写死或从 inputs 获取
        test_runner = inputs.get("test_runner", "")
        mcts = EnhancedMCTS(root_code=full_prompt, n_simulations=3, n_candidates=1)
        best_code = await mcts.run(test_runner)
        
        return {"final_code": best_code}