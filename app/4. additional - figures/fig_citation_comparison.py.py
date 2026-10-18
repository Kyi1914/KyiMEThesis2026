import matplotlib.pyplot as plt
import numpy as np

NAVY, TEAL, GREY, LTGREY = "#16233D", "#0E8C8C", "#6B7280", "#E5E7EB"
plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 11,
    "axes.edgecolor": GREY, "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": LTGREY, "grid.linewidth": 0.7,
    "axes.axisbelow": True, "figure.dpi": 200,
})

groups = ["Citation recall", "Citation precision"]
vr, kg = [0.510, 0.333], [0.510, 0.661]   # VRAG, KGRAG
x = np.arange(len(groups)); w = 0.34

fig, ax = plt.subplots(figsize=(6.2, 4.3))
b1 = ax.bar(x - w/2, vr, w, label="VRAG", color=NAVY)
b2 = ax.bar(x + w/2, kg, w, label="KGRAG", color=TEAL)
for bars, vals in ((b1, vr), (b2, kg)):
    for r, v in zip(bars, vals):
        ax.text(r.get_x()+r.get_width()/2, v+0.012, f"{v:.3f}",
                ha="center", va="bottom", fontsize=9, color=NAVY)
ax.set_xticks(x); ax.set_xticklabels(groups)
ax.set_ylabel("Score"); ax.set_ylim(0, 0.8)
ax.set_title("Section-Citation Recall and Precision (34 questions with gold sections)",
             fontsize=10.5, color=NAVY, pad=10)
ax.legend(frameon=False, loc="upper left")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(length=0)
plt.tight_layout(); plt.savefig("figures/fig_citation_comparison.png", bbox_inches="tight")
plt.show()