import docker
import tarfile
import io
import time
from typing import Tuple
from config import SANDBOX_IMAGE, SANDBOX_TIMEOUT, SANDBOX_MEM_LIMIT, SANDBOX_CPU_QUOTA

class DockerSandbox:
    """修复版长驻容器"""
    
    def __init__(self):
        self.client = docker.from_env()
        self.container = None
        self._start_container()
    
    def _start_container(self):
        """启动容器并创建workspace目录"""
        try:
            self.container = self.client.containers.run(
                image=SANDBOX_IMAGE,
                command="tail -f /dev/null",
                detach=True,
                mem_limit=SANDBOX_MEM_LIMIT,
                cpu_quota=SANDBOX_CPU_QUOTA,
                network_disabled=True,
                tty=True
            )
            # 等待容器启动并创建目录
            time.sleep(2)
            
            # 确保workspace目录存在
            self.container.exec_run("mkdir -p /workspace")
            print(f"✅ 长驻容器启动: {self.container.id[:12]}")
            
        except Exception as e:
            print(f"❌ 容器启动失败: {e}")
            raise
    
    def execute_code(self, code: str, test_runner: str) -> Tuple[int, str, str]:
        """执行代码"""
        try:
            # 上传代码
            self._upload_code(code, test_runner)
            
            # 执行代码
            result = self.container.exec_run(
                "cd /workspace && python test_script.py",
                stderr=True,
                stdout=True,
                timeout=SANDBOX_TIMEOUT
            )
            
            exit_code = result.exit_code
            output = result.output.decode('utf-8', errors='ignore') if result.output else ""
            
            if exit_code == 0:
                return exit_code, output, ""
            else:
                return exit_code, "", output
                
        except Exception as e:
            return -1, "", f"Execution error: {str(e)}"
    
    def _upload_code(self, code: str, test_runner: str):
        """上传代码到容器"""
        full_code = f"{code}\n\nif __name__ == '__main__':\n{test_runner}"
        
        # 创建tar文件
        tar_buffer = io.BytesIO()
        with tarfile.open(fileobj=tar_buffer, mode='w') as tar:
            # 添加文件内容
            file_data = full_code.encode('utf-8')
            tarinfo = tarfile.TarInfo(name="test_script.py")
            tarinfo.size = len(file_data)
            tar.addfile(tarinfo, io.BytesIO(file_data))
        
        tar_buffer.seek(0)
        
        # 上传到workspace目录
        success = self.container.put_archive("/workspace", tar_buffer)
        if not success:
            raise Exception("文件上传失败")

# 回退到原来的临时容器版本（稳定）
def execute_code(code: str, test_runner: str) -> Tuple[int, str, str]:
    """使用稳定的临时容器版本"""
    import uuid
    import tempfile
    import os
    import shutil
    
    client = docker.from_env()
    workdir = tempfile.mkdtemp(prefix="reason_code_")
    script_path = os.path.join(workdir, "submission.py")
    
    with open(script_path, "w", encoding="utf-8") as f:
        f.write(f"{code}\n\nif __name__ == '__main__':\n{test_runner}\n")

    container_name = f"rc_sandbox_{uuid.uuid4().hex[:8]}"
    try:
        container = client.containers.run(
            image=SANDBOX_IMAGE,
            command=["python", "/work/submission.py"],
            name=container_name,
            volumes={workdir: {"bind": "/work", "mode": "ro"}},
            network_disabled=True,
            detach=True,
            stdout=True,
            stderr=True,
            mem_limit=SANDBOX_MEM_LIMIT,
            cpu_quota=SANDBOX_CPU_QUOTA,
        )

        start = time.time()
        while True:
            if time.time() - start > SANDBOX_TIMEOUT:
                try:
                    container.kill()
                except Exception:
                    pass
                exit_code = -1
                out = container.logs(stdout=True, stderr=False).decode(errors="ignore")
                err = container.logs(stdout=False, stderr=True).decode(errors="ignore")
                return exit_code, out, f"TIMEOUT\n{err}"
            
            container.reload()
            status = container.status
            if status in ("exited", "dead"):
                exit_code = container.wait().get("StatusCode", -1)
                out = container.logs(stdout=True, stderr=False).decode(errors="ignore")
                err = container.logs(stdout=False, stderr=True).decode(errors="ignore")
                return exit_code, out, err
            time.sleep(0.05)
    finally:
        try:
            for c in client.containers.list(all=True, filters={"name": container_name}):
                c.remove(force=True)
        except Exception:
            pass
        shutil.rmtree(workdir, ignore_errors=True)
