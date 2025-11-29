import requests
import json
import time

# 这是我们要发给 Agent 的题目
# 故意写错一个代码 (return a - b)，看它能不能修好
payload = {
    "prompt": "def add(a, b):\n    return a - b",
    "test_runner": "assert add(1, 2) == 3\nassert add(10, 20) == 30"
}

print("🚀 发送请求给 Reason-Code Agent...")
start_time = time.time()

try:
    response = requests.post("http://127.0.0.1:8000/reason_and_code", json=payload)
    print(f"✅ 请求完成! 耗时: {time.time() - start_time:.2f}s")
    
    result = response.json()
    print("\n--- 结果 ---")
    print(json.dumps(result, indent=2, ensure_ascii=False))
    
except Exception as e:
    print(f"❌ 请求失败: {e}")