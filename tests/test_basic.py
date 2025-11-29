import pytest
from src.reason_code.agent.mcts import Node, EnhancedMCTS

def test_node_initialization():
    """测试节点初始化逻辑"""
    node = Node(code="print('hello')", parent=None)
    assert node.visits == 0
    assert node.wins == 0.0
    assert node.code == "print('hello')"

def test_ucb_calculation():
    """测试核心数学逻辑 UCB"""
    # 模拟一个访问过10次的父节点
    parent = Node(code="p", parent=None, visits=10)
    # 模拟一个赢了1次、访问2次的子节点
    child = Node(code="c", parent=parent, visits=2, wins=1.0)
    
    score = child.ucb_score(c=1.414)
    # 简单的数学断言
    assert score > 0.5
