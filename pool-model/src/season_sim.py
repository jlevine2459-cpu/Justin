# Season-to-date payout simulation for choosing the Week 11 card.
import numpy as np, pandas as pd, itertools, sys, json
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
F=np.load(W+'field.npz'); R=pd.read_pickle(W+'probs.pkl')
fav=list(F['fav']); 
# align model rows to sheet order (sheet uses JAC, LVR etc.)
alias={'JAC':'JAX'}
R=R.set_index('fav').loc[[alias.get(f,f) for f in fav]].reset_index()
PROB=sys.argv[1] if len(sys.argv)>1 else 'mine'
FUT_EDGE=float(sys.argv[2]) if len(sys.argv)>2 else 1.0
p_fav=R.p_fav.values if PROB=='mine' else np.array(json.loads(PROB))
NS=int(sys.argv[3]) if len(sys.argv)>3 else 30000
SEED=int(sys.argv[4]) if len(sys.argv)>4 else 11
rng=np.random.default_rng(SEED)
CAND=sys.argv[5] if len(sys.argv)>5 else None
w=F['w'].astype(float); isJ=F['is_justin']; picks=F['fav_pick']; tb=F['tb']; tbavg=F['tbavg']
oth=~isJ; n_o=oth.sum()
posted=(picks[:,0]>=0)
share=np.array([picks[posted&oth,k].mean() for k in range(12)])   # share on favorite
SEASON_PAY=np.array([6550,5450,4400,3400,2600,2000,1600,1275,1000,775,600,450,325,200,100]+[0]*500,float)
WEEK_PAY=np.array([400,150]+[0]*500,float)
FUT_WEEKS,GPW=7,13
cards=np.array(list(itertools.product([0,1],repeat=12)),dtype=np.int8)  # 1 = favorite
if CAND: cards=np.load(CAND)
per_sim=np.zeros((NS,len(cards)),dtype=np.float32) if CAND else None
J_TB=55
ev_season=np.zeros(len(cards)); ev_week=np.zeros(len(cards)); ev_wins=np.zeros(len(cards))
pay_samples=[]
p_pick_model=np.maximum(p_fav,1-p_fav); fav_is_pick=(p_fav>=0.5).astype(int)
o_picks=picks[oth].copy(); o_posted=posted[oth]; o_w=w[oth]; o_tb=tb[oth]; o_tbavg=tbavg[oth]
key_noise=2.5
for s in range(NS):
    out=(rng.random(12)<p_fav).astype(np.int8)            # 1 = favorite covers
    # others' week-11 picks: posted are fixed, others drawn from shares
    op=o_picks.copy()
    m=~o_posted
    op[m]=(rng.random((m.sum(),12))<share).astype(np.int8)
    o_wk=(op==out).sum(1)
    # future weeks: resample template games from this week
    tg=rng.integers(0,12,FUT_WEEKS*GPW)
    pf=0.5+FUT_EDGE*(p_fav[tg]-0.5); sh=share[tg]
    fout=(rng.random(len(tg))<pf)
    ofp=(rng.random((n_o,len(tg)))<sh)
    o_fut=(ofp==fout).sum(1)
    j_fut=((fav_is_pick[tg]==1)==fout).sum()  # Justin plays model side in future
    o_tot=o_w+o_wk+o_fut
    # season tiebreak key: current TB avg + noise (lower better) -> composite
    ok=o_tbavg+rng.normal(0,key_noise,n_o); jk=11.4+rng.normal(0,key_noise)
    allk=np.concatenate([ok,[jk]]); r=allk.argsort().argsort()/len(allk)   # 0 best
    o_comp=o_tot+0.5*(1-r[:-1]); j_keypart=0.5*(1-r[-1])
    o_sorted=np.sort(o_comp)
    j_wk=(cards==out).sum(1)
    j_tot=85+j_wk+j_fut
    n_above=n_o-np.searchsorted(o_sorted,j_tot+j_keypart,side='right')
    sp=SEASON_PAY[n_above]
    # weekly: tiebreak by closeness to CIN-WAS total
    tot=max(10,round(rng.normal(54.5,13.5)))
    otb=np.where(o_posted,o_tb,np.clip(np.round(rng.normal(46,8,n_o)),0,99))
    od=np.abs(otb-tot)+rng.random(n_o)*0.5; jd=abs(J_TB-tot)+rng.random()*0.5
    o_wc=np.sort(o_wk+0.5*(1-od/200)); j_wc=j_wk+0.5*(1-jd/200)
    wa=n_o-np.searchsorted(o_wc,j_wc,side='right')
    wp=WEEK_PAY[wa]
    ev_season+=sp; ev_week+=wp; ev_wins+=j_wk
    if CAND: per_sim[s]=sp+wp
    if s<NS: pay_samples.append(sp[[0]]) if False else None
ev_season/=NS; ev_week/=NS; ev_wins/=NS
(np.save(W+f'persim_{SEED}.npy',per_sim) if CAND else None)
np.savez(W+f'sim_{SEED}_{len(cards)}_{"mine" if PROB=="mine" else "alt"}_{FUT_EDGE}.npz',cards=cards,ev_season=ev_season,ev_week=ev_week,ev_wins=ev_wins)
tot=ev_season+ev_week
def show(lbl,c):
    i=next((j for j in range(len(cards)) if (cards[j]==c).all()),None)
    if i is None: return
    print(f"{lbl:28s} wins {ev_wins[i]:.3f}  season ${ev_season[i]:8.2f}  weekly ${ev_week[i]:6.2f}  total ${tot[i]:8.2f}  card "+' '.join(fav[k] if c[k] else R.dog[k] for k in range(12)))
best=np.argsort(-tot)[:8]
show('MODEL max-wins card',fav_is_pick)
for b in best: show('top $',cards[b])
print('share on fav:',dict(zip(fav,share.round(3))))
