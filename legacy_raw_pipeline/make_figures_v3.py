"""Figures 1-5 for "Who Gets the House?".

Every value is transcribed from the tables of the manuscript; nothing is
recomputed here, so the figures cannot drift from the text. Source table for
each panel is named in the block comment above it.

    python3 make_figures_v3.py     ->  figures/Figure_{1..5}.{pdf,png}
"""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D
from matplotlib.patches import Rectangle

plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.grid": True, "grid.color": "#e9e9e9", "grid.linewidth": .7,
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.edgecolor": "#444", "axes.labelcolor": "#222",
    "xtick.color": "#444", "ytick.color": "#444",
    "pdf.fonttype": 42, "ps.fonttype": 42,
    "savefig.dpi": 330, "savefig.bbox": "tight",
})

HOUSE, CONDO, COOP = "#3C6E9F", "#D1495B", "#7A9E7E"
GREY, RULE, ACCENT = "#8C8C8C", "#333333", "#C1663C"


def pct(ax, lo, hi, step, axis="y"):
    t = np.arange(lo, hi + 1e-9, step)
    (ax.set_yticks if axis == "y" else ax.set_xticks)(t)
    (ax.set_yticklabels if axis == "y" else ax.set_xticklabels)(
        [f"{v*100:.0f}%" for v in t])


def save(fig, n):
    fig.savefig(f"figures/Figure_{n}.pdf")
    fig.savefig(f"figures/Figure_{n}.png")
    plt.close(fig)
    print(f"  Figure_{n} written")


# ===================================================================== 1
# Source: Section 4.3, holding-period sweep (houses).
months = [12, 24, 36, 48, 60]
pi_s   = [0.1283, 0.1176, 0.1114, 0.1079, 0.1139]
se_s   = [0.0066, 0.0076, 0.0086, 0.0100, 0.0124]
asym   = [0.1522, 0.0553, 0.0096, -0.0340, -0.0652]

fig, ax = plt.subplots(figsize=(7.4, 4.0))
ax.axhline(0, color=RULE, lw=.9, ls=":", zorder=1)
ax.axvspan(36, 62, color="#f2f6fa", zorder=0)
ax.errorbar(months, pi_s, yerr=[1.96 * s for s in se_s], color=HOUSE,
            marker="o", ms=6.5, lw=2.0, capsize=3.5, zorder=3,
            label=r"symmetric component $\hat\pi_{\mathrm{sym}}$ — the premium")
ax.plot(months, asym, color=CONDO, marker="s", ms=6, lw=1.9, ls="--", zorder=3,
        label=r"asymmetry $A$ — cannot be a premium")
ax.annotate("renovation runs cash-then-financed\nand lands here",
            xy=(12, 0.1522), xytext=(16.5, 0.184), fontsize=8.2, color=CONDO,
            arrowprops=dict(arrowstyle="->", color=CONDO, lw=1.0))
ax.annotate("$A$ reaches zero at 36 months;\n$\\hat\\pi_{\\mathrm{sym}}$ stops moving",
            xy=(36, 0.0096), xytext=(40, 0.055), fontsize=8.2, color="#555",
            arrowprops=dict(arrowstyle="->", color="#666", lw=1.0))
ax.set_xlabel("minimum holding period between the two sales (months)")
ax.set_ylabel("share of price")
ax.set_xticks(months); ax.set_xlim(8, 64)
pct(ax, -0.08, 0.20, 0.04)
ax.legend(frameon=False, fontsize=8.4, loc="lower left")
save(fig, 1)

# ===================================================================== 2
# Source: Section 4.4 (by type, by borough), Section 4.3.1 (permit-free),
#         Section 4.5 (co-operatives).
fig, axes = plt.subplots(1, 2, figsize=(11.8, 4.0),
                         gridspec_kw={"width_ratios": [1, 1.45]})

ax = axes[0]
rows = [("Houses\n(1–3 family)", 0.0934, 0.0762, 0.1103, HOUSE, True),
        ("Condominiums",         0.0074, 0.0001, 0.0153, CONDO, False),
        ("Co-operatives",       -0.0120, -0.0318, 0.0039, COOP,  False)]
ax.axhline(0, color=RULE, lw=1.0, ls="--", zorder=1)
for i, (lab, p, lo, hi, c, is_house) in enumerate(rows):
    if is_house:  # pale marker = unrestricted, solid = permit-free
        ax.plot([i - .13, i - .13], [0.0942, 0.1267], color=HOUSE, lw=3,
                alpha=.32, solid_capstyle="butt", zorder=2)
        ax.plot(i - .13, 0.1114, "o", color=HOUSE, ms=8, alpha=.35, zorder=3)
        ax.annotate("11.1%\nall pairs", xy=(i - .13, 0.1267),
                    xytext=(0, 8), textcoords="offset points", ha="center",
                    fontsize=7.8, color=HOUSE, alpha=.75)
        i = i + .13
    ax.plot([i, i], [lo, hi], color=c, lw=3.2, solid_capstyle="butt", zorder=3)
    ax.plot(i, p, "o", color=c, ms=8.5, zorder=4)
    ax.annotate(f"{p*100:.1f}%", xy=(i, hi), xytext=(0, 8),
                textcoords="offset points", ha="center", fontsize=10,
                color=c, fontweight="bold")
ax.set_xticks(range(3)); ax.set_xticklabels([r[0] for r in rows])
ax.set_xlim(-.6, 2.6)
ax.set_ylabel(r"execution-certainty premium $\hat\pi$")
pct(ax, -0.04, 0.14, 0.02)
ax.set_ylim(-0.055, 0.152)
ax.set_title("(a)  By market", fontsize=9.5, loc="left")

ax = axes[1]
# borough: (name, house, condo, coop) each (pi, lo, hi) or None
boro = [("Manhattan", None, (0.0003, -0.0106, 0.0109), (-0.0135, -0.0315, 0.0087)),
        ("Bronx",     (0.0450, 0.0015, 0.0887), None, None),
        ("Brooklyn",  (0.0924, 0.0633, 0.1152), (0.0085, -0.0053, 0.0230),
                      (-0.0051, -0.0309, 0.0195)),
        ("Queens",    (0.1495, 0.1237, 0.1735), (0.0300, 0.0130, 0.0442), None)]
w = .26
ax.axhline(0, color=RULE, lw=1.0, ls="--", zorder=1)
for i, (name, h, c, k) in enumerate(boro):
    for off, val, col in ((-w, h, HOUSE), (0, c, CONDO), (w, k, COOP)):
        if val is None:
            continue
        p, lo, hi = val
        ax.bar(i + off, p, w * .92, color=col, zorder=2)
        ax.plot([i + off] * 2, [lo, hi], color=RULE, lw=1.3, zorder=3)
for xx in (0 - w, 1 + 0):
    ax.plot(xx, 0.0, marker="_", color=GREY, ms=9, mew=1.6, zorder=3)
    ax.text(xx, -0.004, "too few\npairs", ha="center", va="top",
            fontsize=6.6, color=GREY, style="italic", linespacing=1.05)
ax.set_xticks(range(len(boro))); ax.set_xticklabels([b[0] for b in boro])
ax.set_xlim(-0.58, 3.58)
ax.set_ylabel(r"$\hat\pi$")
pct(ax, -0.04, 0.18, 0.02)
ax.set_ylim(-0.05, 0.19)
ax.set_title("(b)  Within borough, all three markets", fontsize=9.5, loc="left")
ax.legend(handles=[Rectangle((0, 0), 1, 1, color=HOUSE),
                   Rectangle((0, 0), 1, 1, color=CONDO),
                   Rectangle((0, 0), 1, 1, color=COOP)],
          labels=["houses", "condominiums", "co-operatives"],
          frameon=False, fontsize=8.2, loc="upper left", ncol=1)
save(fig, 2)

# ===================================================================== 3
# Source: Section 5.1.2, the inversion d* = pi(1-q) / (q(1-pi)).
fig, ax = plt.subplots(figsize=(8.0, 3.9))
inv = [("Houses (permit-free)\n$\\hat\\pi=9.3\\%$", 0.247, 0.568, 0.784, HOUSE),
       ("Condominiums\n$\\hat\\pi=0.7\\%$",         0.018, 0.041, 0.057, CONDO)]
for i, (lab, lo, mid, hi, c) in enumerate(inv):
    ax.plot([lo, hi], [i, i], color=c, lw=9, solid_capstyle="butt",
            alpha=.9, zorder=2)
    ax.plot(mid, i, "o", color="white", ms=9, zorder=4,
            markeredgecolor=c, markeredgewidth=2.2)
    ax.annotate(f"{lo*100:.0f}%", xy=(lo, i), xytext=(-8, 0),
                textcoords="offset points", ha="right", va="center",
                fontsize=9, color=c, fontweight="bold")
    ax.annotate(f"{hi*100:.0f}%", xy=(hi, i), xytext=(8, 0),
                textcoords="offset points", ha="left", va="center",
                fontsize=9, color=c, fontweight="bold")
ax.axvspan(0.02, 0.06, color="#eaf1ea", zorder=0)
ax.text(0.04, 1.42, "relisting costs that\nsound like the world",
        ha="center", va="center", fontsize=8.2, color="#4a6b4e")
ax.set_yticks(range(2)); ax.set_yticklabels([r[0] for r in inv], fontsize=9)
ax.set_ylim(-0.75, 1.75); ax.invert_yaxis()
ax.set_xlim(0, 0.88)
pct(ax, 0, 0.8, 0.1, axis="x")
ax.set_xlabel("relisting cost $d^*$ the measured premium would have to be compensating for,\n"
              "as a share of property value  (bar spans the three HMDA failure definitions)")
ax.grid(axis="y", visible=False)
save(fig, 3)

# ===================================================================== 4
# Source: Section 5.3, total unjustified disadvantage.
fig, ax = plt.subplots(figsize=(8.2, 4.2))
STAT = "#54A24B"
groups = ["Houses\n(1–3 family)", "Condominiums", "Co-operatives"]
stat = [0.0141, 0.0128, 0.0]
mkt_lo, mkt_hi = [0.015, 0.0, 0.0], [0.056, 0.0, 0.0]
w = .5
for i in range(3):
    if stat[i] > 0:
        ax.bar(i, stat[i], w, color=STAT, zorder=2,
               label="statutory: mortgage recording tax" if i == 0 else None)
    if mkt_lo[i] > 0:
        ax.bar(i, mkt_lo[i], w, bottom=stat[i], color=HOUSE, zorder=2,
               label="market excess $\\pi-\\pi^*$, lower bound" if i == 0 else None)
        ax.bar(i, mkt_hi[i] - mkt_lo[i], w, bottom=stat[i] + mkt_lo[i],
               color=HOUSE, alpha=.38, zorder=2,
               label="market excess, range to upper bound" if i == 0 else None)
ax.axhline(0.01, color=ACCENT, lw=1.7, ls="--", zorder=3)
ax.annotate("the 1% charge\nproposed in 2026", xy=(2.28, 0.010),
            xytext=(2.30, 0.030), fontsize=8.6, color=ACCENT, ha="center",
            va="center", arrowprops=dict(arrowstyle="->", color=ACCENT, lw=1.1))
ax.annotate("2.9 – 7.0 points", xy=(0, 0.071), xytext=(0, 0.077), ha="center",
            fontsize=11, fontweight="bold", color=RULE)
ax.annotate("≈ 1.3 points\nentirely statutory", xy=(1, 0.0128),
            xytext=(1, 0.026), ha="center", fontsize=9.2, color=STAT,
            fontweight="bold")
ax.annotate("≈ 0\nno discount, no tax", xy=(2, 0.0), xytext=(2, 0.010),
            ha="center", fontsize=9.2, color=COOP, fontweight="bold")
ax.set_xticks(range(3)); ax.set_xticklabels(groups)
ax.set_xlim(-.55, 2.75)
ax.set_ylabel("unjustified disadvantage to the financed buyer,\nas a share of price")
pct(ax, 0, 0.08, 0.02)
ax.set_ylim(0, 0.088)
ax.legend(frameon=False, fontsize=8.2, loc="upper right")
save(fig, 4)

# ===================================================================== 5
# Source: Sections 6.4 (panel a), 6.5 (panel b), 6.6 (panel c).
fig, axes = plt.subplots(1, 3, figsize=(13.4, 4.1),
                         gridspec_kw={"width_ratios": [1.25, 1, 1]})

ax = axes[0]
dd = [("$1M   always taxed",      0.042, -0.011, 0.092, STAT),
      ("$2M   taxed from Jul 2019", -0.328, -0.431, -0.222, CONDO),
      ("$3M   taxed from Jul 2019", -0.591, -0.764, -0.425, CONDO),
      ("$1.5M   never taxed",      0.036, -0.031, 0.101, GREY),
      ("$1.75M  never taxed",     -0.008, -0.093, 0.077, GREY),
      ("$2.25M  never taxed",      0.040, -0.071, 0.157, GREY),
      ("$2.5M   never taxed",      0.021, -0.097, 0.148, GREY)]
ax.axvline(0, color=RULE, lw=1.0, ls="--", zorder=1)
for i, (lab, v, lo, hi, c) in enumerate(dd):
    ax.plot([lo, hi], [i, i], color=c, lw=2.6, solid_capstyle="butt", zorder=2)
    ax.plot(v, i, "o", color=c, ms=7, zorder=3)
ax.set_yticks(range(len(dd))); ax.set_yticklabels([d[0] for d in dd], fontsize=8.3)
ax.invert_yaxis(); ax.grid(axis="y", visible=False)
ax.set_xlabel("log change in transactions just above,\nrelative to just below "
              "(after Jul 2019 vs before)")
ax.set_title("(a)  No counterfactual is fitted", fontsize=9.5, loc="left")

ax = axes[1]
labs = ["$1M", "$2M", "$3M", "$1.5M", "$2.5M"]
pre  = [0.1, 7.8, 7.0, 5.2, 7.8]
post = [0.1, 1.6, 1.5, 6.2, 10.6]
x = np.arange(len(labs)); w = .38
ax.bar(x - w / 2, pre, w, color="#7f9dbb", label="before Apr 2019", zorder=2)
ax.bar(x + w / 2, post, w, color=CONDO, label="from Jan 2020", zorder=2)
for i in (1, 2):
    ax.annotate("", xy=(x[i] + w / 2, post[i] + .55),
                xytext=(x[i] - w / 2, pre[i] - .35),
                arrowprops=dict(arrowstyle="->", color=RULE, lw=1.3))
ax.set_xticks(x); ax.set_xticklabels(labs)
ax.set_ylabel(r"sales at exactly $X$ ÷ local density")
ax.legend(frameon=False, fontsize=8.2, loc="upper left")
ax.set_title("(b)  The focal price collapses only where\n      it became taxable",
             fontsize=9.5, loc="left")

ax = axes[2]
labs2 = ["$500k", "$1M", "$2M", "$3M", "$1.5M", "$2.5M"]
charm = [7.9, 78.4, 17.2, 18.5, 0.4, 0.1]
buyer = ["$0", "$10,000", "$5,000", "$7,500", "—", "—"]
cols = [GREY, CONDO, CONDO, CONDO, "#b8b8b8", "#b8b8b8"]
ax.bar(range(len(labs2)), charm, .62, color=cols, zorder=2)
for i, (v, b) in enumerate(zip(charm, buyer)):
    ax.annotate(b, xy=(i, v), xytext=(0, 5), textcoords="offset points",
                ha="center", fontsize=8, color="#444")
ax.set_xticks(range(len(labs2))); ax.set_xticklabels(labs2, fontsize=8.5)
ax.set_ylabel(r"sales at $X-1$ as % of sales at $X-1$ or $X$")
ax.set_ylim(0, 92)
ax.set_title("(c)  The response tracks the buyer's own\n      liability (labelled)",
             fontsize=9.5, loc="left")
save(fig, 5)
print("all figures written")
