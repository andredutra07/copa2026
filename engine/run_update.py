#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
engine/run_update.py — ciclo de atualização (roda na GitHub Action a cada rodada).

  1) coleta tolerante a falha (placares, xG, lesões)
  2) MERGE dos placares sobre data/results.json (fonte de verdade versionada)
  3) ajustes de forma/lesão em data/adjustments.json
  4) recalibra o motor (shrinkage + congelamento), simula a Copa
  5) grava site/predictions.json (o app lê isso) e versiona os dados

Uso: python -m engine.run_update    (ou)    python engine/run_update.py
"""
import os, json, sys
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
sys.path.insert(0, ROOT)

from engine import model, scrape

DATA = os.path.join(ROOT, "data"); SITE = os.path.join(ROOT, "docs")
os.makedirs(DATA, exist_ok=True); os.makedirs(SITE, exist_ok=True)

def _write(path, obj):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False, indent=1)

def main(sims=20000):
    print("[1/5] coletando dados (tolerante a falha)…")
    base = model.load_results()
    try:    results = scrape.scrape_results(base)
    except Exception as e:  print("  resultados: fallback (", e, ")"); results = base
    print(f"      {len(results)} resultados ({len(results)-len(base)} novos)")

    print("[2/5] ajustes de forma/lesão…")
    try:    adj = scrape.collect_adjustments()
    except Exception as e:  print("  ajustes: vazio (", e, ")"); adj = {}
    # preserva ajustes manuais já existentes (do app/celular) que tenham reason 'manual'
    existing = model.load_adjustments()
    for t, d in existing.items():
        if isinstance(d, dict) and d.get("reason", "").startswith("manual"):
            adj[t] = d
    print(f"      {len(adj)} times com ajuste")

    print("[3/5] gravando dados versionados…")
    _write(os.path.join(DATA, "results.json"), results)
    _write(os.path.join(DATA, "adjustments.json"), adj)

    print("[4/5] recalibrando motor + simulando…")
    out = model.build_predictions(N=sims)

    print("[5/5] publicando predictions.json…")
    _write(os.path.join(SITE, "predictions.json"), out)
    print("OK  campeão provável:", out["champions"][0]["team"] if out["champions"] else "—",
          "| calibração log-loss=", out["calibration"]["logloss"])
    return out

if __name__ == "__main__":
    n = int(os.environ.get("SIMS", "20000"))
    main(sims=n)
