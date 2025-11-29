from src.reason_code.tools.registry import registry
import math

@registry.register
def calculator(expression: str) -> str:
    """
    A safe calculator. Input a math expression string.
    Example: calculator("2 + 2")
    """
    try:
        # 限制只能访问 math 库，防止 rm -rf /
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        # 编译并执行表达式
        return str(eval(expression, {"__builtins__": {}}, allowed_names))
    except Exception as e:
        return f"Calculation Error: {e}"

@registry.register
def search_stub(query: str) -> str:
    """
    Simulates a web search engine. Returns mock search results.
    """
    return f"[Mock Search Result] Found relevant info for '{query}': Python 3.13 introduces JIT compiler..."