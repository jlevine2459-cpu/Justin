import pandas as pd, numpy as np
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
g=pd.read_pickle(W+'hist.pkl'); margins=np.arange(-70,71)
def dist(tr,s,hs,half):
    age=tr.season.values.max()-tr.season.values
    w=np.exp(-0.5*((tr.spread_line.values-s)/hs)**2)*(0.5**(age/half) if half else 1)
    d=np.bincount((tr.margin.values+70).astype(int).clip(0,140),weights=w,minlength=141); return d/d.sum()
def rescale(d,s,p):
    a=margins>s;b=margins<s;pp=d[margins==s].sum();o=d.copy();o[a]*=p*(1-pp)/d[a].sum();o[b]*=(1-p)*(1-pp)/d[b].sum();return o
res={}
for half in [None,8,4]:
  for hs in [1.0,2.0]:
    rows=[]
    for season in range(2012,2026):
        tr=g[g.season<season]; te=g[(g.season==season)&g.p_home_cov_px.notna()]
        for _,r in te.iterrows():
            dd=rescale(dist(tr,r.spread_line,hs,half),r.spread_line,r.p_home_cov_px)
            for d in [-3,-2.5,-2,-1.5,-1,-0.5,0.5,1,1.5,2,2.5,3]:
                L=r.spread_line+d
                if L!=np.floor(L)+0.5: continue
                p=dd[margins>L].sum(); y=float(r.margin>L)
                rows.append((season,abs(d),p if d<0 else 1-p,y if d<0 else 1-y))
    R=pd.DataFrame(rows,columns=['season','gap','p','y'])
    cal=R.groupby('gap')[['p','y']].mean()
    print(f'half={half} hs={hs} Brier {((R.p-R.y)**2).mean():.5f} ',' '.join(f'{a}:{x.p:.4f}/{x.y:.4f}' for a,x in cal.iterrows()))
