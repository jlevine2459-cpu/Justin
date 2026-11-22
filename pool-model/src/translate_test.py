# Out-of-sample test: how well do methods convert a market spread into cover probability at a DIFFERENT (pool) line?
import pandas as pd, numpy as np
from scipy.stats import norm
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
g=pd.read_pickle(W+'hist.pkl')
margins=np.arange(-70,71)
def kernel_dist(tr, s, t, hs, ht):
    w=np.exp(-0.5*((tr.spread_line.values-s)/hs)**2)
    if ht: w*=np.exp(-0.5*((tr.total_line.values-t)/ht)**2)
    d=np.bincount((tr.margin.values+70).astype(int).clip(0,140),weights=w,minlength=141)
    return d/d.sum()
def rescale(dist, s, p_home):  # ChatGPT-style: match no-vig home-cover prob at market line, keep push mass
    above=margins>s; below=margins<s; push=margins==s
    pa=dist[above].sum(); pb=dist[below].sum(); pp=dist[push].sum()
    tgt_a=p_home*(1-pp); tgt_b=(1-p_home)*(1-pp)
    out=dist.copy(); out[above]*=tgt_a/pa; out[below]*=tgt_b/pb; return out
rows=[]
for season in range(2012,2026):
    tr=g[g.season<season]; te=g[g.season==season]
    for _,r in te.iterrows():
        s=r.spread_line; t=r.total_line
        dists={'kern_s3_t7':kernel_dist(tr,s,t,3,7),'kern_s1':kernel_dist(tr,s,t,1,None),'kern_s2_t10':kernel_dist(tr,s,t,2,10)}
        offs=[-3,-2.5,-2,-1.5,-1,-0.5,0.5,1,1.5,2,2.5,3]
        for d in offs:
            L=s+d
            if L!=np.floor(L)+0.5: continue  # pool lines are half points
            y=float(r.margin>L)
            rec={'season':season,'d':d,'L':L,'s':s,'y':y,'normal13.5':1-norm.cdf(L,loc=s,scale=13.5)}
            for k,dist in dists.items():
                rec[k]=dist[margins>L].sum()
                if not np.isnan(r.p_home_cov_px):
                    rec[k+'+px']=rescale(dist,s,r.p_home_cov_px)[margins>L].sum()
            rows.append(rec)
R=pd.DataFrame(rows); R.to_pickle(W+'translate_test.pkl')
cols=[c for c in R.columns if c not in('season','d','L','s','y')]
sub=R.dropna()
print('n predictions',len(sub),'games-ish',len(sub)/6)
for c in cols:
    p=sub[c].clip(1e-4,1-1e-4)
    print(f"{c:18s} Brier {((p-sub.y)**2).mean():.5f}  logloss {-(sub.y*np.log(p)+(1-sub.y)*np.log(1-p)).mean():.5f}")
# Key test: probability of the margin landing in the gap between market and pool line (the 'value' region)
sub=sub.assign(gap=lambda x: np.abs(x.d))
print('\nBy |offset| (calibration of kern_s3_t7 vs observed):')
for a,grp in sub.groupby('gap'):
    print(a, len(grp), 'pred', round(grp['kern_s3_t7'].where(grp.d<0,1-grp['kern_s3_t7']).mean(),4), 'obs', round(grp.y.where(grp.d<0,1-grp.y).mean(),4))
