"""
长驻代码执行容器管理
针对M1 Mac优化的Docker执行环境
"""

import docker
import tarfile
import io
import time
import os
from typing import Tuple
from src.reason_code.utils.trace import trace_span
from opentelemetry import context
from src.reason_code.utils.config import SANDBOX_IMAGE, SANDBOX_TIMEOUT, SANDBOX_MEM_LIMIT, SANDBOX_CPU_QUOTA
import structlog
# 引入 Logger
from src.reason_code.utils.logger import logger as global_logger
logger = structlog.get_logger(__name__)


@trace_span(span_name="sandbox_execute")
class PersistentSandbox:
    """
    长驻Docker容器管理类
    针对M1芯片和Docker Desktop优化
    """
    
    def __init__(self, image: str = SANDBOX_IMAGE, timeout: int = SANDBOX_TIMEOUT):
        self.client = docker.from_env()
        self.image = image
        self.timeout = timeout
        self.container = None
        self._initialize_container()
    
    def _initialize_container(self) -> None:
        """初始化并启动长驻容器"""
        try:
            # M1芯片使用arm64架构，但python镜像支持多架构
            self.container = self.client.containers.run(
                self.image,
                command="tail -f /dev/null",  # 保持容器运行
                detach=True,
                mem_limit=SANDBOX_MEM_LIMIT,
                cpu_quota=SANDBOX_CPU_QUOTA,
                network_disabled=True,
                working_dir="/workspace",
                tty=True 
            )
            time.sleep(3)
            # 记录容器启动成功
            logger.info("sandbox_container_started", container_id=self.container.id[:12])
            
        except Exception as e:
            # 🔧 修正：使用 logger.error
            logger.error("sandbox_init_failed", error=str(e))
            self.container = None

    @trace_span(span_name="sandbox_execute")
    def execute_code(self, code: str, test_runner: str) -> Tuple[int, str, str]:
        # 获取当前的上下文 (Token)
        ctx = context.get_current()
        
        # 定义一个内部函数，专门用来在线程池里跑
        def _run_in_thread():
            # 强行把上下文"附身"到这个线程里
            token = context.attach(ctx)
            try:
                # 这里放原来的 Docker 逻辑
                if not self.container:
                    self._initialize_container()
                    if not self.container:
                        return -1, "", "容器未就绪"
                
                full_code = f"{code}\n\nif __name__ == '__main__':\n{test_runner}"
                self._upload_to_container("/workspace/test_code.py", full_code)
                result = self.container.exec_run("python /workspace/test_code.py", stdout=True, stderr=True)
                output = result.output.decode("utf-8", errors="ignore")
                return result.exit_code, output, ""
            finally:
                context.detach(token)

        
        return _run_in_thread()
    
    def _upload_to_container(self, container_path: str, content: str) -> None:
        """通过tar格式上传文件到容器 - M1兼容版本"""
        try:
            tar_buffer = io.BytesIO()
            with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
                data = content.encode("utf-8")
                file_info = tarfile.TarInfo(name="test_code.py")
                file_info.size = len(data)
                tar.addfile(file_info, io.BytesIO(data))
            
            tar_buffer.seek(0)
            self.container.put_archive("/workspace", tar_buffer)
                
        except Exception as e:
            # 🔧 修正：记录上传失败
            logger.error("sandbox_upload_failed", error=str(e))
    
    def cleanup(self) -> None:
        """清理容器资源"""
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
                logger.info("sandbox_cleaned_up")
            except Exception as e:
                # 🔧 修正
                logger.error("sandbox_cleanup_failed", error=str(e))

# --- 全局单例 ---
_global_sandbox = PersistentSandbox()

def execute_code(code: str, test_runner: str) -> Tuple[int, str, str]:
    return _global_sandbox.execute_code(code, test_runner)

import atexit
atexit.register(_global_sandbox.cleanup)