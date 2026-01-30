import matplotlib.pyplot as plt
import numpy as np

def draw_robustness_grayscale():
    # 数据
    datasets = ['MBPP'] # 只画 MBPP 显得更聚焦，或者加上 HumanEval 也可以
    fixed = [4]
    broken = [0] 
    
    # 设置画布
    fig, ax = plt.subplots(figsize=(5, 4))
    
    # 定义位置
    x = np.arange(len(datasets))
    width = 0.6
    
    # --- 核心修改：颜色与纹理 ---
    # Fixed: 深灰，无纹理
    rects1 = ax.bar(x - width/3, fixed, width/1.5, label='Fixed (Net Gain)', 
                    color='#606060', edgecolor='black', linewidth=1)
    
    # Broken: 浅灰 + 斜线纹理 (关键！)
    rects2 = ax.bar(x + width/3, broken, width/1.5, label='Regressions', 
                    color='white', edgecolor='black', hatch='///', linewidth=1)
    
    # --- 标注 ---
    ax.set_ylabel('Number of Tasks', fontsize=11, fontweight='bold')
    # ax.set_title('Robustness Analysis', fontsize=12) # 论文里通常不要标题，用 Caption
    ax.set_xticks([]) # 只有一个数据集时，去掉 X 轴刻度更干净
    ax.set_xlabel('MBPP Dataset', fontsize=11, fontweight='bold')
    
    # Legend
    ax.legend(loc='upper right', frameon=False, fontsize=10)
    
    # Y轴范围
    ax.set_ylim(0, 5)
    ax.set_yticks(range(0, 6))
    ax.grid(axis='y', linestyle='--', alpha=0.3)
    
    # --- 强力标注 Zero Regression ---
    # 在 0 的柱子上方写字
    ax.text(width/3, 0.2, "ZERO\nRegression", ha='center', va='bottom', 
            fontsize=10, fontweight='bold', color='black')
    
    # 在 4 的柱子上方写字
    ax.text(-width/3, 4.1, "+4 Tasks", ha='center', va='bottom', 
            fontsize=10, fontweight='bold')

    # 去掉上边和右边的框线
    ax.spines['top'].set_visible(False)
    ax.spines['right'].set_visible(False)

    plt.tight_layout()
    plt.savefig("fig4_robustness_gray.pdf")
    print("Figure 4 saved (Grayscale).")

draw_robustness_grayscale()