import sys
import os
import asyncio

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.reason_code.workflow.engine import WorkflowEngine
from src.reason_code.workflow.nodes_impl import ToolNode, ReasoningNode
from src.reason_code.tools.builtins import search_stub # 确保注册了工具

async def main():
    print("🚀 启动 Agent Workflow: Search -> Reason -> Code\n")

    # 1. 定义节点 (积木)
    node_search = ToolNode(node_id="google_search", tool_name="search_stub")
    node_reason = ReasoningNode(node_id="coding_brain")

    # 2. 定义流程 (DAG)
    # 逻辑：先用 Google 搜索，再把搜索结果给 MCTS 写代码
    edges = [
        ["google_search", "coding_brain"]
    ]

    # 3. 初始化引擎
    engine = WorkflowEngine([node_search, node_reason], edges)

    # 4. 运行任务
    user_task = {
        "user_input": "用 Python 写一个快排",
        "test_runner": "assert sort([3,1,2]) == [1,2,3]" # 模拟测试用例
    }
    
    result = await engine.run(user_task)
    
    print("\n✅ 工作流执行完毕!")
    print(f"🔧 工具输出: {result.get('tool_result')}")
    print(f"💻 最终代码:\n{result.get('final_code')}")

if __name__ == "__main__":
    asyncio.run(main())