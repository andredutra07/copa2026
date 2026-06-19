#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""engine/model.py — nucleo do Previsor Copa 2026 (Dixon-Coles + mercado + elenco + Monte Carlo)."""
import os, json, math, itertools
import numpy as np
from dataclasses import dataclass, field
from scipy.optimize import minimize

try:
    from . import annex_c
except Exception:
    import annex_c

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
rng = np.random.default_rng(20260614)

TEAMS = {
 'México':{'g':'A','elo':1868,'host':True},'África do Sul':{'g':'A','elo':1625},'Coreia do Sul':{'g':'A','elo':1745},'Tchéquia':{'g':'A','elo':1808},
 'Canadá':{'g':'B','elo':1731,'host':True},'Bósnia':{'g':'B','elo':1595},'Catar':{'g':'B','elo':1558},'Suíça':{'g':'B','elo':1891},
 'Brasil':{'g':'C','elo':1991},'Marrocos':{'g':'C','elo':1860},'Haiti':{'g':'C','elo':1505},'Escócia':{'g':'C','elo':1758},
 'Estados Unidos':{'g':'D','elo':1798,'host':True},'Paraguai':{'g':'D','elo':1722},'Austrália':{'g':'D','elo':1777},'Turquia':{'g':'D','elo':1880},
 'Alemanha':{'g':'E','elo':1910},'Curaçao':{'g':'E','elo':1492},'Costa do Marfim':{'g':'E','elo':1792},'Equador':{'g':'E','elo':1933},
 'Holanda':{'g':'F','elo':1959},'Japão':{'g':'F','elo':1879},'Suécia':{'g':'F','elo':1782},'Tunísia':{'g':'F','elo':1628},
 'Bélgica':{'g':'G','elo':1893},'Egito':{'g':'G','elo':1696},'Irã':{'g':'G','elo':1785},'Nova Zelândia':{'g':'G','elo':1500},
 'Espanha':{'g':'H','elo':2157},'Cabo Verde':{'g':'H','elo':1572},'Arábia Saudita':{'g':'H','elo':1620},'Uruguai':{'g':'H','elo':1890},
 'França':{'g':'I','elo':2063},'Senegal':{'g':'I','elo':1869},'Iraque':{'g':'I','elo':1565},'Noruega':{'g':'I','elo':1922},
 'Argentina':{'g':'J','elo':2115},'Argélia':{'g':'J','elo':1785},'Áustria':{'g':'J','elo':1820},'Jordânia':{'g':'J','elo':1565},
 'Portugal':{'g':'K','elo':1989},'RD Congo':{'g':'K','elo':1690},'Uzbequistão':{'g':'K','elo':1625},'Colômbia':{'g':'K','elo':1982},
 'Inglaterra':{'g':'L','elo':2024},'Croácia':{'g':'L','elo':1933},'Gana':{'g':'L','elo':1705},'Panamá':{'g':'L','elo':1730},
}
TITLE_ODDS = {
 'Espanha':450,'França':500,'Inglaterra':650,'Portugal':800,'Brasil':850,'Argentina':1000,'Alemanha':1300,
 'Holanda':1600,'Bélgica':2200,'Noruega':3300,'Colômbia':3500,'Japão':4000,'Marrocos':5000,'México':6500,
 'Uruguai':6500,'Croácia':6500,'Suíça':6500,'Estados Unidos':4000,
}
NAMES = list(TEAMS)
SQUAD_VAL = {
 'França':1520,'Inglaterra':1360,'Espanha':1220,'Portugal':1010,'Alemanha':947,'Brasil':928,'Argentina':807,
 'Holanda':754,'Noruega':590,'Bélgica':547,'Costa do Marfim':522,'Senegal':478,'Turquia':474,'Marrocos':448,
 'Suécia':406,'Croácia':387,'Estados Unidos':386,'Equador':369,'Uruguai':359,'Suíça':332,'Colômbia':302,'Japão':271,
 'Áustria':290,'Tchéquia':200,'Argélia':190,'México':180,'Escócia':180,'Egito':180,'Coreia do Sul':170,'Canadá':150,
 'Gana':150,'RD Congo':130,'Bósnia':120,'Paraguai':95,'Austrália':85,'Irã':75,'Tunísia':60,'Cabo Verde':42,
 'Uzbequistão':40,'África do Sul':40,'Nova Zelândia':30,'Haiti':30,'Arábia Saudita':30,'Curaçao':25,'Panamá':25,
 'Iraque':25,'Jordânia':22,'Catar':20,
}
GROUPS = {}
for t,d in TEAMS.items(): GROUPS.setdefault(d['g'], []).append(t)
GLET = sorted(GROUPS)
ALT_VENUE_TEAM = {'México'}

FIX = [
 (1,'11/06','México','África do Sul'),(1,'11/06','Coreia do Sul','Tchéquia'),
 (1,'12/06','Canadá','Bósnia'),(1,'12/06','Estados Unidos','Paraguai'),
 (1,'13/06','Catar','Suíça'),(1,'13/06','Brasil','Marrocos'),(1,'13/06','Haiti','Escócia'),(1,'13/06','Austrália','Turquia'),
 (1,'14/06','Alemanha','Curaçao'),(1,'14/06','Holanda','Japão'),(1,'14/06','Costa do Marfim','Equador'),(1,'14/06','Suécia','Tunísia'),
 (1,'15/06','Espanha','Cabo Verde'),(1,'15/06','Bélgica','Egito'),(1,'15/06','Arábia Saudita','Uruguai'),(1,'15/06','Irã','Nova Zelândia'),
 (1,'16/06','França','Senegal'),(1,'16/06','Iraque','Noruega'),(1,'16/06','Argentina','Argélia'),(1,'16/06','Áustria','Jordânia'),
 (1,'17/06','Portugal','RD Congo'),(1,'17/06','Inglaterra','Croácia'),(1,'17/06','Gana','Panamá'),(1,'17/06','Uzbequistão','Colômbia'),
 (2,'18/06','Tchéquia','África do Sul'),(2,'18/06','Suíça','Bósnia'),(2,'18/06','Canadá','Catar'),(2,'18/06','México','Coreia do Sul'),
 (2,'19/06','Escócia','Marrocos'),(2,'19/06','Estados Unidos','Austrália'),(2,'19/06','Brasil','Haiti'),(2,'19/06','Turquia','Paraguai'),
 (2,'20/06','Holanda','Suécia'),(2,'20/06','Alemanha','Costa do Marfim'),(2,'20/06','Equador','Curaçao'),(2,'20/06','Tunísia','Japão'),
 (2,'21/06','Espanha','Arábia Saudita'),(2,'21/06','Bélgica','Irã'),(2,'21/06','Uruguai','Cabo Verde'),(2,'21/06','Nova Zelândia','Egito'),
 (2,'22/06','Argentina','Áustria'),(2,'22/06','França','Iraque'),(2,'22/06','Noruega','Senegal'),(2,'22/06','Jordânia','Argélia'),
 (2,'23/06','Portugal','Uzbequistão'),(2,'23/06','Inglaterra','Gana'),(2,'23/06','Panamá','Croácia'),(2,'23/06','Colômbia','RD Congo'),
 (3,'24/06','Suíça','Canadá'),(3,'24/06','Bósnia','Catar'),(3,'24/06','Escócia','Brasil'),(3,'24/06','Marrocos','Haiti'),(3,'24/06','Tchéquia','México'),(3,'24/06','África do Sul','Coreia do Sul'),
 (3,'25/06','Equador','Alemanha'),(3,'25/06','Curaçao','Costa do Marfim'),(3,'25/06','Japão','Suécia'),(3,'25/06','Tunísia','Holanda'),(3,'25/06','Turquia','Estados Unidos'),(3,'25/06','Paraguai','Austrália'),
 (3,'26/06','Noruega','França'),(3,'26/06','Senegal','Iraque'),(3,'26/06','Cabo Verde','Arábia Saudita'),(3,'26/06','Uruguai','Espanha'),(3,'26/06','Egito','Irã'),(3,'26/06','Nova Zelândia','Bélgica'),
 (3,'27/06','Panamá','Inglaterra'),(3,'27/06','Croácia','Gana'),(3,'27/06','Colômbia','Portugal'),(3,'27/06','RD Congo','Uzbequistão'),(3,'27/06','Argélia','Áustria'),(3,'27/06','Jordânia','Argentina'),
]
MIN_FIT = 24

def _load(name, default):
    p = os.path.join(DATA, name)
    if os.path.exists(p):
        try:
            with open(p, encoding='utf-8') as f: return json.load(f)
        except Exception: return default
    return default

def load_results():
    return _load("results.json", [])

def load_adjustments():
    return _load("adjustments.json", {})

def american_to_prob(o): return 100.0/(o+100.0) if o>0 else (-o)/(-o+100.0)
def devig_title_probs():
    raw={t:american_to_prob(o) for t,o in TITLE_ODDS.items()}; s=sum(raw.values())
    return {t:p/s for t,p in raw.items()}

@dataclass
class DCParams:
    mu: float=0.10; home: float=0.25; rho: float=-0.08
    att: dict=field(default_factory=dict); dfn: dict=field(default_factory=dict)

def elo_market_prior():
    elos=np.array([TEAMS[t]['elo'] for t in NAMES],float)
    z_elo=(elos-elos.mean())/elos.std()
    sv=np.array([math.log(SQUAD_VAL.get(t,80)) for t in NAMES],float)
    z_sv=(sv-sv.mean())/sv.std()
    z_mkt={}
    tp=devig_title_probs()
    if tp:
        lt={t:math.log(p) for t,p in tp.items()}; v=np.array(list(lt.values()))
        z_mkt={t:(lt[t]-v.mean())/v.std() for t in lt}
    s={}
    for i,t in enumerate(NAMES):
        zm = z_mkt.get(t, z_elo[i])
        z = 0.40*z_elo[i] + 0.35*zm + 0.25*z_sv[i]
        s[t]=0.20*z
    return s

def init_params(adjust=None):
    s=elo_market_prior(); p=DCParams()
    p.att={t:s[t] for t in NAMES}; p.dfn={t:s[t] for t in NAMES}
    if adjust:
        for t,d in adjust.items():
            if t in p.att:
                p.att[t]+=d.get('att',0.0); p.dfn[t]-=d.get('def',0.0)
    return p

def lambdas(p, h, a, neutral=True, altitude=False):
    adv=0.0 if neutral else p.home
    if altitude: adv+=0.18
    lh=math.exp(p.mu+p.att[h]-p.dfn[a]+adv); la=math.exp(p.mu+p.att[a]-p.dfn[h])
    return min(lh,6.0),min(la,6.0)

def tau(x,y,lh,la,rho):
    if x==0 and y==0: return 1-lh*la*rho
    if x==0 and y==1: return 1+lh*rho
    if x==1 and y==0: return 1+la*rho
    if x==1 and y==1: return 1-rho
    return 1.0

def score_matrix(p,h,a,neutral=True,altitude=False,mx=10):
    lh,la=lambdas(p,h,a,neutral,altitude)
    ph=np.array([math.exp(-lh)*lh**i/math.factorial(i) for i in range(mx)])
    pa=np.array([math.exp(-la)*la**j/math.factorial(j) for j in range(mx)])
    M=np.outer(ph,pa)
    for i in (0,1):
        for j in (0,1): M[i,j]*=tau(i,j,lh,la,p.rho)
    return M/M.sum(), lh, la

def predict(p,h,a,neutral=True,altitude=False):
    M,lh,la=score_matrix(p,h,a,neutral,altitude)
    pH=float(np.tril(M,-1).sum()); pD=float(np.trace(M)); pA=float(np.triu(M,1).sum())
    i,j=np.unravel_index(M.argmax(),M.shape)
    hi,lo=max(int(i),int(j)),min(int(i),int(j))
    score=(hi,lo) if pH>=pA else (lo,hi)
    return dict(pH=pH,pD=pD,pA=pA,lh=lh,la=la,score=score,score_p=float(M[i,j]))

def fit_params(played, prior, ridge=8.0):
    if len(played)<MIN_FIT: return prior, False
    idx={t:k for k,t in enumerate(NAMES)}; n=len(NAMES)
    x0=np.concatenate([[prior.mu,prior.home,prior.rho],[prior.att[t] for t in NAMES],[prior.dfn[t] for t in NAMES]])
    pri=x0.copy()
    def unpack(x):
        q=DCParams(mu=x[0],home=x[1],rho=float(np.clip(x[2],-0.2,0.2)))
        q.att={t:x[3+idx[t]] for t in NAMES}; q.dfn={t:x[3+n+idx[t]] for t in NAMES}; return q
    def nll(x):
        q=unpack(x); ll=0.0
        for h,a,gh,ga,neu,alt in played:
            lh,la=lambdas(q,h,a,neu,alt)
            ll+=(gh*math.log(lh)-lh-math.lgamma(gh+1))+(ga*math.log(la)-la-math.lgamma(ga+1))
            if gh<2 and ga<2: ll+=math.log(max(tau(gh,ga,lh,la,q.rho),1e-6))
        return -ll+ridge*float(np.sum((x-pri)**2))
    r=minimize(nll,x0,method='L-BFGS-B'); return unpack(r.x), True

def light_update(prior, results, lr=0.16, K0=3.0, cap=0.22, decay=0.97):
    import collections
    sc=collections.defaultdict(float); cc=collections.defaultdict(float); gp=collections.defaultdict(float)
    n=len(results)
    def damp(g):
        return g if g<=3 else 3.0+(g-3.0)*0.4
    for i,r in enumerate(results):
        h,a,gh,ga=r[0],r[1],r[2],r[3]
        w=decay**(n-1-i)
        neu=not(TEAMS[h].get('host') or TEAMS[a].get('host')); alt=(h in ALT_VENUE_TEAM)
        lh,la=lambdas(prior,h,a,neu,alt)
        dgh,dga=damp(gh),damp(ga)
        sc[h]+=w*(dgh-lh)/(lh+1.0); cc[h]+=w*(dga-la)/(la+1.0)
        sc[a]+=w*(dga-la)/(la+1.0); cc[a]+=w*(dgh-lh)/(lh+1.0)
        gp[h]+=w; gp[a]+=w
    p=DCParams(mu=prior.mu,home=prior.home,rho=prior.rho)
    p.att=dict(prior.att); p.dfn=dict(prior.dfn)
    for t in NAMES:
        if gp.get(t,0)>0:
            p.att[t]+=max(-cap,min(cap, lr*sc[t]/(gp[t]+K0)))
            p.dfn[t]+=max(-cap,min(cap, lr*(-cc[t])/(gp[t]+K0)))
    return p

def current_params(results, adjust=None):
    prior=init_params(adjust)
    if len(results)>=MIN_FIT:
        played=[(r[0],r[1],r[2],r[3], not(TEAMS[r[0]].get('host') or TEAMS[r[1]].get('host')), r[0] in ALT_VENUE_TEAM) for r in results]
        return fit_params(played,prior)
    return light_update(prior,results), False

def walk_forward(results):
    prior=init_params(); ll=br=0.0; n=0
    for i,row in enumerate(results):
        h,a,gh,ga=row[0],row[1],row[2],row[3]
        sofar=results[:i]
        if i>=MIN_FIT:
            played=[(r[0],r[1],r[2],r[3], not(TEAMS[r[0]].get('host') or TEAMS[r[1]].get('host')), r[0] in ALT_VENUE_TEAM) for r in sofar]
            p=fit_params(played,prior)[0]
        else:
            p=light_update(prior,sofar)
        neu=not(TEAMS[h].get('host') or TEAMS[a].get('host')); alt=(h in ALT_VENUE_TEAM)
        pr=predict(p,h,a,neutral=neu,altitude=alt); pr_={'H':pr['pH'],'D':pr['pD'],'A':pr['pA']}
        out='H' if gh>ga else 'A' if ga>gh else 'D'
        ll+=-math.log(max(pr_[out],1e-9)); br+=sum((pr_[k]-(1 if k==out else 0))**2 for k in pr_); n+=1
    return dict(n=n, logloss=ll/max(n,1), brier=br/max(n,1))

def project_display(p, results):
    fixed=played_map(results)
    def exp_points(L):
        pts={t:0.0 for t in GROUPS[L]}; gd={t:0.0 for t in GROUPS[L]}
        for h,a in itertools.combinations(GROUPS[L],2):
            if (h,a) in fixed: gh,ga=fixed[(h,a)]
            elif (a,h) in fixed: ga,gh=fixed[(a,h)]
            else:
                pr=predict(p,h,a,neutral=True,altitude=(h in ALT_VENUE_TEAM))
                pts[h]+=3*pr['pH']+pr['pD']; pts[a]+=3*pr['pA']+pr['pD']
                gd[h]+=pr['lh']-pr['la']; gd[a]+=pr['la']-pr['lh']; continue
            gd[h]+=gh-ga; gd[a]+=ga-gh
            if gh>ga: pts[h]+=3
            elif ga>gh: pts[a]+=3
            else: pts[h]+=1; pts[a]+=1
        rank=sorted(GROUPS[L],key=lambda t:(pts[t],gd[t],TEAMS[t]['elo']),reverse=True)
        return rank,pts,gd
    groups={}; W={}; Ru={}; thirds=[]
    for L in GLET:
        rank,pts,gd=exp_points(L)
        groups[L]=[dict(team=t,pts=round(pts[t],1),elo=TEAMS[t]['elo']) for t in rank]
        W[L]=rank[0]; Ru[L]=rank[1]; thirds.append((L,pts[rank[2]],gd[rank[2]],rank[2]))
    thirds.sort(key=lambda x:(x[1],x[2]),reverse=True)
    third_team={x[0]:x[3] for x in thirds[:8]}
    slot_group=annex_c.allocate(sorted(third_team))
    def tie(A,B,label=None):
        pr=predict(p,A,B,neutral=True); aw=pr['pH']>=pr['pA']; w=A if aw else B
        hi,lo=max(pr['score']),min(pr['score']); sc=[hi,lo] if aw else [lo,hi]
        pen=(pr['pH']>0.40 and pr['pA']>0.40 and abs(pr['pH']-pr['pA'])<0.06)
        return dict(A=A,B=B,winner=w,score=sc,pW=round(max(pr['pH'],pr['pA'])/(pr['pH']+pr['pA']),3),pen=pen,label=label)
    bracket=[]
    for i,pair in enumerate(annex_c.R32):
        teams=[]
        for j,s in enumerate(pair):
            if s[0]=='W': teams.append(W[s[1]])
            elif s[0]=='R': teams.append(Ru[s[1]])
            else:
                g=slot_group.get((i,j)); teams.append(third_team.get(g, Ru[GLET[(i+j)%12]]))
        bracket.append(tuple(teams))
    rounds=[]; names=['Round of 32','Oitavas de final','Quartas de final','Semifinais']
    cur=bracket
    for nm in names:
        ties=[tie(A,B) for A,B in cur]; rounds.append(dict(name=nm,ties=ties))
        nxt=[t['winner'] for t in ties]; cur=[(nxt[k],nxt[k+1]) for k in range(0,len(nxt),2)]
    fin=[cur[0][0],cur[0][1]] if cur else []
    semis=rounds[-1]['ties']; losers=[t['B'] if t['winner']==t['A'] else t['A'] for t in semis]
    fteam=tie(fin[0],fin[1],'Final') if len(fin)==2 else None
    third=tie(losers[0],losers[1],'3º lugar') if len(losers)==2 else None
    rounds.append(dict(name='Final & 3º lugar',ties=[x for x in (third,fteam) if x]))
    champion=fteam['winner'] if fteam else None
    return groups, rounds, champion

def wilson_ci(k,n,z=1.96):
    if n==0: return (0.0,0.0)
    ph=k/n; d=1+z*z/n; c=(ph+z*z/(2*n))/d
    half=z*math.sqrt(ph*(1-ph)/n+z*z/(4*n*n))/d
    return (max(0,c-half),min(1,c+half))

def played_map(results):
    m={}
    for row in results:
        h,a,gh,ga=row[0],row[1],row[2],row[3]; m[(h,a)]=(gh,ga); m[(a,h)]=(ga,gh)
    return m

def sim_group(p,L,fixed):
    pts={t:0 for t in GROUPS[L]}; gd=dict(pts); gf=dict(pts)
    for h,a in itertools.combinations(GROUPS[L],2):
        if (h,a) in fixed: gh,ga=fixed[(h,a)]
        elif (a,h) in fixed: ga,gh=fixed[(a,h)]
        else:
            lh,la=lambdas(p,h,a,True,h in ALT_VENUE_TEAM); gh,ga=rng.poisson(lh),rng.poisson(la)
        gf[h]+=gh; gd[h]+=gh-ga; gf[a]+=ga; gd[a]+=ga-gh
        if gh>ga: pts[h]+=3
        elif ga>gh: pts[a]+=3
        else: pts[h]+=1; pts[a]+=1
    rank=sorted(GROUPS[L],key=lambda t:(pts[t],gd[t],gf[t],rng.random()),reverse=True)
    return rank,pts,gd,gf

def ko_winner(p,A,B):
    lh,la=lambdas(p,A,B,True); gh,ga=rng.poisson(lh),rng.poisson(la)
    if gh>ga: return A
    if ga>gh: return B
    pa=0.5+max(-0.12,min(0.12,(p.att[A]+p.dfn[A]-p.att[B]-p.dfn[B])*0.5))
    return A if rng.random()<pa else B

def simulate(p, results, N=20000):
    fixed=played_map(results); champ={t:0 for t in NAMES}; adv={t:0 for t in NAMES}
    for _ in range(N):
        W={}; Ru={}; thirds=[]
        for L in GLET:
            rank,pts,gd,gf=sim_group(p,L,fixed); W[L]=rank[0]; Ru[L]=rank[1]
            thirds.append((L,pts[rank[2]],gd[rank[2]],gf[rank[2]],rank[2]))
        thirds.sort(key=lambda x:(x[1],x[2],x[3],rng.random()),reverse=True)
        best=thirds[:8]; third_team={x[0]:x[4] for x in best}
        for t in list(W.values())+list(Ru.values())+list(third_team.values()): adv[t]+=1
        slot_group=annex_c.allocate(sorted(third_team))
        bracket=[]
        for i,pair in enumerate(annex_c.R32):
            teams=[]
            for j,s in enumerate(pair):
                if s[0]=='W': teams.append(W[s[1]])
                elif s[0]=='R': teams.append(Ru[s[1]])
                else:
                    g=slot_group.get((i,j)); teams.append(third_team.get(g, Ru[GLET[(i+j)%12]]))
            bracket.append(tuple(teams))
        rnd=[ko_winner(p,A,B) for A,B in bracket]
        while len(rnd)>1: rnd=[ko_winner(p,rnd[k],rnd[k+1]) for k in range(0,len(rnd),2)]
        champ[rnd[0]]+=1
    return champ,adv,N

def build_predictions(N=20000):
    import datetime
    results=load_results(); adjust=load_adjustments()
    p,fitted=current_params(results, adjust)
    prior=init_params(adjust)
    wf=walk_forward(results)
    champ,adv,n=simulate(p,results,N)
    tp=devig_title_probs()
    matches=[]
    for r,d,h,a in FIX:
        rec=next((x for x in results if (x[0],x[1])==(h,a) or (x[0],x[1])==(a,h)), None)
        neu=not(TEAMS[h].get('host') or TEAMS[a].get('host')); alt=(h in ALT_VENUE_TEAM)
        pr=predict(p,h,a,neutral=neu,altitude=alt)
        item=dict(round=r,date=d,home=h,away=a,
                  pH=round(pr['pH'],4),pD=round(pr['pD'],4),pA=round(pr['pA'],4),
                  score=list(pr['score']),score_p=round(pr['score_p'],4),played=False)
        if rec:
            gh,ga=(rec[2],rec[3]) if (rec[0],rec[1])==(h,a) else (rec[3],rec[2])
            item.update(played=True,real=[gh,ga])
        matches.append(item)
    w_model,w_mkt=0.55,0.45
    champ_out=[]
    for t in NAMES:
        if champ[t]<=0: continue
        prob=champ[t]/n; lo,hi=wilson_ci(champ[t],n)
        mk=tp.get(t); ens=w_model*prob+w_mkt*(mk if mk else prob)
        champ_out.append(dict(team=t,model=round(prob,4),lo=round(lo,4),hi=round(hi,4),
                              market=(round(mk,4) if mk else None),ensemble=round(ens,4)))
    champ_out=sorted(champ_out,key=lambda c:c['ensemble'],reverse=True)[:16]
    adv_out=[dict(team=t,p=round(adv[t]/n,4)) for t in sorted(NAMES,key=lambda t:adv[t],reverse=True)[:16]]
    groups, knockout, champion_proj = project_display(p, results)
    return dict(
        generated_at=datetime.datetime.now(datetime.timezone.utc).isoformat(),
        sims=n, params=dict(mu=round(p.mu,4),home=round(p.home,4),rho=round(p.rho,4),fitted=fitted,min_fit=MIN_FIT),
        calibration=dict(n=wf['n'],logloss=round(wf['logloss'],3),brier=round(wf['brier'],3)),
        adjustments=adjust, matches=matches, champions=champ_out, advance=adv_out,
        groups=groups, knockout=knockout, champion_proj=champion_proj,
        ratings={t:round(TEAMS[t]['elo'],0) for t in NAMES},
    )

if __name__=='__main__':
    out=build_predictions(N=8000)
    print(json.dumps(out, ensure_ascii=False, indent=1)[:1200], "...")
