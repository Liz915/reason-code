import sys
import structlog
import logging

def setup_logger():
    """
    配置结构化日志系统。
    """
    # 1. 配置标准 logging (Python 自带的底层日志)
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=logging.INFO,
    )

    # 2. 配置 structlog (让日志变成 JSON 格式，或者漂亮的彩色文本)
    structlog.configure(
        processors=[
            structlog.stdlib.filter_by_level,  # 过滤掉等级太低的日志
            structlog.stdlib.add_logger_name,  # 加上模块名
            structlog.stdlib.add_log_level,    # 加上日志等级 (INFO/ERROR)
            structlog.stdlib.PositionalArgumentsFormatter(),
            structlog.processors.TimeStamper(fmt="iso"), # 加上精确时间戳
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info, # 如果报错，显示详细堆栈
            # 下面这一行决定了输出格式：
            # 如果是开发环境，用 ConsoleRenderer (彩色好看)
            # 如果是生产环境，通常用 JSONRenderer (方便机器分析)
            structlog.dev.ConsoleRenderer()  
        ],
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # 返回一个配置好的 logger 实例
    return structlog.get_logger()

# 创建一个全局 logger 供其他文件使用
logger = setup_logger()