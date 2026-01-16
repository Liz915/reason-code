import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch

def draw_system_overview():
    fig, ax = plt.subplots(figsize=(12, 5))
    ax.axis('off')
    
    # 定义样式
    box_props = dict(boxstyle='round,pad=0.5', facecolor='white', edgecolor='black', linewidth=1.5)
    
    # 1. Input
    ax.text(0.1, 0.5, "Problem\nInput", ha='center', va='center', bbox=box_props, fontsize=12)
    
    # 2. Greedy Baseline
    ax.text(0.3, 0.5, "Greedy\nDecoding\n(N=1)", ha='center', va='center', bbox=box_props, fontsize=12)
    
    # 3. Conditional Gate
    ax.text(0.5, 0.5, "Pass\nTests?", ha='center', va='center', bbox=dict(boxstyle='darrow,pad=0.3', facecolor='#e6f3ff', edgecolor='black'), fontsize=10)
    
    # 4. Success Output (Up)
    ax.text(0.5, 0.8, "Output\nSolution", ha='center', va='center', bbox=dict(boxstyle='round', facecolor='#d9ead3', edgecolor='black'), fontsize=12)
    
    # 5. MCTS Loop (Right)
    # Box for MCTS
    rect = Rectangle((0.6, 0.2), 0.35, 0.6, linewidth=1, edgecolor='gray', facecolor='#f9f9f9', linestyle='--')
    ax.add_patch(rect)
    ax.text(0.775, 0.75, "MCTS Search Loop", ha='center', fontsize=10, fontweight='bold', color='gray')
    
    ax.text(0.775, 0.6, "Selection (UCB1)\nExpansion (T=0.5)", ha='center', va='center', bbox=box_props, fontsize=10)
    ax.text(0.775, 0.3, "Sandbox Exec.\n(Binary Reward)", ha='center', va='center', bbox=box_props, fontsize=10)
    
    # Arrows
    # Input -> Greedy
    ax.annotate("", xy=(0.22, 0.5), xytext=(0.16, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5))
    # Greedy -> Gate
    ax.annotate("", xy=(0.44, 0.5), xytext=(0.38, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5))
    # Gate -> Output (Yes)
    ax.annotate("Yes", xy=(0.5, 0.72), xytext=(0.5, 0.58), arrowprops=dict(arrowstyle="->", lw=1.5), ha='center')
    # Gate -> MCTS (No)
    ax.annotate("No", xy=(0.6, 0.5), xytext=(0.56, 0.5), arrowprops=dict(arrowstyle="->", lw=1.5, color='red'))
    
    # MCTS Loop Arrows
    ax.annotate("", xy=(0.775, 0.45), xytext=(0.775, 0.53), arrowprops=dict(arrowstyle="->", lw=1.5))
    ax.annotate("Reflexion", xy=(0.9, 0.53), xytext=(0.9, 0.36), arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=0.5", lw=1.5, linestyle="--"), ha='center')
    
    # MCTS -> Output
    ax.annotate("Success", xy=(0.56, 0.8), xytext=(0.7, 0.8), arrowprops=dict(arrowstyle="->", lw=1.5), ha='center')

    plt.tight_layout()
    plt.savefig("fig1_system.pdf")
    print("Figure 1 saved.")

draw_system_overview()