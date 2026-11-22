# Parse live standings + posted Week 11 cards (names kept in memory only; saved output is anonymous ids)
import re,html,json,numpy as np,pandas as pd
P='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/pool/'
W='/tmp/claude-0/-home-user-Justin/bd92ee02-4857-5c71-ab61-ff408eafe9a7/scratchpad/model/'
def rows(f):
    t=open(P+f,encoding='latin-1').read(); t=re.sub(r'<script.*?</script>','',t,flags=re.S|re.I)
    return [[re.sub(r'\s+',' ',html.unescape(re.sub(r'<[^>]+>','',c))).strip() for c in re.findall(r'<t[dh][^>]*>(.*?)</t[dh]>',r,flags=re.S|re.I)] for r in re.findall(r'<tr[^>]*>(.*?)</tr>',t,flags=re.S|re.I)]
# standings: fixed-width PRE block
t=open(P+'season.htm',encoding='latin-1').read()
st=[]
for line in html.unescape(re.sub(r'<[^>]+>','',t)).splitlines():
    m=re.match(r'^\s*(\d+)\s+(.+?)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.]+)\s+([\d.]+)\s+(\d+)\s+(\d+)\s+(\d+)\s+\S+\s*$',line)
    if m: st.append((int(m[1]),m[2].strip(),int(m[3]),int(m[4]),float(m[7])))
S=pd.DataFrame(st,columns=['pos','name','w','l','tbavg'])
print('standings rows',len(S), S.head(3).to_dict('records'), S[S.name=='Justin Time'].to_dict('records'))
R=rows('picks.htm'); fav=[c.upper() for c in R[1][2:14]]; dog=[c.upper() for c in R[3][2:14]]
cards={}
for r in R[5:]:
    if len(r)>=17 and r[0] and all(r[2:14]) and r[14]:
        cards[r[0]]=([1 if c.upper()==fav[k] else 0 for k,c in enumerate(r[2:14])],int(r[14]))
print('posted cards',len(cards),'justin posted?', 'Justin Time' in cards)
S['posted']=S.name.isin(cards)
print('top-30 posted:',S.head(30).posted.sum(), ' unposted top-15:', S[(S.pos<=15)&~S.posted].pos.tolist())
fav_pick=np.array([cards[n][0] if n in cards else [-1]*12 for n in S.name])
tb=np.array([cards[n][1] if n in cards else -1 for n in S.name])
np.savez(W+'field.npz',w=S.w.values,tbavg=S.tbavg.values,pos=S.pos.values,is_justin=(S.name=='Justin Time').values,fav_pick=fav_pick,tb=tb,fav=np.array(fav),dog=np.array(dog))
