import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import asyncio
from fastapi import FastAPI
from pydantic import BaseModel
from mcts import EnhancedMCTS  # 改为EnhancedMCTS

app = FastAPI()

class TaskRequest(BaseModel):
    prompt: str
    test_runner: str

@app.post("/reason_and_code")
async def reason_and_code(req: TaskRequest):
    """接受编程任务，使用MCTS搜索最佳代码"""
    print(f"🔍 收到任务: {req.prompt[:50]}...")
    
    # 使用增强版MCTS
    mcts = EnhancedMCTS(root_code=req.prompt, n_simulations=15, n_candidates=3)
    best_code = await mcts.run(req.test_runner)
    
    return {
        "best_code": best_code,
        "status": "success", 
        "message": "MCTS搜索完成",
        "search_stats": {
            "simulations": 15,
            "candidates_per_step": 3
        }
    }

@app.get("/")
async def root():
    return {"message": "Reason-Code Enhanced MCTS Coding Agent is running!"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("servers:app", host="127.0.0.1", port=8000, reload=False)
