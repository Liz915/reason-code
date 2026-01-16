from src.reason_code.tools.registry import registry
import math

@registry.register
def calculator(expression: str) -> str:
    """
    A safe calculator. Input a math expression string.
    Example: calculator("2 + 2")
    """
    try:
        # Restrict eval scope to math namespace only (no builtins, no IO)
        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        # Compile and execute the expression
        return str(eval(expression, {"__builtins__": {}}, allowed_names))
    except Exception as e:
        return f"Calculation Error: {e}"

@registry.register
def search_stub(query: str) -> str:
    """
    Mock search tool for demo / workflow testing only.
    Not used in main experiments.
    """
    return f"[Mock Search Result] Found relevant info for '{query}': Python 3.13 introduces JIT compiler..."