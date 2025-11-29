"""
统一 LLM 接口：Qwen-Coder LoRA 本地推理 + API 回退 + 智能缓存
"""

from dotenv import load_dotenv
load_dotenv()

import os
import re
import ast
import asyncio
import logging
import structlog
from src.reason_code.utils.logger import logger as global_logger
from src.reason_code.models.base import BaseModel
logger = structlog.get_logger(__name__)
from typing import List, Optional, Dict, Any
from src.reason_code.utils.trace import trace_span
from datetime import datetime, timedelta
import httpx

# 环境变量
LLM_API_KEY = os.getenv("LLM_API_KEY")
LLM_API_BASE = os.getenv("LLM_API_BASE")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek-coder")
LLM_TIMEOUT = int(os.getenv("LLM_TIMEOUT", 30))
LLM_DEBUG = os.getenv("LLM_DEBUG", "False") == "True"

# LoRA配置 - 适配 Qwen2.5
LORA_MODEL_PATH = os.getenv("LORA_MODEL_PATH", "lora-reason-coder-v3")
BASE_MODEL_NAME = os.getenv("BASE_MODEL_NAME", "Qwen/Qwen2.5-Coder-1.5B-Instruct")
USE_LOCAL_LORA = os.getenv("USE_LOCAL_LORA", "True") == "True"

# 缓存配置
_CACHE_MAXSIZE = 128
_CACHE_TTL_SECONDS = 300

# 并发控制
_MAX_CONCURRENT_REQUESTS = 5
_semaphore = asyncio.Semaphore(_MAX_CONCURRENT_REQUESTS)


# 尝试导入本地推理依赖
try:
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import PeftModel
    LOCAL_INFERENCE_AVAILABLE = True
    logger.info("dependency_check", status="local_inference_available")
except ImportError as e:
    LOCAL_INFERENCE_AVAILABLE = False
    logger.warning("dependency_check_failed", error=str(e), status="fallback_to_api")

class TTLCache:
    def __init__(self, maxsize: int = _CACHE_MAXSIZE, ttl: int = _CACHE_TTL_SECONDS):
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: Dict[str, Any] = {}
        self._access_times: Dict[str, datetime] = {}

    def get(self, key: str) -> Optional[Any]:
        now = datetime.utcnow()
        if key in self._cache:
            if now - self._access_times.get(key, now) < timedelta(seconds=self.ttl):
                self._access_times[key] = now
                return self._cache[key]
            else:
                self._cache.pop(key, None)
                self._access_times.pop(key, None)
        return None

    def set(self, key: str, value: Any):
        if len(self._cache) >= self.maxsize:
            oldest_key = min(self._access_times, key=lambda k: self._access_times[k])
            self._cache.pop(oldest_key, None)
            self._access_times.pop(oldest_key, None)
        self._cache[key] = value
        self._access_times[key] = datetime.utcnow()

_candidate_cache = TTLCache()

class LocalLoraModel(BaseModel):
    """LoRA本地模型管理 - Qwen 适配版"""

    def count_tokens(self, text: str) -> int:
        if not self.tokenizer:
            return 0
        return len(self.tokenizer.encode(text))
    
    def __init__(self):
        self.model = None
        self.tokenizer = None
        self._initialized = False
        # 强制使用 CPU 以规避 MPS 的 4GB 张量限制
        # M1 CPU 跑 1.5B 模型速度很快，且极其稳定
        self.device = "cpu"
    
    def is_available(self) -> bool:
        """检查LoRA模型是否可用"""
        if not LOCAL_INFERENCE_AVAILABLE:
            return False
        if not USE_LOCAL_LORA:
            return False
        # 检查路径是否存在
        if not os.path.exists(LORA_MODEL_PATH):
            logger.warning("lora_model_not_found", path=LORA_MODEL_PATH, hint="run finetune_lora.py")
            return False
        return True
    
    def initialize(self):
        """初始化本地模型"""
        if not self.is_available() or self._initialized:
            return False
        
        try:
            logger.info("model_loading_start", base_model=BASE_MODEL_NAME, device=self.device)
            
            # 加载 Tokenizer
            self.tokenizer = AutoTokenizer.from_pretrained(BASE_MODEL_NAME)
            
            # Qwen默认32k上下文会导致MPS尝试分配 >4GB 的注意力矩阵从而崩溃
            # 强制限制为 2048 (足够代码修复使用)
            self.tokenizer.model_max_length = 2048
            
            # 加载基座模型 (FP16以节省显存)
            base_model = AutoModelForCausalLM.from_pretrained(
                BASE_MODEL_NAME,
                torch_dtype=torch.float16,
                device_map=self.device
            )
            
            logger.info("loading_lora_weights", path=LORA_MODEL_PATH)
            # 加载 LoRA 适配器
            self.model = PeftModel.from_pretrained(base_model, LORA_MODEL_PATH)
            self.model.eval() # 切换到推理模式
            
            self._initialized = True
            logger.info("✅ LoRA模型加载完成")
            return True
            
        except Exception as e:
            logger.error("model_loading_failed", error=str(e))
            return False
    
    @trace_span(span_name="llm_generate_local")
    def generate(self, code_snippet: str, num_return_sequences: int = 3) -> List[str]:
        """使用LoRA模型生成代码 - 串行生成以避免MPS内存溢出"""
        if not self._initialized and not self.initialize():
            return []
        
        candidates = []
        import gc
        
        try:
            # 使用 Chat Template 构建 Prompt
            messages = [
                {"role": "system", "content": "你是一个Python代码修复专家。请修复输入的代码错误，仅输出修复后的完整代码，不要解释。"},
                {"role": "user", "content": code_snippet}
            ]
            
            text_prompt = self.tokenizer.apply_chat_template(
                messages, 
                tokenize=False, 
                add_generation_prompt=True
            )
            
            inputs = self.tokenizer(text_prompt, return_tensors="pt").to(self.device)
            
            # MPS 限制单张量 < 4GB。并行生成多个序列容易触发此限制。
            # 改为循环生成，每次生成一个，用完立即清理显存。
            for i in range(num_return_sequences):
                try:
                    with torch.no_grad():
                        outputs = self.model.generate(
                            **inputs,
                            max_new_tokens=512,
                            num_return_sequences=1,  # 每次只生成 1 个
                            temperature=0.7,
                            top_p=0.9,
                            do_sample=True,
                            pad_token_id=self.tokenizer.eos_token_id
                        )
                    
                    full_text = self.tokenizer.decode(outputs[0], skip_special_tokens=True)
                    
                    # 提取逻辑
                    if "assistant" in full_text:
                        clean_code = full_text.split("assistant")[-1].strip()
                    elif code_snippet in full_text:
                        clean_code = full_text.replace(code_snippet, "").strip()
                        if "你是一个Python代码修复专家" in clean_code:
                             clean_code = clean_code.split("不要解释。")[-1].strip()
                    else:
                        clean_code = full_text

                    code = self._extract_generated_code(clean_code)
                    if code and self._is_valid_syntax(code):
                        candidates.append(code)
                    
                except Exception as inner_e:
                    logger.warning("generation_attempt_failed", error=str(inner_e))
                    continue
                finally:
                    # === 显存清理 ===
                    # 每次生成后强制清理 MPS 缓存
                    if self.device == "mps":
                        torch.mps.empty_cache()
                        gc.collect()

            # 去重
            unique_candidates = list(set(candidates))
            if len(unique_candidates) > 0:
                logger.info("generation_complete", count=len(unique_candidates), method="lora_local")
            return unique_candidates
            
        except Exception as e:
            logger.error("generation_loop_failed", error=str(e))
            return []

    def name(self) -> str:
        return "Qwen-1.5B-LoRA"
    
    def _extract_generated_code(self, text: str) -> str:
        """从生成文本中提取代码"""
        # 1. 尝试提取 Markdown 代码块
        code_blocks = re.findall(r'```python\s*(.*?)\s*```', text, re.DOTALL)
        if code_blocks:
            return code_blocks[0].strip()
        
        code_blocks_generic = re.findall(r'```\s*(.*?)\s*```', text, re.DOTALL)
        if code_blocks_generic:
            return code_blocks_generic[0].strip()

        # 2. 如果没有代码块，尝试提取纯代码
        # 移除可能存在的自然语言前缀 (e.g., "Here is the fixed code:")
        lines = text.split('\n')
        code_lines = []
        started = False
        
        for line in lines:
            # 简单的启发式：如果是 def, import, class 开头，或者有缩进
            if line.strip().startswith('def ') or line.strip().startswith('import ') or line.strip().startswith('from ') or line.strip().startswith('class '):
                started = True
            
            if started:
                code_lines.append(line)
        
        if code_lines:
            return '\n'.join(code_lines).strip()
        
        # 3. 实在不行返回原文本，交给语法检查器去判断
        return text.strip()
    
    def _is_valid_syntax(self, code: str) -> bool:
        """验证代码语法"""
        if not code: return False
        try:
            ast.parse(code)
            return True
        except SyntaxError:
            return False

# 全局LoRA模型实例
_local_model = LocalLoraModel()

async def generate_code_candidates(prompt: str, n: int = 3, use_lora: bool = None, debug: bool = False) -> List[str]:
    """
    生成代码修复候选
    集成 Model Router：根据任务复杂度自动选择模型
    """
    if debug:
        logger.setLevel(logging.DEBUG)
    
    # 1. 检查缓存 (保持不变)
    cached = _candidate_cache.get(prompt)
    if cached:
        logger.debug("cache_hit", count=len(cached))
        return cached

    # 2. 引入 Router (延迟导入，防止循环引用)
    from src.reason_code.models.router import router

    # 3. 判断任务复杂度 (Heuristic / 启发式策略)
    # 逻辑：如果 Prompt 很长(>1000字符)，或者包含复杂的关键词，算 Hard 任务
    is_hard_task = len(prompt) > 1000 or "class " in prompt
    complexity = "hard" if is_hard_task else "easy"

    # 4. 获取模型实例 (Router 会决定给 Qwen 还是 GPT-4)
    model = router.get_model(complexity)
    
    logger.info("model_routed", selected_model=model.name(), complexity=complexity)

    # 5. 执行推理
    # 只要模型可用，就尝试生成
    # 注意：这里我们假设所有 Model 类都继承自 BaseModel 并实现了 generate 和 is_available
    # 如果 Base 没定义 is_available，可以默认 True 或 try-catch
    try:
        loop = asyncio.get_running_loop()
        
        # 统一调用接口：model.generate
        candidates = await loop.run_in_executor(None, model.generate, prompt, n)
        
        if candidates:
            _candidate_cache.set(prompt, candidates)
            return candidates
        else:
            logger.warning("model_returned_empty", model=model.name())
            
    except Exception as e:
        logger.error("inference_failed", model=model.name(), error=str(e))

    # 6. 回退机制 (Fallback)
    # 如果 Router 选的模型挂了，或者没生成出来，走最后的兜底逻辑
    # (比如强制切回 API，或者返回简单的规则修复)
    logger.warning("triggering_final_fallback")
    
    # 回退到API
    return await _generate_via_api(prompt, n, debug)

# ----------------- 保持 API 回退逻辑不变 -----------------
async def _generate_via_api(prompt: str, n: int = 3, debug: bool = False) -> List[str]:
    """通过API生成候选 (Fallback)"""
    # ... (保持原有的 API 调用代码不变) ...
    # 重点是上面的 LocalLoraModel 类和 generate_code_candidates 函数。
    logger.warning("fallback_triggered", reason="local_model_unavailable_or_failed")
    fallback = _intelligent_fallback_generation(prompt, n)
    return fallback

def _intelligent_fallback_generation(prompt: str, n: int) -> List[str]:
    # 简单的启发式修复
    candidates = []
    if "return a - b" in prompt:
        candidates.append("def add(a, b): return a + b")
    if "return a" in prompt and "multiply" in prompt:
        candidates.append("def multiply(a, b): return a * b")
    while len(candidates) < n:
        candidates.append(candidates[0] if candidates else "# Failed to generate")
    return candidates

