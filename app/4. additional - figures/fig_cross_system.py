import matplotlib.pyplot as plt
import numpy as np
from matplotlib.gridspec import GridSpec

NAVY, TEAL, GREY, LTGREY = "#16233D", "#0E8C8C", "#6B7280", "#E5E7EB"
plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 11,
    "axes.edgecolor": GREY, "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": LTGREY, "grid.linewidth": 0.7,
    "axes.axisbelow": True, "figure.dpi": 200,
})

qlabels = ["Answer\nAccuracy", "Response\nRelevancy", "Citation\nrecall", "Citation\nprecision"]
qv, qk = [0.329, 0.751, 0.510, 0.333], [0.417, 0.821, 0.510, 0.661]  # VRAG, KGRAG
lv, lk = [2.12], [4.35]  # median latency (s)

fig = plt.figure(figsize=(9.6, 4.8))
gs = GridSpec(1, 2, width_ratios=[4, 1.15], wspace=0.28)
w = 0.38

ax1 = fig.add_subplot(gs[0]); x = np.arange(len(qlabels))
b1 = ax1.bar(x - w/2, qv, w, color=NAVY, label="VRAG")
b2 = ax1.bar(x + w/2, qk, w, color=TEAL, label="KGRAG")
for bars, vals in ((b1, qv), (b2, qk)):
    for r, v in zip(bars, vals):
        ax1.text(r.get_x()+r.get_width()/2, v+0.015, f"{v:.3f}", ha="center", va="bottom", fontsize=8, color=NAVY)
ax1.set_xticks(x); ax1.set_xticklabels(qlabels, fontsize=9)
ax1.set_ylabel("Score"); ax1.set_ylim(0, 0.95)
ax1.set_title("Quality comparators (higher is better)", fontsize=10, color=NAVY, pad=8)
ax1.spines["top"].set_visible(False); ax1.spines["right"].set_visible(False); ax1.tick_params(length=0)

ax2 = fig.add_subplot(gs[1]); x2 = np.arange(1)
c1 = ax2.bar(x2 - w/2, lv, w, color=NAVY)
c2 = ax2.bar(x2 + w/2, lk, w, color=TEAL)
for bars, vals in ((c1, lv), (c2, lk)):
    for r, v in zip(bars, vals):
        ax2.text(r.get_x()+r.get_width()/2, v+0.08, f"{v:.2f}", ha="center", va="bottom", fontsize=8, color=NAVY)
ax2.set_xticks(x2); ax2.set_xticklabels(["Median\nlatency"], fontsize=9)
ax2.set_ylabel("Seconds"); ax2.set_ylim(0, 5.2)
ax2.set_title("Speed (lower is better)", fontsize=10, color=NAVY, pad=8)
ax2.spines["top"].set_visible(False); ax2.spines["right"].set_visible(False); ax2.tick_params(length=0)

fig.legend([b1, b2], ["VRAG", "KGRAG"], frameon=False, ncol=2, loc="upper center", bbox_to_anchor=(0.5, 1.03), fontsize=10)
plt.tight_layout(rect=[0, 0, 1, 0.94])
plt.savefig("figures/fig_cross_system.png", bbox_inches="tight")
plt.show()