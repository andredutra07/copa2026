# Previsor Copa 2026 ⚽📊

App de previsões da Copa do Mundo 2026 que **se atualiza sozinho a cada rodada**:
um robô (GitHub Actions) coleta placares, recalibra o motor estatístico e republica
o site. Você abre sempre o **mesmo link** no iPhone.

- **Motor:** Dixon-Coles (ataque/defesa por time + correção de empates) fundido com o
  mercado de apostas (de-vig + *log opinion pool*), simulação de Monte Carlo do torneio
  com o **chaveamento oficial** (R32 → final), calibração *out-of-sample* (walk-forward).
- **Saída:** probabilidade de cada jogo + placar mais provável (e a chance dele),
  classificação dos grupos, rota do mata-mata e % de título com **intervalo de confiança**.

> **Importante:** são **probabilidades, não cravadas**. Futebol tem alta variância; o placar
> "mais provável" de um jogo costuma valer só ~10–15%. Use como bússola. Se for apostar,
> defina um limite que você aceita perder e não persiga prejuízo.

---

## 📁 Estrutura
```
engine/      motor (model.py), Annex C, scrapers, orquestrador
data/        dados versionados: results.json, adjustments.json
docs/        o site (index.html) + predictions.json  ← GitHub Pages serve isto
.github/workflows/update.yml   o robô agendado
```

## 🚀 Setup (uma vez só)

1. **Crie um repositório** no GitHub (público, grátis) e suba estes arquivos
   (botão *Add file → Upload files*, arraste tudo, *Commit*).
2. **Ative o Pages:** *Settings → Pages → Build and deployment → Deploy from a branch*
   → Branch **main**, pasta **/docs** → *Save*. Em ~1 min seu site fica em
   `https://SEU-USUARIO.github.io/SEU-REPO/`.
3. **Ative o robô:** aba **Actions** → habilite workflows → abra
   *“Atualizar previsões Copa 2026”* → **Run workflow** (testa na hora). Depois ele roda
   sozinho nos horários do `cron` em `.github/workflows/update.yml`.
4. **No iPhone:** abra o link do Pages no **Safari** → Compartilhar →
   **Adicionar à Tela de Início**. Vira um app em tela cheia.

Pronto. A partir daí o robô atualiza e o app reflete sem você fazer nada.

## 🩹 Ajuste manual de lesão/físico (sem API paga)
Não existe feed gratuito e confiável de lesões. Para registrar um desfalque importante,
edite **`data/adjustments.json`** (no GitHub, *Edit* no arquivo):
```json
{ "Brasil": { "att": -0.08, "def": 0.0, "reason": "manual: titular fora" } }
```
- `att` negativo = ataque pior; `def` positivo = defesa pior. Faixa segura: −0.25 a +0.25.
- Entradas com `"reason": "manual..."` são **preservadas** pelo robô. Commit → próxima
  execução já considera.

## 🔧 Rodar localmente (opcional)
```bash
pip install -r requirements.txt
python engine/run_update.py      # gera docs/predictions.json
# abra docs/index.html no navegador
```

## ⚠️ Limites honestos
- **Lesões/escalações automáticas:** os scrapers são *best-effort* e toleram falha
  (se o site-fonte mudar, o robô ignora e segue). Sem fonte grátis estável, o caminho
  confiável é o ajuste manual acima.
- **xG:** entra como pequeno delta de forma quando o scraper consegue ler o fbref;
  caso contrário não atrapalha.
- **Annex C:** a alocação dos 3ºs respeita os conjuntos de grupos permitidos por slot.
  Para exatidão byte-a-byte com a tabela oficial das 495 combinações, cole-as em
  `engine/annex_c.py → OFFICIAL_TABLE`.
- **A IA não roda sozinha:** quem automatiza é o GitHub Actions. O modelo se auto-calibra
  com os resultados, mas não "pensa" entre execuções.

## 📈 Como ele melhora ao longo da Copa
Cada execução: coleta placares → recalibra (com *shrinkage*; parâmetros ficam congelados
até 24 jogos para não viciar) → mede erro **fora da amostra** (log-loss/Brier) → simula.
Quanto mais jogos, mais afiado — e a aba **Precisão** mostra isso sem maquiagem.
