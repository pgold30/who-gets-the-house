import json, numpy as np, matplotlib
matplotlib.use("Agg"); import matplotlib.pyplot as plt
from prepost import price, date
plt.rcParams.update({"font.family":"DejaVu Sans","font.size":9,"axes.grid":True,
 "grid.color":"#e8e8e8","grid.linewidth":.7,"axes.spines.top":False,"axes.spines.right":False,
 "pdf.fonttype":42,"ps.fonttype":42,"savefig.dpi":330,"savefig.bbox":"tight"})
PRE, POST = date<"2019-04-01", date>="2020-01-01"
pre_p, post_p = price[PRE], price[POST]
V=json.load(open("verify_results.json"))
D=json.load(open("diffbunch_results.json"))

fig=plt.figure(figsize=(13.2,4.2))
gs=fig.add_gridspec(1,3,width_ratios=[1.25,1,1],wspace=.32)

# (a) non-parametric DiD coefficient plot
ax=fig.add_subplot(gs[0])
order=["1000000","2000000","3000000","1500000","1750000","2250000","2500000"]
lab={"1000000":"$1M  notch since 1989","2000000":"$2M  notch from Jul 2019",
     "3000000":"$3M  notch from Jul 2019","1500000":"$1.5M  placebo",
     "1750000":"$1.75M  placebo","2250000":"$2.25M  placebo","2500000":"$2.5M  placebo"}
y=np.arange(len(order))[::-1]
for i,k in zip(y,order):
    v=V[k]; treated = k in ("2000000","3000000")
    c = "#E45756" if treated else ("#54A24B" if k=="1000000" else "#8C8C8C")
    ax.plot([v["ci"][0],v["ci"][1]],[i,i],color=c,lw=2.2,solid_capstyle="butt")
    ax.plot(v["log_change"],i,"o",color=c,ms=6,zorder=3)
ax.axvline(0,color="#333",lw=1,ls="--")
ax.set_yticks(y); ax.set_yticklabels([lab[k] for k in order],fontsize=8.2)
ax.set_xlabel("log change in transactions just above,\nrelative to just below  (after Jul 2019 vs before)")
ax.set_title("(a)  Non-parametric difference-in-differences\nno counterfactual model is fitted",fontsize=9,loc="left")

# (b) focal spike at exactly X, relative to local non-round density
ax=fig.add_subplot(gs[1])
def ratio(p,x,half=25_000):
    near=p[(p>x-half)&(p<x+half)&(p%10_000!=0)]
    return (p==x).sum()/max(len(near)/(2*half)*10_000,1e-9)
pts=[(1_000_000,"$1M"),(2_000_000,"$2M"),(3_000_000,"$3M"),(1_500_000,"$1.5M"),(2_500_000,"$2.5M")]
w=.36; xs=np.arange(len(pts))
ax.bar(xs-w/2,[ratio(pre_p,x) for x,_ in pts],w,color="#4C78A8",label="before Jul 2019")
ax.bar(xs+w/2,[ratio(post_p,x) for x,_ in pts],w,color="#E45756",label="after Jul 2019")
ax.set_xticks(xs); ax.set_xticklabels([l for _,l in pts])
ax.set_ylabel("sales at exactly $X ÷ local density")
ax.legend(frameon=False,fontsize=7.8)
ax.set_title("(b)  The focal price collapses\nonly where it became taxable",fontsize=9,loc="left")
for i,(x,_) in enumerate(pts):
    if x in (2_000_000,3_000_000):
        ax.annotate("",xy=(i+w/2,ratio(post_p,x)+.4),xytext=(i-w/2,ratio(pre_p,x)+.4),
                    arrowprops=dict(arrowstyle="->",color="#333",lw=1.1))

# (c) charm price share
ax=fig.add_subplot(gs[2])
def charm(p,x):
    a=(p==x-1).sum(); b=(p==x).sum()
    return a/(a+b)*100 if a+b else 0
ax.bar(xs-w/2,[charm(pre_p,x) for x,_ in pts],w,color="#4C78A8")
ax.bar(xs+w/2,[charm(post_p,x) for x,_ in pts],w,color="#E45756")
ax.set_xticks(xs); ax.set_xticklabels([l for _,l in pts])
ax.set_ylabel("$X−1 as % of sales at $X−1 or $X")
ax.set_title("(c)  Sellers move one dollar below\nthe new threshold, not the old one",fontsize=9,loc="left")

fig.suptitle("The §1402-b notches switched on 1 July 2019. Three independent tests find the response only at the two thresholds that changed.\nNYC residential sales, 431,471 transactions, 2016–2025.",
             fontsize=10.2,y=1.10,x=.01,ha="left")
fig.savefig("Figure_C6.png"); fig.savefig("Figure_C6.pdf"); plt.close(fig)
print("ok")
