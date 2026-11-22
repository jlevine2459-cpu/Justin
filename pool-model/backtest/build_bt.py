import json,urllib.request,ssl,urllib.parse,os,datetime as dt,pandas as pd,numpy as np
from zoneinfo import ZoneInfo
ET=ZoneInfo('America/New_York')
ctx=ssl.create_default_context(cafile='/root/.ccr/ca-bundle.crt')
def get(u): return json.load(urllib.request.urlopen(urllib.request.Request(u,headers={'User-Agent':'pool-model/1.0'}),timeout=60,context=ctx))
SRC='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/zip/levine-pool-desk-v28/source/data/'
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
weeks=json.load(open(SRC+'weeks.json'))
G=pd.read_csv(W+'raw/games.csv'); G=G[G.season==2026].set_index('game_id')
mk={x['ticker']:x for x in json.load(open('kalshi_markets_all.json'))}
evs={}
for t,x in mk.items(): evs.setdefault(x['event_ticker'],[]).append(t)
KC={'JAX':'JAC'}
os.makedirs('candles',exist_ok=True)
def kal_price(ticker,cutoff):
    f=f'candles/{ticker}.json'
    tier=mk[ticker]['_tier']
    q=urllib.parse.urlencode({'start_ts':cutoff-7200,'end_ts':cutoff,'period_interval':60})
    url=(f'https://api.elections.kalshi.com/trade-api/v2/historical/markets/{ticker}/candlesticks?'+q) if tier=='historical/' else (f'https://api.elections.kalshi.com/trade-api/v2/markets/candlesticks?'+q+'&market_tickers='+ticker)
    if not os.path.exists(f):
        try: json.dump(get(url),open(f,'w'))
        except Exception as e: return None,str(e)
    d=json.load(open(f)); cs=d.get('candlesticks') or (d.get('markets') or [{}])[0].get('candlesticks',[])
    best=None
    for c in cs:
        if c['end_period_ts']>cutoff: continue
        yb=c.get('yes_bid',{}); ya=c.get('yes_ask',{})
        b=yb.get('close_dollars') or yb.get('close'); a=ya.get('close_dollars') or ya.get('close')
        if b is None or a is None: continue
        b=float(b);a=float(a)
        if b>1: b/=100;a/=100
        if best is None or c['end_period_ts']>best[0]: best=(c['end_period_ts'],b,a)
    if not best: return None,'no candle'
    return best,None
rows=[]
for w in weeks:
    if w['week']>10: continue
    for gm in w['games']:
        gid=gm['game_id']; r=G.loc[gid] if gid in G.index else G.loc[gid.replace('LAR','LA')]
        home,away=gm['home'],gm['away']; L=gm['pool_home_spread']   # home gets L points (negative = home favored)
        margin=r.home_score-r.away_score
        home_cov=float(margin+L>0)
        # lock: Sunday 13:00 ET of that week, or kickoff if earlier
        ko=dt.datetime.fromisoformat(f"{r.gameday}T{r.gametime}").replace(tzinfo=ET)
        sun=dt.datetime.fromisoformat(w['deadline']).astimezone(ET)
        cutoff=int(min(ko,sun).timestamp())-300
        # Kalshi: fav team wins by over |L|
        fav=home if L<0 else away; absL=abs(L)
        yy=dt.date.fromisoformat(r.gameday)
        ev=None
        for A in {KC.get(away,away),{'LAR':'LA'}.get(away,away)}:
            for H in {KC.get(home,home),{'LAR':'LA'}.get(home,home)}:
                cand=f"KXNFLSPREAD-{yy:%y}{yy:%b}{yy:%d}".upper()+f"{A}{H}"
                if cand in evs: ev=cand
        kp=None;err='no event'
        if ev:
            t=f"{ev}-{KC.get(fav,fav)}{int(absL+0.5)}"
            if t not in mk: t=f"{ev}-LA{int(absL+0.5)}" if fav=='LAR' else t
            if t not in mk: 
                alt=[x for x in evs[ev] if x.split('-')[-1].rstrip('0123456789')!=KC.get(fav,fav)]
                err='no exact line'
            else:
                kp,err=kal_price(t,cutoff)
        p_fav_k=(kp[1]+kp[2])/2 if kp else np.nan
        p_home_k = p_fav_k if fav==home else 1-p_fav_k
        cg_pick=gm['pick']; cg_p=gm['probability']
        cg_p_home = cg_p if cg_pick==home else 1-cg_p
        strat={k:{p['game']:p['pick'] for p in w['strategies'][k]['picks']} for k in ('season','balanced','weekly')}
        rows.append(dict(week=w['week'],game_id=gid,home=home,away=away,neutral=r.location=='Neutral',pool_home=L,margin=margin,home_cov=home_cov,push=(margin+L==0),
            snap_mkt_home_margin=gm['market_home_margin'],snap_total=gm['market_total'],snap_ho=gm['home_spread_odds'],snap_ao=gm['away_spread_odds'],asOf=w['asOf'],
            close_spread=r.spread_line,close_total=r.total_line,close_ho=r.home_spread_odds,close_ao=r.away_spread_odds,
            cg_p_home=cg_p_home,cg_season=strat['season'].get(f"{away} at {home}"),cg_bal=strat['balanced'].get(f"{away} at {home}"),cg_week=strat['weekly'].get(f"{away} at {home}"),
            k_p_home=p_home_k,k_err=err if not kp else None,k_bidask=(kp[2]-kp[1]) if kp else np.nan,cutoff=cutoff))
B=pd.DataFrame(rows); B.to_pickle('bt.pkl')
print(len(B),'games; kalshi coverage',B.k_p_home.notna().sum()); print(B.k_err.value_counts(dropna=False))
print(B.groupby('week').asOf.first().to_dict())
