import functools
from opentelemetry import trace
from src.reason_code.utils.logger import logger

# 获取全局 tracer
tracer = trace.get_tracer("reason_code")

def trace_span(span_name: str = None, **kwargs):
    """
    自定义的 Trace 装饰器。
    用法: @trace_span(span_name="my_function")
    """
    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **func_kwargs):
            name = span_name or func.__name__
            with tracer.start_as_current_span(name) as span:
                try:
                    # 记录输入参数
                    span.set_attribute("code.function", func.__name__)
                    return await func(*args, **func_kwargs)
                except Exception as e:
                    span.record_exception(e)
                    # 重新抛出异常，不要吞掉
                    raise e
                    
        @functools.wraps(func)
        def sync_wrapper(*args, **func_kwargs):
            name = span_name or func.__name__
            with tracer.start_as_current_span(name) as span:
                try:
                    span.set_attribute("code.function", func.__name__)
                    return func(*args, **func_kwargs)
                except Exception as e:
                    span.record_exception(e)
                    raise e

        # 简单的判断是异步还是同步函数
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper
    return decorator

import asyncio