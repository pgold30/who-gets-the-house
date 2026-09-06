import json, os, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
E="/home/claude/v3_breakeven/"; N="/home/claude/empirical_c6/"
def find(n):
    for d in (E,N):
        if os.path.exists(d+n): return json.load(open(d+n))
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.grid":True,
 "grid.color":"#e8e8e8","grid.linewidth":.7,"axes.spines.top":False,"axes.spines.right":False,
 "pdf.fonttype":42,"ps.fonttype":42,"savefig.dpi":330,"savefig.bbox":"tight"})
HOUSE, CONDO, GREY, RED = "#4C78A8", "#E45756", "#8C8C8C", "#333333"

idx=find("index2_results.json"); brk=find("breakdown_results.json"); mer=find("merged_results.json")

# ---------- Figure 1: the premium is a house phenomenon ----------
fig,axes=plt.subplots(1,2,figsize=(11.6,3.9),gridspec_kw={"width_ratios":[1,1.25]})
ax=axes[0]
rows=[("Houses\n(1-3 family)", brk['distress:all sales/house'], HOUSE),
      ("Condominiums", brk['distress:all sales/condo'], CONDO)]
for i,(lab,r,c) in enumerate(rows):
    lo,hi=r['ci']
    ax.plot([i,i],[lo,hi],color=c,lw=3,solid_capstyle="butt")
    ax.plot(i,r['pi'],"o",color=c,ms=9,zorder=3)
    ax.annotate(f"{r['pi']*100:.1f}%",xy=(i,hi),xytext=(0,7),textcoords="offset points",
                ha="center",fontsize=10,color=c,fontweight="bold")
ax.axhline(0,color=RED,lw=1,ls="--")
ax.set_xticks([0,1]); ax.set_xticklabels([r[0] for r in rows])
ax.set_ylabel("execution-certainty premium $\\pi$")
ax.set_ylim(-0.02,0.15); ax.set_yticks(np.arange(0,0.16,0.03))
ax.set_yticklabels([f"{v*100:.0f}%" for v in np.arange(0,0.16,0.03)])
ax.set_title("(a)  By property type",fontsize=9.5,loc="left")

ax=axes[1]
pairs=[("Manhattan",None,"Manhattan/condo"),("Bronx","Bronx/house",None),
       ("Brooklyn","Brooklyn/house","Brooklyn/condo"),("Queens","Queens/house","Queens/condo")]
w=0.34; xs=np.arange(len(pairs))
for i,(name,hk,ck) in enumerate(pairs):
    if hk:
        r=brk[hk]; ax.bar(i-w/2,r['pi'],w,color=HOUSE,zorder=2)
        ax.plot([i-w/2]*2,r['ci'],color=RED,lw=1.4,zorder=3)
    if ck:
        r=brk[ck]; ax.bar(i+w/2,r['pi'],w,color=CONDO,zorder=2)
        ax.plot([i+w/2]*2,r['ci'],color=RED,lw=1.4,zorder=3)
ax.axhline(0,color=RED,lw=1,ls="--")
ax.set_xticks(xs); ax.set_xticklabels([p[0] for p in pairs])
ax.set_ylabel("$\\pi$")
ax.set_yticks(np.arange(0,0.19,0.03)); ax.set_yticklabels([f"{v*100:.0f}%" for v in np.arange(0,0.19,0.03)])
ax.set_title("(b)  Within borough — houses (blue) against condominiums (red)",fontsize=9.5,loc="left")
ax.legend(handles=[plt.Rectangle((0,0),1,1,color=HOUSE),plt.Rectangle((0,0),1,1,color=CONDO)],
          labels=["houses","condominiums"],frameon=False,fontsize=8,loc="upper left")
fig.savefig("figures/Figure_1.pdf"); fig.savefig("figures/Figure_1.png"); plt.close(fig)

# ---------- Figure 2: symmetry decomposition ----------
h=sorted(idx['holding_sensitivity'],key=lambda r:r['months'])
m=[r['months'] for r in h]; pi=[r['pi'] for r in h]; se=[r['se'] for r in h]; az=[r['asym'] for r in h]
fig,ax=plt.subplots(figsize=(7.6,4.0))
ax.errorbar(m,pi,yerr=[1.96*s for s in se],color=HOUSE,marker="o",ms=6,lw=1.8,capsize=3,
            label="$\\pi$, symmetric component (the premium)")
ax.plot(m,az,color=CONDO,marker="s",ms=6,lw=1.8,ls="--",
        label="asymmetry $A$ (cannot be a premium)")
ax.axhline(0,color=RED,lw=1,ls=":")
ax.axvline(36,color="#999",lw=1,ls="-",alpha=.6)
ax.annotate("asymmetry reaches zero\nat 36 months; $\\pi$ stops moving",
            xy=(36,0.006),xytext=(41,0.075),fontsize=8.2,
            arrowprops=dict(arrowstyle="->",color="#555",lw=1))
ax.set_xlabel("minimum holding period between the two sales (months)")
ax.set_ylabel("share of price")
ax.set_xticks(m); ax.set_yticks(np.arange(-0.08,0.19,0.04))
ax.set_yticklabels([f"{v*100:.0f}%" for v in np.arange(-0.08,0.19,0.04)])
ax.legend(frameon=False,fontsize=8.4,loc="upper right")
fig.savefig("figures/Figure_2.pdf"); fig.savefig("figures/Figure_2.png"); plt.close(fig)
print("figures 1-2 written")

# ---------- Figure 3: the decomposition ----------
import json
fig,ax=plt.subplots(figsize=(8.4,4.2))
STAT="#54A24B"; MKT=HOUSE
groups=["Houses\n(1-3 family)","Condominiums"]
mkt_lo,mkt_hi = 0.033, 0.074
stat = 0.0141
x=np.arange(2); w=0.5
# condominium market excess is zero or negative -> plotted as zero
ax.bar(x[0],stat,w,color=STAT,label="statutory: mortgage recording tax (1.41% of price)",zorder=2)
ax.bar(x[0],mkt_lo,w,bottom=stat,color=MKT,label="market excess $\\pi-\\pi^*$ (lower bound)",zorder=2)
ax.bar(x[0],mkt_hi-mkt_lo,w,bottom=stat+mkt_lo,color=MKT,alpha=.42,
       label="market excess, range to upper bound",zorder=2)
ax.bar(x[1],stat,w,color=STAT,zorder=2)
ax.axhline(0.01,color=RED,lw=1.6,ls="--",zorder=3)
ax.set_xlim(-0.45,2.05)
ax.annotate("the 1% charge\nproposed in 2026",xy=(1.42,0.010),xytext=(1.60,0.028),
            fontsize=8.6,color=RED,ha="left",va="center",
            arrowprops=dict(arrowstyle="->",color=RED,lw=1.1))
ax.annotate(f"4.7 – 8.8 points",xy=(0,stat+mkt_hi),xytext=(0,0.093),ha="center",
            fontsize=10.5,fontweight="bold",color=RED)
ax.annotate("≈ 1.4 points\nentirely statutory",xy=(1,stat),xytext=(1,0.030),ha="center",
            fontsize=9.5,color=STAT,fontweight="bold")
ax.set_xticks(x); ax.set_xticklabels(groups)
ax.set_ylabel("unjustified disadvantage to the financed buyer,\nas a share of price")
ax.set_ylim(0,0.105)
ax.set_yticks(np.arange(0,0.11,0.02)); ax.set_yticklabels([f"{v*100:.0f}%" for v in np.arange(0,0.11,0.02)])
ax.legend(frameon=False,fontsize=8.2,loc="upper right")
fig.savefig("figures/Figure_3.pdf"); fig.savefig("figures/Figure_3.png"); plt.close(fig)
print("figure 3 written")
