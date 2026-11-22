import pandas as pd, numpy as np, sys
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
g=pd.read_csv(W+'raw/games.csv')
g=g[(g.game_type=='REG')&g.result.notna()&g.spread_line.notna()&g.total_line.notna()].copy()
g['margin']=g.result  # home - away
print(len(g), g.season.min(), g.season.max())
def novig(a,b):
    ia=np.where(a<0,-a/(-a+100),100/(a+100)); ib=np.where(b<0,-b/(-b+100),100/(b+100)); return ia/(ia+ib)
g['p_home_cov_px']=novig(g.home_spread_odds,g.away_spread_odds)
print('spread odds coverage', g.home_spread_odds.notna().groupby(g.season).mean().tail(22).round(2).to_dict())
g.to_pickle(W+'hist.pkl')
