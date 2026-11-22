import pandas as pd,numpy as np
B=pd.read_pickle('bt_scored.pkl')
y=B.home_cov.values; push=B.push.values
print('games',len(B),'pushes',push.sum())
def card_from_prob(p): return np.where(p>=0.5,B.home,B.away)
def grade(picks):
    win=np.where(picks==B.home.values, y==1, y==0) & ~push
    return win
models={'ChatGPT recorded (its probabilities)':B.cg_p_home.values,
        'My method, same data ChatGPT had':B.my_snap.values,
        'ChatGPT method, lock-time odds':B.cg_method_lock.values,
        'Sportsbook only, lock-time (my method)':B.book_lock.values,
        'Kalshi only, lock-time':B.kalshi_lock.values,
        'MY FULL MODEL, lock-time':B.my_lock.values}
# market-at-lock reference for 'expected wins' (pick quality): average of sportsbook-lock and kalshi-lock, no road-dog
ref=0.5*B.book_lock.values+0.5*B.kalshi_lock.values
rows=[]
for name,p in models.items():
    picks=card_from_prob(p); win=grade(picks)
    pc=np.clip(p,1e-3,1-1e-3)
    brier=((pc-y)**2)[~push].mean(); ll=-(y*np.log(pc)+(1-y)*np.log(1-pc))[~push].mean()
    exp_ref=np.where(picks==B.home.values,ref,1-ref).sum()
    rows.append((name,win.sum(),(~win&~push).sum(),brier,ll,exp_ref))
for k,lbl in [('cg_season','ChatGPT SEASON card (recorded)'),('cg_bal','ChatGPT BALANCED card (recorded)'),('cg_week','ChatGPT WEEKLY card (recorded)')]:
    picks=B[k].values; win=grade(picks); exp_ref=np.where(picks==B.home.values,ref,1-ref).sum()
    rows.append((lbl,win.sum(),(~win&~push).sum(),np.nan,np.nan,exp_ref))
R=pd.DataFrame(rows,columns=['model','W','L','Brier','LogLoss','ExpWins@lockMkt'])
print(R.round(4).to_string(index=False))
print('coin-flip Brier 0.25, logloss 0.6931')
# per-week W for main comparisons
pw=pd.DataFrame({'week':B.week,'cg_season':grade(B.cg_season.values),'cg_bal':grade(B.cg_bal.values),'my_lock':grade(card_from_prob(B.my_lock.values)),'kalshi':grade(card_from_prob(B.kalshi_lock.values)),'n':1}).groupby('week').sum()
print(pw)
# where my full model and ChatGPT season card disagree
mp=card_from_prob(B.my_lock.values); d=mp!=B.cg_season.values
print('\ndisagreements:',d.sum(),' my record on them',grade(mp)[d].sum(),'-',(~grade(mp)&~push)[d].sum(),' ChatGPT',grade(B.cg_season.values)[d].sum())
D=B[d].assign(my=mp[d])[['week','away','home','pool_home','margin','cg_season','my','cg_p_home','my_lock','kalshi_lock']]
print(D.round(3).to_string(index=False))
