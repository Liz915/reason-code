import docker
import tarfile
import io
import structlog
import sys # 确保导入 sys

logger = structlog.get_logger(__name__)

class Sandbox:
    def __init__(self):
        try:
            self.client = docker.from_env()
            self.image = "python:3.10-slim"
            self.container = None
        except Exception as e:
            # 兼容本地可能没有 docker 运行的情况，防止初始化直接崩
            logger.error("docker_init_failed", error=str(e))
            self.client = None

    def start(self):
        if not self.client:
            raise RuntimeError("Docker client not initialized. Is Docker Desktop running?")
            
        try:
            # 确保容器一直运行
            self.container = self.client.containers.run(
                self.image,
                command="tail -f /dev/null",
                detach=True,
                mem_limit="512m",
                nano_cpus=1000000000
            )
            logger.info("sandbox_container_started", container_id=self.container.short_id)
        except Exception as e:
            logger.error("sandbox_start_failed", error=str(e))
            raise e

    def stop(self):
        if self.container:
            try:
                self.container.remove(force=True)
                logger.info("sandbox_cleaned_up")
                self.container = None
            except Exception:
                pass

    def execute(self, code: str, timeout: int = 10) -> str:
        # 如果容器没启动，先启动
        if not self.container:
            self.start()

        # 包装代码：捕获超时和错误
        # 注意：这里我们把 timeout 参数注入到 signal.alarm 中
        wrapped_code = f"""
import signal
import sys

def handler(signum, frame):
    raise TimeoutError("Execution timed out")

signal.signal(signal.SIGALRM, handler)
signal.alarm({timeout})

try:
{'\n'.join(['    ' + line for line in code.splitlines()])}
except Exception as e:
    print(str(e), file=sys.stderr)
finally:
    signal.alarm(0)
"""
        
        try:
            # 1. 写入文件 (最稳妥的方式)
            self._write_file(self.container, "script.py", wrapped_code)
            
            # 2. 执行文件
            exec_result = self.container.exec_run("python script.py", demux=True)
            
            stdout = exec_result.output[0].decode() if exec_result.output[0] else ""
            stderr = exec_result.output[1].decode() if exec_result.output[1] else ""
            
            # ✅ 关键修改：如果 stderr 有内容，返回 Error；否则返回 stdout 内容供检查
            if stderr:
                return f"Error: {stderr.strip()}"
            return stdout if stdout else "No Output"

        except Exception as e:
            return f"System Error: {str(e)}"

    def _write_file(self, container, filename, content):
        tar_stream = io.BytesIO()
        with tarfile.open(fileobj=tar_stream, mode='w') as tar:
            data = content.encode('utf-8')
            tarinfo = tarfile.TarInfo(name=filename)
            tarinfo.size = len(data)
            tar.addfile(tarinfo, io.BytesIO(data))
        tar_stream.seek(0)
        container.put_archive(path="/", data=tar_stream)

# 全局单例
sandbox = Sandbox()

def execute_code(code: str, timeout: int = 10):
    # 这里默认给 10 秒，防止 CPU 满载时误杀
    return sandbox.execute(code, timeout)