# US-06 — Dashboard de Análise

## Objetivo

Fornecer visualizações interativas com Plotly em três seções distintas:
1. **Visão Geral (Global)** — métricas de todos os vídeos e todos os anotadores
2. **Por Vídeo** — métricas de um vídeo específico, com dados de todos os anotadores
3. **Meu Progresso** — métricas exclusivas do pesquisador autenticado

O dashboard é somente leitura e reflete o estado atual do banco em tempo real.

---

## Referência visual

O dashboard atual (protótipo) já implementa a seção "Visão Geral" com:
- 5 KPI cards: Datasets, Total de Comentários, Humanos, Bots Detectados, Conflitos
- Donut chart: Distribuição Global (Humano / Bot / Conflito) com total no centro
- Bar chart: Comparativo por Dataset (barras agrupadas por Humano / Bot / Conflito)
- Tabela: "Todos os Comentários Bot" com colunas Dataset, Autor, Comentário, Concord. (%) e filtros

Esta implementação deve ser **preservada e expandida** — não substituída.

---

## Regras de negócio

- Três seções navegáveis (abas ou sidebar)
- **Visão Geral** e **Por Vídeo**: dados de todos os anotadores — sem expor nomes individualmente nos gráficos
- **Meu Progresso**: exclusivo do pesquisador autenticado
- Gráficos gerados pelo backend via Plotly (Python) e enviados como JSON de figura
- Dados em tempo real — sem cache agressivo
- Agreement rate = proporção de comentários com 2 anotações em consenso / total com 2 anotações

---

## Seção 1 — Visão Geral (Global)

### KPI Cards (linha superior)

| Card                  | Valor                          | Cor/destaque         |
|-----------------------|--------------------------------|----------------------|
| Datasets              | nº total de datasets           | neutro               |
| Total de Comentários  | total anotado em todos datasets| neutro               |
| Humanos               | total com label `humano`       | verde                |
| Bots Detectados       | total com label `bot`          | vermelho             |
| Conflitos             | total de conflitos             | amarelo              |
| **[novo]** Agreement Rate | % de concordância geral   | azul                 |
| **[novo]** Conflitos Pendentes | nº ainda não resolvidos | laranja            |

### Gráficos

**Distribuição Global** (já existe — manter)
- Tipo: Donut chart (Plotly `Pie` com `hole=0.5`)
- Fatias: Humano (verde), Bot (vermelho), Conflito (amarelo)
- Centro: total de comentários
- Legenda com contagem absoluta e percentual

**Comparativo por Dataset** (já existe — manter e melhorar)
- Tipo: Bar chart agrupado ou empilhado (Plotly `Bar`, `barmode="group"`)
- Eixo X: nome do dataset (nome do vídeo)
- Séries: Humano, Bot, Conflito
- Tooltip: valor absoluto + percentual

**[novo] Evolução das Anotações ao Longo do Tempo**
- Tipo: Line chart (Plotly `Scatter`, `mode="lines+markers"`)
- Eixo X: data (agrupado por dia)
- Eixo Y: nº de anotações realizadas naquele dia
- Útil para acompanhar ritmo da pesquisa

**[novo] Taxa de Bots por Dataset**
- Tipo: Bar chart horizontal (Plotly `Bar`, `orientation="h"`)
- Eixo Y: nome do dataset
- Eixo X: percentual de bots (bot_count / total_annotated * 100)
- Cor condicional: vermelho se > threshold (ex: 10%)

### Filtro por Critério de Limpeza (Visão Geral)

Barra de filtro acima dos gráficos e da tabela que permite segmentar os dados por critério usado na US-03:

```
Grupo 1 — Numérico:   [x] Percentil  [x] Média  [ ] Moda  [ ] Mediana
Grupo 2 — Comportamental: [x] Curtos  [ ] Intervalo  [x] Idênticos  [ ] Perfil
                                                          [Limpar filtros]
```

- Checkboxes independentes por critério — múltipla seleção
- Filtro afeta: KPI cards, todos os gráficos e a tabela de bots
- Quando nenhum filtro ativo: exibe todos os datasets (comportamento padrão)
- Quando filtros ativos: exibe apenas datasets cujo `criteria_applied` contenha **todos** os critérios marcados (interseção)

**[novo] Gráfico: Eficácia por Critério de Limpeza**
- Tipo: Bar chart agrupado (Plotly `Bar`, `barmode="group"`)
- Eixo X: critérios (`percentil`, `media`, `moda`, `mediana`, `curtos`, `intervalo`, `identicos`, `perfil`)
- Séries: nº de datasets que usam aquele critério (barra cinza) + taxa média de bots nos datasets com aquele critério (barra vermelha, eixo Y secundário em %)
- Permite comparar qual critério de limpeza tende a capturar mais bots
- Agrupado visualmente: Grupo 1 (numérico) separado do Grupo 2 (comportamental) por linha divisória

### Tabela "Todos os Comentários Bot" (já existe — expandir)

Colunas atuais: Dataset, Autor, Comentário, Concord. (%)
Colunas a adicionar:
- **Status**: badge `Pendente` / `Resolvido` (para conflitos)
- **Anotadores**: quantos anotaram aquele comentário
- **Critérios**: badges com os critérios de limpeza que flagaram aquele usuário (ex: `percentil`, `curtos`)

Filtros atuais: texto, dataset, autor, anotador — manter todos.
Filtro adicional: **Critério de limpeza** — multi-select com os 8 critérios da US-03.

---

## Seção 2 — Por Vídeo

Ativada ao selecionar um vídeo no dropdown ou na sidebar.

### KPI Cards

| Card                     | Valor                                         |
|--------------------------|-----------------------------------------------|
| Comentários Coletados    | total bruto da coleta (US-02)                 |
| Comentários no Dataset   | após limpeza (US-03)                          |
| Anotados                 | com pelo menos uma anotação                   |
| Bots                     | com label `bot` (consenso ou resolução admin) |
| Humanos                  | com label `humano`                            |
| Agreement Rate           | % de consenso neste vídeo especificamente     |
| Conflitos Pendentes      | sem resolução do admin                        |

### Filtro por Critério de Limpeza (Por Vídeo)

Mesma barra de filtro da Visão Geral, mas aplicada apenas aos datasets deste vídeo.
Particularmente útil aqui: o mesmo vídeo pode ter datasets gerados com critérios diferentes
(ex: `dQw4w9_percentil` vs `dQw4w9_media`), permitindo comparar diretamente os resultados.

### Gráficos

**Distribuição deste Vídeo**
- Mesmo donut da visão geral, mas filtrado para o vídeo selecionado

**Comparativo por Dataset do Vídeo**
- Bar chart dos datasets gerados para este vídeo (ex: `abc123_percentil`, `abc123_media`)
- Eixo X: nome do dataset — sufixo indica o critério usado (ex: `_percentil`, `_media`)
- Séries: Humano, Bot, Conflito
- Facilita comparar qual critério de limpeza produziu mais bots para este vídeo específico

**[novo] Taxa de Bots por Critério — este Vídeo**
- Tipo: Bar chart horizontal
- Eixo Y: critério de limpeza usado
- Eixo X: % de bots no dataset gerado por aquele critério
- Exibe apenas critérios que geraram pelo menos um dataset para este vídeo

**Timeline de Comentários Coletados**
- Tipo: Bar chart ou Line chart com granularidade configurável (hora / dia / semana)
- Eixo X: data/hora
- Eixo Y: nº de comentários postados naquele período
- Útil para identificar rafadas de postagem (padrão de bot)

**Distribuição de Likes**
- Tipo: Histogram (Plotly `Histogram`)
- Dados: `like_count` de todos os comentários do vídeo
- Linhas verticais sobrepostas: média (μ), mediana, limiar de seleção do critério `media`
- Mostra visualmente onde os outliers de likes estão

### Tabela de Comentários Bot do Vídeo

Mesma tabela da Visão Geral, pré-filtrada para o vídeo selecionado, com filtro de critério ativo.

---

## Seção 3 — Meu Progresso

Dados exclusivos do pesquisador autenticado. Foco em acompanhamento da anotação e produtividade.

### KPI Cards

| Card                     | Valor                                                              |
|--------------------------|--------------------------------------------------------------------|
| Datasets atribuídos      | total de datasets que contêm comentários para eu anotar           |
| Datasets concluídos      | datasets onde anotei 100% dos comentários                         |
| Datasets pendentes       | datasets com ao menos um comentário ainda não anotado por mim     |
| Comentários anotados     | total que já classifiquei                                          |
| Comentários pendentes    | total que ainda falta anotar (em todos os meus datasets)          |
| Bots (meus)              | quantos classifiquei como `bot`                                    |
| Humanos (meus)           | quantos classifiquei como `humano`                                 |
| Conflitos gerados        | quantas vezes divergi de outro anotador                            |

### Tabela de Progresso por Dataset

Tabela central desta seção — uma linha por dataset:

| Coluna            | Descrição                                                   |
|-------------------|-------------------------------------------------------------|
| Dataset           | nome do dataset (`dQw4w9_percentil`)                        |
| Vídeo             | nome/ID do vídeo de origem                                  |
| Total             | total de comentários no dataset                             |
| Anotados por mim  | quantos já classifiquei                                     |
| Pendentes         | Total − Anotados                                            |
| % Concluído       | barra de progresso visual + percentual                      |
| Meus Bots         | quantos classifiquei como bot neste dataset                 |
| Conflitos         | nº de conflitos gerados por mim neste dataset               |
| Status            | badge: `Concluído` (verde) / `Em andamento` (azul) / `Não iniciado` (cinza) |
| Ação              | botão "Continuar anotando" → vai direto para US-04          |

### Gráficos

**Minha Distribuição de Rótulos**
- Tipo: Donut chart (Plotly `Pie`, `hole=0.5`)
- Fatias: Bot (vermelho), Humano (verde)
- Centro: total anotado por mim
- Legenda com contagem absoluta e percentual

**Progresso por Dataset**
- Tipo: Bar chart horizontal (Plotly `Bar`, `orientation="h"`)
- Eixo Y: nome do dataset
- Eixo X: % concluído (0–100)
- Cor por status: verde (#22c55e) se 100%, azul (#6366f1) se parcial, cinza (#94a3b8) se 0%
- Tooltip: "X de Y comentários anotados"

**Minhas Anotações ao Longo do Tempo**
- Tipo: Line chart (Plotly `Scatter`, `mode="lines+markers"`)
- Eixo X: data (agrupado por dia)
- Eixo Y: nº de anotações feitas por mim naquele dia
- Útil para o pesquisador acompanhar seu próprio ritmo

---

## Contrato de API

### `GET /dashboard/global`

**Query params:** `criteria=percentil,media,curtos` (opcional — filtra datasets pelos critérios ativos)

**Response 200:**
```json
{
  "summary": {
    "total_datasets": 13,
    "total_comments_annotated": 3539,
    "total_bots": 23,
    "total_humans": 3458,
    "total_conflicts": 58,
    "pending_conflicts": 34,
    "agreement_rate": 0.74
  },
  "active_criteria_filter": ["percentil", "media"],
  "label_distribution_chart": "<json plotly>",
  "comparativo_por_dataset_chart": "<json plotly>",
  "annotations_over_time_chart": "<json plotly>",
  "bot_rate_by_dataset_chart": "<json plotly>",
  "criteria_effectiveness_chart": "<json plotly>"
}
```

---

### `GET /dashboard/criteria-effectiveness`
Retorna a eficácia de cada critério de limpeza globalmente ou para um vídeo.

**Query params:** `video_id=string` (opcional)

**Response 200:**
```json
[
  {
    "criteria": "percentil",
    "group": "numerico",
    "total_datasets": 5,
    "total_comments_selected": 215,
    "total_bots": 48,
    "bot_rate": 0.223
  },
  {
    "criteria": "curtos",
    "group": "comportamental",
    "total_datasets": 3,
    "total_comments_selected": 87,
    "total_bots": 31,
    "bot_rate": 0.356
  }
]
```

---

### `GET /dashboard/video?video_id=...`

**Query params:** `video_id=string` (obrigatório), `criteria=percentil,curtos` (opcional)

**Response 200:**
```json
{
  "video_id": "string",
  "summary": {
    "total_comments_collected": 2847,
    "total_comments_in_datasets": 312,
    "total_annotated": 589,
    "total_bots": 98,
    "total_humans": 181,
    "total_conflicts": 27,
    "pending_conflicts": 14,
    "agreement_rate": 0.72
  },
  "active_criteria_filter": ["percentil"],
  "label_distribution_chart": "<json plotly>",
  "comparativo_por_dataset_chart": "<json plotly>",
  "bot_rate_by_criteria_chart": "<json plotly>",
  "comment_timeline_chart": "<json plotly>",
  "like_distribution_chart": "<json plotly>"
}
```

---

### `GET /dashboard/user`

**Response 200:**
```json
{
  "summary": {
    "total_datasets_assigned": 8,
    "datasets_completed": 3,
    "datasets_pending": 5,
    "total_annotated": 142,
    "total_pending": 87,
    "bots": 67,
    "humans": 75,
    "conflicts_generated": 18
  },
  "datasets": [
    {
      "dataset_id": "uuid",
      "dataset_name": "dQw4w9_percentil",
      "video_id": "dQw4w9WgXcQ",
      "total_comments": 43,
      "annotated_by_me": 43,
      "pending": 0,
      "percent_complete": 100.0,
      "my_bots": 12,
      "my_conflicts": 3,
      "status": "completed"
    }
  ],
  "my_label_distribution_chart": "<json plotly>",
  "my_progress_by_dataset_chart": "<json plotly>",
  "my_annotations_over_time_chart": "<json plotly>"
}
```

> `status`: `"completed"` (100%) | `"in_progress"` (> 0% e < 100%) | `"not_started"` (0%)

---

### `GET /dashboard/bots`
Retorna a tabela "Todos os Comentários Bot" com filtros e paginação.

**Query params:** `dataset_id`, `author`, `annotator_id`, `search`, `page`, `page_size`

**Response 200:**
```json
{
  "total": 23,
  "items": [
    {
      "dataset_name": "Rebuliço",
      "author_display_name": "@victorlopesit...",
      "text_original": "Gabriel Leite PRECISO DE AMIGOS...",
      "concordance_pct": 50,
      "conflict_status": "pending"
    }
  ]
}
```

> `concordance_pct`: 100% = ambos anotaram bot (consenso); 50% = um bot, um humano (conflito).

---

## Schema de banco

Nenhuma tabela nova — agregações SQL sobre `collections`, `comments`, `datasets`,
`dataset_entries`, `annotations`, `annotation_conflicts`, `resolutions`.

**Regra:** nunca carregar registros em Python para calcular em memória —
usar `func.count`, `func.avg`, `GROUP BY` no SQLAlchemy.

---

## Service — geração de gráficos

```python
# services/dashboard.py
import plotly.graph_objects as go
import plotly.io as pio

COLORS = {"humano": "#22c55e", "bot": "#ef4444", "conflito": "#f59e0b"}

def make_donut_chart(bots: int, humans: int, conflicts: int) -> str:
    total = bots + humans + conflicts
    fig = go.Figure(go.Pie(
        labels=["Humano", "Bot", "Conflito"],
        values=[humans, bots, conflicts],
        hole=0.5,
        marker_colors=[COLORS["humano"], COLORS["bot"], COLORS["conflito"]],
    ))
    fig.update_layout(
        annotations=[{"text": str(total), "x": 0.5, "y": 0.5, "font_size": 24, "showarrow": False}]
    )
    return pio.to_json(fig, validate=False)

def make_comparativo_chart(datasets: list[dict]) -> str:
    names = [d["name"] for d in datasets]
    fig = go.Figure(data=[
        go.Bar(name="Humano",   x=names, y=[d["humans"]    for d in datasets], marker_color=COLORS["humano"]),
        go.Bar(name="Bot",      x=names, y=[d["bots"]      for d in datasets], marker_color=COLORS["bot"]),
        go.Bar(name="Conflito", x=names, y=[d["conflicts"] for d in datasets], marker_color=COLORS["conflito"]),
    ])
    fig.update_layout(barmode="group", title="Comparativo por Dataset")
    return pio.to_json(fig, validate=False)

def make_timeline_chart(buckets: list[dict]) -> str:
    fig = go.Figure(go.Scatter(
        x=[b["date"] for b in buckets],
        y=[b["count"] for b in buckets],
        mode="lines+markers",
        line_color="#6366f1",
    ))
    fig.update_layout(title="Evolução das Anotações")
    return pio.to_json(fig, validate=False)

def make_like_distribution_chart(like_counts: list[int], mean: float, median: float) -> str:
    fig = go.Figure()
    fig.add_trace(go.Histogram(x=like_counts, nbinsx=40, name="Comentários", marker_color="#94a3b8"))
    fig.add_vline(x=mean,   line_dash="dash", line_color="red",    annotation_text="Média")
    fig.add_vline(x=median, line_dash="dot",  line_color="orange", annotation_text="Mediana")
    fig.update_layout(title="Distribuição de Likes")
    return pio.to_json(fig, validate=False)

def make_criteria_effectiveness_chart(data: list[dict]) -> str:
    """
    Bar chart agrupado: nº de datasets (cinza) e taxa de bots % (vermelho, eixo Y2)
    por critério de limpeza. Grupo 1 (numérico) e Grupo 2 (comportamental) separados.
    """
    criterios = [d["criteria"] for d in data]
    fig = go.Figure()
    fig.add_trace(go.Bar(
        name="Datasets com este critério",
        x=criterios,
        y=[d["total_datasets"] for d in data],
        marker_color="#94a3b8",
        yaxis="y1",
    ))
    fig.add_trace(go.Bar(
        name="Taxa de bots (%)",
        x=criterios,
        y=[round(d["bot_rate"] * 100, 1) for d in data],
        marker_color="#ef4444",
        yaxis="y2",
    ))
    fig.update_layout(
        barmode="group",
        title="Eficácia por Critério de Limpeza",
        yaxis={"title": "Nº de datasets"},
        yaxis2={"title": "Taxa de bots (%)", "overlaying": "y", "side": "right"},
        # linha divisória visual entre grupo numérico e comportamental
        shapes=[{"type": "line", "x0": 3.5, "x1": 3.5, "y0": 0, "y1": 1,
                 "xref": "x", "yref": "paper", "line": {"dash": "dot", "color": "#cbd5e1"}}],
    )
    return pio.to_json(fig, validate=False)

def compute_agreement_rate(db, video_id=None) -> float:
    from sqlalchemy import func
    q = (
        db.query(func.count(func.distinct(Annotation.label)).label("distinct_labels"))
        .group_by(Annotation.comment_id)
        .having(func.count(Annotation.id) == 2)
    )
    if video_id:
        q = q.join(Comment).join(Collection).filter(Collection.video_id == video_id)
    rows = q.all()
    if not rows:
        return 0.0
    consensus = sum(1 for r in rows if r.distinct_labels == 1)
    return round(consensus / len(rows), 4)
```

---

## Frontend — componentes sugeridos

```
pages/Dashboard/
├── DashboardPage.tsx              # layout com 3 abas: Visão Geral | Por Vídeo | Meu Progresso
│
├── GlobalTab.tsx                  # seção 1 — preserva e expande o protótipo atual
│   ├── KpiCards.tsx               # 7 cards (incluindo Agreement Rate e Conflitos Pendentes)
│   ├── CriteriaFilterBar.tsx      # checkboxes Grupo 1 (numérico) + Grupo 2 (comportamental)
│   ├── PlotlyChart.tsx            # donut + comparativo + evolução + taxa de bots + eficácia por critério
│   └── BotCommentsTable.tsx       # tabela filtável + filtro de critério de limpeza nos badges
│
├── VideoTab.tsx                   # seção 2 — seletor de vídeo + gráficos específicos
│   ├── VideoSelector.tsx          # dropdown com lista de vídeos coletados
│   ├── CriteriaFilterBar.tsx      # reutilizado — filtra datasets deste vídeo por critério
│   ├── KpiCards.tsx               # reutilizado com dados do vídeo selecionado
│   └── PlotlyChart.tsx            # donut + comparativo + taxa por critério + timeline + histograma
│
├── UserTab.tsx                    # seção 3 — progresso pessoal
│   ├── KpiCards.tsx               # 8 cards: datasets concluídos/pendentes, comentários, bots, conflitos
│   ├── DatasetProgressTable.tsx   # tabela por dataset: progresso, status, barra visual, botão "Continuar"
│   └── PlotlyChart.tsx            # donut de rótulos + barra horizontal de progresso + timeline pessoal
│
└── useDashboard.ts                # hook: fetchGlobal(criteria?), fetchVideo(id, criteria?),
                                 #        fetchUser(), fetchBots(filters), fetchCriteriaEffectiveness()
```

**Componente `PlotlyChart` (genérico):**
```typescript
import Plotly from "plotly.js-dist-min";
import { useEffect, useRef } from "react";

export function PlotlyChart({ figureJson }: { figureJson: string }) {
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!ref.current) return;
    const fig = JSON.parse(figureJson);
    Plotly.newPlot(ref.current, fig.data, { ...fig.layout, autosize: true });
    const ro = new ResizeObserver(() => Plotly.Plots.resize(ref.current!));
    ro.observe(ref.current);
    return () => ro.disconnect();
  }, [figureJson]);
  return <div ref={ref} style={{ width: "100%", minHeight: 380 }} />;
}
```

**UX obrigatória:**
- Aba "Por Vídeo": dropdown atualiza todos os gráficos e KPIs ao mudar seleção
- Coluna "Concord." na tabela: 100% verde, 50% amarelo, abaixo de 50% vermelho
- Badge de status na tabela: `Pendente` (laranja) / `Resolvido` (cinza) para conflitos
- Loading skeleton enquanto dados carregam
- Visão Geral e Por Vídeo não exibem nomes individuais de pesquisadores

---

## Casos de erro

| Cenário                | Comportamento                                                  |
|------------------------|----------------------------------------------------------------|
| Sem dados ainda        | Zeros nos KPIs, gráficos com estado vazio — nunca HTTP 404     |
| `video_id` não existe  | Mensagem inline na aba "Por Vídeo": "Vídeo não encontrado."   |

---

## Testes obrigatórios (Pytest)

### Referência de dublês

| Dublê | Quando usar                                                                           |
|-------|---------------------------------------------------------------------------------------|
| Stub  | Controlar `get_current_user` e isolar endpoints de dashboard do banco real            |
| Mock  | Verificar que nenhuma query expõe `username` de outros pesquisadores                  |
| Spy   | Observar quais agregações SQL foram executadas (sem substituir o banco)               |
| Dummy | `video_id` inexistente para testar resposta com dados vazios (deve retornar zeros)    |
| Fake  | Banco SQLite em memória pré-populado com fixture de anotações, conflitos e resoluções |

### Casos de teste

```python
# conftest.py
@pytest.fixture
def fake_db_populated(fake_db):
    """
    Fake: banco pré-populado com:
    - 2 vídeos, 3 datasets
    - 10 comentários anotados: 6 humano, 3 bot, 1 conflito
    - 1 conflito resolvido, 1 pendente
    - 2 pesquisadores com anotações divergentes em 1 comentário
    """
    ...
    return fake_db
```

**`GET /dashboard/global` retorna KPIs corretos e JSON Plotly válido**
- Fake: banco pré-populado
- Stub: `get_current_user` retorna qualquer usuário autenticado
- Afirma `summary.total_bots == 3`, `summary.total_conflicts == 2`, etc.
- Afirma que cada `*_chart` é JSON parseável com chaves `data` e `layout`

**`GET /dashboard/video` retorna apenas dados do vídeo filtrado**
- Fake: banco com dois vídeos distintos
- Stub: `get_current_user` retorna usuário autenticado
- Afirma que KPIs somam apenas os comentários/anotações do `video_id` requisitado

**`GET /dashboard/user` retorna apenas dados do pesquisador autenticado**
- Fake: banco com anotações de dois pesquisadores diferentes
- Stub: `get_current_user` retorna pesquisador A
- Afirma `summary.total_annotated` conta apenas as anotações do pesquisador A

**`agreement_rate` calculado corretamente**
- Fake: banco com 4 comentários — 2 em consenso, 1 em conflito, 1 com só 1 anotação
- Spy: `mocker.spy(services.dashboard, "compute_agreement_rate")` — verifica que foi chamada e retornou o valor correto
- Afirma `agreement_rate == 0.667` (2 consenso / 3 com 2 anotações)

**`GET /dashboard/bots` com filtro de dataset retorna apenas aquele dataset**
- Fake: banco com bots em dois datasets distintos
- Stub: `get_current_user` retorna usuário autenticado
- Afirma que todos os itens retornados têm `dataset_id == dataset_filtrado`

**Nenhum endpoint expõe `username` de outros pesquisadores**
- Fake: banco com dois pesquisadores nomeados
- Stub: `get_current_user` retorna pesquisador A
- Mock: inspeciona o JSON de todos os `*_chart` retornados
  — afirma que o `username` do pesquisador B não aparece em nenhum campo serializado
  `assert "maria" not in response.text`

**`GET /dashboard/global` com `criteria=percentil` filtra corretamente**
- Fake: banco com datasets gerados por critérios diferentes (`percentil`, `media`, `curtos`)
- Stub: `get_current_user`
- Afirma que KPIs somam apenas os datasets com `"percentil"` em `criteria_applied`

**Dados ausentes retornam zeros, não 404**
- Dummy: `video_id="video_inexistente"`
- Stub: `get_current_user`
- Afirma HTTP 200 com `summary.total_annotated == 0` e charts vazios parseáveis

---

## Dependências com outras USs

- **US-02:** `total_comments_collected` e timeline de comentários por data de postagem
- **US-03:** datasets, comentários selecionados e distribuição por critério
- **US-04:** anotações, conflitos e cálculo do agreement rate
- **US-05:** `resolutions` para status dos conflitos na tabela de bots
