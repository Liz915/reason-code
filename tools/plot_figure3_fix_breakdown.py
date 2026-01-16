import matplotlib.pyplot as plt
import numpy as np

def draw_robustness():
    datasets = ['MBPP', 'HumanEval']
    fixed = [4, 3]
    broken = [0, 0] # Conditional 策略消除了 Broken
    
    x = np.arange(len(datasets))
    width = 0.4
    
    fig, ax = plt.subplots(figsize=(6, 5))
    rects1 = ax.bar(x - width/2, fixed, width, label='Fixed (Net Gain)', color='#2ca02c') # Green
    rects2 = ax.bar(x + width/2, broken, width, label='Broken (Regression)', color='#d62728') # Red
    
    ax.set_ylabel('Number of Problems')
    ax.set_title('Robustness Analysis (Conditional Strategy)')
    ax.set_xticks(x)
    ax.set_xticklabels(datasets)
    ax.legend()
    
    ax.bar_label(rects1, padding=3)
    ax.bar_label(rects2, padding=3)
    
    ax.set_ylim(0, 5) # 设置 Y 轴范围美观一点
    
    plt.tight_layout()
    plt.savefig("fig3_robustness.pdf")
    print("Figure 3 saved.")

draw_robustness()