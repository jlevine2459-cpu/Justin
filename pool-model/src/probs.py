import pandas as pd,numpy as np,json
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
g=pd.read_pickle(W+'hist.pkl'); margins=np.arange(-70,71)
cur=pd.read_csv(W+'raw/games.csv'); cur=cur[(cur.season==2026)&(cur.week==11)&(cur.gameday>='2026-11-22')]
def novig(a,b):
    f=lambda x: -x/(-x+100) if x<0 else 100/(x+100); ia,ib=f(a),f(b); return ia/(ia+ib)
def dist(s,t):
    tr=g[g.season<2026]
    w=np.exp(-0.5*((tr.spread_line.values-s)/2)**2)*np.exp(-0.5*((tr.total_line.values-t)/10)**2)
    d=np.bincount((tr.margin.values+70).astype(int).clip(0,140),weights=w,minlength=141); return d/d.sum()
def rescale(d,s,p):
    a=margins>s;b=margins<s;pp=d[margins==s].sum();o=d.copy();o[a]*=p*(1-pp)/d[a].sum();o[b]*=(1-p)*(1-pp)/d[b].sum();return o
K=json.load(open(W+'raw/kalshi_exact.json')); P=json.load(open(W+'raw/polymarket.json'))
pool={'BUF':16.5,'CAR':2.5,'CHI':10.5,'DAL':7.5,'DET':5.5,'KC':16.5,'JAX':6.5,'LAC':3.5,'DEN':10.5,'PIT':4.5,'SF':3.5,'CIN':4.5}
kmap={'BUF':'26NOV22MIABUF','CAR':'26NOV22BALCAR','CHI':'26NOV22NOCHI','DAL':'26NOV22TENDAL','DET':'26NOV22TBDET','KC':'26NOV22ARIKC','JAX':'26NOV22JACNYG','LAC':'26NOV22NYJLAC','DEN':'26NOV22LVDEN','PIT':'26NOV22PITPHI','SF':'26NOV22MINSF','CIN':'26NOV23CINWAS'}
rows=[]
for _,r in cur.iterrows():
    home,away=r.home_team,r.away_team
    fav=home if home in pool else away; L=pool[fav]
    homefav = fav==home
    pool_home_line = L if homefav else -L          # home must win by more than this for home side to cover (in home-margin terms)
    s=r.spread_line; t=r.total_line
    p_px=novig(r.home_spread_odds,r.away_spread_odds); p_px_sh=0.5+0.5*(p_px-0.5)   # shrink juice 50% (weak historical evidence)
    d=rescale(dist(s,t),s,p_px_sh)
    p_home_cover_book = d[margins>pool_home_line].sum()
    p_fav_book = p_home_cover_book if homefav else 1-p_home_cover_book
    k=K[kmap[fav]]['mid']
    pm=[v for v in P.values() if v['question'].endswith(f'(-{L})') ]
    # polymarket match by team name in question
    p_fav_ex=k
    for slug,v in P.items():
        if kmap[fav][7:].lower()[:3] in slug.replace('-','') or True:
            pass
    rows.append(dict(game=f'{away} at {home}',fav=fav,dog=(away if homefav else home),pool_line=L,market_spread=(s if homefav else -s),total=t,
        juice_home=r.home_spread_odds,juice_away=r.away_spread_odds,p_fav_book=p_fav_book,p_fav_kalshi=k,
        road_dog=(r.location!='Neutral' and homefav), home_dog=(r.location!='Neutral' and not homefav), neutral=r.location=='Neutral'))
R=pd.DataFrame(rows)
# Polymarket: match slugs manually by fav-line text
pm_by={}
for slug,v in P.items():
    outs=json.loads(v['outcomes']); prices=json.loads(v['outcomePrices'])
    pm_by[float(v['question'].split('(-')[1].rstrip(')'))*0+0]=None
names={'BUF':'Bills','CAR':'Panthers','CHI':'Bears','DAL':'Cowboys','DET':'Lions','KC':'Chiefs','JAX':'Jaguars','LAC':'Chargers','DEN':'Broncos','PIT':'Steelers','SF':'49ers','CIN':'Bengals'}
def pmp(f):
    for v in P.values():
        if v['question'].startswith(f'Spread: {names[f]} '):
            return (float(v['bestBid'])+float(v['bestAsk']))/2
R['p_fav_poly']=R.fav.map(pmp)
R['p_fav_exch']=(R.p_fav_kalshi+R.p_fav_poly)/2
R['p_fav_market']=0.5*R.p_fav_book+0.5*R.p_fav_exch
# road-dog prior: +0.8pp to road dog (walk-forward 2008-26 road-dog leans 51.9%, shrunk), none for home dogs / neutral
R['angle']=np.where(R.road_dog,-0.008,0.0)
R['p_fav']=R.p_fav_market+R.angle
R['pick']=np.where(R.p_fav>=0.5,R.fav,R.dog); R['p_pick']=np.maximum(R.p_fav,1-R.p_fav)
pd.set_option('display.width',250)
print(R[['game','fav','pool_line','market_spread','juice_home','juice_away','p_fav_book','p_fav_kalshi','p_fav_poly','p_fav_market','angle','p_fav','pick','p_pick']].round(3).to_string(index=False))
R.to_pickle(W+'probs.pkl')
