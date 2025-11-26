"""
DeepSeek + 优化 MCTS 性能对比测试
展示候选生成和搜索时间
"""

import time
import asyncio
import sys
import os
from typing import Dict, Any
import traceback

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from llm import generate_code_candidates
from mcts_optimized import OptimizedMCTS

# 测试用例
test_cases = [
    (
        "加法修复",
        "def add(a, b): return a - b",  # 故意错误
        """
import sys
from submission import add

if add(2, 3) != 5:
    sys.exit(1)
sys.exit(0)
"""
    ),
    (
        "乘法修复", 
        "def multiply(a, b): return a",  # 故意错误
        """
import sys
from submission import multiply

if multiply(3, 4) != 12:
    sys.exit(1)
sys.exit(0)
"""
    ),
]


async def run_performance_test():
    print("=" * 60)
    print("DeepSeek + 优化 MCTS 性能对比测试")
    print("=" * 60)

    results = []
    
    for name, code, test_runner in test_cases:
        print(f"\n🔍 测试用例: {name}")
        print(f"初始代码: {code}")

        case_result = {
            'name': name,
            'initial_code': code,
            'candidates': [],
            'gen_time': 0,
            'search_time': 0,
            'success': False,
            'best_score': 0.0
        }

        try:
            # 1️⃣ 候选生成
            print("🚀 生成候选代码...")
            start_time = time.time()
            candidates = await generate_code_candidates(code, n=3)
            gen_time = time.time() - start_time

            case_result['gen_time'] = gen_time
            case_result['candidates'] = candidates

            print(f"✅ 生成候选数: {len(candidates)}")
            for i, c in enumerate(candidates, 1):
                print(f"候选 {i}:\n{c}\n{'-'*30}")
            print(f"⏱️ 候选生成时间: {gen_time:.3f} 秒")

            # 2️⃣ 优化 MCTS 搜索
            if candidates:
                print("🎯 开始MCTS搜索...")
                start_time = time.time()
                mcts = OptimizedMCTS(
                    root_code=candidates[0],  # 使用第一个候选作为起点
                    n_simulations=10,
                    n_candidates=min(3, len(candidates))
                )
                result = await mcts.run(test_runner)
                search_time = time.time() - start_time

                case_result['search_time'] = search_time
                
                # 修复：正确处理返回结果格式
                if isinstance(result, dict):
                    case_result['success'] = result.get('success', False)
                    case_result['best_score'] = result.get('best_score', 0.0)
                    case_result['best_code'] = result.get('best_code', '')
                    case_result['test_passed'] = result.get('test_passed', False)
                else:
                    # 如果返回的是其他类型，记录错误
                    print(f"⚠️ MCTS返回了非字典格式: {type(result)}")
                    case_result['success'] = False
                    case_result['error'] = f"MCTS返回了非字典格式: {type(result)}"

                print(f"🎯 MCTS 搜索完成: {search_time:.3f} 秒")
                print(f"搜索结果 - 成功: {case_result['success']}, 得分: {case_result['best_score']:.2f}")
                if case_result.get('best_code'):
                    print(f"最佳代码: {case_result['best_code']}")
                print(f"📊 总耗时 (生成 + 搜索): {gen_time + search_time:.3f} 秒")
            else:
                print("❌ 没有生成有效的候选代码")
                case_result['error'] = "没有生成有效的候选代码"

        except Exception as e:
            print(f"❌ 测试用例 {name} 执行失败: {e}")
            traceback.print_exc()  # 打印详细错误堆栈
            case_result['error'] = str(e)

        results.append(case_result)

    # 生成总结报告
    _generate_summary_report(results)


def _generate_summary_report(results: list):
    """生成性能测试总结报告"""
    print("\n" + "=" * 60)
    print("📈 性能测试总结报告")
    print("=" * 60)
    
    total_gen_time = sum(r['gen_time'] for r in results)
    total_search_time = sum(r['search_time'] for r in results)
    success_count = sum(1 for r in results if r.get('success', False))
    total_candidates = sum(len(r.get('candidates', [])) for r in results)
    
    print(f"总测试用例数: {len(results)}")
    print(f"成功用例数: {success_count}")
    print(f"总生成候选数: {total_candidates}")
    print(f"总候选生成时间: {total_gen_time:.3f} 秒")
    print(f"总MCTS搜索时间: {total_search_time:.3f} 秒")
    print(f"总耗时: {total_gen_time + total_search_time:.3f} 秒")
    print(f"平均每个用例耗时: {(total_gen_time + total_search_time) / len(results):.3f} 秒")
    
    if success_count > 0:
        success_rate = success_count / len(results) * 100
        print(f"🎉 成功率: {success_rate:.1f}%")
        
        # 计算平均得分
        avg_score = sum(r.get('best_score', 0) for r in results) / len(results)
        print(f"📊 平均得分: {avg_score:.2f}")
    else:
        print("⚠️ 所有测试用例均失败")
        
        # 显示具体错误
        print("\n🔍 错误分析:")
        for i, result in enumerate(results):
            if result.get('error'):
                print(f"  用例 {i+1} ({result['name']}): {result['error']}")


if __name__ == "__main__":
    asyncio.run(run_performance_test())