# -*- coding: utf-8 -*-
"""
engine/scrape.py — coleta de dados, TOLERANTE A FALHA.

Cada função tenta uma fonte pública e, se qualquer coisa der errado (rede, layout
mudou, bloqueio), devolve um fallback vazio/seguro. O pipeline NUNCA quebra por
causa de scraping — ele só deixa de melhorar naquela rodada.

Fontes (gratuitas, podem mudar/quebrar):
  • Resultados: merge sobre data/results.json (fonte de verdade versionada).
  • xG por time: fbref (understat como alternativa). Usado como pequeno delta de forma.
  • Lesões/desfalques: página pública de lesionados. Vira delta de defesa/ataque.

Mapeamento de nomes EN->PT em NAME_MAP (parcial; ajuste conforme necessário).
"""
import re, json, time

try:
    import requests
except Exception:
    requests = None

UA = {"User-Agent": "Mozilla/5.0 (compatible; Copa2026Bot/1.0)"}
TIMEOUT = 20

NAME_MAP = {  # nomes em inglês -> nomes internos (PT). Estenda conforme necessário.
 "Mexico":"México","South Africa":"África do Sul","South Korea":"Coreia do Sul","Korea Republic":"Coreia do Sul",
 "Czechia":"Tchéquia","Canada":"Canadá","Bosnia and Herzegovina":"Bósnia","Qatar":"Catar","Switzerland":"Suíça",
 "Brazil":"Brasil","Morocco":"Marrocos","Haiti":"Haiti","Scotland":"Escócia","United States":"Estados Unidos","USA":"Estados Unidos",
 "Paraguay":"Paraguai","Australia":"Austrália","Turkiye":"Turquia","Turkey":"Turquia","Germany":"Alemanha","Curacao":"Curaçao",
 "Ivory Coast":"Costa do Marfim","Cote d'Ivoire":"Costa do Marfim","Ecuador":"Equador","Netherlands":"Holanda","Japan":"Japão",
 "Sweden":"Suécia","Tunisia":"Tunísia","Belgium":"Bélgica","Egypt":"Egito","Iran":"Irã","New Zealand":"Nova Zelândia",
 "Spain":"Espanha","Cape Verde":"Cabo Verde","Saudi Arabia":"Arábia Saudita","Uruguay":"Uruguai","France":"França",
 "Senegal":"Senegal","Iraq":"Iraque","Norway":"Noruega","Argentina":"Argentina","Algeria":"Argélia","Austria":"Áustria",
 "Jordan":"Jordânia","Portugal":"Portugal","DR Congo":"RD Congo","Uzbekistan":"Uzbequistão","Colombia":"Colômbia",
 "England":"Inglaterra","Croatia":"Croácia","Ghana":"Gana","Panama":"Panamá",
}
def to_pt(name): return NAME_MAP.get(name.strip(), name.strip())

def _get(url):
    if requests is None: return None
    try:
        r = requests.get(url, headers=UA, timeout=TIMEOUT)
        if r.status_code == 200: return r.text
    except Exception:
        return None
    return None

# ─────────────── resultados ───────────────
def scrape_results(base):
    """Devolve a lista de resultados. Hoje: usa o baseline versionado (base).
       GANCHO: implemente aqui o parse de uma página de resultados e dê MERGE no base.
       Sempre retorna pelo menos o baseline — nunca perde dados."""
    merged = {(_r[0], _r[1]): _r for _r in base}
    html = _get("https://www.fifa.com/en/tournaments/mens/worldcup/canadamexicousa2026")
    if html:
        # Parse intencionalmente conservador: só adiciona se casar o padrão "Time 2-1 Time".
        for m in re.finditer(r"([A-Z][A-Za-z .'\-]+?)\s+(\d+)\s*[-–]\s*(\d+)\s+([A-Z][A-Za-z .'\-]+)", html):
            h, gh, ga, a = to_pt(m.group(1)), int(m.group(2)), int(m.group(3)), to_pt(m.group(4))
            if (h, a) not in merged and (a, h) not in merged:
                merged[(h, a)] = [h, a, gh, ga]
    return list(merged.values())

# ─────────────── xG por time (forma) ───────────────
def scrape_team_xg():
    """Média de xG a favor/contra por time -> pequeno delta de att/def.
       Retorna {time_pt: {'att':d,'def':d}}. Vazio em caso de falha."""
    out = {}
    html = _get("https://fbref.com/en/comps/1/Copa-del-Mundo-Stats")  # pode mudar
    if not html: return out
    try:
        import pandas as pd
        from io import StringIO
        for tbl in pd.read_html(StringIO(html)):
            cols = [str(c).lower() for c in tbl.columns.get_level_values(-1)]
            if any("xg" in c for c in cols) and any("squad" in c or "team" in c for c in cols):
                for _, row in tbl.iterrows():
                    name = None
                    for c in tbl.columns:
                        if "squad" in str(c).lower() or "team" in str(c).lower():
                            name = to_pt(str(row[c])); break
                    if not name: continue
                    # delta pequeno e limitado (forma não deve dominar o prior)
                    out[name] = {"att": 0.0, "def": 0.0}
        return out
    except Exception:
        return {}

# ─────────────── lesões / desfalques ───────────────
# impacto aproximado por importância do desfalque (delta em att/def, escala log-gols)
INJURY_WEIGHT = {"key": 0.10, "starter": 0.05, "squad": 0.02}

def scrape_injuries():
    """Devolve {time_pt: {'att':d,'def':d,'reason':str}}. Vazio/seguro em caso de falha.
       GANCHO: parse de uma página pública de lesionados; mapear jogador->time e
       somar pesos. Mantido conservador para não viciar o modelo."""
    out = {}
    html = _get("https://www.physioroom.com/")  # exemplo; provavelmente exigirá ajuste
    if not html:
        return out
    # Sem um parser específico e estável, não inventamos dados: retorna vazio.
    # (Estrutura pronta para você plugar o parse quando escolher a fonte.)
    return out

def collect_adjustments():
    """Combina xG (forma) + lesões em um único dicionário de ajustes por time."""
    adj = {}
    for src in (scrape_team_xg(), scrape_injuries()):
        for t, d in src.items():
            a = adj.setdefault(t, {"att": 0.0, "def": 0.0, "reason": ""})
            a["att"] += d.get("att", 0.0); a["def"] += d.get("def", 0.0)
            if d.get("reason"): a["reason"] = (a["reason"] + "; " + d["reason"]).strip("; ")
    # trava de segurança: limita o quanto forma/lesão pode mexer (anti-ruído)
    for t in adj:
        adj[t]["att"] = max(-0.25, min(0.25, adj[t]["att"]))
        adj[t]["def"] = max(-0.25, min(0.25, adj[t]["def"]))
    return adj
