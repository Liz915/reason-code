import sys
import os


# 获取当前文件 (app.py) 的目录
current_dir = os.path.dirname(os.path.abspath(__file__))
# 向上找 3 层，定位到项目根目录 (即 reason-code 文件夹)
# 结构: reason-code/src/reason_code/api/app.py
project_root = os.path.dirname(os.path.dirname(os.path.dirname(current_dir)))

# 把项目根目录加入到 Python 的搜索路径中
if project_root not in sys.path:
    sys.path.insert(0, project_root)

import asyncio
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import uvicorn

# 现在 Python 知道根目录了，我们可以从 src. 开始导入
from src.reason_code.agent.mcts import EnhancedMCTS
# 引入 Logger
from src.reason_code.utils.logger import logger

# --- 引入 Phoenix 监控 (让 Trace 生效) ---
import phoenix as px
from openinference.instrumentation.openai import OpenAIInstrumentor
from opentelemetry import trace as trace_api
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

app = FastAPI()

# --- 初始化 Phoenix 监控 ---
def setup_phoenix():
    try:
        # 配置 OpenTelemetry 发送数据给本地的 Phoenix
        endpoint = os.getenv("PHOENIX_COLLECTOR_ENDPOINT", "http://127.0.0.1:6006/v1/traces")
        tracer_provider = TracerProvider()
        tracer_provider.add_span_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
        trace_api.set_tracer_provider(tracer_provider)
        
        # 自动抓取 LLM 调用
        OpenAIInstrumentor().instrument()
        logger.info("phoenix_instrumentation_enabled", endpoint=endpoint)
    except Exception as e:
        logger.warning("phoenix_setup_failed", error=str(e))

setup_phoenix()

class TaskRequest(BaseModel):
    prompt: str
    test_runner: str

# 模拟数据库
TASKS = {}

async def run_mcts_task(task_id: str, prompt: str, runner: str):
    """后台运行 MCTS 的工作函数"""
    logger.info("task_started", task_id=task_id)
    TASKS[task_id] = {"status": "running"}
    try:
        # 实例化 MCTS
        mcts = EnhancedMCTS(root_code=prompt, n_simulations=1, n_candidates=1)
        # 运行搜索
        best_code = await mcts.run(runner)
        
        TASKS[task_id] = {
            "status": "completed", 
            "result": best_code,
            "message": "Optimization success"
        }
        logger.info("task_completed", task_id=task_id)
    except Exception as e:
        logger.error("task_failed", task_id=task_id, error=str(e))
        TASKS[task_id] = {"status": "failed", "error": str(e)}

@app.post("/reason_and_code")
async def reason_and_code(req: TaskRequest, background_tasks: BackgroundTasks):
    """
    接受编程任务，异步执行 MCTS
    """
    import uuid
    task_id = str(uuid.uuid4())
    
    # 放入后台任务队列 (Async + Queue 模式)
    background_tasks.add_task(run_mcts_task, task_id, req.prompt, req.test_runner)
    
    logger.info("request_received", task_id=task_id, prompt_preview=req.prompt[:50])
    
    return {
        "task_id": task_id,
        "status": "queued", 
        "message": "Task submitted to background worker"
    }

@app.get("/task/{task_id}")
async def get_result(task_id: str):
    """查询任务结果"""
    task = TASKS.get(task_id)
    if not task:
        return {"status": "not_found"}
    return task

@app.get("/")
async def root():
    return {"message": "Reason-Code Enhanced MCTS Coding Agent is running!"}

if __name__ == "__main__":
    # 启动服务器，端口 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)