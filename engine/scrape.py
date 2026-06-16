# -*- coding: utf-8 -*-
"""
engine/scrape.py — coleta de placares via WIKIPEDIA (API oficial), TOLERANTE A FALHA.
"""
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

NAME_MAP = {
 "Mexico":"México","South Africa":"África do Sul","South Korea":"Coreia do Sul","Korea Republic":"Coreia do Sul",
 "Czechia":"Tchéquia","Canada":"Canadá","Bosnia and Herzegovina":"Bósnia","Bosnia":"Bósnia","Qatar":"Catar","Switzerland":"Suíça",
 "Brazil":"Brasil","Morocco":"Marrocos","Haiti":"Haiti","Scotland":"Escócia","United States":"Estados Unidos","USA":"Estados Unidos",
 "Paraguay":"Paraguai","Australia":"Austrália","Turkey":"Turquia","Türkiye":"Turquia","Germany":"Alemanha","Curaçao":"Curaçao","Curacao":"Curaçao",
 "Ivory Coast":"Costa do Marfim","Côte d'Ivoire":"Costa do Marfim","Cote d'Ivoire":"Costa do Marfim","Ecuador":"Equador",
 "Netherlands":"Holanda","Japan":"Japão","Sweden":"Suécia","Tunisia":"Tunísia","Belgium":"Bélgica","Egypt":"Egito","Iran":"Irã","IR Iran":"Irã",
 "New Zealand":"Nova Zelândia","Spain":"Espanha","Cape Verde":"Cabo Verde","Cabo Verde":"Cabo Verde","Saudi Arabia":"Arábia Saudita",
 "Uruguay":"Uruguai","France":"França","Senegal":"Senegal","Iraq":"Iraque","Norway":"Noruega","Argentina":"Argentina","Algeria":"Argélia",
 "Austria":"Áustria","Jordan":"Jordânia","Portugal":"Portugal","DR Congo":"RD Congo","Uzbekistan":"Uzbequistão","Colombia":"Colômbia",
 "England":"Inglaterra","Croatia":"Croácia","Ghana":"Gana","Panama":"Panamá",
}

def _clean_name(s):
    s = re.sub(r"\{\{[^{}]*\}\}", "", s)
    s = re.sub(r"\[\[(?:[^\]|]*\|)?([^\]]+)\]\]", r"\1", s)
    s = s.replace("[[", "").replace("]]", "").replace("'", "")
    s = re.sub(r"<[^>]+>", "", s)
    return s.strip()

def to_pt(name):
    n = _clean_name(name)
    if n in NAME_MAP: return NAME_MAP[n]
    for en, pt in NAME_MAP.items():
        if en.lower() in n.lower(): return pt
    return None

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

def _get_wikitext(L):
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
    log = {"fonte": "wikipedia", "grupos_ok": [], "grupos_falha": [], "novos": [], "nao_mapeados": []}
    for L in GROUPS_LETTERS:
        wt = _get_wikitext(L)
        if not wt:
            log["grupos_falha"].append(L); continue
        log["grupos_ok"].append(L)
        for raw1, g1, g2, raw2 in parse_football_boxes(wt):
            h, a = to_pt(raw1), to_pt(raw2)
            if not h or not a:
                log["nao_mapeados"].append({"g": L, "t1": _clean_name(raw1), "t2": _clean_name(raw2)}); continue
            if (h, a) not in merged and (a, h) not in merged:
                merged[(h, a)] = [h, a, g1, g2]; log["novos"].append(f"{h} {g1}-{g2} {a}")
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
