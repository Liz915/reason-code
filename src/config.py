
"""
配置文件
"""

import os
from dotenv import load_dotenv

load_dotenv()

# LLM配置
LLM_API_KEY = os.getenv("LLM_API_KEY")
# 如果没有key也让它过，因为我们现在主要用本地模型
LLM_API_BASE = os.getenv("LLM_API_BASE", "https://api.deepseek.com/v1")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-coder")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", "30"))
LLM_DEBUG = os.getenv("LLM_DEBUG", "False").lower() == "true"

# MCTS配置
MCTS_C = float(os.getenv("MCTS_C", "1.4"))

# 沙箱配置
SANDBOX_IMAGE = os.getenv("SANDBOX_IMAGE", "python:3.10-slim")
SANDBOX_TIMEOUT = int(os.getenv("SANDBOX_TIMEOUT", "10"))
SANDBOX_MEM_LIMIT = os.getenv("SANDBOX_MEM_LIMIT", "256m")

# Docker CPU配额，默认100000 (100% CPU)
SANDBOX_CPU_QUOTA = int(os.getenv("SANDBOX_CPU_QUOTA", "100000"))