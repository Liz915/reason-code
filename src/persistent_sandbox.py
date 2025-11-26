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


class PersistentSandbox:
    """
    长驻Docker容器管理类
    针对M1芯片和Docker Desktop优化
    """
    
    def __init__(self, image: str = "python:3.10-slim", timeout: int = 10):
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
                mem_limit="256m",
                network_disabled=True,
                # 移除platform参数，让Docker自动选择合适架构
                working_dir="/workspace",
                tty=True  # 分配伪终端，提高兼容性
            )
            
            # 等待容器稳定
            time.sleep(3)
            print(f"长驻容器已启动: {self.container.id[:12]}")
            
            # 测试容器基本功能
            self._test_container()
            
        except Exception as e:
            print(f"容器初始化失败: {e}")
            self.container = None
    
    def _test_container(self) -> None:
        """测试容器基本功能"""
        try:
            # 检查Python版本
            result = self.container.exec_run("python --version")
            print(f"容器Python版本: {result.output.decode().strip()}")
            
            # 检查工作目录
            result = self.container.exec_run("pwd")
            print(f"容器工作目录: {result.output.decode().strip()}")
            
        except Exception as e:
            print(f"容器测试失败: {e}")
    
    def execute_code(self, code: str, test_runner: str) -> Tuple[int, str, str]:
        """
        在容器中执行代码并返回结果
        """
        if not self.container:
            return -1, "", "容器未就绪"
        
        try:
            # 组合代码和测试逻辑
            full_code = f"{code}\n\nif __name__ == '__main__':\n{test_runner}"
            
            # 上传代码到容器
            self._upload_to_container("/workspace/test_code.py", full_code)
            
            # 执行测试 - 移除timeout参数，使用外部超时控制
            result = self.container.exec_run(
                "python /workspace/test_code.py",
                stdout=True,
                stderr=True
            )
            
            output = result.output.decode("utf-8", errors="ignore")
            return result.exit_code, output, ""
            
        except Exception as e:
            return -1, "", f"执行异常: {str(e)}"
    
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
            
            # 直接上传到workspace目录
            success = self.container.put_archive("/workspace", tar_buffer)
            if not success:
                print("文件上传失败")
                
        except Exception as e:
            print(f"文件上传异常: {e}")
    
    def cleanup(self) -> None:
        """清理容器资源"""
        if self.container:
            try:
                self.container.stop()
                self.container.remove()
                print("长驻容器已清理")
            except Exception as e:
                print(f"容器清理失败: {e}")


def test_m1_compatibility():
    """测试M1兼容性"""
    print("测试M1 Mac Docker兼容性...")
    
    sandbox = PersistentSandbox()
    
    if sandbox.container:
        # 简单测试
        test_code = "def add(a, b): return a + b"
        test_runner = "    print('结果:', add(2, 3))"
        
        exit_code, output, error = sandbox.execute_code(test_code, test_runner)
        print(f"测试执行结果: 退出码={exit_code}, 输出={output.strip()}, 错误={error}")
        
        sandbox.cleanup()
    else:
        print("容器启动失败，请检查Docker Desktop是否运行")


if __name__ == "__main__":
    test_m1_compatibility()