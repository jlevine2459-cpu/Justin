import pandas as pd,numpy as np,json
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
B=pd.read_pickle('bt.pkl'); H=pd.read_pickle(W+'hist.pkl'); H=H[H.season<2026]
margins=np.arange(-70,71)
def novig(a,b):
    f=lambda x: -x/(-x+100) if x<0 else 100/(x+100); ia,ib=f(a),f(b); return ia/(ia+ib)
def kdist(s,t,hs,ht):
    w=np.exp(-0.5*((H.spread_line.values-s)/hs)**2)*np.exp(-0.5*((H.total_line.values-t)/ht)**2)
    d=np.bincount((H.margin.values+70).astype(int).clip(0,140),weights=w,minlength=141); return d/d.sum()
def rescale(d,s,p):
    a=margins>s;b=margins<s;pp=d[margins==s].sum();o=d.copy();o[a]*=p*(1-pp)/d[a].sum();o[b]*=(1-p)*(1-pp)/d[b].sum();return o
def p_home_cover(s,t,ho,ao,L,shrink,hs,ht):
    p=novig(ho,ao); p=0.5+shrink*(p-0.5)
    d=rescale(kdist(s,t,hs,ht),s,p); return d[margins+L>0].sum()
# road-dog prior from pre-2026 data only
h=H[(H.spread_line!=H.result)&(H.spread_line!=0)&(H.location!='Neutral')&(H.season>=2008)]
rd=h[h.spread_line>0]; rd_rate=(rd.result<rd.spread_line).mean(); RD=0.5*(rd_rate-0.5)
print(f'road-dog cover rate 2008-2025 {rd_rate:.4f} -> prior {RD:+.4f}')
def roaddog_adj(r):
    if r.neutral: return 0.0
    # pool line determines who is the dog in the pool: home gets L points; if L>0 home is pool dog
    return -RD if r.pool_home<0 else 0.0   # home favoured -> away road dog gets +RD, so home prob -RD
out=[]
for _,r in B.iterrows():
    snap_s=-r.snap_mkt_home_margin*-1  # market_home_margin = expected home margin
    s_snap=r.snap_mkt_home_margin; s_close=r.close_spread
    L=r.pool_home
    my_snap = p_home_cover(s_snap,r.snap_total,r.snap_ho,r.snap_ao,L,0.5,2,10)+roaddog_adj(r)
    cgm_close = p_home_cover(s_close,r.close_total,r.close_ho,r.close_ao,L,1.0,3,7)
    book_close= p_home_cover(s_close,r.close_total,r.close_ho,r.close_ao,L,0.5,2,10)
    my_lock = 0.5*book_close+0.5*r.k_p_home+roaddog_adj(r)
    out.append(dict(my_snap=my_snap,cg_method_lock=cgm_close,book_lock=book_close,my_lock=my_lock,kalshi_lock=r.k_p_home))
B=pd.concat([B,pd.DataFrame(out,index=B.index)],axis=1)
B.to_pickle('bt_scored.pkl')
