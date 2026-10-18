import matplotlib.pyplot as plt
import numpy as np

NAVY, TEAL, GREY, LTGREY = "#16233D", "#0E8C8C", "#6B7280", "#E5E7EB"
plt.rcParams.update({
    "font.family": "DejaVu Serif", "font.size": 11,
    "axes.edgecolor": GREY, "axes.linewidth": 0.8,
    "axes.grid": True, "grid.color": LTGREY, "grid.linewidth": 0.7,
    "axes.axisbelow": True, "figure.dpi": 200,
})

metrics = ["Context\nPrecision", "Context\nRecall", "Faithfulness",
           "Noise\nSensitivity", "Response\nRelevancy", "Answer\nAccuracy"]
vrag  = [0.810, 0.342, 0.740, 0.268, 0.751, 0.329]
vsd   = [0.016, 0.001, 0.009, 0.003, 0.002, 0.007]
kgrag = [0.769, 0.564, 0.764, 0.323, 0.821, 0.417]
ksd   = [0.018, 0.040, 0.014, 0.018, 0.001, 0.004]

x = np.arange(len(metrics)); w = 0.38
fig, ax = plt.subplots(figsize=(9, 4.6))
b1 = ax.bar(x - w/2, vrag, w, yerr=vsd, capsize=3, label="VRAG", color=NAVY,
            error_kw=dict(ecolor=GREY, lw=1))
b2 = ax.bar(x + w/2, kgrag, w, yerr=ksd, capsize=3, label="KGRAG", color=TEAL,
            error_kw=dict(ecolor=GREY, lw=1))
for bars, vals in ((b1, vrag), (b2, kgrag)):
    for r, v in zip(bars, vals):
        ax.text(r.get_x()+r.get_width()/2, v+0.02, f"{v:.2f}", ha="center",
                va="bottom", fontsize=7.5, color=NAVY)
ax.axvspan(3.5, 5.5, color=TEAL, alpha=0.05)               # shade cross-system
ax.text(4.5, 0.96, "cross-system comparators", ha="center", fontsize=7.5,
        color=TEAL, style="italic")
ax.set_xticks(x); ax.set_xticklabels(metrics, fontsize=8.5)
ax.set_ylabel("Score"); ax.set_ylim(0, 1.0)
ax.set_title("RAGAS Metrics for VRAG and KGRAG (mean ± SD over 3 judge runs, n = 35)",
             fontsize=11, color=NAVY, pad=10)
ax.legend(frameon=False, loc="upper right")
ax.spines["top"].set_visible(False); ax.spines["right"].set_visible(False)
ax.tick_params(length=0)
plt.tight_layout(); plt.savefig("figures/fig_ragas_comparison.png", bbox_inches="tight")
plt.show()