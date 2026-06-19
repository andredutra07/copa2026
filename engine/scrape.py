# -*- coding: utf-8 -*-
"""engine/scrape.py — coleta de placares, TOLERANTE A FALHA. Fontes: TheSportsDB (JSON) + Wikipedia (reserva)."""
import re, json, os
try:
    import requests
except Exception:
    requests = None

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
UA = {"User-Agent": "Copa2026Bot/1.0 (uso pessoal; via GitHub)"}
TIMEOUT = 25
GROUPS_LETTERS = list("ABCDEFGHIJKL")

TSDB_KEY = "3"
TSDB_LEAGUE = "4429"
TSDB_SEASONS = ["2025-2026", "2026"]
INPLAY = {"1H","2H","HT","ET","LIVE","Live","Halftime","First Half","Second Half"}
NOTSTARTED = {"NS","Not Started",""}

NAME_MAP = {
 "Mexico":"México","South Africa":"África do Sul","South Korea":"Coreia do Sul","Korea Republic":"Coreia do Sul",
 "Czechia":"Tchéquia","Czech Republic":"Tchéquia","Canada":"Canadá","Bosnia and Herzegovina":"Bósnia","Bosnia":"Bósnia",
 "Qatar":"Catar","Switzerland":"Suíça","Brazil":"Brasil","Morocco":"Marrocos","Haiti":"Haiti","Scotland":"Escócia",
 "United States":"Estados Unidos","USA":"Estados Unidos","Paraguay":"Paraguai","Australia":"Austrália","Turkey":"Turquia","Türkiye":"Turquia",
 "Germany":"Alemanha","Curaçao":"Curaçao","Curacao":"Curaçao","Ivory Coast":"Costa do Marfim","Côte d'Ivoire":"Costa do Marfim","Cote d'Ivoire":"Costa do Marfim",
 "Ecuador":"Equador","Netherlands":"Holanda","Japan":"Japão","Sweden":"Suécia","Tunisia":"Tunísia","Belgium":"Bélgica","Egypt":"Egito",
 "Iran":"Irã","IR Iran":"Irã","New Zealand":"Nova Zelândia","Spain":"Espanha","Cape Verde":"Cabo Verde","Cabo Verde":"Cabo Verde",
 "Saudi Arabia":"Arábia Saudita","Uruguay":"Uruguai","France":"França","Senegal":"Senegal","Iraq":"Iraque","Norway":"Noruega",
 "Argentina":"Argentina","Algeria":"Argélia","Austria":"Áustria","Jordan":"Jordânia","Portugal":"Portugal","DR Congo":"RD Congo",
 "Democratic Republic of the Congo":"RD Congo","Congo DR":"RD Congo","Uzbekistan":"Uzbequistão","Colombia":"Colômbia",
 "England":"Inglaterra","Croatia":"Croácia","Ghana":"Gana","Panama":"Panamá",
}

def to_pt(name):
    if not name: return None
    n = name.strip()
    if n in NAME_MAP: return NAME_MAP[n]
    for en, pt in NAME_MAP.items():
        if en.lower() in n.lower(): return pt
    return None

def _intval(x):
    try:
        if x is None or str(x).strip() == "": return None
        return int(str(x).strip())
    except Exception:
        return None

def parse_tsdb_events(events):
    out = []
    for ev in events or []:
        hs, as_ = _intval(ev.get("intHomeScore")), _intval(ev.get("intAwayScore"))
        status = (ev.get("strStatus") or "").strip()
        if hs is None or as_ is None: continue
        if status in INPLAY or status in NOTSTARTED: continue
        h, a = to_pt(ev.get("strHomeTeam")), to_pt(ev.get("strAwayTeam"))
        if h and a:
            out.append((h, a, hs, as_, status, ev.get("strHomeTeam"), ev.get("strAwayTeam")))
    return out

def _tsdb_fetch():
    if requests is None: return None
    url = f"https://www.thesportsdb.com/api/v1/json/{TSDB_KEY}/eventsseason.php"
    all_ev = []; ok = False
    for season in TSDB_SEASONS:
        try:
            r = requests.get(url, params={"id": TSDB_LEAGUE, "s": season}, headers=UA, timeout=TIMEOUT)
            if r.status_code != 200: continue
            ev = r.json().get("events")
            if ev:
                ok = True; all_ev.extend(ev)
        except Exception:
            continue
    return all_ev if ok else None

def _clean_name(s):
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", s)
    s = s.replace("[[", "").replace("]]", "").replace("'", "")
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()

def parse_football_boxes(wikitext):
    out = []
    for blk in re.split(r"\{\{\s*[Ff]ootball box", wikitext)[1:]:
        blk = blk.split("}}")[0] if "}}" in blk else blk
        t1 = re.search(r"team1\s*=\s*([^\n|]+)", blk)
        sc = re.search(r"score\s*=\s*(\d+)\s*[\u2013\-:]\s*(\d+)", blk)
        t2 = re.search(r"team2\s*=\s*([^\n|]+)", blk)
        if t1 and sc and t2:
            out.append((t1.group(1), int(sc.group(1)), int(sc.group(2)), t2.group(1)))
    return out

def _wiki_fetch(L):
    if requests is None: return None
    try:
        r = requests.get("https://en.wikipedia.org/w/index.php",
                         params={"title": f"2026_FIFA_World_Cup_Group_{L}", "action": "raw"},
                         headers=UA, timeout=TIMEOUT)
        return r.text if r.status_code == 200 else None
    except Exception:
        return None

def scrape_results(base):
    merged = {(r[0], r[1]): list(r) for r in base}
    log = {"fonte_primaria": "thesportsdb", "tsdb_eventos": 0, "tsdb_finalizados": 0,
           "wiki_grupos_ok": [], "novos": [], "nao_mapeados": [], "erro": None}
    def add(h, a, gh, ga):
        if (h, a) not in merged and (a, h) not in merged:
            merged[(h, a)] = [h, a, gh, ga]; log["novos"].append(f"{h} {gh}-{ga} {a}")
    events = _tsdb_fetch()
    if events is not None:
        log["tsdb_eventos"] = len(events)
        fin = parse_tsdb_events(events)
        log["tsdb_finalizados"] = len(fin)
        for h, a, gh, ga, status, rh, ra in fin:
            add(h, a, gh, ga)
        for ev in events:
            if to_pt(ev.get("strHomeTeam")) is None or to_pt(ev.get("strAwayTeam")) is None:
                log["nao_mapeados"].append({"h": ev.get("strHomeTeam"), "a": ev.get("strAwayTeam")})
    else:
        log["erro"] = "tsdb_indisponivel"
    if not log["novos"]:
        for L in GROUPS_LETTERS:
            wt = _wiki_fetch(L)
            if not wt: continue
            log["wiki_grupos_ok"].append(L)
            for raw1, g1, g2, raw2 in parse_football_boxes(wt):
                h, a = to_pt(_clean_name(raw1)), to_pt(_clean_name(raw2))
                if h and a: add(h, a, g1, g2)
    log["nao_mapeados"] = log["nao_mapeados"][:20]
    try:
        with open(os.path.join(DATA, "scrape_log.json"), "w", encoding="utf-8") as f:
            json.dump(log, f, ensure_ascii=False, indent=1)
    except Exception:
        pass
    return [tuple(v) for v in merged.values()]

def scrape_team_xg(): return {}
def scrape_injuries(): return {}
def collect_adjustments():
    adj = {}
    for src in (scrape_team_xg(), scrape_injuries()):
        for t, d in src.items():
            a = adj.setdefault(t, {"att":0.0,"def":0.0,"reason":""})
            a["att"]+=d.get("att",0.0); a["def"]+=d.get("def",0.0)
    for t in adj:
        adj[t]["att"]=max(-0.25,min(0.25,adj[t]["att"])); adj[t]["def"]=max(-0.25,min(0.25,adj[t]["def"]))
    return adj
