import matplotlib.pyplot as plt

# Data
methods = {
    'Greedy Baseline': {'cost': 1.0, 'acc': 71.2, 'marker': 'o', 'color': 'gray', 's': 100},
    'Best-of-N (N=10)': {'cost': 10.0, 'acc': 72.8, 'marker': '^', 'color': '#d62728', 's': 120}, # Red
    'Reason-Code (Ours)': {'cost': 1.5, 'acc': 72.8, 'marker': '*', 'color': '#1f77b4', 's': 200}  # Blue
}

fig, ax = plt.subplots(figsize=(6, 4))

# Plot points
for name, data in methods.items():
    ax.scatter(data['cost'], data['acc'], marker=data['marker'], s=data['s'], c=data['color'], label=name, edgecolors='black', zorder=10, alpha=0.9)
    # Annotation
    offset_y = 0.3 if name != 'Greedy Baseline' else -0.5
    ax.text(data['cost'], data['acc'] + offset_y, f"  {data['acc']}%", fontsize=10, fontweight='bold', verticalalignment='center')

# Draw Pareto line (visual guide)
line_x = [1.0, 1.5, 10.0]
line_y = [71.2, 72.8, 72.8]
ax.plot(line_x, line_y, linestyle='--', color='gray', alpha=0.5, zorder=1)

ax.grid(True, linestyle=':', alpha=0.6)
ax.set_xlabel('Relative Inference Cost (Token Count)', fontsize=12, fontweight='bold')
ax.set_ylabel('MBPP Pass@1 Accuracy (%)', fontsize=12, fontweight='bold')
ax.set_title('Efficiency Frontier: Accuracy vs. Cost', fontsize=13)
ax.set_xlim(0, 11)
ax.set_ylim(70, 74)
ax.legend(loc='lower right', frameon=True, framealpha=0.9)

plt.tight_layout()
plt.savefig('pareto_frontier.pdf', dpi=300)
print("Saved pareto_frontier.pdf")