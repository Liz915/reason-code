import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, FancyArrowPatch, BoxStyle

def draw_system_fixed():
    fig, ax = plt.subplots(figsize=(10, 4))
    ax.axis('off')
    ax.set_xlim(0, 10)
    ax.set_ylim(0, 5)
    
    # --- 定义样式 ---
    # 圆角矩形 (标准节点)
    node_style = dict(boxstyle='round,pad=0.6,rounding_size=0.2', facecolor='white', edgecolor='black', linewidth=1.2)
    # 修复点：使用 'darrow' 替代 'diamond'，看起来像流程图的判定框
    decision_style = dict(boxstyle='darrow,pad=0.3', facecolor='#f9f9f9', edgecolor='black', linewidth=1.2)
    
    # 虚线框 (MCTS Scope)
    mcts_scope = Rectangle((6.2, 0.5), 3.5, 3.5, linewidth=1, edgecolor='gray', facecolor='#f9f9f9', linestyle='--', zorder=0)
    ax.add_patch(mcts_scope)
    ax.text(7.95, 3.7, "MCTS Search (N=3)", ha='center', fontsize=9, fontweight='bold', color='#555555')

    # --- 绘制节点 (Nodes) ---
    # 1. Input
    ax.text(1.0, 2.5, "Problem\nInput", ha='center', va='center', bbox=node_style, fontsize=10)
    
    # 2. Greedy
    ax.text(3.0, 2.5, "Greedy\nGeneration\n(N=1)", ha='center', va='center', bbox=node_style, fontsize=10)
    
    # 3. Gate (Decision) -> 这里用了 decision_style
    ax.text(5.0, 2.5, "Pass\nTests?", ha='center', va='center', bbox=decision_style, fontsize=9)
    
    # 4. MCTS Logic
    ax.text(8.0, 2.5, "Selection (UCB)\n&\nExpansion", ha='center', va='center', bbox=node_style, fontsize=10)
    
    # 5. Output
    ax.text(5.0, 4.5, "Final Solution\n(Output)", ha='center', va='center', bbox=dict(boxstyle='round,pad=0.5', facecolor='#e0e0e0', edgecolor='black'), fontsize=10)

    # --- 绘制直角连线 (Manhattan Arrows) ---
    def draw_arrow(posA, posB, text=None, text_pos=None, color='black', style='->', connection='arc3'):
        # mutation_scale 控制箭头大小
        arrow = FancyArrowPatch(posA, posB, arrowstyle=style, color=color, 
                                connectionstyle=connection, linewidth=1.2, mutation_scale=15)
        ax.add_patch(arrow)
        if text:
            ax.text(text_pos[0], text_pos[1], text, ha='center', va='center', fontsize=9, 
                    bbox=dict(facecolor='white', edgecolor='none', pad=0))

    # Input -> Greedy (Straight)
    draw_arrow((1.6, 2.5), (2.2, 2.5))
    
    # Greedy -> Gate (Straight)
    draw_arrow((3.8, 2.5), (4.4, 2.5))
    
    # Gate -> Output (YES: Straight Up)
    draw_arrow((5.0, 3.1), (5.0, 4.1))
    ax.text(5.2, 3.6, "Yes", fontsize=9, fontweight='bold')
    
    # Gate -> MCTS (NO: Straight Right)
    draw_arrow((5.6, 2.5), (7.1, 2.5))
    ax.text(6.35, 2.7, "No\n(Fail)", ha='center', fontsize=9, color='#d62728')
    
    # MCTS -> Output (Feedback Loop: Right -> Up -> Left)
    # 使用 Angle 连接风格画直角线
    arrow_feedback = FancyArrowPatch((8.0, 3.1), (5.8, 4.5), 
                                     arrowstyle='->', color='black', linewidth=1.2, mutation_scale=15,
                                     connectionstyle="Angle,angleA=90,angleB=0,rad=5") 
    ax.add_patch(arrow_feedback)
    ax.text(8.1, 3.5, "Success", ha='left', fontsize=9)

    # Reflexion Loop (Self-loop on MCTS)
    ax.annotate("Reflexion\nFeedback", xy=(8.0, 1.9), xytext=(8.0, 1.0),
                arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-0.5", lw=1, linestyle="--"),
                ha='center', fontsize=8, color='#555555')

    plt.tight_layout()
    plt.savefig("fig2_system_manhattan.pdf")
    print("✅ Figure 2 saved as fig2_system_manhattan.pdf")

if __name__ == "__main__":
    draw_system_fixed()