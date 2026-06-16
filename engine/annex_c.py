# -*- coding: utf-8 -*-
"""
engine/annex_c.py — Chaveamento oficial do Round of 32 (formato 48 times).

A FIFA fixa os confrontos de 1º e 2º colocados, e aloca os 8 melhores 3ºs a slots
específicos conforme DE QUAIS GRUPOS eles vêm (Anexo C / Annex C das regras — 495
combinações possíveis de 8 grupos entre 12).

Aqui implementamos:
  • a grade oficial de slots 1º/2º (publicada);
  • os CONJUNTOS DE GRUPOS PERMITIDOS por slot de 3º (publicados);
  • uma alocação determinística que respeita esses conjuntos (casamento bipartido).

Para ficar IDÊNTICO byte-a-byte à tabela oficial, basta colar as 495 linhas
oficiais em OFFICIAL_TABLE (formato {frozenset_de_grupos: {(i,j): 'GRUPO'}}).
Enquanto isso não é colado, usamos a alocação por restrição — que respeita as
mesmas regras de elegibilidade e coincide com a tabela na grande maioria dos casos.
"""

# slot = ('W', grupo) | ('R', grupo) | ('T3', 'conjunto de grupos permitidos')
R32 = [
 (('R','A'),('R','B')),
 (('W','C'),('R','F')),
 (('W','E'),('T3','ABCDF')),
 (('W','F'),('R','C')),
 (('R','E'),('R','I')),
 (('W','I'),('T3','CDFGH')),
 (('W','A'),('T3','CEFHI')),
 (('W','L'),('T3','EHIJK')),
 (('W','G'),('T3','AEHIJ')),
 (('W','D'),('T3','BEFIJ')),
 (('W','B'),('R','G')),
 (('W','J'),('R','H')),
 (('W','K'),('T3','ADGHL')),
 (('W','H'),('T3','BDGKL')),
 (('R','D'),('R','J')),
 (('R','K'),('R','L')),
]

# Cole aqui a tabela oficial se quiser exatidão byte-a-byte. Ex.:
# OFFICIAL_TABLE = { frozenset('ABCDEFGH'): {(2,1):'A',(5,1):'C', ...}, ... }
OFFICIAL_TABLE = {}

_T3_SLOTS = [((i,j), set(s[1])) for i,pair in enumerate(R32) for j,s in enumerate(pair) if s[0]=='T3']

def allocate(third_groups):
    """Recebe a lista de grupos cujos 3ºs avançaram (até 8) e devolve {(i,j): grupo}."""
    key = frozenset(third_groups)
    if key in OFFICIAL_TABLE:
        return dict(OFFICIAL_TABLE[key])
    # alocação por restrição (mais restritos primeiro), determinística
    order = sorted(range(len(_T3_SLOTS)), key=lambda k: len(_T3_SLOTS[k][1]))
    res = {}
    def bt(k, avail):
        if k == len(order):
            return True
        pos, allowed = _T3_SLOTS[order[k]]
        for g in sorted(avail):
            if g in allowed:
                res[pos] = g
                if bt(k+1, avail - {g}):
                    return True
                del res[pos]
        if bt(k+1, avail):   # permite slot vazio (se < 8 terceiros)
            return True
        return False
    bt(0, set(third_groups))
    return res
