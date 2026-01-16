import matplotlib.pyplot as plt

def draw_efficiency():
    # HumanEval Data
    sampling_cost = [1, 10]
    sampling_pass = [86.6, 88.4] # Baseline -> Best-of-10
    
    rc_cost = [1.0, 1.5]
    rc_pass = [86.6, 88.4] # Baseline -> Conditional
    
    plt.figure(figsize=(7, 5))
    
    # Plot Sampling (Dashed)
    plt.plot(sampling_cost, sampling_pass, linestyle='--', color='gray', marker='o', label='Best-of-N Sampling')
    
    # Plot Reason-Code (Solid, Red)
    plt.plot(rc_cost, rc_pass, linestyle='-', color='#d62728', marker='*', markersize=12, linewidth=2, label='Reason-Code (Ours)')
    
    # Annotations
    plt.annotate("10x Cost", xy=(10, 88.4), xytext=(8, 87.5), arrowprops=dict(arrowstyle="->"))
    plt.annotate("1.5x Cost", xy=(1.5, 88.4), xytext=(2, 89.0), arrowprops=dict(arrowstyle="->", color='#d62728'))
    
    plt.xlabel("Relative Token Cost (1.0 = Greedy)", fontsize=12)
    plt.ylabel("HumanEval Pass@1 (%)", fontsize=12)
    plt.title("Efficiency Frontier: Ours vs. Sampling", fontsize=14)
    plt.grid(True, linestyle=':', alpha=0.6)
    plt.legend(fontsize=11)
    
    plt.tight_layout()
    plt.savefig("fig2_efficiency.pdf")
    print("Figure 2 saved.")

draw_efficiency()