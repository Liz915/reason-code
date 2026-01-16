"""
parameters is a lightweight signature description for LLM prompting,
NOT a strict JSON schema.
"""

import inspect
from typing import Callable, Dict, Any, List

class ToolRegistry:
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
        self._schemas: List[Dict[str, Any]] = []

    def register(self, func: Callable):
        """
        装饰器：注册一个工具函数
        使用方法: @registry.register
        """
        tool_name = func.__name__
        doc = func.__doc__ or "No description provided."
        
        # 获取参数签名，生成 Schema 给 LLM 看
        sig = inspect.signature(func)
        params = {
            k: str(v.annotation) 
            for k, v in sig.parameters.items()
        }

        tool_schema = {
            "name": tool_name,
            "description": doc.strip(),
            "parameters": str(params)
        }

        self._tools[tool_name] = func
        self._schemas.append(tool_schema)
        # print(f"🔧 Tool Registered: {tool_name}")
        return func

    def get_tool(self, name: str) -> Callable:
        return self._tools.get(name)

    def get_schemas(self) -> str:
        """返回给 LLM 看的工具说明书"""
        import json
        return json.dumps(self._schemas, indent=2, ensure_ascii=False)

    def execute(self, tool_name: str, **kwargs) -> Any:
        tool = self.get_tool(tool_name)
        if not tool:
            raise ValueError(f"Tool {tool_name} not found")
        try:
            return tool(**kwargs)
        except Exception as e:
            return f"Error executing {tool_name}: {e}"

# 全局单例
registry = ToolRegistry()